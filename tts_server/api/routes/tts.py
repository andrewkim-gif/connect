"""
TTS Endpoints
POST /api/v1/tts/synthesize
"""

import io
import uuid
import logging
import soundfile as sf
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse

from models.request import SynthesizeRequest, StyleSynthesizeRequest, HybridSynthesizeRequest
from models.response import ErrorCode
from services.tts_engine import tts_engine
from services.voice_manager import voice_manager
from services.model_manager import model_manager
from api.deps import verify_api_key, check_rate_limit_synthesize
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/synthesize",
    summary="텍스트 → 음성 합성",
    description="텍스트를 음성으로 변환합니다. WAV 또는 PCM 포맷으로 반환합니다.",
    responses={
        200: {
            "content": {"audio/wav": {}},
            "description": "합성된 오디오 파일",
        },
        400: {"description": "잘못된 요청"},
        401: {"description": "인증 실패"},
        429: {"description": "Rate limit 초과"},
        500: {"description": "서버 에러"},
    },
)
async def synthesize(
    request: SynthesizeRequest,
    http_request: Request,
    api_key: str = Depends(verify_api_key),
    _rate_limit: None = Depends(check_rate_limit_synthesize),
):
    """
    텍스트를 음성으로 합성

    헤더로 반환되는 메타데이터:
    - X-Audio-Duration: 오디오 길이 (초)
    - X-Processing-Time: 처리 시간 (ms)
    - X-Sample-Rate: 샘플 레이트
    - X-Voice-ID: 사용된 음성 ID
    - X-Request-ID: 요청 ID
    """
    # Request ID: 미들웨어에서 생성된 것 사용, 없으면 새로 생성
    request_id = getattr(http_request.state, "request_id", str(uuid.uuid4())[:8])

    # 텍스트 길이 검증
    if len(request.text) > settings.MAX_TEXT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": ErrorCode.TEXT_TOO_LONG,
                "message": f"Text exceeds maximum length of {settings.MAX_TEXT_LENGTH}",
                "request_id": request_id,
            },
        )

    try:
        # TTS 합성
        # finetuned: 학습된 GD 목소리 사용
        # clone/icl: 캐릭터별 ICL 방식 음성 복제
        audio, sample_rate, processing_time = await tts_engine.synthesize(
            text=request.text,
            mode=request.mode.value,  # ModelMode enum → str
            character_id=request.character_id,  # 캐릭터 ID
            voice_mode=request.voice_mode,  # finetuned 또는 icl
        )

        duration = tts_engine.get_audio_duration(audio, sample_rate)

        logger.info(
            f"[{request_id}] Synthesized: "
            f"mode={request.mode.value}, "
            f"text_len={len(request.text)}, "
            f"duration={duration:.2f}s, "
            f"time={processing_time:.0f}ms"
        )

        # 응답 헤더
        headers = {
            "X-Audio-Duration": str(round(duration, 3)),
            "X-Processing-Time": str(int(processing_time)),
            "X-Sample-Rate": str(sample_rate),
            "X-Model-Mode": request.mode.value,
            "X-Request-ID": request_id,
        }

        # WAV 포맷으로 반환
        if request.format == "wav":
            buffer = io.BytesIO()
            sf.write(buffer, audio, sample_rate, format="WAV")
            buffer.seek(0)

            return StreamingResponse(
                buffer,
                media_type="audio/wav",
                headers=headers,
            )

        # PCM 포맷으로 반환 (raw bytes)
        else:
            # int16으로 변환
            audio_int16 = (audio * 32767).astype("int16")
            buffer = io.BytesIO(audio_int16.tobytes())

            return StreamingResponse(
                buffer,
                media_type="audio/pcm",
                headers=headers,
            )

    except Exception as e:
        logger.error(f"[{request_id}] Synthesis error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": ErrorCode.MODEL_ERROR,
                "message": "TTS synthesis failed",
                "detail": str(e),
                "request_id": request_id,
            },
        )


@router.post(
    "/synthesize/style",
    summary="스타일 제어 합성 (VoiceDesign)",
    description="자연어 지시로 감정/억양을 제어하여 음성을 합성합니다.",
    responses={
        200: {
            "content": {"audio/wav": {}},
            "description": "합성된 오디오 파일",
        },
        400: {"description": "잘못된 요청"},
        503: {"description": "VoiceDesign 모델 비활성화"},
    },
)
async def synthesize_with_style(
    request: StyleSynthesizeRequest,
    http_request: Request,
    api_key: str = Depends(verify_api_key),
    _rate_limit: None = Depends(check_rate_limit_synthesize),
):
    """
    VoiceDesign 모델로 스타일/감정 제어 합성

    instruct 예시:
    - "밝고 활기찬 목소리로 말하세요"
    - "웃으면서 유쾌하게 말하세요"
    - "차분하고 나직한 목소리로 말하세요"
    - "신나고 흥분된 목소리로 말하세요"
    """
    request_id = getattr(http_request.state, "request_id", str(uuid.uuid4())[:8])

    # VoiceDesign 모델 확인
    if not tts_engine.has_voice_design():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "VOICE_DESIGN_DISABLED",
                "message": "VoiceDesign model is not enabled",
                "request_id": request_id,
            },
        )

    # 텍스트 길이 검증
    if len(request.text) > settings.MAX_TEXT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": ErrorCode.TEXT_TOO_LONG,
                "message": f"Text exceeds maximum length of {settings.MAX_TEXT_LENGTH}",
                "request_id": request_id,
            },
        )

    try:
        # VoiceDesign 합성
        audio, sample_rate, processing_time = await tts_engine.synthesize_with_style(
            text=request.text,
            instruct=request.instruct,
            temperature=request.temperature,
            top_k=request.top_k,
            top_p=request.top_p,
        )

        duration = tts_engine.get_audio_duration(audio, sample_rate)

        logger.info(
            f"[{request_id}] VoiceDesign synthesized: "
            f"instruct='{request.instruct[:30]}...', "
            f"text_len={len(request.text)}, "
            f"duration={duration:.2f}s, "
            f"time={processing_time:.0f}ms"
        )

        headers = {
            "X-Audio-Duration": str(round(duration, 3)),
            "X-Processing-Time": str(int(processing_time)),
            "X-Sample-Rate": str(sample_rate),
            "X-Request-ID": request_id,
        }

        if request.format == "wav":
            buffer = io.BytesIO()
            sf.write(buffer, audio, sample_rate, format="WAV")
            buffer.seek(0)

            return StreamingResponse(
                buffer,
                media_type="audio/wav",
                headers=headers,
            )
        else:
            audio_int16 = (audio * 32767).astype("int16")
            buffer = io.BytesIO(audio_int16.tobytes())

            return StreamingResponse(
                buffer,
                media_type="audio/pcm",
                headers=headers,
            )

    except Exception as e:
        logger.error(f"[{request_id}] VoiceDesign error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": ErrorCode.MODEL_ERROR,
                "message": "VoiceDesign synthesis failed",
                "detail": str(e),
                "request_id": request_id,
            },
        )


@router.post(
    "/synthesize/hybrid",
    summary="하이브리드 합성 (GD 목소리 + 스타일 제어)",
    description="""
    VoiceDesign + Base 모델을 결합하여 GD 목소리 특성을 유지하면서
    감정/억양을 제어합니다.

    워크플로우:
    1. VoiceDesign으로 스타일이 적용된 레퍼런스 오디오 생성
    2. Base 모델로 GD 목소리 특성을 유지하며 최종 합성

    실시간 대화에 적합한 저지연(~200ms) 합성을 지원합니다.
    """,
    responses={
        200: {
            "content": {"audio/wav": {}},
            "description": "합성된 오디오 파일",
        },
        400: {"description": "잘못된 요청"},
        503: {"description": "VoiceDesign 모델 비활성화"},
    },
)
async def synthesize_hybrid(
    request: HybridSynthesizeRequest,
    http_request: Request,
    api_key: str = Depends(verify_api_key),
    _rate_limit: None = Depends(check_rate_limit_synthesize),
):
    """
    하이브리드 합성: GD 목소리 + 감정/스타일 제어

    instruct 예시:
    - "밝고 활기찬 목소리로"
    - "웃으면서 유쾌하게"
    - "GD처럼 자신감 있고 쿨하게"
    - "신나고 흥분된 목소리로"
    - "차분하고 나직하게"
    """
    request_id = getattr(http_request.state, "request_id", str(uuid.uuid4())[:8])

    # VoiceDesign 모델 확인
    if not tts_engine.has_voice_design():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "VOICE_DESIGN_DISABLED",
                "message": "VoiceDesign model is not enabled. Set ENABLE_VOICE_DESIGN=true",
                "request_id": request_id,
            },
        )

    # 텍스트 길이 검증
    if len(request.text) > settings.MAX_TEXT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": ErrorCode.TEXT_TOO_LONG,
                "message": f"Text exceeds maximum length of {settings.MAX_TEXT_LENGTH}",
                "request_id": request_id,
            },
        )

    try:
        # 하이브리드 합성
        audio, sample_rate, processing_time = await tts_engine.synthesize_hybrid(
            text=request.text,
            instruct=request.instruct,
            mode=request.mode.value,  # ModelMode enum → str
        )

        duration = tts_engine.get_audio_duration(audio, sample_rate)

        logger.info(
            f"[{request_id}] Hybrid synthesized: "
            f"instruct='{request.instruct[:20]}...', "
            f"text_len={len(request.text)}, "
            f"duration={duration:.2f}s, "
            f"time={processing_time:.0f}ms"
        )

        headers = {
            "X-Audio-Duration": str(round(duration, 3)),
            "X-Processing-Time": str(int(processing_time)),
            "X-Sample-Rate": str(sample_rate),
            "X-Model-Mode": request.mode.value,
            "X-Synthesis-Mode": "hybrid",
            "X-Request-ID": request_id,
        }

        if request.format == "wav":
            buffer = io.BytesIO()
            sf.write(buffer, audio, sample_rate, format="WAV")
            buffer.seek(0)

            return StreamingResponse(
                buffer,
                media_type="audio/wav",
                headers=headers,
            )
        else:
            audio_int16 = (audio * 32767).astype("int16")
            buffer = io.BytesIO(audio_int16.tobytes())

            return StreamingResponse(
                buffer,
                media_type="audio/pcm",
                headers=headers,
            )

    except Exception as e:
        logger.error(f"[{request_id}] Hybrid synthesis error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": ErrorCode.MODEL_ERROR,
                "message": "Hybrid synthesis failed",
                "detail": str(e),
                "request_id": request_id,
            },
        )
