# GD Voice Clone TTS Streaming Server - System Architecture

## Overview

G-Dragon 음성 복제 기반 실시간 스트리밍 TTS 서버 아키텍처 설계 문서.

**목표:**
- TTFA (Time To First Audio): ~100ms
- Mouth-to-ear latency: Sub-500ms
- RTF (Real-Time Factor): < 1.0
- WebSocket 기반 실시간 스트리밍

**기술 스택:**
- TTS Model: Davinci Voice 12Hz-1.7B-Base
- Framework: FastAPI + Uvicorn
- Runtime: PyTorch + FlashAttention 2
- Hardware: NVIDIA RTX 5090 32GB

---

## C4 Level 1: System Context

```
                    ┌─────────────┐
                    │   Client    │
                    │ (Mobile/Web)│
                    └──────┬──────┘
                           │ WebSocket / HTTP
                           ▼
                    ┌─────────────┐
                    │  TTS Server │
                    │  (FastAPI)  │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Davinci     │
                    │ Voice (GPU) │
                    └─────────────┘
```

---

## C4 Level 2: Container Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     GD Voice Clone TTS System                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐     ┌──────────────────────────────────┐ │
│  │  API Gateway     │────▶│  TTS Streaming Service           │ │
│  │  (FastAPI)       │     │  (Davinci Voice + Voice Clone)       │ │
│  │                  │     │                                   │ │
│  │  - REST /api/v1  │     │  - ModelManager                  │ │
│  │  - WebSocket /ws │     │  - VoiceManager (캐시)           │ │
│  │  - Health Check  │     │  - StreamingHandler              │ │
│  │  - Port: 8000    │     │  - TTSEngine                     │ │
│  └──────────────────┘     └──────────────────────────────────┘ │
│           │                           │                         │
│           │                           ▼                         │
│           │               ┌──────────────────────────────────┐ │
│           │               │  GPU Runtime                     │ │
│           │               │  (PyTorch + FlashAttention 2)    │ │
│           │               │                                   │ │
│           │               │  - RTX 5090 32GB                 │ │
│           │               │  - CUDA 12.8                     │ │
│           │               │  - bfloat16 precision            │ │
│           │               │  - VRAM 사용: ~4GB               │ │
│           │               └──────────────────────────────────┘ │
│           │                                                     │
│           ▼                                                     │
│  ┌──────────────────┐     ┌──────────────────────────────────┐ │
│  │  Voice Store     │     │  Config Store                    │ │
│  │  (File System)   │     │  (.env / YAML)                   │ │
│  │                  │     │                                   │ │
│  │  - GD samples    │     │  - Model paths                   │ │
│  │  - Cached prompts│     │  - Server settings               │ │
│  │  - /data/voices/ │     │  - Performance tuning            │ │
│  └──────────────────┘     └──────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## C4 Level 3: Component Diagram

### TTS Streaming Service Components

```
┌─────────────────────────────────────────────────────────────────┐
│                   TTS Streaming Service                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │ ModelManager    │    │ VoiceManager    │                     │
│  │                 │    │                 │                     │
│  │ - load_model()  │    │ - load_voices() │                     │
│  │ - warmup()      │    │ - get_prompt()  │                     │
│  │ - get_model()   │    │ - cache_prompt()│                     │
│  └────────┬────────┘    └────────┬────────┘                     │
│           │                      │                               │
│           ▼                      ▼                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │               TTSEngine                                  │   │
│  │                                                          │   │
│  │  - synthesize(text, voice_id) → audio                   │   │
│  │  - stream_synthesize(text, voice_id) → AsyncGenerator   │   │
│  │  - clone_voice(ref_audio) → voice_prompt                │   │
│  └─────────────────────────────────────────────────────────┘   │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │               StreamingHandler                           │   │
│  │                                                          │   │
│  │  - chunk_generator(audio) → Iterator[bytes]             │   │
│  │  - encode_pcm(audio) → bytes                            │   │
│  │  - CHUNK_SIZE = 2400 samples (100ms @ 24kHz)            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### API Gateway Components

```
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway (FastAPI)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │ REST Router     │    │ WebSocket Router│                     │
│  │                 │    │                 │                     │
│  │ POST /synthesize│    │ /ws/tts/stream  │                     │
│  │ POST /clone     │    │ - on_connect    │                     │
│  │ GET /voices     │    │ - on_message    │                     │
│  │ GET /health     │    │ - on_disconnect │                     │
│  └────────┬────────┘    └────────┬────────┘                     │
│           │                      │                               │
│           ▼                      ▼                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │               ConnectionManager                          │   │
│  │                                                          │   │
│  │  - active_connections: Dict[str, WebSocket]             │   │
│  │  - connect(ws, client_id)                               │   │
│  │  - disconnect(client_id)                                │   │
│  │  - send_audio(client_id, chunk) → async                 │   │
│  │  - broadcast(chunk) → async                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Security

### Authentication & Authorization

```
┌─────────────────────────────────────────────────────────────────┐
│                    Security Architecture                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │ API Key Auth    │    │ Rate Limiter    │                     │
│  │                 │    │                 │                     │
│  │ X-API-Key header│    │ Token Bucket    │                     │
│  │ validate_key()  │    │ per client/IP   │                     │
│  └────────┬────────┘    └────────┬────────┘                     │
│           │                      │                               │
│           ▼                      ▼                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │               Security Middleware                        │   │
│  │                                                          │   │
│  │  - authenticate(request) → API key validation           │   │
│  │  - rate_limit(client_id) → Token bucket check           │   │
│  │  - authorize(scope) → Permission verification           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### REST API Authentication

```python
# API Key 인증 (HTTP Header)
async def verify_api_key(x_api_key: str = Header(...)):
    if not x_api_key or x_api_key not in valid_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key
```

#### WebSocket Authentication

```python
# WebSocket 연결 시 쿼리 파라미터로 인증
# ws://server:8000/ws/tts/stream?api_key=xxx

async def websocket_auth(websocket: WebSocket):
    api_key = websocket.query_params.get("api_key")
    if not api_key or api_key not in valid_keys:
        await websocket.close(code=4001, reason="Unauthorized")
        return None
    return api_key
```

### Rate Limiting

```python
# Token Bucket 알고리즘
class RateLimiter:
    def __init__(self):
        self.buckets: Dict[str, TokenBucket] = {}

    async def check(self, client_id: str) -> bool:
        """
        Rate limits:
        - REST: 60 requests/minute per client
        - WebSocket: 30 messages/minute per connection
        - Synthesize: 10 requests/minute (GPU intensive)
        """
        bucket = self.get_or_create_bucket(client_id)
        return bucket.consume()
```

| Endpoint | Rate Limit | Window |
|----------|------------|--------|
| `/api/v1/tts/synthesize` | 10 req | 1 minute |
| `/api/v1/tts/voices` | 60 req | 1 minute |
| `/ws/tts/stream` | 30 msg | 1 minute |
| `/api/v1/health` | 120 req | 1 minute |

### CORS Configuration

```python
# main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # ["https://app.example.com"]
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)
```

---

## Error Handling

### Error Response Schema

```python
# models/response.py
from pydantic import BaseModel
from typing import Optional
from enum import Enum

class ErrorCode(str, Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    RATE_LIMITED = "RATE_LIMITED"
    VOICE_NOT_FOUND = "VOICE_NOT_FOUND"
    TEXT_TOO_LONG = "TEXT_TOO_LONG"
    MODEL_ERROR = "MODEL_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"

class ErrorResponse(BaseModel):
    error: ErrorCode
    message: str
    detail: Optional[str] = None
    request_id: Optional[str] = None

# Example responses:
# 400: {"error": "TEXT_TOO_LONG", "message": "Text exceeds 500 characters"}
# 401: {"error": "UNAUTHORIZED", "message": "Invalid API key"}
# 429: {"error": "RATE_LIMITED", "message": "Rate limit exceeded", "detail": "Retry after 30 seconds"}
# 500: {"error": "MODEL_ERROR", "message": "TTS synthesis failed"}
```

### WebSocket Error Handling

```python
# WebSocket 에러 코드 정의
class WSCloseCode:
    NORMAL = 1000           # 정상 종료
    GOING_AWAY = 1001       # 서버 종료
    PROTOCOL_ERROR = 1002   # 프로토콜 에러
    INVALID_DATA = 1003     # 잘못된 데이터

    # Custom codes (4000-4999)
    UNAUTHORIZED = 4001     # 인증 실패
    RATE_LIMITED = 4002     # Rate limit 초과
    TEXT_TOO_LONG = 4003    # 텍스트 길이 초과
    VOICE_NOT_FOUND = 4004  # 음성 ID 없음
    SYNTHESIS_ERROR = 4005  # TTS 합성 실패
```

### WebSocket Disconnect Handling

```python
# api/websocket/stream.py
from starlette.websockets import WebSocketDisconnect

@app.websocket("/ws/tts/stream")
async def websocket_endpoint(websocket: WebSocket):
    client_id = None
    try:
        # 연결 및 인증
        client_id = await connection_manager.connect(websocket)
        if not client_id:
            return

        # 메시지 처리 루프
        while True:
            data = await websocket.receive_json()
            await process_message(websocket, data, client_id)

    except WebSocketDisconnect as e:
        # 클라이언트 연결 끊김 (정상)
        logger.info(f"Client {client_id} disconnected: code={e.code}")

    except Exception as e:
        # 예상치 못한 에러
        logger.error(f"WebSocket error for {client_id}: {e}")
        await websocket.close(code=WSCloseCode.SYNTHESIS_ERROR)

    finally:
        # 항상 정리 작업 수행
        if client_id:
            await connection_manager.disconnect(client_id)
            # 진행 중인 TTS 작업 취소
            await tts_engine.cancel_synthesis(client_id)
```

### Global Exception Handler

```python
# core/exceptions.py
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    logger.error(f"[{request_id}] Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "request_id": request_id
        }
    )
```

---

## API Design

### REST Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/tts/synthesize` | 텍스트 → 음성 변환 (비스트리밍) | API Key |
| GET | `/api/v1/tts/voices` | 사용 가능한 음성 목록 | API Key |
| POST | `/api/v1/tts/clone` | 새 음성 클로닝 | API Key |
| GET | `/api/v1/health` | 서버 상태 확인 | None |

#### POST /api/v1/tts/synthesize

```json
// Request
{
  "text": "안녕하세요, 지드래곤입니다.",
  "voice_id": "gd-default",
  "language": "ko",
  "speed": 1.0,
  "format": "wav"
}

// Response: audio/wav binary
// Headers:
//   X-Audio-Duration: 2.5
//   X-Processing-Time: 650
```

#### GET /api/v1/tts/voices

```json
// Response
{
  "voices": [
    {
      "id": "gd-default",
      "name": "G-Dragon (기본)",
      "mode": "x_vector",
      "description": "X-Vector 모드, ref_text 불필요"
    },
    {
      "id": "gd-icl",
      "name": "G-Dragon (ICL)",
      "mode": "icl",
      "description": "높은 품질, ref_text 필요"
    }
  ]
}
```

### WebSocket Endpoint

#### WS /ws/tts/stream

**Client → Server (JSON):**
```json
{
  "type": "synthesize",
  "text": "안녕하세요",
  "voice_id": "gd-default"
}
```

**Server → Client:**
```json
{"type": "start", "timestamp": 1709012345.123}
```
```
[Binary: PCM audio chunk, 16-bit, 24kHz, mono]
```
```json
{"type": "end", "duration": 2.5, "chunks": 25}
```

---

## Streaming Sequence

```
Client                    Server                    TTS Engine
  │                         │                           │
  │──── WS Connect ────────▶│                           │
  │◀─── Connection OK ──────│                           │
  │                         │                           │
  │──── {synthesize} ──────▶│                           │
  │     text:"안녕하세요"    │                           │
  │                         │──── generate_voice_clone ▶│
  │                         │     (cached prompt)       │
  │                         │                           │
  │◀─── {type:"start"} ─────│                           │
  │                         │◀─── audio_chunk[0] ───────│ ~100ms TTFA
  │◀─── [PCM 2400 samples] ─│                           │
  │                         │◀─── audio_chunk[1] ───────│
  │◀─── [PCM 2400 samples] ─│                           │
  │         ...             │          ...              │
  │                         │◀─── audio_chunk[N] ───────│
  │◀─── [PCM 2400 samples] ─│                           │
  │◀─── {type:"end"} ───────│                           │
  │                         │                           │
```

**청크 크기:** 2400 samples = 100ms @ 24kHz
**예상 TTFA:** 100-150ms (워밍업 후)

---

## Performance Optimization

### 최적화 기법

| 기법 | 효과 | 구현 |
|------|------|------|
| **프롬프트 캐싱** | -20ms/요청 | 서버 시작 시 GD 음성 사전 계산 |
| **모델 워밍업** | -200ms (첫 요청) | 더미 추론으로 CUDA 커널 컴파일 |
| **FlashAttention 2** | -30% VRAM | 어텐션 메모리 최적화 |
| **bfloat16** | 50% VRAM 절약 | 정밀도/성능 균형 |
| **청크 스트리밍** | 낮은 TTFA | 100ms 청크 단위 전송 |

### 예상 성능

| 지표 | 목표 | 테스트 결과 |
|------|------|-------------|
| 모델 로딩 | <10s | 6.8초 ✅ |
| VRAM 사용 | <8GB | 3.91GB ✅ |
| RTF | <1.0 | 0.59-0.83 ✅ |
| TTFA | ~100ms | 측정 예정 |
| 전체 레이턴시 | <500ms | 595-685ms (개선 필요) |

### 동시성 처리

```python
# 단일 GPU 환경: 순차 처리 + 큐잉
class TTSQueue:
    def __init__(self):
        self.queue = asyncio.Queue(maxsize=10)
        self.processing = False

    async def enqueue(self, request):
        await self.queue.put(request)
        return await request.wait()
```

**확장 전략:**
- Phase 1: 단일 GPU, 순차 처리
- Phase 2: 요청 큐 + 우선순위
- Phase 3: 다중 GPU 복제

---

## Project Structure

```
/home/nexus/connect/server/tts_server/
├── main.py                 # FastAPI 앱 진입점
├── config.py               # 설정 (환경변수, 상수)
├── requirements.txt        # 의존성
├── .env                    # 환경 변수 (gitignore)
│
├── api/
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── tts.py          # POST /api/v1/tts/synthesize
│   │   ├── voices.py       # GET /api/v1/tts/voices
│   │   └── health.py       # GET /api/v1/health
│   └── websocket/
│       ├── __init__.py
│       └── stream.py       # WS /ws/tts/stream
│
├── services/
│   ├── __init__.py
│   ├── tts_engine.py       # TTSEngine 클래스
│   ├── model_manager.py    # 모델 로딩/캐싱
│   ├── voice_manager.py    # 음성 프롬프트 관리
│   └── streaming.py        # 청크 스트리밍 핸들러
│
├── models/
│   ├── __init__.py
│   ├── request.py          # Pydantic 요청 스키마
│   └── response.py         # Pydantic 응답 스키마
│
├── core/
│   ├── __init__.py
│   ├── exceptions.py       # 커스텀 예외
│   └── connection.py       # WebSocket 연결 관리
│
├── data/
│   ├── voices/             # GD 음성 샘플 (.wav)
│   │   └── gd-default.wav
│   └── prompts/            # 캐시된 프롬프트 (.pkl)
│       └── gd-default.pkl
│
└── tests/
    ├── __init__.py
    ├── test_tts.py         # REST API 테스트
    ├── test_websocket.py   # WebSocket 테스트
    └── test_streaming.py   # 스트리밍 테스트
```

---

## Configuration

### Application Lifespan (FastAPI 권장 패턴)

```python
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    FastAPI 0.95+ 권장 패턴 (on_event deprecated 대체)
    """
    # === STARTUP ===
    logger.info("Starting TTS Server...")

    # 1. 모델 로딩
    app.state.model = await model_manager.load_model()

    # 2. 음성 프롬프트 캐싱
    app.state.voice_prompts = await voice_manager.load_prompts()

    # 3. 모델 워밍업 (CUDA 커널 컴파일)
    if settings.WARMUP_ON_START:
        await tts_engine.warmup(app.state.model)

    logger.info("TTS Server ready!")

    yield  # 서버 실행

    # === SHUTDOWN ===
    logger.info("Shutting down TTS Server...")

    # 1. 활성 연결 정리
    await connection_manager.close_all()

    # 2. 진행 중인 작업 취소
    await tts_queue.cancel_all()

    # 3. GPU 메모리 해제
    await model_manager.unload_model()

    logger.info("TTS Server shutdown complete.")

# FastAPI 앱 생성
app = FastAPI(
    title="GD Voice Clone TTS Server",
    version="1.0.0",
    lifespan=lifespan,  # lifespan 패턴 사용
)
```

### Settings

```python
# config.py
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # Security
    API_KEYS: List[str] = []  # 쉼표로 구분된 API 키 목록
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Rate Limiting
    RATE_LIMIT_SYNTHESIZE: int = 10  # requests per minute
    RATE_LIMIT_WEBSOCKET: int = 30   # messages per minute
    RATE_LIMIT_WINDOW: int = 60      # seconds

    # Model
    MODEL_NAME: str = "davinci-voice/davinci-voice-12Hz-1.7B-Base"
    DEVICE: str = "cuda:0"
    DTYPE: str = "bfloat16"
    ATTN_IMPL: str = "flash_attention_2"

    # Voice
    DEFAULT_VOICE_ID: str = "gd-default"
    VOICE_SAMPLES_DIR: str = "data/voices"
    VOICE_PROMPTS_DIR: str = "data/prompts"

    # Audio
    SAMPLE_RATE: int = 24000
    CHUNK_SIZE: int = 2400  # 100ms @ 24kHz
    MAX_TEXT_LENGTH: int = 500

    # Performance
    WARMUP_ON_START: bool = True
    REQUEST_TIMEOUT: int = 30
    MAX_CONCURRENT_REQUESTS: int = 10

    # Graceful Shutdown
    SHUTDOWN_TIMEOUT: int = 30  # seconds to wait for active requests

    class Config:
        env_file = ".env"
        env_prefix = "TTS_"

settings = Settings()
```

### 환경 변수 (.env)

```bash
# Server
TTS_HOST=0.0.0.0
TTS_PORT=8000
TTS_DEBUG=false

# Security
TTS_API_KEYS=key1,key2,key3
TTS_CORS_ORIGINS=http://localhost:3000,https://app.example.com

# Rate Limiting
TTS_RATE_LIMIT_SYNTHESIZE=10
TTS_RATE_LIMIT_WEBSOCKET=30

# Model
TTS_MODEL_NAME=davinci-voice/davinci-voice-12Hz-1.7B-Base
TTS_DEVICE=cuda:0
TTS_WARMUP_ON_START=true

# Graceful Shutdown
TTS_SHUTDOWN_TIMEOUT=30
```

### Graceful Shutdown

```python
# core/shutdown.py
import signal
import asyncio

class GracefulShutdown:
    """Graceful shutdown handler for active connections and requests."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.shutdown_event = asyncio.Event()

    def setup_signals(self):
        """Register signal handlers for graceful shutdown."""
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self.handle_signal, sig)

    def handle_signal(self, sig):
        logger.info(f"Received signal {sig.name}, initiating graceful shutdown...")
        self.shutdown_event.set()

    async def wait_for_shutdown(self):
        """Wait for shutdown signal with timeout."""
        await self.shutdown_event.wait()

        # 활성 요청 완료 대기
        logger.info(f"Waiting {self.timeout}s for active requests to complete...")

        try:
            async with asyncio.timeout(self.timeout):
                await connection_manager.wait_all_closed()
        except asyncio.TimeoutError:
            logger.warning("Shutdown timeout, forcing close remaining connections")
            await connection_manager.force_close_all()
```

---

## ADRs (Architecture Decision Records)

### ADR-001: 스트리밍 프로토콜

| | |
|---|---|
| **Status** | Accepted |
| **Decision** | WebSocket |
| **Alternatives** | SSE, HTTP/2 Server Push |
| **Rationale** | 양방향 통신 (인터럽트), 바이너리 데이터 효율적 전송, 실시간 통화 확장 대비 |

### ADR-002: 오디오 포맷

| | |
|---|---|
| **Status** | Accepted |
| **Decision** | PCM 16-bit 24kHz (스트리밍), WAV (REST) |
| **Alternatives** | Opus, MP3, AAC |
| **Rationale** | PCM은 인코딩 오버헤드 없어 최소 레이턴시, 대역폭 필요시 Opus 추후 추가 |

### ADR-003: 프롬프트 캐싱 전략

| | |
|---|---|
| **Status** | Accepted |
| **Decision** | 서버 시작 시 사전 계산 + 메모리 캐시 |
| **Alternatives** | 요청 시 계산, Redis 캐시 |
| **Rationale** | GD 음성 고정이므로 캐싱 효과 극대화, 메모리 ~100MB로 미미 |

### ADR-004: 동시성 모델

| | |
|---|---|
| **Status** | Accepted |
| **Decision** | 단일 추론 + asyncio 요청 큐 |
| **Alternatives** | 다중 프로세스, GPU 멀티스트림 |
| **Rationale** | GPU는 한 번에 하나의 추론이 효율적, 확장 시 다중 GPU로 전환 |

### ADR-005: 앱 라이프사이클 관리

| | |
|---|---|
| **Status** | Accepted |
| **Decision** | FastAPI lifespan 컨텍스트 매니저 |
| **Alternatives** | @app.on_event("startup/shutdown") (deprecated) |
| **Rationale** | FastAPI 0.95+ 권장 패턴, 리소스 정리 보장, 타입 안전성 |

### ADR-006: WebSocket 인증 방식

| | |
|---|---|
| **Status** | Accepted |
| **Decision** | Query parameter API key (?api_key=xxx) |
| **Alternatives** | 첫 메시지 인증, Cookie 인증 |
| **Rationale** | WebSocket은 HTTP 헤더 사용 불가, 연결 전 인증으로 빠른 거부 가능 |

### ADR-007: Rate Limiting 알고리즘

| | |
|---|---|
| **Status** | Accepted |
| **Decision** | Token Bucket (인메모리) |
| **Alternatives** | Sliding Window, Redis Rate Limit |
| **Rationale** | 단일 서버 환경에서 성능 최적, 버스트 허용, 추후 Redis로 확장 가능 |

---

## Implementation Phases

### Phase 0: 스트리밍 API 검증 (Pre-Implementation)

> ⚠️ **CRITICAL**: qwen-tts 라이브러리의 스트리밍 API 존재 여부 확인 필요

- [ ] `model.generate_voice_clone()` 스트리밍 지원 확인
- [ ] AsyncGenerator 반환 가능 여부 테스트
- [ ] 스트리밍 미지원 시 대안 설계 (전체 생성 → 청크 분할)

### Phase 1: MVP REST API (Day 1)

- [x] 모델 로딩 테스트
- [x] 음성 클로닝 테스트
- [ ] FastAPI 서버 기본 구조 (lifespan 패턴)
- [ ] POST /api/v1/tts/synthesize
- [ ] GET /api/v1/tts/voices
- [ ] GET /api/v1/health
- [ ] 프롬프트 캐싱
- [ ] Error Response Schema 구현
- [ ] CORS 설정

### Phase 2: 보안 및 인증 (Day 2)

- [ ] API Key 인증 미들웨어
- [ ] Rate Limiting 구현
- [ ] WebSocket 인증 (query param)
- [ ] Global Exception Handler
- [ ] Request ID 로깅

### Phase 3: WebSocket 스트리밍 (Day 3-4)

- [ ] WebSocket 연결 관리 (ConnectionManager)
- [ ] WS /ws/tts/stream 엔드포인트
- [ ] 청크 단위 오디오 전송
- [ ] WebSocketDisconnect 핸들링
- [ ] 연결 타임아웃
- [ ] 진행 중 작업 취소 (클라이언트 종료 시)

### Phase 4: 최적화 및 운영 (Day 5)

- [ ] 모델 워밍업
- [ ] 요청 큐잉
- [ ] 동시성 제한
- [ ] Graceful Shutdown 구현
- [ ] 로깅/모니터링
- [ ] 부하 테스트

---

## Risk Assessment

| 위험 | 확률 | 영향 | 대응 |
|------|------|------|------|
| **qwen-tts 스트리밍 미지원** | 중 | 높음 | 전체 생성 후 청크 분할 (레이턴시 증가) |
| **GPU OOM (동시 요청)** | 중 | 높음 | 요청 큐 + 순차 처리 + Rate Limiting |
| **WebSocket 연결 끊김** | 낮음 | 중 | WebSocketDisconnect 핸들링, 작업 취소 |
| **TTFA 목표 미달** | 중 | 중 | 청크 크기 조정, 추가 최적화 |
| **음성 품질 저하** | 낮음 | 중 | ICL 모드 사용, 더 긴 ref_audio |
| **API Key 유출** | 낮음 | 높음 | Rate Limiting, 키 로테이션, 모니터링 |
| **DoS 공격** | 중 | 중 | Rate Limiting, CORS, 연결 수 제한 |
| **서버 장애 시 데이터 손실** | 낮음 | 중 | Graceful Shutdown, 작업 상태 보존 |

### 모니터링 지표

```python
# Prometheus 메트릭 (추후 추가)
tts_requests_total          # 총 요청 수
tts_request_duration_seconds # 요청 처리 시간
tts_ttfa_seconds            # Time To First Audio
tts_active_connections      # 활성 WebSocket 연결
tts_queue_size              # 대기 큐 크기
tts_gpu_memory_bytes        # GPU 메모리 사용량
```

---

## Verification Checklist

구현 전 검증 항목 (/da:verify 결과 반영):

### Critical (즉시 확인 필요)
- [ ] **PERF-001**: qwen-tts 스트리밍 API 존재 확인 (Phase 0)

### High Priority (Phase 1-2에서 구현)
- [x] **ARCH-001**: lifespan 패턴 적용 (on_event deprecated 대체)
- [x] **API-001**: WebSocket 인증 설계 (query param 방식)
- [x] **API-002**: WebSocketDisconnect 예외 처리 설계
- [x] **SEC-001**: Rate Limiting 설계 (Token Bucket)
- [x] **SEC-002**: API Key 인증 설계
- [x] **PERF-002**: Graceful Shutdown 설계
- [x] **BP-001**: Error Response Schema 정의

### Medium Priority (Phase 3-4에서 구현)
- [x] **CORS-001**: CORS 설정 추가
- [ ] **TEST-001**: 스트리밍 통합 테스트 작성
- [ ] **DOC-001**: API 문서화 (OpenAPI)

---

*Last Updated: 2026-02-27*
*Author: Claude Code (da:system)*
*Verified: /da:verify 검증 완료 - 14개 이슈 반영*
