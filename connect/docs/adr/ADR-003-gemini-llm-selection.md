# ADR-003: Gemini 3.0 Flash as Primary Chat LLM

## Status
**Accepted**

## Context
StarCall 플랫폼의 채팅 기능에 사용할 LLM을 선정해야 합니다.
핵심 요구사항:
- 빠른 응답 속도 (< 2초)
- 한국어 품질
- 비용 효율성
- 페르소나 유지력

## Decision
**Gemini 3.0 Flash**를 채팅 LLM으로 채택합니다.

### 선정 근거

| 기준 | Gemini 3.0 Flash | Claude 3.5 Sonnet | GPT-4o |
|------|------------------|-------------------|--------|
| 응답 속도 | ⭐⭐⭐ 매우 빠름 | ⭐⭐ 보통 | ⭐⭐ 보통 |
| 한국어 품질 | ⭐⭐⭐ 우수 | ⭐⭐⭐ 우수 | ⭐⭐ 양호 |
| 비용 | ⭐⭐⭐ 저렴 | ⭐⭐ 중간 | ⭐ 비쌈 |
| 페르소나 | ⭐⭐ 양호 | ⭐⭐⭐ 우수 | ⭐⭐ 양호 |
| 이미지 통합 | ⭐⭐⭐ 네이티브 | ❌ 없음 | ⭐⭐ 별도 |

### API 사양
```yaml
Model: gemini-3.0-flash
Input_Tokens: 1M context window
Output_Tokens: 32K max
Multimodal: Text + Image input
Pricing: ~$0.075/1M input, ~$0.30/1M output
```

## Alternatives Rejected

### Claude 3.5 Sonnet
- **장점**: 페르소나 유지력 최고, 한국어 품질 우수
- **단점**: 비용 높음, 이미지 생성 통합 없음
- **결론**: 이미지 생성 기능과 통합 시너지 부족

### GPT-4o
- **장점**: DALL-E 통합 가능
- **단점**: 비용 높음, 한국어 상대적 약함
- **결론**: 비용 대비 효율 부족

### Gemini 1.5 Pro
- **장점**: 더 긴 컨텍스트
- **단점**: Flash 대비 느림, 비용 높음
- **결론**: 채팅 용도로는 Flash가 적합

## Consequences

### Positive
- 빠른 응답으로 대화 몰입감 향상
- 비용 효율적인 대규모 서비스 가능
- Gemini 이미지 모델과 일관된 생태계

### Negative
- Claude 대비 복잡한 지시 따르기 약간 부족
- 프롬프트 엔지니어링 추가 필요

### Mitigation
- Few-shot 예시로 페르소나 강화
- Constitutional AI 패턴으로 가드레일 설정
- 필요시 복잡한 시나리오만 Claude fallback
