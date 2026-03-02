# GD Voice Call API Documentation

실시간 음성통화 WebSocket API - G-Dragon 음성 클론 TTS

## 주요 특징

- **세션 기반 대화 격리**: 각 WebSocket 연결(client_id)별로 독립적인 대화 기록 유지
- **동시 접속 지원**: 여러 사용자가 동시에 접속해도 대화가 섞이지 않음
- **자동 세션 정리**: 연결 종료 시 세션 메모리 자동 해제

## 연결 정보

| 항목 | 값 |
|------|-----|
| 프로토콜 | WebSocket |
| 엔드포인트 | `ws://host:5002/ws/voice/call` |
| 보안 연결 | `wss://host:5002/ws/voice/call` |
| 인증 | Query parameter: `?api_key=YOUR_KEY` |

## 빠른 시작

### Python
```python
import asyncio
import websockets
import json
import base64

async def voice_chat():
    async with websockets.connect("ws://localhost:5002/ws/voice/call") as ws:
        # 1. 연결 확인
        msg = await ws.recv()
        print(json.loads(msg))  # {"type": "connected", ...}

        # 2. 음성 전송 (PCM 16-bit 16kHz)
        with open("question.wav", "rb") as f:
            audio = f.read()

        await ws.send(json.dumps({
            "type": "voice_input",
            "audio": base64.b64encode(audio).decode(),
            "voice_id": "gd-icl"
        }))

        # 3. 응답 수신
        while True:
            msg = await ws.recv()
            if isinstance(msg, bytes):
                print(f"Audio chunk: {len(msg)} bytes")
            else:
                data = json.loads(msg)
                print(data)
                if data["type"] == "response_end":
                    break

asyncio.run(voice_chat())
```

### JavaScript
```javascript
const ws = new WebSocket("ws://localhost:5002/ws/voice/call");

ws.onopen = () => {
    console.log("Connected");
};

ws.onmessage = (event) => {
    if (event.data instanceof Blob) {
        // Binary audio data
        console.log("Audio chunk:", event.data.size, "bytes");
    } else {
        const data = JSON.parse(event.data);
        console.log(data);
    }
};

// Send audio
function sendAudio(base64Audio) {
    ws.send(JSON.stringify({
        type: "voice_input",
        audio: base64Audio,
        voice_id: "gd-icl"
    }));
}
```

---

## 메시지 프로토콜

### Client → Server

#### 1. 음성 입력
```json
{
    "type": "voice_input",
    "audio": "<base64 encoded PCM 16-bit 16kHz>",
    "voice_id": "gd-icl"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| type | string | ✓ | `"voice_input"` |
| audio | string | ✓ | Base64 인코딩된 PCM 오디오 |
| voice_id | string | | TTS 음성 ID (기본: `"gd-default"`) |

**오디오 포맷:**
- PCM 16-bit signed little-endian
- 16000 Hz (mono)
- 최대 30초

#### 2. 응답 중단
```json
{"type": "interrupt"}
```

#### 3. 대화 초기화
```json
{"type": "reset"}
```

#### 4. 핑
```json
{"type": "ping"}
```

---

### Server → Client

#### 1. 연결 확인
```json
{
    "type": "connected",
    "client_id": "abc123",
    "sample_rate_in": 16000,
    "sample_rate_out": 24000,
    "max_audio_length": 30
}
```

#### 2. STT 결과 (음성 인식)
```json
{
    "type": "transcription",
    "text": "안녕하세요",
    "language": "ko",
    "confidence": 0.95
}
```

#### 3. LLM 응답 시작
```json
{"type": "response_start"}
```

#### 4. LLM 텍스트 청크 (스트리밍)
```json
{
    "type": "response_text",
    "text": "야 뭐야",
    "is_final": false
}
```

#### 5. TTS 오디오 청크
- **바이너리 메시지** (JSON 아님)
- PCM 16-bit signed little-endian
- 24000 Hz mono
- 청크 크기: 약 2400 bytes (100ms)

#### 6. 응답 완료
```json
{
    "type": "response_end",
    "metrics": {
        "stt_ms": 150,
        "llm_ttfa_ms": 800,
        "tts_ttfa_ms": 1200,
        "total_ms": 5000,
        "audio_duration": 3.5,
        "user_text": "안녕하세요",
        "response_text": "야 뭐야 반가워"
    }
}
```

#### 7. 중단됨
```json
{"type": "interrupted"}
```

#### 8. 대화 초기화 완료
```json
{"type": "reset_complete"}
```

#### 9. 퐁
```json
{"type": "pong"}
```

#### 10. 에러
```json
{
    "type": "error",
    "code": "RATE_LIMITED",
    "message": "Rate limit exceeded",
    "retry_after": 60
}
```

**에러 코드:**
| 코드 | 설명 |
|------|------|
| `4001` | 인증 실패 |
| `4002` | Rate limit 초과 |
| `4003` | 오디오 길이 초과 |
| `4004` | 파이프라인 오류 |
| `4005` | 기능 비활성화 |
| `STT_FAILED` | 음성 인식 실패 |
| `STT_EMPTY` | 인식된 음성 없음 |
| `LLM_FAILED` | LLM 응답 실패 |

---

## 음성 포맷

### 입력 (Client → Server)
| 항목 | 값 |
|------|-----|
| 포맷 | PCM (Raw) |
| 비트 깊이 | 16-bit signed little-endian |
| 샘플레이트 | 16000 Hz |
| 채널 | Mono |
| 최대 길이 | 30초 |

### 출력 (Server → Client)
| 항목 | 값 |
|------|-----|
| 포맷 | PCM (Raw) |
| 비트 깊이 | 16-bit signed little-endian |
| 샘플레이트 | 24000 Hz |
| 채널 | Mono |

---

## 음성 ID

| ID | 설명 | 품질 | 속도 |
|----|------|------|------|
| `gd-icl` | In-Context Learning 방식 | 높음 | 느림 |
| `gd-default` | X-Vector 방식 | 중간 | 빠름 |

---

## Rate Limiting

- WebSocket 메시지: 30회/분
- 초과 시 `error` 메시지와 함께 `retry_after` 반환

---

## 예제 코드

### Python Client (전체)

`examples/voice_client.py` 참조

```bash
# 설치
pip install websockets

# 실행
python examples/voice_client.py --audio question.wav --output response.wav

# 옵션
--server ws://localhost:5002/ws/voice/call  # 서버 URL
--api-key YOUR_KEY                          # API 키
--voice gd-icl                              # 음성 ID
```

### 오디오 변환

```python
import wave
import struct

# WAV → PCM
def wav_to_pcm(wav_path):
    with wave.open(wav_path, 'rb') as wf:
        return wf.readframes(wf.getnframes())

# PCM → WAV
def pcm_to_wav(pcm_data, wav_path, sample_rate=24000):
    with wave.open(wav_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
```

---

## 외부 접속 (ngrok)

```bash
# ngrok 설정 (ngrok.yml)
tunnels:
  tts-api:
    addr: 5002
    proto: http

# 실행
ngrok start tts-api

# 접속
wss://xxxx.ngrok-free.app/ws/voice/call
```

---

## 문제 해결

### 연결 안됨
1. 서버 상태 확인: `curl http://localhost:5002/api/v1/health`
2. 포트 확인: `lsof -i:5002`
3. 방화벽 확인

### 음성 인식 안됨
1. 오디오 포맷 확인 (16kHz, 16-bit, mono)
2. 오디오 길이 확인 (30초 이하)
3. 노이즈 제거된 음성 사용

### 응답이 짧게 끊김
1. 서버 로그 확인: `tail -f /tmp/tts_server.log`
2. `finish_reason: MAX_TOKENS` → thinking_config 확인
