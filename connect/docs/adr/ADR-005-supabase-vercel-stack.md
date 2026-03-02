# ADR-005: Supabase + Vercel Stack Selection

## Status
**Accepted**

## Context
PLAN.md에서는 PostgreSQL + Redis + NextAuth + Socket.io + Docker 조합을 계획했습니다.
그러나 사용자가 **Supabase + Vercel** 스택을 명시적으로 요청했습니다.

### 요구사항
- 빠른 개발 속도 (MVP 12주)
- 관리 부담 최소화
- 실시간 기능 (타이핑, 메시지)
- 글로벌 배포 (한국 중심)
- 비용 효율성

## Decision
**Next.js 14 + Supabase + Vercel** 풀스택 솔루션을 채택합니다.

### 스택 구성

```
┌─────────────────────────────────────────────────────┐
│  Frontend: Next.js 14 (App Router)                  │
│  Backend: Vercel Edge Functions                     │
│  Database: Supabase PostgreSQL + pgvector           │
│  Auth: Supabase Auth (OAuth)                        │
│  Realtime: Supabase Realtime (WebSocket)            │
│  Storage: Supabase Storage (CDN)                    │
│  Hosting: Vercel (Edge Network)                     │
└─────────────────────────────────────────────────────┘
```

## Rationale

### 1. Supabase 선정 이유

| Feature | Self-hosted | Supabase | 비교 |
|---------|-------------|----------|------|
| PostgreSQL | 직접 관리 | 관리형 | ✓ 운영 부담 감소 |
| Auth | NextAuth 구현 | 내장 | ✓ RLS 자동 연동 |
| Realtime | Socket.io 구현 | 내장 | ✓ 즉시 사용 가능 |
| Storage | S3 설정 | 내장 CDN | ✓ RLS 적용 |
| pgvector | 직접 설치 | 활성화만 | ✓ RAG 즉시 사용 |

### 2. Vercel 선정 이유

| Feature | Docker/nginx | Vercel | 비교 |
|---------|--------------|--------|------|
| 배포 | 수동 설정 | Git push | ✓ CI/CD 자동화 |
| 스케일링 | 수동 | 자동 | ✓ Serverless |
| CDN | 별도 설정 | 글로벌 내장 | ✓ 즉시 적용 |
| Edge | 불가능 | Edge Runtime | ✓ 낮은 지연시간 |
| Preview | 수동 | PR별 자동 | ✓ 협업 효율 |

### 3. 통합 시너지

```
Supabase + Vercel = Managed Full-Stack

- Vercel Supabase Integration 공식 지원
- 환경 변수 자동 주입
- Edge Function에서 Supabase 최적화
- 공유된 리전 (서울/도쿄)
```

## Alternatives Rejected

### 1. PlanetScale + Vercel
- **장점**: MySQL 호환, 브랜칭
- **단점**: pgvector 없음 (RAG 불가), Realtime 없음
- **결론**: 벡터 검색 필수로 탈락

### 2. Firebase + Vercel
- **장점**: Realtime Database, Auth
- **단점**: NoSQL (관계형 필요), 벡터 검색 없음
- **결론**: 복잡한 쿼리에 부적합

### 3. Neon + Vercel
- **장점**: Serverless PostgreSQL, 브랜칭
- **단점**: Realtime 없음, Auth 없음, Storage 없음
- **결론**: 추가 서비스 필요로 복잡성 증가

### 4. Self-hosted (원래 PLAN.md)
- **장점**: 완전한 제어권
- **단점**: 운영 부담, 스케일링 수동, 개발 지연
- **결론**: MVP 속도 우선으로 탈락

## Consequences

### Positive
- **개발 속도 2-3배 향상**: 인프라 설정 없이 즉시 개발
- **운영 부담 제거**: 관리형 서비스로 유지보수 최소화
- **자동 스케일링**: 트래픽 증가에 자동 대응
- **보안 기본 탑재**: RLS, TLS, JWT 기본 제공
- **글로벌 성능**: 서울 리전 + Edge Network

### Negative
- **벤더 종속**: Supabase/Vercel 의존성
- **비용 증가 가능**: 트래픽 증가 시 예상보다 높을 수 있음
- **커스터마이징 제한**: 플랫폼 제약 내에서 작업
- **TTS 서버 분리**: 음성 서버는 여전히 self-hosted

### Mitigation
- **탈출 전략**: Supabase는 표준 PostgreSQL, 언제든 마이그레이션 가능
- **비용 모니터링**: Vercel/Supabase 대시보드 알림 설정
- **TTS 연동**: WebSocket 프록시로 기존 TTS 서버 연결 유지

## Implementation Notes

```bash
# 1. Supabase 프로젝트 생성
# https://supabase.com/dashboard → New Project

# 2. Vercel 연결
vercel link
vercel integration add supabase

# 3. 로컬 개발 환경
npx supabase init
npx supabase start
npx supabase db push

# 4. 배포
vercel --prod
```

## References
- [Supabase Documentation](https://supabase.com/docs)
- [Vercel + Supabase Guide](https://vercel.com/integrations/supabase)
- [Next.js 14 App Router](https://nextjs.org/docs/app)
