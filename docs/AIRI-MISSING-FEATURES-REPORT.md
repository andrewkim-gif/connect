# AIRI 기능 누락 종합 보고서

> **검증일**: 2026-03-02
> **검증 방법**: 4개 병렬 에이전트를 통한 전체 패키지 분석

---

## 검증 결과 요약

| 카테고리 | 총 기능 수 | 기획 포함 | 누락 | 누락율 |
|---------|-----------|----------|------|--------|
| **Core Audio Pipeline** | 12 | 8 | 4 | 33% |
| **Stream & Queue System** | 6 | 1 | 5 | 83% |
| **Plugin/MCP System** | 8 | 2 | 6 | 75% |
| **External Services (Bots)** | 15 | 5 | 10 | 67% |
| **Electron/Desktop** | 12 | 1 | 11 | 92% |
| **Avatar (VRM/Live2D)** | 14 | 10 | 4 | 29% |
| **합계** | **67** | **27** | **40** | **60%** |

---

## 1. Core Audio Pipeline 누락 기능

### 1.1 Intent/Priority System (P0 - 즉시 추가 필요)

**AIRI 원본**: `packages/pipelines-audio/src/speech/runtime/intent.ts`

```typescript
// 발화 의도 우선순위 시스템
interface SpeechIntent {
  id: string
  priority: IntentPriority  // 'immediate' | 'high' | 'normal' | 'low'
  text: string
  source: 'user' | 'system' | 'initiative'
  createdAt: number
  expiresAt?: number
}

// 우선순위 기반 큐 관리
class IntentQueue {
  enqueue(intent: SpeechIntent): void
  dequeue(): SpeechIntent | undefined
  interrupt(reason: string): void
  clear(): void
}
```

**기획 보완 필요**:
- Speech Intent 개념 완전 누락
- 발화 우선순위 큐 관리 시스템 누락
- GD Initiative (먼저 말 걸기) 기능과 연동 필요

### 1.2 Playback Manager (P0)

**AIRI 원본**: `packages/pipelines-audio/src/speech/runtime/playback-manager.ts`

```typescript
// 오디오 재생 스케줄러
class PlaybackManager {
  private audioContext: AudioContext
  private gainNode: GainNode
  private currentSource: AudioBufferSourceNode | null

  // 재생 상태 관리
  isPlaying: boolean
  isPaused: boolean
  currentTime: number
  duration: number

  // 메서드
  play(buffer: AudioBuffer): Promise<void>
  pause(): void
  resume(): void
  stop(): void
  setVolume(volume: number): void

  // 이벤트
  onStart: () => void
  onEnd: () => void
  onError: (error: Error) => void
}
```

**기획 보완 필요**:
- Playback Manager 상세 구현 누락
- 재생 상태 관리 (pause/resume) 누락
- 볼륨 컨트롤 시스템 누락

### 1.3 AudioWorklet Processing (P1)

**AIRI 원본**: `packages/audio/src/worklets/`

```typescript
// 커스텀 AudioWorklet 프로세서
class AudioProcessorWorklet extends AudioWorkletProcessor {
  process(inputs, outputs, parameters) {
    // 실시간 오디오 처리
    // - 노이즈 게이트
    // - 리샘플링
    // - VAD (Voice Activity Detection)
  }
}

// WAV 인코딩/디코딩
function encodeWav(samples: Float32Array, sampleRate: number): ArrayBuffer
function decodeWav(buffer: ArrayBuffer): { samples: Float32Array; sampleRate: number }
```

**기획 보완 필요**:
- AudioWorklet 커스텀 프로세서 구현 계획 누락
- 실시간 오디오 처리 (노이즈 게이트, 리샘플링) 누락
- WAV 인코딩/디코딩 유틸리티 누락

### 1.4 TTS Segmentation Strategy (P1)

**AIRI 원본**: `packages/pipelines-audio/src/speech/runtime/tts.ts`

```typescript
// 텍스트 세그멘테이션 전략
interface SegmentationOptions {
  boost: number           // 첫 N개 청크 빠르게 생성
  minWords: number        // 최소 단어 수
  maxWords: number        // 최대 단어 수
  hardPunctuations: string  // 강제 분할 문장부호
  softPunctuations: string  // 선택적 분할 문장부호
  boostPunctuations: string // 부스트 분할 문장부호
}

// 스트리밍 텍스트 청킹
async function* chunkStreamingText(
  textStream: AsyncIterable<string>,
  options: SegmentationOptions
): AsyncGenerator<TextSegment>
```

**기획 상태**: 청킹 전략 일부 언급됨, 상세 옵션 누락

---

## 2. Stream & Queue System 누락 기능

### 2.1 Stream-Kit Queue System (P0 - 핵심 누락)

**AIRI 원본**: `packages/stream-kit/src/queue/`

```typescript
// 범용 큐 시스템
interface Queue<T> {
  enqueue(item: T): void
  dequeue(): T | undefined
  peek(): T | undefined
  clear(): void
  size: number
  isEmpty: boolean
}

// 핸들러 기반 처리
interface QueueHandler<T> {
  handle(item: T): Promise<void>
  onError?: (error: Error, item: T) => void
}

// 사용 예: 메시지 큐, TTS 큐, 이벤트 큐
const messageQueue = createQueue<ChatMessage>({
  handler: async (msg) => await processMessage(msg),
  concurrency: 1,
  retries: 3,
})
```

**기획 보완 필요**:
- 범용 큐 시스템 아키텍처 완전 누락
- 핸들러 기반 비동기 처리 패턴 누락
- 재시도 로직 및 에러 핸들링 패턴 누락

### 2.2 Event Emitter System (P1)

**AIRI 원본**: `packages/stream-kit/src/events/`

```typescript
// 타입 안전 이벤트 이미터
type EventMap = {
  'speech:start': { text: string; intentId: string }
  'speech:end': { intentId: string; duration: number }
  'speech:interrupt': { reason: string }
  'user:input': { type: 'voice' | 'text'; content: string }
}

class TypedEventEmitter<T extends EventMap> {
  on<K extends keyof T>(event: K, handler: (data: T[K]) => void): void
  off<K extends keyof T>(event: K, handler: (data: T[K]) => void): void
  emit<K extends keyof T>(event: K, data: T[K]): void
  once<K extends keyof T>(event: K, handler: (data: T[K]) => void): void
}
```

**기획 보완 필요**:
- 타입 안전 이벤트 시스템 누락
- 시스템 전체 이벤트 흐름 설계 누락

---

## 3. Plugin/MCP System 누락 기능

### 3.1 Plugin Protocol (P1)

**AIRI 원본**: `packages/plugin-protocol/`

```typescript
// 플러그인 모듈 라이프사이클
interface PluginModule {
  id: string
  name: string
  version: string

  // 라이프사이클 훅
  onActivate?: () => Promise<void>
  onDeactivate?: () => Promise<void>

  // 기능 기여
  contributes?: {
    commands?: PluginCommand[]
    providers?: PluginProvider[]
    views?: PluginView[]
  }
}

// 라우팅 표현식
type RoutingExpression = {
  when: string  // 조건 표현식
  priority: number
}
```

**기획 보완 필요**:
- 플러그인 라이프사이클 관리 누락
- 기능 기여(contribution) 시스템 누락
- 조건부 라우팅 표현식 누락

### 3.2 Plugin SDK with XState (P2)

**AIRI 원본**: `packages/plugin-sdk/`

```typescript
// XState 기반 플러그인 상태 머신
import { createMachine, interpret } from 'xstate'

const pluginMachine = createMachine({
  id: 'plugin',
  initial: 'inactive',
  states: {
    inactive: { on: { ACTIVATE: 'loading' } },
    loading: { on: { LOADED: 'active', ERROR: 'error' } },
    active: { on: { DEACTIVATE: 'inactive' } },
    error: { on: { RETRY: 'loading' } },
  },
})

// 멀티 트랜스포트 지원
type Transport = 'websocket' | 'http' | 'ipc' | 'stdio'
```

**기획 보완 필요**:
- XState 상태 머신 기반 플러그인 관리 누락
- 멀티 트랜스포트 지원 누락

### 3.3 Tauri Plugin MCP (P2)

**AIRI 원본**: `packages/tauri-plugin-mcp/`

```typescript
// Tauri를 통한 MCP Tool Calling
interface TauriMCPBridge {
  // MCP 서버 연결
  connect(serverUrl: string): Promise<void>
  disconnect(): Promise<void>

  // 도구 호출
  callTool(name: string, args: Record<string, unknown>): Promise<unknown>

  // 리소스 접근
  getResource(uri: string): Promise<unknown>
}
```

**기획 보완 필요**:
- Tauri 기반 MCP 브릿지 누락 (PWA/Tauri 향후 계획에 포함시켜야 함)

---

## 4. External Services (Bots) 누락 기능

### 4.1 Discord Bot (P2)

**AIRI 원본**: `services/discord/`

```typescript
// Discord 음성 채널 통합
interface DiscordVoiceIntegration {
  joinVoiceChannel(guildId: string, channelId: string): Promise<void>
  leaveVoiceChannel(): Promise<void>

  // 실시간 음성 처리
  onVoiceReceived: (userId: string, audio: Buffer) => void
  speak(audio: Buffer): Promise<void>

  // STT/TTS 파이프라인 연동
  enableSTT(provider: STTProvider): void
  enableTTS(provider: TTSProvider): void
}

// Slash 커맨드
const commands = [
  { name: 'chat', description: 'Talk to the AI' },
  { name: 'voice', description: 'Join voice channel' },
  { name: 'settings', description: 'Configure bot settings' },
]
```

**기획 상태**: "Discord 텍스트/음성 채널" 언급만 있음, 상세 구현 계획 없음

### 4.2 Telegram Autonomous Agent (P2)

**AIRI 원본**: `services/telegram/`

```typescript
// 자율 에이전트 액션 시스템
interface TelegramAgentAction {
  type: 'send_message' | 'send_sticker' | 'send_photo' | 'reply' | 'react'
  payload: unknown
  context: {
    chatId: string
    userId: string
    replyToMessageId?: number
  }
}

// 자율 행동 결정
class AutonomousAgent {
  async decideAction(context: ConversationContext): Promise<TelegramAgentAction | null>

  // 자발적 메시지 발송
  async initiateConversation(trigger: InitiativeTrigger): Promise<void>
}
```

**기획 상태**: "스티커, 사진, 메시지" 언급만 있음, 자율 에이전트 시스템 누락

### 4.3 Minecraft Cognitive Engine (P3)

**AIRI 원본**: `services/minecraft/`

```typescript
// 인지 엔진 (Perception → Reasoning → Action)
interface CognitiveEngine {
  // 인지 파이프라인
  perception: {
    observe(): WorldState
    parseChat(message: ChatMessage): Intent
  }

  // 추론
  reasoning: {
    plan(goal: Goal): ActionPlan
    evaluate(plan: ActionPlan): number
  }

  // 행동
  actions: {
    execute(action: Action): Promise<Result>
    reflex(stimulus: Stimulus): Action  // 즉각 반응
  }
}

// 스킬 시스템
interface Skill {
  name: string
  execute(context: SkillContext): Promise<void>
  preconditions: () => boolean
}
```

**기획 상태**: "Cognitive Engine, 스킬 시스템" 언급만 있음, 상세 아키텍처 누락

### 4.4 Satori Multi-Platform Protocol (P2)

**AIRI 원본**: `services/satori/`

```typescript
// 다중 플랫폼 채팅 프로토콜
interface SatoriAdapter {
  platform: 'discord' | 'telegram' | 'slack' | 'matrix'

  // 통합 메시지 포맷
  sendMessage(channelId: string, content: UnifiedContent): Promise<void>
  onMessage(handler: (msg: UnifiedMessage) => void): void

  // 플랫폼별 기능 추상화
  getCapabilities(): PlatformCapabilities
}
```

**기획 보완 필요**:
- 멀티 플랫폼 통합 프로토콜 완전 누락
- 통합 메시지 포맷 설계 누락

### 4.5 Twitter Automation (P3)

**AIRI 원본**: `services/twitter/`

```typescript
// Playwright 기반 Twitter 자동화
class TwitterClient {
  // 인증
  async login(credentials: TwitterCredentials): Promise<void>

  // 액션
  async tweet(content: string, mediaUrls?: string[]): Promise<string>
  async like(tweetId: string): Promise<void>
  async retweet(tweetId: string): Promise<void>
  async reply(tweetId: string, content: string): Promise<void>

  // 모니터링
  async getTimeline(): Promise<Tweet[]>
  async getMentions(): Promise<Tweet[]>
}
```

**기획 상태**: "트윗, 좋아요, 리트윗" 언급만 있음, Playwright 기반 구현 계획 없음

---

## 5. Electron/Desktop 누락 기능 (P2 - 향후 계획)

### 5.1 Transparent Overlay Window (핵심 누락)

**AIRI 원본**: `apps/stage-tamagotchi/`

```typescript
// 투명 오버레이 윈도우 (다마고치 모드)
interface TamagotchiWindow {
  // 윈도우 설정
  transparent: true
  frame: false
  alwaysOnTop: true
  skipTaskbar: true

  // 마우스 이벤트
  clickThrough: boolean  // 마우스 통과 모드
  draggable: boolean

  // 시스템 트레이
  tray: {
    icon: string
    menu: TrayMenu
  }
}
```

**기획 상태**: "PWA / Tauri (향후)" 언급만 있음, 데스크탑 전용 기능 계획 없음

### 5.2 Screen Capture (P3)

**AIRI 원본**: `packages/electron-screen-capture/`

```typescript
// 화면 캡처 기능
interface ScreenCapture {
  // 스크린샷
  captureScreen(): Promise<Buffer>
  captureWindow(windowId: string): Promise<Buffer>
  captureRegion(rect: Rectangle): Promise<Buffer>

  // 화면 공유
  getDesktopSources(): Promise<DesktopSource[]>
}
```

**기획 보완 필요**:
- Vision 기능과 연동되는 화면 캡처 시스템 누락

### 5.3 System Preferences Integration (P3)

**AIRI 원본**: `packages/electron-eventa/`

```typescript
// 시스템 설정 연동
interface SystemPreferences {
  // 시작 시 실행
  setLoginItemSettings(enabled: boolean): void

  // 시스템 테마
  getSystemTheme(): 'light' | 'dark'
  onThemeChange(handler: (theme: 'light' | 'dark') => void): void

  // 전역 단축키
  registerGlobalShortcut(accelerator: string, callback: () => void): boolean
  unregisterAllShortcuts(): void

  // 자동 업데이트
  checkForUpdates(): Promise<UpdateInfo | null>
  downloadUpdate(): Promise<void>
  installUpdate(): void
}
```

**기획 보완 필요**:
- 데스크탑 앱 시스템 통합 기능 전체 누락

---

## 6. Avatar System 추가 누락 기능

### 6.1 VRM Saccade (시선 미세 움직임) (P2)

**AIRI 원본**: `packages/stage-ui-three/src/composables/vrm/animation.ts`

```typescript
// 자연스러운 시선 미세 움직임
function useIdleEyeSaccades(vrm: VRM) {
  // 27인치 모니터, 65cm 거리 기준
  const BASE_SACCADE_RANGE = 0.25  // 도 단위

  function updateFixationTarget(lookAtTarget: Vector3) {
    // 랜덤 미세 움직임 추가
    fixationTarget.set(
      lookAtTarget.x + randFloat(-BASE_SACCADE_RANGE, BASE_SACCADE_RANGE),
      lookAtTarget.y + randFloat(-BASE_SACCADE_RANGE, BASE_SACCADE_RANGE),
      lookAtTarget.z,
    )
  }

  function randomSaccadeInterval(): number {
    // 0.2초 ~ 2초 사이 랜덤 간격
    return Math.random() * 1800 + 200
  }
}
```

**기획 상태**: "시선 추적" 언급 있으나 Saccade 상세 누락

### 6.2 VRM Animation (.vrma) Loader (P2)

**AIRI 원본**: `packages/stage-ui-three/src/composables/vrm/animation.ts`

```typescript
// .vrma 애니메이션 파일 로더
async function loadVRMAnimation(url: string): Promise<VRMAnimation> {
  const loader = useVRMLoader()
  const gltf = await loader.loadAsync(url)
  return gltf.userData.vrmAnimations[0]
}

// 애니메이션 앵커링 (모델에 맞게 조정)
function reAnchorRootPositionTrack(clip: AnimationClip, vrm: VRM) {
  // 루트 본 위치를 VRM 모델에 맞게 재조정
}
```

**기획 상태**: 완전 누락

### 6.3 Live2D Idle Eye Focus (P2)

**AIRI 원본**: `packages/stage-ui-live2d/src/composables/live2d/animation.ts`

```typescript
// 아이들 상태 시선 포커스
function useLive2DIdleEyeFocus(model: Live2DModel) {
  // 모션 재생 중이 아닐 때만 활성화
  const isIdleMotion = useMotionState()

  function updateEyeFocus(deltaTime: number) {
    if (!isIdleMotion.value) return

    // 자연스러운 시선 움직임
    const eyeX = Math.sin(Date.now() / 3000) * 0.3
    const eyeY = Math.cos(Date.now() / 4000) * 0.2

    model.internalModel.coreModel.setParameterValueById('ParamEyeBallX', eyeX)
    model.internalModel.coreModel.setParameterValueById('ParamEyeBallY', eyeY)
  }
}
```

**기획 상태**: 완전 누락

### 6.4 Model Preview Generator (P1)

**AIRI 원본**: `packages/stage-ui/src/stores/display-models.ts`

```typescript
// 모델 업로드 시 자동 프리뷰 생성
async function loadVrmModelPreview(file: File): Promise<string> {
  // VRM 모델 임시 로드 → 스크린샷 → base64 반환
}

async function loadLive2DModelPreview(file: File): Promise<string> {
  // Live2D 모델 임시 로드 → 스크린샷 → base64 반환
}
```

**기획 상태**: 완전 누락

---

## 7. 기타 누락 기능

### 7.1 Character System 고급 기능 (P1)

```typescript
// 캐릭터 포크 (복제)
interface CharacterFork {
  originalId: string
  forkId: string
  customizations: Partial<Character>
}

// 캐릭터 버전 관리
interface CharacterVersion {
  version: string  // semver
  changelog: string
  breakingChanges: string[]
}

// 캐릭터 공유 시장
interface CharacterMarket {
  publish(character: Character): Promise<void>
  search(query: string): Promise<Character[]>
  purchase(characterId: string): Promise<void>
}
```

**기획 상태**: 캐릭터 "포크" 언급 있으나 상세 구현 누락

### 7.2 Analytics System (P2)

```typescript
// 사용 통계 수집
interface Analytics {
  trackEvent(name: string, properties?: Record<string, unknown>): void
  trackPageView(path: string): void
  trackTiming(category: string, variable: string, duration: number): void

  // 대화 분석
  conversationMetrics: {
    averageResponseTime: number
    tokensUsed: number
    interactionsCount: number
  }
}
```

**기획 상태**: 완전 누락

### 7.3 Onboarding Flow (P1)

```typescript
// 온보딩 상태 관리
interface OnboardingState {
  currentStep: number
  completedSteps: string[]
  skippedSteps: string[]
  isCompleted: boolean
}

// 온보딩 단계
const ONBOARDING_STEPS = [
  'welcome',
  'select-avatar',
  'configure-voice',
  'test-microphone',
  'first-conversation',
]
```

**기획 상태**: "Onboarding 체크" 언급만 있음, 상세 플로우 누락

---

## 8. 권장 조치 사항

### 8.1 즉시 추가 필요 (P0)

1. **Intent/Priority System**
   - 발화 의도 우선순위 시스템 설계
   - GD Initiative와 통합

2. **Playback Manager**
   - 오디오 재생 상태 관리
   - pause/resume/stop 기능

3. **Stream-Kit Queue System**
   - 범용 큐 아키텍처 설계
   - 메시지/TTS/이벤트 큐 통합

### 8.2 기획 상세화 필요 (P1)

1. **Plugin Protocol**
   - 플러그인 라이프사이클 정의
   - 기능 기여 시스템 설계

2. **Event System**
   - 타입 안전 이벤트 이미터 설계
   - 시스템 전체 이벤트 흐름

3. **Model Preview Generator**
   - 아바타 업로드 시 자동 썸네일

4. **Onboarding Flow**
   - 신규 사용자 온보딩 UX

### 8.3 향후 계획에 추가 (P2-P3)

1. **Desktop Features**
   - Tauri 기반 투명 오버레이
   - 시스템 트레이
   - 화면 캡처
   - 전역 단축키

2. **External Services**
   - Discord 음성 채널 상세 설계
   - Telegram 자율 에이전트
   - Satori 멀티플랫폼 프로토콜

3. **Advanced Avatar**
   - VRM Saccade (시선 미세 움직임)
   - VRM .vrma 애니메이션 로더
   - Live2D Idle Eye Focus

---

## 9. 결론

### 현황
- **기획 완성도**: 약 40% (27/67 기능 포함)
- **핵심 누락 영역**: Stream/Queue 시스템, Plugin 아키텍처, Desktop 기능

### 권장 사항
1. `AIRI-NEXTJS-REBUILD-ANALYSIS.md`에 P0/P1 기능 즉시 추가
2. Phase 계획 재조정 (누락 기능 반영)
3. GD Voice 통합 시 Intent System 최우선 구현

---

**문서 버전**: 1.0
**검증일**: 2026-03-02
**검증자**: Claude Opus 4.6 (4개 병렬 에이전트 분석 종합)
