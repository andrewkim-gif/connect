# AIRI + GD Voice 통합 연구 보고서

## 1. AIRI 프로젝트 개요

### 프로젝트 정체성
- **목표**: Neuro-sama 스타일의 AI VTuber/디지털 컴패니언 플랫폼
- **핵심 특징**: 웹 기술 기반 (WebGPU, WebAudio, WebSocket, WASM)
- **지원 플랫폼**: Web, Desktop (Electron), Mobile (Capacitor)

### 기술 스택
```yaml
Frontend:
  - Vue 3 + Pinia + VueUse
  - TypeScript
  - UnoCSS
  - Vite

Backend/Services:
  - Node.js
  - Discord/Telegram 봇
  - Minecraft/Factorio 에이전트

Audio Pipeline:
  - WebAudio API
  - VAD (Voice Activity Detection)
  - Streaming TTS/STT

3D/2D Avatar:
  - VRM (Three.js)
  - Live2D
```

---

## 2. AIRI 핵심 아키텍처 분석

### 2.1 Speech Pipeline (`packages/pipelines-audio`)
```
Text Input → TTS Chunker → TTS Engine → Playback Manager → Audio Output
              ↓
         TextToken Stream → Segment → TTS Request → Audio Buffer
```

#### 핵심 컴포넌트
1. **SpeechPipeline**: 텍스트 → 오디오 변환 파이프라인
2. **Intent System**: 발화 우선순위 및 큐 관리
3. **TTS Chunker**: 스트리밍 텍스트 청킹 (boost, hard, soft punctuation)
4. **Playback Manager**: 오디오 재생 스케줄링

### 2.2 TTS Provider 시스템 (`packages/stage-ui/src/stores/providers.ts`)
```typescript
// 지원 TTS 프로바이더
- ElevenLabs (primary)
- Aliyun (Azure)
- Web Speech API (browser native)
- OpenAI Compatible
- 그 외 다수
```

### 2.3 STT 시스템
- Client-side speech recognition (Web Speech API)
- Server-side transcription providers (Whisper, Deepgram 등)

---

## 3. GD Voice 시스템 현황

### 현재 구조
```
                    ┌─────────────────────────────────────────┐
                    │           GD Voice Server               │
                    │         (tts_server @ :5001)            │
                    │                                         │
Voice Input ───────►│  STT ───► LLM (Gemini) ───► TTS        │
                    │  (Whisper)   (G-Dragon)    (Custom)     │
                    │                                         │
                    │         WebSocket Streaming             │
                    └───────────────┬─────────────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────────────┐
                    │        Web Client (index.html)          │
                    │       (tts_test_app @ :5002)            │
                    │                                         │
                    │  - Voice Activity Detection             │
                    │  - Barge-in Detection                   │
                    │  - GD Initiative Timer                  │
                    │  - Audio Playback                       │
                    └─────────────────────────────────────────┘
```

### GD Voice 핵심 기능
1. **실시간 음성 대화**: STT → LLM → TTS 파이프라인
2. **끼어들기 (Barge-in)**: 사용자가 GD 발화 중 끼어들기
3. **GD Initiative**: 5초 침묵 시 GD가 먼저 말 걸기
4. **문장 단위 TTS 청킹**: 자연스러운 운율 유지

---

## 4. 통합 시나리오 분석

### 시나리오 A: GD Voice를 AIRI TTS Provider로 통합
```
목표: AIRI의 TTS 프로바이더로 GD Voice 백엔드 연결

장점:
- AIRI의 풍부한 UI/UX (VRM, Live2D 아바타)
- 기존 GD 페르소나 + TTS 유지
- WebSocket 기반 실시간 스트리밍

구현:
1. AIRI Provider 인터페이스 구현
2. GD Voice 백엔드를 unspeech 호환 엔드포인트로 변환
3. AIRI에서 "GD Voice" 프로바이더 선택 가능
```

### 시나리오 B: AIRI UI를 GD Voice 프론트엔드로 교체
```
목표: GD Voice 백엔드 + AIRI 프론트엔드

장점:
- 고급 아바타 시스템 (VRM, Live2D)
- 성숙한 오디오 파이프라인
- 다양한 플랫폼 지원 (Web, Desktop, Mobile)

구현:
1. AIRI의 chat.ts를 GD WebSocket으로 교체
2. Audio pipeline을 GD 스트리밍에 연결
3. G-Dragon 캐릭터 프로필 생성
```

### 시나리오 C: 하이브리드 통합
```
목표: 양쪽 강점 결합

GD Voice 백엔드:
- G-Dragon 페르소나 LLM
- 한국어 특화 TTS
- 세션 기반 대화 관리

AIRI 프론트엔드:
- VRM/Live2D 아바타 렌더링
- Speech Pipeline 오케스트레이션
- Lip-sync 및 표정 제어

통합 포인트:
- AIRI → GD Voice: WebSocket 메시지
- GD Voice → AIRI: 오디오 스트림 + 텍스트 이벤트
```

---

## 5. 기술적 통합 포인트

### 5.1 TTS Provider 통합 (unspeech 방식)
```typescript
// GD Voice를 unspeech 호환 프로바이더로 래핑
interface GDVoiceProvider {
  speech: async (text: string, options?: {
    voice_id?: string
    session_id?: string
  }) => Promise<ArrayBuffer>

  speechStream: async function* (text: string, options?: {
    voice_id?: string
    session_id?: string
  }) => AsyncGenerator<Uint8Array>
}

// AIRI providers.ts에 GD Voice 추가
const gdVoiceProvider: ProviderMetadata = {
  id: 'gd-voice',
  category: 'speech',
  tasks: ['tts'],
  name: 'GD Voice',
  createProvider: (config) => {
    return createGDVoiceProvider({
      baseUrl: config.baseUrl || 'ws://localhost:5001',
      sessionId: config.sessionId || 'default'
    })
  }
}
```

### 5.2 WebSocket 브릿지
```typescript
// AIRI Speech Runtime ↔ GD Voice WebSocket
class GDVoiceBridge {
  private ws: WebSocket

  async speak(text: string): Promise<AudioBuffer> {
    return new Promise((resolve) => {
      this.ws.send(JSON.stringify({ type: 'voice_input', audio: text }))
      // 바이너리 오디오 수신 핸들링
    })
  }

  interrupt(reason: string) {
    this.ws.send(JSON.stringify({ type: 'interrupt', reason }))
  }
}
```

### 5.3 캐릭터 시스템 통합
```yaml
# AIRI Character Profile for G-Dragon
character_id: "gd-dragon"
name: "G-Dragon"
persona:
  system_prompt: "당신은 G-Dragon입니다..."
  voice_id: "gd-default"

voice_settings:
  provider: "gd-voice"
  streaming: true

avatar:
  type: "vrm" # 또는 "live2d"
  model_url: "assets/gd-avatar.vrm"
```

---

## 6. 권장 통합 전략

### Phase 1: 프로토타입 (1-2주)
```
1. GD Voice 백엔드에 REST API 추가
   - POST /v1/audio/speech (OpenAI 호환)
   - GET /v1/voices (음성 목록)

2. AIRI에 GD Voice Provider 추가
   - packages/stage-ui/src/stores/providers/gd-voice/

3. 기본 연동 테스트
```

### Phase 2: 심화 통합 (2-4주)
```
1. WebSocket 양방향 스트리밍
   - AIRI Speech Intent → GD Voice
   - GD Voice 오디오 → AIRI Playback

2. Barge-in / GD Initiative 연동
   - AIRI의 Intent 시스템과 통합

3. 캐릭터 프로필 시스템 연동
```

### Phase 3: 프로덕션 (4-8주)
```
1. VRM 아바타 제작 (G-Dragon 모델)
2. Lip-sync 최적화
3. 모바일/데스크탑 앱 배포
4. 멀티 플랫폼 테스트
```

---

## 7. 코드 수정 예시

### GD Voice 백엔드 확장 (REST API)
```python
# tts_server/api/rest/tts.py
from fastapi import APIRouter

router = APIRouter(prefix="/v1/audio")

@router.post("/speech")
async def create_speech(request: SpeechRequest):
    """OpenAI 호환 TTS 엔드포인트"""
    audio = await tts_engine.synthesize(
        text=request.input,
        voice_id=request.voice or "gd-default"
    )
    return Response(content=audio, media_type="audio/wav")

@router.get("/voices")
async def list_voices():
    """사용 가능한 음성 목록"""
    return {"voices": [{"voice_id": "gd-default", "name": "G-Dragon"}]}
```

### AIRI Provider 생성
```typescript
// packages/stage-ui/src/stores/providers/gd-voice/index.ts
import { createSpeechProvider } from '@xsai-ext/providers/utils'

export function createGDVoiceProvider(options: {
  baseUrl: string
  sessionId?: string
}) {
  return createSpeechProvider({
    speech: async (text, voice) => {
      const response = await fetch(`${options.baseUrl}/v1/audio/speech`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          input: text,
          voice: voice || 'gd-default',
          session_id: options.sessionId
        })
      })
      return response.arrayBuffer()
    }
  })
}
```

---

## 8. 결론

### 핵심 가치
| 구분 | GD Voice | AIRI | 통합 시 |
|------|----------|------|---------|
| 페르소나 | G-Dragon (강점) | 커스텀 가능 | GD 페르소나 유지 |
| TTS | 한국어 최적화 | 다양한 프로바이더 | 선택적 사용 |
| 아바타 | 없음 | VRM/Live2D | AIRI 아바타 활용 |
| 플랫폼 | Web only | Web/Desktop/Mobile | 전체 플랫폼 |
| 대화 | 끼어들기, Initiative | Intent 시스템 | 양쪽 강점 결합 |

### 권장 사항
1. **시나리오 C (하이브리드)** 권장
2. Phase 1 프로토타입으로 시작
3. REST API 호환 레이어 우선 구현
4. WebSocket 스트리밍은 Phase 2에서

---

## 부록: AIRI 실행 정보

```bash
# 실행 중인 서버
AIRI Web: http://localhost:5173/

# 개발 명령어
pnpm dev          # Web 버전
pnpm dev:tamagotchi  # Desktop 버전
pnpm dev:docs     # 문서 사이트
```
