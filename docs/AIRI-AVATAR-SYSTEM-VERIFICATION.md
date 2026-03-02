# 버추얼 아바타 시스템 검증 보고서

## 검증 결과 요약

| 기능 | AIRI 원본 | 기존 기획 | 검증 결과 |
|------|----------|----------|----------|
| VRM 3D 아바타 로딩 | ✅ | ✅ | Pass |
| Live2D 2D 아바타 | ✅ | ✅ | Pass |
| 립싱크 (wLipSync) | ✅ | ✅ | Pass |
| VRM 표정 시스템 | ✅ | ⚠️ 간략 | **상세화 필요** |
| VRM 눈 깜빡임 | ✅ | ❌ 누락 | **추가 필요** |
| VRM 시선 추적 (Saccade) | ✅ | ❌ 누락 | **추가 필요** |
| VRM 애니메이션 (.vrma) | ✅ | ❌ 누락 | **추가 필요** |
| VRM SpringBone 물리 | ✅ | ⚠️ 언급만 | **상세화 필요** |
| Live2D 모션 매니저 | ✅ | ❌ 누락 | **추가 필요** |
| Live2D Beat Sync | ✅ | ❌ 누락 | **추가 필요** |
| Live2D 자동 눈깜빡임 | ✅ | ❌ 누락 | **추가 필요** |
| Live2D 아이들 시선 | ✅ | ❌ 누락 | **추가 필요** |
| 아바타 모델 관리 스토어 | ✅ | ⚠️ DB만 | **로직 상세화 필요** |
| 프리셋 아바타 모델 | ✅ | ❌ 누락 | **추가 필요** |

---

## 1. 누락된 VRM 기능 상세

### 1.1 VRM 표정 시스템 (Expression/Emote)
```typescript
// AIRI 원본: packages/stage-ui-three/src/composables/vrm/expression.ts

// 6가지 기본 감정 상태
const emotionStates = {
  happy: { expression: [{ name: 'happy', value: 1.0 }, { name: 'aa', value: 0.3 }] },
  sad: { expression: [{ name: 'sad', value: 1.0 }, { name: 'oh', value: 0.2 }] },
  angry: { expression: [{ name: 'angry', value: 1.0 }, { name: 'ee', value: 0.4 }] },
  surprised: { expression: [{ name: 'surprised', value: 1.0 }, { name: 'oh', value: 0.6 }] },
  neutral: { expression: [{ name: 'neutral', value: 1.0 }] },
  think: { expression: [{ name: 'think', value: 1.0 }] },
}

// 주요 기능
- setEmotion(name, intensity): 감정 설정
- setEmotionWithResetAfter(name, ms, intensity): 일정 시간 후 자동 리셋
- 부드러운 블렌딩 (easeInOutCubic)
- 다중 blendshape 조합
```

**기획 보완 필요**: 현재 기획서에는 "표정 제어"만 언급되어 있고, 구체적인 감정 상태와 블렌딩 메커니즘이 없음.

### 1.2 VRM 눈 깜빡임 (Blink)
```typescript
// AIRI 원본: packages/stage-ui-three/src/composables/vrm/animation.ts

function useBlink() {
  const BLINK_DURATION = 0.2  // 0.2초 동안 깜빡임
  const MIN_BLINK_INTERVAL = 1  // 최소 1초 간격
  const MAX_BLINK_INTERVAL = 6  // 최대 6초 간격

  // 사인 커브 기반 부드러운 애니메이션
  const blinkValue = Math.sin(Math.PI * blinkProgress)
  vrm.expressionManager.setValue('blink', blinkValue)
}
```

**기획 보완 필요**: 자연스러운 눈 깜빡임 기능 완전 누락.

### 1.3 VRM 시선 추적 (Idle Eye Saccades)
```typescript
// AIRI 원본: packages/stage-ui-three/src/composables/vrm/animation.ts

function useIdleEyeSaccades() {
  // 27인치 모니터, 65cm 거리 기준 자연스러운 시선 움직임 시뮬레이션
  function updateFixationTarget(lookAtTarget) {
    fixationTarget.set(
      lookAtTarget.x + randFloat(-0.25, 0.25),
      lookAtTarget.y + randFloat(-0.25, 0.25),
      lookAtTarget.z,
    )
  }

  // randomSaccadeInterval() 기반 랜덤 시선 이동
}
```

**기획 보완 필요**: 아이들 상태에서의 자연스러운 시선 움직임 기능 누락.

### 1.4 VRM 애니메이션 파일 (.vrma)
```typescript
// AIRI 원본: packages/stage-ui-three/src/composables/vrm/animation.ts

async function loadVRMAnimation(url: string) {
  const loader = useVRMLoader()
  const gltf = await loader.loadAsync(url)
  return gltf.userData.vrmAnimations[0]
}

function reAnchorRootPositionTrack(clip, vrm) {
  // 애니메이션의 루트 포지션을 VRM 모델에 맞게 재앵커링
}
```

**기획 보완 필요**: .vrma 파일 로딩 및 적용 기능 누락. 기본 idle_loop.vrma 애니메이션 포함.

---

## 2. 누락된 Live2D 기능 상세

### 2.1 Live2D 모션 매니저
```typescript
// AIRI 원본: packages/stage-ui-live2d/src/composables/live2d/motion-manager.ts

interface MotionManagerPluginContext {
  model: CubismModel
  internalModel: PixiLive2DInternalModel
  motionManager: PixiLive2DInternalModel['motionManager']
  isIdleMotion: boolean
  // ... 기타 컨텍스트
}

// 플러그인 시스템으로 모션 업데이트 확장 가능
function register(plugin: MotionManagerPlugin, stage: 'pre' | 'post')
```

**기획 보완 필요**: 모션 그룹 관리, 아이들 모션 제어 기능 누락.

### 2.2 Live2D Beat Sync (음악 동기화)
```typescript
// AIRI 원본: packages/stage-ui-live2d/src/composables/live2d/beat-sync.ts

type BeatSyncStyleName = 'punchy-v' | 'balanced-v' | 'swing-lr' | 'sway-sine'

interface BeatStyleConfig {
  topYaw: number     // 머리 좌우 회전
  topRoll: number    // 머리 기울기
  bottomDip: number  // 머리 숙임
  pattern: 'v' | 'swing' | 'sway'
  swingLift?: number
}

// BPM 기반 자동 스타일 전환
if (bpm < 120) style = 'swing-lr'
else if (bpm < 180) style = 'balanced-v'
else style = 'punchy-v'
```

**기획 보완 필요**: 음악/TTS 박자에 맞춘 머리 움직임 동기화 기능 완전 누락. 이는 AIRI의 핵심 차별화 기능.

### 2.3 Live2D 자동 눈깜빡임
```typescript
// AIRI 원본: motion-manager.ts

function useMotionUpdatePluginAutoEyeBlink() {
  const blinkCloseDuration = 200  // ms
  const blinkOpenDuration = 200   // ms
  const minDelay = 3000           // 최소 3초
  const maxDelay = 8000           // 최대 8초

  // Cubism SDK 내장 eyeBlink 또는 커스텀 구현 선택 가능
}
```

**기획 보완 필요**: Live2D 모델의 자동 눈깜빡임 제어 기능 누락.

### 2.4 Live2D 아이들 시선 포커스
```typescript
// AIRI 원본: packages/stage-ui-live2d/src/composables/live2d/animation.ts

function useLive2DIdleEyeFocus() {
  // 아이들 상태에서 자연스러운 시선 움직임
  // 모션이 재생 중이 아닐 때 활성화
}
```

**기획 보완 필요**: 아이들 상태에서의 Live2D 시선 제어 누락.

---

## 3. 누락된 아바타 관리 기능

### 3.1 디스플레이 모델 스토어
```typescript
// AIRI 원본: packages/stage-ui/src/stores/display-models.ts

enum DisplayModelFormat {
  Live2dZip = 'live2d-zip',
  Live2dDirectory = 'live2d-directory',
  VRM = 'vrm',
  PMXZip = 'pmx-zip',
  PMXDirectory = 'pmx-directory',
  PMD = 'pmd',
}

// 프리셋 모델 (기본 제공)
const displayModelsPresets = [
  { id: 'preset-live2d-1', name: 'Hiyori (Pro)', ... },
  { id: 'preset-live2d-2', name: 'Hiyori (Free)', ... },
  { id: 'preset-vrm-1', name: 'AvatarSample_A', ... },
  { id: 'preset-vrm-2', name: 'AvatarSample_B', ... },
]

// 기능
- loadDisplayModelsFromIndexedDB()
- addDisplayModel(format, file)
- removeDisplayModel(id)
- resetDisplayModels()
- 프리뷰 이미지 자동 생성
```

**기획 보완 필요**:
- DB 스키마는 있으나 클라이언트 측 관리 로직 상세 누락
- IndexedDB + LocalForage 기반 오프라인 저장 전략 누락
- 프리셋 모델 배포 전략 누락

### 3.2 모델 프리뷰 생성
```typescript
// VRM 프리뷰
loadVrmModelPreview(file: File): Promise<string>

// Live2D 프리뷰
loadLive2DModelPreview(file: File): Promise<string>
```

**기획 보완 필요**: 아바타 업로드 시 자동 썸네일 생성 기능 누락.

---

## 4. 기획 보완 권장사항

### 4.1 즉시 추가 필요 (P0)
1. **VRM 눈 깜빡임 시스템**
2. **Live2D Beat Sync**
3. **프리셋 아바타 모델 전략**

### 4.2 상세화 필요 (P1)
1. **VRM 표정 시스템 상세**
   - 6가지 기본 감정 + 커스텀 감정 지원
   - 블렌딩 곡선 및 타이밍
2. **Live2D 모션 매니저**
   - 모션 그룹 관리
   - 아이들/액션 모션 분리
3. **아바타 모델 관리 UX**
   - 업로드 플로우
   - 프리뷰 생성
   - 오프라인 캐싱

### 4.3 추가 고려 (P2)
1. **VRM 시선 추적 (Saccade)**
2. **VRM .vrma 애니메이션**
3. **Live2D 자동 눈깜빡임**
4. **Live2D 아이들 시선 포커스**

---

## 5. Next.js 전환 시 구현 코드 예시

### 5.1 VRM 표정 훅
```typescript
// lib/avatar/vrm-expression.ts
import { useCallback, useRef, useState } from 'react';
import type { VRM } from '@pixiv/three-vrm';

type EmotionName = 'happy' | 'sad' | 'angry' | 'surprised' | 'neutral' | 'think';

const EMOTION_CONFIGS: Record<EmotionName, { expressions: { name: string; value: number }[]; blendDuration: number }> = {
  happy: { expressions: [{ name: 'happy', value: 1.0 }, { name: 'aa', value: 0.3 }], blendDuration: 0.3 },
  sad: { expressions: [{ name: 'sad', value: 1.0 }, { name: 'oh', value: 0.2 }], blendDuration: 0.3 },
  angry: { expressions: [{ name: 'angry', value: 1.0 }, { name: 'ee', value: 0.4 }], blendDuration: 0.2 },
  surprised: { expressions: [{ name: 'surprised', value: 1.0 }, { name: 'oh', value: 0.6 }], blendDuration: 0.1 },
  neutral: { expressions: [{ name: 'neutral', value: 1.0 }], blendDuration: 0.5 },
  think: { expressions: [{ name: 'think', value: 1.0 }], blendDuration: 0.5 },
};

export function useVRMExpression(vrm: VRM | null) {
  const [currentEmotion, setCurrentEmotion] = useState<EmotionName>('neutral');
  const transitionRef = useRef({ progress: 0, isTransitioning: false });
  const targetValuesRef = useRef<Map<string, number>>(new Map());
  const currentValuesRef = useRef<Map<string, number>>(new Map());

  const setEmotion = useCallback((emotion: EmotionName, intensity = 1) => {
    if (!vrm?.expressionManager) return;

    const config = EMOTION_CONFIGS[emotion];
    setCurrentEmotion(emotion);
    transitionRef.current = { progress: 0, isTransitioning: true };

    // Reset all expressions
    currentValuesRef.current.clear();
    targetValuesRef.current.clear();

    // Set targets
    for (const expr of config.expressions) {
      currentValuesRef.current.set(expr.name, vrm.expressionManager.getValue(expr.name) ?? 0);
      targetValuesRef.current.set(expr.name, expr.value * Math.min(1, Math.max(0, intensity)));
    }
  }, [vrm]);

  const update = useCallback((deltaTime: number) => {
    if (!vrm?.expressionManager || !transitionRef.current.isTransitioning) return;

    const config = EMOTION_CONFIGS[currentEmotion];
    transitionRef.current.progress += deltaTime / config.blendDuration;

    if (transitionRef.current.progress >= 1) {
      transitionRef.current.progress = 1;
      transitionRef.current.isTransitioning = false;
    }

    const eased = easeInOutCubic(transitionRef.current.progress);

    for (const [name, target] of targetValuesRef.current) {
      const start = currentValuesRef.current.get(name) ?? 0;
      const current = start + (target - start) * eased;
      vrm.expressionManager.setValue(name, current);
    }
  }, [vrm, currentEmotion]);

  return { currentEmotion, setEmotion, update };
}

function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}
```

### 5.2 VRM 눈 깜빡임 훅
```typescript
// lib/avatar/vrm-blink.ts
import { useCallback, useRef } from 'react';
import type { VRM } from '@pixiv/three-vrm';

const BLINK_DURATION = 0.2;
const MIN_BLINK_INTERVAL = 1;
const MAX_BLINK_INTERVAL = 6;

export function useVRMBlink(vrm: VRM | null) {
  const stateRef = useRef({
    isBlinking: false,
    progress: 0,
    timeSinceLastBlink: 0,
    nextBlinkTime: Math.random() * (MAX_BLINK_INTERVAL - MIN_BLINK_INTERVAL) + MIN_BLINK_INTERVAL,
  });

  const update = useCallback((delta: number) => {
    if (!vrm?.expressionManager) return;

    const state = stateRef.current;
    state.timeSinceLastBlink += delta;

    if (!state.isBlinking && state.timeSinceLastBlink >= state.nextBlinkTime) {
      state.isBlinking = true;
      state.progress = 0;
    }

    if (state.isBlinking) {
      state.progress += delta / BLINK_DURATION;
      const blinkValue = Math.sin(Math.PI * state.progress);
      vrm.expressionManager.setValue('blink', blinkValue);

      if (state.progress >= 1) {
        state.isBlinking = false;
        state.timeSinceLastBlink = 0;
        vrm.expressionManager.setValue('blink', 0);
        state.nextBlinkTime = Math.random() * (MAX_BLINK_INTERVAL - MIN_BLINK_INTERVAL) + MIN_BLINK_INTERVAL;
      }
    }
  }, [vrm]);

  return { update };
}
```

### 5.3 Live2D Beat Sync 훅
```typescript
// lib/avatar/live2d-beat-sync.ts
import { useCallback, useRef } from 'react';

type BeatStyle = 'punchy-v' | 'balanced-v' | 'swing-lr' | 'sway-sine';

interface BeatSyncState {
  targetY: number;
  targetZ: number;
  velocityY: number;
  velocityZ: number;
  primed: boolean;
  lastBeatTimestamp: number | null;
  avgInterval: number | null;
  style: BeatStyle;
}

export function useLive2DBeatSync(baseAngles: () => { x: number; y: number; z: number }) {
  const stateRef = useRef<BeatSyncState>({
    targetY: 0,
    targetZ: 0,
    velocityY: 0,
    velocityZ: 0,
    primed: false,
    lastBeatTimestamp: null,
    avgInterval: null,
    style: 'punchy-v',
  });

  const scheduleBeat = useCallback((timestamp?: number) => {
    const now = timestamp ?? performance.now();
    const state = stateRef.current;
    const base = baseAngles();

    if (!state.primed) {
      state.primed = true;
      state.lastBeatTimestamp = now;
      return;
    }

    const interval = state.lastBeatTimestamp ? now - state.lastBeatTimestamp : 600;
    state.lastBeatTimestamp = now;
    state.avgInterval = state.avgInterval ? state.avgInterval * 0.7 + interval * 0.3 : interval;

    // Auto-style based on BPM
    const bpm = 60000 / state.avgInterval;
    state.style = bpm < 120 ? 'swing-lr' : bpm < 180 ? 'balanced-v' : 'punchy-v';

    // Trigger head movement based on style
    // ... (full implementation)
  }, [baseAngles]);

  const updateTargets = useCallback((now: number) => {
    // Spring physics for smooth head movement
    const stiffness = 120;
    const damping = 16;
    // ... (full physics implementation)
  }, []);

  return {
    state: stateRef.current,
    scheduleBeat,
    updateTargets,
  };
}
```

---

## 6. 결론

### 검증 결과
- **Pass**: 기본 VRM/Live2D 로딩, 립싱크는 기획에 포함됨
- **Fail**: 세부 애니메이션 시스템(눈 깜빡임, 시선, Beat Sync)이 대부분 누락됨

### 권장 조치
1. `AIRI-NEXTJS-REBUILD-ANALYSIS.md`에 누락된 아바타 기능 섹션 추가
2. Phase 3 (아바타 시스템) 로드맵에 세부 기능 반영
3. Live2D Beat Sync는 GD Voice의 핵심 차별화 기능이므로 필수 구현

---

**문서 버전**: 1.0
**검증일**: 2026-03-02
**검증자**: Claude Opus 4.6
