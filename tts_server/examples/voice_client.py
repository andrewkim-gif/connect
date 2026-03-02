"""
GD Voice Call Client - 외부 API 사용 예제
WebSocket 기반 실시간 음성통화 클라이언트

사용법:
    python voice_client.py --server wss://your-server.com/ws/voice/call
    python voice_client.py --audio question.wav
    python voice_client.py --text "안녕하세요"  # TTS만 테스트
"""

import asyncio
import json
import base64
import argparse
import struct
import wave
from typing import Optional, Callable, AsyncGenerator
from dataclasses import dataclass

try:
    import websockets
except ImportError:
    print("websockets 패키지가 필요합니다: pip install websockets")
    exit(1)


@dataclass
class VoiceResponse:
    """음성 응답 결과"""
    user_text: str           # STT 인식 결과
    response_text: str       # GD 응답 텍스트
    audio_data: bytes        # 응답 음성 (PCM 24kHz 16-bit)
    metrics: dict            # 성능 메트릭


class GDVoiceClient:
    """
    GD Voice Call WebSocket Client

    실시간 음성 대화를 위한 클라이언트
    음성 → STT → LLM (GD) → TTS → 음성
    """

    def __init__(
        self,
        server_url: str = "ws://localhost:5002/ws/voice/call",
        api_key: Optional[str] = None,
        voice_id: str = "gd-icl",
    ):
        """
        Args:
            server_url: WebSocket 서버 URL
            api_key: API 키 (서버에서 인증 활성화 시)
            voice_id: TTS 음성 ID ("gd-icl" 또는 "gd-default")
        """
        self.server_url = server_url
        self.api_key = api_key
        self.voice_id = voice_id
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.client_id: Optional[str] = None
        self.sample_rate_in = 16000   # 입력 샘플레이트
        self.sample_rate_out = 24000  # 출력 샘플레이트

    async def connect(self) -> bool:
        """서버에 연결"""
        try:
            url = self.server_url
            if self.api_key:
                url += f"?api_key={self.api_key}"

            self.ws = await websockets.connect(url)

            # 연결 확인 메시지 수신
            response = await self.ws.recv()
            data = json.loads(response)

            if data.get("type") == "connected":
                self.client_id = data.get("client_id")
                self.sample_rate_in = data.get("sample_rate_in", 16000)
                self.sample_rate_out = data.get("sample_rate_out", 24000)
                print(f"✓ 연결됨: {self.client_id}")
                print(f"  입력 샘플레이트: {self.sample_rate_in}Hz")
                print(f"  출력 샘플레이트: {self.sample_rate_out}Hz")
                return True
            else:
                print(f"✗ 연결 실패: {data}")
                return False

        except Exception as e:
            print(f"✗ 연결 오류: {e}")
            return False

    async def disconnect(self):
        """연결 종료"""
        if self.ws:
            await self.ws.close()
            self.ws = None
            print("✓ 연결 종료")

    async def send_audio(
        self,
        audio_bytes: bytes,
        on_transcription: Optional[Callable[[str], None]] = None,
        on_response_text: Optional[Callable[[str], None]] = None,
        on_audio_chunk: Optional[Callable[[bytes], None]] = None,
    ) -> VoiceResponse:
        """
        음성 전송 및 응답 수신

        Args:
            audio_bytes: PCM 16-bit 16kHz 오디오 데이터
            on_transcription: STT 결과 콜백
            on_response_text: LLM 응답 텍스트 콜백 (스트리밍)
            on_audio_chunk: TTS 오디오 청크 콜백 (스트리밍)

        Returns:
            VoiceResponse: 전체 응답 결과
        """
        if not self.ws:
            raise ConnectionError("서버에 연결되지 않음")

        # 음성 전송
        await self.ws.send(json.dumps({
            "type": "voice_input",
            "audio": base64.b64encode(audio_bytes).decode(),
            "voice_id": self.voice_id,
        }))

        # 응답 수신
        user_text = ""
        response_text = ""
        audio_data = b""
        metrics = {}

        while True:
            message = await self.ws.recv()

            # 바이너리 = 오디오 청크
            if isinstance(message, bytes):
                audio_data += message
                if on_audio_chunk:
                    on_audio_chunk(message)
                continue

            # JSON 메시지
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "transcription":
                user_text = data.get("text", "")
                if on_transcription:
                    on_transcription(user_text)

            elif msg_type == "response_text":
                text = data.get("text", "")
                response_text += text
                if on_response_text:
                    on_response_text(text)

            elif msg_type == "response_end":
                metrics = data.get("metrics", {})
                # 전체 응답 텍스트가 metrics에 포함됨
                if "response_text" in metrics:
                    response_text = metrics["response_text"]
                break

            elif msg_type == "error":
                raise Exception(f"서버 오류: {data.get('message')}")

        return VoiceResponse(
            user_text=user_text,
            response_text=response_text,
            audio_data=audio_data,
            metrics=metrics,
        )

    async def chat(
        self,
        audio_bytes: bytes,
        print_stream: bool = True,
    ) -> VoiceResponse:
        """
        간편한 채팅 메서드 (스트리밍 출력 포함)

        Args:
            audio_bytes: PCM 오디오 데이터
            print_stream: 스트리밍 출력 여부

        Returns:
            VoiceResponse
        """
        def on_transcription(text):
            if print_stream:
                print(f"\n👤 나: {text}")

        def on_response_text(text):
            if print_stream:
                print(text, end="", flush=True)

        if print_stream:
            print("\n🎤 GD: ", end="")

        response = await self.send_audio(
            audio_bytes,
            on_transcription=on_transcription,
            on_response_text=on_response_text,
        )

        if print_stream:
            print(f"\n\n⏱️ 처리시간: {response.metrics.get('total_ms', 0)}ms")
            print(f"🔊 음성길이: {response.metrics.get('audio_duration', 0)}s")

        return response

    async def reset_conversation(self):
        """대화 기록 초기화"""
        if not self.ws:
            raise ConnectionError("서버에 연결되지 않음")

        await self.ws.send(json.dumps({"type": "reset"}))
        response = await self.ws.recv()
        data = json.loads(response)

        if data.get("type") == "reset_complete":
            print("✓ 대화 기록 초기화됨")
        else:
            print(f"✗ 초기화 실패: {data}")


def load_wav_as_pcm(file_path: str, target_rate: int = 16000) -> bytes:
    """
    WAV 파일을 PCM 데이터로 로드

    Args:
        file_path: WAV 파일 경로
        target_rate: 목표 샘플레이트 (기본 16000)

    Returns:
        bytes: PCM 16-bit 데이터
    """
    with wave.open(file_path, 'rb') as wf:
        # WAV 정보 확인
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        frame_rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

        print(f"WAV: {channels}ch, {sample_width*8}bit, {frame_rate}Hz, {len(frames)}bytes")

        # 모노 변환
        if channels == 2:
            samples = struct.unpack(f'<{len(frames)//2}h', frames)
            mono = [(samples[i] + samples[i+1]) // 2 for i in range(0, len(samples), 2)]
            frames = struct.pack(f'<{len(mono)}h', *mono)

        # 리샘플링 (간단한 linear interpolation)
        if frame_rate != target_rate:
            samples = struct.unpack(f'<{len(frames)//2}h', frames)
            ratio = target_rate / frame_rate
            new_length = int(len(samples) * ratio)
            resampled = []
            for i in range(new_length):
                src_idx = i / ratio
                idx = int(src_idx)
                frac = src_idx - idx
                if idx + 1 < len(samples):
                    val = int(samples[idx] * (1 - frac) + samples[idx + 1] * frac)
                else:
                    val = samples[idx]
                resampled.append(val)
            frames = struct.pack(f'<{len(resampled)}h', *resampled)

        return frames


def save_pcm_as_wav(pcm_data: bytes, file_path: str, sample_rate: int = 24000):
    """
    PCM 데이터를 WAV 파일로 저장

    Args:
        pcm_data: PCM 16-bit 데이터
        file_path: 저장할 파일 경로
        sample_rate: 샘플레이트
    """
    with wave.open(file_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    print(f"✓ 저장됨: {file_path}")


async def main():
    parser = argparse.ArgumentParser(description="GD Voice Call Client")
    parser.add_argument(
        "--server", "-s",
        default="ws://localhost:5002/ws/voice/call",
        help="WebSocket 서버 URL",
    )
    parser.add_argument(
        "--api-key", "-k",
        help="API 키",
    )
    parser.add_argument(
        "--audio", "-a",
        help="전송할 WAV 오디오 파일",
    )
    parser.add_argument(
        "--voice", "-v",
        default="gd-icl",
        choices=["gd-icl", "gd-default"],
        help="TTS 음성 ID",
    )
    parser.add_argument(
        "--output", "-o",
        default="response.wav",
        help="응답 음성 저장 경로",
    )

    args = parser.parse_args()

    # 클라이언트 생성
    client = GDVoiceClient(
        server_url=args.server,
        api_key=args.api_key,
        voice_id=args.voice,
    )

    # 연결
    if not await client.connect():
        return

    try:
        if args.audio:
            # 파일에서 오디오 로드
            print(f"\n📁 오디오 로드: {args.audio}")
            audio_data = load_wav_as_pcm(args.audio)

            # 채팅
            response = await client.chat(audio_data)

            # 응답 음성 저장
            if response.audio_data:
                save_pcm_as_wav(
                    response.audio_data,
                    args.output,
                    client.sample_rate_out,
                )
        else:
            print("\n사용법: python voice_client.py --audio question.wav")
            print("또는 대화형 모드를 사용하세요.")

    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
