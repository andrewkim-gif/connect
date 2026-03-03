# GD Voice Call App - 전면 재설계 기획

## 📋 Executive Summary

현재 `tts_test_app`을 분석한 결과, 다음과 같은 핵심 문제점들이 발견됨:

### 현재 문제점
1. **전화 발신음 없음** - ringback_korea.wav 파일은 있으나 제대로 재생 안됨
2. **음파(Waveform) 시각화 안됨** - audioLevel 업데이트 문제
3. **모델 선택 UI 미흡** - voiceId 변경이 제대로 반영 안됨
4. **전화 연결 UX 부족** - 아이폰 전화앱 수준의 피드백 없음
5. **상태 전환 불안정** - greeting → listening → speaking 전환 시 버그
6. **오디오 재생 끊김** - 스트리밍 오디오 버퍼링 문제

---

## 🎯 프로젝트 목표

### Primary Goals
1. 아이폰 전화앱 수준의 매끄러운 UX
2. 안정적인 실시간 음성 통화
3. 시각적 피드백 (음파, 상태 인디케이터)
4. 직관적인 설정 UI

### Success Metrics
- 전화 발신 → 연결 → 통화 → 종료 전체 플로우 100% 동작
- 음파 시각화 listening/speaking 모두 동작
- 발신음 재생 확인
- 모델 선택 즉시 반영

---

## 🏗️ 시스템 아키텍처

### 기술 스택
```yaml
Frontend:
  Framework: Next.js 15 (App Router)
  Language: TypeScript (strict)
  State: Zustand
  Styling: Tailwind CSS + shadcn/ui
  Audio: Web Audio API

Backend: (기존 유지)
  Server: FastAPI (Python)
  WebSocket: /ws/voice/call
  TTS: Custom TTS Engine
  STT: Whisper
  LLM: Claude/GPT
```

### 핵심 컴포넌트 구조
```
app/
├── page.tsx                    # 메인 페이지 (연락처/통화 화면)
├── layout.tsx                  # 루트 레이아웃
├── globals.css                 # 전역 스타일
components/
├── phone/
│   ├── PhoneApp.tsx            # 메인 전화 앱 컨테이너
│   ├── ContactScreen.tsx       # 연락처 화면
│   ├── CallingScreen.tsx       # 발신 중 화면 (링톤)
│   ├── CallScreen.tsx          # 통화 중 화면
│   ├── ProfileAvatar.tsx       # 프로필 아바타 (애니메이션)
│   ├── CallTimer.tsx           # 통화 시간 표시
│   ├── Waveform.tsx            # 음파 시각화 (Canvas)
│   ├── ControlGrid.tsx         # 아이폰 스타일 3x3 컨트롤
│   └── SettingsSheet.tsx       # 설정 바텀 시트
├── ui/                         # shadcn/ui 컴포넌트
hooks/
├── useVoiceCall.ts             # WebSocket + 상태 관리 통합
├── useAudioPlayer.ts           # 오디오 재생 (스트리밍)
├── useAudioRecorder.ts         # 마이크 녹음 + VAD
├── useRingTone.ts              # 발신음 재생
└── useWaveform.ts              # 음파 애니메이션
stores/
└── callStore.ts                # Zustand 전역 상태
types/
├── call.ts                     # 통화 관련 타입
└── websocket.ts                # WebSocket 메시지 타입
lib/
├── audioUtils.ts               # 오디오 유틸리티
└── utils.ts                    # 일반 유틸리티
```

---

## 📱 화면 설계

### 1. ContactScreen (연락처 화면)
```
┌─────────────────────────┐
│ 연락처            ⚙️    │ <- 헤더 + 설정 버튼
├─────────────────────────┤
│                         │
│   ┌────┐                │
│   │ GD │  GD (지디)     │ <- 프로필 아바타
│   └────┘  AI 음성 어시스턴트│
│                    📞   │ <- 전화 버튼
│                         │
├─────────────────────────┤
│  탭하여 통화 시작       │ <- 안내 텍스트
└─────────────────────────┘
```

### 2. CallingScreen (발신 중)
```
┌─────────────────────────┐
│                         │
│       ┌──────┐          │
│       │  GD  │          │ <- 큰 아바타
│       └──────┘          │
│       GD (지디)         │
│     "발신 중..."        │ <- 상태 텍스트
│                         │
│   🔇    📱    🔊        │ <- 음소거/키패드/스피커
│                         │
│       (📞 종료)         │ <- 빨간 종료 버튼
└─────────────────────────┘
```

### 3. CallScreen (통화 중)
```
┌─────────────────────────┐
│                         │
│       ┌──────┐          │
│       │  GD  │          │ <- 프로필 (말할 때 펄스)
│       └──────┘          │
│       GD (지디)         │
│       00:45             │ <- 통화 시간
│     "듣는 중..."        │ <- 상태 인디케이터
│                         │
│  ████████████████████   │ <- 음파 시각화
│                         │
├─────────────────────────┤
│  🔇     💬     🔊       │
│ 음소거   대화   스피커  │
│                         │
│  📹     👤     ⚙️       │
│ 영상   연락처   설정    │
├─────────────────────────┤
│       (📞 종료)         │
└─────────────────────────┘
```

### 4. SettingsSheet (설정 바텀 시트)
```
┌─────────────────────────┐
│  ━━━━━━━━               │ <- 드래그 핸들
│                     ✕   │
│  통화 설정              │
├─────────────────────────┤
│  서버 주소              │
│  [crossconnect.ngrok.app]│
│                         │
│  음성 모델              │
│  ○ GD Default (빠름)    │
│  ● GD ICL (고품질)      │
│                         │
│  침묵 감지 임계값       │
│  [────●──────] 0.01     │
│                         │
└─────────────────────────┘
```

---

## 🔄 상태 흐름 (FSM)

```
[idle] ──전화걸기──> [connecting] ──WS연결──> [ringing]
                                              │
                         ┌──────────────<─────┘
                         │ (2-5초 발신음 재생)
                         ↓
                    [greeting] ──GD인사──> [speaking]
                         │                    │
                         │                    ↓
                         │              [listening]
                         │                    │
                         │     ┌──────────────┤
                         │     ↓              │
                    [speaking] <──AI응답──────┘
                         │
                         ↓
[idle] <──종료────── [ended]
```

### 상태별 동작
| 상태 | 발신음 | 녹음 | 재생 | 음파 | 타이머 |
|------|--------|------|------|------|--------|
| idle | ❌ | ❌ | ❌ | ❌ | ❌ |
| connecting | ❌ | ❌ | ❌ | ❌ | ❌ |
| ringing | ✅ | ❌ | ❌ | ❌ | ❌ |
| greeting | ❌ | ❌ | ✅ | ✅ | ✅ |
| listening | ❌ | ✅ | ❌ | ✅ | ✅ |
| speaking | ❌ | ❌ | ✅ | ✅ | ✅ |
| ended | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## 🎵 오디오 시스템 설계

### 1. 발신음 (RingTone)
```typescript
// useRingTone.ts
- HTML5 Audio로 /sounds/ringback_korea.wav 재생
- loop: true, volume: 0.5
- ringing 상태에서만 재생
- greeting 전환 시 즉시 중지
```

### 2. 음파 시각화 (Waveform)
```typescript
// useWaveform.ts
문제점 해결:
1. audioLevel을 useRef로 관리 (클로저 문제 해결)
2. Zustand subscribe로 실시간 업데이트
3. AnalyserNode로 speaking 시 오디오 레벨 측정
4. listening 시 마이크 레벨 측정

구현:
- Canvas 기반 바 차트 시각화
- 32개 바, 중앙에서 위아래로 확장
- 보라~파랑 그라데이션
- 부드러운 애니메이션 (0.15 lerp)
- 최소 움직임 보장 (baseLevel: 0.05)
```

### 3. 오디오 재생 (AudioPlayer)
```typescript
// useAudioPlayer.ts
- AudioContext (24kHz)
- AnalyserNode 연결 (음파 시각화용)
- 스케줄링 기반 무간극 재생 (nextPlayTime)
- Barge-in 시 즉시 중지
```

### 4. 녹음 (AudioRecorder)
```typescript
// useAudioRecorder.ts
- MediaRecorder (webm/opus)
- 리샘플링: 브라우저 샘플레이트 → 16kHz
- VAD (Voice Activity Detection)
- 자동 침묵 감지 후 전송
```

---

## 📡 WebSocket 프로토콜

### Client → Server
```typescript
// 음성 입력
{ type: 'voice_input', audio: '<base64 PCM 16kHz>', voice_id: 'gd-default' }

// 인사 요청
{ type: 'greeting', voice_id: 'gd-default' }

// 인터럽트 (Barge-in)
{ type: 'interrupt', reason: 'barge_in' }

// 대화 초기화
{ type: 'reset' }

// Ping
{ type: 'ping' }
```

### Server → Client
```typescript
// 연결 확인
{ type: 'connected', client_id: string, sample_rate_in: 16000, sample_rate_out: 24000 }

// STT 결과
{ type: 'transcription', text: string, language: string, confidence: number }

// 응답 시작
{ type: 'response_start' }

// 텍스트 스트리밍
{ type: 'response_text', text: string, is_final: boolean }

// 오디오 청크 (Binary)
[PCM 16-bit 24kHz mono]

// 응답 완료
{ type: 'response_end', metrics: { stt_ms, llm_ttfa_ms, tts_ttfa_ms, total_ms, ... } }

// 에러
{ type: 'error', code: string, message: string }

// Pong
{ type: 'pong' }
```

---

## 🛠️ 구현 계획

### Phase 1: 기반 구축 (2-3시간)
1. 프로젝트 초기화 (Next.js 15 + TypeScript)
2. 기본 컴포넌트 구조 설정
3. Zustand 스토어 재설계
4. 타입 정의

### Phase 2: UI 구현 (3-4시간)
1. ContactScreen 구현
2. CallingScreen 구현 (발신음 포함)
3. CallScreen 구현
4. SettingsSheet 구현
5. shadcn/ui 컴포넌트 통합

### Phase 3: 오디오 시스템 (3-4시간)
1. useRingTone 재구현
2. useWaveform 재구현 (버그 수정)
3. useAudioPlayer 재구현 (AnalyserNode 추가)
4. useAudioRecorder 재구현

### Phase 4: 통합 및 테스트 (2-3시간)
1. useVoiceCall 통합
2. 전체 플로우 테스트
3. 버그 수정 및 최적화
4. 성능 튜닝

---

## ⚠️ 핵심 버그 수정 사항

### 1. 음파 안 움직임 문제
```typescript
// 문제: audioLevel이 클로저에 캡처되어 업데이트 안됨
// 해결: useRef + Zustand subscribe 패턴
useEffect(() => {
  const unsubscribe = useCallStore.subscribe((state) => {
    audioLevelRef.current = state.audioLevel;
  });
  return unsubscribe;
}, []);
```

### 2. 발신음 안 나는 문제
```typescript
// 문제: Audio 요소 생성 타이밍
// 해결: 컴포넌트 마운트 시 사전 로드
useEffect(() => {
  audio = new Audio('/sounds/ringback_korea.wav');
  audio.preload = 'auto';
  audio.load();
}, []);
```

### 3. speaking 시 audioLevel 0 문제
```typescript
// 문제: 재생 오디오의 레벨을 측정하지 않음
// 해결: AnalyserNode 연결
source.connect(analyserRef.current);
analyserRef.current.connect(ctx.destination);
// requestAnimationFrame으로 레벨 모니터링
```

### 4. 모델 선택 반영 안됨
```typescript
// 문제: voiceId가 greeting 요청에 포함 안됨
// 해결: greeting 메시지에 voiceId 명시적 포함
ws.send(JSON.stringify({
  type: 'greeting',
  voice_id: voiceId  // 현재 선택된 모델
}));
```

---

## 📊 테스트 체크리스트

### 기능 테스트
- [ ] 연락처 화면에서 GD 탭 → 전화 시작
- [ ] 발신 중 화면에서 발신음 재생
- [ ] 2-5초 후 GD 인사말 재생
- [ ] 통화 시간 타이머 동작
- [ ] 음파 시각화 (listening/speaking)
- [ ] 음소거 토글 동작
- [ ] 스피커 토글 동작
- [ ] 대화 내용 팝업
- [ ] 설정 변경 (서버 주소, 음성 모델)
- [ ] 통화 종료

### 오디오 테스트
- [ ] 발신음 재생 및 중지
- [ ] 마이크 권한 요청
- [ ] 음성 녹음 및 전송
- [ ] STT 결과 수신
- [ ] TTS 오디오 재생
- [ ] Barge-in (끼어들기)

### 에러 처리
- [ ] WebSocket 연결 실패
- [ ] 마이크 권한 거부
- [ ] 서버 에러
- [ ] 네트워크 끊김

---

## 📝 추가 개선 아이디어 (Future)

1. **GD Initiative** - 5초 침묵 시 GD가 먼저 말걸기 (이미 서버 지원)
2. **대화 기록 저장** - localStorage/IndexedDB
3. **다크/라이트 테마** - 시스템 설정 연동
4. **통화 품질 표시** - 네트워크 상태, 지연 시간
5. **PWA 지원** - 오프라인 알림, 설치 가능
6. **진동 피드백** - 전화 연결 시 햅틱
7. **배경 효과** - 통화 중 그라데이션 애니메이션
8. **이모지 반응** - 대화 중 빠른 반응

---

## 🚀 시작하기

```bash
# 1. 새 프로젝트 생성
npx create-next-app@latest gd-voice-call --typescript --tailwind --app --src-dir

# 2. 의존성 설치
pnpm add zustand lucide-react

# 3. shadcn/ui 설정
npx shadcn-ui@latest init
npx shadcn-ui@latest add button sheet slider select

# 4. 사운드 파일 복사
cp -r ../tts_test_app/public/sounds ./public/

# 5. 개발 서버 시작
pnpm dev --port 5002
```

---

**작성일**: 2026-03-02
**작성자**: Claude (da:plan)
**상태**: Draft - 사용자 승인 대기
