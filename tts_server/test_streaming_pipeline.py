#!/usr/bin/env python3
"""
스트리밍 파이프라인 테스트
TTFA (Time to First Audio) 측정
"""

import asyncio
import time
import websockets
import json
import base64
import wave
import io


async def test_voice_call():
    """음성 통화 테스트"""
    url = "ws://localhost:5002/ws/voice/call"

    # 테스트용 짧은 오디오 생성 (1초, "안녕" 발음 시뮬레이션)
    # 실제 테스트에서는 미리 녹음된 파일 사용
    sample_rate = 16000
    duration = 0.5  # 짧은 테스트
    samples = int(sample_rate * duration)
    audio_data = bytes([0] * (samples * 2))  # 무음 (실제 STT에서는 인식 안될 수 있음)

    # 실제 테스트용 파일이 있으면 사용
    test_audio_path = "/home/nexus/connect/server/tts_server/data/test_audio.wav"
    try:
        with wave.open(test_audio_path, 'rb') as wav:
            audio_data = wav.readframes(wav.getnframes())
        print(f"Using test audio: {test_audio_path}")
    except FileNotFoundError:
        print("No test audio file found, using silence (STT will fail)")

    async with websockets.connect(url) as ws:
        # 연결 확인
        msg = await ws.recv()
        data = json.loads(msg)
        print(f"Connected: {data}")

        # 음성 전송
        print("\nSending voice input...")
        start_time = time.time()

        await ws.send(json.dumps({
            "type": "voice_input",
            "audio": base64.b64encode(audio_data).decode(),
            "voice_id": "gd-icl",
        }))

        # 응답 수신 및 TTFA 측정
        ttfa = None
        audio_chunks = 0
        total_audio_bytes = 0

        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=60)

                if isinstance(msg, bytes):
                    # 오디오 청크
                    audio_chunks += 1
                    total_audio_bytes += len(msg)

                    if ttfa is None:
                        ttfa = (time.time() - start_time) * 1000
                        print(f"\n🎵 TTFA (Time to First Audio): {ttfa:.0f}ms")

                    print(f"  Audio chunk #{audio_chunks}: {len(msg)} bytes")

                else:
                    data = json.loads(msg)
                    msg_type = data.get("type")

                    if msg_type == "transcription":
                        print(f"\n📝 STT: {data.get('text')}")

                    elif msg_type == "response_start":
                        print("\n🤖 LLM response starting...")

                    elif msg_type == "response_text":
                        print(f"  Text: {data.get('text')}", end="", flush=True)

                    elif msg_type == "response_end":
                        metrics = data.get("metrics", {})
                        print("\n\n" + "=" * 50)
                        print("📊 Final Metrics:")
                        print(f"  STT:      {metrics.get('stt_ms', 0):5}ms")
                        print(f"  LLM TTFA: {metrics.get('llm_ttfa_ms', 0):5}ms")
                        print(f"  TTS TTFA: {metrics.get('tts_ttfa_ms', 0):5}ms")
                        print(f"  Total:    {metrics.get('total_ms', 0):5}ms")
                        print(f"  Audio:    {metrics.get('audio_duration', 0):.2f}s")
                        print(f"  Chunks:   {metrics.get('chunk_count', audio_chunks)}")
                        print("=" * 50)
                        break

                    elif msg_type == "error":
                        print(f"\n❌ Error: {data.get('message')}")
                        break

            except asyncio.TimeoutError:
                print("Timeout waiting for response")
                break


if __name__ == "__main__":
    asyncio.run(test_voice_call())
