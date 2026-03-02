"""
Voice Pipeline Streaming - 실시간 음성통화를 위한 최적화 파이프라인
LLM과 TTS를 병렬로 처리하여 TTFA 최소화
"""

import logging
import asyncio
import time
import re
from typing import AsyncGenerator, Optional, Dict, Any, List
from dataclasses import dataclass

from services.stt_engine import STTEngine, get_stt_engine
from services.llm_engine import LLMEngine, get_llm_engine
from services.tts_engine import tts_engine
from services.streaming import streaming_handler
from config import settings

logger = logging.getLogger(__name__)


@dataclass
class StreamingMetrics:
    """스트리밍 파이프라인 메트릭"""
    start_time: float = 0.0
    stt_ms: float = 0.0
    llm_ttfa_ms: float = 0.0
    tts_ttfa_ms: float = 0.0
    total_ms: float = 0.0
    audio_duration: float = 0.0
    user_text: str = ""
    response_text: str = ""
    chunk_count: int = 0


@dataclass
class TTSJob:
    """TTS 작업 단위"""
    text: str
    index: int
    priority: int = 0  # 0 = 일반, 1 = 첫 청크 (높은 우선순위)


@dataclass
class PipelineEvent:
    """파이프라인 이벤트"""
    type: str  # transcription, response_start, response_text, audio, response_end, error, interrupted
    data: Optional[Any] = None
    metrics: Optional[Dict[str, Any]] = None


class StreamingVoicePipeline:
    """
    실시간 음성 통화를 위한 스트리밍 파이프라인

    최적화:
    1. LLM → TTS 병렬 처리 (asyncio.Queue)
    2. 절(clause) 단위 분할로 TTFA 최소화
    3. 첫 청크 우선 처리
    4. 오디오 청크 즉시 스트리밍
    """

    # 텍스트 분할 패턴 (문장 단위 - 운율 보존)
    # 쉼표, 콜론, 세미콜론에서는 분할하지 않음 (자연스러운 운율 유지)
    # 문장 종결 기호(. ! ? ~)에서만 분할
    SENTENCE_PATTERN = re.compile(
        r'([^.。!！?？~]+[.。!！?？~]?)',
        re.UNICODE
    )
    # 문장 종결 기호 (여기서만 분할)
    SENTENCE_ENDINGS = '.。!！?？~'

    def __init__(
        self,
        stt_engine: Optional[STTEngine] = None,
        llm_engine: Optional[LLMEngine] = None,
        voice_id: str = "gd-default",
        max_concurrent_tts: Optional[int] = None,
        min_chunk_length: Optional[int] = None,
        max_chunk_length: Optional[int] = None,
    ):
        self._stt = stt_engine
        self._llm = llm_engine
        self.voice_id = voice_id

        # 설정 값 (config 또는 파라미터에서)
        self.max_concurrent_tts = max_concurrent_tts or settings.VOICE_PIPELINE_MAX_CONCURRENT_TTS
        self.min_chunk_length = min_chunk_length or settings.VOICE_PIPELINE_MIN_CHUNK_LENGTH
        self.max_chunk_length = max_chunk_length or settings.VOICE_PIPELINE_MAX_CHUNK_LENGTH

        self._is_processing = False
        self._should_interrupt = False

        # TTS 작업 큐
        self._tts_queue: asyncio.Queue[Optional[TTSJob]] = asyncio.Queue()
        self._audio_queue: asyncio.Queue[Optional[tuple]] = asyncio.Queue()

        # 세마포어로 동시 TTS 제한
        self._tts_semaphore = asyncio.Semaphore(self.max_concurrent_tts)

    @property
    def stt(self) -> STTEngine:
        if self._stt is None:
            self._stt = get_stt_engine()
        return self._stt

    @property
    def llm(self) -> LLMEngine:
        if self._llm is None:
            self._llm = get_llm_engine()
        return self._llm

    def _split_into_chunks(self, text: str, is_first_chunk: bool = False) -> List[str]:
        """
        텍스트를 문장 단위로 분할 (운율 보존 우선)

        핵심 전략:
        - 쉼표에서 분할하지 않음 (운율 끊김 방지)
        - 문장 종결 기호(. ! ? ~)에서만 분할
        - 자연스러운 음성 합성을 위해 문장 단위 유지

        is_first_chunk=True: 첫 청크도 문장 단위 (단, 길이 제한)
        """
        chunks = []
        current = ""

        # === 문장 단위 분할 전략 (운율 보존) ===
        #
        # 핵심 변경:
        # - 쉼표, 콜론, 세미콜론에서 분할하지 않음
        # - 문장 종결 기호에서만 분할
        # - 첫 청크도 완전한 문장 단위 (단, 길이 제한 있음)
        #
        # 전략:
        # 1. 첫 청크: 첫 문장 전체 (최대 25자, 넘으면 분할)
        # 2. 이후: 완전한 문장 단위 (최대 60자)
        if is_first_chunk:
            min_len = 5    # 최소 5자 (너무 짧은 문장 방지)
            max_len = 25   # 최대 25자 (첫 문장)
        else:
            min_len = 10   # 최소 10자
            max_len = 60   # 최대 60자 (긴 문장도 허용 - 운율 유지)

        for match in self.SENTENCE_PATTERN.finditer(text):
            part = match.group(1).strip()
            if not part:
                continue

            current += part

            # 문장 종결 기호에서만 분할 (쉼표에서 분할 안함!)
            if len(current) >= min_len and current and current[-1] in self.SENTENCE_ENDINGS:
                chunks.append(current)
                current = ""
            # 최대 길이 초과 시 강제 분할 (안전장치)
            elif len(current) > max_len * 1.5:
                chunks.append(current)
                current = ""

        # 남은 텍스트
        if current.strip():
            chunks.append(current.strip())

        return chunks

    async def _tts_worker(
        self,
        voice_id: str,
        metrics: StreamingMetrics,
    ) -> None:
        """TTS 작업자 - 큐에서 텍스트를 받아 TTS 처리"""
        while True:
            try:
                job = await self._tts_queue.get()

                if job is None:  # 종료 신호
                    await self._audio_queue.put(None)
                    break

                if self._should_interrupt:
                    continue

                async with self._tts_semaphore:
                    try:
                        logger.info(f"TTS #{job.index}: '{job.text[:50]}...' ({len(job.text)}자)")

                        # voice_id를 mode로 변환 (tts_engine.synthesize는 mode 파라미터 사용)
                        mode = "finetuned" if voice_id in ["gd-default", "finetuned"] else "auto"
                        audio, sample_rate, tts_ms = await tts_engine.synthesize(
                            text=job.text,
                            mode=mode,
                        )

                        # TTFA 측정 (첫 청크)
                        if job.index == 0 and metrics.tts_ttfa_ms == 0:
                            metrics.tts_ttfa_ms = (time.time() - metrics.start_time) * 1000

                        # 오디오 큐에 추가 (인덱스와 함께 - 순서 보장용)
                        await self._audio_queue.put((job.index, audio, sample_rate))

                        metrics.audio_duration += len(audio) / sample_rate
                        metrics.chunk_count += 1

                        logger.info(f"TTS #{job.index} done: {len(audio)/sample_rate:.2f}s ({tts_ms:.0f}ms)")

                    except Exception as e:
                        logger.error(f"TTS error for job #{job.index} ('{job.text[:30]}...'): {e}")
                        import traceback
                        logger.error(traceback.format_exc())

            except asyncio.CancelledError:
                break

    async def process_audio(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        voice_id: Optional[str] = None,
        session_id: str = "default",
    ) -> AsyncGenerator[PipelineEvent, None]:
        """
        실시간 음성 처리 파이프라인

        흐름:
        1. STT: 음성 → 텍스트
        2. LLM 스트리밍 시작 (백그라운드)
        3. 텍스트 청크 수집 → TTS 큐에 추가
        4. TTS 워커가 병렬로 처리
        5. 오디오 청크 순서대로 스트리밍
        """
        metrics = StreamingMetrics(start_time=time.time())
        self._is_processing = True
        self._should_interrupt = False
        voice_id = voice_id or self.voice_id

        # 큐 초기화
        self._tts_queue = asyncio.Queue()
        self._audio_queue = asyncio.Queue()

        try:
            # === 1. STT ===
            stt_start = time.time()

            try:
                result = await self.stt.transcribe_bytes(audio_bytes, sample_rate=sample_rate)
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
                yield PipelineEvent(type="error", data={"code": "STT_FAILED", "message": str(e)})
                return

            if self._should_interrupt:
                yield PipelineEvent(type="interrupted")
                return

            if not result.text.strip():
                yield PipelineEvent(type="error", data={"code": "STT_EMPTY", "message": "인식된 음성이 없습니다"})
                return

            # === 2. LLM + TTS 병렬 처리 ===
            yield PipelineEvent(type="response_start")

            # TTS 워커 시작
            tts_task = asyncio.create_task(self._tts_worker(voice_id, metrics))

            # LLM 스트리밍 + TTS 큐잉
            llm_start = time.time()
            llm_ttfa_set = False
            full_response = ""
            text_buffer = ""
            chunk_index = 0

            try:
                first_chunk_sent = False

                async for text_chunk in self.llm.generate_stream(result.text, session_id=session_id):
                    if self._should_interrupt:
                        await self._tts_queue.put(None)
                        yield PipelineEvent(type="interrupted")
                        return

                    # TTFA 측정
                    if not llm_ttfa_set:
                        metrics.llm_ttfa_ms = (time.time() - llm_start) * 1000
                        llm_ttfa_set = True

                    full_response += text_chunk
                    text_buffer += text_chunk

                    # 텍스트 청크 이벤트
                    yield PipelineEvent(
                        type="response_text",
                        data={"text": text_chunk, "is_final": False}
                    )

                    # 첫 청크: 빠른 응답 + 문장 단위 (운율 보존)
                    chunks = self._split_into_chunks(text_buffer, is_first_chunk=not first_chunk_sent)

                    # 완성된 청크가 있으면 TTS 큐에 추가
                    if len(chunks) > 1:
                        for chunk_text in chunks[:-1]:
                            await self._tts_queue.put(TTSJob(
                                text=chunk_text,
                                index=chunk_index,
                                priority=1 if chunk_index == 0 else 0,
                            ))
                            chunk_index += 1
                            first_chunk_sent = True
                        text_buffer = chunks[-1]  # 마지막 불완전 청크 유지

            except Exception as e:
                logger.error(f"LLM error: {e}")
                await self._tts_queue.put(None)
                yield PipelineEvent(type="error", data={"code": "LLM_FAILED", "message": str(e)})
                return

            # 남은 텍스트 처리
            if text_buffer.strip():
                await self._tts_queue.put(TTSJob(
                    text=text_buffer.strip(),
                    index=chunk_index,
                    priority=0,
                ))

            # TTS 종료 신호
            await self._tts_queue.put(None)

            # 오디오 스트리밍 (순서 보장)
            audio_buffer: Dict[int, tuple] = {}  # index → (audio, sr)
            next_audio_index = 0

            while True:
                item = await self._audio_queue.get()

                if item is None:  # 종료
                    break

                idx, audio, sr = item
                audio_buffer[idx] = (audio, sr)

                # 순서대로 전송
                while next_audio_index in audio_buffer:
                    audio, sr = audio_buffer.pop(next_audio_index)

                    async for chunk in streaming_handler.stream_chunks(audio):
                        if self._should_interrupt:
                            yield PipelineEvent(type="interrupted")
                            break
                        yield PipelineEvent(type="audio", data=chunk.data)

                    next_audio_index += 1

            # TTS 워커 완료 대기
            await tts_task

            # === 완료 ===
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
                    "response_text": metrics.response_text,
                    "chunk_count": metrics.chunk_count,
                }
            )

            logger.info(
                f"Streaming pipeline complete: "
                f"STT={metrics.stt_ms:.0f}ms, LLM_TTFA={metrics.llm_ttfa_ms:.0f}ms, "
                f"TTS_TTFA={metrics.tts_ttfa_ms:.0f}ms, Total={metrics.total_ms:.0f}ms, "
                f"Chunks={metrics.chunk_count}"
            )

        finally:
            self._is_processing = False

    def interrupt(self) -> None:
        """현재 처리 중단"""
        self._should_interrupt = True
        logger.info("Streaming pipeline interrupted")

    @property
    def is_processing(self) -> bool:
        return self._is_processing

    def reset_conversation(self, session_id: str = "default") -> None:
        if self._llm is not None:
            self._llm.reset_conversation(session_id)

    def remove_session(self, session_id: str) -> None:
        if self._llm is not None:
            self._llm.remove_session(session_id)

    async def process_text(
        self,
        text: str,
        voice_id: Optional[str] = None,
        session_id: str = "default",
    ) -> AsyncGenerator[PipelineEvent, None]:
        """
        텍스트 입력 처리 (GD Initiative용 - STT 스킵)

        GD가 먼저 말 걸기 등 텍스트 프롬프트로 시작하는 경우 사용
        """
        metrics = StreamingMetrics(start_time=time.time())
        self._is_processing = True
        self._should_interrupt = False
        voice_id = voice_id or self.voice_id

        # 큐 초기화
        self._tts_queue = asyncio.Queue()
        self._audio_queue = asyncio.Queue()

        try:
            yield PipelineEvent(type="response_start")

            # TTS 워커 시작
            tts_task = asyncio.create_task(self._tts_worker(voice_id, metrics))

            # LLM 스트리밍
            llm_start = time.time()
            llm_ttfa_set = False
            full_response = ""
            text_buffer = ""
            chunk_index = 0
            first_chunk_sent = False

            try:
                async for text_chunk in self.llm.generate_stream(text, session_id=session_id):
                    if self._should_interrupt:
                        await self._tts_queue.put(None)
                        yield PipelineEvent(type="interrupted")
                        return

                    if not llm_ttfa_set:
                        metrics.llm_ttfa_ms = (time.time() - llm_start) * 1000
                        llm_ttfa_set = True

                    full_response += text_chunk
                    text_buffer += text_chunk

                    yield PipelineEvent(
                        type="response_text",
                        data={"text": text_chunk, "is_final": False}
                    )

                    chunks = self._split_into_chunks(text_buffer, is_first_chunk=not first_chunk_sent)

                    if len(chunks) > 1:
                        for chunk_text in chunks[:-1]:
                            await self._tts_queue.put(TTSJob(
                                text=chunk_text,
                                index=chunk_index,
                                priority=1 if chunk_index == 0 else 0,
                            ))
                            chunk_index += 1
                            first_chunk_sent = True
                        text_buffer = chunks[-1]

            except Exception as e:
                logger.error(f"LLM error in process_text: {e}")
                await self._tts_queue.put(None)
                yield PipelineEvent(type="error", data={"code": "LLM_FAILED", "message": str(e)})
                return

            if text_buffer.strip():
                await self._tts_queue.put(TTSJob(
                    text=text_buffer.strip(),
                    index=chunk_index,
                    priority=0,
                ))

            await self._tts_queue.put(None)

            # 오디오 스트리밍
            audio_buffer: Dict[int, tuple] = {}
            next_audio_index = 0

            while True:
                item = await self._audio_queue.get()
                if item is None:
                    break

                idx, audio, sr = item
                audio_buffer[idx] = (audio, sr)

                while next_audio_index in audio_buffer:
                    audio, sr = audio_buffer.pop(next_audio_index)
                    async for chunk in streaming_handler.stream_chunks(audio):
                        if self._should_interrupt:
                            yield PipelineEvent(type="interrupted")
                            break
                        yield PipelineEvent(type="audio", data=chunk.data)
                    next_audio_index += 1

            await tts_task

            metrics.total_ms = (time.time() - metrics.start_time) * 1000
            metrics.response_text = full_response

            yield PipelineEvent(
                type="response_end",
                metrics={
                    "llm_ttfa_ms": int(metrics.llm_ttfa_ms),
                    "tts_ttfa_ms": int(metrics.tts_ttfa_ms),
                    "total_ms": int(metrics.total_ms),
                    "response_text": metrics.response_text,
                    "chunk_count": metrics.chunk_count,
                    "type": "gd_initiative",
                }
            )

        finally:
            self._is_processing = False


# 싱글톤 인스턴스
streaming_voice_pipeline: Optional[StreamingVoicePipeline] = None


def get_streaming_voice_pipeline() -> StreamingVoicePipeline:
    """Streaming Voice Pipeline 인스턴스 반환"""
    global streaming_voice_pipeline
    if streaming_voice_pipeline is None:
        streaming_voice_pipeline = StreamingVoicePipeline()
    return streaming_voice_pipeline
