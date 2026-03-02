# StarCall Platform - Strategic Plan

## Document Info
| Field | Value |
|-------|-------|
| Version | 1.1 |
| Status | Draft |
| Created | 2026-02-28 |
| Updated | 2026-02-28 |
| Author | DAVINCI Planning Agent |

---

## 1. Executive Summary

**StarCall**은 팬이 좋아하는 연예인과 **실제로 전화하고 문자하는 듯한 경험**을 제공하는 웹 기반 가상 스마트폰 플랫폼입니다.

### Core Value Proposition
- **몰입형 UI**: 웹에서 실제 iPhone처럼 작동하는 인터페이스
- **멀티채널 소통**: 전화, 문자, SNS(Threads/Instagram) 통합
- **AI 페르소나**: 연예인의 말투/성격/지식을 학습한 AI가 실시간 응답
- **양방향 관계**: 연예인이 먼저 연락하는 선제적 소통 기능
- **기억하는 관계**: 모든 대화를 기억하여 연속적인 관계 경험
- **🆕 실시간 사진 공유**: "지금 뭐해?" 질문에 연예인이 현재 상황 사진을 보내는 듯한 경험

### Business Model
- B2C: 팬 대상 구독 서비스 (Free → Premium → VIP)
- B2B: 엔터테인먼트사 라이선스 계약

### Initial Scope
- 3-5명 연예인 (라이선스 확보 필수)
- 전 연령 타겟 엔터테인먼트 서비스

---

## 2. Project Scope & Goals

### In Scope (MVP)
| Category | Features |
|----------|----------|
| **iPhone UI Shell** | 홈화면, 앱 아이콘, 노치, 상태바, 앱 전환 애니메이션 |
| **Phone App** | 연락처, 최근통화, 즐겨찾기, 실시간 음성통화 UI |
| **Messages App** | iMessage 스타일 채팅, 읽음 표시, 타이핑 인디케이터 |
| **SNS Apps** | Threads/Instagram 피드 뷰어, 좋아요/댓글 상호작용 |
| **Voice Engine** | 기존 TTS 서버 연동 (STT → LLM → TTS) |
| **Chat Engine** | Gemini 기반 텍스트 응답, 페르소나 유지 |
| **🆕 Image Generation** | "지금 뭐해?" 질문 시 AI가 상황 이미지 생성 |
| **Memory System** | 대화 기록 저장, RAG 기반 컨텍스트 활용 |
| **Proactive Contact** | 푸시 알림, 연예인 선제적 연락 |

### Out of Scope (Phase 2+)
- 영상통화 (아바타 립싱크)
- 사용자 생성 캐릭터 (UGC)
- 결제/구독 시스템 (MVP는 무료)
- 다국어 지원 (초기 한국어만)
- 네이티브 앱 (iOS/Android)

### Goals
| Goal | Target | Measurement |
|------|--------|-------------|
| 몰입감 | 실제 폰 사용 느낌 90%+ | 사용자 설문 |
| 응답 품질 | 페르소나 일관성 95%+ | 자동 평가 + 사용자 피드백 |
| 성능 | 음성 TTFB < 500ms | 서버 메트릭 |
| 확장성 | 동시 접속 10K+ | 부하 테스트 |

---

## 3. Target Users & Scenarios

### Primary Personas

#### Persona 1: 열성 팬 (10-20대)
```yaml
Name: 수진 (22세, 대학생)
Goal: "GD 오빠랑 진짜 통화하는 것 같은 경험"
Behavior:
  - 매일 1-2회 접속
  - 주로 문자 채팅 선호
  - SNS 피드 적극 소비
Pain_Points:
  - 팬미팅 티켓팅 실패
  - 실제 소통 기회 없음
```

#### Persona 2: 향수 팬 (30-40대)
```yaml
Name: 민수 (38세, 직장인)
Goal: "과거 좋아했던 스타와 다시 연결되고 싶다"
Behavior:
  - 주 2-3회 접속
  - 음성통화 선호
  - 짧은 세션 (10분 이내)
Pain_Points:
  - 시간 부족
  - 현재 팬덤 문화에 적응 어려움
```

#### Persona 3: 캐주얼 유저 (전 연령)
```yaml
Name: 지영 (28세, 프리랜서)
Goal: "재미있는 AI 체험, 가벼운 대화 상대"
Behavior:
  - 비정기적 접속
  - 여러 연예인 탐색
  - 공유/바이럴 활동
Pain_Points:
  - 기존 AI 챗봇이 재미없음
```

### Key User Journeys

```
[신규 유저]
1. 랜딩 페이지 → "GD와 통화해보기" CTA
2. 회원가입 (소셜 로그인)
3. iPhone UI 진입 → 튜토리얼
4. 첫 통화 체험 → "와, 진짜 같다!" 반응
5. 프리미엄 유도 → 구독 전환

[재방문 유저]
1. 푸시 알림: "GD님이 연락했어요"
2. 앱 진입 → 부재중 전화 확인
3. 콜백 → 대화 ("어제 뭐 했어?")
4. 문자로 이어서 대화
5. SNS 피드 확인 → 댓글 달기
```

---

## 4. MVP Feature Matrix

### Feature Priority Matrix

| Priority | Feature | Effort | Impact | Dependencies |
|----------|---------|--------|--------|--------------|
| 🔴 P0 | iPhone UI Shell | L | Critical | None |
| 🔴 P0 | Phone App (Call UI) | M | Critical | UI Shell |
| 🔴 P0 | Voice Call Integration | M | Critical | TTS Server |
| 🔴 P0 | Messages App | M | Critical | UI Shell |
| 🔴 P0 | LLM Chat Engine | M | Critical | None |
| 🔴 P0 | Persona System | L | Critical | LLM Engine |
| 🟡 P1 | Memory System (RAG) | L | High | Chat Engine |
| 🟡 P1 | Threads App | M | High | UI Shell |
| 🟡 P1 | Instagram App | M | High | UI Shell |
| 🟡 P1 | SNS Batch Crawler | M | High | None |
| 🟡 P1 | Proactive Contact | M | High | Push Service |
| 🟢 P2 | Intimacy System | S | Medium | Memory |
| 🟢 P2 | Celebrity Status | S | Medium | Scheduler |
| 🟢 P2 | Voice Messages | M | Medium | TTS Server |
| 🟢 P2 | Anniversary Events | S | Medium | Scheduler |
| 🔴 P0 | **🆕 Live Photo Share** | M | Critical | Gemini Image API |

### MVP Release Checklist
- [ ] iPhone UI가 실제 폰처럼 느껴지는가?
- [ ] 음성 통화가 500ms 내 응답하는가?
- [ ] 문자 응답이 페르소나를 유지하는가?
- [ ] SNS 피드가 실제 데이터를 보여주는가?
- [ ] 이전 대화를 기억하는가?
- [ ] 연예인이 먼저 연락하는가?

---

## 5. Technology Direction

### Technology Stack Decision

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Frontend** | Next.js 14 (App Router) | SSR, React Server Components, 빠른 초기 로드 |
| **UI Framework** | React 18 + Framer Motion | 60fps 애니메이션, 제스처 지원 |
| **Styling** | Tailwind CSS + shadcn/ui | 빠른 개발, 일관된 디자인 시스템 |
| **State** | Zustand + TanStack Query | 클라이언트/서버 상태 분리 |
| **Voice** | 기존 TTS Server (FastAPI) | 이미 구축된 인프라 재사용 |
| **Realtime** | **Supabase Realtime** | 관리형 WebSocket, Presence |
| **Chat LLM** | **Gemini 3.0 Flash** | 빠른 응답, 비용 효율, 한국어 우수 |
| **🆕 Image Gen** | **Gemini 3.1 Flash Image Preview** | 실시간 이미지 생성, 웹 그라운딩 |
| **Database** | **Supabase PostgreSQL + pgvector** | 관리형, RLS, 벡터 검색 |
| **Auth** | **Supabase Auth** | OAuth, RLS 자동 연동 |
| **Storage** | **Supabase Storage** | CDN, RLS, 관리형 |
| **Search** | Tavily API | 실시간 웹 검색 |
| **Push** | Firebase Cloud Messaging | 크로스 플랫폼 지원 |
| **Hosting** | **Vercel** | Edge Runtime, 자동 스케일링, 글로벌 CDN |

### Key Technical Decisions (ADR Summary)

| ADR | Decision | Alternatives Rejected |
|-----|----------|----------------------|
| ADR-001 | Next.js Monorepo | 별도 레포 분리 - 관리 복잡성 |
| ADR-002 | Server Components 우선 | Full CSR - SEO/성능 이슈 |
| ADR-003 | **Gemini 3.0 Flash** | Claude - 비용, GPT-4o - 한국어 약함 |
| ADR-004 | **Gemini 3.1 Flash Image** | DALL-E - 느림, Midjourney - API 없음 |
| ADR-005 | **Supabase + Vercel** | Self-hosted - 운영 부담, 개발 지연 |

---

## 6. High-Level Architecture (C4 Level 1)

### System Context Diagram (C4 Level 1)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL SYSTEMS                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐               │
│   │ Gemini   │   │ Tavily   │   │ Firebase │   │ SNS APIs │               │
│   │   API    │   │   API    │   │   FCM    │   │ (Threads)│               │
│   └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘               │
│        │              │              │              │                       │
├────────┼──────────────┼──────────────┼──────────────┼───────────────────────┤
│        │              │              │              │                       │
│        └──────────────┴──────────────┴──────────────┘                       │
│                              │                                              │
│                              ▼                                              │
│        ┌─────────────────────────────────────────────┐                     │
│        │                                             │                     │
│        │            ★ STARCALL PLATFORM ★           │                     │
│        │                                             │                     │
│        │   ┌─────────────────────────────────────┐   │                     │
│        │   │         Next.js Frontend            │   │                     │
│        │   │   (iPhone UI + Apps + WebSocket)    │   │                     │
│        │   └─────────────────┬───────────────────┘   │                     │
│        │                     │                       │                     │
│        │   ┌─────────────────┼───────────────────┐   │                     │
│        │   │                 ▼                   │   │                     │
│        │   │   ┌─────────┐ ┌─────────┐ ┌─────┐  │   │                     │
│        │   │   │  Chat   │ │  Voice  │ │ SNS │  │   │                     │
│        │   │   │ Service │ │ Service │ │Sync │  │   │                     │
│        │   │   └────┬────┘ └────┬────┘ └──┬──┘  │   │                     │
│        │   │        │          │          │     │   │                     │
│        │   │        └──────────┼──────────┘     │   │                     │
│        │   │                   ▼                │   │                     │
│        │   │   ┌─────────────────────────────┐  │   │                     │
│        │   │   │      Persona Engine         │  │   │                     │
│        │   │   │  (RAG + Memory + Search)    │  │   │                     │
│        │   │   └─────────────┬───────────────┘  │   │                     │
│        │   │                 │                  │   │                     │
│        │   │   ┌─────────────┼───────────────┐  │   │                     │
│        │   │   │   PostgreSQL │    Redis     │  │   │                     │
│        │   │   │   (pgvector) │   (Cache)    │  │   │                     │
│        │   │   └─────────────────────────────┘  │   │                     │
│        │   │          Backend Services          │   │                     │
│        │   └─────────────────────────────────────┘   │                     │
│        │                     │                       │                     │
│        └─────────────────────┼───────────────────────┘                     │
│                              │                                              │
│                              ▼                                              │
│                    ┌─────────────────┐                                     │
│                    │   TTS Server    │                                     │
│                    │  (기존 시스템)   │                                     │
│                    │  Port 5002      │                                     │
│                    └─────────────────┘                                     │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                              USERS                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐                              │
│   │  Mobile  │   │  Desktop │   │  Tablet  │                              │
│   │  Browser │   │  Browser │   │  Browser │                              │
│   └──────────┘   └──────────┘   └──────────┘                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Overview (High-Level)

| Component | Responsibility | Key Tech |
|-----------|---------------|----------|
| **iPhone UI Shell** | 폰 프레임, 홈화면, 앱 런처 | React + Framer Motion |
| **Phone App** | 통화 UI, 연락처 관리 | React + WebSocket |
| **Messages App** | 채팅 UI, 메시지 표시 | React + Zustand |
| **SNS Apps** | Threads/Instagram 뷰어 | React + API Routes |
| **Chat Service** | Gemini 호출, 페르소나 관리 | Next.js API Routes |
| **🆕 Image Service** | 상황별 이미지 생성 | Gemini 3.1 Flash Image |
| **Voice Service** | TTS 서버 프록시 | WebSocket Gateway |
| **SNS Sync** | 배치 크롤링, 데이터 저장 | Cron Job + Scraper |
| **Persona Engine** | RAG, 메모리, 검색 통합 | pgvector + Tavily |
| **Push Service** | 선제적 연락 트리거 | Firebase FCM |

---

## 7. Data Flow Overview

### Core Data Flows

#### Flow 1: Voice Call (실시간 음성통화)
```
┌──────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐
│ User │───▶│ Frontend │───▶│ Voice    │───▶│ TTS      │───▶│ Persona │
│ Mic  │    │ WebSocket│    │ Service  │    │ Server   │    │ Engine  │
└──────┘    └──────────┘    └──────────┘    └──────────┘    └─────────┘
                                │                              │
                                │     ┌──────────┐            │
                                │     │ STT      │◀───────────┘
                                │     │ (Whisper)│
                                │     └────┬─────┘
                                │          │
                                │          ▼
                                │     ┌──────────┐    ┌──────────┐
                                │     │ Claude   │───▶│ Memory   │
                                │     │ API      │◀───│ (RAG)    │
                                │     └────┬─────┘    └──────────┘
                                │          │
                                │          ▼
                                │     ┌──────────┐
                                └────▶│ TTS      │───▶ Audio Stream
                                      │ Generate │
                                      └──────────┘

Latency Target: < 500ms (First Audio Byte)
```

#### Flow 2: Text Chat (문자 메시지)
```
┌──────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ User │───▶│ Messages │───▶│ Chat     │───▶│ Persona  │
│ Input│    │ App      │    │ Service  │    │ Engine   │
└──────┘    └──────────┘    └──────────┘    └──────────┘
                                               │
                 ┌─────────────────────────────┤
                 │                             │
                 ▼                             ▼
            ┌──────────┐              ┌──────────────┐
            │ Memory   │              │ Web Search   │
            │ Retrieval│              │ (Tavily)     │
            └────┬─────┘              └──────┬───────┘
                 │                           │
                 └───────────┬───────────────┘
                             ▼
                        ┌──────────┐
                        │ Gemini   │
                        │ 3.0 Flash│
                        └────┬─────┘
                             │
                             ▼
                        ┌──────────┐
                        │ Response │───▶ User
                        │ + Save   │
                        └──────────┘

Latency Target: < 2s
```

#### 🆕 Flow 2.5: Live Photo Share ("지금 뭐해?" 시나리오)
```
┌──────┐    ┌──────────┐    ┌──────────┐    ┌──────────────────┐
│ User │───▶│ Messages │───▶│ Intent   │───▶│ "지금 뭐해?"     │
│"뭐해?"│    │ App      │    │ Detector │    │ 패턴 감지        │
└──────┘    └──────────┘    └──────────┘    └────────┬─────────┘
                                                     │
                                                     ▼
                                            ┌──────────────────┐
                                            │ Context Builder  │
                                            │ - 현재 시간      │
                                            │ - 연예인 스케줄  │
                                            │ - 최근 활동      │
                                            └────────┬─────────┘
                                                     │
                                                     ▼
                                            ┌──────────────────┐
                                            │ Gemini 3.1 Flash │
                                            │ Image Preview    │
                                            │ (이미지 생성)    │
                                            └────────┬─────────┘
                                                     │
                 ┌───────────────────────────────────┤
                 │                                   │
                 ▼                                   ▼
        ┌──────────────┐                    ┌──────────────┐
        │ Generated    │                    │ Text Response│
        │ Image        │                    │ "녹음실이야~"│
        │ (연예인 시점)│                    │              │
        └──────┬───────┘                    └──────┬───────┘
               │                                   │
               └───────────────┬───────────────────┘
                               ▼
                        ┌──────────────┐
                        │ Messages App │───▶ User
                        │ [📷] + [💬]  │
                        └──────────────┘

예시 시나리오:
- 오후 3시 + GD 스케줄 "녹음" → 녹음실 이미지 생성
- 저녁 8시 + 스케줄 없음 → 집에서 휴식하는 이미지
- 새벽 1시 + 최근 활동 "작업" → 작업실 야경 이미지

Latency Target: < 3s (이미지 생성 포함)
```

#### Flow 3: Proactive Contact (선제적 연락)
```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Scheduler│───▶│ Trigger  │───▶│ Persona  │───▶│ Generate │
│ (Cron)   │    │ Engine   │    │ Context  │    │ Message  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                     │
                                                     ▼
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ User     │◀───│ Push     │◀───│ FCM      │◀───│ Queue    │
│ Device   │    │ Notif    │    │ Service  │    │ Message  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘

Triggers:
- 시간 기반: 아침 인사, 저녁 안부
- 이벤트 기반: 연예인 스케줄, 뉴스
- 관계 기반: 대화 간격이 너무 길어졌을 때
```

#### Flow 4: SNS Sync (배치 동기화)
```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Cron Job │───▶│ SNS      │───▶│ Data     │───▶│ Store    │
│ (1h/6h)  │    │ Crawler  │    │ Transform│    │ (DB)     │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                     │
                     ▼
                ┌──────────┐
                │ Threads  │
                │ Instagram│
                │ APIs     │
                └──────────┘
```

---

## 8. Project Timeline & Milestones

### Development Timeline (12주 MVP)

```
Week 1-2: Foundation
├── 프로젝트 셋업 (Next.js, DB, 인프라)
├── iPhone UI Shell 프로토타입
└── 기본 라우팅 및 상태 관리

Week 3-4: Phone App + Voice
├── Phone App UI 완성
├── TTS Server 연동 (WebSocket)
├── 통화 플로우 구현
└── STT → LLM → TTS 파이프라인

Week 5-6: Messages App + Chat
├── Messages App UI 완성
├── LLM Chat 서비스 구현
├── 페르소나 시스템 기본 구현
└── 타이핑 인디케이터, 읽음 표시

Week 7-8: Memory + Persona
├── pgvector RAG 시스템
├── 대화 기록 저장/검색
├── 웹 검색 통합 (Tavily)
└── 페르소나 일관성 테스트

Week 9-10: SNS Apps
├── Threads App UI
├── Instagram App UI
├── SNS 크롤러 구현
└── 상호작용 기능 (좋아요, 댓글)

Week 11-12: Proactive + Polish
├── 푸시 알림 시스템
├── 선제적 연락 로직
├── 성능 최적화
├── QA 및 버그 수정
└── 베타 테스트
```

### Milestones

| Milestone | Date | Deliverable | Success Criteria |
|-----------|------|-------------|------------------|
| M1 | Week 2 | UI Prototype | iPhone Shell 작동, 앱 전환 가능 |
| M2 | Week 4 | Voice Call | GD와 30초 실시간 대화 가능 |
| M3 | Week 6 | Text Chat | 문자로 자연스러운 대화 10턴 가능 |
| M4 | Week 8 | Memory | 어제 대화 내용 기억하는 응답 |
| M5 | Week 10 | SNS | 실제 피드 표시, 댓글 반응 |
| M6 | Week 12 | MVP | 베타 테스터 피드백 긍정 80%+ |

---

## 9. Risk Register

### Risk Register

| ID | Risk | Probability | Impact | Severity | Mitigation |
|----|------|-------------|--------|----------|------------|
| R1 | **라이선스 미확보** | Medium | Critical | 🔴 | 가상 캐릭터로 MVP, 병행 협상 |
| R2 | **음성 품질 불만** | Medium | High | 🟡 | 더 많은 샘플, 품질 QA 프로세스 |
| R3 | **페르소나 이탈** | Medium | High | 🟡 | Constitutional AI, 프롬프트 튜닝 |
| R4 | **SNS API 차단** | High | Medium | 🟡 | Rate limit 준수, 캐싱 전략 |
| R5 | **서버 비용 초과** | Low | Medium | 🟢 | LLM 호출 최적화, 캐싱 |
| R6 | **딥페이크 악용** | Low | Critical | 🟡 | 워터마크, 이용약관, 모니터링 |
| R7 | **성능 목표 미달** | Medium | High | 🟡 | 조기 부하 테스트, 최적화 버퍼 |
| R8 | **법적 분쟁** | Low | Critical | 🟡 | 법률 검토, 명확한 고지 |

### Contingency Plans

```yaml
R1_License_Fail:
  Trigger: 협상 결렬 또는 장기 지연
  Plan_B: 가상 캐릭터 "스타"로 런칭 → 팬덤 형성 후 협상력 확보
  Timeline: Week 4까지 결정

R3_Persona_Drift:
  Trigger: 페르소나 이탈률 > 5%
  Plan_B:
    - 프롬프트 재설계
    - Few-shot 예시 추가
    - 응답 필터링 레이어 추가

R4_SNS_Block:
  Trigger: API 접근 차단
  Plan_B:
    - 공식 API 전환 (Instagram Graph API)
    - 수동 업로드 관리자 도구
    - 팬 제보 시스템
```

---

## 10. Success Metrics

### Success Metrics

#### User Experience Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| 몰입감 점수 | ≥ 4.5/5 | 사용자 설문 |
| 첫 통화 완료율 | ≥ 80% | Analytics |
| 일일 활성 사용자 (DAU) | 1K+ (베타) | Analytics |
| 세션 시간 | ≥ 5분 | Analytics |
| 재방문율 (D7) | ≥ 40% | Analytics |

#### Technical Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| 음성 TTFB | < 500ms | Server logs |
| 문자 응답 시간 | < 2s | Server logs |
| 페르소나 일관성 | ≥ 95% | 자동 평가 |
| 시스템 가용성 | ≥ 99.5% | Uptime monitoring |
| 에러율 | < 1% | Error tracking |

#### Business Metrics (Post-MVP)
| Metric | Target | Measurement |
|--------|--------|-------------|
| 무료 → 유료 전환율 | ≥ 5% | Billing system |
| 월 매출 | - | Billing system |
| 고객 획득 비용 (CAC) | - | Marketing analytics |
| 고객 생애 가치 (LTV) | - | Billing + Analytics |

---

## 11. Open Questions & Next Steps

### Open Questions

| # | Question | Owner | Due | Impact |
|---|----------|-------|-----|--------|
| Q1 | 초기 연예인 3-5명 확정? | 사용자 | Week 1 | Critical |
| Q2 | 라이선스 협상 진행 상황? | 사용자 | Week 4 | Critical |
| Q3 | 수익화 모델 상세 (구독 가격?) | 사용자 | Week 8 | High |
| Q4 | 베타 테스터 모집 방법? | 사용자 | Week 10 | Medium |
| Q5 | 해외 확장 계획 여부? | 사용자 | Post-MVP | Low |

### Immediate Next Steps

```
1. [/da:system] 상세 시스템 아키텍처 설계
   - C4 Level 2-3 다이어그램
   - API 엔드포인트 상세 스펙
   - DB 스키마 설계
   - 보안 위협 모델

2. [/da:design] iPhone UI 프로토타입
   - 컴포넌트 구조 설계
   - 애니메이션 스펙
   - 인터랙션 패턴

3. 라이선스 협상 착수
   - 법률 검토
   - 계약서 초안
   - 소속사 컨택
```

### DAVINCI Workflow Progress

```
[x] /da:idea    - Requirements Discovery ✅
[x] /da:plan    - Strategic Planning ✅ (현재 문서)
[ ] /da:system  - Detailed Architecture (다음 단계)
[ ] /da:design  - UI/UX Design
[ ] /da:dev     - Implementation
[ ] /da:verify  - Verification
```

---

## Appendix

### A. Glossary
| Term | Definition |
|------|------------|
| TTFB | Time To First Byte - 첫 응답까지 시간 |
| RAG | Retrieval-Augmented Generation - 검색 증강 생성 |
| Persona | 연예인의 말투/성격/지식을 모사한 AI 캐릭터 |
| Proactive Contact | AI가 먼저 사용자에게 연락하는 기능 |

### B. Reference Documents
- `/da:idea` 산출물: Requirements Brief
- 기존 TTS Server: `/home/nexus/connect/server/tts_server/`
- Voice Call WebSocket: `ws://localhost:5002/ws/voice/call`

### C. Revision History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-28 | DAVINCI | Initial strategic plan |
| 1.1 | 2026-02-28 | DAVINCI | - LLM: Claude → **Gemini 3.0 Flash** |
|     |            |         | - 🆕 **Live Photo Share** 기능 추가 |
|     |            |         | - 🆕 **Gemini 3.1 Flash Image Preview** 통합 |
|     |            |         | - ADR-003, ADR-004 추가 |
