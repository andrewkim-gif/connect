"""
Characters API - 캐릭터 목록 및 상세 정보
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from services.character_registry import get_character_registry

router = APIRouter()


@router.get("/characters")
async def list_characters() -> Dict[str, Any]:
    """
    캐릭터 목록 조회

    Returns:
        characters: 모든 캐릭터 목록
        ready_count: 사용 가능한 캐릭터 수
    """
    registry = get_character_registry()
    all_chars = registry.list_all()

    return {
        "characters": [c.to_dict() for c in all_chars],
        "ready_count": len(registry.list_ready()),
        "total_count": len(all_chars),
    }


@router.get("/characters/{character_id}")
async def get_character(character_id: str) -> Dict[str, Any]:
    """
    특정 캐릭터 상세 정보

    Args:
        character_id: 캐릭터 ID (gd, jhk 등)

    Returns:
        캐릭터 상세 정보
    """
    registry = get_character_registry()
    character = registry.get(character_id)

    if not character:
        raise HTTPException(
            status_code=404,
            detail=f"Character not found: {character_id}"
        )

    return {
        "character": character.to_dict(),
        "greetings_count": len(character.greetings),
        "has_system_prompt": bool(character.system_prompt),
    }


@router.get("/characters/{character_id}/greetings")
async def get_character_greetings(character_id: str) -> Dict[str, Any]:
    """
    캐릭터 인사말 목록

    Args:
        character_id: 캐릭터 ID

    Returns:
        인사말 목록
    """
    registry = get_character_registry()
    character = registry.get(character_id)

    if not character:
        raise HTTPException(
            status_code=404,
            detail=f"Character not found: {character_id}"
        )

    return {
        "character_id": character_id,
        "greetings": character.greetings,
    }
