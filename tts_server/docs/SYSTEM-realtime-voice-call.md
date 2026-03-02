# 🏗️ 실시간 GD 음성통화 시스템 - 상세 아키텍처 설계

**Version**: 1.1
**Date**: 2026-02-28
**Author**: DAVINCI System Architect
**Status**: Implemented
**Parent**: [PLAN-realtime-voice-call.md](./PLAN-realtime-voice-call.md)

---

## 1. 아키텍처 개요 (C4 Level 2)

### 1.1 Container Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GD Voice Call System                           │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         FastAPI Server (:5002)                       │   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │   │
│  │  │ REST API     │  │ WebSocket    │  │ WebSocket                │  │   │
│  │  │ /api/v1/*    │  │ /ws/tts/*    │  │ /ws/voice/call           │  │   │
│  │  │ (기존)       │  │ (기존 TTS)   │  │ (신규 - 음성통화)        │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘  │   │
│  │                                               │                     │   │
│  │  ┌────────────────────────────────────────────┼─────────────────┐  │   │
│  │  │                Voice Pipeline              │                 │  │   │
│  │  │  ┌─────────┐   ┌─────────┐   ┌─────────┐  │                 │  │   │
│  │  │  │   STT   │ → │   LLM   │ → │   TTS   │  │                 │  │   │
│  │  │  │ Engine  │   │ Engine  │   │ Engine  │  │                 │  │   │
│  │  │  └────┬────┘   └────┬────┘   └────┬────┘  │                 │  │   │
│  │  │       │             │             │       │                 │  │   │
│  │  │       ▼             ▼             ▼       │                 │  │   │
│  │  │  faster-whisper  Gemini API   Davinci Voice   │                 │  │   │
│  │  │  (large-v3)      (2.0-flash)  (1.7B)      │                 │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         Streamlit UI (:5001)                         │   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │   │
│  │  │ TTS 테스트   │  │ 음성통화     │  │ 설정 패널               │  │   │
│  │  │ (기존)       │  │ (신규)       │  │                          │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘

External:
  ┌──────────────┐
  │ Gemini API   │ ← API Key (환경변수)
  │ (Google)     │
  └──────────────┘
```

### 1.2 Component Diagram (C4 Level 3)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Voice Pipeline (services/)                        │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                          voice_pipeline.py                              │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│  │  │ VoicePipeline                                                   │   │ │
│  │  │                                                                 │   │ │
│  │  │  + stt_engine: STTEngine                                        │   │ │
│  │  │  + llm_engine: LLMEngine                                        │   │ │
│  │  │  + tts_engine: TTSEngine                                        │   │ │
│  │  │                                                                 │   │ │
│  │  │  + async process_audio(audio_bytes) → AsyncGenerator[bytes]     │   │ │
│  │  │  + async transcribe(audio_bytes) → str                          │   │ │
│  │  │  + async generate_response(text) → AsyncGenerator[str]          │   │ │
│  │  │  + async synthesize(text) → AsyncGenerator[bytes]               │   │ │
│  │  └─────────────────────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌───────────────────┐  ┌───────────────────┐  ┌────────────────────────┐  │
│  │ stt_engine.py     │  │ llm_engine.py     │  │ tts_engine.py (기존)   │  │
│  │                   │  │                   │  │                        │  │
│  │ STTEngine         │  │ LLMEngine         │  │ TTSEngine              │  │
│  │  - model: Whisper │  │  - client: genai  │  │  - model: Davinci Voice    │  │
│  │  - transcribe()   │  │  - system_prompt  │  │  - synthesize()        │  │
│  │  - transcribe_    │  │  - chat_history   │  │  - synthesize_stream() │  │
│  │    stream()       │  │  - generate()     │  │                        │  │
│  └───────────────────┘  │  - generate_      │  └────────────────────────┘  │
│                         │    stream()       │                               │
│                         └───────────────────┘                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 상세 API 설계

### 2.1 WebSocket 엔드포인트

**Endpoint**: `WS /ws/voice/call`

#### 2.1.1 연결 수립

```yaml
# 클라이언트 연결 시 서버 응답
Server → Client:
  {
    "type": "connected",
    "client_id": "uuid-string",
    "config": {
      "sample_rate": 16000,      # STT 입력 샘플레이트
      "output_sample_rate": 24000, # TTS 출력 샘플레이트
      "audio_format": "pcm_s16le"
    }
  }
```

#### 2.1.2 메시지 스키마

```yaml
# === Client → Server ===

# 1. 오디오 청크 전송
{
  "type": "audio",
  "data": "<base64-encoded-pcm>",
  "timestamp": 1709123456789
}

# 2. 발화 종료 신호
{
  "type": "end_turn"
}

# 3. 인터럽트 (응답 중단)
{
  "type": "interrupt"
}

# 4. 세션 설정 변경
{
  "type": "config",
  "voice_id": "gd-default",
  "temperature": 0.7
}

# === Server → Client ===

# 1. STT 결과 (중간)
{
  "type": "transcription_partial",
  "text": "안녕하세요 저는",
  "is_final": false
}

# 2. STT 결과 (최종)
{
  "type": "transcription",
  "text": "안녕하세요 저는 팬이에요",
  "is_final": true,
  "confidence": 0.95
}

# 3. LLM 응답 시작
{
  "type": "response_start",
  "request_id": "uuid"
}

# 4. LLM 텍스트 청크 (디버그용)
{
  "type": "response_text",
  "text": "야, 진짜? ",
  "is_final": false
}

# 5. TTS 오디오 청크
{
  "type": "audio",
  "data": "<base64-encoded-pcm>",
  "chunk_index": 0
}

# 6. 응답 완료
{
  "type": "response_end",
  "request_id": "uuid",
  "metrics": {
    "stt_ms": 320,
    "llm_ttfa_ms": 180,
    "tts_ttfa_ms": 250,
    "total_ms": 1200,
    "audio_duration": 2.5
  }
}

# 7. 에러
{
  "type": "error",
  "code": "STT_FAILED",
  "message": "음성 인식 실패"
}
```

#### 2.1.3 상태 머신

```
                    ┌─────────────────────────────────────────┐
                    │                                         │
                    ▼                                         │
┌──────────┐   connect   ┌──────────┐   audio    ┌──────────┐│
│DISCONNECTED│──────────→│   IDLE   │──────────→│LISTENING ││
└──────────┘             └──────────┘            └────┬─────┘│
                              ▲                       │      │
                              │                  end_turn    │
                              │                       │      │
                              │                       ▼      │
                         response_end           ┌──────────┐ │
                              │                 │PROCESSING│ │
                              │                 └────┬─────┘ │
                              │                      │       │
                              │               response_start │
                              │                      │       │
                              │                      ▼       │
                              │                 ┌──────────┐ │
                              └─────────────────│ SPEAKING │─┘
                                                └──────────┘
                                                     │
                                                 interrupt
                                                     │
                                                     ▼
                                               [IDLE로 복귀]
```

---

## 3. 서비스 클래스 설계

### 3.1 STTEngine

```python
# services/stt_engine.py

from faster_whisper import WhisperModel
from typing import AsyncGenerator, Optional
import numpy as np

class STTEngine:
    """Speech-to-Text 엔진 (faster-whisper 기반)"""

    def __init__(
        self,
        model_size: str = "large-v3",
        device: str = "cuda",
        compute_type: str = "float16"
    ):
        self.model: Optional[WhisperModel] = None
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type

    async def load_model(self) -> None:
        """모델 로딩 (startup 시 호출)"""
        ...

    async def transcribe(
        self,
        audio: np.ndarray,
        language: str = "ko"
    ) -> str:
        """
        오디오 → 텍스트 변환

        Args:
            audio: PCM 오디오 데이터 (16kHz, mono, float32)
            language: 언어 코드

        Returns:
            전사된 텍스트
        """
        ...

    async def transcribe_stream(
        self,
        audio_chunks: AsyncGenerator[bytes, None],
        language: str = "ko"
    ) -> AsyncGenerator[dict, None]:
        """
        스트리밍 전사 (VAD + 실시간)

        Yields:
            {"text": str, "is_final": bool, "confidence": float}
        """
        ...
```

### 3.2 LLMEngine

```python
# services/llm_engine.py

from google import genai
from google.genai import types
from typing import AsyncGenerator, List, Optional

class LLMEngine:
    """LLM 대화 엔진 (Gemini API 기반)"""

    GD_SYSTEM_PROMPT = """당신은 G-Dragon(지드래곤, 권지용)입니다.
BIGBANG의 리더이자 한국을 대표하는 아티스트입니다.

## 성격
- 자신감 있고 솔직함
- 예술과 음악에 대한 열정
- 유머 감각과 친근함

## 말투
- 자연스럽고 캐주얼한 한국어
- "야", "뭐", "진짜", "아 그래?" 등 자연스러운 표현
- 짧고 임팩트 있게 (1-3문장)

## 규칙
- 항상 G-Dragon으로서 대화
- 음악, 패션, 예술 관련 주제에 열정적
- 팬들에게 친근하게 대함
- 너무 길게 말하지 않음"""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
        temperature: float = 0.8
    ):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.history: List[ChatMessage] = []
        self._init_history()

    def _init_history(self) -> None:
        """시스템 프롬프트를 history로 시뮬레이션

        NOTE: Gemini의 chats.create()는 system_instruction을 지원하지 않으므로
        history의 첫 메시지로 시스템 프롬프트를 설정
        """
        self.history = [
            ChatMessage(
                role="user",
                text=f"[시스템 설정]\n{self.GD_SYSTEM_PROMPT}\n\n이제부터 위 설정대로 대화해줘."
            ),
            ChatMessage(
                role="model",
                text="알겠어. 나 GD야. 뭐 물어볼 거 있어? 편하게 말해~"
            ),
        ]

    async def generate(self, user_input: str) -> str:
        """
        응답 생성 (비스트리밍)

        Args:
            user_input: 사용자 입력 텍스트

        Returns:
            GD 페르소나 응답
        """
        ...

    async def generate_stream(
        self,
        user_input: str
    ) -> AsyncGenerator[str, None]:
        """
        스트리밍 응답 생성

        Args:
            user_input: 사용자 입력 텍스트

        Yields:
            응답 텍스트 청크

        NOTE: generate_content_stream() 사용 (chats.send_message_stream이 아님)
        history를 직접 관리하며 contents로 전달
        """
        contents = self._build_contents(user_input)
        stream = self.client.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=self.temperature,
                max_output_tokens=150,
            ),
        )

        full_response = ""
        for chunk in stream:
            if chunk.text:
                full_response += chunk.text
                yield chunk.text

        # 히스토리 업데이트
        self.history.append(ChatMessage(role="user", text=user_input))
        self.history.append(ChatMessage(role="model", text=full_response))

    def reset_conversation(self) -> None:
        """대화 기록 초기화"""
        self._init_history()

    def get_history(self) -> List[dict]:
        """대화 기록 반환"""
        ...
```

### 3.3 VoicePipeline

```python
# services/voice_pipeline.py

from typing import AsyncGenerator, Optional
import asyncio
import time

class VoicePipeline:
    """STT → LLM → TTS 통합 파이프라인"""

    def __init__(
        self,
        stt_engine: STTEngine,
        llm_engine: LLMEngine,
        tts_engine: TTSEngine
    ):
        self.stt = stt_engine
        self.llm = llm_engine
        self.tts = tts_engine

        self._is_processing = False
        self._should_interrupt = False

    async def process_audio(
        self,
        audio_bytes: bytes,
        voice_id: str = "gd-default"
    ) -> AsyncGenerator[dict, None]:
        """
        음성 입력 → 음성 출력 파이프라인

        Args:
            audio_bytes: PCM 오디오 데이터 (16kHz)
            voice_id: TTS 음성 ID

        Yields:
            다양한 타입의 메시지 (transcription, response_text, audio, etc.)
        """
        metrics = {"start_time": time.time()}
        self._is_processing = True
        self._should_interrupt = False

        try:
            # 1. STT: 음성 → 텍스트
            stt_start = time.time()
            user_text = await self.stt.transcribe(audio_bytes)
            metrics["stt_ms"] = (time.time() - stt_start) * 1000

            yield {
                "type": "transcription",
                "text": user_text,
                "is_final": True
            }

            if self._should_interrupt:
                return

            # 2. LLM: 응답 생성 (스트리밍)
            yield {"type": "response_start"}

            llm_start = time.time()
            llm_ttfa = None
            full_response = ""

            # TTS를 위한 텍스트 버퍼
            text_buffer = ""

            async for text_chunk in self.llm.generate_stream(user_text):
                if self._should_interrupt:
                    return

                if llm_ttfa is None:
                    llm_ttfa = (time.time() - llm_start) * 1000
                    metrics["llm_ttfa_ms"] = llm_ttfa

                full_response += text_chunk
                text_buffer += text_chunk

                yield {
                    "type": "response_text",
                    "text": text_chunk,
                    "is_final": False
                }

                # 문장 단위로 TTS 시작 (지연시간 최소화)
                if any(p in text_buffer for p in [".", "!", "?", "~"]):
                    tts_start = time.time()
                    async for audio_chunk in self.tts.synthesize_stream(
                        text_buffer, voice_id
                    ):
                        if self._should_interrupt:
                            return

                        if "tts_ttfa_ms" not in metrics:
                            metrics["tts_ttfa_ms"] = (time.time() - tts_start) * 1000

                        yield {
                            "type": "audio",
                            "data": audio_chunk
                        }

                    text_buffer = ""

            # 남은 텍스트 TTS 처리
            if text_buffer:
                async for audio_chunk in self.tts.synthesize_stream(
                    text_buffer, voice_id
                ):
                    if self._should_interrupt:
                        return
                    yield {"type": "audio", "data": audio_chunk}

            # 완료
            metrics["total_ms"] = (time.time() - metrics["start_time"]) * 1000
            yield {
                "type": "response_end",
                "metrics": metrics
            }

        finally:
            self._is_processing = False

    def interrupt(self) -> None:
        """현재 처리 중단"""
        self._should_interrupt = True

    @property
    def is_processing(self) -> bool:
        """처리 중 여부"""
        return self._is_processing
```

---

## 4. WebSocket 핸들러 설계

```python
# api/websocket/voice_call.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional
import json
import base64
import asyncio

router = APIRouter()

class VoiceCallHandler:
    """음성통화 WebSocket 핸들러"""

    def __init__(
        self,
        websocket: WebSocket,
        pipeline: VoicePipeline,
        client_id: str
    ):
        self.ws = websocket
        self.pipeline = pipeline
        self.client_id = client_id
        self.state = "IDLE"
        self.audio_buffer = bytearray()
        self.voice_id = "gd-default"

    async def handle(self) -> None:
        """메인 핸들링 루프"""
        await self._send_connected()

        try:
            while True:
                message = await self.ws.receive_text()
                data = json.loads(message)
                await self._handle_message(data)
        except WebSocketDisconnect:
            pass

    async def _handle_message(self, data: dict) -> None:
        """메시지 타입별 처리"""
        msg_type = data.get("type")

        if msg_type == "audio":
            await self._handle_audio(data)
        elif msg_type == "end_turn":
            await self._handle_end_turn()
        elif msg_type == "interrupt":
            await self._handle_interrupt()
        elif msg_type == "config":
            await self._handle_config(data)

    async def _handle_audio(self, data: dict) -> None:
        """오디오 청크 수신"""
        self.state = "LISTENING"
        audio_bytes = base64.b64decode(data["data"])
        self.audio_buffer.extend(audio_bytes)

    async def _handle_end_turn(self) -> None:
        """발화 종료 → 파이프라인 실행"""
        if len(self.audio_buffer) == 0:
            return

        self.state = "PROCESSING"
        audio_data = bytes(self.audio_buffer)
        self.audio_buffer.clear()

        async for event in self.pipeline.process_audio(
            audio_data, self.voice_id
        ):
            if event["type"] == "response_start":
                self.state = "SPEAKING"
            await self._send(event)

        self.state = "IDLE"

    async def _handle_interrupt(self) -> None:
        """응답 중단"""
        self.pipeline.interrupt()
        self.audio_buffer.clear()
        self.state = "IDLE"
        await self._send({"type": "interrupted"})

    async def _send(self, data: dict) -> None:
        """메시지 전송"""
        if data.get("type") == "audio":
            # 오디오는 바이너리로 전송
            await self.ws.send_bytes(data["data"])
        else:
            await self.ws.send_text(json.dumps(data))


@router.websocket("/ws/voice/call")
async def voice_call_endpoint(websocket: WebSocket):
    """음성통화 WebSocket 엔드포인트"""
    await websocket.accept()

    client_id = str(uuid.uuid4())[:8]
    handler = VoiceCallHandler(
        websocket=websocket,
        pipeline=voice_pipeline,  # 전역 인스턴스
        client_id=client_id
    )

    await handler.handle()
```

---

## 5. 시퀀스 다이어그램

### 5.1 정상 흐름

```
User        Frontend       WebSocket      STT         LLM         TTS
 │              │              │            │           │           │
 │  말하기 시작  │              │            │           │           │
 ├─────────────→│              │            │           │           │
 │              │ audio chunks │            │           │           │
 │              ├─────────────→│            │           │           │
 │              │ audio chunks │            │           │           │
 │              ├─────────────→│            │           │           │
 │              │              │            │           │           │
 │  말하기 끝   │              │            │           │           │
 ├─────────────→│              │            │           │           │
 │              │  end_turn    │            │           │           │
 │              ├─────────────→│            │           │           │
 │              │              │ transcribe │           │           │
 │              │              ├───────────→│           │           │
 │              │              │   text     │           │           │
 │              │              │←───────────┤           │           │
 │              │ transcription│            │           │           │
 │              │←─────────────┤            │           │           │
 │              │              │            │           │           │
 │              │              │     generate_stream    │           │
 │              │              ├────────────────────────→│          │
 │              │              │      text chunks       │           │
 │              │              │←────────────────────────┤           │
 │              │ response_text│            │           │           │
 │              │←─────────────┤            │           │           │
 │              │              │            │      synthesize_stream│
 │              │              ├────────────────────────────────────→│
 │              │              │            │           │ audio     │
 │              │              │←───────────────────────────────────┤
 │              │  audio chunk │            │           │           │
 │              │←─────────────┤            │           │           │
 │   재생       │              │            │           │           │
 │←─────────────┤              │            │           │           │
 │              │              │            │           │           │
 │              │ response_end │            │           │           │
 │              │←─────────────┤            │           │           │
 │              │              │            │           │           │
```

### 5.2 인터럽트 흐름

```
User        Frontend       WebSocket      Pipeline
 │              │              │              │
 │ (응답 재생 중)│              │              │
 │              │              │   [SPEAKING] │
 │              │              │              │
 │  말하기 시작  │              │              │
 ├─────────────→│              │              │
 │              │  interrupt   │              │
 │              ├─────────────→│              │
 │              │              │  interrupt() │
 │              │              ├─────────────→│
 │              │              │              │
 │              │ interrupted  │              │
 │              │←─────────────┤              │
 │ (재생 중단)  │              │              │
 │←─────────────┤              │              │
 │              │              │    [IDLE]    │
 │              │  audio       │              │
 │              ├─────────────→│              │
 │              │              │              │
```

---

## 6. 설정 확장

```python
# config.py 추가 항목

class Settings(BaseSettings):
    # ... 기존 설정 ...

    # === STT ===
    STT_MODEL_SIZE: str = "large-v3"  # tiny, base, small, medium, large-v3
    STT_DEVICE: str = "cuda"
    STT_COMPUTE_TYPE: str = "float16"
    STT_LANGUAGE: str = "ko"

    # === LLM (Gemini) ===
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_TEMPERATURE: float = 0.8
    GEMINI_MAX_TOKENS: int = 150

    # === Voice Pipeline ===
    VOICE_CALL_ENABLED: bool = True
    VOICE_CALL_MAX_AUDIO_LENGTH: int = 30  # 최대 입력 오디오 길이 (초)
    VOICE_CALL_SAMPLE_RATE_IN: int = 16000  # STT 입력
    VOICE_CALL_SAMPLE_RATE_OUT: int = 24000  # TTS 출력
```

```bash
# .env 추가 항목

# STT (faster-whisper)
TTS_STT_MODEL_SIZE=large-v3
TTS_STT_DEVICE=cuda
TTS_STT_COMPUTE_TYPE=float16

# LLM (Gemini)
TTS_GEMINI_API_KEY=your-api-key-here
TTS_GEMINI_MODEL=gemini-2.0-flash
TTS_GEMINI_TEMPERATURE=0.8

# Voice Pipeline
TTS_VOICE_CALL_ENABLED=true
```

---

## 7. 에러 처리

### 7.1 에러 코드

| 코드 | 설명 | HTTP 대응 |
|------|------|----------|
| `STT_FAILED` | 음성 인식 실패 | 400 |
| `STT_TIMEOUT` | STT 타임아웃 | 408 |
| `STT_AUDIO_TOO_SHORT` | 오디오 너무 짧음 | 400 |
| `LLM_FAILED` | LLM 응답 실패 | 502 |
| `LLM_TIMEOUT` | LLM 타임아웃 | 504 |
| `LLM_RATE_LIMITED` | Gemini API 제한 | 429 |
| `TTS_FAILED` | TTS 합성 실패 | 500 |
| `PIPELINE_INTERRUPTED` | 사용자 인터럽트 | - |
| `INVALID_MESSAGE` | 잘못된 메시지 형식 | 400 |

### 7.2 에러 메시지 형식

```json
{
  "type": "error",
  "code": "LLM_FAILED",
  "message": "Gemini API 응답 실패",
  "details": {
    "original_error": "...",
    "retry_after": 5
  }
}
```

---

## 8. GPU 메모리 계획

```yaml
RTX 4090 (24GB) 기준:

모델별 메모리:
  - Davinci Voice 1.7B (bfloat16): ~4GB
  - faster-whisper large-v3 (float16): ~3GB
  - CUDA 오버헤드: ~1GB

총 사용량: ~8GB (여유 ~16GB)

최적화 옵션 (필요시):
  - STT: medium 모델 사용 (~1.5GB)
  - TTS: float16 변환 (~3GB)
```

---

## 9. 파일 구조 (최종)

```
tts_server/
├── main.py                         # FastAPI 앱 + lifespan
├── config.py                       # 설정 (확장)
├── .env                            # 환경변수 (확장)
│
├── services/
│   ├── __init__.py
│   ├── model_manager.py            # 모델 관리 (기존)
│   ├── voice_manager.py            # 음성 프로필 (기존)
│   ├── tts_engine.py               # TTS 엔진 (기존)
│   ├── streaming.py                # TTS 스트리밍 (기존)
│   ├── stt_engine.py               # STT 엔진 (신규) ⭐
│   ├── llm_engine.py               # LLM 엔진 (신규) ⭐
│   └── voice_pipeline.py           # 통합 파이프라인 (신규) ⭐
│
├── api/
│   ├── routes/
│   │   ├── health.py               # 헬스체크 (기존)
│   │   ├── voices.py               # 음성 목록 (기존)
│   │   └── tts.py                  # TTS API (기존)
│   └── websocket/
│       ├── stream.py               # TTS 스트리밍 (기존)
│       └── voice_call.py           # 음성통화 (신규) ⭐
│
├── core/
│   ├── middleware.py               # 미들웨어 (기존)
│   ├── connection.py               # 연결 관리 (기존)
│   └── exceptions.py               # 예외 (기존)
│
├── models/
│   ├── request.py                  # 요청 모델 (기존)
│   └── response.py                 # 응답 모델 (기존)
│
├── streamlit_app.py                # 테스트 UI (확장) ⭐
│
└── docs/
    ├── PLAN-realtime-voice-call.md
    └── SYSTEM-realtime-voice-call.md
```

---

## 10. 구현 우선순위

### Phase 1: Core (Day 1-2)

1. **stt_engine.py** - faster-whisper 통합
2. **llm_engine.py** - Gemini API + GD 페르소나
3. **voice_pipeline.py** - 파이프라인 연결

### Phase 2: WebSocket (Day 2-3)

4. **voice_call.py** - WebSocket 핸들러
5. **main.py** - 라우터 등록, lifespan 확장
6. **config.py** - 설정 확장

### Phase 3: UI (Day 3)

7. **streamlit_app.py** - 마이크 입력 UI 추가

---

## 11. ADR (아키텍처 결정 기록)

### ADR-001: LLM 선택 - Gemini 2.0 Flash

**결정**: Claude API → Gemini 2.0 Flash 변경

**근거**:
- 사용자 요청 (기존 API 키 보유)
- 스트리밍 지원 (`send_message_stream`)
- 빠른 응답 속도 (Flash 모델)
- 채팅 히스토리 관리 내장

### ADR-002: STT 모델 선택 - faster-whisper large-v3

**결정**: faster-whisper large-v3 사용

**근거**:
- 로컬 실행 (지연시간 최소화)
- 한국어 인식 정확도 높음
- GPU 메모리 여유 (8GB 중 3GB)
- CTranslate2 최적화로 빠른 추론

### ADR-003: 스트리밍 TTS 전략 - 문장 단위

**결정**: LLM 응답을 문장 단위로 TTS에 전달

**근거**:
- TTFA (Time to First Audio) 최소화
- 자연스러운 음성 끊김
- 문장 종결 부호로 분리 용이

---

**Next Step**: `/da:dev`로 Phase 1 Core 구현 시작
