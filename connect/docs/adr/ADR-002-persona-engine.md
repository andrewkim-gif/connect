# ADR-002: Persona Engine Architecture

## Status
**Accepted**

## Context
연예인 페르소나를 일관되게 유지하면서 실시간 정보를 반영해야 합니다.
페르소나 시스템의 아키텍처를 결정해야 합니다.

## Decision
**RAG + Constitutional AI + Web Search** 하이브리드 아키텍처를 채택합니다.

```
┌─────────────────────────────────────────────────┐
│                 Persona Engine                   │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  │
│  │ Knowledge │  │ Memory    │  │ Web       │  │
│  │ Base      │  │ Store     │  │ Search    │  │
│  │ (Static)  │  │ (Dynamic) │  │ (Realtime)│  │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  │
│        │              │              │         │
│        └──────────────┼──────────────┘         │
│                       ▼                        │
│              ┌───────────────┐                 │
│              │ Context       │                 │
│              │ Assembler     │                 │
│              └───────┬───────┘                 │
│                      │                         │
│                      ▼                         │
│              ┌───────────────┐                 │
│              │ LLM (Claude)  │                 │
│              │ + System Prompt                 │
│              │ + Constitution│                 │
│              └───────┬───────┘                 │
│                      │                         │
│                      ▼                         │
│              ┌───────────────┐                 │
│              │ Response      │                 │
│              │ Filter        │                 │
│              └───────────────┘                 │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Components

1. **Knowledge Base (Static)**
   - 연예인 기본 정보 (생년월일, 경력, 성격)
   - 말투 패턴, 자주 쓰는 표현
   - Vector DB (pgvector)에 저장

2. **Memory Store (Dynamic)**
   - 사용자별 대화 기록
   - 관계 컨텍스트 (친밀도, 이전 대화 주제)
   - PostgreSQL + pgvector

3. **Web Search (Realtime)**
   - 최신 뉴스, 활동 정보
   - Tavily API
   - 캐싱으로 비용 최적화

4. **Constitution (Guard Rails)**
   - 캐릭터 이탈 방지 규칙
   - 민감한 주제 회피
   - 일관된 말투 유지

## Rationale
- **RAG**: 방대한 지식을 효율적으로 활용
- **Constitutional AI**: 페르소나 일탈 방지
- **Web Search**: 실시간성 확보 ("어제 뮤뱅 어땠어?" 대응)

## Alternatives Rejected
| Alternative | Rejection Reason |
|-------------|------------------|
| Fine-tuned Model | 비용, 업데이트 어려움 |
| Full Context (No RAG) | 토큰 비용, 컨텍스트 한계 |
| LangChain | 추상화 오버헤드, 디버깅 어려움 |

## Consequences
### Positive
- 실시간 정보 반영 가능
- 페르소나 일관성 유지
- 확장 가능한 구조

### Negative
- 복잡도 증가
- 여러 서비스 의존성

### Mitigation
- 캐싱으로 외부 API 의존도 감소
- 폴백 로직으로 장애 대응
