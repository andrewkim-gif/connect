# ADR-001: Monorepo Structure with Next.js

## Status
**Accepted**

## Context
StarCall 플랫폼은 Frontend(iPhone UI), Backend(API), 그리고 기존 TTS Server 연동이 필요합니다.
코드베이스 구조를 결정해야 합니다.

## Decision
**Next.js App Router 기반 Monorepo** 구조를 채택합니다.

```
starcall/
├── src/
│   ├── app/           # Next.js App Router (Pages + API Routes)
│   ├── components/    # React Components
│   ├── services/      # Business Logic
│   ├── lib/           # Utilities
│   └── types/         # TypeScript Definitions
├── public/            # Static Assets
└── docs/              # Documentation
```

## Rationale
1. **단순성**: 별도 백엔드 서버 없이 Next.js API Routes로 처리
2. **기존 인프라**: TTS Server는 별도 포트(5002)로 이미 운영 중
3. **빠른 개발**: 프론트엔드/백엔드 경계 없이 빠른 이터레이션
4. **배포 용이**: 단일 Docker 이미지로 배포

## Alternatives Rejected
| Alternative | Rejection Reason |
|-------------|------------------|
| Separate Frontend/Backend repos | 관리 복잡성, 배포 파이프라인 2개 |
| NestJS Backend | 오버엔지니어링, 초기 MVP에 불필요 |
| Turborepo Monorepo | 단일 앱에는 과도한 복잡성 |

## Consequences
### Positive
- 빠른 개발 속도
- 타입 공유 용이
- 단순한 배포

### Negative
- 백엔드 확장 시 분리 필요할 수 있음
- API Routes 성능 한계 (고부하 시)

### Mitigation
- 고부하 API는 TTS Server처럼 별도 서비스로 분리
- Edge Functions 활용 검토
