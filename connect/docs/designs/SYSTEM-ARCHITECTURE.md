# StarCall - System Architecture Document

## Document Info
| Field | Value |
|-------|-------|
| Version | 1.0 |
| Status | Draft |
| Created | 2026-02-28 |
| Author | DAVINCI System Architect |
| Parent | PLAN.md v1.1 |

---

## 1. Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           VERCEL EDGE NETWORK                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                     Next.js 14 Application                       │   │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │   │
│   │  │ iPhone   │  │ Phone    │  │ Messages │  │ SNS      │        │   │
│   │  │ UI Shell │  │ App      │  │ App      │  │ Apps     │        │   │
│   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │   │
│   │                                                                  │   │
│   │  ┌────────────────────────────────────────────────────────────┐ │   │
│   │  │                    API Routes (Edge)                        │ │   │
│   │  │  /api/chat  /api/voice  /api/image  /api/sns  /api/push    │ │   │
│   │  └────────────────────────────────────────────────────────────┘ │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
└────────────────────────────────────┼────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────┐
│                              SUPABASE                                    │
├────────────────────────────────────┼────────────────────────────────────┤
│   ┌──────────┐  ┌──────────┐  ┌───┴────┐  ┌──────────┐  ┌──────────┐  │
│   │ Auth     │  │ Database │  │Realtime│  │ Storage  │  │ Edge     │  │
│   │ (OAuth)  │  │ (Postgres│  │(WebSock│  │ (Images) │  │ Functions│  │
│   │          │  │ +pgvector│  │ et)    │  │          │  │          │  │
│   └──────────┘  └──────────┘  └────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────┐
│                         EXTERNAL SERVICES                                │
├────────────────────────────────────┼────────────────────────────────────┤
│   ┌──────────┐  ┌──────────┐  ┌───┴────┐  ┌──────────┐                 │
│   │ Gemini   │  │ TTS      │  │ Tavily │  │ Firebase │                 │
│   │ API      │  │ Server   │  │ Search │  │ FCM      │                 │
│   │ (Chat+Img│  │ (5002)   │  │        │  │          │                 │
│   └──────────┘  └──────────┘  └────────┘  └──────────┘                 │
└─────────────────────────────────────────────────────────────────────────┘
```

### Architecture Principles

| Principle | Implementation |
|-----------|----------------|
| **Serverless First** | Vercel Edge Functions + Supabase Edge Functions |
| **Real-time Native** | Supabase Realtime for WebSocket |
| **Database as Backend** | Supabase PostgreSQL + Row Level Security |
| **Edge Computing** | Vercel Edge Runtime for low latency |
| **Managed Services** | Auth, Storage, DB 모두 Supabase 관리형 |

---

## 2. Technology Stack (Updated)

### Updated Technology Stack

| Layer | Technology | Purpose | Rationale |
|-------|------------|---------|-----------|
| **Frontend** | Next.js 14 (App Router) | SSR, RSC, Routing | Vercel 최적화, 빠른 초기 로드 |
| **UI** | React 18 + Framer Motion | 60fps 애니메이션 | iPhone 느낌 구현 |
| **Styling** | Tailwind CSS + shadcn/ui | 빠른 개발 | 일관된 디자인 시스템 |
| **State** | Zustand + TanStack Query | 클라이언트/서버 상태 | 가볍고 효율적 |
| **Auth** | **Supabase Auth** | OAuth, Session | 관리형, RLS 연동 |
| **Database** | **Supabase PostgreSQL** | 관계형 + pgvector | 벡터 검색, RLS |
| **Realtime** | **Supabase Realtime** | WebSocket, Presence | 타이핑 인디케이터, 읽음 표시 |
| **Storage** | **Supabase Storage** | 이미지 저장 | CDN 연동, RLS |
| **Hosting** | **Vercel** | Edge Functions, CDN | Next.js 최적화, 글로벌 배포 |
| **Chat LLM** | Gemini 3.0 Flash | 텍스트 응답 | 빠른 응답, 비용 효율 |
| **Image Gen** | Gemini 3.1 Flash Image | 이미지 생성 | 실시간 사진 공유 |
| **Voice** | 기존 TTS Server | 음성 합성 | 이미 구축된 인프라 |
| **Search** | Tavily API | 실시간 웹 검색 | 최신 정보 반영 |
| **Push** | Firebase FCM | 푸시 알림 | 크로스 플랫폼 |

### Stack Migration from PLAN.md

| Component | PLAN.md (이전) | SYSTEM (변경) | 이유 |
|-----------|---------------|---------------|------|
| Database | PostgreSQL 직접 | Supabase | 관리형, RLS, Realtime 통합 |
| Auth | NextAuth.js | Supabase Auth | DB와 통합, RLS 연동 |
| Cache | Redis | Supabase + Vercel KV | 관리형, 글로벌 배포 |
| WebSocket | Socket.io | Supabase Realtime | 관리형, Presence 지원 |
| Infra | Docker + nginx | Vercel | 서버리스, 자동 스케일링 |
| Storage | 로컬/S3 | Supabase Storage | CDN, RLS, 관리형 |

---

## 3. C4 Model - Container Diagram (Level 2)

### Container Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              StarCall System                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────── VERCEL ────────────────────────────────┐  │
│  │                                                                        │  │
│  │  ┌────────────────────────────────────────────────────────────────┐   │  │
│  │  │              Next.js 14 App (React Server Components)           │   │  │
│  │  │                                                                 │   │  │
│  │  │  Pages (App Router)           │  Components                    │   │  │
│  │  │  ├── /                        │  ├── IPhoneShell              │   │  │
│  │  │  ├── /phone                   │  ├── PhoneApp                 │   │  │
│  │  │  ├── /messages                │  ├── MessagesApp              │   │  │
│  │  │  ├── /messages/[celebrity]    │  ├── ChatBubble               │   │  │
│  │  │  ├── /threads                 │  ├── ThreadsFeed              │   │  │
│  │  │  └── /instagram               │  └── InstagramFeed            │   │  │
│  │  └────────────────────────────────────────────────────────────────┘   │  │
│  │                                    │                                   │  │
│  │  ┌────────────────────────────────┼────────────────────────────────┐  │  │
│  │  │           API Routes (Edge Runtime)                              │  │  │
│  │  │                                │                                 │  │  │
│  │  │  /api/chat/send           → Gemini 3.0 Flash (텍스트)           │  │  │
│  │  │  /api/chat/image          → Gemini 3.1 Flash (이미지 생성)      │  │  │
│  │  │  /api/voice/connect       → TTS Server WebSocket Proxy          │  │  │
│  │  │  /api/persona/context     → RAG 컨텍스트 조회                   │  │  │
│  │  │  /api/sns/feed            → SNS 피드 조회                       │  │  │
│  │  │  /api/push/trigger        → FCM 푸시 발송                       │  │  │
│  │  │  /api/cron/proactive      → 선제적 연락 (Vercel Cron)           │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                       │                                      │
│  ┌────────────────────────────────────┼─────────────────────────────────┐   │
│  │                              SUPABASE                                 │   │
│  │                                    │                                  │   │
│  │  ┌──────────────┐  ┌──────────────┼──────────────┐  ┌─────────────┐  │   │
│  │  │    Auth      │  │         Database            │  │   Storage   │  │   │
│  │  │              │  │                             │  │             │  │   │
│  │  │ - OAuth2     │  │  users          │ RLS ✓    │  │ - avatars/  │  │   │
│  │  │ - Session    │  │  celebrities    │ RLS ✓    │  │ - generated/│  │   │
│  │  │ - JWT        │  │  conversations  │ RLS ✓    │  │ - sns/      │  │   │
│  │  │              │  │  messages       │ RLS ✓    │  │             │  │   │
│  │  └──────────────┘  │  memory_vectors │ RLS ✓    │  └─────────────┘  │   │
│  │                    │  sns_posts      │ RLS ✓    │                   │   │
│  │  ┌──────────────┐  │  schedules      │ RLS ✓    │  ┌─────────────┐  │   │
│  │  │   Realtime   │  └─────────────────────────────┘  │Edge Function│  │   │
│  │  │              │                                   │             │  │   │
│  │  │ - Broadcast  │  ┌─────────────────────────────┐  │ - sns-sync  │  │   │
│  │  │ - Presence   │  │       pgvector Extension    │  │ - cleanup   │  │   │
│  │  │ - Postgres   │  │  (Memory RAG)               │  │             │  │   │
│  │  │   Changes    │  └─────────────────────────────┘  └─────────────┘  │   │
│  │  └──────────────┘                                                    │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │                        EXTERNAL SERVICES                               │   │
│  │                                                                        │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │   │
│  │  │ Gemini API   │  │ TTS Server   │  │ Tavily API   │  │ Firebase  │  │   │
│  │  │              │  │              │  │              │  │ FCM       │  │   │
│  │  │ gemini-3.0-  │  │ Port 5002    │  │ Web Search   │  │           │  │   │
│  │  │ flash        │  │ WebSocket    │  │ (실시간 정보)│  │ Push      │  │   │
│  │  │ gemini-3.1-  │  │              │  │              │  │ Notif     │  │   │
│  │  │ flash-image  │  │              │  │              │  │           │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └───────────┘  │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Container Responsibilities

| Container | Technology | Responsibility |
|-----------|------------|----------------|
| **Next.js App** | React 18, App Router | UI 렌더링, 클라이언트 상태 관리 |
| **API Routes** | Vercel Edge Runtime | 비즈니스 로직, 외부 API 프록시 |
| **Supabase Auth** | GoTrue | 인증, 세션, JWT 발급 |
| **Supabase DB** | PostgreSQL 15 | 영구 데이터 저장, RLS |
| **Supabase Realtime** | Phoenix Channels | 실시간 메시지, Presence |
| **Supabase Storage** | S3 Compatible | 이미지 저장, CDN |
| **Supabase Edge** | Deno | 백그라운드 작업 (SNS Sync) |

---

## 4. C4 Model - Component Diagram (Level 3)

### Frontend Component Architecture

```
src/
├── app/                          # Next.js App Router
│   ├── layout.tsx                # Root layout (providers)
│   ├── page.tsx                  # Landing page
│   ├── (phone)/                  # iPhone UI Group
│   │   ├── layout.tsx            # IPhoneShell wrapper
│   │   ├── home/page.tsx         # Home screen
│   │   ├── phone/                # Phone App
│   │   │   ├── page.tsx          # Contacts list
│   │   │   ├── [id]/page.tsx     # Contact detail
│   │   │   └── call/[id]/page.tsx# Active call UI
│   │   ├── messages/             # Messages App
│   │   │   ├── page.tsx          # Conversations list
│   │   │   └── [id]/page.tsx     # Chat room
│   │   ├── threads/page.tsx      # Threads feed
│   │   └── instagram/page.tsx    # Instagram feed
│   └── api/                      # API Routes
│       ├── chat/
│       │   ├── send/route.ts     # POST: Send message
│       │   └── image/route.ts    # POST: Generate image
│       ├── voice/
│       │   └── connect/route.ts  # WebSocket proxy
│       ├── persona/
│       │   └── context/route.ts  # GET: RAG context
│       └── cron/
│           └── proactive/route.ts# Cron: Proactive contact
│
├── components/
│   ├── iphone/                   # iPhone UI Components
│   │   ├── IPhoneFrame.tsx       # Phone frame (notch, corners)
│   │   ├── StatusBar.tsx         # Time, battery, wifi
│   │   ├── HomeScreen.tsx        # App icons grid
│   │   ├── AppIcon.tsx           # Individual app icon
│   │   └── NavigationBar.tsx     # Bottom swipe indicator
│   │
│   ├── phone/                    # Phone App Components
│   │   ├── ContactList.tsx       # Celebrity contacts
│   │   ├── ContactCard.tsx       # Individual contact
│   │   ├── DialPad.tsx           # Dial animation
│   │   ├── CallScreen.tsx        # Active call UI
│   │   └── CallControls.tsx      # Mute, speaker, end
│   │
│   ├── messages/                 # Messages App Components
│   │   ├── ConversationList.tsx  # Chat list
│   │   ├── ChatRoom.tsx          # Message thread
│   │   ├── ChatBubble.tsx        # Message bubble
│   │   ├── ImageBubble.tsx       # Image message
│   │   ├── TypingIndicator.tsx   # "..." animation
│   │   └── MessageInput.tsx      # Text input
│   │
│   └── sns/                      # SNS App Components
│       ├── FeedPost.tsx          # Post card
│       ├── CommentSection.tsx    # Comments
│       └── StoryViewer.tsx       # Stories
│
├── hooks/
│   ├── useChat.ts                # Chat logic (TanStack Query)
│   ├── useVoiceCall.ts           # Voice call WebSocket
│   ├── useRealtime.ts            # Supabase Realtime
│   ├── usePresence.ts            # Online/typing status
│   └── usePersona.ts             # Persona context
│
├── lib/
│   ├── supabase/
│   │   ├── client.ts             # Browser client
│   │   ├── server.ts             # Server client
│   │   └── admin.ts              # Admin client (service role)
│   ├── gemini/
│   │   ├── chat.ts               # Gemini 3.0 Flash
│   │   └── image.ts              # Gemini 3.1 Image
│   └── utils/
│       ├── intent-detector.ts    # "지금 뭐해?" 감지
│       └── context-builder.ts    # 이미지 생성 컨텍스트
│
├── stores/
│   ├── app-store.ts              # 현재 앱 상태 (Zustand)
│   ├── call-store.ts             # 통화 상태
│   └── chat-store.ts             # 채팅 상태
│
└── types/
    ├── database.types.ts         # Supabase generated types
    ├── celebrity.ts              # Celebrity type
    ├── message.ts                # Message type
    └── api.ts                    # API request/response
```

### API Route Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    /api/chat/send (Edge)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │   Request    │────▶│   Intent     │────▶│   Context    │    │
│  │   Parser     │     │   Detector   │     │   Builder    │    │
│  └──────────────┘     └──────────────┘     └──────────────┘    │
│                              │                    │             │
│                              ▼                    ▼             │
│                       ┌──────────────┐     ┌──────────────┐    │
│                       │ "뭐해?" 감지 │     │  RAG Query   │    │
│                       │   (regex)    │     │  (pgvector)  │    │
│                       └──────────────┘     └──────────────┘    │
│                              │                    │             │
│                              ▼                    ▼             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                     Gemini Service                        │  │
│  │  ┌────────────────┐              ┌────────────────────┐  │  │
│  │  │ gemini-3.0-    │   OR         │ gemini-3.1-flash-  │  │  │
│  │  │ flash (텍스트) │              │ image (이미지생성) │  │  │
│  │  └────────────────┘              └────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   Response Handler                        │  │
│  │  - 메시지 저장 (Supabase)                                │  │
│  │  - 이미지 저장 (Storage)                                  │  │
│  │  - Realtime broadcast                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 5. Database Schema (Supabase)

### Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     users       │       │   celebrities   │       │  conversations  │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (uuid) PK    │       │ id (uuid) PK    │       │ id (uuid) PK    │
│ email           │       │ name            │       │ user_id FK      │──┐
│ display_name    │       │ persona_prompt  │       │ celebrity_id FK │──┼──┐
│ avatar_url      │       │ voice_id        │       │ intimacy_level  │  │  │
│ fcm_token       │       │ avatar_url      │       │ last_message_at │  │  │
│ preferences     │       │ status          │       │ unread_count    │  │  │
│ created_at      │       │ schedule_data   │       │ created_at      │  │  │
│ updated_at      │       │ knowledge_base  │       │ updated_at      │  │  │
└────────┬────────┘       └────────┬────────┘       └─────────────────┘  │  │
         │                         │                         ▲           │  │
         │                         │                         │           │  │
         │     ┌───────────────────┴─────────────────────────┘           │  │
         │     │                                                         │  │
         ▼     ▼                                                         │  │
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐  │  │
│    messages     │       │ memory_vectors  │       │   sns_posts     │  │  │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤  │  │
│ id (uuid) PK    │       │ id (uuid) PK    │       │ id (uuid) PK    │  │  │
│ conversation_id │◀──────│ conversation_id │       │ celebrity_id FK │◀─┼──┘
│ sender (enum)   │       │ content         │       │ platform (enum) │  │
│ content         │       │ embedding (vec) │       │ external_id     │  │
│ message_type    │       │ metadata        │       │ content         │  │
│ image_url       │       │ created_at      │       │ media_urls      │  │
│ is_read         │       └─────────────────┘       │ likes_count     │  │
│ created_at      │                                 │ posted_at       │  │
└─────────────────┘       ┌─────────────────┐       │ synced_at       │  │
                          │   schedules     │       └─────────────────┘  │
                          ├─────────────────┤                            │
                          │ id (uuid) PK    │       ┌─────────────────┐  │
                          │ celebrity_id FK │◀──────│  user_comments  │  │
                          │ title           │       ├─────────────────┤  │
                          │ start_time      │       │ id (uuid) PK    │  │
                          │ end_time        │       │ post_id FK      │  │
                          │ location        │       │ user_id FK      │◀─┘
                          │ activity_type   │       │ content         │
                          └─────────────────┘       │ ai_reply        │
                                                    │ created_at      │
                                                    └─────────────────┘
```

### Table Definitions

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table (extends Supabase auth.users)
CREATE TABLE public.users (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  display_name TEXT,
  avatar_url TEXT,
  fcm_token TEXT,
  preferences JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Celebrities table
CREATE TABLE public.celebrities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  persona_prompt TEXT NOT NULL,          -- 페르소나 시스템 프롬프트
  voice_id TEXT NOT NULL,                -- TTS 음성 ID (예: 'gd-icl')
  avatar_url TEXT,
  status TEXT DEFAULT 'available',       -- available, busy, offline
  schedule_data JSONB DEFAULT '[]',      -- 스케줄 정보
  knowledge_base JSONB DEFAULT '{}',     -- 기본 지식 (생년월일, 경력 등)
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversations table
CREATE TABLE public.conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  celebrity_id UUID NOT NULL REFERENCES public.celebrities(id) ON DELETE CASCADE,
  intimacy_level INTEGER DEFAULT 0,      -- 친밀도 (0-100)
  last_message_at TIMESTAMPTZ,
  unread_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, celebrity_id)
);

-- Messages table
CREATE TABLE public.messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
  sender TEXT NOT NULL CHECK (sender IN ('user', 'celebrity')),
  content TEXT NOT NULL,
  message_type TEXT DEFAULT 'text' CHECK (message_type IN ('text', 'image', 'voice', 'call')),
  image_url TEXT,                        -- 이미지 메시지 URL
  is_read BOOLEAN DEFAULT FALSE,
  metadata JSONB DEFAULT '{}',           -- 추가 메타데이터
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Memory vectors for RAG
CREATE TABLE public.memory_vectors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
  content TEXT NOT NULL,                 -- 원본 텍스트
  embedding VECTOR(1536),                -- OpenAI embedding 차원
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create vector similarity search index
CREATE INDEX ON public.memory_vectors
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- SNS posts table
CREATE TABLE public.sns_posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  celebrity_id UUID NOT NULL REFERENCES public.celebrities(id) ON DELETE CASCADE,
  platform TEXT NOT NULL CHECK (platform IN ('threads', 'instagram')),
  external_id TEXT NOT NULL,             -- 원본 플랫폼의 post ID
  content TEXT,
  media_urls TEXT[] DEFAULT '{}',
  likes_count INTEGER DEFAULT 0,
  posted_at TIMESTAMPTZ,
  synced_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(platform, external_id)
);

-- Schedules table
CREATE TABLE public.schedules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  celebrity_id UUID NOT NULL REFERENCES public.celebrities(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  start_time TIMESTAMPTZ NOT NULL,
  end_time TIMESTAMPTZ,
  location TEXT,
  activity_type TEXT,                    -- recording, filming, rest, etc.
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User comments on SNS posts
CREATE TABLE public.user_comments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id UUID NOT NULL REFERENCES public.sns_posts(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  ai_reply TEXT,                         -- AI가 생성한 답글
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Row Level Security Policies

```sql
-- Enable RLS on all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memory_vectors ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_comments ENABLE ROW LEVEL SECURITY;

-- Users: 자신의 데이터만 접근
CREATE POLICY "Users can view own profile"
  ON public.users FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON public.users FOR UPDATE
  USING (auth.uid() = id);

-- Conversations: 자신의 대화만 접근
CREATE POLICY "Users can view own conversations"
  ON public.conversations FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create conversations"
  ON public.conversations FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Messages: 자신의 대화에 속한 메시지만 접근
CREATE POLICY "Users can view messages in own conversations"
  ON public.messages FOR SELECT
  USING (
    conversation_id IN (
      SELECT id FROM public.conversations WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "Users can insert messages in own conversations"
  ON public.messages FOR INSERT
  WITH CHECK (
    conversation_id IN (
      SELECT id FROM public.conversations WHERE user_id = auth.uid()
    )
  );

-- Celebrities: 모든 사용자가 조회 가능
CREATE POLICY "Anyone can view celebrities"
  ON public.celebrities FOR SELECT
  USING (true);

-- SNS Posts: 모든 사용자가 조회 가능
CREATE POLICY "Anyone can view sns posts"
  ON public.sns_posts FOR SELECT
  USING (true);
```

### Database Indexes

```sql
-- Performance indexes
CREATE INDEX idx_conversations_user ON public.conversations(user_id);
CREATE INDEX idx_conversations_celebrity ON public.conversations(celebrity_id);
CREATE INDEX idx_conversations_last_message ON public.conversations(last_message_at DESC);

CREATE INDEX idx_messages_conversation ON public.messages(conversation_id);
CREATE INDEX idx_messages_created ON public.messages(created_at DESC);

CREATE INDEX idx_memory_conversation ON public.memory_vectors(conversation_id);

CREATE INDEX idx_sns_posts_celebrity ON public.sns_posts(celebrity_id);
CREATE INDEX idx_sns_posts_posted ON public.sns_posts(posted_at DESC);

CREATE INDEX idx_schedules_celebrity ON public.schedules(celebrity_id);
CREATE INDEX idx_schedules_time ON public.schedules(start_time);
```

---

## 6. API Design

### API Endpoints Overview

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/chat/send` | 문자 메시지 전송 | ✓ |
| POST | `/api/chat/image` | 이미지 생성 요청 | ✓ |
| GET | `/api/persona/context` | RAG 컨텍스트 조회 | ✓ |
| POST | `/api/voice/connect` | 음성통화 WebSocket 프록시 | ✓ |
| GET | `/api/sns/feed` | SNS 피드 조회 | ✓ |
| POST | `/api/sns/comment` | SNS 댓글 작성 | ✓ |
| POST | `/api/push/register` | FCM 토큰 등록 | ✓ |
| POST | `/api/cron/proactive` | 선제적 연락 (Vercel Cron) | Internal |
| POST | `/api/cron/sns-sync` | SNS 동기화 (Vercel Cron) | Internal |

### API Specifications

#### POST /api/chat/send
```typescript
// Request
interface ChatSendRequest {
  celebrity_id: string;
  message: string;
}

// Response
interface ChatSendResponse {
  success: boolean;
  user_message: Message;
  ai_response: Message;
  generated_image?: {
    url: string;
    caption: string;
  };
}

// Example
POST /api/chat/send
{
  "celebrity_id": "gd-uuid",
  "message": "지금 뭐해?"
}

// Response (with image generation)
{
  "success": true,
  "user_message": {
    "id": "msg-1",
    "sender": "user",
    "content": "지금 뭐해?",
    "message_type": "text",
    "created_at": "2026-02-28T15:00:00Z"
  },
  "ai_response": {
    "id": "msg-2",
    "sender": "celebrity",
    "content": "녹음 중이야~ 🎤",
    "message_type": "image",
    "image_url": "https://xxx.supabase.co/storage/v1/object/generated/...",
    "created_at": "2026-02-28T15:00:02Z"
  },
  "generated_image": {
    "url": "https://xxx.supabase.co/storage/v1/object/generated/...",
    "caption": "녹음 중이야~ 🎤"
  }
}
```

#### POST /api/chat/image
```typescript
// Request (manual image generation)
interface ImageGenerateRequest {
  celebrity_id: string;
  context: {
    activity: string;
    time_of_day: string;
    location?: string;
  };
}

// Response
interface ImageGenerateResponse {
  success: boolean;
  image_url: string;
  caption: string;
}
```

#### GET /api/persona/context
```typescript
// Request
GET /api/persona/context?celebrity_id=xxx&query=어제 대화 내용

// Response
interface PersonaContextResponse {
  memories: Array<{
    content: string;
    similarity: number;
    created_at: string;
  }>;
  schedule: Array<{
    title: string;
    time: string;
    activity_type: string;
  }>;
  recent_sns: Array<{
    content: string;
    posted_at: string;
  }>;
}
```

#### POST /api/voice/connect
```typescript
// WebSocket Upgrade
// Client → Vercel → TTS Server (ws://localhost:5002/ws/voice/call)

// Initial handshake
{
  "type": "connect",
  "celebrity_id": "gd-uuid",
  "conversation_id": "conv-uuid"
}

// Audio stream (client → server)
{
  "type": "audio",
  "data": "base64_encoded_audio"
}

// Response stream (server → client)
{
  "type": "response",
  "audio": "base64_encoded_tts",
  "text": "여보세요?"
}

// Call end
{
  "type": "end",
  "duration": 120,
  "summary": "통화 요약..."
}
```

#### Vercel Cron Jobs
```typescript
// vercel.json
{
  "crons": [
    {
      "path": "/api/cron/proactive",
      "schedule": "0 9,21 * * *"  // 매일 9시, 21시
    },
    {
      "path": "/api/cron/sns-sync",
      "schedule": "0 */6 * * *"   // 6시간마다
    }
  ]
}
```

---

## 7. Real-time Architecture

### Supabase Realtime Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      REALTIME FEATURES                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. POSTGRES CHANGES (Database → Client)                            │
│  ──────────────────────────────────────                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐           │
│  │ messages    │────▶│ Supabase    │────▶│ Client      │           │
│  │ INSERT      │     │ Realtime    │     │ Subscription│           │
│  └─────────────┘     └─────────────┘     └─────────────┘           │
│                                                                      │
│  Channel: `messages:conversation_id=eq.{conv_id}`                   │
│  Event: INSERT → 새 메시지 알림                                     │
│  Event: UPDATE → 읽음 상태 변경                                     │
│                                                                      │
│  2. BROADCAST (Client ↔ Client via Server)                          │
│  ──────────────────────────────────────                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐           │
│  │ Client A    │────▶│ Supabase    │────▶│ Client B    │           │
│  │ (typing)    │     │ Broadcast   │     │ (show ...)  │           │
│  └─────────────┘     └─────────────┘     └─────────────┘           │
│                                                                      │
│  Channel: `typing:{celebrity_id}`                                   │
│  Event: typing_start → 타이핑 인디케이터 표시                       │
│  Event: typing_stop → 타이핑 인디케이터 숨김                        │
│                                                                      │
│  3. PRESENCE (Online Status)                                        │
│  ──────────────────────────────────────                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐           │
│  │ Celebrity   │────▶│ Supabase    │────▶│ All Users   │           │
│  │ Status      │     │ Presence    │     │ Subscribed  │           │
│  └─────────────┘     └─────────────┘     └─────────────┘           │
│                                                                      │
│  Channel: `presence:celebrity:{id}`                                 │
│  State: { status: 'available' | 'busy' | 'offline' }               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Realtime Implementation

```typescript
// lib/supabase/realtime.ts
import { createClient } from '@supabase/supabase-js';
import type { RealtimeChannel } from '@supabase/supabase-js';

export function subscribeToMessages(
  conversationId: string,
  onMessage: (message: Message) => void
): RealtimeChannel {
  const supabase = createClient(/* ... */);

  return supabase
    .channel(`messages:${conversationId}`)
    .on(
      'postgres_changes',
      {
        event: 'INSERT',
        schema: 'public',
        table: 'messages',
        filter: `conversation_id=eq.${conversationId}`,
      },
      (payload) => {
        onMessage(payload.new as Message);
      }
    )
    .subscribe();
}

export function broadcastTyping(
  celebrityId: string,
  isTyping: boolean
): void {
  const supabase = createClient(/* ... */);

  supabase
    .channel(`typing:${celebrityId}`)
    .send({
      type: 'broadcast',
      event: isTyping ? 'typing_start' : 'typing_stop',
      payload: { timestamp: Date.now() },
    });
}

export function trackCelebrityPresence(
  celebrityId: string,
  onStatusChange: (status: string) => void
): RealtimeChannel {
  const supabase = createClient(/* ... */);

  return supabase
    .channel(`presence:celebrity:${celebrityId}`)
    .on('presence', { event: 'sync' }, () => {
      const state = channel.presenceState();
      // ... handle state
    })
    .subscribe();
}
```

### Realtime Use Cases

| Feature | Channel Type | Event |
|---------|-------------|-------|
| 새 메시지 수신 | Postgres Changes | INSERT on messages |
| 읽음 표시 업데이트 | Postgres Changes | UPDATE on messages |
| 타이핑 인디케이터 | Broadcast | typing_start/stop |
| 연예인 상태 | Presence | status change |
| 새 SNS 포스트 | Postgres Changes | INSERT on sns_posts |
| 선제적 연락 알림 | Broadcast | proactive_contact |

---

## 8. External Service Integration

### External Service Integration Map

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      EXTERNAL SERVICE INTEGRATIONS                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     GEMINI API (Google AI)                       │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │                                                                  │   │
│  │  Chat (gemini-3.0-flash)           Image (gemini-3.1-flash-img) │   │
│  │  ├── 페르소나 응답 생성              ├── "뭐해?" 이미지 생성     │   │
│  │  ├── RAG 컨텍스트 통합               ├── 상황별 이미지 템플릿    │   │
│  │  └── 웹 검색 결과 반영               └── Safety filter 적용     │   │
│  │                                                                  │   │
│  │  Endpoints:                                                      │   │
│  │  - https://generativelanguage.googleapis.com/v1beta/models/     │   │
│  │  - Rate Limit: 1500 QPM (flash), 100 QPM (image)                │   │
│  │  - API Key: GOOGLE_AI_API_KEY                                   │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     TTS SERVER (Self-hosted)                     │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │                                                                  │   │
│  │  Location: localhost:5002 (또는 ngrok 터널)                      │   │
│  │  Protocol: WebSocket                                             │   │
│  │  Endpoint: /ws/voice/call                                        │   │
│  │                                                                  │   │
│  │  Features:                                                       │   │
│  │  ├── STT (Whisper) - 사용자 음성 → 텍스트                        │   │
│  │  ├── LLM (Gemini) - 응답 생성                                    │   │
│  │  └── TTS (GD Voice) - 텍스트 → 음성                              │   │
│  │                                                                  │   │
│  │  Env: TTS_SERVER_URL=wss://crossconnect.ngrok.app               │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     TAVILY API (Web Search)                      │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │                                                                  │   │
│  │  Use Case: 실시간 정보 검색 (뉴스, 스케줄, 활동)                 │   │
│  │                                                                  │   │
│  │  Trigger:                                                        │   │
│  │  ├── "어제 뮤뱅 어땠어?" → 뮤뱅 검색                             │   │
│  │  ├── 시사 관련 질문 → 뉴스 검색                                  │   │
│  │  └── 최신 활동 질문 → SNS/기사 검색                              │   │
│  │                                                                  │   │
│  │  Endpoint: https://api.tavily.com/search                        │   │
│  │  Rate Limit: 1000 req/day (Free), unlimited (Pro)               │   │
│  │  Env: TAVILY_API_KEY                                            │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     FIREBASE FCM (Push Notifications)            │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │                                                                  │   │
│  │  Use Case: 선제적 연락, 부재중 전화 알림                         │   │
│  │                                                                  │   │
│  │  Notification Types:                                             │   │
│  │  ├── proactive_message: "GD: 잘 잤어? ㅎㅎ"                      │   │
│  │  ├── missed_call: "GD님이 전화했어요"                            │   │
│  │  └── new_post: "GD님이 새 글을 올렸어요"                         │   │
│  │                                                                  │   │
│  │  Env: FIREBASE_SERVICE_ACCOUNT (JSON)                           │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Environment Variables

```bash
# .env.local (Vercel Environment Variables)

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGci...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...      # Server-only

# Google AI (Gemini)
GOOGLE_AI_API_KEY=AIza...

# TTS Server
TTS_SERVER_URL=wss://crossconnect.ngrok.app
TTS_SERVER_LOCAL=ws://localhost:5002       # Fallback

# Tavily
TAVILY_API_KEY=tvly-...

# Firebase
FIREBASE_PROJECT_ID=starcall-xxx
FIREBASE_CLIENT_EMAIL=firebase-adminsdk@...
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."

# Vercel
VERCEL_URL=https://starcall.vercel.app
CRON_SECRET=xxx                            # Cron job authentication
```

---

## 9. Security Architecture

### Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SECURITY LAYERS                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Layer 1: NETWORK                                                        │
│  ─────────────────                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  • HTTPS only (Vercel auto-provision)                           │   │
│  │  • CORS: only starcall.vercel.app                               │   │
│  │  • Rate limiting: Vercel Edge + Supabase                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Layer 2: AUTHENTICATION                                                 │
│  ─────────────────────────                                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Provider: Supabase Auth                                        │   │
│  │                                                                  │   │
│  │  OAuth Providers:                                                │   │
│  │  ├── Google (primary)                                           │   │
│  │  ├── Kakao (한국 사용자)                                         │   │
│  │  └── Apple (iOS 사용자)                                          │   │
│  │                                                                  │   │
│  │  Token Flow:                                                     │   │
│  │  1. User → OAuth Provider → Authorization Code                  │   │
│  │  2. Supabase → Verify → Issue JWT (access + refresh)            │   │
│  │  3. Client stores in httpOnly cookie (Supabase handles)         │   │
│  │  4. JWT auto-refresh before expiry                              │   │
│  │                                                                  │   │
│  │  JWT Claims:                                                     │   │
│  │  {                                                               │   │
│  │    "sub": "user-uuid",                                          │   │
│  │    "email": "user@email.com",                                   │   │
│  │    "role": "authenticated",                                     │   │
│  │    "exp": 1234567890                                            │   │
│  │  }                                                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Layer 3: AUTHORIZATION (Row Level Security)                            │
│  ───────────────────────────────────────────                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │  RLS Policies (Supabase):                                       │   │
│  │  ┌─────────────────────────────────────────────────────────┐   │   │
│  │  │ Table          │ SELECT    │ INSERT    │ UPDATE/DELETE │   │   │
│  │  ├─────────────────────────────────────────────────────────┤   │   │
│  │  │ users          │ own only  │ own only  │ own only      │   │   │
│  │  │ conversations  │ own only  │ own only  │ own only      │   │   │
│  │  │ messages       │ own conv  │ own conv  │ -             │   │   │
│  │  │ memory_vectors │ own conv  │ service   │ -             │   │   │
│  │  │ celebrities    │ all       │ admin     │ admin         │   │   │
│  │  │ sns_posts      │ all       │ service   │ service       │   │   │
│  │  │ schedules      │ all       │ admin     │ admin         │   │   │
│  │  └─────────────────────────────────────────────────────────┘   │   │
│  │                                                                  │   │
│  │  auth.uid() = user_id 패턴으로 자동 필터링                       │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Layer 4: API SECURITY                                                   │
│  ─────────────────────                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │  API Route Protection:                                          │   │
│  │  ```typescript                                                  │   │
│  │  // middleware.ts                                               │   │
│  │  export async function middleware(request: NextRequest) {       │   │
│  │    const supabase = createMiddlewareClient({ req, res });      │   │
│  │    const { data: { session } } = await supabase.auth.getSession();│ │
│  │                                                                  │   │
│  │    if (!session && request.nextUrl.pathname.startsWith('/api')) {│   │
│  │      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });│
│  │    }                                                            │   │
│  │    return NextResponse.next();                                  │   │
│  │  }                                                              │   │
│  │  ```                                                            │   │
│  │                                                                  │   │
│  │  Cron Job Protection:                                           │   │
│  │  ```typescript                                                  │   │
│  │  // api/cron/proactive/route.ts                                │   │
│  │  if (request.headers.get('Authorization') !== `Bearer ${process.env.CRON_SECRET}`) {│
│  │    return Response.json({ error: 'Forbidden' }, { status: 403 });│   │
│  │  }                                                              │   │
│  │  ```                                                            │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Layer 5: DATA PROTECTION                                                │
│  ────────────────────────                                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │  Encryption:                                                     │   │
│  │  • At Rest: Supabase (AES-256)                                  │   │
│  │  • In Transit: TLS 1.3                                          │   │
│  │  • API Keys: Vercel encrypted env vars                          │   │
│  │                                                                  │   │
│  │  PII Handling:                                                   │   │
│  │  • Email: stored, RLS protected                                 │   │
│  │  • FCM Token: stored, RLS protected                             │   │
│  │  • Conversation: RLS protected, user-specific                   │   │
│  │  • Voice recordings: NOT stored (streaming only)                │   │
│  │                                                                  │   │
│  │  Data Retention:                                                 │   │
│  │  • Messages: 1 year                                             │   │
│  │  • Memory vectors: 1 year                                       │   │
│  │  • Generated images: 30 days                                    │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### OWASP Top 10 Mitigation

| Vulnerability | Mitigation |
|---------------|------------|
| **A01: Broken Access Control** | Supabase RLS, middleware auth check |
| **A02: Cryptographic Failures** | TLS 1.3, AES-256, no plaintext secrets |
| **A03: Injection** | Parameterized queries (Supabase client) |
| **A04: Insecure Design** | Defense in depth, principle of least privilege |
| **A05: Security Misconfiguration** | Vercel security defaults, strict CORS |
| **A06: Vulnerable Components** | Dependabot, npm audit |
| **A07: Auth Failures** | Supabase Auth, OAuth only, no passwords |
| **A08: Data Integrity Failures** | RLS, service role isolation |
| **A09: Logging Failures** | Vercel logs, Supabase audit logs |
| **A10: SSRF** | Input validation, allowlisted external services |

---

## 10. Deployment Architecture (Vercel)

### Vercel Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        VERCEL DEPLOYMENT                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     EDGE NETWORK (Global)                        │   │
│  │                                                                  │   │
│  │   Seoul ──┬── Tokyo ──┬── Singapore                             │   │
│  │           │           │                                          │   │
│  │   ┌───────┴───────────┴───────┐                                 │   │
│  │   │    Vercel Edge Runtime     │                                │   │
│  │   │    (API Routes, Middleware)│                                │   │
│  │   └───────────────────────────┘                                 │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     BUILD OUTPUT                                 │   │
│  │                                                                  │   │
│  │   Static Files          Server Components      Edge Functions   │   │
│  │   ├── _next/static/     ├── RSC Payload       ├── api/chat/    │   │
│  │   ├── images/           ├── Streaming         ├── api/voice/   │   │
│  │   └── fonts/            └── Suspense          └── middleware    │   │
│  │                                                                  │   │
│  │   CDN Cached            Server Rendered        Edge Executed    │   │
│  │   (31 days)             (per request)          (< 25ms cold)    │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Deployment Configuration

```json
// vercel.json
{
  "framework": "nextjs",
  "regions": ["icn1"],  // Seoul (primary for Korean users)
  "functions": {
    "api/**/*.ts": {
      "runtime": "edge",
      "maxDuration": 30
    },
    "api/cron/**/*.ts": {
      "runtime": "nodejs20.x",
      "maxDuration": 60
    }
  },
  "crons": [
    {
      "path": "/api/cron/proactive",
      "schedule": "0 9,21 * * *"
    },
    {
      "path": "/api/cron/sns-sync",
      "schedule": "0 */6 * * *"
    }
  ],
  "headers": [
    {
      "source": "/api/(.*)",
      "headers": [
        { "key": "Access-Control-Allow-Origin", "value": "https://starcall.vercel.app" },
        { "key": "Access-Control-Allow-Methods", "value": "GET, POST, OPTIONS" },
        { "key": "Access-Control-Allow-Headers", "value": "Content-Type, Authorization" }
      ]
    }
  ]
}
```

### CI/CD Pipeline

```yaml
# GitHub Actions + Vercel
┌─────────────────────────────────────────────────────────────────┐
│                      CI/CD PIPELINE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Push to main                                                    │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────┐                                                │
│  │    Lint     │  ESLint + Prettier                             │
│  │   (30s)     │                                                │
│  └─────────────┘                                                │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────┐                                                │
│  │    Type     │  TypeScript strict                             │
│  │   Check     │                                                │
│  │   (45s)     │                                                │
│  └─────────────┘                                                │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────┐                                                │
│  │    Test     │  Vitest + Testing Library                      │
│  │   (2min)    │                                                │
│  └─────────────┘                                                │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────┐                                                │
│  │   Build     │  next build                                    │
│  │   (3min)    │                                                │
│  └─────────────┘                                                │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────┐  ┌─────────────┐                               │
│  │  Preview    │  │ Production  │  (main branch only)           │
│  │  Deploy     │  │   Deploy    │                               │
│  └─────────────┘  └─────────────┘                               │
│                                                                  │
│  Preview URL: starcall-xxx-preview.vercel.app                   │
│  Production:  starcall.vercel.app                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Environment Setup

```bash
# 1. Vercel CLI 설치 및 로그인
npm i -g vercel
vercel login

# 2. 프로젝트 연결
vercel link

# 3. 환경 변수 설정
vercel env add NEXT_PUBLIC_SUPABASE_URL production
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production
vercel env add SUPABASE_SERVICE_ROLE_KEY production
vercel env add GOOGLE_AI_API_KEY production
vercel env add TAVILY_API_KEY production
vercel env add TTS_SERVER_URL production
vercel env add CRON_SECRET production

# 4. Supabase 연결
vercel integrations add supabase

# 5. 배포
vercel --prod
```

---

## 11. Performance & Scalability

### Performance Targets & Optimization

#### Latency Targets

| Operation | Target | P95 | Strategy |
|-----------|--------|-----|----------|
| Page Load (LCP) | < 2.5s | < 3s | RSC, Edge, CDN |
| Chat Response | < 2s | < 3s | Edge Runtime, Streaming |
| Image Generation | < 3s | < 5s | Gemini Flash, Caching |
| Voice TTFB | < 500ms | < 800ms | TTS Server Direct |
| DB Query | < 50ms | < 100ms | Indexes, Connection Pool |

#### Scalability Design

```
┌─────────────────────────────────────────────────────────────────────┐
│                     SCALABILITY ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Concurrent Users Target: 10,000+                                   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  TIER 1: EDGE (Vercel)                                       │   │
│  │  ├── Auto-scaling (serverless)                               │   │
│  │  ├── Global CDN (static assets)                              │   │
│  │  ├── Edge Runtime (API routes)                               │   │
│  │  └── Regional deployment (Seoul primary)                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  TIER 2: DATABASE (Supabase)                                 │   │
│  │  ├── Connection pooling (PgBouncer)                          │   │
│  │  ├── Read replicas (if needed)                               │   │
│  │  ├── Realtime scaling (horizontal)                           │   │
│  │  └── Plan: Pro ($25/mo → Team for scale)                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  TIER 3: EXTERNAL APIS                                       │   │
│  │  ├── Gemini: 1500 QPM (rate limiting)                        │   │
│  │  ├── Tavily: 1000/day (caching)                              │   │
│  │  ├── TTS Server: 단일 서버 (bottleneck 주의)                 │   │
│  │  └── FCM: 무제한                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### Caching Strategy

```typescript
// 1. Vercel Edge Config (빠른 config 조회)
const celebrities = await get('celebrities'); // < 1ms

// 2. React Query Cache (클라이언트)
const { data } = useQuery({
  queryKey: ['celebrity', id],
  staleTime: 5 * 60 * 1000,  // 5분
  cacheTime: 30 * 60 * 1000, // 30분
});

// 3. Supabase Realtime Cache
// 자동으로 최신 데이터 구독, 별도 캐시 불필요

// 4. Generated Image Cache (Supabase Storage)
// 유사 상황 이미지 재사용
const cacheKey = `${celebrityId}:${activity}:${timeOfDay}`;
const cachedImage = await storage.from('generated').download(cacheKey);

// 5. RAG Context Cache (pgvector)
// 자주 조회되는 컨텍스트 미리 준비
CREATE MATERIALIZED VIEW frequent_contexts AS
SELECT * FROM memory_vectors
WHERE created_at > NOW() - INTERVAL '7 days';
```

#### Rate Limiting

```typescript
// Vercel Edge Middleware
import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';

const ratelimit = new Ratelimit({
  redis: Redis.fromEnv(),
  limiter: Ratelimit.slidingWindow(100, '1 m'), // 100 req/min per user
});

export async function middleware(request: NextRequest) {
  const ip = request.ip ?? '127.0.0.1';
  const { success, limit, reset, remaining } = await ratelimit.limit(ip);

  if (!success) {
    return NextResponse.json(
      { error: 'Too many requests' },
      { status: 429, headers: { 'X-RateLimit-Remaining': remaining.toString() } }
    );
  }

  return NextResponse.next();
}
```

#### Performance Monitoring

```typescript
// Vercel Analytics + Web Vitals
import { Analytics } from '@vercel/analytics/react';
import { SpeedInsights } from '@vercel/speed-insights/next';

// Custom metrics
export function reportWebVitals(metric: NextWebVitalsMetric) {
  // LCP, FID, CLS, TTFB, FCP
  if (metric.label === 'web-vital') {
    console.log(metric.name, metric.value);
    // Send to analytics
  }
}

// Supabase query performance
const { data, error, count } = await supabase
  .from('messages')
  .select('*', { count: 'exact' })
  .eq('conversation_id', convId)
  .order('created_at', { ascending: false })
  .limit(50);

// Log slow queries (> 100ms)
if (queryTime > 100) {
  console.warn(`Slow query: ${queryTime}ms`, { table: 'messages', convId });
}
```

---

## 12. Sequence Diagrams

### Core Sequence Diagrams

#### Sequence 1: Text Chat with Image Generation ("지금 뭐해?")

```
┌──────┐   ┌────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│Client│   │Vercel  │   │Supabase │   │ Gemini  │   │ Tavily  │   │ Storage │
│      │   │Edge    │   │         │   │   API   │   │         │   │         │
└──┬───┘   └───┬────┘   └────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘
   │           │             │             │             │             │
   │ POST /api/chat/send     │             │             │             │
   │ { message: "뭐해?" }    │             │             │             │
   │──────────▶│             │             │             │             │
   │           │             │             │             │             │
   │           │ Verify JWT  │             │             │             │
   │           │────────────▶│             │             │             │
   │           │◀────────────│             │             │             │
   │           │             │             │             │             │
   │           │ Intent Detection         │             │             │
   │           │ (regex: "뭐해")          │             │             │
   │           │ → IMAGE_REQUEST          │             │             │
   │           │             │             │             │             │
   │           │ Get Context              │             │             │
   │           │────────────▶│             │             │             │
   │           │ (schedule, memory)       │             │             │
   │           │◀────────────│             │             │             │
   │           │             │             │             │             │
   │           │ Search recent news       │             │             │
   │           │─────────────────────────────────────▶│             │
   │           │◀─────────────────────────────────────│             │
   │           │             │             │             │             │
   │           │ Generate Image           │             │             │
   │           │ (gemini-3.1-flash-image) │             │             │
   │           │──────────────────────────▶│             │             │
   │           │◀──────────────────────────│             │             │
   │           │             │             │             │             │
   │           │ Upload to Storage                                    │
   │           │─────────────────────────────────────────────────────▶│
   │           │◀─────────────────────────────────────────────────────│
   │           │             │             │             │             │
   │           │ Generate Text Response   │             │             │
   │           │ (gemini-3.0-flash)       │             │             │
   │           │──────────────────────────▶│             │             │
   │           │◀──────────────────────────│             │             │
   │           │             │             │             │             │
   │           │ Save Messages            │             │             │
   │           │────────────▶│             │             │             │
   │           │             │             │             │             │
   │           │             │ Realtime Broadcast        │             │
   │           │             │──────────────────────────────────▶ Client
   │           │             │             │             │             │
   │ Response  │             │             │             │             │
   │ { image_url, text }     │             │             │             │
   │◀──────────│             │             │             │             │
   │           │             │             │             │             │

Timeline: ~2-3 seconds total
```

#### Sequence 2: Voice Call Flow

```
┌──────┐   ┌────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│Client│   │Vercel  │   │ TTS     │   │ Gemini  │   │Supabase │
│      │   │Proxy   │   │ Server  │   │ (Chat)  │   │         │
└──┬───┘   └───┬────┘   └────┬────┘   └────┬────┘   └────┬────┘
   │           │             │             │             │
   │ WS Connect               │             │             │
   │ /api/voice/connect       │             │             │
   │──────────▶│             │             │             │
   │           │             │             │             │
   │           │ WS Connect  │             │             │
   │           │ /ws/voice/call            │             │
   │           │────────────▶│             │             │
   │           │◀────────────│             │             │
   │◀──────────│             │             │             │
   │           │             │             │             │
   │ Audio Stream (user speaking)          │             │
   │──────────▶│────────────▶│             │             │
   │           │             │             │             │
   │           │             │ STT (Whisper)│             │
   │           │             │ "안녕 뭐해?" │             │
   │           │             │             │             │
   │           │             │ Get Context │             │
   │           │             │────────────────────────▶│
   │           │             │◀────────────────────────│
   │           │             │             │             │
   │           │             │ Generate Response        │
   │           │             │────────────▶│             │
   │           │             │◀────────────│             │
   │           │             │             │             │
   │           │             │ TTS (GD Voice)           │
   │           │             │ Audio Stream │             │
   │◀──────────│◀────────────│             │             │
   │           │             │             │             │
   │           │             │ Save to Memory            │
   │           │             │────────────────────────▶│
   │           │             │             │             │
   │ ... (continues until call ends)       │             │
   │           │             │             │             │
   │ Call End  │             │             │             │
   │──────────▶│────────────▶│             │             │
   │           │             │             │             │
   │           │             │ Save Call Summary        │
   │           │             │────────────────────────▶│
   │           │             │             │             │

Latency per turn: < 500ms TTFB
```

#### Sequence 3: Proactive Contact (Cron Job)

```
┌─────────┐   ┌────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│ Vercel  │   │ Edge   │   │Supabase │   │ Gemini  │   │Firebase │
│  Cron   │   │Function│   │         │   │         │   │  FCM    │
└────┬────┘   └───┬────┘   └────┬────┘   └────┬────┘   └────┬────┘
     │            │             │             │             │
     │ Trigger (9 AM daily)     │             │             │
     │───────────▶│             │             │             │
     │            │             │             │             │
     │            │ Get eligible users        │             │
     │            │ (active, has FCM token)   │             │
     │            │────────────▶│             │             │
     │            │◀────────────│             │             │
     │            │             │             │             │
     │            │ For each user:            │             │
     │            │ ┌─────────────────────────────────────┐│
     │            │ │ Get conversation context            ││
     │            │ │────────────▶│             │         ││
     │            │ │◀────────────│             │         ││
     │            │ │             │             │         ││
     │            │ │ Generate proactive message          ││
     │            │ │ "좋은 아침! 잘 잤어?"    │         ││
     │            │ │──────────────────────────▶│         ││
     │            │ │◀──────────────────────────│         ││
     │            │ │             │             │         ││
     │            │ │ Save message│             │         ││
     │            │ │────────────▶│             │         ││
     │            │ │             │             │         ││
     │            │ │ Send push notification    │         ││
     │            │ │──────────────────────────────────▶││
     │            │ │             │             │         ││
     │            │ └─────────────────────────────────────┘│
     │            │             │             │             │
     │◀───────────│             │             │             │
     │ Complete   │             │             │             │

Runs: 2x daily (9 AM, 9 PM)
Users processed: batch of 100
```

---

## Appendix

### A. ADR Index

| ADR | Title | Status |
|-----|-------|--------|
| ADR-001 | Monorepo Structure | Accepted → **Updated** |
| ADR-002 | Persona Engine | Accepted |
| ADR-003 | Gemini LLM Selection | Accepted |
| ADR-004 | Live Photo Feature | Accepted |
| ADR-005 | **Supabase + Vercel Stack** | **New** |

### B. Technology Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Hosting | Vercel | Next.js 최적화, Edge Runtime, 글로벌 CDN |
| Database | Supabase PostgreSQL | 관리형, RLS, Realtime, pgvector |
| Auth | Supabase Auth | DB 통합, OAuth, RLS 연동 |
| Realtime | Supabase Realtime | 관리형, Postgres Changes, Broadcast |
| Storage | Supabase Storage | CDN, RLS, 관리형 |
| LLM | Gemini 3.0 Flash | 빠른 응답, 비용 효율 |
| Image | Gemini 3.1 Flash Image | 실시간 이미지 생성 |
| Voice | 기존 TTS Server | 이미 구축된 인프라 |

### C. Cost Estimation (Monthly)

| Service | Tier | Cost | Notes |
|---------|------|------|-------|
| Vercel | Pro | $20/user | Edge 함수, Analytics |
| Supabase | Pro | $25 | 8GB DB, 250GB 전송 |
| Gemini API | Pay-as-you-go | ~$50-100 | 예상 사용량 기준 |
| Tavily | Free/Pro | $0-49 | 사용량에 따라 |
| Firebase | Spark (Free) | $0 | Push 알림 무료 |
| **Total** | | **~$100-200** | MVP 기준 |

### D. Migration Checklist (from PLAN.md)

- [x] PostgreSQL → Supabase PostgreSQL
- [x] NextAuth.js → Supabase Auth
- [x] Redis → Supabase + Vercel KV (optional)
- [x] Socket.io → Supabase Realtime
- [x] Docker + nginx → Vercel Serverless
- [x] 로컬 Storage → Supabase Storage
- [x] Claude → Gemini 3.0 Flash

### E. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-28 | DAVINCI | Initial system architecture |
| | | | - Next.js + Supabase + Vercel 스택 |
| | | | - C4 Level 2-3 다이어그램 |
| | | | - Database Schema (RLS 포함) |
| | | | - API 스펙 |
| | | | - Security Architecture |
| | | | - Deployment Pipeline |
| | | | - Sequence Diagrams |
