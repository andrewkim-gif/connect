"""
Streaming Handler - 청크 단위 오디오 스트리밍
"""

import logging
import numpy as np
from typing import Iterator, AsyncIterator
from dataclasses import dataclass

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class AudioChunk:
    """오디오 청크"""

    data: bytes  # PCM 16-bit bytes
    index: int  # 청크 번호
    samples: int  # 샘플 수
    is_last: bool = False


class StreamingHandler:
    """
    청크 단위 오디오 스트리밍 핸들러

    qwen-tts는 네이티브 스트리밍을 지원하지 않으므로,
    전체 오디오 생성 후 청크로 분할하여 스트리밍합니다.

    청크 크기: 2400 samples = 100ms @ 24kHz
    포맷: PCM 16-bit mono
    """

    def __init__(
        self,
        chunk_size: int = 2400,  # 100ms @ 24kHz
        sample_rate: int = 24000,
    ):
        self.chunk_size = chunk_size
        self.sample_rate = sample_rate

    def audio_to_pcm(self, audio: np.ndarray) -> bytes:
        """
        float32 오디오 → PCM 16-bit bytes 변환

        Args:
            audio: numpy array (float32, -1.0 ~ 1.0)

        Returns:
            PCM 16-bit little-endian bytes
        """
        # float32 → int16
        audio_int16 = (audio * 32767).astype(np.int16)
        return audio_int16.tobytes()

    def chunk_audio(self, audio: np.ndarray) -> Iterator[AudioChunk]:
        """
        오디오를 청크로 분할

        Args:
            audio: numpy array (float32)

        Yields:
            AudioChunk 객체
        """
        total_samples = len(audio)
        num_chunks = (total_samples + self.chunk_size - 1) // self.chunk_size

        for i in range(num_chunks):
            start = i * self.chunk_size
            end = min(start + self.chunk_size, total_samples)

            chunk_audio = audio[start:end]
            chunk_bytes = self.audio_to_pcm(chunk_audio)

            yield AudioChunk(
                data=chunk_bytes,
                index=i,
                samples=end - start,
                is_last=(i == num_chunks - 1),
            )

    async def stream_chunks(
        self,
        audio: np.ndarray,
    ) -> AsyncIterator[AudioChunk]:
        """
        비동기 청크 스트리밍

        Args:
            audio: numpy array (float32)

        Yields:
            AudioChunk 객체
        """
        for chunk in self.chunk_audio(audio):
            yield chunk

    def get_chunk_duration_ms(self) -> float:
        """청크 재생 시간 (ms)"""
        return (self.chunk_size / self.sample_rate) * 1000

    def estimate_chunks(self, audio_length: int) -> int:
        """예상 청크 수"""
        return (audio_length + self.chunk_size - 1) // self.chunk_size


# 전역 인스턴스
streaming_handler = StreamingHandler(
    chunk_size=settings.CHUNK_SIZE,
    sample_rate=settings.SAMPLE_RATE,
)
