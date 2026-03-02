"""
Voice Manager - 음성 프롬프트 캐싱 및 관리
"""

import os
import pickle
import logging
import asyncio
from typing import Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class VoiceProfile:
    """음성 프로필"""

    id: str
    name: str
    mode: str  # "x_vector" or "icl"
    description: str
    sample_path: str
    ref_text: Optional[str] = None
    prompt: Optional[Any] = None  # 캐시된 voice_clone_prompt


class VoiceManager:
    """음성 프로필 및 프롬프트 관리자"""

    def __init__(self):
        self.voices: Dict[str, VoiceProfile] = {}
        self._lock = asyncio.Lock()

    def register_voice(
        self,
        voice_id: str,
        name: str,
        mode: str,
        description: str,
        sample_path: str,
        ref_text: Optional[str] = None,
    ) -> None:
        """음성 프로필 등록"""
        self.voices[voice_id] = VoiceProfile(
            id=voice_id,
            name=name,
            mode=mode,
            description=description,
            sample_path=sample_path,
            ref_text=ref_text,
        )
        logger.info(f"Registered voice: {voice_id} ({mode} mode)")

    async def cache_prompt(
        self,
        voice_id: str,
        model: Any,
        prompts_dir: str,
    ) -> None:
        """음성 프롬프트 사전 계산 및 캐싱"""
        if voice_id not in self.voices:
            raise KeyError(f"Voice not found: {voice_id}")

        voice = self.voices[voice_id]
        cache_path = os.path.join(prompts_dir, f"{voice_id}.pkl")

        # 캐시 파일이 있으면 로드
        if os.path.exists(cache_path):
            logger.info(f"Loading cached prompt for {voice_id}")
            with open(cache_path, "rb") as f:
                voice.prompt = pickle.load(f)
            return

        # 새로 생성
        logger.info(f"Creating voice prompt for {voice_id}...")

        loop = asyncio.get_event_loop()
        prompt = await loop.run_in_executor(
            None,
            self._create_prompt_sync,
            model,
            voice,
        )

        voice.prompt = prompt

        # 캐시 저장
        os.makedirs(prompts_dir, exist_ok=True)
        with open(cache_path, "wb") as f:
            pickle.dump(prompt, f)

        logger.info(f"Cached voice prompt: {cache_path}")

    def _create_prompt_sync(self, model: Any, voice: VoiceProfile) -> Any:
        """동기 프롬프트 생성"""
        x_vector_only = voice.mode == "x_vector"

        prompt = model.create_voice_clone_prompt(
            ref_audio=voice.sample_path,
            ref_text=voice.ref_text if not x_vector_only else None,
            x_vector_only_mode=x_vector_only,
        )

        return prompt

    def get_voice(self, voice_id: str) -> VoiceProfile:
        """음성 프로필 조회"""
        if voice_id not in self.voices:
            raise KeyError(f"Voice not found: {voice_id}")
        return self.voices[voice_id]

    def get_prompt(self, voice_id: str) -> Any:
        """캐시된 프롬프트 조회"""
        voice = self.get_voice(voice_id)
        if voice.prompt is None:
            raise RuntimeError(f"Prompt not cached for voice: {voice_id}")
        return voice.prompt

    def list_voices(self) -> list[VoiceProfile]:
        """등록된 모든 음성 목록"""
        return list(self.voices.values())

    def has_voice(self, voice_id: str) -> bool:
        """음성 존재 여부"""
        return voice_id in self.voices

    def cached_count(self) -> int:
        """캐시된 프롬프트 수"""
        return sum(1 for v in self.voices.values() if v.prompt is not None)


# 싱글톤 인스턴스
voice_manager = VoiceManager()
