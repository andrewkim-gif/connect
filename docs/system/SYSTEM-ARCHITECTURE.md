# Connect + AIRI 시스템 아키텍처 설계

> **문서 버전**: 1.0
> **작성일**: 2026-03-02
> **기반 문서**: AIRI-NEXTJS-REBUILD-ANALYSIS.md

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [C4 Model - Level 2 (Container)](#2-c4-model---level-2-container)
3. [C4 Model - Level 3 (Component)](#3-c4-model---level-3-component)
4. [API 상세 설계](#4-api-상세-설계)
5. [데이터 모델 상세 (ERD)](#5-데이터-모델-상세-erd)
6. [실시간 시스템 설계](#6-실시간-시스템-설계)
7. [아바타 시스템 아키텍처](#7-아바타-시스템-아키텍처)
8. [오디오 파이프라인 설계](#8-오디오-파이프라인-설계)
9. [보안 아키텍처](#9-보안-아키텍처)
10. [인프라 및 배포](#10-인프라-및-배포)

---

## 1. 시스템 개요

### 1.1 프로젝트 목표

**Connect**: 팬과 연예인 AI 페르소나 간의 실시간 음성/채팅 플랫폼
**AIRI 통합**: 버추얼 아바타 (VRM/Live2D), 고급 TTS/STT, RAG 메모리 시스템

### 1.2 핵심 사용자 플로우

```
┌─────────────────────────────────────────────────────────────────┐
│                      Connect 사용자 플로우                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 인증 플로우                                                  │
│     └─→ 소셜 로그인 (Google/Kakao/Apple)                        │
│     └─→ Supabase Auth 세션 생성                                 │
│     └─→ 온보딩 체크 → (미완료 시) 온보딩 플로우                    │
│                                                                 │
│  2. 연예인 선택                                                  │
│     └─→ 캐릭터 목록 조회 (인기순/최신순)                          │
│     └─→ 캐릭터 상세 (아바타 미리보기, 프로필)                      │
│     └─→ 대화 세션 생성 또는 기존 세션 재개                        │
│                                                                 │
│  3. 대화 플로우                                                  │
│     ┌─────────────┐                                             │
│     │ User Input  │ (Voice/Text)                                │
│     └──────┬──────┘                                             │
│            ▼                                                    │
│     ┌──────────────┐      ┌──────────────┐                      │
│     │  STT Engine  │ ←──→ │  VAD Detect  │                      │
│     └──────┬───────┘      └──────────────┘                      │
│            ▼                                                    │
│     ┌──────────────────┐                                        │
│     │ Intent Queue     │ ← Priority 기반 발화 관리               │
│     │ (P0-P3 Priority) │                                        │
│     └──────┬───────────┘                                        │
│            ▼                                                    │
│     ┌──────────────────┐                                        │
│     │ Chat Orchestrator│ ← Context Injection (RAG)              │
│     │ (Vercel AI SDK)  │   System Prompt + Character Persona    │
│     └──────┬───────────┘                                        │
│            ▼                                                    │
│     ┌──────────────────┐                                        │
│     │ LLM Streaming    │ ← Multi-Provider (OpenAI/Anthropic/    │
│     │                  │   Google/GD Voice)                     │
│     └──────┬───────────┘                                        │
│            ▼                                                    │
│     ┌──────────────────┐                                        │
│     │ TTS Pipeline     │ ← Chunking → TTS → Playback Queue      │
│     │                  │   wLipSync 연동                         │
│     └──────┬───────────┘                                        │
│            ▼                                                    │
│     ┌──────────────────┐                                        │
│     │ Avatar Renderer  │ ← VRM/Live2D 렌더링                     │
│     │                  │   표정, 립싱크, Beat Sync               │
│     └──────────────────┘                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 기술 스택 확정

| 레이어 | 기술 | 버전 |
|-------|------|------|
| **Frontend** | Next.js (App Router) | 16.x |
| | React | 19.x |
| | Tailwind CSS | 4.x |
| | shadcn/ui + Radix | latest |
| | Zustand | 5.x |
| | Framer Motion | 12.x |
| **3D/2D** | @react-three/fiber | 9.x |
| | @pixiv/three-vrm | 3.x |
| | pixi-live2d-display | 0.4.x |
| | wLipSync | custom |
| **Backend** | Vercel Edge Functions | - |
| | Vercel AI SDK | 4.x |
| | Supabase (Postgres + Auth + Realtime + Storage) | 2.x |
| **Audio** | Web Audio API | - |
| | AudioWorklet | - |
| | MediaStream API | - |
| **External** | OpenAI / Anthropic / Google AI | - |
| | ElevenLabs / OpenAI TTS | - |
| | GD Voice (Custom TTS Server) | - |

---

## 2. C4 Model - Level 2 (Container)

### 2.1 Container Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CONNECT PLATFORM                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         VERCEL EDGE NETWORK                          │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │  Next.js    │  │   API       │  │  Streaming  │  │  Static     │ │   │
│  │  │  App Router │  │   Routes    │  │  Endpoints  │  │  Assets     │ │   │
│  │  │             │  │             │  │             │  │             │ │   │
│  │  │  - Pages    │  │  - /chat    │  │  - SSE      │  │  - Avatars  │ │   │
│  │  │  - Layouts  │  │  - /tts     │  │  - WebSocket│  │  - Audio    │ │   │
│  │  │  - RSC      │  │  - /stt     │  │    Proxy    │  │  - Models   │ │   │
│  │  └─────────────┘  │  - /memory  │  └─────────────┘  └─────────────┘ │   │
│  │                   │  - /auth    │                                    │   │
│  │                   └─────────────┘                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                 ┌──────────────────┼──────────────────┐                     │
│                 │                  │                  │                     │
│                 ▼                  ▼                  ▼                     │
│  ┌─────────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │     SUPABASE        │  │   LLM PROVIDERS │  │  TTS PROVIDERS  │         │
│  ├─────────────────────┤  ├─────────────────┤  ├─────────────────┤         │
│  │                     │  │                 │  │                 │         │
│  │  ┌───────────────┐  │  │  - OpenAI       │  │  - ElevenLabs   │         │
│  │  │   PostgreSQL  │  │  │  - Anthropic    │  │  - OpenAI TTS   │         │
│  │  │   + pgvector  │  │  │  - Google AI    │  │  - GD Voice     │         │
│  │  └───────────────┘  │  │  - Groq         │  │    (Custom)     │         │
│  │                     │  │  - DeepSeek     │  │                 │         │
│  │  ┌───────────────┐  │  └─────────────────┘  └─────────────────┘         │
│  │  │   Auth        │  │                                                   │
│  │  │   (OAuth)     │  │                                                   │
│  │  └───────────────┘  │                                                   │
│  │                     │                                                   │
│  │  ┌───────────────┐  │                                                   │
│  │  │   Realtime    │  │                                                   │
│  │  │   (WebSocket) │  │                                                   │
│  │  └───────────────┘  │                                                   │
│  │                     │                                                   │
│  │  ┌───────────────┐  │                                                   │
│  │  │   Storage     │  │                                                   │
│  │  │   (S3 호환)   │  │                                                   │
│  │  └───────────────┘  │                                                   │
│  └─────────────────────┘                                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT (Browser)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   React     │  │   Three.js  │  │   PixiJS    │  │  Web Audio  │         │
│  │   App       │  │   + VRM     │  │   + Live2D  │  │   + Worklet │         │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Zustand   │  │  Supabase   │  │  MediaStream│  │  IndexedDB  │         │
│  │   Stores    │  │  Client     │  │  (Mic)      │  │  (Cache)    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Container 상세

| Container | 기술 | 역할 | 통신 |
|-----------|------|------|------|
| **Next.js App** | Next.js 16 + RSC | UI 렌더링, 라우팅 | HTTPS |
| **API Routes** | Vercel Edge | REST/Streaming API | HTTPS |
| **Supabase DB** | PostgreSQL 15 + pgvector | 데이터 저장, 벡터 검색 | TCP/SSL |
| **Supabase Auth** | GoTrue | 인증, 세션 관리 | HTTPS |
| **Supabase Realtime** | Phoenix Channels | 실시간 이벤트 | WebSocket |
| **Supabase Storage** | S3 호환 | 파일 저장 | HTTPS |
| **LLM Providers** | OpenAI/Anthropic/Google | LLM 추론 | HTTPS |
| **TTS Providers** | ElevenLabs/GD Voice | 음성 합성 | HTTPS/WS |

### 2.3 통신 프로토콜

```yaml
Client_to_API:
  - HTTPS: REST API 호출
  - SSE: LLM 스트리밍 응답
  - WebSocket: 실시간 이벤트 (Supabase Realtime 경유)

API_to_Supabase:
  - PostgreSQL Wire Protocol (pg_pool)
  - Realtime: Phoenix Channels

API_to_LLM:
  - HTTPS + SSE (OpenAI SDK 스트리밍)
  - Vercel AI SDK 추상화

API_to_TTS:
  - HTTPS: REST API (ElevenLabs)
  - WebSocket: GD Voice 스트리밍
```

---

## 3. C4 Model - Level 3 (Component)

### 3.1 Frontend Components

```
src/
├── app/                          # Next.js App Router
│   ├── (auth)/                   # 인증 그룹
│   │   ├── login/page.tsx
│   │   ├── signup/page.tsx
│   │   └── callback/page.tsx
│   ├── (main)/                   # 메인 앱 그룹
│   │   ├── page.tsx              # 홈 (연예인 목록)
│   │   ├── chat/[characterId]/page.tsx
│   │   ├── characters/page.tsx
│   │   └── settings/page.tsx
│   ├── api/                      # API Routes
│   │   ├── chat/route.ts         # LLM 스트리밍
│   │   ├── tts/route.ts          # TTS 생성
│   │   ├── stt/route.ts          # STT 처리
│   │   ├── memory/route.ts       # RAG 검색/저장
│   │   └── webhooks/route.ts     # 외부 웹훅
│   ├── layout.tsx
│   └── globals.css
│
├── components/
│   ├── ui/                       # shadcn/ui 기반
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── dialog.tsx
│   │   └── ...
│   ├── chat/                     # 채팅 컴포넌트
│   │   ├── ChatContainer.tsx
│   │   ├── MessageList.tsx
│   │   ├── MessageBubble.tsx
│   │   ├── VoiceInput.tsx
│   │   └── TextInput.tsx
│   ├── avatar/                   # 아바타 컴포넌트
│   │   ├── AvatarStage.tsx       # 아바타 렌더링 컨테이너
│   │   ├── VRMAvatar.tsx         # VRM 3D 아바타
│   │   ├── Live2DAvatar.tsx      # Live2D 2D 아바타
│   │   └── AvatarControls.tsx
│   ├── character/                # 캐릭터 관련
│   │   ├── CharacterCard.tsx
│   │   ├── CharacterList.tsx
│   │   └── CharacterProfile.tsx
│   ├── layouts/                  # 레이아웃
│   │   ├── Header.tsx
│   │   ├── MobileHeader.tsx
│   │   ├── Sidebar.tsx
│   │   └── BackgroundProvider.tsx
│   ├── onboarding/               # 온보딩
│   │   ├── OnboardingWizard.tsx
│   │   ├── steps/
│   │   └── OnboardingProgress.tsx
│   └── providers/                # Context Providers
│       ├── ThemeProvider.tsx
│       ├── AuthProvider.tsx
│       └── AudioProvider.tsx
│
├── lib/
│   ├── stores/                   # Zustand 스토어
│   │   ├── useChatStore.ts       # 채팅 상태
│   │   ├── useCharacterStore.ts  # 캐릭터 상태
│   │   ├── useAudioStore.ts      # 오디오 상태
│   │   ├── useAvatarStore.ts     # 아바타 상태
│   │   ├── useIntentStore.ts     # Intent Queue
│   │   └── useOnboardingStore.ts # 온보딩 상태
│   ├── audio/                    # 오디오 시스템
│   │   ├── speech-pipeline.ts    # TTS 파이프라인
│   │   ├── stt-pipeline.ts       # STT 파이프라인
│   │   ├── playback-manager.ts   # 재생 관리
│   │   ├── intent-queue.ts       # Intent 큐
│   │   └── worklets/             # AudioWorklet
│   ├── avatar/                   # 아바타 시스템
│   │   ├── vrm-loader.ts
│   │   ├── vrm-expression.ts
│   │   ├── vrm-blink.ts
│   │   ├── vrm-lip-sync.ts
│   │   ├── live2d-loader.ts
│   │   ├── live2d-beat-sync.ts
│   │   └── preview-generator.ts
│   ├── supabase/                 # Supabase 클라이언트
│   │   ├── client.ts
│   │   ├── server.ts
│   │   └── middleware.ts
│   ├── providers/                # LLM/TTS 프로바이더
│   │   ├── llm/
│   │   ├── tts/
│   │   └── stt/
│   ├── memory/                   # RAG 시스템
│   │   ├── rag.ts
│   │   └── embedding.ts
│   ├── events/                   # 이벤트 시스템
│   │   └── typed-emitter.ts
│   └── utils/
│       ├── cn.ts
│       └── format.ts
│
├── types/                        # TypeScript 타입
│   ├── chat.ts
│   ├── character.ts
│   ├── avatar.ts
│   ├── audio.ts
│   └── index.ts
│
└── styles/                       # 추가 스타일
    ├── chromatic.css             # AIRI 색상 시스템
    └── transitions.css           # 애니메이션
```

### 3.2 Component Interaction Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           Chat Page Component                             │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                        AvatarStage                                  │  │
│  │  ┌──────────────────────┐    ┌──────────────────────┐              │  │
│  │  │     VRMAvatar        │ OR │    Live2DAvatar      │              │  │
│  │  │  - Three.js Canvas   │    │  - PixiJS Canvas     │              │  │
│  │  │  - VRM Expression    │    │  - Live2D Model      │              │  │
│  │  │  - VRM LipSync       │    │  - Beat Sync         │              │  │
│  │  │  - VRM Blink         │    │  - Auto Blink        │              │  │
│  │  └──────────────────────┘    └──────────────────────┘              │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                    ▲                                      │
│                                    │ lipSyncValue, emotion                │
│                                    │                                      │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                        ChatContainer                                │  │
│  │  ┌──────────────┐  ┌───────────────────────┐  ┌──────────────────┐ │  │
│  │  │ MessageList  │  │    CurrentMessage     │  │   InputArea      │ │  │
│  │  │              │  │   (Streaming + Sync)  │  │ ┌──────────────┐ │ │  │
│  │  │ - History    │  │                       │  │ │ VoiceInput   │ │ │  │
│  │  │ - Scroll     │  │ - PoppinText          │  │ │ - PTT/VAD    │ │ │  │
│  │  │              │  │ - TypingIndicator     │  │ └──────────────┘ │ │  │
│  │  └──────────────┘  └───────────────────────┘  │ ┌──────────────┐ │ │  │
│  │                                                │ │ TextInput    │ │ │  │
│  │                                                │ └──────────────┘ │ │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                    │                                      │
│                                    ▼                                      │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                        Audio Pipeline                               │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │  │
│  │  │ STTPipeline  │  │ IntentQueue  │  │ PlaybackManager          │  │  │
│  │  │ - Mic Input  │  │ - Priority   │  │ - AudioContext           │  │  │
│  │  │ - VAD        │  │ - Interrupt  │  │ - GainNode               │  │  │
│  │  │ - Whisper    │  │              │  │ - Queue                  │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Zustand Store Architecture

```typescript
// Store 간 관계
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ useCharacterStore│────▶│   useChatStore  │────▶│  useAudioStore  │
│                 │     │                 │     │                 │
│ - characters    │     │ - sessions      │     │ - isPlaying     │
│ - selected      │     │ - messages      │     │ - volume        │
│ - persona       │     │ - isStreaming   │     │ - playbackMgr   │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │ useIntentStore  │────▶│  useAvatarStore │
                        │                 │     │                 │
                        │ - queue         │     │ - currentModel  │
                        │ - currentIntent │     │ - emotion       │
                        │ - addIntent     │     │ - lipSyncValue  │
                        └─────────────────┘     └─────────────────┘
```

---

## 4. API 상세 설계

### 4.1 API 엔드포인트 목록

| 엔드포인트 | 메서드 | 설명 | Runtime |
|-----------|--------|------|---------|
| `/api/chat` | POST | LLM 채팅 스트리밍 | Edge |
| `/api/tts` | POST | TTS 생성 | Edge |
| `/api/stt` | POST | STT 변환 | Node.js |
| `/api/memory/search` | POST | RAG 검색 | Edge |
| `/api/memory/ingest` | POST | 메모리 저장 | Edge |
| `/api/characters` | GET | 캐릭터 목록 | Edge |
| `/api/characters/[id]` | GET | 캐릭터 상세 | Edge |
| `/api/sessions` | GET/POST | 세션 관리 | Edge |
| `/api/webhooks/gd-voice` | POST | GD Voice 웹훅 | Node.js |

### 4.2 Chat API 상세

```typescript
// POST /api/chat
// Runtime: Edge (스트리밍 지원)

// Request
interface ChatRequest {
  messages: Array<{
    role: 'user' | 'assistant' | 'system'
    content: string
  }>
  characterId: string
  sessionId: string
  options?: {
    provider?: 'openai' | 'anthropic' | 'google' | 'gd-voice'
    model?: string
    temperature?: number
    maxTokens?: number
    enableRAG?: boolean
  }
}

// Response: SSE Stream
// Content-Type: text/event-stream

// Event Types:
// data: {"type":"text-delta","textDelta":"안녕"}
// data: {"type":"tool-call","toolCallId":"...","toolName":"..."}
// data: {"type":"finish","finishReason":"stop","usage":{...}}

// Implementation
import { streamText, convertToCoreMessages } from 'ai'
import { openai } from '@ai-sdk/openai'
import { anthropic } from '@ai-sdk/anthropic'
import { google } from '@ai-sdk/google'

export async function POST(req: Request) {
  const { messages, characterId, sessionId, options } = await req.json()

  // 1. 캐릭터 시스템 프롬프트 로드
  const character = await getCharacter(characterId)
  const systemPrompt = buildSystemPrompt(character)

  // 2. RAG 컨텍스트 주입 (옵션)
  let contextMessages = []
  if (options?.enableRAG !== false) {
    const context = await findRelevantMemories(sessionId, messages)
    contextMessages = context.map(c => ({
      role: 'system' as const,
      content: `[Memory] ${c.content}`
    }))
  }

  // 3. 프로바이더 선택
  const model = selectModel(options?.provider, options?.model)

  // 4. 스트리밍 응답
  const result = streamText({
    model,
    system: systemPrompt,
    messages: [
      ...contextMessages,
      ...convertToCoreMessages(messages)
    ],
    temperature: options?.temperature ?? 0.7,
    maxTokens: options?.maxTokens ?? 1024,
  })

  return result.toDataStreamResponse()
}
```

### 4.3 TTS API 상세

```typescript
// POST /api/tts
// Runtime: Edge

// Request
interface TTSRequest {
  text: string
  provider: 'elevenlabs' | 'openai' | 'gd-voice'
  voiceId: string
  options?: {
    speed?: number
    stability?: number
    similarityBoost?: number
  }
}

// Response
// Content-Type: audio/mpeg (또는 audio/wav)
// Body: Binary audio data

// Implementation
export async function POST(req: Request) {
  const { text, provider, voiceId, options } = await req.json()

  switch (provider) {
    case 'elevenlabs':
      return await elevenLabsTTS(text, voiceId, options)

    case 'openai':
      return await openaiTTS(text, voiceId, options)

    case 'gd-voice':
      return await gdVoiceTTS(text, voiceId, options)

    default:
      return new Response('Invalid provider', { status: 400 })
  }
}

async function elevenLabsTTS(text: string, voiceId: string, options: any) {
  const response = await fetch(
    `https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`,
    {
      method: 'POST',
      headers: {
        'xi-api-key': process.env.ELEVENLABS_API_KEY!,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text,
        model_id: 'eleven_multilingual_v2',
        voice_settings: {
          stability: options?.stability ?? 0.5,
          similarity_boost: options?.similarityBoost ?? 0.75,
        }
      })
    }
  )

  return new Response(response.body, {
    headers: { 'Content-Type': 'audio/mpeg' }
  })
}

async function gdVoiceTTS(text: string, voiceId: string, options: any) {
  const response = await fetch(
    `${process.env.GD_VOICE_URL}/v1/audio/speech`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        input: text,
        voice: voiceId,
        session_id: options?.sessionId
      })
    }
  )

  return new Response(response.body, {
    headers: { 'Content-Type': 'audio/wav' }
  })
}
```

### 4.4 Memory API 상세

```typescript
// POST /api/memory/search
// Runtime: Edge

// Request
interface MemorySearchRequest {
  query: string
  characterId: string
  sessionId: string
  options?: {
    limit?: number
    threshold?: number
    memoryTypes?: ('working' | 'short_term' | 'long_term')[]
  }
}

// Response
interface MemorySearchResponse {
  memories: Array<{
    id: string
    content: string
    memoryType: string
    similarity: number
    createdAt: string
  }>
}

// POST /api/memory/ingest
// Request
interface MemoryIngestRequest {
  content: string
  characterId: string
  sessionId: string
  memoryType: 'working' | 'short_term' | 'long_term'
  category: 'chat' | 'relationships' | 'events'
  importance?: number
}

// Response
interface MemoryIngestResponse {
  id: string
  success: boolean
}
```

### 4.5 Error Response 표준

```typescript
// 모든 API 에러 응답 형식
interface APIError {
  error: {
    code: string           // 'RATE_LIMIT_EXCEEDED', 'INVALID_REQUEST', etc.
    message: string        // 사람이 읽을 수 있는 메시지
    details?: unknown      // 추가 디버그 정보
  }
  status: number           // HTTP 상태 코드
}

// Error Codes
const ERROR_CODES = {
  INVALID_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  RATE_LIMIT_EXCEEDED: 429,
  PROVIDER_ERROR: 502,
  INTERNAL_ERROR: 500,
} as const
```

---

## 5. 데이터 모델 상세 (ERD)

### 5.1 ERD Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATABASE SCHEMA                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────┐         ┌───────────────────┐                        │
│  │     profiles      │         │    characters     │                        │
│  ├───────────────────┤         ├───────────────────┤                        │
│  │ id (PK, FK→auth)  │         │ id (PK)           │                        │
│  │ username          │         │ creator_id (FK)   │◄─────┐                 │
│  │ display_name      │         │ name              │      │                 │
│  │ avatar_url        │         │ name_ko           │      │                 │
│  │ settings (JSONB)  │         │ profile_image     │      │                 │
│  │ onboarding_done   │         │ cover_image       │      │                 │
│  │ created_at        │         │ bio               │      │                 │
│  │ updated_at        │         │ persona (JSONB)   │      │                 │
│  └────────┬──────────┘         │ is_public         │      │                 │
│           │                    │ created_at        │      │                 │
│           │                    └─────────┬─────────┘      │                 │
│           │                              │                │                 │
│           │                              │                │                 │
│           ▼                              ▼                │                 │
│  ┌───────────────────┐         ┌───────────────────┐      │                 │
│  │   chat_sessions   │         │   avatar_models   │      │                 │
│  ├───────────────────┤         ├───────────────────┤      │                 │
│  │ id (PK)           │         │ id (PK)           │      │                 │
│  │ user_id (FK)      │◄────────│ character_id (FK) │──────┘                 │
│  │ character_id (FK) │         │ name              │                        │
│  │ title             │         │ model_type        │ (vrm|live2d)           │
│  │ last_message_at   │         │ source_type       │ (url|file|builtin)     │
│  │ created_at        │         │ url               │                        │
│  │ deleted_at        │         │ preview_url       │                        │
│  └────────┬──────────┘         │ config (JSONB)    │                        │
│           │                    │ created_at        │                        │
│           │                    └───────────────────┘                        │
│           │                                                                 │
│           ▼                                                                 │
│  ┌───────────────────┐         ┌───────────────────┐                        │
│  │   chat_messages   │         │ memory_fragments  │                        │
│  ├───────────────────┤         ├───────────────────┤                        │
│  │ id (PK)           │         │ id (PK)           │                        │
│  │ session_id (FK)   │         │ user_id (FK)      │                        │
│  │ role              │         │ character_id (FK) │                        │
│  │ content           │         │ session_id (FK)   │                        │
│  │ name              │         │ content           │                        │
│  │ tokens_used       │         │ memory_type       │ (working|short|long)   │
│  │ model_used        │         │ category          │                        │
│  │ latency_ms        │         │ importance        │ (1-10)                 │
│  │ metadata (JSONB)  │         │ embedding         │ vector(1536)           │
│  │ embedding         │ vector  │ metadata (JSONB)  │                        │
│  │ created_at        │         │ created_at        │                        │
│  └───────────────────┘         │ deleted_at        │                        │
│                                └───────────────────┘                        │
│                                                                             │
│  ┌───────────────────┐         ┌───────────────────┐                        │
│  │ provider_configs  │         │   user_voices     │                        │
│  ├───────────────────┤         ├───────────────────┤                        │
│  │ id (PK)           │         │ id (PK)           │                        │
│  │ user_id (FK)      │         │ user_id (FK)      │                        │
│  │ provider_id       │         │ character_id (FK) │                        │
│  │ provider_type     │         │ provider          │ (elevenlabs|gd-voice)  │
│  │ name              │         │ voice_id          │                        │
│  │ config (JSONB)    │ 암호화  │ is_default        │                        │
│  │ is_validated      │         │ created_at        │                        │
│  │ is_default        │         └───────────────────┘                        │
│  │ created_at        │                                                      │
│  └───────────────────┘                                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 테이블 상세 스키마

```sql
-- profiles: 사용자 프로필 (auth.users 확장)
CREATE TABLE profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username TEXT UNIQUE,
  display_name TEXT,
  avatar_url TEXT,
  settings JSONB DEFAULT '{}',
  onboarding_done BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- characters: 연예인/AI 캐릭터
CREATE TABLE characters (
  id TEXT PRIMARY KEY,  -- 'gd', 'iu' 등 slug
  creator_id UUID REFERENCES profiles(id),
  name TEXT NOT NULL,
  name_ko TEXT,
  profile_image TEXT,
  cover_image TEXT,
  bio TEXT,
  persona JSONB NOT NULL DEFAULT '{}',
  -- persona 구조:
  -- {
  --   "basePrompt": "시스템 프롬프트",
  --   "speechStyle": "말투 설명",
  --   "personality": ["키워드"],
  --   "topics": ["관심사"],
  --   "greetings": ["인사말"],
  --   "voiceId": "기본 음성 ID"
  -- }
  is_public BOOLEAN DEFAULT FALSE,
  likes_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- avatar_models: 아바타 모델 (VRM/Live2D)
CREATE TABLE avatar_models (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  character_id TEXT REFERENCES characters(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  model_type TEXT NOT NULL CHECK (model_type IN ('vrm', 'live2d')),
  source_type TEXT CHECK (source_type IN ('url', 'file', 'builtin')),
  url TEXT,
  preview_url TEXT,
  config JSONB DEFAULT '{}',
  -- config 구조:
  -- VRM: { "scale": 1.0, "cameraPosition": [0, 1.5, 2] }
  -- Live2D: { "scale": 0.3, "position": [0.5, 0.5] }
  is_default BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- chat_sessions: 대화 세션
CREATE TABLE chat_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  character_id TEXT REFERENCES characters(id),
  title TEXT,
  last_message_at TIMESTAMPTZ,
  message_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

-- chat_messages: 채팅 메시지
CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('system', 'user', 'assistant', 'tool')),
  content TEXT NOT NULL,
  name TEXT,  -- tool 호출 시 이름
  tokens_used INTEGER,
  model_used TEXT,
  latency_ms INTEGER,
  metadata JSONB DEFAULT '{}',
  embedding VECTOR(1536),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- memory_fragments: RAG 메모리
CREATE TABLE memory_fragments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  character_id TEXT REFERENCES characters(id),
  session_id UUID REFERENCES chat_sessions(id),
  content TEXT NOT NULL,
  memory_type TEXT NOT NULL CHECK (memory_type IN ('working', 'short_term', 'long_term')),
  category TEXT NOT NULL CHECK (category IN ('chat', 'relationships', 'events', 'preferences')),
  importance INTEGER DEFAULT 5 CHECK (importance BETWEEN 1 AND 10),
  embedding VECTOR(1536),
  metadata JSONB DEFAULT '{}',
  access_count INTEGER DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

-- 인덱스
CREATE INDEX idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_embedding ON chat_messages
  USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_memory_fragments_user_char ON memory_fragments(user_id, character_id);
CREATE INDEX idx_memory_fragments_embedding ON memory_fragments
  USING hnsw (embedding vector_cosine_ops) WHERE deleted_at IS NULL;
CREATE INDEX idx_chat_sessions_user ON chat_sessions(user_id) WHERE deleted_at IS NULL;
```

### 5.3 RLS (Row Level Security) 정책

```sql
-- profiles: 본인만 수정 가능
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view all profiles" ON profiles
  FOR SELECT USING (true);

CREATE POLICY "Users can update own profile" ON profiles
  FOR UPDATE USING (auth.uid() = id);

-- chat_sessions: 본인 세션만 접근
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access own sessions" ON chat_sessions
  FOR ALL USING (auth.uid() = user_id);

-- chat_messages: 본인 세션의 메시지만 접근
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access messages in own sessions" ON chat_messages
  FOR ALL USING (
    session_id IN (
      SELECT id FROM chat_sessions WHERE user_id = auth.uid()
    )
  );

-- memory_fragments: 본인 메모리만 접근
ALTER TABLE memory_fragments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access own memories" ON memory_fragments
  FOR ALL USING (auth.uid() = user_id);
```

---

## 6. 실시간 시스템 설계

### 6.1 Supabase Realtime 채널 구조

```typescript
// 채널 네이밍 컨벤션
const CHANNELS = {
  // 채팅 세션 채널 (메시지 실시간 동기화)
  chatSession: (sessionId: string) => `chat:${sessionId}`,

  // 사용자 상태 채널 (온라인/오프라인)
  userPresence: (userId: string) => `presence:${userId}`,

  // 음성 활동 브로드캐스트 (말하기 시작/끝)
  voiceActivity: (sessionId: string) => `voice:${sessionId}`,

  // 아바타 상태 동기화 (표정, 립싱크)
  avatarState: (sessionId: string) => `avatar:${sessionId}`,
}
```

### 6.2 실시간 이벤트 타입

```typescript
// 이벤트 타입 정의
interface RealtimeEvents {
  // 채팅 이벤트
  'chat:message_created': {
    sessionId: string
    message: ChatMessage
  }
  'chat:typing_start': {
    sessionId: string
    role: 'user' | 'assistant'
  }
  'chat:typing_end': {
    sessionId: string
    role: 'user' | 'assistant'
  }

  // 음성 이벤트
  'voice:speaking_start': {
    sessionId: string
    speaker: 'user' | 'assistant'
    intentId?: string
  }
  'voice:speaking_end': {
    sessionId: string
    speaker: 'user' | 'assistant'
    duration: number
  }
  'voice:interrupt': {
    sessionId: string
    reason: 'user_interrupt' | 'timeout' | 'error'
  }

  // 아바타 이벤트
  'avatar:emotion_change': {
    sessionId: string
    emotion: string
    intensity: number
  }
  'avatar:lip_sync': {
    sessionId: string
    vowel: 'A' | 'E' | 'I' | 'O' | 'U'
    value: number
  }
}
```

### 6.3 Realtime 훅 구현

```typescript
// lib/realtime/use-chat-realtime.ts
import { useEffect, useCallback } from 'react'
import { createClient } from '@/lib/supabase/client'
import { useChatStore } from '@/lib/stores/useChatStore'

export function useChatRealtime(sessionId: string) {
  const addMessage = useChatStore(s => s.addMessage)
  const setTyping = useChatStore(s => s.setTyping)

  useEffect(() => {
    const supabase = createClient()

    // 1. DB 변경 구독 (새 메시지)
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
          addMessage(payload.new as ChatMessage)
        }
      )
      // 2. 브로드캐스트 구독 (타이핑 상태)
      .on('broadcast', { event: 'typing_start' }, () => {
        setTyping(true)
      })
      .on('broadcast', { event: 'typing_end' }, () => {
        setTyping(false)
      })
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [sessionId, addMessage, setTyping])

  // 타이핑 브로드캐스트 함수
  const broadcastTyping = useCallback(async (isTyping: boolean) => {
    const supabase = createClient()
    const channel = supabase.channel(`chat:${sessionId}`)

    await channel.send({
      type: 'broadcast',
      event: isTyping ? 'typing_start' : 'typing_end',
      payload: {},
    })
  }, [sessionId])

  return { broadcastTyping }
}
```

### 6.4 Presence 시스템

```typescript
// lib/realtime/use-presence.ts
import { useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase/client'

interface PresenceState {
  onlineAt: string
  status: 'online' | 'away' | 'busy'
}

export function usePresence(sessionId: string, userId: string) {
  const [onlineUsers, setOnlineUsers] = useState<Map<string, PresenceState>>(new Map())

  useEffect(() => {
    const supabase = createClient()
    const channel = supabase.channel(`presence:${sessionId}`)

    channel
      .on('presence', { event: 'sync' }, () => {
        const state = channel.presenceState<PresenceState>()
        const users = new Map<string, PresenceState>()

        Object.entries(state).forEach(([key, presences]) => {
          if (presences[0]) {
            users.set(key, presences[0])
          }
        })

        setOnlineUsers(users)
      })
      .subscribe(async (status) => {
        if (status === 'SUBSCRIBED') {
          await channel.track({
            onlineAt: new Date().toISOString(),
            status: 'online',
          })
        }
      })

    return () => {
      supabase.removeChannel(channel)
    }
  }, [sessionId, userId])

  return { onlineUsers }
}
```

### 6.5 음성 활동 브로드캐스트

```typescript
// lib/realtime/use-voice-broadcast.ts
import { useCallback, useRef } from 'react'
import { createClient } from '@/lib/supabase/client'

export function useVoiceBroadcast(sessionId: string) {
  const channelRef = useRef<ReturnType<typeof createClient>['channel'] | null>(null)

  const initChannel = useCallback(() => {
    if (channelRef.current) return

    const supabase = createClient()
    channelRef.current = supabase.channel(`voice:${sessionId}`)
    channelRef.current.subscribe()
  }, [sessionId])

  const broadcastSpeakingStart = useCallback((speaker: 'user' | 'assistant') => {
    channelRef.current?.send({
      type: 'broadcast',
      event: 'speaking_start',
      payload: { speaker, timestamp: Date.now() },
    })
  }, [])

  const broadcastSpeakingEnd = useCallback((speaker: 'user' | 'assistant', duration: number) => {
    channelRef.current?.send({
      type: 'broadcast',
      event: 'speaking_end',
      payload: { speaker, duration, timestamp: Date.now() },
    })
  }, [])

  const broadcastInterrupt = useCallback((reason: string) => {
    channelRef.current?.send({
      type: 'broadcast',
      event: 'interrupt',
      payload: { reason, timestamp: Date.now() },
    })
  }, [])

  return {
    initChannel,
    broadcastSpeakingStart,
    broadcastSpeakingEnd,
    broadcastInterrupt,
  }
}
```

---

## 7. 아바타 시스템 아키텍처

### 7.1 아바타 렌더링 파이프라인

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        AVATAR RENDERING PIPELINE                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐    │
│  │  Audio Source   │────▶│  wLipSync Node  │────▶│  Vowel Values   │    │
│  │  (TTS Output)   │     │  (AudioWorklet) │     │  A/E/I/O/U      │    │
│  └─────────────────┘     └─────────────────┘     └────────┬────────┘    │
│                                                           │              │
│                                                           ▼              │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐    │
│  │  Emotion State  │────▶│  Expression     │────▶│  Blendshape     │    │
│  │  (from LLM)     │     │  Controller     │     │  Values         │    │
│  └─────────────────┘     └─────────────────┘     └────────┬────────┘    │
│                                                           │              │
│                          ┌────────────────────────────────┘              │
│                          ▼                                               │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                     AVATAR RENDERER                                │  │
│  │  ┌─────────────────────────┐  ┌─────────────────────────┐         │  │
│  │  │       VRM (3D)          │  │     Live2D (2D)         │         │  │
│  │  ├─────────────────────────┤  ├─────────────────────────┤         │  │
│  │  │ • Three.js + R3F        │  │ • PixiJS                │         │  │
│  │  │ • @pixiv/three-vrm      │  │ • pixi-live2d-display   │         │  │
│  │  │ • VRM Expression        │  │ • Cubism SDK            │         │  │
│  │  │ • VRM Blink             │  │ • Auto Blink            │         │  │
│  │  │ • VRM Saccade           │  │ • Beat Sync             │         │  │
│  │  │ • SpringBone Physics    │  │ • Idle Eye Focus        │         │  │
│  │  └─────────────────────────┘  └─────────────────────────┘         │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 7.2 VRM 시스템 컴포넌트

```typescript
// components/avatar/VRMAvatar.tsx
'use client'

import { useRef, useEffect, useCallback } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Environment } from '@react-three/drei'
import { VRM, VRMLoaderPlugin } from '@pixiv/three-vrm'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader'

import { useVRMLipSync } from '@/lib/avatar/vrm-lip-sync'
import { useVRMExpression } from '@/lib/avatar/vrm-expression'
import { useVRMBlink } from '@/lib/avatar/vrm-blink'
import { useVRMSaccade } from '@/lib/avatar/vrm-saccade'
import { useAvatarStore } from '@/lib/stores/useAvatarStore'

interface VRMAvatarProps {
  modelUrl: string
  audioSource?: AudioNode
}

export function VRMAvatar({ modelUrl, audioSource }: VRMAvatarProps) {
  return (
    <Canvas camera={{ position: [0, 1.5, 2], fov: 35 }}>
      <ambientLight intensity={0.6} />
      <directionalLight position={[5, 5, 5]} intensity={2} castShadow />
      <VRMModel modelUrl={modelUrl} audioSource={audioSource} />
      <OrbitControls
        target={[0, 1.2, 0]}
        enablePan={false}
        minDistance={1}
        maxDistance={4}
      />
      <Environment preset="studio" />
    </Canvas>
  )
}

function VRMModel({ modelUrl, audioSource }: VRMAvatarProps) {
  const vrmRef = useRef<VRM | null>(null)
  const { emotion, lipSyncEnabled } = useAvatarStore()

  // VRM 로드
  useEffect(() => {
    const loader = new GLTFLoader()
    loader.register(parser => new VRMLoaderPlugin(parser))

    loader.load(modelUrl, gltf => {
      const vrm = gltf.userData.vrm as VRM
      vrm.scene.rotation.y = Math.PI  // 카메라를 향하도록
      vrmRef.current = vrm
    })

    return () => {
      if (vrmRef.current) {
        vrmRef.current.scene.traverse(obj => {
          if ('dispose' in obj) (obj as any).dispose()
        })
      }
    }
  }, [modelUrl])

  // 립싱크
  const { updateLipSync } = useVRMLipSync(vrmRef.current, audioSource)

  // 표정
  const { setEmotion, updateExpression } = useVRMExpression(vrmRef.current)

  // 눈 깜빡임
  const { updateBlink } = useVRMBlink(vrmRef.current)

  // 시선 미세 움직임
  const { updateSaccade } = useVRMSaccade(vrmRef.current)

  // 감정 변화 반영
  useEffect(() => {
    if (emotion) {
      setEmotion(emotion.name, emotion.intensity)
    }
  }, [emotion, setEmotion])

  // 프레임 업데이트
  useFrame((_, delta) => {
    if (!vrmRef.current) return

    if (lipSyncEnabled) {
      updateLipSync(delta)
    }
    updateExpression(delta)
    updateBlink(delta)
    updateSaccade(delta)

    vrmRef.current.update(delta)
  })

  return vrmRef.current ? <primitive object={vrmRef.current.scene} /> : null
}
```

### 7.3 Live2D 시스템 컴포넌트

```typescript
// components/avatar/Live2DAvatar.tsx
'use client'

import { useRef, useEffect, useCallback } from 'react'
import { Application } from 'pixi.js'
import { Live2DModel } from 'pixi-live2d-display/cubism4'

import { useLive2DLipSync } from '@/lib/avatar/live2d-lip-sync'
import { useLive2DBeatSync } from '@/lib/avatar/live2d-beat-sync'
import { useLive2DAutoBlink } from '@/lib/avatar/live2d-auto-blink'
import { useAvatarStore } from '@/lib/stores/useAvatarStore'

interface Live2DAvatarProps {
  modelUrl: string
  audioSource?: AudioNode
}

export function Live2DAvatar({ modelUrl, audioSource }: Live2DAvatarProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const appRef = useRef<Application | null>(null)
  const modelRef = useRef<Live2DModel | null>(null)

  const { emotion, lipSyncValue, beatSyncEnabled } = useAvatarStore()

  // PixiJS 초기화
  useEffect(() => {
    if (!containerRef.current) return

    const app = new Application({
      view: containerRef.current as unknown as HTMLCanvasElement,
      resizeTo: containerRef.current,
      backgroundAlpha: 0,
      antialias: true,
      resolution: 2,
    })
    appRef.current = app

    // Live2D 모델 로드
    Live2DModel.from(modelUrl, {
      autoInteract: false,
      autoUpdate: true,
    }).then(model => {
      modelRef.current = model

      // 캔버스 중앙에 배치
      model.anchor.set(0.5, 0.5)
      model.position.set(app.screen.width / 2, app.screen.height * 0.6)

      // 크기 조정
      const scale = Math.min(
        app.screen.width / model.width * 0.8,
        app.screen.height / model.height * 0.9
      )
      model.scale.set(scale)

      app.stage.addChild(model)
    })

    return () => {
      app.destroy(true)
    }
  }, [modelUrl])

  // 립싱크
  const { updateLipSync } = useLive2DLipSync(modelRef.current, audioSource)

  // Beat Sync
  const { scheduleBeat, updatePhysics } = useLive2DBeatSync(
    modelRef.current,
    { x: 0, y: 0, z: 0 }
  )

  // 자동 눈 깜빡임
  const { updateAutoBlink } = useLive2DAutoBlink(modelRef.current)

  // 프레임 업데이트
  useEffect(() => {
    if (!appRef.current) return

    const ticker = appRef.current.ticker
    const updateLoop = (delta: number) => {
      const deltaTime = delta / 60  // 초 단위로 변환

      updateLipSync(deltaTime)
      updateAutoBlink(deltaTime)

      if (beatSyncEnabled) {
        updatePhysics(performance.now())
      }
    }

    ticker.add(updateLoop)
    return () => ticker.remove(updateLoop)
  }, [updateLipSync, updateAutoBlink, updatePhysics, beatSyncEnabled])

  // 감정 변화 시 모션 재생
  useEffect(() => {
    if (!modelRef.current || !emotion) return

    const motionGroup = `motion_${emotion.name}`
    modelRef.current.motion(motionGroup, 0)
  }, [emotion])

  return (
    <div
      ref={containerRef}
      className="w-full h-full"
      style={{ touchAction: 'none' }}
    />
  )
}
```

### 7.4 아바타 스토어

```typescript
// lib/stores/useAvatarStore.ts
import { create } from 'zustand'

type AvatarType = 'vrm' | 'live2d'
type EmotionName = 'happy' | 'sad' | 'angry' | 'surprised' | 'neutral' | 'think'

interface AvatarState {
  // 현재 모델 정보
  currentModel: {
    id: string
    type: AvatarType
    url: string
  } | null

  // 감정 상태
  emotion: {
    name: EmotionName
    intensity: number
  } | null

  // 립싱크 상태
  lipSyncEnabled: boolean
  lipSyncValue: number

  // Beat Sync (Live2D)
  beatSyncEnabled: boolean

  // Actions
  setModel: (model: AvatarState['currentModel']) => void
  setEmotion: (name: EmotionName, intensity?: number) => void
  clearEmotion: () => void
  setLipSyncEnabled: (enabled: boolean) => void
  setLipSyncValue: (value: number) => void
  setBeatSyncEnabled: (enabled: boolean) => void
}

export const useAvatarStore = create<AvatarState>((set) => ({
  currentModel: null,
  emotion: null,
  lipSyncEnabled: true,
  lipSyncValue: 0,
  beatSyncEnabled: true,

  setModel: (model) => set({ currentModel: model }),

  setEmotion: (name, intensity = 1) => set({
    emotion: { name, intensity: Math.max(0, Math.min(1, intensity)) }
  }),

  clearEmotion: () => set({ emotion: { name: 'neutral', intensity: 1 } }),

  setLipSyncEnabled: (enabled) => set({ lipSyncEnabled: enabled }),

  setLipSyncValue: (value) => set({ lipSyncValue: value }),

  setBeatSyncEnabled: (enabled) => set({ beatSyncEnabled: enabled }),
}))
```

---

## 8. 오디오 파이프라인 설계

### 8.1 오디오 파이프라인 구조

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         AUDIO PIPELINE                                    │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     INPUT (STT) PIPELINE                          │   │
│  │                                                                   │   │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────────────┐   │   │
│  │  │  Mic    │──▶│  VAD    │──▶│ Resample│──▶│ STT Provider    │   │   │
│  │  │ Stream  │   │ Worklet │   │ (16kHz) │   │ (Whisper/etc)   │   │   │
│  │  └─────────┘   └─────────┘   └─────────┘   └────────┬────────┘   │   │
│  │                                                      │            │   │
│  │                                              transcript           │   │
│  └──────────────────────────────────────────────────────┼────────────┘   │
│                                                         │                │
│                                                         ▼                │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    INTENT QUEUE                                   │   │
│  │  ┌────────────────────────────────────────────────────────────┐  │   │
│  │  │  Priority Queue: immediate > high > normal > low           │  │   │
│  │  │                                                            │  │   │
│  │  │  [P0: System Interrupt] → [P1: User Response] → [P2: Idle]│  │   │
│  │  └────────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┬────────────┘   │
│                                                         │                │
│                                                         ▼                │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    OUTPUT (TTS) PIPELINE                          │   │
│  │                                                                   │   │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────────────┐   │   │
│  │  │ Chunker │──▶│  TTS    │──▶│ Playback│──▶│  wLipSync       │   │   │
│  │  │ (Text)  │   │ Provider│   │ Manager │   │  (Audio→Vowels) │   │   │
│  │  └─────────┘   └─────────┘   └─────────┘   └─────────────────┘   │   │
│  │       │                           │               │              │   │
│  │       │                           │               │              │   │
│  │  boost/hard/soft             pause/resume      A/E/I/O/U        │   │
│  │  punctuation                  volume            values           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Intent Queue 구현

```typescript
// lib/audio/intent-queue.ts
export type IntentPriority = 'immediate' | 'high' | 'normal' | 'low'

export interface SpeechIntent {
  id: string
  priority: IntentPriority
  text: string
  source: 'user' | 'system' | 'initiative'
  createdAt: number
  expiresAt?: number
  metadata?: {
    emotion?: string
    interruptible?: boolean
    voiceId?: string
  }
}

const PRIORITY_ORDER: Record<IntentPriority, number> = {
  immediate: 4,
  high: 3,
  normal: 2,
  low: 1,
}

export class IntentQueue {
  private queue: SpeechIntent[] = []
  private listeners: Set<(queue: SpeechIntent[]) => void> = new Set()

  enqueue(intent: Omit<SpeechIntent, 'id' | 'createdAt'>): SpeechIntent {
    const fullIntent: SpeechIntent = {
      ...intent,
      id: crypto.randomUUID(),
      createdAt: Date.now(),
    }

    // 우선순위 기반 삽입
    const insertIndex = this.queue.findIndex(
      i => PRIORITY_ORDER[i.priority] < PRIORITY_ORDER[fullIntent.priority]
    )

    if (insertIndex === -1) {
      this.queue.push(fullIntent)
    } else {
      this.queue.splice(insertIndex, 0, fullIntent)
    }

    this.notify()
    return fullIntent
  }

  dequeue(): SpeechIntent | undefined {
    const intent = this.queue.shift()
    if (intent) this.notify()
    return intent
  }

  peek(): SpeechIntent | undefined {
    return this.queue[0]
  }

  interrupt(reason: string): SpeechIntent[] {
    // interruptible=true인 의도만 제거
    const interrupted = this.queue.filter(
      i => i.metadata?.interruptible !== false
    )
    this.queue = this.queue.filter(
      i => i.metadata?.interruptible === false
    )
    this.notify()
    return interrupted
  }

  clear(): void {
    this.queue = []
    this.notify()
  }

  subscribe(listener: (queue: SpeechIntent[]) => void): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  private notify(): void {
    this.listeners.forEach(l => l([...this.queue]))
  }

  get size(): number {
    return this.queue.length
  }

  get isEmpty(): boolean {
    return this.queue.length === 0
  }
}
```

### 8.3 Playback Manager 구현

```typescript
// lib/audio/playback-manager.ts
export class PlaybackManager {
  private audioContext: AudioContext | null = null
  private gainNode: GainNode | null = null
  private currentSource: AudioBufferSourceNode | null = null
  private playbackQueue: AudioBuffer[] = []

  // 상태
  isPlaying = false
  isPaused = false
  volume = 1

  // 이벤트
  onStart?: (buffer: AudioBuffer) => void
  onEnd?: () => void
  onError?: (error: Error) => void

  async init(): Promise<void> {
    this.audioContext = new AudioContext()
    this.gainNode = this.audioContext.createGain()
    this.gainNode.connect(this.audioContext.destination)
  }

  async play(buffer: AudioBuffer): Promise<void> {
    if (!this.audioContext || !this.gainNode) {
      await this.init()
    }

    // 현재 재생 중지
    this.stop()

    this.currentSource = this.audioContext!.createBufferSource()
    this.currentSource.buffer = buffer
    this.currentSource.connect(this.gainNode!)

    this.currentSource.onended = () => {
      this.isPlaying = false
      this.onEnd?.()
      this.processQueue()
    }

    try {
      this.currentSource.start()
      this.isPlaying = true
      this.onStart?.(buffer)
    } catch (error) {
      this.onError?.(error as Error)
    }
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
    if (this.isPlaying && this.audioContext?.state === 'running') {
      this.audioContext.suspend()
      this.isPaused = true
    }
  }

  resume(): void {
    if (this.isPaused && this.audioContext?.state === 'suspended') {
      this.audioContext.resume()
      this.isPaused = false
    }
  }

  stop(): void {
    if (this.currentSource) {
      try {
        this.currentSource.stop()
        this.currentSource.disconnect()
      } catch {
        // 이미 종료된 경우 무시
      }
      this.currentSource = null
    }
    this.isPlaying = false
    this.isPaused = false
  }

  setVolume(volume: number): void {
    this.volume = Math.max(0, Math.min(1, volume))
    if (this.gainNode && this.audioContext) {
      this.gainNode.gain.setValueAtTime(this.volume, this.audioContext.currentTime)
    }
  }

  clearQueue(): void {
    this.playbackQueue = []
  }

  // wLipSync 연동을 위한 AudioNode 반환
  getAudioNode(): GainNode | null {
    return this.gainNode
  }
}
```

### 8.4 TTS Chunking 전략

```typescript
// lib/audio/tts-chunker.ts
export interface ChunkOptions {
  boost: number           // 첫 N개 청크 빠르게 생성
  minWords: number        // 최소 단어 수
  maxWords: number        // 최대 단어 수
  hardPunctuations: string  // 강제 분할: .。!！?？
  softPunctuations: string  // 선택적 분할: ,，、:：;；
  boostPunctuations: string // 부스트 분할: ~\n
}

const DEFAULT_OPTIONS: ChunkOptions = {
  boost: 2,
  minWords: 3,
  maxWords: 15,
  hardPunctuations: '.。!！?？',
  softPunctuations: ',，、:：;；',
  boostPunctuations: '~\n',
}

export async function* chunkText(
  text: string,
  options: Partial<ChunkOptions> = {}
): AsyncGenerator<{ text: string; index: number; isFinal: boolean }> {
  const opts = { ...DEFAULT_OPTIONS, ...options }

  // Intl.Segmenter로 단어 분리
  const segmenter = new Intl.Segmenter('ko', { granularity: 'word' })
  const words = [...segmenter.segment(text)]
    .filter(s => s.isWordLike || opts.hardPunctuations.includes(s.segment))
    .map(s => s.segment)

  let currentChunk: string[] = []
  let chunkIndex = 0

  for (let i = 0; i < words.length; i++) {
    const word = words[i]
    currentChunk.push(word)

    const isHardPunctuation = opts.hardPunctuations.includes(word)
    const isSoftPunctuation = opts.softPunctuations.includes(word)
    const isBoostPhase = chunkIndex < opts.boost
    const wordCount = currentChunk.length

    // 청크 분할 조건
    const shouldSplit =
      isHardPunctuation ||
      (isSoftPunctuation && wordCount >= opts.minWords) ||
      (isBoostPhase && wordCount >= opts.minWords) ||
      wordCount >= opts.maxWords

    if (shouldSplit) {
      yield {
        text: currentChunk.join(''),
        index: chunkIndex,
        isFinal: i === words.length - 1,
      }
      currentChunk = []
      chunkIndex++
    }
  }

  // 남은 텍스트
  if (currentChunk.length > 0) {
    yield {
      text: currentChunk.join(''),
      index: chunkIndex,
      isFinal: true,
    }
  }
}

// 스트리밍 텍스트용 청커
export async function* chunkStreamingText(
  textStream: AsyncIterable<string>,
  options: Partial<ChunkOptions> = {}
): AsyncGenerator<{ text: string; index: number; isFinal: boolean }> {
  const opts = { ...DEFAULT_OPTIONS, ...options }
  let buffer = ''
  let chunkIndex = 0

  for await (const delta of textStream) {
    buffer += delta

    // 분할 가능한 위치 찾기
    let splitIndex = -1

    for (let i = buffer.length - 1; i >= 0; i--) {
      const char = buffer[i]
      if (opts.hardPunctuations.includes(char)) {
        splitIndex = i + 1
        break
      }
    }

    if (splitIndex > 0) {
      const chunk = buffer.slice(0, splitIndex)
      buffer = buffer.slice(splitIndex)

      yield {
        text: chunk,
        index: chunkIndex,
        isFinal: false,
      }
      chunkIndex++
    }
  }

  // 마지막 버퍼
  if (buffer.trim()) {
    yield {
      text: buffer,
      index: chunkIndex,
      isFinal: true,
    }
  }
}
```

### 8.5 VAD (Voice Activity Detection)

```typescript
// lib/audio/vad-worklet.ts
// AudioWorklet으로 구현되어야 함

class VADWorklet extends AudioWorkletProcessor {
  private silenceThreshold = 0.01
  private silenceDuration = 0
  private maxSilence = 1.5  // 1.5초 무음 시 종료

  static get parameterDescriptors() {
    return [
      { name: 'threshold', defaultValue: 0.01 },
      { name: 'maxSilence', defaultValue: 1.5 },
    ]
  }

  process(
    inputs: Float32Array[][],
    outputs: Float32Array[][],
    parameters: Record<string, Float32Array>
  ): boolean {
    const input = inputs[0]?.[0]
    if (!input) return true

    // RMS 계산
    let sum = 0
    for (let i = 0; i < input.length; i++) {
      sum += input[i] * input[i]
    }
    const rms = Math.sqrt(sum / input.length)

    // 음성 활동 감지
    const isVoice = rms > this.silenceThreshold

    if (isVoice) {
      this.silenceDuration = 0
      this.port.postMessage({ type: 'voice_start' })
    } else {
      this.silenceDuration += input.length / sampleRate

      if (this.silenceDuration >= this.maxSilence) {
        this.port.postMessage({ type: 'voice_end' })
      }
    }

    // Pass-through
    if (outputs[0]?.[0]) {
      outputs[0][0].set(input)
    }

    return true
  }
}

registerProcessor('vad-worklet', VADWorklet)
```

---

## 9. 보안 아키텍처

### 9.1 인증 플로우

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        AUTHENTICATION FLOW                                │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    SUPABASE AUTH                                 │    │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │    │
│  │  │  Google   │  │   Kakao   │  │   Apple   │  │  Discord  │    │    │
│  │  │   OAuth   │  │   OAuth   │  │   OAuth   │  │   OAuth   │    │    │
│  │  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘    │    │
│  │        │              │              │              │           │    │
│  │        └──────────────┴──────────────┴──────────────┘           │    │
│  │                              │                                   │    │
│  │                              ▼                                   │    │
│  │  ┌─────────────────────────────────────────────────────────┐    │    │
│  │  │                    GoTrue Server                         │    │    │
│  │  │  • JWT 발행 (access_token + refresh_token)              │    │    │
│  │  │  • 세션 관리                                             │    │    │
│  │  │  • MFA 지원 (선택)                                       │    │    │
│  │  └─────────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    NEXT.JS MIDDLEWARE                            │   │
│  │  • JWT 검증                                                     │   │
│  │  • 세션 갱신 (refresh)                                          │   │
│  │  • Protected Routes 리다이렉트                                   │   │
│  │  • Rate Limiting (by IP)                                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 9.2 보안 체크리스트

```yaml
Authentication:
  ✅ OAuth 2.0 + PKCE (소셜 로그인)
  ✅ JWT 기반 세션 (access + refresh token)
  ✅ HttpOnly 쿠키 (XSS 방지)
  ✅ Secure + SameSite=Lax 쿠키 속성
  ⬜ MFA 지원 (Phase 2)

Authorization:
  ✅ Row Level Security (RLS) - Supabase
  ✅ 사용자별 데이터 격리
  ✅ API Rate Limiting
  ⬜ RBAC (관리자 기능 추가 시)

Data_Protection:
  ✅ HTTPS only (Vercel 자동)
  ✅ API Key 서버 사이드 보관
  ✅ 민감 정보 환경변수
  ⬜ provider_configs 암호화 (AES-256-GCM)

Input_Validation:
  ✅ Zod 스키마 검증
  ✅ SQL Injection 방지 (Supabase 파라미터)
  ✅ XSS 방지 (React 자동 이스케이프)
  ✅ CSRF 토큰 (Supabase Auth 내장)

API_Security:
  ✅ Edge Middleware 인증 검사
  ✅ Rate Limiting (Vercel Edge)
  ✅ CORS 제한 (origin whitelist)
  ⬜ Request signing (외부 웹훅)
```

### 9.3 Rate Limiting 설계

```typescript
// middleware.ts
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// 간단한 인메모리 Rate Limiter (Edge에서 동작)
const rateLimitMap = new Map<string, { count: number; resetAt: number }>()

const RATE_LIMITS = {
  '/api/chat': { requests: 30, window: 60 },      // 30 req/min
  '/api/tts': { requests: 20, window: 60 },       // 20 req/min
  '/api/stt': { requests: 20, window: 60 },       // 20 req/min
  '/api/memory': { requests: 60, window: 60 },    // 60 req/min
  'default': { requests: 100, window: 60 },       // 100 req/min
}

function getRateLimit(pathname: string) {
  for (const [path, limit] of Object.entries(RATE_LIMITS)) {
    if (pathname.startsWith(path)) return limit
  }
  return RATE_LIMITS.default
}

export async function middleware(request: NextRequest) {
  const ip = request.ip ?? request.headers.get('x-forwarded-for') ?? 'unknown'
  const pathname = request.nextUrl.pathname

  // API 엔드포인트에만 Rate Limiting 적용
  if (pathname.startsWith('/api/')) {
    const limit = getRateLimit(pathname)
    const key = `${ip}:${pathname}`
    const now = Date.now()

    let entry = rateLimitMap.get(key)

    if (!entry || now > entry.resetAt) {
      entry = { count: 0, resetAt: now + limit.window * 1000 }
    }

    entry.count++
    rateLimitMap.set(key, entry)

    if (entry.count > limit.requests) {
      return new NextResponse(
        JSON.stringify({ error: { code: 'RATE_LIMIT_EXCEEDED', message: 'Too many requests' } }),
        {
          status: 429,
          headers: {
            'Content-Type': 'application/json',
            'Retry-After': String(Math.ceil((entry.resetAt - now) / 1000)),
          },
        }
      )
    }
  }

  return NextResponse.next()
}

export const config = {
  matcher: '/api/:path*',
}
```

### 9.4 API Key 관리

```typescript
// 환경변수 구조
/*
# .env.local (절대 커밋 금지)

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...  # 서버만

# LLM Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_AI_API_KEY=...

# TTS Providers
ELEVENLABS_API_KEY=...
GD_VOICE_URL=http://localhost:5001

# 암호화
ENCRYPTION_KEY=...  # 32 bytes hex

# Cron
CRON_SECRET=...
*/

// lib/crypto.ts - API Key 암호화/복호화
import { createCipheriv, createDecipheriv, randomBytes } from 'crypto'

const ALGORITHM = 'aes-256-gcm'
const KEY = Buffer.from(process.env.ENCRYPTION_KEY!, 'hex')

export function encrypt(plaintext: string): string {
  const iv = randomBytes(16)
  const cipher = createCipheriv(ALGORITHM, KEY, iv)

  let encrypted = cipher.update(plaintext, 'utf8', 'hex')
  encrypted += cipher.final('hex')

  const authTag = cipher.getAuthTag()

  return `${iv.toString('hex')}:${authTag.toString('hex')}:${encrypted}`
}

export function decrypt(ciphertext: string): string {
  const [ivHex, authTagHex, encrypted] = ciphertext.split(':')

  const iv = Buffer.from(ivHex, 'hex')
  const authTag = Buffer.from(authTagHex, 'hex')

  const decipher = createDecipheriv(ALGORITHM, KEY, iv)
  decipher.setAuthTag(authTag)

  let decrypted = decipher.update(encrypted, 'hex', 'utf8')
  decrypted += decipher.final('utf8')

  return decrypted
}
```

### 9.5 Supabase RLS 정책 상세

```sql
-- 1. profiles: 본인 프로필만 수정 가능
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view profiles"
  ON profiles FOR SELECT
  USING (true);

CREATE POLICY "Users can update own profile"
  ON profiles FOR UPDATE
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
  ON profiles FOR INSERT
  WITH CHECK (auth.uid() = id);

-- 2. characters: 공개 캐릭터는 누구나, 비공개는 소유자만
ALTER TABLE characters ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view public characters"
  ON characters FOR SELECT
  USING (is_public = true OR creator_id = auth.uid());

CREATE POLICY "Creators can manage own characters"
  ON characters FOR ALL
  USING (creator_id = auth.uid());

-- 3. chat_sessions: 본인 세션만
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own sessions"
  ON chat_sessions FOR ALL
  USING (user_id = auth.uid());

-- 4. chat_messages: 본인 세션의 메시지만
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access messages in own sessions"
  ON chat_messages FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM chat_sessions
      WHERE chat_sessions.id = chat_messages.session_id
      AND chat_sessions.user_id = auth.uid()
    )
  );

-- 5. memory_fragments: 본인 메모리만
ALTER TABLE memory_fragments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own memories"
  ON memory_fragments FOR ALL
  USING (user_id = auth.uid());

-- 6. provider_configs: 본인 설정만
ALTER TABLE provider_configs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own provider configs"
  ON provider_configs FOR ALL
  USING (user_id = auth.uid());
```

---

## 10. 인프라 및 배포

### 10.1 Vercel 배포 아키텍처

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        VERCEL DEPLOYMENT                                  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     VERCEL EDGE NETWORK                          │    │
│  │                                                                  │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │    │
│  │  │  CDN        │  │  Edge       │  │  Serverless Functions   │  │    │
│  │  │  (Static)   │  │  Functions  │  │  (Node.js Runtime)      │  │    │
│  │  │             │  │             │  │                         │  │    │
│  │  │  • _next/   │  │  • /api/*   │  │  • /api/stt (large)     │  │    │
│  │  │  • avatars/ │  │  • Edge RT  │  │  • /api/webhooks/*      │  │    │
│  │  │  • audio/   │  │  • <50ms    │  │  • Node.js RT           │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │    │
│  │                                                                  │    │
│  │  ┌─────────────────────────────────────────────────────────┐    │    │
│  │  │                    STREAMING                             │    │    │
│  │  │  • LLM Response (SSE)                                   │    │    │
│  │  │  • TTS Audio (Chunked Transfer)                         │    │    │
│  │  │  • Edge Runtime 최적화                                   │    │    │
│  │  └─────────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     CI/CD PIPELINE                               │    │
│  │                                                                  │    │
│  │  GitHub Push ──▶ Preview Deploy ──▶ Production Deploy           │    │
│  │       │              │                    │                      │    │
│  │       ▼              ▼                    ▼                      │    │
│  │  ┌─────────┐  ┌─────────────┐  ┌─────────────────────────┐      │    │
│  │  │ Lint &  │  │ Preview URL │  │ Production               │      │    │
│  │  │ Type    │  │ (PR 별)     │  │ connect.vercel.app      │      │    │
│  │  │ Check   │  │             │  │                         │      │    │
│  │  └─────────┘  └─────────────┘  └─────────────────────────┘      │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 10.2 환경 구성

```yaml
# vercel.json
{
  "framework": "nextjs",
  "buildCommand": "pnpm build",
  "installCommand": "pnpm install",
  "regions": ["icn1"],  # 서울 리전 우선

  "crons": [
    {
      "path": "/api/cron/cleanup-memories",
      "schedule": "0 0 * * *"  # 매일 자정 (UTC)
    },
    {
      "path": "/api/cron/refresh-embeddings",
      "schedule": "0 */6 * * *"  # 6시간마다
    }
  ],

  "headers": [
    {
      "source": "/api/(.*)",
      "headers": [
        { "key": "Access-Control-Allow-Credentials", "value": "true" },
        { "key": "Access-Control-Allow-Origin", "value": "$VERCEL_URL" }
      ]
    }
  ]
}
```

### 10.3 환경변수 설정

```yaml
# Production (Vercel Dashboard)
NEXT_PUBLIC_SUPABASE_URL: https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY: eyJ...
SUPABASE_SERVICE_ROLE_KEY: eyJ...

OPENAI_API_KEY: sk-...
ANTHROPIC_API_KEY: sk-ant-...
GOOGLE_AI_API_KEY: ...
ELEVENLABS_API_KEY: ...

GD_VOICE_URL: https://gd-voice.xxx.com  # 프로덕션 GD Voice

ENCRYPTION_KEY: ...  # 32 bytes hex
CRON_SECRET: ...

# Preview (자동 생성)
VERCEL_URL: connect-xxx-team.vercel.app

# Development (.env.local)
NEXT_PUBLIC_SUPABASE_URL: http://localhost:54321
GD_VOICE_URL: http://localhost:5001
```

### 10.4 모니터링 및 로깅

```typescript
// lib/monitoring/logger.ts
type LogLevel = 'debug' | 'info' | 'warn' | 'error'

interface LogEntry {
  level: LogLevel
  message: string
  timestamp: string
  context?: Record<string, unknown>
  error?: {
    name: string
    message: string
    stack?: string
  }
}

export function log(level: LogLevel, message: string, context?: Record<string, unknown>) {
  const entry: LogEntry = {
    level,
    message,
    timestamp: new Date().toISOString(),
    context,
  }

  // Vercel Log Drain으로 전송됨
  console.log(JSON.stringify(entry))
}

export function logError(error: Error, context?: Record<string, unknown>) {
  log('error', error.message, {
    ...context,
    error: {
      name: error.name,
      message: error.message,
      stack: error.stack,
    },
  })
}

// API Route에서 사용
export async function POST(req: Request) {
  const startTime = Date.now()

  try {
    // ... 로직
    log('info', 'API call succeeded', {
      path: '/api/chat',
      duration: Date.now() - startTime,
    })
  } catch (error) {
    logError(error as Error, { path: '/api/chat' })
    throw error
  }
}
```

### 10.5 성능 예산

```yaml
Performance_Budget:
  LCP: < 2.5s          # Largest Contentful Paint
  FID: < 100ms         # First Input Delay
  CLS: < 0.1           # Cumulative Layout Shift
  TTI: < 3.5s          # Time to Interactive
  Bundle_Size:
    First_Load_JS: < 100KB
    Total_JS: < 300KB

API_Response_Times:
  /api/chat (first token): < 500ms
  /api/tts (first chunk): < 300ms
  /api/memory/search: < 200ms
  /api/characters: < 100ms

Avatar_Rendering:
  VRM_Load: < 3s
  Live2D_Load: < 2s
  FPS: 60 (target), 30 (minimum)
```

### 10.6 디렉토리 구조 최종

```
connect/app/
├── src/
│   ├── app/                      # Next.js App Router
│   │   ├── (auth)/               # 인증 페이지 그룹
│   │   │   ├── login/page.tsx
│   │   │   ├── signup/page.tsx
│   │   │   └── callback/page.tsx
│   │   ├── (main)/               # 메인 앱 그룹
│   │   │   ├── page.tsx          # 홈 (캐릭터 목록)
│   │   │   ├── layout.tsx        # 메인 레이아웃
│   │   │   ├── chat/
│   │   │   │   └── [characterId]/page.tsx
│   │   │   ├── characters/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/page.tsx
│   │   │   └── settings/
│   │   │       ├── page.tsx
│   │   │       ├── profile/page.tsx
│   │   │       └── providers/page.tsx
│   │   ├── api/                  # API Routes
│   │   │   ├── chat/route.ts
│   │   │   ├── tts/route.ts
│   │   │   ├── stt/route.ts
│   │   │   ├── memory/
│   │   │   │   ├── search/route.ts
│   │   │   │   └── ingest/route.ts
│   │   │   ├── characters/
│   │   │   │   ├── route.ts
│   │   │   │   └── [id]/route.ts
│   │   │   ├── sessions/route.ts
│   │   │   ├── cron/
│   │   │   │   └── cleanup-memories/route.ts
│   │   │   └── webhooks/
│   │   │       └── gd-voice/route.ts
│   │   ├── layout.tsx            # Root Layout
│   │   ├── globals.css
│   │   └── not-found.tsx
│   │
│   ├── components/
│   │   ├── ui/                   # shadcn/ui
│   │   ├── chat/                 # 채팅 컴포넌트
│   │   ├── avatar/               # 아바타 컴포넌트
│   │   ├── character/            # 캐릭터 컴포넌트
│   │   ├── layouts/              # 레이아웃 컴포넌트
│   │   ├── onboarding/           # 온보딩
│   │   └── providers/            # Context Providers
│   │
│   ├── lib/
│   │   ├── stores/               # Zustand 스토어
│   │   ├── audio/                # 오디오 시스템
│   │   ├── avatar/               # 아바타 시스템
│   │   ├── supabase/             # Supabase 클라이언트
│   │   ├── providers/            # LLM/TTS 프로바이더
│   │   ├── memory/               # RAG 시스템
│   │   ├── realtime/             # 실시간 훅
│   │   ├── events/               # 이벤트 시스템
│   │   └── utils/                # 유틸리티
│   │
│   ├── types/                    # TypeScript 타입
│   ├── styles/                   # 추가 스타일
│   └── middleware.ts             # Next.js 미들웨어
│
├── public/
│   ├── avatars/                  # 프리셋 아바타 모델
│   │   ├── vrm/
│   │   └── live2d/
│   ├── audio/                    # 오디오 파일
│   └── celebrities/              # 연예인 이미지
│
├── supabase/
│   └── migrations/               # DB 마이그레이션
│       ├── 001_init.sql
│       ├── 002_characters.sql
│       ├── 003_chat.sql
│       ├── 004_memory.sql
│       └── 005_rls.sql
│
├── .env.local                    # 로컬 환경변수
├── .env.example                  # 환경변수 예시
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── package.json
└── vercel.json
```

---

## 부록

### A. ADR (Architecture Decision Records)

| ID | 제목 | 상태 |
|----|------|------|
| ADR-001 | Vercel AI SDK 선택 | Accepted |
| ADR-002 | Supabase 통합 | Accepted |
| ADR-003 | VRM + Live2D 동시 지원 | Accepted |
| ADR-004 | Intent Priority Queue 도입 | Accepted |

### B. 관련 문서

- [AIRI-NEXTJS-REBUILD-ANALYSIS.md](../AIRI-NEXTJS-REBUILD-ANALYSIS.md)
- [AIRI-MISSING-FEATURES-REPORT.md](../AIRI-MISSING-FEATURES-REPORT.md)
- [AIRI-AVATAR-SYSTEM-VERIFICATION.md](../AIRI-AVATAR-SYSTEM-VERIFICATION.md)
