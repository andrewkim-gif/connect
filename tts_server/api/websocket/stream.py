"""
WebSocket TTS Streaming Endpoint
WS /ws/tts/stream
"""

import time
import logging
import asyncio
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import ValidationError

from config import settings
from models.request import WebSocketMessage
from services.tts_engine import tts_engine
from services.voice_manager import voice_manager
from services.streaming import streaming_handler
from core.connection import connection_manager
from core.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)
router = APIRouter()


# WebSocket 에러 코드 정의
class WSCloseCode:
    """WebSocket Close Codes"""

    NORMAL = 1000  # 정상 종료
    GOING_AWAY = 1001  # 서버 종료
    PROTOCOL_ERROR = 1002  # 프로토콜 에러
    INVALID_DATA = 1003  # 잘못된 데이터

    # Custom codes (4000-4999)
    UNAUTHORIZED = 4001  # 인증 실패
    RATE_LIMITED = 4002  # Rate limit 초과
    TEXT_TOO_LONG = 4003  # 텍스트 길이 초과
    VOICE_NOT_FOUND = 4004  # 음성 ID 없음
    SYNTHESIS_ERROR = 4005  # TTS 합성 실패


async def authenticate_websocket(
    websocket: WebSocket,
    api_key: Optional[str],
) -> bool:
    """
    WebSocket 인증

    Args:
        websocket: WebSocket 연결
        api_key: Query parameter로 전달된 API 키

    Returns:
        True: 인증 성공
        False: 인증 실패 (연결 종료됨)
    """
    # 개발 모드에서 API 키가 설정되지 않은 경우 생략
    if settings.DEBUG and not settings.API_KEYS:
        return True

    # API 키 검증
    if settings.API_KEYS:
        if not api_key or api_key not in settings.API_KEYS:
            await websocket.close(
                code=WSCloseCode.UNAUTHORIZED,
                reason="Invalid or missing API key",
            )
            logger.warning(f"WebSocket auth failed: invalid API key")
            return False

    return True


async def handle_synthesize(
    client_id: str,
    message: WebSocketMessage,
) -> None:
    """
    합성 요청 처리

    1. 유효성 검증
    2. Rate Limit 확인
    3. TTS 합성
    4. 청크 스트리밍
    """
    # 텍스트 검증
    if not message.text:
        await connection_manager.send_json(client_id, {
            "type": "error",
            "code": WSCloseCode.INVALID_DATA,
            "message": "Text is required",
        })
        return

    if len(message.text) > settings.MAX_TEXT_LENGTH:
        await connection_manager.send_json(client_id, {
            "type": "error",
            "code": WSCloseCode.TEXT_TOO_LONG,
            "message": f"Text exceeds {settings.MAX_TEXT_LENGTH} characters",
        })
        return

    # 음성 ID 검증
    voice_id = message.voice_id or "gd-default"
    if not voice_manager.has_voice(voice_id):
        await connection_manager.send_json(client_id, {
            "type": "error",
            "code": WSCloseCode.VOICE_NOT_FOUND,
            "message": f"Voice not found: {voice_id}",
        })
        return

    # Rate Limit 확인
    rate_limiter = get_rate_limiter()
    allowed, retry_after = rate_limiter.check_websocket(client_id)
    if not allowed:
        await connection_manager.send_json(client_id, {
            "type": "error",
            "code": WSCloseCode.RATE_LIMITED,
            "message": "Rate limit exceeded",
            "retry_after": int(retry_after) + 1,
        })
        return

    # 이미 합성 중인 경우
    if connection_manager.is_synthesizing(client_id):
        await connection_manager.send_json(client_id, {
            "type": "error",
            "code": WSCloseCode.PROTOCOL_ERROR,
            "message": "Synthesis already in progress",
        })
        return

    # 합성 시작
    connection_manager.set_synthesizing(client_id, True)
    start_time = time.time()

    try:
        # 시작 메시지
        await connection_manager.send_json(client_id, {
            "type": "start",
            "voice_id": voice_id,
            "timestamp": start_time,
        })

        # TTS 합성
        audio, sample_rate, processing_time = await tts_engine.synthesize(
            text=message.text,
            voice_id=voice_id,
        )

        # TTFA (Time To First Audio) 측정
        ttfa = (time.time() - start_time) * 1000
        logger.info(f"[{client_id}] TTFA: {ttfa:.0f}ms")

        # 청크 스트리밍
        chunk_count = 0
        async for chunk in streaming_handler.stream_chunks(audio):
            # 연결 확인
            if not connection_manager.get_connection(client_id):
                logger.warning(f"[{client_id}] Connection lost during streaming")
                return

            # 바이너리 청크 전송
            success = await connection_manager.send_bytes(client_id, chunk.data)
            if not success:
                logger.warning(f"[{client_id}] Failed to send chunk {chunk.index}")
                return

            chunk_count += 1

        # 완료 메시지
        duration = len(audio) / sample_rate
        total_time = (time.time() - start_time) * 1000

        await connection_manager.send_json(client_id, {
            "type": "end",
            "duration": round(duration, 3),
            "chunks": chunk_count,
            "ttfa_ms": int(ttfa),
            "total_ms": int(total_time),
        })

        logger.info(
            f"[{client_id}] Streamed: {len(message.text)} chars → "
            f"{duration:.2f}s audio ({chunk_count} chunks, {total_time:.0f}ms)"
        )

    except Exception as e:
        logger.error(f"[{client_id}] Synthesis error: {e}", exc_info=True)
        await connection_manager.send_json(client_id, {
            "type": "error",
            "code": WSCloseCode.SYNTHESIS_ERROR,
            "message": "TTS synthesis failed",
            "detail": str(e),
        })

    finally:
        connection_manager.set_synthesizing(client_id, False)


@router.websocket("/ws/tts/stream")
async def websocket_tts_stream(
    websocket: WebSocket,
    api_key: Optional[str] = Query(default=None, alias="api_key"),
):
    """
    WebSocket TTS 스트리밍 엔드포인트

    연결: ws://server:8000/ws/tts/stream?api_key=xxx

    Client → Server (JSON):
        {"type": "synthesize", "text": "안녕하세요", "voice_id": "gd-default"}
        {"type": "ping"}

    Server → Client:
        {"type": "start", "voice_id": "gd-default", "timestamp": 1234567890.123}
        [Binary: PCM audio chunks, 16-bit, 24kHz, mono]
        {"type": "end", "duration": 2.5, "chunks": 25, "ttfa_ms": 120, "total_ms": 650}
        {"type": "pong"}
        {"type": "error", "code": 4005, "message": "..."}
    """
    # 인증
    if not await authenticate_websocket(websocket, api_key):
        return

    # 연결 수락
    client_id = await connection_manager.connect(websocket, api_key)
    if not client_id:
        return

    try:
        # 연결 확인 메시지
        await connection_manager.send_json(client_id, {
            "type": "connected",
            "client_id": client_id,
            "sample_rate": settings.SAMPLE_RATE,
            "chunk_size": settings.CHUNK_SIZE,
            "chunk_duration_ms": streaming_handler.get_chunk_duration_ms(),
        })

        # 메시지 처리 루프
        while True:
            try:
                # JSON 메시지 수신
                data = await websocket.receive_json()
                connection_manager.record_received(client_id)

                # 메시지 파싱
                try:
                    message = WebSocketMessage(**data)
                except ValidationError as e:
                    await connection_manager.send_json(client_id, {
                        "type": "error",
                        "code": WSCloseCode.INVALID_DATA,
                        "message": "Invalid message format",
                        "detail": str(e),
                    })
                    continue

                # 메시지 타입별 처리
                if message.type == "synthesize":
                    await handle_synthesize(client_id, message)

                elif message.type == "ping":
                    await connection_manager.send_json(client_id, {"type": "pong"})

                else:
                    await connection_manager.send_json(client_id, {
                        "type": "error",
                        "code": WSCloseCode.INVALID_DATA,
                        "message": f"Unknown message type: {message.type}",
                    })

            except WebSocketDisconnect as e:
                logger.info(f"[{client_id}] Client disconnected: code={e.code}")
                break

    except Exception as e:
        logger.error(f"[{client_id}] WebSocket error: {e}", exc_info=True)

    finally:
        # 연결 정리
        await connection_manager.disconnect(client_id)
