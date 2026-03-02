# GD Voice TTS API Integration Guide

## Overview

GD Voice TTS Server는 G-Dragon 음성으로 텍스트를 음성으로 변환하는 API를 제공합니다.

**Base URL**: `https://crossconnect.ngrok.app`

## Authentication

API 키가 설정된 경우 모든 요청에 `X-API-Key` 헤더가 필요합니다.

```
X-API-Key: your-api-key-here
```

---

## Endpoints

### 1. Health Check

서버 상태를 확인합니다.

```http
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "gpu_available": true,
  "gpu_memory_used_gb": 7.8,
  "voices_cached": 2
}
```

---

### 2. 기본 TTS 합성

텍스트를 GD 음성으로 변환합니다.

```http
POST /api/v1/tts/synthesize
Content-Type: application/json
```

**Request Body:**
```json
{
  "text": "안녕하세요, 지드래곤입니다.",
  "mode": "finetuned",
  "voice_id": "gd-default",
  "format": "wav"
}
```

**Parameters:**

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `text` | string | (필수) | 합성할 텍스트 (최대 500자) |
| `mode` | string | `"auto"` | 모델 모드: `finetuned`, `clone`, `auto` |
| `format` | string | `"wav"` | 출력 포맷: `wav`, `pcm` |

**Mode 설명:**

| 모드 | 모델 | 특징 |
|------|------|------|
| `finetuned` | GD v5 학습 모델 | 최고 품질, 빠름, 권장 |
| `clone` | Base 모델 + ICL | ICL 방식 고품질 음성 복제 |
| `auto` | 자동 선택 | finetuned 우선, 없으면 clone 사용 |

**Response:**
- Content-Type: `audio/wav` 또는 `audio/pcm`
- Binary audio data

**Response Headers:**
```
X-Audio-Duration: 2.345
X-Processing-Time: 890
X-Sample-Rate: 24000
X-Model-Mode: finetuned
X-Request-ID: abc12345
```

---

### 3. 음성 목록 조회

사용 가능한 음성 목록을 조회합니다.

```http
GET /api/v1/tts/voices
```

**Response:**
```json
{
  "voices": [
    {
      "id": "gd-clone",
      "name": "G-Dragon (ICL Clone)",
      "mode": "icl",
      "description": "ICL 모드 음성 복제 (고품질)"
    }
  ]
}
```

> Note: clone 모드에서는 ICL 방식만 사용합니다. finetuned 모드를 권장합니다.

---

## Code Examples

### Python

```python
import requests

BASE_URL = "https://crossconnect.ngrok.app"

# TTS 합성
response = requests.post(
    f"{BASE_URL}/api/v1/tts/synthesize",
    json={
        "text": "안녕하세요, 지드래곤입니다.",
        "mode": "finetuned",
        "format": "wav"
    },
    headers={"X-API-Key": "your-api-key"}  # 필요시
)

if response.status_code == 200:
    with open("output.wav", "wb") as f:
        f.write(response.content)

    # 메타데이터 확인
    print(f"Duration: {response.headers.get('X-Audio-Duration')}s")
    print(f"Processing: {response.headers.get('X-Processing-Time')}ms")
```

### JavaScript/TypeScript

```typescript
const BASE_URL = "https://crossconnect.ngrok.app";

async function synthesize(text: string): Promise<Blob> {
  const response = await fetch(`${BASE_URL}/api/v1/tts/synthesize`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      // "X-API-Key": "your-api-key"  // 필요시
    },
    body: JSON.stringify({
      text,
      mode: "finetuned",
      format: "wav"
    })
  });

  if (!response.ok) {
    throw new Error(`TTS failed: ${response.status}`);
  }

  // 메타데이터
  const duration = response.headers.get("X-Audio-Duration");
  const processingTime = response.headers.get("X-Processing-Time");
  console.log(`Duration: ${duration}s, Processing: ${processingTime}ms`);

  return response.blob();
}

// 사용 예시
const audioBlob = await synthesize("안녕하세요!");
const audioUrl = URL.createObjectURL(audioBlob);
const audio = new Audio(audioUrl);
audio.play();
```

### Swift (iOS)

```swift
import Foundation
import AVFoundation

class TTSService {
    static let baseURL = "https://crossconnect.ngrok.app"

    func synthesize(text: String) async throws -> Data {
        guard let url = URL(string: "\(Self.baseURL)/api/v1/tts/synthesize") else {
            throw URLError(.badURL)
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        // request.setValue("your-api-key", forHTTPHeaderField: "X-API-Key")

        let body: [String: Any] = [
            "text": text,
            "mode": "finetuned",
            "format": "wav"
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }

        // 메타데이터
        if let duration = httpResponse.value(forHTTPHeaderField: "X-Audio-Duration") {
            print("Duration: \(duration)s")
        }

        return data
    }

    func playAudio(data: Data) {
        do {
            let player = try AVAudioPlayer(data: data)
            player.play()
        } catch {
            print("Audio playback error: \(error)")
        }
    }
}
```

### Kotlin (Android)

```kotlin
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

class TTSService {
    companion object {
        const val BASE_URL = "https://crossconnect.ngrok.app"
    }

    private val client = OkHttpClient()

    suspend fun synthesize(text: String): ByteArray {
        val json = JSONObject().apply {
            put("text", text)
            put("mode", "finetuned")
            put("format", "wav")
        }

        val request = Request.Builder()
            .url("$BASE_URL/api/v1/tts/synthesize")
            .post(json.toString().toRequestBody("application/json".toMediaType()))
            // .addHeader("X-API-Key", "your-api-key")
            .build()

        val response = client.newCall(request).execute()

        if (!response.isSuccessful) {
            throw Exception("TTS failed: ${response.code}")
        }

        // 메타데이터
        val duration = response.header("X-Audio-Duration")
        val processingTime = response.header("X-Processing-Time")
        println("Duration: ${duration}s, Processing: ${processingTime}ms")

        return response.body?.bytes() ?: throw Exception("Empty response")
    }
}
```

### React Native

```typescript
import { Audio } from 'expo-av';

const BASE_URL = "https://crossconnect.ngrok.app";

export async function synthesizeAndPlay(text: string): Promise<void> {
  const response = await fetch(`${BASE_URL}/api/v1/tts/synthesize`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      text,
      mode: "finetuned",
      format: "wav"
    })
  });

  if (!response.ok) {
    throw new Error(`TTS failed: ${response.status}`);
  }

  const blob = await response.blob();
  const uri = URL.createObjectURL(blob);

  const { sound } = await Audio.Sound.createAsync({ uri });
  await sound.playAsync();
}
```

---

## Error Responses

```json
{
  "error": "ERROR_CODE",
  "message": "Human readable message",
  "detail": "Additional details",
  "request_id": "abc12345"
}
```

**Error Codes:**
| 코드 | HTTP Status | 설명 |
|------|-------------|------|
| `UNAUTHORIZED` | 401 | API 키 누락 또는 잘못됨 |
| `RATE_LIMITED` | 429 | 요청 한도 초과 |
| `TEXT_TOO_LONG` | 400 | 텍스트 500자 초과 |
| `VOICE_NOT_FOUND` | 400 | 존재하지 않는 voice_id |
| `MODEL_ERROR` | 500 | 모델 합성 실패 |

---

## Rate Limits

- TTS 합성: **10 requests/minute** per client
- 일반 요청: **60 requests/minute** per client

429 응답 시 `Retry-After` 헤더를 확인하세요.

---

## Best Practices

1. **모드 선택**: 품질 우선이면 `finetuned`, 유연성 우선이면 `clone` 사용
2. **텍스트 길이**: 500자 이하로 유지, 긴 텍스트는 문장 단위로 분할
3. **에러 처리**: 429 에러 시 `Retry-After` 헤더 값만큼 대기 후 재시도
4. **캐싱**: 동일 텍스트에 대한 응답은 클라이언트에서 캐싱 권장

---

## Support

- API Documentation: https://crossconnect.ngrok.app/docs
- Swagger UI: https://crossconnect.ngrok.app/redoc
