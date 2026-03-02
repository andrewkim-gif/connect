#!/usr/bin/env python3
"""
Quick Test - GD Voice API 빠른 테스트

사용법:
    python quick_test.py                     # 기본 테스트 (테스트 음성 생성)
    python quick_test.py "안녕하세요"          # 텍스트로 테스트 음성 생성 후 테스트
    python quick_test.py --file audio.wav    # 파일로 테스트
"""

import asyncio
import json
import base64
import sys
import struct

try:
    import websockets
except ImportError:
    print("설치 필요: pip install websockets")
    sys.exit(1)


def generate_test_audio(duration_sec: float = 2.0, frequency: int = 440) -> bytes:
    """테스트용 사인파 오디오 생성 (16kHz, 16-bit)"""
    import math
    sample_rate = 16000
    samples = int(sample_rate * duration_sec)
    audio = []
    for i in range(samples):
        t = i / sample_rate
        # 간단한 사인파 (실제로는 음성이 아님, 연결 테스트용)
        value = int(32767 * 0.3 * math.sin(2 * math.pi * frequency * t))
        audio.append(value)
    return struct.pack(f'<{len(audio)}h', *audio)


async def test_voice_api(
    server_url: str = "ws://localhost:5002/ws/voice/call",
    audio_data: bytes = None,
):
    """WebSocket API 테스트"""

    print(f"\n🔌 서버 연결: {server_url}")

    try:
        async with websockets.connect(server_url) as ws:
            # 1. 연결 확인
            msg = await ws.recv()
            data = json.loads(msg)
            if data.get("type") != "connected":
                print(f"❌ 연결 실패: {data}")
                return

            print(f"✅ 연결 성공!")
            print(f"   Client ID: {data['client_id']}")
            print(f"   입력: {data['sample_rate_in']}Hz")
            print(f"   출력: {data['sample_rate_out']}Hz")

            # 2. 핑 테스트
            await ws.send(json.dumps({"type": "ping"}))
            msg = await ws.recv()
            ping_data = json.loads(msg)
            if ping_data.get("type") == "pong":
                print("✅ Ping/Pong 정상")

            # 3. 음성 테스트 (옵션)
            if audio_data:
                print(f"\n🎤 음성 전송 중... ({len(audio_data)} bytes)")

                await ws.send(json.dumps({
                    "type": "voice_input",
                    "audio": base64.b64encode(audio_data).decode(),
                    "voice_id": "gd-icl",
                }))

                audio_chunks = []
                transcription = ""
                response_text = ""

                while True:
                    msg = await ws.recv()

                    if isinstance(msg, bytes):
                        audio_chunks.append(msg)
                        print(f"   🔊 오디오 청크: {len(msg)} bytes")
                        continue

                    data = json.loads(msg)
                    msg_type = data.get("type")

                    if msg_type == "transcription":
                        transcription = data.get("text", "")
                        print(f"\n📝 STT: {transcription}")

                    elif msg_type == "response_start":
                        print("\n🤖 GD 응답:")

                    elif msg_type == "response_text":
                        text = data.get("text", "")
                        response_text += text
                        print(text, end="", flush=True)

                    elif msg_type == "response_end":
                        metrics = data.get("metrics", {})
                        print(f"\n\n✅ 완료!")
                        print(f"   총 시간: {metrics.get('total_ms', 0)}ms")
                        print(f"   STT: {metrics.get('stt_ms', 0)}ms")
                        print(f"   음성 길이: {metrics.get('audio_duration', 0)}s")
                        print(f"   오디오 청크: {len(audio_chunks)}개")

                        # 전체 응답 텍스트
                        full_response = metrics.get("response_text", response_text)
                        print(f"\n📄 전체 응답: {full_response}")
                        break

                    elif msg_type == "error":
                        print(f"\n❌ 에러: {data.get('message')}")
                        break

            print("\n✅ 테스트 완료!")

    except ConnectionRefusedError:
        print("❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
    except Exception as e:
        print(f"❌ 오류: {e}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="GD Voice API Quick Test")
    parser.add_argument("text", nargs="?", help="테스트 텍스트 (음성 생성용)")
    parser.add_argument("--file", "-f", help="테스트할 WAV 파일")
    parser.add_argument("--server", "-s", default="ws://localhost:5002/ws/voice/call")
    parser.add_argument("--no-audio", action="store_true", help="연결 테스트만")

    args = parser.parse_args()

    audio_data = None

    if args.file:
        # 파일에서 로드
        import wave
        with wave.open(args.file, 'rb') as wf:
            audio_data = wf.readframes(wf.getnframes())
            print(f"📁 파일 로드: {args.file}")
    elif args.text:
        # TTS로 테스트 음성 생성 (여기서는 더미)
        print(f"⚠️ 텍스트 입력은 아직 지원하지 않습니다.")
        print(f"   음성 파일을 사용하세요: --file audio.wav")
        return
    elif not args.no_audio:
        # 더미 오디오 생성 (연결 테스트용)
        print("🎵 테스트 오디오 생성 (사인파 - 음성 아님)")
        audio_data = generate_test_audio(2.0, 440)

    asyncio.run(test_voice_api(args.server, audio_data))


if __name__ == "__main__":
    main()
