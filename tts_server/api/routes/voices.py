"""
Voices Endpoint
GET /api/v1/tts/voices
"""

from fastapi import APIRouter, Depends

from models.response import VoicesResponse, VoiceInfo
from services.voice_manager import voice_manager
from api.deps import verify_api_key

router = APIRouter()


@router.get(
    "/voices",
    response_model=VoicesResponse,
    summary="음성 목록 조회",
    description="사용 가능한 음성 목록을 반환합니다.",
)
async def list_voices(
    _: str = Depends(verify_api_key),
) -> VoicesResponse:
    """사용 가능한 음성 목록"""
    voices = voice_manager.list_voices()

    return VoicesResponse(
        voices=[
            VoiceInfo(
                id=v.id,
                name=v.name,
                mode=v.mode,
                description=v.description,
            )
            for v in voices
        ]
    )
