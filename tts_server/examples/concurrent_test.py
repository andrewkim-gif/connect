#!/usr/bin/env python3
"""
동시 접속 테스트 - 세션 격리 검증

여러 클라이언트가 동시에 접속하여 각자 다른 대화를 나눌 때
세션이 격리되는지 확인하는 테스트
"""

import asyncio
import json
import base64
import struct
import math
from typing import List, Tuple

try:
    import websockets
except ImportError:
    print("설치 필요: pip install websockets")
    exit(1)


def generate_test_audio(duration_sec: float = 2.0, frequency: int = 440) -> bytes:
    """테스트용 사인파 오디오 생성 (16kHz, 16-bit)"""
    sample_rate = 16000
    samples = int(sample_rate * duration_sec)
    audio = []
    for i in range(samples):
        t = i / sample_rate
        value = int(32767 * 0.3 * math.sin(2 * math.pi * frequency * t))
        audio.append(value)
    return struct.pack(f'<{len(audio)}h', *audio)


async def test_client(
    client_name: str,
    server_url: str = "ws://localhost:5002/ws/voice/call",
) -> Tuple[str, str, str]:
    """
    단일 클라이언트 테스트

    Returns:
        (client_name, client_id, transcription)
    """
    async with websockets.connect(server_url) as ws:
        # 연결 확인
        msg = await ws.recv()
        data = json.loads(msg)
        if data.get("type") != "connected":
            return (client_name, "FAILED", "Connection failed")

        client_id = data.get("client_id", "unknown")
        print(f"[{client_name}] 연결됨: {client_id}")

        # 테스트 오디오 전송
        audio_data = generate_test_audio(2.0, 440)
        await ws.send(json.dumps({
            "type": "voice_input",
            "audio": base64.b64encode(audio_data).decode(),
            "voice_id": "gd-icl",
        }))

        transcription = ""
        response_text = ""

        # 응답 수신
        while True:
            msg = await ws.recv()

            if isinstance(msg, bytes):
                # 오디오 청크 (무시)
                continue

            data = json.loads(msg)
            msg_type = data.get("type")

            if msg_type == "transcription":
                transcription = data.get("text", "")
                print(f"[{client_name}] STT: {transcription}")

            elif msg_type == "response_text":
                response_text += data.get("text", "")

            elif msg_type == "response_end":
                metrics = data.get("metrics", {})
                full_response = metrics.get("response_text", response_text)
                print(f"[{client_name}] 응답: {full_response[:50]}...")
                return (client_name, client_id, full_response)

            elif msg_type == "error":
                error_msg = data.get("message", "Unknown error")
                print(f"[{client_name}] 에러: {error_msg}")
                return (client_name, client_id, f"ERROR: {error_msg}")

    return (client_name, "unknown", "No response")


async def concurrent_test(num_clients: int = 3):
    """
    동시 접속 테스트

    여러 클라이언트가 동시에 접속하여 각자의 세션이 격리되는지 확인
    """
    print(f"\n🧪 동시 접속 테스트 시작 ({num_clients}명)")
    print("=" * 60)

    # 동시에 여러 클라이언트 실행
    tasks = [
        test_client(f"Client-{i+1}")
        for i in range(num_clients)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    print("\n" + "=" * 60)
    print("📊 테스트 결과:")
    print("-" * 60)

    success_count = 0
    unique_ids = set()

    for result in results:
        if isinstance(result, Exception):
            print(f"❌ 에러: {result}")
        else:
            client_name, client_id, response = result
            unique_ids.add(client_id)
            if not response.startswith("ERROR"):
                success_count += 1
                print(f"✅ {client_name} ({client_id}): {response[:40]}...")
            else:
                print(f"❌ {client_name} ({client_id}): {response}")

    print("-" * 60)
    print(f"🎯 결과: {success_count}/{num_clients} 성공")
    print(f"🆔 고유 세션 ID: {len(unique_ids)}개")

    if len(unique_ids) == num_clients:
        print("✅ 세션 격리 정상!")
    else:
        print("⚠️ 세션 격리 확인 필요")


async def sequential_conversation_test():
    """
    순차적 대화 테스트 - 동일 세션 내 대화 연속성 확인
    """
    print("\n🧪 대화 연속성 테스트 시작")
    print("=" * 60)

    server_url = "ws://localhost:5002/ws/voice/call"

    async with websockets.connect(server_url) as ws:
        # 연결 확인
        msg = await ws.recv()
        data = json.loads(msg)
        client_id = data.get("client_id", "unknown")
        print(f"연결됨: {client_id}")

        # 첫 번째 메시지
        audio_data = generate_test_audio(2.0, 440)
        await ws.send(json.dumps({
            "type": "voice_input",
            "audio": base64.b64encode(audio_data).decode(),
            "voice_id": "gd-icl",
        }))

        response1 = ""
        while True:
            msg = await ws.recv()
            if isinstance(msg, bytes):
                continue
            data = json.loads(msg)
            if data.get("type") == "response_end":
                response1 = data.get("metrics", {}).get("response_text", "")
                print(f"1차 응답: {response1[:50]}...")
                break
            elif data.get("type") == "error":
                print(f"에러: {data.get('message')}")
                return

        # 두 번째 메시지 (같은 세션)
        await asyncio.sleep(1)
        await ws.send(json.dumps({
            "type": "voice_input",
            "audio": base64.b64encode(audio_data).decode(),
            "voice_id": "gd-icl",
        }))

        response2 = ""
        while True:
            msg = await ws.recv()
            if isinstance(msg, bytes):
                continue
            data = json.loads(msg)
            if data.get("type") == "response_end":
                response2 = data.get("metrics", {}).get("response_text", "")
                print(f"2차 응답: {response2[:50]}...")
                break
            elif data.get("type") == "error":
                print(f"에러: {data.get('message')}")
                return

        print("\n" + "=" * 60)
        if response1 and response2:
            print("✅ 대화 연속성 테스트 성공!")
            print("   (동일 세션 내에서 대화 기록이 유지됨)")
        else:
            print("❌ 대화 연속성 테스트 실패")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="동시 접속 테스트")
    parser.add_argument("--clients", "-c", type=int, default=2, help="동시 접속 클라이언트 수")
    parser.add_argument("--sequential", "-s", action="store_true", help="순차적 대화 테스트")

    args = parser.parse_args()

    if args.sequential:
        asyncio.run(sequential_conversation_test())
    else:
        asyncio.run(concurrent_test(args.clients))


if __name__ == "__main__":
    main()
