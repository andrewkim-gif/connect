"""
Voice Pipeline - STT → LLM → TTS 통합 파이프라인
실시간 음성통화를 위한 음성 처리 파이프라인
"""

import logging
import asyncio
import time
from typing import AsyncGenerator, Optional, Dict, Any
from dataclasses import dataclass

from services.stt_engine import STTEngine, get_stt_engine
from services.llm_engine import LLMEngine, get_llm_engine
from services.tts_engine import tts_engine
from services.streaming import streaming_handler

logger = logging.getLogger(__name__)


@dataclass
class PipelineMetrics:
    """파이프라인 메트릭"""
    start_time: float = 0.0
    stt_ms: float = 0.0
    llm_ttfa_ms: float = 0.0  # Time to First LLM token
    tts_ttfa_ms: float = 0.0  # Time to First Audio
    total_ms: float = 0.0
    audio_duration: float = 0.0
    user_text: str = ""
    response_text: str = ""


@dataclass
class PipelineEvent:
    """파이프라인 이벤트"""
    type: str  # transcription, response_start, response_text, audio, response_end, error
    data: Optional[Any] = None
    metrics: Optional[Dict[str, Any]] = None


class VoicePipeline:
    """STT → LLM → TTS 통합 파이프라인"""

    def __init__(
        self,
        stt_engine: Optional[STTEngine] = None,
        llm_engine: Optional[LLMEngine] = None,
        voice_id: str = "gd-default",
    ):
        self._stt = stt_engine
        self._llm = llm_engine
        self.voice_id = voice_id

        self._is_processing = False
        self._should_interrupt = False
        self._lock = asyncio.Lock()

    @property
    def stt(self) -> STTEngine:
        """STT 엔진 (지연 초기화)"""
        if self._stt is None:
            self._stt = get_stt_engine()
        return self._stt

    @property
    def llm(self) -> LLMEngine:
        """LLM 엔진 (지연 초기화)"""
        if self._llm is None:
            self._llm = get_llm_engine()
        return self._llm

    async def process_audio(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        voice_id: Optional[str] = None,
        session_id: str = "default",
        character_id: str = "gd",
    ) -> AsyncGenerator[PipelineEvent, None]:
        """
        음성 입력 → 음성 출력 파이프라인

        Args:
            audio_bytes: PCM 16-bit 오디오 데이터
            sample_rate: 입력 샘플레이트 (기본 16000)
            voice_id: TTS 음성 ID
            session_id: 세션 ID (동시 접속 사용자 격리)

        Yields:
            PipelineEvent (transcription, response_text, audio, etc.)
        """
        async with self._lock:
            metrics = PipelineMetrics(start_time=time.time())
            self._is_processing = True
            self._should_interrupt = False
            voice_id = voice_id or self.voice_id

            try:
                # === 1. STT: 음성 → 텍스트 ===
                stt_start = time.time()

                try:
                    result = await self.stt.transcribe_bytes(
                        audio_bytes,
                        sample_rate=sample_rate,
                    )
                    metrics.stt_ms = (time.time() - stt_start) * 1000
                    metrics.user_text = result.text

                    yield PipelineEvent(
                        type="transcription",
                        data={
                            "text": result.text,
                            "language": result.language,
                            "confidence": result.confidence,
                            "is_final": True,
                        }
                    )

                except Exception as e:
                    logger.error(f"STT error: {e}")
                    yield PipelineEvent(
                        type="error",
                        data={"code": "STT_FAILED", "message": str(e)}
                    )
                    return

                if self._should_interrupt:
                    yield PipelineEvent(type="interrupted")
                    return

                # 텍스트가 비어있으면 종료
                if not result.text.strip():
                    yield PipelineEvent(
                        type="error",
                        data={"code": "STT_EMPTY", "message": "인식된 음성이 없습니다"}
                    )
                    return

                # === 2. LLM: 응답 생성 (스트리밍) ===
                yield PipelineEvent(type="response_start")

                llm_start = time.time()
                llm_ttfa_set = False
                full_response = ""
                text_buffer = ""

                try:
                    # session_id로 세션별 대화 기록 격리, character_id로 페르소나 적용
                    async for text_chunk in self.llm.generate_stream(result.text, session_id=session_id, character_id=character_id):
                        if self._should_interrupt:
                            yield PipelineEvent(type="interrupted")
                            return

                        # TTFA 측정
                        if not llm_ttfa_set:
                            metrics.llm_ttfa_ms = (time.time() - llm_start) * 1000
                            llm_ttfa_set = True

                        full_response += text_chunk
                        text_buffer += text_chunk

                        # LLM 텍스트 청크 전송 (디버그용)
                        yield PipelineEvent(
                            type="response_text",
                            data={"text": text_chunk, "is_final": False}
                        )

                        # === 3. TTS: 문장 단위로 음성 생성 ===
                        # 문장 종결 부호에서만 TTS 호출 (안정성 우선)
                        sentence_endings = [".", "!", "?", "~", "。", "！", "？"]
                        should_synthesize = (
                            any(text_buffer.rstrip().endswith(p) for p in sentence_endings)
                            and len(text_buffer) >= 5
                        )

                        if should_synthesize:
                            try:
                                logger.info(f"TTS 문장 처리: '{text_buffer}'")
                                audio, sample_rate_out, _ = await tts_engine.synthesize(
                                    text=text_buffer,
                                    voice_id=voice_id,
                                )

                                # TTS TTFA 측정
                                if metrics.tts_ttfa_ms == 0:
                                    metrics.tts_ttfa_ms = (time.time() - metrics.start_time) * 1000

                                # 청크로 분할하여 스트리밍
                                async for chunk in streaming_handler.stream_chunks(audio):
                                    if self._should_interrupt:
                                        yield PipelineEvent(type="interrupted")
                                        return

                                    yield PipelineEvent(
                                        type="audio",
                                        data=chunk.data
                                    )

                                metrics.audio_duration += len(audio) / sample_rate_out
                                logger.info(f"TTS 문장 완료: {len(audio)} samples")

                            except Exception as e:
                                logger.error(f"TTS error for chunk '{text_buffer}': {e}")
                                # TTS 에러는 계속 진행 (다음 청크 시도)

                            text_buffer = ""

                except Exception as e:
                    logger.error(f"LLM error: {e}")
                    yield PipelineEvent(
                        type="error",
                        data={"code": "LLM_FAILED", "message": str(e)}
                    )
                    return

                # 남은 텍스트 TTS 처리
                if text_buffer.strip():
                    try:
                        logger.info(f"TTS 남은 텍스트 처리: '{text_buffer}'")
                        audio, sample_rate_out, _ = await tts_engine.synthesize(
                            text=text_buffer,
                            voice_id=voice_id,
                        )

                        async for chunk in streaming_handler.stream_chunks(audio):
                            if self._should_interrupt:
                                yield PipelineEvent(type="interrupted")
                                return

                            yield PipelineEvent(type="audio", data=chunk.data)

                        metrics.audio_duration += len(audio) / sample_rate_out
                        logger.info(f"TTS 남은 텍스트 완료: {len(audio)} samples")

                    except Exception as e:
                        logger.error(f"TTS error for final chunk '{text_buffer}': {e}")

                # === 4. 완료 ===
                metrics.total_ms = (time.time() - metrics.start_time) * 1000
                metrics.response_text = full_response

                yield PipelineEvent(
                    type="response_end",
                    metrics={
                        "stt_ms": int(metrics.stt_ms),
                        "llm_ttfa_ms": int(metrics.llm_ttfa_ms),
                        "tts_ttfa_ms": int(metrics.tts_ttfa_ms),
                        "total_ms": int(metrics.total_ms),
                        "audio_duration": round(metrics.audio_duration, 2),
                        "user_text": metrics.user_text,
                        "response_text": metrics.response_text,  # 전체 텍스트 전송
                    }
                )

                logger.info(
                    f"Pipeline complete: '{metrics.user_text[:30]}...' → "
                    f"'{metrics.response_text[:30]}...' "
                    f"(total={metrics.total_ms:.0f}ms, audio={metrics.audio_duration:.1f}s)"
                )

            finally:
                self._is_processing = False

    def interrupt(self) -> None:
        """현재 처리 중단"""
        self._should_interrupt = True
        logger.info("Pipeline interrupted")

    @property
    def is_processing(self) -> bool:
        """처리 중 여부"""
        return self._is_processing

    def reset_conversation(self, session_id: str = "default") -> None:
        """세션별 대화 기록 초기화"""
        if self._llm is not None:
            self._llm.reset_conversation(session_id)

    def remove_session(self, session_id: str) -> None:
        """세션 완전 제거 (연결 종료 시)"""
        if self._llm is not None:
            self._llm.remove_session(session_id)


# 싱글톤 인스턴스
voice_pipeline: Optional[VoicePipeline] = None


def get_voice_pipeline() -> VoicePipeline:
    """Voice Pipeline 인스턴스 반환"""
    global voice_pipeline
    if voice_pipeline is None:
        voice_pipeline = VoicePipeline()
    return voice_pipeline
