"""
GD Voice Clone TTS Server - Main Entry Point
FastAPI + lifespan 패턴
"""

import sys
import os
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# 모듈 경로 추가
sys.path.insert(0, os.path.dirname(__file__))

from core.middleware import (
    RequestIDMiddleware,
    LoggingMiddleware,
    SecurityHeadersMiddleware,
)

from config import settings
from services.model_manager import model_manager
from services.voice_manager import voice_manager
from services.tts_engine import tts_engine
from api.routes import health, voices, tts
from api.websocket import stream as ws_stream
from api.websocket import voice_call as ws_voice_call
from core.connection import connection_manager
from services.stt_engine import get_stt_engine

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    FastAPI 0.95+ 권장 패턴 (on_event deprecated 대체)
    """
    # === STARTUP ===
    logger.info("=" * 60)
    logger.info("Starting GD Voice Clone TTS Server...")
    logger.info("=" * 60)

    try:
        # 1. Fine-tuned 모델 로딩 (GD v5 - best quality)
        if settings.ENABLE_FINETUNED:
            logger.info("[1/6] Loading Fine-tuned GD v5 model...")
            await model_manager.load_model(
                model_name=settings.FINETUNED_MODEL_PATH,
                device=settings.DEVICE,
                dtype=settings.DTYPE,
                attn_impl=settings.ATTN_IMPL,
                model_key="finetuned",
                model_type="finetuned",
            )

        # 2. Base 모델 로딩 (Voice Clone 모드)
        if settings.ENABLE_CLONE:
            logger.info("[2/6] Loading Base model (voice clone)...")
            await model_manager.load_model(
                model_name=settings.BASE_MODEL_NAME,
                device=settings.DEVICE,
                dtype=settings.DTYPE,
                attn_impl=settings.ATTN_IMPL,
                model_key="clone",
                model_type="clone",
            )

        # 2.5. VoiceDesign 모델 로딩 (감정/스타일 제어용)
        if settings.ENABLE_VOICE_DESIGN:
            logger.info("[2.5/6] Loading VoiceDesign model (prosody control)...")
            await model_manager.load_model(
                model_name=settings.VOICE_DESIGN_MODEL,
                device=settings.DEVICE,
                dtype=settings.DTYPE,
                attn_impl=settings.ATTN_IMPL,
                model_key="voice_design",
                model_type="voice_design",
            )

        # 3. 음성 프로필 등록
        logger.info("[3/6] Registering voice profiles...")

        # Voice Clone 모드용 프로필 등록 (ref_audio 기반)
        gd_ref_text = "네. 네. 또 미체라는 철학과의 사상 중에 가장 대표 되는 개념인데. 신은 동안 저를 좀."

        voice_manager.register_voice(
            voice_id="gd-default",
            name="G-Dragon (X-Vector)",
            mode="x_vector",
            description="X-Vector 모드 (빠름, 런타임 클로닝)",
            sample_path=settings.GD_SAMPLE_PATH,
        )
        voice_manager.register_voice(
            voice_id="gd-icl",
            name="G-Dragon (ICL)",
            mode="icl",
            description="ICL 모드 (높은 품질, ref_text 사용)",
            sample_path=settings.GD_SAMPLE_PATH,
            ref_text=gd_ref_text,
        )

        # 4. Voice Clone 모델용 프롬프트 캐싱
        if settings.ENABLE_CLONE:
            logger.info("[4/6] Caching voice prompts for clone mode...")
            clone_model = model_manager.get_model("clone")
            for voice_id in ["gd-default", "gd-icl"]:
                await voice_manager.cache_prompt(
                    voice_id=voice_id,
                    model=clone_model,
                    prompts_dir=settings.VOICE_PROMPTS_DIR,
                )
        else:
            logger.info("[4/6] Skipping voice prompt caching (clone mode disabled)")

        # 4. STT 모델 로딩 (Voice Call 기능 활성화 시)
        if settings.VOICE_CALL_ENABLED:
            try:
                logger.info("[4/6] Loading STT model for voice call...")
                stt_engine = get_stt_engine()
                await stt_engine.load_model()
            except (ImportError, ModuleNotFoundError) as e:
                logger.warning(f"[4/6] STT model not available: {e}")
                logger.warning("Voice call feature will be disabled. Install: pip install faster-whisper")
                # frozen pydantic model 우회
                object.__setattr__(settings, 'VOICE_CALL_ENABLED', False)
            except Exception as e:
                logger.error(f"[4/6] STT model loading failed: {e}")
                object.__setattr__(settings, 'VOICE_CALL_ENABLED', False)
        else:
            logger.info("[4/6] Skipping STT model (voice call disabled)")

        # 5. 모델 워밍업
        if settings.WARMUP_ON_START:
            logger.info("[5/6] Warming up TTS engine...")
            await tts_engine.warmup()
        else:
            logger.info("[5/6] Skipping warmup (disabled)")

        # 6. 로드된 모델 요약
        logger.info("[6/6] Models loaded:")
        for model_key in model_manager.list_models():
            logger.info(f"  - {model_key}")
        if settings.VOICE_CALL_ENABLED:
            logger.info(f"  - STT ({settings.STT_MODEL_SIZE})")

        # 7. WebSocket Heartbeat 시작 (연결 유지)
        logger.info("[7/7] Starting WebSocket heartbeat...")
        await connection_manager.start_heartbeat()

        logger.info("=" * 60)
        logger.info(f"TTS Server ready! http://{settings.HOST}:{settings.PORT}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise

    yield  # 서버 실행

    # === SHUTDOWN ===
    logger.info("=" * 60)
    logger.info("Shutting down TTS Server...")
    logger.info("=" * 60)

    # 1. WebSocket 연결 종료
    await connection_manager.close_all()

    # 2. STT 모델 언로드
    if settings.VOICE_CALL_ENABLED:
        stt_engine = get_stt_engine()
        await stt_engine.unload_model()

    # 3. GPU 메모리 해제
    await model_manager.unload_model()

    logger.info("TTS Server shutdown complete.")


# FastAPI 앱 생성
app = FastAPI(
    title="GD Voice Clone TTS Server",
    description="G-Dragon 음성 복제 기반 실시간 TTS 서버",
    version="1.0.0",
    lifespan=lifespan,
)

# === 미들웨어 (역순으로 등록: 마지막 등록 = 먼저 실행) ===

# 4. Security Headers (마지막 실행)
app.add_middleware(SecurityHeadersMiddleware)

# 3. Logging (Request ID 필요)
app.add_middleware(LoggingMiddleware)

# 2. Request ID (가장 먼저 실행되어야 함)
app.add_middleware(RequestIDMiddleware)

# 1. CORS (최외곽)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-Process-Time", "X-Audio-Duration"],
)


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리"""
    import uuid

    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    logger.error(f"[{request_id}] Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "request_id": request_id,
        },
    )


# 라우터 등록
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(voices.router, prefix="/api/v1/tts", tags=["TTS"])
app.include_router(tts.router, prefix="/api/v1/tts", tags=["TTS"])

# WebSocket 라우터 등록
app.include_router(ws_stream.router, tags=["WebSocket"])
app.include_router(ws_voice_call.router, tags=["Voice Call"])


@app.get("/", include_in_schema=False)
async def root():
    """루트 리다이렉트"""
    return {"message": "GD Voice Clone TTS Server", "docs": "/docs", "voice_call": "/voice-call"}


@app.get("/voice-call", include_in_schema=False)
async def voice_call_ui():
    """실시간 음성통화 UI"""
    static_path = os.path.join(os.path.dirname(__file__), "static", "voice_call.html")
    return FileResponse(static_path, media_type="text/html")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
