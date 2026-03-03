"""
TTS Engine - 음성 합성 엔진
생성 파라미터 지원 (temperature, top_k, top_p 등)

Supports:
- Fine-tuned model (GD v5): generate_custom_voice()
- Base model: generate_voice_clone() with voice_clone_prompt
"""

import time
import logging
import asyncio
import numpy as np
from typing import Tuple, Optional, Any, Dict

from services.model_manager import model_manager
from services.voice_manager import voice_manager
from config import settings

logger = logging.getLogger(__name__)

# === Audio Tail Processing Constants ===
# 자연스러운 음성 끝 처리를 위한 설정
TAIL_SILENCE_MS = 150      # tail silence 길이 (ms)
FADE_OUT_MS = 50           # fade-out 길이 (ms)
ENABLE_TAIL_PROCESSING = True  # tail 처리 활성화


class TTSEngine:
    """TTS 합성 엔진"""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._warmup_done = False

    def _add_tail_silence(
        self,
        audio: np.ndarray,
        sample_rate: int,
        fade_out_ms: int = FADE_OUT_MS,
        silence_ms: int = TAIL_SILENCE_MS,
    ) -> np.ndarray:
        """
        오디오 끝에 자연스러운 fade-out + silence tail 추가

        문제: TTS 모델이 문장 끝에서 갑자기 끊김 ("했습니다" → "했습니다-끊김")
        해결: fade-out으로 자연스럽게 줄이고, silence로 여운 추가

        Args:
            audio: 원본 오디오 (float32, -1.0 ~ 1.0)
            sample_rate: 샘플레이트 (24000)
            fade_out_ms: fade-out 길이 (기본 50ms)
            silence_ms: tail silence 길이 (기본 150ms)

        Returns:
            tail이 추가된 오디오 (float32)
        """
        if not ENABLE_TAIL_PROCESSING:
            return audio

        # Fade-out 적용 (자연스러운 볼륨 감소)
        fade_samples = int(sample_rate * fade_out_ms / 1000)
        if len(audio) > fade_samples:
            # 선형 fade-out: 1.0 → 0.0
            fade_curve = np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)
            audio = audio.copy()  # 원본 보호
            audio[-fade_samples:] = audio[-fade_samples:] * fade_curve

        # Silence tail 추가 (여운)
        silence_samples = int(sample_rate * silence_ms / 1000)
        silence = np.zeros(silence_samples, dtype=np.float32)

        result = np.concatenate([audio, silence])

        logger.debug(
            f"Tail added: fade={fade_out_ms}ms, silence={silence_ms}ms, "
            f"original={len(audio)/sample_rate:.2f}s → final={len(result)/sample_rate:.2f}s"
        )

        return result

    async def warmup(self) -> None:
        """모델 워밍업 (CUDA 커널 컴파일)"""
        if self._warmup_done:
            return

        logger.info("Warming up TTS engine...")

        try:
            # 짧은 텍스트로 워밍업
            await self.synthesize(text="워밍업")
            self._warmup_done = True
            logger.info("TTS engine warmup complete")
        except Exception as e:
            logger.warning(f"Warmup failed: {e}")

    def _resolve_mode(self, mode: str) -> str:
        """모드 해석: auto → 실제 모드로 변환"""
        if mode == "auto":
            # Fine-tuned 우선, 없으면 clone
            if model_manager.has_finetuned():
                return "finetuned"
            elif model_manager.has_clone():
                return "clone"
            else:
                raise RuntimeError("No TTS model available")
        return mode

    async def synthesize(
        self,
        text: str,
        mode: str = "auto",  # "finetuned", "clone", "auto"
        character_id: str = "gd",  # 캐릭터 ID (gd, jhk 등)
        voice_mode: str = "icl",  # finetuned 또는 icl
    ) -> Tuple[np.ndarray, int, float]:
        """
        텍스트 → 음성 합성

        Args:
            text: 합성할 텍스트
            mode: 모델 모드
                - finetuned: GD v5 학습 모델 (권장)
                - clone: ICL 방식 실시간 음성 복제
                - auto: finetuned 우선
            character_id: 캐릭터 ID (gd, jhk 등)
            voice_mode: 음성 모드 (finetuned, icl)

        Returns:
            (audio_array, sample_rate, processing_time_ms)
        """
        start_time = time.time()

        # voice_mode에 따라 mode 결정
        if voice_mode == "finetuned":
            resolved_mode = "finetuned"
        elif voice_mode == "icl":
            resolved_mode = "clone"
        else:
            # 기존 로직 유지
            resolved_mode = self._resolve_mode(mode)

        # 모델 선택
        if resolved_mode == "finetuned":
            if not model_manager.has_finetuned():
                raise RuntimeError("Fine-tuned model not loaded. Set ENABLE_FINETUNED=true")
            model = model_manager.get_model("finetuned")
        else:
            if not model_manager.has_clone():
                raise RuntimeError("Clone model not loaded. Set ENABLE_CLONE=true")
            model = model_manager.get_model("clone")

        # 생성 파라미터 (config 기본값 사용)
        gen_params = {
            "do_sample": settings.GEN_DO_SAMPLE,
            "top_k": settings.GEN_TOP_K,
            "top_p": settings.GEN_TOP_P,
            "temperature": settings.GEN_TEMPERATURE,
            "repetition_penalty": settings.GEN_REPETITION_PENALTY,
            "language": settings.GEN_LANGUAGE,
        }

        logger.debug(f"Synthesis mode={resolved_mode}, character={character_id}, voice_mode={voice_mode}")

        # GPU 동시 접근 제한을 위해 lock 사용
        async with self._lock:
            loop = asyncio.get_event_loop()

            if resolved_mode == "finetuned":
                # Fine-tuned 모델: generate_custom_voice() 사용
                result = await loop.run_in_executor(
                    None,
                    self._synthesize_finetuned_sync,
                    model,
                    text,
                    gen_params,
                )
            else:
                # Clone 모델: ICL 방식으로 generate_voice_clone() 사용
                # 캐릭터별 voice prompt 선택
                # character_id -> voice_model_icl 매핑 (character_registry 사용)
                from services.character_registry import get_character_registry
                registry = get_character_registry()
                character = registry.get(character_id)

                if character and character.voice_model_icl:
                    voice_prompt_id = character.voice_model_icl
                else:
                    # 기본값: gd-clone
                    voice_prompt_id = "gd-clone"
                    logger.warning(f"No ICL voice model for character '{character_id}', using 'gd-clone'")

                try:
                    voice_prompt = voice_manager.get_prompt(voice_prompt_id)
                    logger.info(f"Using voice prompt: {voice_prompt_id}")
                except (KeyError, RuntimeError) as e:
                    logger.error(f"Voice prompt '{voice_prompt_id}' not available: {e}")
                    # gd-clone으로 폴백
                    voice_prompt = voice_manager.get_prompt("gd-clone")
                    logger.warning(f"Falling back to 'gd-clone'")

                result = await loop.run_in_executor(
                    None,
                    self._synthesize_voice_clone_sync,
                    model,
                    text,
                    voice_prompt,
                    gen_params,
                )

        audio, sample_rate = result

        # 🔧 FIX: 자연스러운 음성 끝 처리 (tail silence 추가)
        # 문제: TTS가 문장 끝에서 "툭" 끊김
        # 해결: fade-out + silence tail로 자연스러운 여운 추가
        audio = self._add_tail_silence(audio, sample_rate)

        processing_time = (time.time() - start_time) * 1000

        logger.info(
            f"Synthesized ({resolved_mode}): {len(text)} chars → "
            f"{len(audio)/sample_rate:.2f}s audio "
            f"({processing_time:.0f}ms)"
        )

        return audio, sample_rate, processing_time

    def _synthesize_finetuned_sync(
        self,
        model: Any,
        text: str,
        gen_params: Dict[str, Any],
    ) -> Tuple[np.ndarray, int]:
        """동기 합성 - Fine-tuned 모델 (GD v5)"""
        result = model.generate_custom_voice(
            text=text,
            speaker=settings.FINETUNED_SPEAKER,  # "gd"
            language=gen_params.get("language", "Korean"),
        )

        audio_list, sample_rate = result
        audio = audio_list[0]

        if isinstance(audio, np.ndarray):
            return audio, sample_rate

        return np.array(audio), sample_rate

    def _synthesize_voice_clone_sync(
        self,
        model: Any,
        text: str,
        voice_prompt: Any,
        gen_params: Dict[str, Any],
    ) -> Tuple[np.ndarray, int]:
        """동기 합성 - Voice Clone 모드 (Base 모델)"""
        result = model.generate_voice_clone(
            text=text,
            voice_clone_prompt=voice_prompt,
            language=gen_params.get("language"),
            do_sample=gen_params.get("do_sample", True),
            top_k=gen_params.get("top_k", 50),
            top_p=gen_params.get("top_p", 0.9),
            temperature=gen_params.get("temperature", 0.7),
            repetition_penalty=gen_params.get("repetition_penalty", 1.1),
        )

        audio_list, sample_rate = result
        audio = audio_list[0]

        if isinstance(audio, np.ndarray):
            return audio, sample_rate

        return np.array(audio), sample_rate

    def get_audio_duration(self, audio: np.ndarray, sample_rate: int) -> float:
        """오디오 길이 (초)"""
        return len(audio) / sample_rate

    async def synthesize_with_style(
        self,
        text: str,
        instruct: str,
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
    ) -> Tuple[np.ndarray, int, float]:
        """
        VoiceDesign 모델로 스타일/감정 제어 합성

        Args:
            text: 합성할 텍스트
            instruct: 자연어 스타일 지시 (예: "밝고 활기찬 목소리로", "웃으면서 말하는 듯한")
            temperature: 샘플링 온도
            top_k: top-k 샘플링
            top_p: nucleus 샘플링

        Returns:
            (audio_array, sample_rate, processing_time_ms)
        """
        if not model_manager.has_model("voice_design"):
            raise RuntimeError("VoiceDesign model not loaded. Enable ENABLE_VOICE_DESIGN in config.")

        async with self._lock:
            start_time = time.time()

            model = model_manager.get_model("voice_design")

            gen_params = {
                "do_sample": settings.GEN_DO_SAMPLE,
                "top_k": top_k if top_k is not None else settings.GEN_TOP_K,
                "top_p": top_p if top_p is not None else settings.GEN_TOP_P,
                "temperature": temperature if temperature is not None else settings.GEN_TEMPERATURE,
                "language": settings.GEN_LANGUAGE,
            }

            logger.debug(f"VoiceDesign params: instruct='{instruct[:50]}...', {gen_params}")

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._synthesize_voice_design_sync,
                model,
                text,
                instruct,
                gen_params,
            )

            audio, sample_rate = result
            processing_time = (time.time() - start_time) * 1000

            logger.info(
                f"VoiceDesign synthesized: {len(text)} chars → "
                f"{len(audio)/sample_rate:.2f}s audio "
                f"({processing_time:.0f}ms)"
            )

            return audio, sample_rate, processing_time

    def _synthesize_voice_design_sync(
        self,
        model: Any,
        text: str,
        instruct: str,
        gen_params: Dict[str, Any],
    ) -> Tuple[np.ndarray, int]:
        """동기 VoiceDesign 합성"""
        result = model.generate_voice_design(
            text=text,
            instruct=instruct,
            language=gen_params.get("language", "Korean"),
            do_sample=gen_params.get("do_sample", True),
            top_k=gen_params.get("top_k", 50),
            top_p=gen_params.get("top_p", 0.9),
            temperature=gen_params.get("temperature", 0.7),
        )

        audio_list, sample_rate = result
        audio = audio_list[0]

        if isinstance(audio, np.ndarray):
            return audio, sample_rate

        return np.array(audio), sample_rate

    def has_voice_design(self) -> bool:
        """VoiceDesign 모델 사용 가능 여부"""
        return model_manager.has_model("voice_design")

    async def synthesize_hybrid(
        self,
        text: str,
        instruct: str,
        mode: str = "auto",  # "finetuned", "clone", "auto"
    ) -> Tuple[np.ndarray, int, float]:
        """
        하이브리드 합성: GD 목소리 + 감정/스타일 제어

        Fine-tuned 모델: instruct를 텍스트에 포함하여 합성
        Clone 모델: ICL 방식으로 음성 복제 + 감정 적용

        Args:
            text: 합성할 텍스트
            instruct: 감정/스타일 지시 (예: "웃으면서 밝게")
            mode: 모델 모드 (finetuned, clone, auto)

        Returns:
            (audio_array, sample_rate, processing_time_ms)
        """
        async with self._lock:
            start_time = time.time()

            # 모드 결정
            resolved_mode = self._resolve_mode(mode)

            # 모델 선택
            if resolved_mode == "finetuned":
                if not model_manager.has_finetuned():
                    raise RuntimeError("Fine-tuned model not loaded")
                model = model_manager.get_model("finetuned")
            else:
                if not model_manager.has_clone():
                    raise RuntimeError("Clone model not loaded")
                model = model_manager.get_model("clone")

            gen_params = {
                "do_sample": settings.GEN_DO_SAMPLE,
                "top_k": settings.GEN_TOP_K,
                "top_p": settings.GEN_TOP_P,
                "temperature": settings.GEN_TEMPERATURE,
                "language": settings.GEN_LANGUAGE,
            }

            logger.info(f"Hybrid synthesis: instruct='{instruct[:30]}...', text='{text[:30]}...', mode={resolved_mode}")

            loop = asyncio.get_event_loop()

            if resolved_mode == "finetuned":
                # Fine-tuned 모델: instruct를 텍스트에 포함
                result = await loop.run_in_executor(
                    None,
                    self._synthesize_hybrid_finetuned_sync,
                    model,
                    text,
                    instruct,
                    gen_params,
                )
            else:
                # Clone 모델: ICL 방식으로 voice clone prompt 사용
                gd_voice_prompt = voice_manager.get_prompt("gd-clone")

                result = await loop.run_in_executor(
                    None,
                    self._synthesize_hybrid_voice_clone_sync,
                    model,
                    text,
                    instruct,
                    gen_params,
                    gd_voice_prompt,
                )

            audio, sample_rate = result
            processing_time = (time.time() - start_time) * 1000

            logger.info(
                f"Hybrid synthesized ({resolved_mode}): {len(text)} chars → "
                f"{len(audio)/sample_rate:.2f}s audio "
                f"({processing_time:.0f}ms)"
            )

            return audio, sample_rate, processing_time

    def _synthesize_hybrid_finetuned_sync(
        self,
        model: Any,
        text: str,
        instruct: str,
        gen_params: Dict[str, Any],
    ) -> Tuple[np.ndarray, int]:
        """동기 하이브리드 합성 - Fine-tuned 모델"""
        language = gen_params.get("language", "Korean")

        # 감정 힌트를 텍스트 앞에 추가
        emotion_text = f"[{instruct}] {text}"

        logger.debug(f"Hybrid (finetuned): emotion_text='{emotion_text[:50]}...'")

        wavs, sample_rate = model.generate_custom_voice(
            text=emotion_text,
            speaker=settings.FINETUNED_SPEAKER,
            language=language,
        )

        audio = wavs[0]
        if isinstance(audio, np.ndarray):
            return audio, sample_rate

        return np.array(audio), sample_rate

    def _synthesize_hybrid_voice_clone_sync(
        self,
        model: Any,
        text: str,
        instruct: str,
        gen_params: Dict[str, Any],
        gd_voice_prompt: Any,
    ) -> Tuple[np.ndarray, int]:
        """동기 하이브리드 합성 - Voice Clone 모드"""
        language = gen_params.get("language", "Korean")

        # 감정 힌트를 텍스트 앞에 추가
        emotion_text = f"[{instruct}] {text}"

        logger.debug(f"Hybrid (voice_clone): emotion_text='{emotion_text[:50]}...'")

        wavs, sample_rate = model.generate_voice_clone(
            text=emotion_text,
            language=language,
            voice_clone_prompt=gd_voice_prompt,
            do_sample=gen_params.get("do_sample", True),
            top_k=gen_params.get("top_k", 50),
            top_p=gen_params.get("top_p", 0.9),
            temperature=gen_params.get("temperature", 0.7),
        )

        audio = wavs[0]
        if isinstance(audio, np.ndarray):
            return audio, sample_rate

        return np.array(audio), sample_rate


# 싱글톤 인스턴스
tts_engine = TTSEngine()
