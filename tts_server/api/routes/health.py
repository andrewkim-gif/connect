"""
Health Check Endpoint
GET /api/v1/health
"""

import torch
from fastapi import APIRouter

from models.response import HealthResponse
from services.model_manager import model_manager
from services.voice_manager import voice_manager

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="서버 상태 확인",
    description="서버 및 모델 상태를 확인합니다.",
)
async def health_check() -> HealthResponse:
    """서버 상태 확인"""
    return HealthResponse(
        status="healthy" if model_manager.is_loaded() else "degraded",
        model_loaded=model_manager.is_loaded(),
        gpu_available=torch.cuda.is_available(),
        gpu_memory_used_gb=model_manager.get_gpu_memory_gb(),
        voices_cached=voice_manager.cached_count(),
    )
