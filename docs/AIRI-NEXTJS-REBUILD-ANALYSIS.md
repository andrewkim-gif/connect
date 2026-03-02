# AIRI → Next.js + Vercel + Supabase 재구현 분석

> 완전한 기능 분석 및 기술 전환 전략

**최종 업데이트**: 2026-03-02 (누락 기능 보완 완료)

---

## 관련 검증 문서

| 문서 | 설명 | 상태 |
|------|------|------|
| [AIRI-INTEGRATION-RESEARCH.md](./AIRI-INTEGRATION-RESEARCH.md) | AIRI + GD Voice 통합 연구 | ✅ 완료 |
| [AIRI-UI-UX-REUSE-VERIFICATION.md](./AIRI-UI-UX-REUSE-VERIFICATION.md) | UI/UX 스타일 재활용 검증 | ✅ 완료 |
| [AIRI-AVATAR-SYSTEM-VERIFICATION.md](./AIRI-AVATAR-SYSTEM-VERIFICATION.md) | 버추얼 아바타 시스템 검증 | ✅ 완료 |
| [AIRI-MISSING-FEATURES-REPORT.md](./AIRI-MISSING-FEATURES-REPORT.md) | 누락 기능 종합 보고서 | ✅ 완료 |

---

## 목차

1. [AIRI 전체 기능 분석](#1-airi-전체-기능-분석)
2. [기술 스택 매핑](#2-기술-스택-매핑)
3. [핵심 시스템별 재구현 전략](#3-핵심-시스템별-재구현-전략)
4. [Supabase 데이터베이스 설계](#4-supabase-데이터베이스-설계)
5. [Vercel 배포 아키텍처](#5-vercel-배포-아키텍처)
6. [구현 우선순위 및 로드맵](#6-구현-우선순위-및-로드맵)
7. [누락 기능 보완](#7-누락-기능-보완-2026-03-02-추가) ⭐ NEW

---

## 1. AIRI 전체 기능 분석

### 1.1 핵심 기능 목록

| 카테고리 | 기능 | 상세 설명 |
|---------|------|----------|
| **Brain (두뇌)** | LLM 통합 | 30+ 프로바이더 지원, 스트리밍 응답, Tool calling |
| | 캐릭터 페르소나 | 시스템 프롬프트, 성격 설정, 다국어 지원 |
| | 대화 관리 | 세션 기반, 컨텍스트 주입, 히스토리 관리 |
| **Ears (청각)** | STT | 7+ 프로바이더, 실시간 스트리밍, VAD |
| | 음성 입력 | WebRTC, AudioWorklet, 리샘플링 |
| **Mouth (입)** | TTS | 12+ 프로바이더, 청킹 전략, SSML 지원 |
| | 립싱크 | wLipSync 기반, 모음 매핑 |
| **Body (몸)** | VRM 아바타 | Three.js, 표정, 시선 추적, SpringBone |
| | Live2D 아바타 | PixiJS, 모션, Beat Sync |
| | 모션 캡처 | MediaPipe, 포즈/손/얼굴 추적 |
| **Memory (기억)** | RAG | pgvector, 코사인 유사도, 시간 가중치 |
| | 메모리 타입 | 작업/단기/장기/근육 메모리 |
| | 에피소드 | 대화, 소개, 이벤트 기록 |
| **Integrations** | Discord | 텍스트/음성 채널 |
| | Telegram | 스티커, 사진, 메시지 |
| | Twitter | 트윗, 좋아요, 리트윗 |
| | Minecraft | Cognitive Engine, 스킬 시스템 |
| | Factorio | 게임 자동화 |
| **Plugins** | MCP | Tool calling, 외부 서비스 연동 |
| | 확장 시스템 | 플러그인 프로토콜, SDK |

### 1.2 사용자 플로우

```
┌─────────────────────────────────────────────────────────────────┐
│                    AIRI 사용자 플로우                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 초기화 (App Mount)                                          │
│     ├─→ Analytics 초기화                                        │
│     ├─→ 캐릭터 Store 로드 (기본 캐릭터 생성)                      │
│     ├─→ Onboarding 체크                                         │
│     ├─→ Chat Session 초기화                                     │
│     ├─→ Server Channel 연결 (WebSocket)                         │
│     └─→ Display Models 로드 (VRM/Live2D)                        │
│                                                                 │
│  2. 대화 플로우                                                  │
│     ┌───────────┐                                               │
│     │ User Input│ (Voice/Text)                                  │
│     └─────┬─────┘                                               │
│           ▼                                                     │
│     ┌───────────────┐                                           │
│     │ Hearing Store │ ← STT (음성인 경우)                        │
│     │ (VAD → STT)   │   - MediaStream → VAD Worklet             │
│     └───────┬───────┘   - STT Provider 호출                      │
│             ▼                                                    │
│     ┌───────────────────┐                                        │
│     │ Chat Orchestrator │ ← Context Injection                    │
│     │ (ingest → queue)  │   - datetime, modules, RAG             │
│     └───────┬───────────┘                                        │
│             ▼                                                    │
│     ┌───────────────────┐                                        │
│     │ Message Composer  │ ← System + Context + User Messages     │
│     └───────┬───────────┘                                        │
│             ▼                                                    │
│     ┌───────────────────┐                                        │
│     │   LLM Streaming   │ ← Provider 선택 → Stream 요청          │
│     │   (Tool Calling)  │   MCP 도구 호출 (있는 경우)             │
│     └───────┬───────────┘                                        │
│             ▼                                                    │
│     ┌───────────────────┐                                        │
│     │ Response Parser   │ ← Speech vs Reasoning 분류             │
│     │ (LLM Markers)     │   Special tokens 처리                  │
│     └───────┬───────────┘                                        │
│             ▼                                                    │
│     ┌───────────────────┐                                        │
│     │ Speech Pipeline   │ ← TTS 생성 → Audio Playback            │
│     │ (Chunker → TTS)   │   Lip-sync 동기화                      │
│     └───────┬───────────┘                                        │
│             ▼                                                    │
│     ┌───────────────────┐                                        │
│     │ Avatar Renderer   │ ← VRM/Live2D 렌더링                    │
│     │ (Lip-sync, Emote) │   표정/시선/모션 제어                   │
│     └───────────────────┘                                        │
│                                                                 │
│  3. 게임 통합 (선택적)                                           │
│     Minecraft/Factorio → spark:notify → Character → spark:command │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 기술 스택 매핑

### 2.1 AIRI → Next.js 기술 전환

| AIRI (현재) | Next.js 버전 | 비고 |
|------------|-------------|------|
| Vue 3 + Pinia | React + Zustand/Jotai | 상태 관리 |
| Vite | Next.js (Turbopack) | 빌드 도구 |
| UnoCSS | Tailwind CSS | 스타일링 |
| reka-ui | shadcn/ui + Radix | UI 컴포넌트 |
| vue-i18n | next-intl | 다국어 |
| @vueuse/core | @tanstack/react-query + 커스텀 훅 | 유틸리티 |
| localforage/IndexedDB | Supabase + localStorage | 스토리지 |
| H3.js WebSocket | Vercel Edge + Supabase Realtime | 실시간 |
| Drizzle ORM | Supabase Client (Postgres) | ORM |
| postgres.js | Supabase (@supabase/supabase-js) | DB 클라이언트 |
| Electron | PWA / Tauri (향후) | 데스크탑 |

### 2.2 핵심 라이브러리 매핑

| 기능 | AIRI 라이브러리 | Next.js 대체 |
|-----|----------------|-------------|
| **3D 렌더링** | @pixiv/three-vrm + Three.js | @react-three/fiber + @react-three/drei + @pixiv/three-vrm |
| **2D 렌더링** | pixi-live2d-display + PixiJS | @pixi/react + pixi-live2d-display |
| **립싱크** | wLipSync | wLipSync (동일) |
| **오디오** | Web Audio API (직접 구현) | use-sound + Tone.js |
| **모션캡처** | @mediapipe/tasks-vision | @mediapipe/tasks-vision (동일) |
| **LLM 클라이언트** | xsai (@moeru-ai/xsai) | Vercel AI SDK (@ai-sdk/*) |
| **TTS 클라이언트** | unspeech | unspeech 또는 직접 구현 |
| **STT 클라이언트** | Web Speech API + 커스텀 | @speechly/react-client 또는 직접 구현 |
| **벡터 DB** | drizzle-orm + pgvector | Supabase pgvector (supabase-js) |
| **인증** | better-auth | Supabase Auth / NextAuth.js |
| **실시간** | H3.js WebSocket | Supabase Realtime / Ably |
| **상태 저장** | unstorage + IndexedDB | Zustand + persist + IndexedDB |
| **폼 검증** | valibot | zod |
| **아이콘** | @iconify | lucide-react |
| **날짜** | 직접 구현 | date-fns |
| **유틸** | es-toolkit | lodash-es / radash |

---

## 3. 핵심 시스템별 재구현 전략

### 3.1 LLM/Chat 시스템

**AIRI 구조:**
- `stores/chat.ts`: 채팅 오케스트레이터
- `stores/llm.ts`: LLM 스트리밍
- `stores/modules/consciousness.ts`: 모델 선택

**Next.js 재구현:**

```typescript
// app/api/chat/route.ts - Vercel AI SDK 기반 스트리밍
import { streamText, convertToCoreMessages } from 'ai'
import { openai } from '@ai-sdk/openai'
import { anthropic } from '@ai-sdk/anthropic'
import { google } from '@ai-sdk/google'

export async function POST(req: Request) {
  const { messages, provider, model, characterId } = await req.json()

  // 캐릭터 시스템 프롬프트 로드
  const character = await getCharacter(characterId)
  const systemPrompt = buildSystemPrompt(character)

  // 컨텍스트 주입 (RAG)
  const context = await getRelevantContext(messages, characterId)

  // 프로바이더 선택
  const llm = selectProvider(provider, model)

  const result = streamText({
    model: llm,
    system: systemPrompt,
    messages: [
      ...context.map(c => ({ role: 'system', content: c })),
      ...convertToCoreMessages(messages),
    ],
    tools: await getMCPTools(),  // MCP 도구 지원
  })

  return result.toDataStreamResponse()
}

// 프로바이더 팩토리
function selectProvider(provider: string, model: string) {
  switch (provider) {
    case 'openai': return openai(model)
    case 'anthropic': return anthropic(model)
    case 'google': return google(model)
    // ... 기타 프로바이더
  }
}
```

```typescript
// lib/stores/chat-store.ts - Zustand 채팅 상태
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ChatState {
  sessions: Record<string, ChatSession>
  activeSessionId: string | null
  messages: ChatMessage[]
  isStreaming: boolean

  // Actions
  sendMessage: (content: string) => Promise<void>
  createSession: (characterId: string) => string
  switchSession: (sessionId: string) => void
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      sessions: {},
      activeSessionId: null,
      messages: [],
      isStreaming: false,

      sendMessage: async (content) => {
        set({ isStreaming: true })

        const response = await fetch('/api/chat', {
          method: 'POST',
          body: JSON.stringify({
            messages: [...get().messages, { role: 'user', content }],
            characterId: get().sessions[get().activeSessionId!].characterId,
          }),
        })

        // 스트리밍 응답 처리
        const reader = response.body?.getReader()
        // ... 스트림 파싱

        set({ isStreaming: false })
      },
    }),
    { name: 'chat-storage' }
  )
)
```

### 3.2 Speech Pipeline (TTS/STT)

**AIRI 구조:**
- `packages/pipelines-audio`: 오디오 파이프라인
- `packages/audio`: 오디오 컨텍스트
- `stores/modules/speech.ts`: TTS 설정
- `stores/modules/hearing.ts`: STT 설정

**Next.js 재구현:**

```typescript
// lib/audio/speech-pipeline.ts - TTS 파이프라인
export class SpeechPipeline {
  private audioContext: AudioContext
  private ttsProvider: TTSProvider
  private playbackQueue: AudioBuffer[] = []

  async speak(text: string, options?: SpeakOptions) {
    // 1. 텍스트 청킹 (AIRI와 동일한 전략)
    const chunks = this.chunkText(text, {
      boost: 2,           // 첫 2개는 빠르게
      minWords: 4,
      maxWords: 12,
      hardPunctuations: '.。!！?？',
      softPunctuations: ',，、:：;；',
    })

    // 2. 병렬 TTS 생성 + 순차 재생
    for await (const chunk of chunks) {
      const audio = await this.ttsProvider.synthesize(chunk.text)
      await this.playAudio(audio)
    }
  }

  private chunkText(text: string, options: ChunkOptions): TextChunk[] {
    // AIRI의 tts.ts 청킹 로직 포팅
    const segmenter = new Intl.Segmenter(undefined, { granularity: 'word' })
    // ... 청킹 구현
  }
}

// lib/audio/tts-providers.ts - TTS 프로바이더
export async function createTTSProvider(type: string, config: any): Promise<TTSProvider> {
  switch (type) {
    case 'elevenlabs':
      return new ElevenLabsProvider(config.apiKey, config.voiceId)
    case 'openai':
      return new OpenAITTSProvider(config.apiKey, config.voice)
    case 'gd-voice':  // GD Voice 통합
      return new GDVoiceProvider(config.wsUrl, config.sessionId)
    // ... 기타 프로바이더
  }
}
```

```typescript
// lib/audio/stt-pipeline.ts - STT 파이프라인
export function useSTT(options: STTOptions) {
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const mediaStreamRef = useRef<MediaStream | null>(null)

  const startListening = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaStreamRef.current = stream

    // VAD (Voice Activity Detection)
    const audioContext = new AudioContext()
    const source = audioContext.createMediaStreamSource(stream)
    const analyser = audioContext.createAnalyser()
    source.connect(analyser)

    // Web Speech API 또는 커스텀 STT
    if (options.provider === 'web-speech') {
      const recognition = new webkitSpeechRecognition()
      recognition.continuous = true
      recognition.interimResults = true
      recognition.onresult = (event) => {
        const result = event.results[event.results.length - 1]
        setTranscript(result[0].transcript)
      }
      recognition.start()
    } else {
      // 커스텀 STT 프로바이더 (Whisper, Deepgram 등)
      await streamToSTTProvider(stream, options.provider)
    }

    setIsListening(true)
  }

  return { isListening, transcript, startListening, stopListening }
}
```

```typescript
// components/voice-input.tsx - 음성 입력 컴포넌트
'use client'
import { useSTT } from '@/lib/audio/stt-pipeline'
import { useChatStore } from '@/lib/stores/chat-store'

export function VoiceInput() {
  const { isListening, transcript, startListening, stopListening } = useSTT({
    provider: 'web-speech',
    language: 'ko-KR',
  })
  const sendMessage = useChatStore(s => s.sendMessage)

  const handleStop = async () => {
    stopListening()
    if (transcript) {
      await sendMessage(transcript)
    }
  }

  return (
    <button
      onMouseDown={startListening}
      onMouseUp={handleStop}
      className={cn('mic-button', isListening && 'recording')}
    >
      {isListening ? <MicOnIcon /> : <MicOffIcon />}
    </button>
  )
}
```

### 3.3 Avatar 시스템

**AIRI 구조:**
- `packages/stage-ui-three`: VRM (Three.js)
- `packages/stage-ui-live2d`: Live2D (PixiJS)
- `packages/model-driver-lipsync`: 립싱크
- `packages/model-driver-mediapipe`: 모션 캡처

**핵심 기능 (기획 보완):**

| 기능 | VRM (3D) | Live2D (2D) | 구현 우선순위 |
|------|----------|-------------|--------------|
| 모델 로딩 | @pixiv/three-vrm | pixi-live2d-display | P0 |
| 립싱크 | wLipSync + AEIOU 매핑 | wLipSync + ParamMouthOpenY | P0 |
| 눈 깜빡임 | blink expression + 사인 곡선 | eyeBlink 파라미터 + 커스텀 타이머 | P1 |
| 표정/감정 | 6가지 기본 + 블렌딩 | 표정 모션 그룹 | P1 |
| 시선 추적 | LookAt + Saccade 시뮬레이션 | ParamEyeX/Y + 아이들 포커스 | P2 |
| Beat Sync | N/A | 머리 움직임 음악 동기화 (4가지 스타일) | P1 |
| 애니메이션 | .vrma 파일 + SpringBone | 모션 그룹 (idle/action) | P1 |

**VRM 표정 시스템:**
```typescript
// 6가지 기본 감정 상태
const EMOTIONS = {
  happy: [{ name: 'happy', value: 1.0 }, { name: 'aa', value: 0.3 }],
  sad: [{ name: 'sad', value: 1.0 }, { name: 'oh', value: 0.2 }],
  angry: [{ name: 'angry', value: 1.0 }, { name: 'ee', value: 0.4 }],
  surprised: [{ name: 'surprised', value: 1.0 }, { name: 'oh', value: 0.6 }],
  neutral: [{ name: 'neutral', value: 1.0 }],
  think: [{ name: 'think', value: 1.0 }],
}
// easeInOutCubic 블렌딩, 0.1~0.5초 전환 시간
```

**Live2D Beat Sync (핵심 차별화 기능):**
```typescript
// BPM 기반 머리 움직임 스타일 자동 전환
type BeatStyle = 'punchy-v' | 'balanced-v' | 'swing-lr' | 'sway-sine'

// BPM < 120 → swing-lr (좌우 스윙)
// BPM < 180 → balanced-v (균형 V자)
// BPM >= 180 → punchy-v (빠른 V자)
```

**아바타 모델 관리:**
```typescript
// 지원 포맷
enum DisplayModelFormat {
  Live2dZip = 'live2d-zip',
  VRM = 'vrm',
  // PMX, PMD 추후 지원 가능
}

// 프리셋 모델 (기본 제공)
const PRESET_MODELS = [
  { id: 'hiyori-pro', format: 'live2d-zip', name: 'Hiyori (Pro)' },
  { id: 'avatar-sample-a', format: 'vrm', name: 'AvatarSample_A' },
]
```

**Next.js 재구현:**

```typescript
// components/avatar/vrm-avatar.tsx - VRM 3D 아바타
'use client'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Environment } from '@react-three/drei'
import { VRM, VRMLoaderPlugin } from '@pixiv/three-vrm'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader'
import { useVRMLipSync } from '@/lib/avatar/vrm-lip-sync'
import { useVRMExpression } from '@/lib/avatar/vrm-expression'

export function VRMAvatarScene({ modelUrl, audioSource }: Props) {
  const [vrm, setVrm] = useState<VRM | null>(null)

  // VRM 로드
  useEffect(() => {
    const loader = new GLTFLoader()
    loader.register(parser => new VRMLoaderPlugin(parser))
    loader.load(modelUrl, gltf => {
      const vrm = gltf.userData.vrm as VRM
      setVrm(vrm)
    })
  }, [modelUrl])

  return (
    <Canvas camera={{ position: [0, 1.5, 2], fov: 40 }}>
      <ambientLight intensity={0.6} />
      <directionalLight position={[5, 5, 5]} intensity={2} />
      {vrm && (
        <VRMModel
          vrm={vrm}
          audioSource={audioSource}
        />
      )}
      <OrbitControls target={[0, 1, 0]} />
      <Environment preset="studio" />
    </Canvas>
  )
}

function VRMModel({ vrm, audioSource }: { vrm: VRM; audioSource?: AudioNode }) {
  const { updateLipSync } = useVRMLipSync(vrm, audioSource)
  const { setEmotion } = useVRMExpression(vrm)

  useFrame((_, delta) => {
    updateLipSync(delta)
    vrm.update(delta)
  })

  return <primitive object={vrm.scene} />
}
```

```typescript
// lib/avatar/vrm-lip-sync.ts - VRM 립싱크 훅
import { createWLipSyncNode } from 'w-lip-sync'

const BLENDSHAPE_MAP = {
  A: 'aa', E: 'ee', I: 'ih', O: 'oh', U: 'ou'
}

export function useVRMLipSync(vrm: VRM, audioSource?: AudioNode) {
  const lipSyncRef = useRef<WLipSyncNode | null>(null)
  const smoothState = useRef({ A: 0, E: 0, I: 0, O: 0, U: 0 })

  useEffect(() => {
    if (!audioSource) return

    const audioContext = new AudioContext()
    createWLipSyncNode(audioContext).then(node => {
      lipSyncRef.current = node
      audioSource.connect(node)
    })
  }, [audioSource])

  const updateLipSync = (delta: number) => {
    const node = lipSyncRef.current
    if (!node || !vrm.expressionManager) return

    const volume = Math.min((node.volume ?? 0) * 0.9, 1) ** 0.7

    // 모음 가중치 계산 및 스무딩
    for (const key of ['A', 'E', 'I', 'O', 'U']) {
      const target = node[key.toLowerCase()] ?? 0
      const attack = 0.15, release = 0.08
      const rate = 1 - Math.exp(-(target > smoothState.current[key] ? attack : release) / delta)
      smoothState.current[key] += (target - smoothState.current[key]) * rate

      vrm.expressionManager.setValue(BLENDSHAPE_MAP[key], smoothState.current[key] * volume)
    }
  }

  return { updateLipSync }
}
```

```typescript
// components/avatar/live2d-avatar.tsx - Live2D 2D 아바타
'use client'
import { Application } from 'pixi.js'
import { Live2DModel } from 'pixi-live2d-display/cubism4'

export function Live2DAvatar({ modelUrl, mouthOpen }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const modelRef = useRef<Live2DModel | null>(null)

  useEffect(() => {
    const app = new Application({
      view: containerRef.current,
      transparent: true,
      autoDensity: true,
      resolution: 2,
    })

    Live2DModel.from(modelUrl).then(model => {
      modelRef.current = model
      model.anchor.set(0.5, 0.5)
      app.stage.addChild(model)
    })

    return () => app.destroy()
  }, [modelUrl])

  // 입 모양 동기화
  useEffect(() => {
    if (modelRef.current) {
      modelRef.current.internalModel.coreModel.setParameterValueById(
        'ParamMouthOpenY',
        mouthOpen
      )
    }
  }, [mouthOpen])

  return <div ref={containerRef} className="w-full h-full" />
}
```

```typescript
// lib/avatar/vrm-blink.ts - VRM 눈 깜빡임 훅
export function useVRMBlink(vrm: VRM | null) {
  const BLINK_DURATION = 0.2
  const MIN_INTERVAL = 1, MAX_INTERVAL = 6

  const stateRef = useRef({
    isBlinking: false,
    progress: 0,
    timeSinceLast: 0,
    nextBlinkTime: Math.random() * (MAX_INTERVAL - MIN_INTERVAL) + MIN_INTERVAL,
  })

  const update = useCallback((delta: number) => {
    if (!vrm?.expressionManager) return
    const s = stateRef.current

    s.timeSinceLast += delta
    if (!s.isBlinking && s.timeSinceLast >= s.nextBlinkTime) {
      s.isBlinking = true
      s.progress = 0
    }

    if (s.isBlinking) {
      s.progress += delta / BLINK_DURATION
      vrm.expressionManager.setValue('blink', Math.sin(Math.PI * s.progress))

      if (s.progress >= 1) {
        s.isBlinking = false
        s.timeSinceLast = 0
        vrm.expressionManager.setValue('blink', 0)
        s.nextBlinkTime = Math.random() * (MAX_INTERVAL - MIN_INTERVAL) + MIN_INTERVAL
      }
    }
  }, [vrm])

  return { update }
}
```

```typescript
// lib/avatar/live2d-beat-sync.ts - Live2D Beat Sync 훅 (핵심 차별화 기능)
type BeatStyle = 'punchy-v' | 'balanced-v' | 'swing-lr' | 'sway-sine'

const STYLE_CONFIG = {
  'punchy-v': { topYaw: 10, topRoll: 8, bottomDip: 4, pattern: 'v' },
  'balanced-v': { topYaw: 6, topRoll: 0, bottomDip: 6, pattern: 'v' },
  'swing-lr': { topYaw: 8, topRoll: 0, bottomDip: 6, swingLift: 8, pattern: 'swing' },
  'sway-sine': { topYaw: 10, topRoll: 0, bottomDip: 0, swingLift: 10, pattern: 'sway' },
}

export function useLive2DBeatSync(model: Live2DModel, baseAngles: { x: number; y: number; z: number }) {
  const stateRef = useRef({
    targetY: baseAngles.y,
    targetZ: baseAngles.z,
    velocityY: 0,
    velocityZ: 0,
    primed: false,
    lastBeatTimestamp: null as number | null,
    avgInterval: null as number | null,
    style: 'punchy-v' as BeatStyle,
  })

  const scheduleBeat = useCallback((timestamp?: number) => {
    const now = timestamp ?? performance.now()
    const s = stateRef.current

    if (!s.primed) { s.primed = true; s.lastBeatTimestamp = now; return }

    const interval = s.lastBeatTimestamp ? now - s.lastBeatTimestamp : 600
    s.lastBeatTimestamp = now
    s.avgInterval = s.avgInterval ? s.avgInterval * 0.7 + interval * 0.3 : interval

    // BPM 기반 자동 스타일 전환
    const bpm = 60000 / s.avgInterval
    s.style = bpm < 120 ? 'swing-lr' : bpm < 180 ? 'balanced-v' : 'punchy-v'

    // 머리 움직임 세그먼트 생성
    const config = STYLE_CONFIG[s.style]
    // ... V자, 스윙, 스웨이 패턴에 따라 targetY/Z 업데이트
  }, [])

  const updatePhysics = useCallback((now: number) => {
    const s = stateRef.current
    // 스프링 물리 (stiffness=120, damping=16)
    // Semi-implicit Euler로 부드러운 머리 움직임
    model.internalModel.coreModel.setParameterValueById('ParamAngleY', s.targetY)
    model.internalModel.coreModel.setParameterValueById('ParamAngleZ', s.targetZ)
  }, [model])

  return { scheduleBeat, updatePhysics, state: stateRef.current }
}
```

### 3.4 Memory/RAG 시스템

**AIRI 구조:**
- PostgreSQL + pgvector
- Drizzle ORM
- 코사인 유사도 검색
- 메모리 프래그먼트 타입

**Supabase 재구현:**

```sql
-- Supabase Migration: Memory System with pgvector

-- 벡터 확장 활성화
create extension if not exists vector;

-- 메모리 프래그먼트 테이블
create table memory_fragments (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  character_id text not null,

  content text not null,
  memory_type text not null check (memory_type in ('working', 'short_term', 'long_term', 'muscle')),
  category text not null check (category in ('chat', 'relationships', 'people', 'life', 'events')),

  importance integer default 5 check (importance between 1 and 10),
  emotional_impact integer default 0 check (emotional_impact between -10 and 10),
  access_count integer default 1,

  -- 벡터 임베딩 (다중 차원 지원)
  embedding vector(1536),  -- OpenAI ada-002
  embedding_model text default 'text-embedding-ada-002',

  metadata jsonb default '{}',

  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  deleted_at timestamptz  -- 소프트 삭제
);

-- HNSW 인덱스 (코사인 유사도 최적화)
create index memory_fragments_embedding_idx on memory_fragments
  using hnsw (embedding vector_cosine_ops)
  where deleted_at is null;

-- 복합 인덱스
create index memory_fragments_user_character_idx on memory_fragments(user_id, character_id);
create index memory_fragments_type_idx on memory_fragments(memory_type);
```

```typescript
// lib/memory/rag.ts - RAG 검색 구현
import { createClient } from '@supabase/supabase-js'
import { openai } from '@ai-sdk/openai'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

export async function findRelevantMemories(
  userId: string,
  characterId: string,
  query: string,
  options?: { limit?: number; threshold?: number }
) {
  const { limit = 5, threshold = 0.5 } = options ?? {}

  // 1. 쿼리 임베딩 생성
  const embedding = await generateEmbedding(query)

  // 2. 유사도 검색 (RPC 함수 호출)
  const { data, error } = await supabase.rpc('search_memories', {
    query_embedding: embedding,
    match_user_id: userId,
    match_character_id: characterId,
    match_threshold: threshold,
    match_count: limit,
  })

  if (error) throw error
  return data as MemoryFragment[]
}

async function generateEmbedding(text: string): Promise<number[]> {
  const response = await openai.embeddings.create({
    model: 'text-embedding-ada-002',
    input: text,
  })
  return response.data[0].embedding
}

// app/api/memory/ingest/route.ts - 메모리 저장 API
export async function POST(req: Request) {
  const { content, memoryType, category, characterId } = await req.json()
  const userId = await getCurrentUserId()

  // 임베딩 생성
  const embedding = await generateEmbedding(content)

  // Supabase 저장
  const { data, error } = await supabase
    .from('memory_fragments')
    .insert({
      user_id: userId,
      character_id: characterId,
      content,
      memory_type: memoryType,
      category,
      embedding,
    })
    .select()
    .single()

  return Response.json(data)
}
```

```sql
-- Supabase RPC Function: 유사도 검색
create or replace function search_memories(
  query_embedding vector(1536),
  match_user_id uuid,
  match_character_id text,
  match_threshold float default 0.5,
  match_count int default 5
)
returns table (
  id uuid,
  content text,
  memory_type text,
  category text,
  importance integer,
  similarity float,
  created_at timestamptz
)
language sql stable
as $$
  select
    mf.id,
    mf.content,
    mf.memory_type,
    mf.category,
    mf.importance,
    1 - (mf.embedding <=> query_embedding) as similarity,
    mf.created_at
  from memory_fragments mf
  where mf.user_id = match_user_id
    and mf.character_id = match_character_id
    and mf.deleted_at is null
    and 1 - (mf.embedding <=> query_embedding) > match_threshold
  order by
    (1 - (mf.embedding <=> query_embedding)) * 1.2  -- 유사도 가중치
    + (mf.importance / 10.0) * 0.3                   -- 중요도 가중치
    + extract(epoch from (now() - mf.created_at)) / 86400 / 30 * -0.1  -- 시간 감쇠
    desc
  limit match_count;
$$;
```

---

## 4. Supabase 데이터베이스 설계

### 4.1 핵심 테이블 스키마

```sql
-- =====================================================
-- SUPABASE SCHEMA FOR AIRI-LIKE PLATFORM
-- =====================================================

-- 1. 사용자 프로필 (auth.users 확장)
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text unique,
  display_name text,
  avatar_url text,
  settings jsonb default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- 2. 캐릭터 정의
create table characters (
  id text primary key,
  creator_id uuid references profiles(id),
  owner_id uuid references profiles(id),

  -- 기본 정보
  version text not null default '1.0.0',
  cover_url text,
  avatar_url text,

  -- 통계
  likes_count integer default 0,
  bookmarks_count integer default 0,
  interactions_count integer default 0,
  forks_count integer default 0,

  -- 공개 설정
  is_public boolean default false,
  price_credit text default '0',

  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- 3. 캐릭터 다국어 정보
create table character_i18n (
  id uuid primary key default gen_random_uuid(),
  character_id text references characters(id) on delete cascade,
  language text not null,

  name text not null,
  tagline text,
  description text,
  system_prompt text,  -- 캐릭터 페르소나
  tags text[] default '{}',

  unique(character_id, language)
);

-- 4. 캐릭터 능력 (LLM, TTS, VLM, ASR 설정)
create table character_capabilities (
  id uuid primary key default gen_random_uuid(),
  character_id text references characters(id) on delete cascade,
  capability_type text not null check (capability_type in ('llm', 'tts', 'vlm', 'asr')),
  config jsonb not null default '{}'
);

-- 5. 아바타 모델
create table avatar_models (
  id uuid primary key default gen_random_uuid(),
  character_id text references characters(id) on delete cascade,

  name text not null,
  model_type text not null check (model_type in ('vrm', 'live2d', 'png', '2d')),
  source_type text check (source_type in ('url', 'file', 'builtin')),
  url text,
  file_path text,
  preview_url text,
  config jsonb default '{}',

  created_at timestamptz default now()
);

-- 6. 채팅 세션
create table chat_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete cascade,
  character_id text references characters(id),

  title text,
  session_type text default 'private' check (session_type in ('private', 'group')),

  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  deleted_at timestamptz
);

-- 7. 채팅 메시지
create table chat_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references chat_sessions(id) on delete cascade,

  role text not null check (role in ('system', 'user', 'assistant', 'tool', 'error')),
  content text not null,
  name text,  -- tool 호출 시 이름

  -- 메타데이터
  tokens_used integer,
  model_used text,
  latency_ms integer,
  metadata jsonb default '{}',

  -- 벡터 임베딩 (RAG용)
  embedding vector(1536),

  created_at timestamptz default now()
);

-- 8. 프로바이더 설정
create table user_provider_configs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete cascade,

  provider_id text not null,  -- 'openai', 'anthropic', 'elevenlabs' 등
  provider_type text not null check (provider_type in ('chat', 'tts', 'stt', 'embed')),
  name text not null,
  config jsonb not null default '{}',  -- API 키 등 (암호화 권장)

  is_validated boolean default false,
  is_default boolean default false,

  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- 인덱스
create index chat_messages_session_idx on chat_messages(session_id);
create index chat_messages_embedding_idx on chat_messages using hnsw (embedding vector_cosine_ops);
create index chat_sessions_user_idx on chat_sessions(user_id);
create index characters_creator_idx on characters(creator_id);
```

### 4.2 벡터 검색 (pgvector)

```sql
-- 유사 메시지 검색 함수
create or replace function search_similar_messages(
  p_session_id uuid,
  p_query_embedding vector(1536),
  p_match_count int default 5,
  p_match_threshold float default 0.5
)
returns table (
  id uuid,
  role text,
  content text,
  similarity float,
  created_at timestamptz
)
language plpgsql
as $$
begin
  return query
  select
    cm.id,
    cm.role,
    cm.content,
    1 - (cm.embedding <=> p_query_embedding) as similarity,
    cm.created_at
  from chat_messages cm
  where cm.session_id = p_session_id
    and cm.embedding is not null
    and 1 - (cm.embedding <=> p_query_embedding) > p_match_threshold
  order by cm.embedding <=> p_query_embedding
  limit p_match_count;
end;
$$;

-- 캐릭터별 관련 기억 검색
create or replace function search_character_memories(
  p_user_id uuid,
  p_character_id text,
  p_query_embedding vector(1536),
  p_limit int default 10
)
returns table (
  content text,
  memory_type text,
  importance integer,
  similarity float
)
language sql stable
as $$
  select
    mf.content,
    mf.memory_type,
    mf.importance,
    1 - (mf.embedding <=> p_query_embedding) as similarity
  from memory_fragments mf
  where mf.user_id = p_user_id
    and mf.character_id = p_character_id
    and mf.deleted_at is null
  order by mf.embedding <=> p_query_embedding
  limit p_limit;
$$;
```

### 4.3 실시간 기능 (Realtime)

```typescript
// lib/realtime/supabase-realtime.ts
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

// 채팅 메시지 실시간 구독
export function subscribeToChatMessages(
  sessionId: string,
  onMessage: (message: ChatMessage) => void
) {
  const channel = supabase
    .channel(`chat:${sessionId}`)
    .on(
      'postgres_changes',
      {
        event: 'INSERT',
        schema: 'public',
        table: 'chat_messages',
        filter: `session_id=eq.${sessionId}`,
      },
      (payload) => {
        onMessage(payload.new as ChatMessage)
      }
    )
    .subscribe()

  return () => {
    supabase.removeChannel(channel)
  }
}

// Presence (사용자 온라인 상태)
export function usePresence(sessionId: string, userId: string) {
  const [onlineUsers, setOnlineUsers] = useState<string[]>([])

  useEffect(() => {
    const channel = supabase.channel(`presence:${sessionId}`)

    channel
      .on('presence', { event: 'sync' }, () => {
        const state = channel.presenceState()
        setOnlineUsers(Object.keys(state))
      })
      .subscribe(async (status) => {
        if (status === 'SUBSCRIBED') {
          await channel.track({ user_id: userId, online_at: new Date().toISOString() })
        }
      })

    return () => {
      supabase.removeChannel(channel)
    }
  }, [sessionId, userId])

  return onlineUsers
}

// Broadcast (실시간 이벤트 브로드캐스트)
export function useBroadcast(channelName: string) {
  const channelRef = useRef<RealtimeChannel | null>(null)

  useEffect(() => {
    channelRef.current = supabase.channel(channelName)
    channelRef.current.subscribe()

    return () => {
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current)
      }
    }
  }, [channelName])

  const broadcast = (event: string, payload: any) => {
    channelRef.current?.send({
      type: 'broadcast',
      event,
      payload,
    })
  }

  const onBroadcast = (event: string, callback: (payload: any) => void) => {
    channelRef.current?.on('broadcast', { event }, ({ payload }) => {
      callback(payload)
    })
  }

  return { broadcast, onBroadcast }
}
```

```typescript
// 사용 예시: 음성 활동 브로드캐스트
export function useVoiceActivity(sessionId: string) {
  const { broadcast, onBroadcast } = useBroadcast(`voice:${sessionId}`)

  // 내가 말하기 시작할 때
  const startSpeaking = () => {
    broadcast('speaking_start', { userId: currentUserId })
  }

  // 상대방 말하기 시작 감지
  onBroadcast('speaking_start', ({ userId }) => {
    // UI 업데이트: 상대방 아바타 입 움직임 등
  })

  return { startSpeaking, stopSpeaking }
}
```

---

## 5. Vercel 배포 아키텍처

### 5.1 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AIRI Next.js 아키텍처                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      VERCEL EDGE NETWORK                            │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                     │   │
│  │  ┌───────────────┐    ┌───────────────┐    ┌───────────────┐       │   │
│  │  │  Edge Runtime │    │  Edge Runtime │    │  Edge Runtime │       │   │
│  │  │  (미들웨어)    │    │  (API Routes) │    │   (Streaming) │       │   │
│  │  ├───────────────┤    ├───────────────┤    ├───────────────┤       │   │
│  │  │ • Auth 체크   │    │ • /api/chat   │    │ • LLM 스트리밍│       │   │
│  │  │ • Rate Limit  │    │ • /api/tts    │    │ • TTS 스트리밍│       │   │
│  │  │ • Geo 라우팅  │    │ • /api/stt    │    │ • SSE 이벤트 │       │   │
│  │  └───────────────┘    └───────────────┘    └───────────────┘       │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               │                                             │
│                               ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      NEXT.JS APP ROUTER                             │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                     │   │
│  │  app/                                                               │   │
│  │  ├── (auth)/           # 인증 관련 페이지                            │   │
│  │  │   ├── login/                                                     │   │
│  │  │   └── signup/                                                    │   │
│  │  ├── (main)/           # 메인 앱                                    │   │
│  │  │   ├── chat/         # 채팅 인터페이스                             │   │
│  │  │   ├── characters/   # 캐릭터 관리                                 │   │
│  │  │   └── settings/     # 설정                                       │   │
│  │  ├── api/              # API 라우트                                 │   │
│  │  │   ├── chat/         # LLM 스트리밍                               │   │
│  │  │   ├── tts/          # TTS 생성                                   │   │
│  │  │   ├── stt/          # STT 처리                                   │   │
│  │  │   ├── memory/       # RAG/메모리                                 │   │
│  │  │   └── webhooks/     # 외부 웹훅                                  │   │
│  │  └── layout.tsx        # 루트 레이아웃                               │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               │                                             │
│                               ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         SUPABASE                                    │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                     │   │
│  │  ┌───────────────┐    ┌───────────────┐    ┌───────────────┐       │   │
│  │  │   Auth        │    │   Database    │    │   Storage     │       │   │
│  │  ├───────────────┤    ├───────────────┤    ├───────────────┤       │   │
│  │  │ • OAuth       │    │ • PostgreSQL  │    │ • 아바타 모델 │       │   │
│  │  │ • Magic Link  │    │ • pgvector    │    │ • 오디오 파일 │       │   │
│  │  │ • Session     │    │ • RLS         │    │ • 이미지      │       │   │
│  │  └───────────────┘    └───────────────┘    └───────────────┘       │   │
│  │                                                                     │   │
│  │  ┌───────────────┐    ┌───────────────┐                            │   │
│  │  │   Realtime    │    │   Edge Func   │                            │   │
│  │  ├───────────────┤    ├───────────────┤                            │   │
│  │  │ • Presence    │    │ • 임베딩 생성 │                            │   │
│  │  │ • Broadcast   │    │ • 백그라운드  │                            │   │
│  │  │ • DB Changes  │    │   처리        │                            │   │
│  │  └───────────────┘    └───────────────┘                            │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    EXTERNAL SERVICES                                │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  • LLM: OpenAI, Anthropic, Google, Groq, DeepSeek                  │   │
│  │  • TTS: ElevenLabs, OpenAI TTS, Azure Speech, GD Voice             │   │
│  │  • STT: Whisper, Deepgram, Web Speech API                          │   │
│  │  • Bots: Discord, Telegram (Vercel Serverless 또는 별도 서비스)      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Edge Functions 활용

```typescript
// middleware.ts - Edge 미들웨어
import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export const config = {
  matcher: ['/api/:path*', '/chat/:path*', '/characters/:path*'],
}

export async function middleware(req: NextRequest) {
  const res = NextResponse.next()
  const supabase = createMiddlewareClient({ req, res })

  // 인증 체크
  const { data: { session } } = await supabase.auth.getSession()

  if (!session && req.nextUrl.pathname.startsWith('/chat')) {
    return NextResponse.redirect(new URL('/login', req.url))
  }

  // Rate limiting (Edge에서 빠르게 처리)
  const ip = req.ip ?? '127.0.0.1'
  const rateLimit = await checkRateLimit(ip)
  if (!rateLimit.allowed) {
    return new NextResponse('Too Many Requests', { status: 429 })
  }

  return res
}
```

```typescript
// app/api/chat/route.ts - Edge Runtime LLM 스트리밍
export const runtime = 'edge'

import { streamText } from 'ai'
import { openai } from '@ai-sdk/openai'

export async function POST(req: Request) {
  const { messages, model } = await req.json()

  const result = streamText({
    model: openai(model),
    messages,
    // Edge에서 스트리밍 처리
  })

  return result.toDataStreamResponse()
}
```

```typescript
// app/api/tts/route.ts - Edge TTS 프록시
export const runtime = 'edge'

export async function POST(req: Request) {
  const { text, voice, provider } = await req.json()

  // 프로바이더별 TTS 요청
  const audioStream = await generateTTS(text, voice, provider)

  return new Response(audioStream, {
    headers: {
      'Content-Type': 'audio/mpeg',
      'Transfer-Encoding': 'chunked',
    },
  })
}

async function generateTTS(text: string, voice: string, provider: string) {
  switch (provider) {
    case 'elevenlabs':
      return fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voice}/stream`, {
        method: 'POST',
        headers: {
          'xi-api-key': process.env.ELEVENLABS_API_KEY!,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text, model_id: 'eleven_multilingual_v2' }),
      }).then(r => r.body)

    case 'openai':
      return fetch('https://api.openai.com/v1/audio/speech', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ model: 'tts-1', input: text, voice }),
      }).then(r => r.body)

    case 'gd-voice':
      // GD Voice 백엔드 호출
      return fetch(`${process.env.GD_VOICE_URL}/v1/audio/speech`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input: text, voice }),
      }).then(r => r.body)
  }
}
```

### 5.3 Serverless Functions

```typescript
// app/api/memory/ingest/route.ts - 메모리 저장 (Node.js Runtime)
export const runtime = 'nodejs'
export const maxDuration = 60  // 최대 60초 (Pro 플랜)

import { createClient } from '@supabase/supabase-js'
import { openai } from '@ai-sdk/openai'

export async function POST(req: Request) {
  const { sessionId, content, memoryType } = await req.json()

  // 1. 임베딩 생성 (시간 소요)
  const embedding = await openai.embeddings.create({
    model: 'text-embedding-ada-002',
    input: content,
  })

  // 2. Supabase 저장
  const supabase = createClient(
    process.env.SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  )

  const { data, error } = await supabase
    .from('memory_fragments')
    .insert({
      content,
      memory_type: memoryType,
      embedding: embedding.data[0].embedding,
    })
    .select()
    .single()

  return Response.json(data)
}
```

```typescript
// app/api/webhooks/discord/route.ts - Discord 웹훅 처리
export const runtime = 'nodejs'

import { verifyDiscordRequest } from '@/lib/discord/verify'

export async function POST(req: Request) {
  // Discord 서명 검증
  const isValid = await verifyDiscordRequest(req)
  if (!isValid) {
    return new Response('Unauthorized', { status: 401 })
  }

  const body = await req.json()

  // Interaction 타입별 처리
  switch (body.type) {
    case 1: // PING
      return Response.json({ type: 1 })

    case 2: // APPLICATION_COMMAND
      const response = await handleSlashCommand(body)
      return Response.json(response)

    case 3: // MESSAGE_COMPONENT
      const componentResponse = await handleComponent(body)
      return Response.json(componentResponse)
  }
}
```

```typescript
// Vercel Cron Job: 메모리 정리
// vercel.json
{
  "crons": [
    {
      "path": "/api/cron/cleanup-memories",
      "schedule": "0 0 * * *"  // 매일 자정
    }
  ]
}

// app/api/cron/cleanup-memories/route.ts
export const runtime = 'nodejs'

export async function GET(req: Request) {
  // Vercel Cron 인증 확인
  const authHeader = req.headers.get('authorization')
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return new Response('Unauthorized', { status: 401 })
  }

  // 30일 이상 된 working memory 삭제
  const supabase = createClient(...)
  await supabase
    .from('memory_fragments')
    .update({ deleted_at: new Date().toISOString() })
    .eq('memory_type', 'working')
    .lt('created_at', new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString())

  return Response.json({ success: true })
}
```

---

## 6. 구현 우선순위 및 로드맵

### Phase 1: 기반 구축 (2주)

```yaml
Week 1: 프로젝트 초기화
  - [ ] Next.js 15 + App Router 프로젝트 생성
  - [ ] Supabase 프로젝트 생성 및 연동
  - [ ] shadcn/ui 설정 + 기본 컴포넌트
  - [ ] Tailwind CSS + 다크모드 설정
  - [ ] Zustand 상태 관리 설정
  - [ ] next-intl 다국어 설정 (ko, en, ja)

Week 2: 인증 및 기본 UI
  - [ ] Supabase Auth 설정 (OAuth: Google, GitHub, Discord)
  - [ ] 인증 미들웨어 구현
  - [ ] 기본 레이아웃 (사이드바, 헤더)
  - [ ] 설정 페이지 기본 구조
  - [ ] 프로바이더 설정 UI (API 키 입력)
  - [ ] Vercel 배포 파이프라인 설정

Deliverables:
  - 인증된 사용자만 접근 가능한 기본 앱
  - Supabase 연동 완료
  - Vercel 자동 배포
```

### Phase 2: 핵심 기능 (4주)

```yaml
Week 3-4: LLM 채팅 시스템
  - [ ] Vercel AI SDK 통합
  - [ ] /api/chat 스트리밍 엔드포인트
  - [ ] 다중 프로바이더 지원 (OpenAI, Anthropic, Google, Groq)
  - [ ] 채팅 UI 컴포넌트
  - [ ] 메시지 히스토리 저장 (Supabase)
  - [ ] 세션 관리 (생성, 전환, 삭제)

Week 5: 캐릭터 시스템 + 핵심 인프라
  - [ ] 캐릭터 CRUD API
  - [ ] 캐릭터 프로필 UI (페르소나, 설정)
  - [ ] 시스템 프롬프트 관리
  - [ ] 캐릭터 다국어 지원
  - [ ] 캐릭터 갤러리/마켓플레이스 UI
  - [ ] **[추가] Intent/Priority Queue 시스템** (P0)
  - [ ] **[추가] Typed Event Emitter 시스템** (P1)
  - [ ] **[추가] Onboarding Flow 구현** (P1)

Week 6: Memory/RAG 시스템
  - [ ] pgvector 확장 활성화
  - [ ] 메모리 테이블 마이그레이션
  - [ ] 임베딩 생성 API
  - [ ] 유사도 검색 RPC 함수
  - [ ] 대화 컨텍스트에 RAG 통합
  - [ ] 메모리 타입별 관리 (working/short/long-term)

Deliverables:
  - 완전한 텍스트 채팅 시스템
  - 커스텀 캐릭터 생성 가능
  - RAG 기반 장기 기억
```

### Phase 3: 아바타 시스템 (4주)

```yaml
Week 7-8: 음성 시스템 (STT/TTS)
  - [ ] Web Speech API 기반 STT
  - [ ] /api/tts 엔드포인트 (ElevenLabs, OpenAI TTS)
  - [ ] GD Voice 프로바이더 통합
  - [ ] TTS 청킹 전략 구현 (boost, hard/soft punctuation)
  - [ ] 음성 입력 UI (Push-to-talk, VAD)
  - [ ] **[추가] Playback Manager 구현** (P0) - pause/resume/queue
  - [ ] **[추가] AudioWorklet 프로세서** (P1) - 노이즈 게이트, 리샘플링
  - [ ] Barge-in (끼어들기) 지원 - Intent 시스템 연동

Week 9-10: 아바타 렌더링
  - [ ] @react-three/fiber 설정
  - [ ] VRM 로더 및 렌더러 컴포넌트
  - [ ] pixi-live2d-display 통합
  - [ ] Live2D 렌더러 컴포넌트
  - [ ] wLipSync 립싱크 통합 (AEIOU 모음 매핑)
  - [ ] 표정/감정 시스템 (6가지 기본 감정 + 블렌딩)
  - [ ] VRM 눈 깜빡임 (사인 곡선 기반)
  - [ ] VRM 시선 추적 + Saccade (미세 움직임)
  - [ ] **[추가] Live2D Beat Sync** (P1) - BPM 기반 머리 움직임
  - [ ] **[추가] Live2D 자동 눈 깜빡임** (P2)
  - [ ] **[추가] Live2D Idle Eye Focus** (P2)
  - [ ] **[추가] Model Preview Generator** (P1) - 업로드 시 자동 썸네일
  - [ ] 아바타 모델 업로드/관리 (프리셋 모델 포함)

Deliverables:
  - 음성 대화 가능
  - VRM/Live2D 아바타 렌더링
  - 립싱크 동기화
```

### Phase 4: 통합 및 최적화 (2주)

```yaml
Week 11: 통합 및 폴리싱
  - [ ] 전체 플로우 통합 테스트
  - [ ] 에러 핸들링 강화
  - [ ] 로딩 상태/스켈레톤 UI
  - [ ] 반응형 디자인 (모바일 지원)
  - [ ] PWA 설정 (서비스 워커, 오프라인 지원)
  - [ ] 접근성 (a11y) 검토

Week 12: 성능 최적화 및 배포
  - [ ] Lighthouse 점수 최적화
  - [ ] 번들 사이즈 분석 및 최적화
  - [ ] Edge 캐싱 전략
  - [ ] Supabase RLS 보안 검토
  - [ ] 프로덕션 환경 변수 설정
  - [ ] 모니터링 설정 (Vercel Analytics, Sentry)
  - [ ] 문서화 (README, API 문서)

Deliverables:
  - 프로덕션 배포 완료
  - 성능 최적화 완료
  - 문서화 완료
```

### 향후 확장 (Phase 5+)

```yaml
Optional Features:
  - [ ] Discord 봇 통합 (Vercel Serverless) - 음성 채널 STT/TTS
  - [ ] Telegram 봇 통합 - 자율 에이전트 액션 시스템
  - [ ] Satori 멀티플랫폼 프로토콜 - Discord/Telegram/Slack 통합
  - [ ] Minecraft 에이전트 (별도 서비스) - Cognitive Engine
  - [ ] MCP 플러그인 시스템 - 라이프사이클 관리, 기능 기여
  - [ ] Plugin SDK with XState - 상태 머신 기반 플러그인
  - [ ] 모션 캡처 (MediaPipe)
  - [ ] 데스크탑 앱 (Tauri) - 투명 오버레이, 시스템 트레이, 전역 단축키
  - [ ] 모바일 앱 (React Native / Capacitor)
  - [ ] 마켓플레이스 (캐릭터 공유/판매)
  - [ ] Analytics 시스템 - 대화 분석, 사용 통계
```

---

## 7. 누락 기능 보완 (2026-03-02 추가)

> 4개 병렬 에이전트 분석 결과 발견된 누락 기능들

### 7.1 Intent/Priority System (P0)

**AIRI 원본 개념**: 발화 의도 우선순위 기반 큐 관리

```typescript
// lib/audio/intent-queue.ts - 발화 의도 큐 시스템
export type IntentPriority = 'immediate' | 'high' | 'normal' | 'low'

export interface SpeechIntent {
  id: string
  priority: IntentPriority
  text: string
  source: 'user' | 'system' | 'initiative'  // GD Initiative 지원
  createdAt: number
  expiresAt?: number
  metadata?: {
    emotion?: string
    interruptible?: boolean
  }
}

class IntentQueue {
  private queue: SpeechIntent[] = []

  enqueue(intent: SpeechIntent): void {
    // 우선순위 기반 정렬 삽입
    const insertIndex = this.queue.findIndex(i =>
      this.priorityValue(i.priority) < this.priorityValue(intent.priority)
    )
    if (insertIndex === -1) {
      this.queue.push(intent)
    } else {
      this.queue.splice(insertIndex, 0, intent)
    }
  }

  dequeue(): SpeechIntent | undefined {
    return this.queue.shift()
  }

  interrupt(reason: string): SpeechIntent[] {
    // 인터럽트 가능한 의도들 제거
    const interrupted = this.queue.filter(i => i.metadata?.interruptible !== false)
    this.queue = this.queue.filter(i => i.metadata?.interruptible === false)
    return interrupted
  }

  private priorityValue(priority: IntentPriority): number {
    const values = { immediate: 4, high: 3, normal: 2, low: 1 }
    return values[priority]
  }
}

// Zustand 스토어 통합
export const useIntentStore = create<IntentState>((set, get) => ({
  queue: new IntentQueue(),
  currentIntent: null,

  addIntent: (intent: Omit<SpeechIntent, 'id' | 'createdAt'>) => {
    const fullIntent = {
      ...intent,
      id: crypto.randomUUID(),
      createdAt: Date.now(),
    }
    get().queue.enqueue(fullIntent)
    set({ queue: get().queue })
  },

  processNext: async () => {
    const intent = get().queue.dequeue()
    if (intent) {
      set({ currentIntent: intent })
      // TTS 파이프라인으로 전달
      await speakWithIntent(intent)
      set({ currentIntent: null })
    }
  },
}))
```

### 7.2 Playback Manager (P0)

**AIRI 원본 개념**: 오디오 재생 상태 및 스케줄링 관리

```typescript
// lib/audio/playback-manager.ts
export class PlaybackManager {
  private audioContext: AudioContext
  private gainNode: GainNode
  private currentSource: AudioBufferSourceNode | null = null
  private playbackQueue: AudioBuffer[] = []

  // 상태
  isPlaying = false
  isPaused = false
  currentTime = 0
  duration = 0
  volume = 1

  // 이벤트 핸들러
  onStart?: () => void
  onEnd?: () => void
  onError?: (error: Error) => void
  onProgress?: (currentTime: number, duration: number) => void

  constructor() {
    this.audioContext = new AudioContext()
    this.gainNode = this.audioContext.createGain()
    this.gainNode.connect(this.audioContext.destination)
  }

  async play(buffer: AudioBuffer): Promise<void> {
    // 현재 재생 중인 소스 중지
    this.stop()

    this.currentSource = this.audioContext.createBufferSource()
    this.currentSource.buffer = buffer
    this.currentSource.connect(this.gainNode)

    this.currentSource.onended = () => {
      this.isPlaying = false
      this.onEnd?.()
      this.processQueue()
    }

    this.currentSource.start()
    this.isPlaying = true
    this.duration = buffer.duration
    this.onStart?.()
  }

  enqueue(buffer: AudioBuffer): void {
    this.playbackQueue.push(buffer)
    if (!this.isPlaying) {
      this.processQueue()
    }
  }

  private processQueue(): void {
    const next = this.playbackQueue.shift()
    if (next) {
      this.play(next)
    }
  }

  pause(): void {
    if (this.isPlaying && this.audioContext.state === 'running') {
      this.audioContext.suspend()
      this.isPaused = true
    }
  }

  resume(): void {
    if (this.isPaused) {
      this.audioContext.resume()
      this.isPaused = false
    }
  }

  stop(): void {
    if (this.currentSource) {
      this.currentSource.stop()
      this.currentSource.disconnect()
      this.currentSource = null
    }
    this.isPlaying = false
    this.isPaused = false
  }

  setVolume(volume: number): void {
    this.volume = Math.max(0, Math.min(1, volume))
    this.gainNode.gain.setValueAtTime(this.volume, this.audioContext.currentTime)
  }

  clearQueue(): void {
    this.playbackQueue = []
  }
}

// React 훅
export function usePlaybackManager() {
  const managerRef = useRef<PlaybackManager | null>(null)
  const [state, setState] = useState({ isPlaying: false, isPaused: false, volume: 1 })

  useEffect(() => {
    managerRef.current = new PlaybackManager()
    managerRef.current.onStart = () => setState(s => ({ ...s, isPlaying: true }))
    managerRef.current.onEnd = () => setState(s => ({ ...s, isPlaying: false }))
    return () => managerRef.current?.stop()
  }, [])

  return {
    ...state,
    play: (buffer: AudioBuffer) => managerRef.current?.play(buffer),
    enqueue: (buffer: AudioBuffer) => managerRef.current?.enqueue(buffer),
    pause: () => { managerRef.current?.pause(); setState(s => ({ ...s, isPaused: true })) },
    resume: () => { managerRef.current?.resume(); setState(s => ({ ...s, isPaused: false })) },
    stop: () => { managerRef.current?.stop(); setState(s => ({ ...s, isPlaying: false, isPaused: false })) },
    setVolume: (v: number) => { managerRef.current?.setVolume(v); setState(s => ({ ...s, volume: v })) },
  }
}
```

### 7.3 Event System (P1)

**AIRI 원본 개념**: 타입 안전 시스템 전체 이벤트 관리

```typescript
// lib/events/typed-emitter.ts
type EventMap = {
  'speech:start': { intentId: string; text: string }
  'speech:end': { intentId: string; duration: number }
  'speech:interrupt': { reason: string; intentId?: string }
  'user:input': { type: 'voice' | 'text'; content: string }
  'avatar:emotion': { emotion: string; intensity: number }
  'avatar:lipSync': { vowel: 'A' | 'E' | 'I' | 'O' | 'U'; value: number }
  'system:ready': {}
  'system:error': { error: Error; context?: string }
}

class TypedEventEmitter<T extends Record<string, unknown>> {
  private listeners = new Map<keyof T, Set<(data: any) => void>>()

  on<K extends keyof T>(event: K, handler: (data: T[K]) => void): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event)!.add(handler)
    return () => this.off(event, handler)
  }

  off<K extends keyof T>(event: K, handler: (data: T[K]) => void): void {
    this.listeners.get(event)?.delete(handler)
  }

  emit<K extends keyof T>(event: K, data: T[K]): void {
    this.listeners.get(event)?.forEach(handler => handler(data))
  }

  once<K extends keyof T>(event: K, handler: (data: T[K]) => void): void {
    const onceHandler = (data: T[K]) => {
      handler(data)
      this.off(event, onceHandler)
    }
    this.on(event, onceHandler)
  }
}

// 싱글톤 인스턴스
export const systemEvents = new TypedEventEmitter<EventMap>()

// React 훅
export function useSystemEvent<K extends keyof EventMap>(
  event: K,
  handler: (data: EventMap[K]) => void
) {
  useEffect(() => {
    return systemEvents.on(event, handler)
  }, [event, handler])
}
```

### 7.4 Onboarding Flow (P1)

```typescript
// lib/stores/onboarding-store.ts
const ONBOARDING_STEPS = [
  'welcome',
  'select-avatar',
  'configure-voice',
  'test-microphone',
  'first-conversation',
] as const

type OnboardingStep = typeof ONBOARDING_STEPS[number]

interface OnboardingState {
  currentStep: number
  completedSteps: OnboardingStep[]
  skippedSteps: OnboardingStep[]
  isCompleted: boolean

  // Actions
  nextStep: () => void
  prevStep: () => void
  skipStep: () => void
  completeOnboarding: () => void
  resetOnboarding: () => void
}

export const useOnboardingStore = create<OnboardingState>()(
  persist(
    (set, get) => ({
      currentStep: 0,
      completedSteps: [],
      skippedSteps: [],
      isCompleted: false,

      nextStep: () => {
        const current = ONBOARDING_STEPS[get().currentStep]
        set({
          currentStep: get().currentStep + 1,
          completedSteps: [...get().completedSteps, current],
        })
        if (get().currentStep >= ONBOARDING_STEPS.length) {
          get().completeOnboarding()
        }
      },

      prevStep: () => set({ currentStep: Math.max(0, get().currentStep - 1) }),

      skipStep: () => {
        const current = ONBOARDING_STEPS[get().currentStep]
        set({
          currentStep: get().currentStep + 1,
          skippedSteps: [...get().skippedSteps, current],
        })
      },

      completeOnboarding: () => set({ isCompleted: true }),
      resetOnboarding: () => set({ currentStep: 0, completedSteps: [], skippedSteps: [], isCompleted: false }),
    }),
    { name: 'onboarding-storage' }
  )
)

// components/onboarding/onboarding-wizard.tsx
export function OnboardingWizard() {
  const { currentStep, isCompleted, nextStep, skipStep } = useOnboardingStore()

  if (isCompleted) return null

  const StepComponent = {
    welcome: WelcomeStep,
    'select-avatar': SelectAvatarStep,
    'configure-voice': ConfigureVoiceStep,
    'test-microphone': TestMicrophoneStep,
    'first-conversation': FirstConversationStep,
  }[ONBOARDING_STEPS[currentStep]]

  return (
    <Dialog open={!isCompleted}>
      <DialogContent>
        <StepComponent onNext={nextStep} onSkip={skipStep} />
        <OnboardingProgress current={currentStep} total={ONBOARDING_STEPS.length} />
      </DialogContent>
    </Dialog>
  )
}
```

### 7.5 Model Preview Generator (P1)

```typescript
// lib/avatar/preview-generator.ts

// VRM 모델 프리뷰 생성
export async function generateVRMPreview(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)

    // 임시 캔버스 생성
    const canvas = document.createElement('canvas')
    canvas.width = 256
    canvas.height = 256

    // Three.js 장면 설정
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 20)
    camera.position.set(0, 1.3, 2)
    camera.lookAt(0, 1, 0)

    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true })
    renderer.setSize(256, 256)

    // 조명
    scene.add(new THREE.AmbientLight(0xffffff, 0.6))
    const dirLight = new THREE.DirectionalLight(0xffffff, 2)
    dirLight.position.set(5, 5, 5)
    scene.add(dirLight)

    // VRM 로드
    const loader = new GLTFLoader()
    loader.register(parser => new VRMLoaderPlugin(parser))
    loader.load(url, gltf => {
      const vrm = gltf.userData.vrm as VRM
      scene.add(vrm.scene)

      // 렌더링
      renderer.render(scene, camera)
      const dataUrl = canvas.toDataURL('image/png')

      // 정리
      URL.revokeObjectURL(url)
      renderer.dispose()

      resolve(dataUrl)
    }, undefined, reject)
  })
}

// Live2D 모델 프리뷰 생성
export async function generateLive2DPreview(file: File): Promise<string> {
  const zip = await JSZip.loadAsync(file)
  const modelJson = Object.keys(zip.files).find(f => f.endsWith('.model3.json'))

  if (!modelJson) throw new Error('Invalid Live2D model')

  // 캔버스 설정
  const canvas = document.createElement('canvas')
  canvas.width = 256
  canvas.height = 256

  const app = new PIXI.Application({ view: canvas, transparent: true, resolution: 1 })

  // 모델 로드 (zip URL)
  const model = await Live2DModel.from(URL.createObjectURL(file))
  model.anchor.set(0.5, 0.5)
  model.position.set(128, 180)
  model.scale.set(0.15)

  app.stage.addChild(model)
  app.render()

  const dataUrl = canvas.toDataURL('image/png')

  // 정리
  app.destroy()

  return dataUrl
}
```

### 7.6 Desktop Features 계획 (P2 - Tauri)

```yaml
Tauri Desktop Features:
  Window_Management:
    - 투명 오버레이 윈도우 (다마고치 모드)
    - 클릭 스루 모드 (마우스 통과)
    - Always on top
    - 멀티 윈도우 지원

  System_Tray:
    - 트레이 아이콘
    - 빠른 액션 메뉴
    - 상태 표시

  System_Integration:
    - 전역 단축키 (예: Ctrl+Shift+Space로 음성 입력)
    - 시작 시 실행
    - 시스템 테마 연동
    - 자동 업데이트

  Screen_Capture:
    - 화면 캡처 (Vision 기능 연동)
    - 화면 공유 소스 선택

# 구현 예정 파일 구조
tauri/
├── src-tauri/
│   ├── src/
│   │   ├── main.rs
│   │   ├── commands/         # Tauri 커맨드
│   │   │   ├── window.rs     # 윈도우 관리
│   │   │   ├── tray.rs       # 시스템 트레이
│   │   │   └── shortcuts.rs  # 전역 단축키
│   │   └── plugins/
│   │       └── mcp.rs        # MCP 브릿지
│   └── tauri.conf.json
└── src/
    └── hooks/
        └── useTauri.ts       # Tauri API 훅
```

---

## 부록

### A. GD Voice 통합 포인트

```yaml
GD Voice 백엔드 현황:
  서버 위치: /home/nexus/connect/server/tts_server/
  포트: 5001 (WebSocket)
  기능:
    - STT (Whisper)
    - LLM (Gemini - G-Dragon 페르소나)
    - TTS (커스텀 한국어 최적화)
    - 실시간 스트리밍
    - Barge-in (끼어들기)
    - GD Initiative (먼저 말걸기)

통합 전략:
  Option A - REST API 래퍼:
    - /v1/audio/speech (OpenAI 호환)
    - /v1/audio/transcriptions
    - /v1/voices

  Option B - WebSocket 브릿지:
    - Next.js API Route에서 GD Voice WebSocket 프록시
    - Supabase Realtime으로 이벤트 브로드캐스트

  Option C - 직접 클라이언트 연결:
    - 클라이언트에서 직접 GD Voice WebSocket 연결
    - CORS 설정 필요

권장 구현 (Option A):
  # GD Voice 백엔드에 추가
  # tts_server/api/rest/speech.py

  @router.post("/v1/audio/speech")
  async def create_speech(request: SpeechRequest):
      audio = await tts_engine.synthesize(
          text=request.input,
          voice_id=request.voice or "gd-default"
      )
      return Response(content=audio, media_type="audio/wav")

  # Next.js에서 사용
  # lib/providers/gd-voice.ts

  export async function synthesize(text: string) {
    const response = await fetch(`${GD_VOICE_URL}/v1/audio/speech`, {
      method: 'POST',
      body: JSON.stringify({ input: text, voice: 'gd-default' }),
    })
    return response.arrayBuffer()
  }
```

### B. 참고 파일 경로 (AIRI 원본)

```yaml
Core Features:
  Chat Orchestrator: packages/stage-ui/src/stores/chat.ts
  LLM Store: packages/stage-ui/src/stores/llm.ts
  Consciousness Module: packages/stage-ui/src/stores/modules/consciousness.ts
  Speech Module: packages/stage-ui/src/stores/modules/speech.ts
  Hearing Module: packages/stage-ui/src/stores/modules/hearing.ts

Audio Pipeline:
  Speech Pipeline: packages/pipelines-audio/src/speech-pipeline.ts
  TTS Chunker: packages/pipelines-audio/src/processors/tts-chunker.ts
  Audio Context: packages/audio/src/audio-context/index.ts
  TTS Utils: packages/stage-ui/src/utils/tts.ts

Avatar System:
  VRM Loader: packages/stage-ui-three/src/composables/vrm/loader.ts
  VRM Core: packages/stage-ui-three/src/composables/vrm/core.ts
  VRM Lip-sync: packages/stage-ui-three/src/composables/vrm/lip-sync.ts
  VRM Expression: packages/stage-ui-three/src/composables/vrm/expression.ts
  VRM Animation: packages/stage-ui-three/src/composables/vrm/animation.ts
  Live2D Model: packages/stage-ui-live2d/src/components/scenes/live2d/Model.vue
  Live2D Store: packages/stage-ui-live2d/src/stores/live2d.ts
  Lip-sync Driver: packages/model-driver-lipsync/src/live2d/index.ts

Memory/Database:
  Memory Schema: services/telegram-bot/src/db/schema.ts
  Server DB: apps/server/src/services/db.ts
  Character Schema: apps/server/src/schemas/characters.ts
  Chat Schema: apps/server/src/schemas/chats.ts
  Client Storage: packages/stage-ui/src/database/storage.ts

Providers:
  Provider Store: packages/stage-ui/src/stores/providers.ts
  Provider Catalog: packages/stage-ui/src/stores/provider-catalog.ts
  ElevenLabs: packages/stage-ui/src/stores/providers/elevenlabs/
  OpenAI Compatible: packages/stage-ui/src/stores/providers/openai-compatible-builder.ts

Server:
  Server Runtime: packages/server-runtime/src/index.ts
  Server SDK: packages/server-sdk/src/client.ts
  Server Shared: packages/server-shared/src/types/websocket/events.ts

Integrations:
  Discord Bot: services/discord-bot/src/adapters/airi-adapter.ts
  Telegram Bot: services/telegram-bot/src/bots/telegram/index.ts
  Minecraft: services/minecraft/src/cognitive/container.ts
  Plugin Protocol: packages/plugin-protocol/src/types/events.ts
  Plugin SDK: packages/plugin-sdk/src/plugin/define.ts
```

### C. 기술 스택 요약

```yaml
Current (AIRI):
  Frontend: Vue 3 + Pinia + VueUse + UnoCSS
  Backend: H3.js + Hono + Drizzle ORM
  Database: PostgreSQL + pgvector + DuckDB WASM
  Realtime: WebSocket (직접 구현)
  Auth: better-auth
  Desktop: Electron
  Mobile: Capacitor

Target (Next.js + Vercel + Supabase):
  Frontend: React 18/19 + Zustand + shadcn/ui + Tailwind CSS
  Backend: Next.js API Routes (Edge + Node.js)
  Database: Supabase (PostgreSQL + pgvector)
  Realtime: Supabase Realtime
  Auth: Supabase Auth
  Desktop: PWA (향후 Tauri)
  Mobile: PWA (향후 React Native)

Key Libraries:
  LLM: Vercel AI SDK (@ai-sdk/*)
  3D: @react-three/fiber + @pixiv/three-vrm
  2D: pixi-live2d-display
  Audio: Web Audio API + wLipSync
  Forms: react-hook-form + zod
  Fetching: @tanstack/react-query
  i18n: next-intl
  Icons: lucide-react
```
