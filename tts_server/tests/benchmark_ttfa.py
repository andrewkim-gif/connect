#!/usr/bin/env python3
"""
TTFA Benchmark - 실시간 음성통화 성능 측정
WebSocket으로 음성 전송 → 응답 시간 측정
"""

import asyncio
import websockets
import json
import time
import wave
import struct
import statistics
import sys
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

# 테스트 설정
WS_URL = "ws://localhost:5002/ws/voice/call"
TEST_AUDIO_PATH = "/home/nexus/connect/server/tts_server/data/test_audio.wav"
NUM_TESTS = 20  # 기본 테스트 횟수


@dataclass
class TestResult:
    """단일 테스트 결과"""
    test_id: int
    stt_ms: float = 0.0
    llm_ttfa_ms: float = 0.0
    tts_ttfa_ms: float = 0.0
    total_ms: float = 0.0
    first_audio_ms: float = 0.0  # 실제 첫 오디오 수신까지
    chunk_count: int = 0
    user_text: str = ""
    response_text: str = ""
    success: bool = False
    error: str = ""


@dataclass
class BenchmarkStats:
    """벤치마크 통계"""
    results: List[TestResult] = field(default_factory=list)

    @property
    def successful(self) -> List[TestResult]:
        return [r for r in self.results if r.success]

    def _stat(self, values: List[float]) -> dict:
        if not values:
            return {"min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0}
        values.sort()
        return {
            "min": min(values),
            "max": max(values),
            "avg": statistics.mean(values),
            "p50": statistics.median(values),
            "p95": values[int(len(values) * 0.95)] if len(values) >= 20 else max(values),
        }

    def summary(self) -> dict:
        s = self.successful
        if not s:
            return {"error": "No successful tests"}

        return {
            "total_tests": len(self.results),
            "successful": len(s),
            "failed": len(self.results) - len(s),
            "stt_ms": self._stat([r.stt_ms for r in s]),
            "llm_ttfa_ms": self._stat([r.llm_ttfa_ms for r in s]),
            "tts_ttfa_ms": self._stat([r.tts_ttfa_ms for r in s]),
            "first_audio_ms": self._stat([r.first_audio_ms for r in s]),
            "total_ms": self._stat([r.total_ms for r in s]),
            "avg_chunks": statistics.mean([r.chunk_count for r in s]),
        }


def load_audio_clip(path: str, duration_sec: float = 3.0) -> bytes:
    """WAV 파일에서 일부 클립 로드"""
    with wave.open(path, 'rb') as wav:
        sample_rate = wav.getframerate()
        n_channels = wav.getnchannels()
        sample_width = wav.getsampwidth()

        # duration_sec 만큼만 읽기
        n_frames = int(sample_rate * duration_sec)
        frames = wav.readframes(n_frames)

        # Mono로 변환 (필요시)
        if n_channels == 2:
            samples = struct.unpack(f"<{len(frames)//2}h", frames)
            mono = [(samples[i] + samples[i+1]) // 2 for i in range(0, len(samples), 2)]
            frames = struct.pack(f"<{len(mono)}h", *mono)

        return frames


async def run_single_test(test_id: int, audio_data: bytes) -> TestResult:
    """단일 테스트 실행"""
    import base64

    result = TestResult(test_id=test_id)
    start_time = time.time()
    first_audio_time = None

    try:
        async with websockets.connect(WS_URL, ping_interval=30) as ws:
            # 1. 연결 확인
            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(msg)
            if data.get("type") != "connected":
                result.error = f"Unexpected connect msg: {data}"
                return result

            # 2. 오디오 전송 (Base64 JSON 형식)
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            await ws.send(json.dumps({
                "type": "voice_input",
                "audio": audio_b64,
                "voice_id": "gd-default"
            }))

            # 음성 전송 시점 기록
            send_time = time.time()

            # 3. 응답 수신
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=30.0)

                    if isinstance(msg, bytes):
                        # 첫 오디오 수신 시간 기록
                        if first_audio_time is None:
                            first_audio_time = time.time()
                            result.first_audio_ms = (first_audio_time - send_time) * 1000
                        continue

                    data = json.loads(msg)
                    msg_type = data.get("type")

                    if msg_type == "transcription":
                        result.user_text = data.get("text", "")

                    elif msg_type == "response_text":
                        result.response_text += data.get("text", "")

                    elif msg_type == "response_end":
                        metrics = data.get("metrics", {})
                        result.stt_ms = metrics.get("stt_ms", 0)
                        result.llm_ttfa_ms = metrics.get("llm_ttfa_ms", 0)
                        result.tts_ttfa_ms = metrics.get("tts_ttfa_ms", 0)
                        result.total_ms = metrics.get("total_ms", 0)
                        result.chunk_count = metrics.get("chunk_count", 0)
                        result.success = True
                        break

                    elif msg_type == "error":
                        result.error = data.get("message", "Unknown error")
                        break

                    elif msg_type == "ping":
                        await ws.send(json.dumps({"type": "pong"}))

                except asyncio.TimeoutError:
                    result.error = "Response timeout"
                    break

    except Exception as e:
        result.error = str(e)

    return result


async def run_benchmark(num_tests: int = NUM_TESTS, audio_path: str = TEST_AUDIO_PATH):
    """벤치마크 실행"""
    print(f"\n{'='*60}")
    print(f"  TTFA Benchmark - {num_tests} tests")
    print(f"{'='*60}\n")

    # 오디오 로드
    print(f"Loading audio from: {audio_path}")
    try:
        audio_data = load_audio_clip(audio_path, duration_sec=3.0)
        print(f"Audio loaded: {len(audio_data)} bytes\n")
    except FileNotFoundError:
        print(f"ERROR: Audio file not found: {audio_path}")
        return None

    stats = BenchmarkStats()

    print(f"{'#':>3} | {'STT':>6} | {'LLM':>6} | {'TTS':>6} | {'1st Audio':>9} | {'Total':>7} | {'Status'}")
    print(f"{'-'*3}-+-{'-'*6}-+-{'-'*6}-+-{'-'*6}-+-{'-'*9}-+-{'-'*7}-+-{'-'*10}")

    for i in range(num_tests):
        result = await run_single_test(i + 1, audio_data)
        stats.results.append(result)

        if result.success:
            print(f"{i+1:>3} | {result.stt_ms:>5.0f}ms | {result.llm_ttfa_ms:>5.0f}ms | "
                  f"{result.tts_ttfa_ms:>5.0f}ms | {result.first_audio_ms:>7.0f}ms | "
                  f"{result.total_ms:>5.0f}ms | ✅ {result.chunk_count} chunks")
        else:
            print(f"{i+1:>3} | {'--':>6} | {'--':>6} | {'--':>6} | {'--':>9} | "
                  f"{'--':>7} | ❌ {result.error[:30]}")

        # 테스트 간 간격 (연결 정리 시간)
        await asyncio.sleep(0.5)

    return stats


def print_summary(stats: BenchmarkStats):
    """결과 요약 출력"""
    summary = stats.summary()

    print(f"\n{'='*60}")
    print(f"  BENCHMARK RESULTS")
    print(f"{'='*60}\n")

    print(f"  Tests: {summary['successful']}/{summary['total_tests']} successful")
    print(f"  Avg Chunks: {summary.get('avg_chunks', 0):.1f}\n")

    print(f"  {'Metric':<15} | {'Min':>7} | {'Avg':>7} | {'P50':>7} | {'P95':>7} | {'Max':>7}")
    print(f"  {'-'*15}-+-{'-'*7}-+-{'-'*7}-+-{'-'*7}-+-{'-'*7}-+-{'-'*7}")

    metrics = [
        ("STT", "stt_ms"),
        ("LLM TTFA", "llm_ttfa_ms"),
        ("TTS TTFA", "tts_ttfa_ms"),
        ("First Audio", "first_audio_ms"),
        ("Total", "total_ms"),
    ]

    for label, key in metrics:
        s = summary.get(key, {})
        if isinstance(s, dict):
            print(f"  {label:<15} | {s['min']:>6.0f}ms | {s['avg']:>6.0f}ms | "
                  f"{s['p50']:>6.0f}ms | {s['p95']:>6.0f}ms | {s['max']:>6.0f}ms")

    # 성능 등급 판정
    first_audio_p50 = summary.get("first_audio_ms", {}).get("p50", 99999)

    print(f"\n  {'='*50}")
    if first_audio_p50 < 2000:
        print(f"  ⭐ EXCELLENT: First Audio P50 = {first_audio_p50:.0f}ms (<2s)")
    elif first_audio_p50 < 3000:
        print(f"  ✅ GOOD: First Audio P50 = {first_audio_p50:.0f}ms (<3s)")
    elif first_audio_p50 < 5000:
        print(f"  ⚠️  FAIR: First Audio P50 = {first_audio_p50:.0f}ms (<5s)")
    else:
        print(f"  ❌ SLOW: First Audio P50 = {first_audio_p50:.0f}ms (≥5s)")
    print(f"  {'='*50}\n")


async def main():
    num_tests = int(sys.argv[1]) if len(sys.argv) > 1 else NUM_TESTS

    stats = await run_benchmark(num_tests=num_tests)

    if stats:
        print_summary(stats)
        return stats.summary()

    return None


if __name__ == "__main__":
    asyncio.run(main())
