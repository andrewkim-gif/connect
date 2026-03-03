"""
Character Registry - 멀티 캐릭터 관리 시스템
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# 페르소나 임포트
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data.personas.gd_persona import GD_SYSTEM_PROMPT, GD_GREETINGS
from data.personas.jhk_persona import JHK_SYSTEM_PROMPT, JHK_GREETINGS


@dataclass
class CharacterProfile:
    """캐릭터 프로필"""
    id: str
    name: str
    description: str
    avatar: str
    greeting_text: str  # 대표 인사말

    # 음성 모델
    voice_model_finetuned: Optional[str] = None
    voice_model_icl: Optional[str] = None
    sample_audio: Optional[str] = None
    ref_text: Optional[str] = None

    # LLM 페르소나
    system_prompt: str = ""
    greetings: List[str] = field(default_factory=list)

    # 상태
    status: str = "pending"  # ready, pending, disabled

    def get_voice_modes(self) -> List[str]:
        """사용 가능한 음성 모드 목록"""
        modes = []
        if self.voice_model_finetuned:
            modes.append("finetuned")
        if self.voice_model_icl:
            modes.append("icl")
        return modes

    def is_ready(self) -> bool:
        """캐릭터 사용 가능 여부"""
        return self.status == "ready" and len(self.get_voice_modes()) > 0

    def to_dict(self) -> Dict[str, Any]:
        """API 응답용 딕셔너리 변환"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "avatar": self.avatar,
            "greeting_text": self.greeting_text,
            "status": self.status,
            "voice_modes": self.get_voice_modes(),
        }


class CharacterRegistry:
    """캐릭터 레지스트리 - 싱글톤"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.characters: Dict[str, CharacterProfile] = {}
        self._initialized = True
        self._register_default_characters()

    def _register_default_characters(self):
        """기본 캐릭터 등록"""
        # G-Dragon
        self.register(CharacterProfile(
            id="gd",
            name="G-Dragon",
            description="빅뱅 리더, K-POP 아이콘",
            avatar="/static/avatars/gd.png",
            greeting_text="야~ 뭐야?",
            voice_model_finetuned="gd-voice-v5",
            voice_model_icl="gd-clone",
            sample_audio="/home/nexus/connect/server/sample/gd_sample_18s_v2.wav",
            ref_text="신선하다 하기보다 저한테 좀 충격이 있고 그런 일단 아무래도 그 지금 힙합도 물론 조금 많이 변화가 있지만 그때만 해도 굉장히 랩하면 갱스터 랩이 주된 주류의 힙합의 핵심 의미였기 때문에",
            system_prompt=GD_SYSTEM_PROMPT,
            greetings=GD_GREETINGS,
            status="ready",
        ))

        # 장현국 - NEXUS 대표
        self.register(CharacterProfile(
            id="jhk",
            name="장현국",
            description="NEXUS 대표, 블록체인 게임의 선구자",
            avatar="/static/avatars/jhk.png",
            greeting_text="네, 말씀하세요",
            voice_model_finetuned="jang-voice-v1",  # Fine-tuning 완료
            voice_model_icl="jang-clone",  # ICL 프롬프트 준비 완료
            sample_audio="/home/nexus/connect/server/sample/jang_sample_icl.wav",
            ref_text="하나가 TVL 이잖아요. Total Value Act. 작년 2024년 2월 기준으로 위믹스가 전세계 12등 이었어요. 5억불로. 솔라나가 5등 이었는데",
            system_prompt=JHK_SYSTEM_PROMPT,
            greetings=JHK_GREETINGS,
            status="ready",  # ICL 모드 사용 가능
        ))

        logger.info(f"Registered {len(self.characters)} characters: {list(self.characters.keys())}")

    def register(self, character: CharacterProfile) -> None:
        """캐릭터 등록"""
        self.characters[character.id] = character
        logger.info(f"Character registered: {character.id} ({character.name})")

    def get(self, character_id: str) -> Optional[CharacterProfile]:
        """캐릭터 조회"""
        return self.characters.get(character_id)

    def get_or_default(self, character_id: Optional[str] = None) -> CharacterProfile:
        """캐릭터 조회 (없으면 기본 캐릭터)"""
        if character_id and character_id in self.characters:
            return self.characters[character_id]
        # 기본값: gd
        return self.characters.get("gd", list(self.characters.values())[0])

    def list_all(self) -> List[CharacterProfile]:
        """모든 캐릭터 목록"""
        return list(self.characters.values())

    def list_ready(self) -> List[CharacterProfile]:
        """사용 가능한 캐릭터 목록"""
        return [c for c in self.characters.values() if c.is_ready()]

    def update_status(self, character_id: str, status: str) -> bool:
        """캐릭터 상태 업데이트"""
        if character_id not in self.characters:
            return False
        self.characters[character_id].status = status
        logger.info(f"Character {character_id} status updated: {status}")
        return True

    def update_voice_model(
        self,
        character_id: str,
        finetuned: Optional[str] = None,
        icl: Optional[str] = None,
        sample_audio: Optional[str] = None,
        ref_text: Optional[str] = None,
    ) -> bool:
        """캐릭터 음성 모델 업데이트"""
        if character_id not in self.characters:
            return False

        char = self.characters[character_id]
        if finetuned is not None:
            char.voice_model_finetuned = finetuned
        if icl is not None:
            char.voice_model_icl = icl
        if sample_audio is not None:
            char.sample_audio = sample_audio
        if ref_text is not None:
            char.ref_text = ref_text

        # 음성 모델이 하나라도 있으면 ready로 변경
        if char.get_voice_modes():
            char.status = "ready"

        logger.info(f"Character {character_id} voice model updated")
        return True


# 싱글톤 인스턴스
character_registry = CharacterRegistry()


def get_character_registry() -> CharacterRegistry:
    """레지스트리 인스턴스 반환"""
    return character_registry
