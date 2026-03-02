"""
STT Engine - Speech-to-Text 엔진 (faster-whisper 기반)
실시간 음성통화를 위한 음성 인식
"""

import logging
import asyncio
import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """전사 결과"""
    text: str
    language: str
    confidence: float
    duration: float  # 오디오 길이 (초)


class STTEngine:
    """Speech-to-Text 엔진 (faster-whisper 기반)"""

    def __init__(
        self,
        model_size: str = "large-v3",
        device: str = "cuda",
        compute_type: str = "float16",
        language: str = "ko",
        beam_size: int = 5,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.beam_size = beam_size
        self.model = None
        self._lock = asyncio.Lock()

    async def load_model(self) -> None:
        """모델 로딩 (startup 시 호출)"""
        if self.model is not None:
            logger.warning("STT model already loaded")
            return

        logger.info(f"Loading STT model: {self.model_size} on {self.device}")

        loop = asyncio.get_event_loop()
        try:
            self.model = await loop.run_in_executor(None, self._load_model_sync)
        except (ImportError, ModuleNotFoundError) as e:
            # 예외를 상위로 전파하여 main.py에서 처리
            raise ImportError(str(e)) from e

        logger.info(f"STT model loaded: {self.model_size}")

    def _load_model_sync(self):
        """동기 모델 로딩"""
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise ImportError(
                "faster-whisper 패키지가 필요합니다: pip install faster-whisper"
            )

        return WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
        )

    async def unload_model(self) -> None:
        """모델 언로드"""
        if self.model is not None:
            del self.model
            self.model = None
            logger.info("STT model unloaded")

    def is_loaded(self) -> bool:
        """모델 로딩 여부"""
        return self.model is not None

    async def transcribe(
        self,
        audio: np.ndarray,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        오디오 → 텍스트 변환

        Args:
            audio: PCM 오디오 데이터 (16kHz, mono, float32, -1.0 ~ 1.0)
            language: 언어 코드 (None이면 자동 감지)

        Returns:
            TranscriptionResult
        """
        if self.model is None:
            raise RuntimeError("STT model not loaded. Call load_model() first.")

        async with self._lock:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._transcribe_sync,
                audio,
                language or self.language,
            )
            return result

    def _transcribe_sync(
        self,
        audio: np.ndarray,
        language: str,
    ) -> TranscriptionResult:
        """동기 전사"""
        import time
        start_time = time.time()

        # faster-whisper는 float32 [-1, 1] 범위의 numpy array를 기대
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # 정규화 (혹시 범위 벗어난 경우)
        if np.abs(audio).max() > 1.0:
            audio = audio / np.abs(audio).max()

        segments, info = self.model.transcribe(
            audio,
            language=language,
            beam_size=self.beam_size,
            vad_filter=True,  # Voice Activity Detection 사용
            vad_parameters={
                "threshold": 0.5,
                "min_speech_duration_ms": 250,
                "min_silence_duration_ms": 1000,
            },
        )

        # 세그먼트 텍스트 합치기
        texts = []
        total_confidence = 0.0
        segment_count = 0

        for segment in segments:
            texts.append(segment.text.strip())
            # avg_logprob를 확률로 변환 (대략적)
            total_confidence += np.exp(segment.avg_logprob)
            segment_count += 1

        full_text = " ".join(texts).strip()
        avg_confidence = total_confidence / max(segment_count, 1)

        elapsed = time.time() - start_time
        logger.info(
            f"STT: {info.duration:.2f}s audio → '{full_text[:50]}...' "
            f"({elapsed*1000:.0f}ms, conf={avg_confidence:.2f})"
        )

        return TranscriptionResult(
            text=full_text,
            language=info.language,
            confidence=avg_confidence,
            duration=info.duration,
        )

    async def transcribe_bytes(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        PCM 바이트 → 텍스트 변환

        Args:
            audio_bytes: PCM 16-bit signed int bytes
            sample_rate: 샘플레이트 (기본 16000)
            language: 언어 코드

        Returns:
            TranscriptionResult
        """
        # bytes → numpy array (int16 → float32)
        audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0

        # 리샘플링 필요 시 (16kHz가 아닌 경우)
        if sample_rate != 16000:
            audio_float32 = self._resample(audio_float32, sample_rate, 16000)

        return await self.transcribe(audio_float32, language)

    def _resample(
        self,
        audio: np.ndarray,
        orig_sr: int,
        target_sr: int,
    ) -> np.ndarray:
        """리샘플링"""
        try:
            import librosa
            return librosa.resample(audio, orig_sr=orig_sr, target_sr=target_sr)
        except ImportError:
            # librosa 없으면 scipy 사용
            from scipy import signal
            num_samples = int(len(audio) * target_sr / orig_sr)
            return signal.resample(audio, num_samples)


# 싱글톤 인스턴스 (main.py에서 초기화)
stt_engine: Optional[STTEngine] = None


def get_stt_engine() -> STTEngine:
    """STT 엔진 인스턴스 반환"""
    global stt_engine
    if stt_engine is None:
        from config import settings
        stt_engine = STTEngine(
            model_size=settings.STT_MODEL_SIZE,
            device=settings.STT_DEVICE,
            compute_type=settings.STT_COMPUTE_TYPE,
            language=settings.STT_LANGUAGE,
            beam_size=settings.STT_BEAM_SIZE,
        )
    return stt_engine
