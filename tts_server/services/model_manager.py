"""
Model Manager - Davinci Voice 다중 모델 관리
Fine-tuned (GD v5) + Base (Voice Clone) + VoiceDesign (Prosody Control)
"""

import torch
import logging
import asyncio
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)


class ModelManager:
    """TTS 다중 모델 관리자

    Supports:
    - finetuned: GD v5 fine-tuned model (generate_custom_voice)
    - clone: Base model for voice cloning (generate_voice_clone)
    - voice_design: VoiceDesign model for prosody control
    """

    def __init__(self):
        # 다중 모델 지원
        self.models: Dict[str, Any] = {}
        self.model_types: Dict[str, str] = {}  # model_key -> "finetuned" | "clone" | "voice_design"
        self.sample_rate: int = 24000
        self._lock = asyncio.Lock()

    async def load_model(
        self,
        model_name: str,
        device: str = "cuda:0",
        dtype: str = "bfloat16",
        attn_impl: str = "flash_attention_2",
        model_key: str = "base",
        model_type: str = "clone",  # "finetuned", "clone", "voice_design"
    ) -> Any:
        """모델 로딩 (비동기 래퍼)

        Args:
            model_name: 모델 경로 또는 HuggingFace 모델명
            device: 디바이스 (cuda:0)
            dtype: 데이터 타입 (bfloat16)
            attn_impl: 어텐션 구현 (flash_attention_2)
            model_key: 모델 키 (finetuned, clone, voice_design)
            model_type: 모델 타입 (finetuned, clone, voice_design)
        """
        async with self._lock:
            if model_key in self.models:
                logger.info(f"Model '{model_key}' already loaded, skipping...")
                return self.models[model_key]

            logger.info(f"Loading model '{model_key}' ({model_type}): {model_name}")
            logger.info(f"  Device: {device}")
            logger.info(f"  Dtype: {dtype}")
            logger.info(f"  Attention: {attn_impl}")

            # 블로킹 작업을 스레드풀에서 실행
            loop = asyncio.get_event_loop()
            model = await loop.run_in_executor(
                None,
                self._load_model_sync,
                model_name,
                device,
                dtype,
                attn_impl,
                model_type,
            )

            self.models[model_key] = model
            self.model_types[model_key] = model_type

            # 메모리 사용량 로깅
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated(0) / 1024**3
                logger.info(f"Model '{model_key}' ({model_type}) loaded. Total GPU memory: {allocated:.2f} GB")

            return model

    def _load_model_sync(
        self,
        model_name: str,
        device: str,
        dtype: str,
        attn_impl: str,
        model_type: str = "clone",
    ) -> Any:
        """동기 모델 로딩 (실제 로딩 작업)"""
        dtype_map = {
            "bfloat16": torch.bfloat16,
            "float16": torch.float16,
            "float32": torch.float32,
        }

        if model_type == "finetuned":
            # Fine-tuned 모델은 직접 Qwen3TTSModel로 로드
            from qwen_tts import Qwen3TTSModel

            logger.info(f"Loading fine-tuned GD model from {model_name}")
            model = Qwen3TTSModel.from_pretrained(
                model_name,
                device_map=device,
                dtype=dtype_map.get(dtype, torch.bfloat16),
                attn_implementation=attn_impl,
            )
        else:
            # Base/VoiceDesign 모델은 DavinciVoiceModel 래퍼 사용
            from davinci_voice import DavinciVoiceModel

            logger.info(f"Loading {model_type} model from {model_name}")
            model = DavinciVoiceModel.from_pretrained(
                model_name,
                device_map=device,
                dtype=dtype_map.get(dtype, torch.bfloat16),
                attn_implementation=attn_impl,
            )

        return model

    def has_finetuned(self) -> bool:
        """Fine-tuned 모델 로드 여부"""
        return "finetuned" in self.models

    def has_clone(self) -> bool:
        """Clone 모델 로드 여부"""
        return "clone" in self.models

    def get_model_type(self, model_key: str) -> Optional[str]:
        """모델 타입 조회"""
        return self.model_types.get(model_key)

    async def unload_model(self, model_key: str = None) -> None:
        """모델 언로딩 및 GPU 메모리 해제"""
        async with self._lock:
            if model_key:
                # 특정 모델만 언로드
                if model_key in self.models:
                    logger.info(f"Unloading model '{model_key}'...")
                    del self.models[model_key]
            else:
                # 모든 모델 언로드
                logger.info("Unloading all models...")
                self.models.clear()

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()

            logger.info("Models unloaded, GPU memory released")

    def get_model(self, model_key: str = "base") -> Any:
        """로드된 모델 반환"""
        if model_key not in self.models:
            raise RuntimeError(f"Model '{model_key}' not loaded. Call load_model() first.")
        return self.models[model_key]

    def has_model(self, model_key: str) -> bool:
        """모델 로드 상태 확인"""
        return model_key in self.models

    def is_loaded(self) -> bool:
        """기본 모델 로드 상태 확인 (하위 호환성)"""
        return "base" in self.models

    def list_models(self) -> list[str]:
        """로드된 모델 목록"""
        return list(self.models.keys())

    def get_gpu_memory_gb(self) -> Optional[float]:
        """GPU 메모리 사용량 (GB)"""
        if torch.cuda.is_available():
            return torch.cuda.memory_allocated(0) / 1024**3
        return None


# 싱글톤 인스턴스
model_manager = ModelManager()
