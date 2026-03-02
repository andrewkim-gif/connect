"""
WebSocket Voice Call Endpoint
WS /ws/voice/call - 실시간 음성통화 (STT → LLM → TTS)
"""

import logging
import base64
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from config import settings
from services.voice_pipeline import get_voice_pipeline
from services.voice_pipeline_streaming import get_streaming_voice_pipeline
from core.connection import connection_manager
from core.rate_limiter import get_rate_limiter


def get_active_pipeline():
    """설정에 따라 적절한 파이프라인 반환"""
    if settings.VOICE_PIPELINE_STREAMING:
        return get_streaming_voice_pipeline()
    return get_voice_pipeline()

logger = logging.getLogger(__name__)
router = APIRouter()


# WebSocket 에러 코드 정의
class VoiceCallCloseCode:
    """Voice Call WebSocket Close Codes"""

    NORMAL = 1000
    GOING_AWAY = 1001
    PROTOCOL_ERROR = 1002
    INVALID_DATA = 1003

    # Custom codes (4000-4999)
    UNAUTHORIZED = 4001
    RATE_LIMITED = 4002
    AUDIO_TOO_LONG = 4003
    PIPELINE_ERROR = 4004
    NOT_ENABLED = 4005


async def handle_voice_input(
    client_id: str,
    audio_base64: str,
    voice_id: Optional[str] = None,
) -> None:
    """
    음성 입력 처리 (STT → LLM → TTS 파이프라인)

    Args:
        client_id: 클라이언트 ID
        websocket: WebSocket 연결
        audio_base64: Base64 인코딩된 PCM 오디오 (16-bit, 16kHz)
        voice_id: TTS 음성 ID (기본: gd-default)
    """
    # Rate Limit 확인
    rate_limiter = get_rate_limiter()
    allowed, retry_after = rate_limiter.check_websocket(client_id)
    if not allowed:
        await connection_manager.send_json(client_id, {
            "type": "error",
            "code": VoiceCallCloseCode.RATE_LIMITED,
            "message": "Rate limit exceeded",
            "retry_after": int(retry_after) + 1,
        })
        return

    # 오디오 디코딩
    try:
        audio_bytes = base64.b64decode(audio_base64)
    except Exception as e:
        await connection_manager.send_json(client_id, {
            "type": "error",
            "code": VoiceCallCloseCode.INVALID_DATA,
            "message": f"Invalid base64 audio: {e}",
        })
        return

    # 오디오 길이 검증 (16kHz, 16-bit = 32000 bytes/sec)
    max_bytes = settings.VOICE_CALL_MAX_AUDIO_LENGTH * 32000
    if len(audio_bytes) > max_bytes:
        await connection_manager.send_json(client_id, {
            "type": "error",
            "code": VoiceCallCloseCode.AUDIO_TOO_LONG,
            "message": f"Audio exceeds {settings.VOICE_CALL_MAX_AUDIO_LENGTH}s limit",
        })
        return

    # 파이프라인 실행 (스트리밍 모드 지원)
    pipeline = get_active_pipeline()

    try:
        # client_id를 session_id로 전달하여 사용자별 대화 기록 격리
        async for event in pipeline.process_audio(
            audio_bytes=audio_bytes,
            sample_rate=settings.VOICE_CALL_SAMPLE_RATE_IN,
            voice_id=voice_id or "gd-default",
            session_id=client_id,  # 사용자별 세션 격리
        ):
            # 연결 확인
            if not connection_manager.get_connection(client_id):
                logger.warning(f"[{client_id}] Connection lost during pipeline")
                pipeline.interrupt()
                return

            # 이벤트 타입별 처리
            if event.type == "transcription":
                # STT 결과 전송
                await connection_manager.send_json(client_id, {
                    "type": "transcription",
                    "text": event.data["text"],
                    "language": event.data.get("language"),
                    "confidence": event.data.get("confidence"),
                })

            elif event.type == "response_start":
                # LLM 응답 시작
                await connection_manager.send_json(client_id, {
                    "type": "response_start",
                })

            elif event.type == "response_text":
                # LLM 텍스트 청크 (디버그용)
                await connection_manager.send_json(client_id, {
                    "type": "response_text",
                    "text": event.data["text"],
                    "is_final": event.data.get("is_final", False),
                })

            elif event.type == "audio":
                # TTS 오디오 청크 (바이너리)
                success = await connection_manager.send_bytes(client_id, event.data)
                if not success:
                    logger.warning(f"[{client_id}] Failed to send audio chunk")
                    pipeline.interrupt()
                    return

            elif event.type == "response_end":
                # 응답 완료
                await connection_manager.send_json(client_id, {
                    "type": "response_end",
                    "metrics": event.metrics,
                })

            elif event.type == "interrupted":
                await connection_manager.send_json(client_id, {
                    "type": "interrupted",
                })

            elif event.type == "error":
                await connection_manager.send_json(client_id, {
                    "type": "error",
                    "code": event.data.get("code", "UNKNOWN"),
                    "message": event.data.get("message", "Unknown error"),
                })

    except Exception as e:
        logger.error(f"[{client_id}] Pipeline error: {e}", exc_info=True)
        await connection_manager.send_json(client_id, {
            "type": "error",
            "code": VoiceCallCloseCode.PIPELINE_ERROR,
            "message": str(e),
        })


@router.websocket("/ws/voice")
async def websocket_voice_call(
    websocket: WebSocket,
    api_key: Optional[str] = Query(default=None, alias="api_key"),
):
    """
    실시간 음성통화 WebSocket 엔드포인트

    연결: ws://server:5001/ws/voice?api_key=xxx

    Client → Server (JSON):
        {
            "type": "voice_input",
            "audio": "<base64 PCM 16-bit 16kHz>",
            "voice_id": "gd-default"  // optional
        }
        {"type": "interrupt"}  // 현재 응답 중단
        {"type": "reset"}      // 대화 기록 초기화
        {"type": "ping"}

    Server → Client:
        {"type": "connected", "client_id": "...", "sample_rate_in": 16000, "sample_rate_out": 24000}
        {"type": "transcription", "text": "안녕하세요", "language": "ko", "confidence": 0.95}
        {"type": "response_start"}
        {"type": "response_text", "text": "야 뭐야", "is_final": false}
        [Binary: PCM audio chunks, 16-bit, 24kHz, mono]
        {"type": "response_end", "metrics": {...}}
        {"type": "interrupted"}
        {"type": "pong"}
        {"type": "error", "code": "...", "message": "..."}
    """
    # 먼저 WebSocket 연결 수락 (close() 전에 accept() 필요)
    await websocket.accept()

    # 기능 활성화 확인
    if not settings.VOICE_CALL_ENABLED:
        await websocket.close(
            code=VoiceCallCloseCode.NOT_ENABLED,
            reason="Voice call feature is not enabled",
        )
        return

    # 인증 (이미 accept 되었으므로 close만 처리)
    if settings.API_KEYS:
        if not api_key or api_key not in settings.API_KEYS:
            await websocket.close(
                code=VoiceCallCloseCode.UNAUTHORIZED,
                reason="Invalid or missing API key",
            )
            logger.warning("Voice call auth failed: invalid API key")
            return

    # 연결 등록 (이미 accept() 됨)
    client_id = await connection_manager.register(websocket, api_key)
    if not client_id:
        return

    pipeline = get_active_pipeline()

    try:
        # 연결 확인 메시지
        await connection_manager.send_json(client_id, {
            "type": "connected",
            "client_id": client_id,
            "sample_rate_in": settings.VOICE_CALL_SAMPLE_RATE_IN,
            "sample_rate_out": settings.VOICE_CALL_SAMPLE_RATE_OUT,
            "max_audio_length": settings.VOICE_CALL_MAX_AUDIO_LENGTH,
        })

        logger.info(f"[{client_id}] Voice call connected")

        # 메시지 처리 루프
        while True:
            try:
                data = await websocket.receive_json()
                connection_manager.record_received(client_id)

                msg_type = data.get("type")

                if msg_type == "start_call":
                    # 통화 시작 요청 - 클라이언트가 링톤 재생 시작
                    voice_id = data.get("voice_id", "gd-default")
                    logger.info(f"[{client_id}] Call started with voice_id={voice_id}")

                    # 1. call_started 응답 (클라이언트가 링톤 재생)
                    await connection_manager.send_json(client_id, {
                        "type": "call_started",
                        "voice_id": voice_id,
                    })

                    # 2. 링톤 시간 후 자동으로 greeting 생성 (2-4초 대기)
                    import asyncio
                    import random
                    ring_duration = 2.0 + random.random() * 2.0  # 2-4초
                    await asyncio.sleep(ring_duration)

                    # 3. 인사말 TTS 생성
                    import numpy as np
                    from services.tts_engine import tts_engine

                    greetings = [
                        "응~ 안녕? 무슨 일이야?",
                        "어 안녕! 왜 전화했어?",
                        "응 나야~ 뭐야?",
                        "여보세요? 아 안녕!",
                    ]
                    greeting_text = random.choice(greetings)

                    # 응답 시작
                    await connection_manager.send_json(client_id, {
                        "type": "response_start",
                    })

                    # 텍스트 전송
                    await connection_manager.send_json(client_id, {
                        "type": "response_text",
                        "text": greeting_text,
                        "is_final": True,
                    })

                    # TTS 생성
                    try:
                        mode = "finetuned" if voice_id in ["gd-default", "finetuned"] else "auto"
                        audio_array, sample_rate, processing_time = await tts_engine.synthesize(
                            text=greeting_text,
                            mode=mode,
                        )
                        if audio_array is not None and connection_manager.get_connection(client_id):
                            # Float32 → Int16 PCM 변환
                            audio_int16 = (audio_array * 32767).astype(np.int16)
                            audio_bytes = audio_int16.tobytes()

                            # 청크 단위로 전송 (100ms at 24kHz)
                            chunk_size = 4800
                            for i in range(0, len(audio_bytes), chunk_size):
                                chunk = audio_bytes[i:i+chunk_size]
                                if connection_manager.get_connection(client_id):
                                    await connection_manager.send_bytes(client_id, chunk)
                                else:
                                    break

                            logger.info(f"[{client_id}] Greeting TTS: '{greeting_text}' ({processing_time:.0f}ms)")
                    except Exception as e:
                        logger.error(f"[{client_id}] Greeting TTS error: {e}")

                    # 응답 완료 + listening 상태로 전환
                    await connection_manager.send_json(client_id, {
                        "type": "response_end",
                        "metrics": {"type": "greeting"},
                    })

                    # listening 상태 알림 (클라이언트가 녹음 시작)
                    await connection_manager.send_json(client_id, {
                        "type": "listening",
                    })

                elif msg_type == "voice_input":
                    audio_base64 = data.get("audio")
                    if not audio_base64:
                        await connection_manager.send_json(client_id, {
                            "type": "error",
                            "code": VoiceCallCloseCode.INVALID_DATA,
                            "message": "Audio data is required",
                        })
                        continue

                    await handle_voice_input(
                        client_id=client_id,
                        audio_base64=audio_base64,
                        voice_id=data.get("voice_id"),
                    )

                elif msg_type == "audio_chunk":
                    # 스트리밍 오디오 청크 수신 - 버퍼에 누적
                    audio_base64 = data.get("audio")
                    if audio_base64:
                        if not hasattr(websocket, '_audio_buffer'):
                            websocket._audio_buffer = []
                        websocket._audio_buffer.append(audio_base64)

                elif msg_type == "audio_end":
                    # 발화 종료 - 버퍼의 오디오 처리
                    if hasattr(websocket, '_audio_buffer') and websocket._audio_buffer:
                        # 모든 청크를 합쳐서 처리
                        combined_audio = ''.join(websocket._audio_buffer)
                        websocket._audio_buffer = []

                        await handle_voice_input(
                            client_id=client_id,
                            audio_base64=combined_audio,
                            voice_id=data.get("voice_id"),
                        )
                    else:
                        logger.warning(f"[{client_id}] audio_end received but no audio buffer")

                elif msg_type == "interrupt":
                    reason = data.get("reason", "manual")
                    if pipeline.is_processing:
                        pipeline.interrupt()

                    # Barge-in인 경우 LLM 컨텍스트에 기록
                    if reason == "barge_in":
                        logger.info(f"[{client_id}] Barge-in detected - user interrupted GD")
                        # LLM 엔진에 끼어들기 컨텍스트 추가
                        llm_engine = pipeline.llm if hasattr(pipeline, 'llm') else None
                        if llm_engine:
                            llm_engine.add_system_context(
                                session_id=client_id,
                                context="[유저가 끼어들어서 내 말을 끊었습니다. 자연스럽게 대화를 이어가세요.]"
                            )

                    await connection_manager.send_json(client_id, {
                        "type": "interrupted",
                        "reason": reason,
                    })

                elif msg_type == "reset":
                    # 세션별 대화 기록 초기화
                    pipeline.reset_conversation(session_id=client_id)
                    await connection_manager.send_json(client_id, {
                        "type": "reset_complete",
                    })

                elif msg_type == "greeting":
                    # 인사 TTS 생성 (서버가 인사말 선택 - Single Source of Truth)
                    import random
                    import numpy as np
                    from services.tts_engine import tts_engine

                    voice_id = data.get("voice_id", "gd-default")

                    # 서버에서 인사말 선택 (클라이언트가 아님!)
                    greetings = [
                        "응~ 안녕? 무슨 일이야?",
                        "어 안녕! 왜 전화했어?",
                        "응 나야~ 뭐야?",
                        "여보세요? 아 안녕!",
                    ]
                    greeting_text = random.choice(greetings)

                    # 1. 응답 시작 알림
                    await connection_manager.send_json(client_id, {
                        "type": "response_start",
                    })

                    # 2. 실제 텍스트 전송 (클라이언트는 이것만 표시)
                    await connection_manager.send_json(client_id, {
                        "type": "response_text",
                        "text": greeting_text,
                        "is_final": True,
                    })

                    # 3. TTS 생성 및 스트리밍
                    try:
                        # voice_id가 "finetuned"가 아니면 "auto" 사용
                        mode = "finetuned" if voice_id in ["gd-default", "finetuned"] else "auto"
                        audio_array, sample_rate, processing_time = await tts_engine.synthesize(
                            text=greeting_text,
                            mode=mode,
                        )
                        if audio_array is not None and connection_manager.get_connection(client_id):
                            # Float32 → Int16 PCM 변환
                            audio_int16 = (audio_array * 32767).astype(np.int16)
                            audio_bytes = audio_int16.tobytes()

                            # 청크 단위로 전송 (스트리밍 효과)
                            chunk_size = 4800  # 100ms at 24kHz (2 bytes per sample)
                            for i in range(0, len(audio_bytes), chunk_size):
                                chunk = audio_bytes[i:i+chunk_size]
                                if connection_manager.get_connection(client_id):
                                    await connection_manager.send_bytes(client_id, chunk)
                                else:
                                    break

                            logger.info(f"[{client_id}] Greeting TTS: '{greeting_text}' ({processing_time:.0f}ms)")
                    except Exception as e:
                        logger.error(f"[{client_id}] Greeting TTS error: {e}")

                    # 4. 응답 완료
                    await connection_manager.send_json(client_id, {
                        "type": "response_end",
                        "metrics": {"type": "greeting"},
                    })

                elif msg_type == "ping":
                    await connection_manager.send_json(client_id, {"type": "pong"})

                elif msg_type == "gd_initiative":
                    # GD가 먼저 말 걸기 (유저 5초 침묵 시)
                    logger.info(f"[{client_id}] GD Initiative triggered - user silent for 5s")

                    # 스트리밍 파이프라인 직접 사용 (process_text 메서드 필요)
                    streaming_pipeline = get_streaming_voice_pipeline()

                    # 이미 처리 중이면 무시 (중복 방지)
                    if streaming_pipeline.is_processing or pipeline.is_processing:
                        logger.warning(f"[{client_id}] GD Initiative ignored - already processing")
                        await connection_manager.send_json(client_id, {
                            "type": "gd_initiative_skipped",
                            "reason": "already_processing",
                        })
                        continue

                    # LLM에게 GD가 먼저 말걸도록 프롬프트
                    gd_prompts = [
                        "[유저가 5초간 아무 말도 안 합니다. 자연스럽게 대화를 이끌어가세요. 뭐 하냐고 물어보거나, 할 말 없으면 끊어도 된다고 해주세요.]",
                        "[유저가 말이 없네요. 궁금한 거 있으면 물어보라고 하거나, 심심하면 이야기 해달라고 해보세요.]",
                    ]
                    import random
                    gd_prompt = random.choice(gd_prompts)

                    # 파이프라인으로 GD 발화 생성
                    try:
                        async for event in streaming_pipeline.process_text(
                            text=gd_prompt,
                            voice_id=data.get("voice_id", "gd-default"),
                            session_id=client_id,
                        ):
                            if event.type == "response_start":
                                await connection_manager.send_json(client_id, {
                                    "type": "response_start",
                                })
                            elif event.type == "response_text":
                                await connection_manager.send_json(client_id, {
                                    "type": "response_text",
                                    "text": event.data["text"],
                                    "is_final": event.data.get("is_final", False),
                                })
                            elif event.type == "audio":
                                await connection_manager.send_bytes(client_id, event.data)
                            elif event.type == "response_end":
                                await connection_manager.send_json(client_id, {
                                    "type": "response_end",
                                    "metrics": event.metrics,
                                })
                    except Exception as e:
                        logger.error(f"[{client_id}] GD Initiative error: {e}")

                elif msg_type == "end_call":
                    # 통화 종료 요청
                    logger.info(f"[{client_id}] End call requested")
                    if pipeline.is_processing:
                        pipeline.interrupt()
                    await connection_manager.send_json(client_id, {
                        "type": "call_ended",
                    })
                    break  # WebSocket 연결 종료

                else:
                    await connection_manager.send_json(client_id, {
                        "type": "error",
                        "code": VoiceCallCloseCode.INVALID_DATA,
                        "message": f"Unknown message type: {msg_type}",
                    })

            except WebSocketDisconnect as e:
                logger.info(f"[{client_id}] Voice call disconnected: code={e.code}")
                break

    except Exception as e:
        logger.error(f"[{client_id}] Voice call error: {e}", exc_info=True)

    finally:
        # 연결 정리
        if pipeline.is_processing:
            pipeline.interrupt()
        # 세션 메모리 정리 (대화 기록 삭제)
        pipeline.remove_session(session_id=client_id)
        await connection_manager.disconnect(client_id)
        logger.info(f"[{client_id}] Voice call cleanup complete")
