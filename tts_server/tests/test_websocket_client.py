#!/usr/bin/env python3
"""
WebSocket TTS Streaming Test Client
"""

import asyncio
import json
import time
import wave
import struct
import sys
import os

# 경로 설정
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    import websockets
except ImportError:
    print("Installing websockets...")
    os.system("pip install websockets")
    import websockets


async def test_websocket_tts():
    """WebSocket TTS 스트리밍 테스트"""
    uri = "ws://localhost:8000/ws/tts/stream"

    print("=" * 60)
    print("WebSocket TTS Streaming Test")
    print("=" * 60)

    try:
        async with websockets.connect(uri) as ws:
            # 연결 확인 메시지 수신
            msg = await ws.recv()
            data = json.loads(msg)
            print(f"\n[Connected] {data}")

            # 합성 요청
            test_text = "안녕하세요, 저는 지드래곤입니다. 오늘도 좋은 하루 보내세요."
            print(f"\n[Sending] text: '{test_text}'")

            await ws.send(json.dumps({
                "type": "synthesize",
                "text": test_text,
                "voice_id": "gd-default",
            }))

            # 응답 수신
            audio_chunks = []
            start_time = time.time()
            ttfa = None

            while True:
                msg = await ws.recv()

                if isinstance(msg, bytes):
                    # 바이너리 오디오 청크
                    if ttfa is None:
                        ttfa = (time.time() - start_time) * 1000
                        print(f"\n[TTFA] {ttfa:.0f}ms (first audio chunk)")

                    audio_chunks.append(msg)
                    print(f"  [Chunk {len(audio_chunks)}] {len(msg)} bytes", end="\r")

                else:
                    # JSON 메시지
                    data = json.loads(msg)
                    print(f"\n[{data['type'].upper()}] {data}")

                    if data["type"] == "end":
                        break
                    elif data["type"] == "error":
                        print(f"Error: {data['message']}")
                        break

            # 결과 출력
            total_time = (time.time() - start_time) * 1000
            total_bytes = sum(len(c) for c in audio_chunks)
            print(f"\n" + "=" * 60)
            print(f"Results:")
            print(f"  - Chunks: {len(audio_chunks)}")
            print(f"  - Total bytes: {total_bytes}")
            print(f"  - TTFA: {ttfa:.0f}ms" if ttfa else "  - TTFA: N/A")
            print(f"  - Total time: {total_time:.0f}ms")
            print("=" * 60)

            # 오디오 저장
            if audio_chunks:
                output_path = "/tmp/ws_test_output.wav"
                save_audio(audio_chunks, output_path)
                print(f"\nSaved to: {output_path}")

            # Ping 테스트
            print("\n[Ping Test]")
            await ws.send(json.dumps({"type": "ping"}))
            msg = await ws.recv()
            print(f"  Response: {msg}")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


def save_audio(chunks: list[bytes], output_path: str):
    """PCM 청크를 WAV 파일로 저장"""
    # 모든 청크 합치기
    audio_data = b"".join(chunks)

    # WAV 파일로 저장
    with wave.open(output_path, "wb") as wav:
        wav.setnchannels(1)  # mono
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(24000)  # 24kHz
        wav.writeframes(audio_data)


if __name__ == "__main__":
    asyncio.run(test_websocket_tts())
