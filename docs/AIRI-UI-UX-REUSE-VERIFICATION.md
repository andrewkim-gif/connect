# AIRI UI/UX 스타일 재활용 검증 보고서

## 검증 결과 요약

| 영역 | 재활용 가능성 | 난이도 | 우선순위 |
|------|-------------|--------|---------|
| 🎨 색상 시스템 (Chromatic) | ✅ 높음 | 중간 | P0 |
| 📝 타이포그래피 | ✅ 높음 | 낮음 | P1 |
| 🎭 애니메이션 | ✅ 높음 | 중간 | P1 |
| 🔘 UI 컴포넌트 | ⚠️ 중간 | 높음 | P2 |
| 📐 레이아웃 구조 | ✅ 높음 | 낮음 | P0 |
| 🌗 다크모드 | ✅ 높음 | 낮음 | P0 |

---

## 1. 색상 시스템 분석 (Chromatic Preset)

### AIRI 원본 구현
```typescript
// @proj-airi/unocss-preset-chromatic
// OKLCH 색상 공간 기반 동적 테마 시스템

// CSS 변수 기반 동적 색상
:root {
  --chromatic-hue: 220.44;  // 기본 색조 (파란 계열)
  --chromatic-chroma: calc(0.18 + (cos(var(--chromatic-hue) * 3.14159265 / 180) * 0.04));
}

// 12단계 색상 쉐이드 (50-950)
--chromatic-chroma-50: calc(var(--chromatic-chroma) * 0.3);
--chromatic-chroma-100: calc(var(--chromatic-chroma) * 0.5);
// ... 950까지
```

### Next.js/Tailwind 전환 전략
```typescript
// tailwind.config.ts
import { oklch } from 'culori';

const chromaticColors = {
  primary: {
    DEFAULT: 'oklch(62% var(--chroma) calc(var(--hue) + 0))',
    50: 'oklch(95% calc(var(--chroma) * 0.3) calc(var(--hue) + 0))',
    100: 'oklch(95% calc(var(--chroma) * 0.5) calc(var(--hue) + 0))',
    // ... 950까지
  },
  complementary: {
    // hue + 180도 오프셋
  }
};

export default {
  theme: {
    extend: {
      colors: chromaticColors,
    }
  }
};
```

### 재활용 방법
1. **CSS 변수 유지**: `--chromatic-hue`, `--chromatic-chroma-*` 변수명 동일하게 사용
2. **globals.css에 프리플라이트 추가**: AIRI의 `:root` 정의 그대로 복사
3. **Tailwind 플러그인 생성**: `tailwind-preset-chromatic.ts` 작성

---

## 2. 타이포그래피 시스템

### AIRI 폰트 스택
```yaml
Primary_Fonts:
  sans: "DM Sans Variable"
  sans-rounded: "Comfortaa Variable"
  cute: "Sniglet, Kiwi Maru"  # 일본어/영어 귀여운 폰트
  mono: "DM Mono"
  serif: "DM Serif Display"

Special_Fonts:
  jura: "Jura Variable"       # 미래적 느낌
  gugi: "Gugi"                # 한국어 특화
  quicksand: "Quicksand Variable"
  urbanist: "Urbanist Variable"
  m-plus-rounded: "M PLUS Rounded 1c"  # 일본어 둥근 폰트
```

### Next.js 전환
```typescript
// app/layout.tsx
import { DM_Sans, Comfortaa, Kiwi_Maru } from 'next/font/google';

const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-sans',
});

const comfortaa = Comfortaa({
  subsets: ['latin'],
  variable: '--font-sans-rounded',
});

// tailwind.config.ts
fontFamily: {
  sans: ['var(--font-sans)', 'system-ui'],
  'sans-rounded': ['var(--font-sans-rounded)', 'var(--font-sans)'],
  cute: ['Sniglet', 'Kiwi Maru', 'var(--font-sans-rounded)'],
}
```

---

## 3. 애니메이션 시스템

### AIRI 핵심 애니메이션
```css
/* vue-transitions.css - 그대로 재활용 가능 */

/* 페이드 슬라이드 (좌→우) */
.fade-slide-out-l-to-r-enter-active,
.fade-slide-out-l-to-r-leave-active {
  transition: opacity 0.2s ease-in-out, transform 0.2s ease-in-out;
}

/* 오버레이 */
@keyframes overlayShow {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* 콘텐츠 팝업 */
@keyframes contentShow {
  from {
    opacity: 0;
    transform: translate(-50%, -48%) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
}

/* 슬라이드 애니메이션 (4방향) */
@keyframes slideUpAndFade { /* ... */ }
@keyframes slideDownAndFade { /* ... */ }
@keyframes slideLeftAndFade { /* ... */ }
@keyframes slideRightAndFade { /* ... */ }
```

### Next.js 전환
```typescript
// tailwind.config.ts
animation: {
  keyframes: {
    'overlay-show': '{ from { opacity: 0 } to { opacity: 1 } }',
    'content-show': '{ from { opacity: 0; transform: translate(-50%, -48%) scale(0.96) } to { opacity: 1; transform: translate(-50%, -50%) scale(1) } }',
    'slide-up-fade': '{ from { opacity: 0; transform: translateY(2px) } to { opacity: 1; transform: translateY(0) } }',
    // ...
  },
  durations: {
    'overlay-show': '300ms',
    'content-show': '150ms',
    'slide-up-fade': '400ms',
  },
  timingFns: {
    'overlay-show': 'cubic-bezier(0.16, 1, 0.3, 1)',
    // ...
  }
}
```

### Framer Motion 래퍼
```tsx
// components/transitions/fade-slide.tsx
import { motion } from 'framer-motion';

export const FadeSlide = ({ children, direction = 'left' }) => (
  <motion.div
    initial={{ opacity: 0, x: direction === 'left' ? -10 : 10 }}
    animate={{ opacity: 1, x: 0 }}
    exit={{ opacity: 0, x: direction === 'left' ? 10 : -10 }}
    transition={{ duration: 0.2, ease: 'easeInOut' }}
  >
    {children}
  </motion.div>
);
```

---

## 4. UI 컴포넌트 매핑

### AIRI 컴포넌트 → shadcn/ui + 커스텀

| AIRI 컴포넌트 | 재활용 전략 | 난이도 |
|--------------|-------------|--------|
| `@proj-airi/ui/Button` | shadcn Button + 스타일 오버라이드 | 낮음 |
| `@proj-airi/ui/Input` | shadcn Input + 스타일 오버라이드 | 낮음 |
| `@proj-airi/ui/Select` | shadcn Select (Radix 기반, 동일) | 낮음 |
| `@proj-airi/ui/Combobox` | shadcn Combobox (Reka UI → Radix) | 중간 |
| `PoppinText` | 커스텀 구현 필요 (스트리밍 텍스트) | 높음 |
| `WidgetStage` | 커스텀 구현 (Three.js/Live2D) | 높음 |

### Button 스타일 매핑
```tsx
// AIRI 버튼 variant를 shadcn에 적용
// components/ui/button.tsx

const buttonVariants = cva(
  "rounded-lg font-medium outline-none transition-all duration-200 ease-in-out disabled:cursor-not-allowed disabled:opacity-50 backdrop-blur-md focus:ring-2",
  {
    variants: {
      variant: {
        primary: [
          "bg-primary-500/15 hover:bg-primary-500/20 active:bg-primary-500/30",
          "dark:bg-primary-700/30 dark:hover:bg-primary-700/40 dark:active:bg-primary-700/30",
          "focus:ring-primary-300/60 dark:focus:ring-primary-600/30",
          "border-2 border-solid border-primary-500/5 dark:border-primary-900/40",
          "text-primary-950 dark:text-primary-100",
        ].join(" "),
        secondary: [
          "bg-neutral-100/55 hover:bg-neutral-400/20 active:bg-neutral-400/30",
          "dark:bg-neutral-700/60 dark:hover:bg-neutral-700/80 dark:active:bg-neutral-700/60",
          // ...
        ].join(" "),
        danger: [
          "bg-red-500/15 hover:bg-red-500/20 active:bg-red-500/30",
          // ...
        ].join(" "),
        ghost: "bg-transparent hover:bg-neutral-100/50 dark:hover:bg-neutral-800/50",
      },
      size: {
        sm: "px-3 py-1.5 text-xs",
        md: "px-4 py-2 text-sm",
        lg: "px-6 py-3 text-base",
      }
    }
  }
);
```

---

## 5. 레이아웃 구조

### AIRI 메인 레이아웃
```
┌─────────────────────────────────────────┐
│              Header (반응형)             │
│  Desktop: full nav  │  Mobile: hamburger │
├─────────────────────┬───────────────────┤
│                     │                   │
│    WidgetStage      │  InteractiveArea  │
│    (Avatar 영역)     │  (채팅/설정 영역)  │
│    flex-1           │  max-w-500px      │
│                     │  min-w-30%        │
│                     │                   │
├─────────────────────┴───────────────────┤
│    MobileInteractiveArea (모바일 전용)    │
└─────────────────────────────────────────┘
```

### Next.js App Router 레이아웃
```tsx
// app/layout.tsx
export default function RootLayout({ children }) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body className={cn(dmSans.variable, comfortaa.variable)}>
        <ThemeProvider>
          <StageTransitionProvider>
            {children}
          </StageTransitionProvider>
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}

// app/(main)/page.tsx
export default function MainPage() {
  return (
    <BackgroundProvider>
      <div className="relative flex flex-col z-2 h-[100dvh] w-[100vw] overflow-hidden">
        <Header className="hidden md:flex" />
        <MobileHeader className="flex md:hidden" />

        <div className="relative flex flex-1 flex-row gap-x-2 md:flex-col">
          <WidgetStage className="flex-1 min-w-1/2" />
          <InteractiveArea className="hidden md:flex max-w-[500px] min-w-[30%]" />
          <MobileInteractiveArea className="md:hidden" />
        </div>
      </div>
    </BackgroundProvider>
  );
}
```

---

## 6. 다크모드 구현

### AIRI 다크모드 패턴
```css
/* 전역 배경 */
:root {
  --bg-color-light: rgb(255 255 255);
  --bg-color-dark: rgb(18 18 18);
  --bg-color: var(--bg-color-light);
}

html.dark {
  --bg-color: var(--bg-color-dark);
  color-scheme: dark;
}

/* 컴포넌트 레벨 */
.component {
  @apply bg-neutral-50 dark:bg-neutral-950;
  @apply text-neutral-950 dark:text-neutral-100;
  @apply border-neutral-200 dark:border-neutral-800;
}
```

### Next.js + next-themes
```tsx
// components/theme-provider.tsx
import { ThemeProvider as NextThemesProvider } from "next-themes";

export function ThemeProvider({ children }) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange={false}
    >
      {children}
    </NextThemesProvider>
  );
}
```

---

## 7. 특수 컴포넌트 재구현 가이드

### PoppinText (스트리밍 텍스트 애니메이션)
```tsx
// components/poppin-text.tsx
'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface PoppinTextProps {
  text?: string | ReadableStream<Uint8Array>;
  className?: string;
}

export function PoppinText({ text, className }: PoppinTextProps) {
  const [characters, setCharacters] = useState<string[]>([]);

  useEffect(() => {
    if (typeof text === 'string') {
      const segmenter = new Intl.Segmenter('und', { granularity: 'grapheme' });
      setCharacters([...segmenter.segment(text)].map(s => s.segment));
    } else if (text) {
      // ReadableStream 처리
      const reader = text.getReader();
      const decoder = new TextDecoder();
      // ... 스트림 처리 로직
    }
  }, [text]);

  return (
    <div className={className}>
      <AnimatePresence>
        {characters.map((char, i) => (
          <motion.span
            key={i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-block text-primary-400 dark:text-primary-100"
          >
            {char}
          </motion.span>
        ))}
      </AnimatePresence>
    </div>
  );
}
```

### BackgroundProvider (그라데이션 배경)
```tsx
// components/background-provider.tsx
'use client';

import { useTheme } from 'next-themes';
import { cn } from '@/lib/utils';

export function BackgroundProvider({ children, className }) {
  const { resolvedTheme } = useTheme();

  return (
    <div
      className={cn(
        "relative min-h-screen transition-all duration-300",
        resolvedTheme === 'dark' ? 'bg-[#121212]' : 'bg-white',
        className
      )}
    >
      {/* Gradient overlay */}
      <div
        className="pointer-events-none absolute inset-x-0 top-0 z-1 h-24 lg:h-32"
        style={{
          background: `linear-gradient(to bottom,
            oklch(62% var(--chroma) var(--hue)) 0%,
            transparent 100%)`
        }}
      />
      {children}
    </div>
  );
}
```

---

## 8. 파일 구조 권장사항

```
app/
├── globals.css              # AIRI CSS 변수 + Tailwind 통합
├── layout.tsx               # 폰트, 테마 프로바이더
├── (main)/
│   ├── page.tsx             # 메인 페이지 (index.vue 대응)
│   └── layout.tsx           # 메인 레이아웃
├── settings/
│   ├── page.tsx
│   └── characters/
│       └── page.tsx
└── auth/
    └── login/page.tsx

components/
├── ui/                      # shadcn/ui 기반 (AIRI 스타일 적용)
│   ├── button.tsx
│   ├── input.tsx
│   ├── select.tsx
│   └── combobox.tsx
├── layouts/
│   ├── header.tsx           # AIRI Header 포팅
│   ├── mobile-header.tsx
│   ├── interactive-area.tsx
│   └── background-provider.tsx
├── widgets/
│   ├── poppin-text.tsx      # 스트리밍 텍스트
│   ├── popping-subtitles.tsx
│   └── widget-stage.tsx     # 아바타 스테이지
├── transitions/
│   ├── fade-slide.tsx
│   ├── stage-transition.tsx
│   └── index.ts
└── providers/
    ├── theme-provider.tsx
    └── stage-transition-provider.tsx

styles/
├── chromatic.css            # AIRI chromatic 색상 시스템
├── transitions.css          # AIRI 트랜지션
└── vue-transitions.css      # Vue 트랜지션 → React 변환
```

---

## 9. 검증 체크리스트

### Phase 1: 기반 시스템 (Week 1-2)
- [ ] Chromatic 색상 시스템 Tailwind 플러그인 구현
- [ ] 폰트 시스템 설정 (next/font)
- [ ] globals.css에 CSS 변수 정의
- [ ] 다크모드 테마 프로바이더 구현
- [ ] 기본 트랜지션 CSS 포팅

### Phase 2: 핵심 컴포넌트 (Week 3-4)
- [ ] Button 컴포넌트 (7가지 variant)
- [ ] Input/Select/Combobox 컴포넌트
- [ ] Header/MobileHeader 레이아웃
- [ ] BackgroundProvider 컴포넌트
- [ ] Toaster 통합

### Phase 3: 특수 컴포넌트 (Week 5-6)
- [ ] PoppinText 스트리밍 텍스트
- [ ] StageTransition 페이지 전환
- [ ] WidgetStage 아바타 영역
- [ ] InteractiveArea 채팅 영역

---

## 10. 결론

### ✅ 재활용 권장 항목
1. **Chromatic 색상 시스템**: OKLCH 기반 동적 테마는 CSS 변수로 완벽 재활용 가능
2. **타이포그래피**: DM Sans, Comfortaa 등 Google Fonts로 동일하게 사용
3. **애니메이션 키프레임**: CSS 애니메이션은 그대로 포팅 가능
4. **다크모드 패턴**: Tailwind dark: 프리픽스 + next-themes로 동일 구현
5. **레이아웃 구조**: 반응형 레이아웃 패턴 그대로 적용

### ⚠️ 수정 필요 항목
1. **Reka UI → Radix UI**: 컴포넌트 기반 라이브러리 전환 필요
2. **Vue Transition → Framer Motion**: 페이지 전환 로직 재구현
3. **UnoCSS → Tailwind**: 일부 유틸리티 클래스 문법 차이

### 🎯 핵심 가치 보존
- **독특한 OKLCH 기반 색상 시스템** → 그대로 유지
- **부드러운 cubic-bezier 애니메이션** → 동일 타이밍 함수 사용
- **glassmorphism 효과** → backdrop-blur-md 스타일 유지
- **반응형 모바일/데스크탑 레이아웃** → 동일 브레이크포인트 사용

---

**문서 버전**: 1.0
**검증일**: 2026-03-02
**검증자**: Claude Opus 4.6
