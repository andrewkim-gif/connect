# ADR-004: Live Photo Share with Gemini 3.1 Flash Image Preview

## Status
**Accepted**

## Context
사용자가 "지금 뭐해?", "어디야?" 같은 질문을 할 때,
연예인이 마치 실시간으로 사진을 찍어 보내는 듯한 경험을 제공하고 싶습니다.

### 요구사항
- 질문 의도 감지 → 상황에 맞는 이미지 생성
- 연예인의 현재 컨텍스트 반영 (시간, 스케줄, 최근 활동)
- 자연스러운 1인칭 시점 이미지
- 빠른 생성 속도 (< 3초)

## Decision
**Gemini 3.1 Flash Image Preview** (`gemini-3.1-flash-image-preview`)를 사용합니다.

### 모델 사양
```yaml
Model: gemini-3.1-flash-image-preview
Codename: Nano Banana 2
Input: Text + Image/PDF (131K tokens)
Output: Image + Text (32K tokens)

Supported_Resolutions:
  - 0.5K, 1K (default), 2K, 4K

Aspect_Ratios:
  - 1:1, 4:3, 3:4, 16:9, 9:16
  - NEW: 1:4, 4:1, 1:8, 8:1

Special_Features:
  - 이미지 검색 그라운딩 (웹 데이터 활용)
  - 다국어 텍스트 렌더링
  - 대화형 편집
```

### 구현 전략

#### 1. Intent Detection (의도 감지)
```python
TRIGGER_PATTERNS = [
    r"지금\s*(뭐|뭘)\s*(해|하고)",
    r"뭐\s*해\?",
    r"어디\s*(야|있어|에\s*있어)",
    r"뭐\s*하고\s*있어",
    r"지금\s*어디",
    r"사진\s*(보내|찍어|줘)",
]
```

#### 2. Context Builder (컨텍스트 구성)
```python
def build_image_context(celebrity_id: str) -> dict:
    return {
        "current_time": datetime.now(),
        "time_of_day": get_time_category(),  # 아침/낮/저녁/밤
        "schedule": get_celebrity_schedule(celebrity_id),
        "recent_activity": get_recent_sns_activity(celebrity_id),
        "persona": get_celebrity_persona(celebrity_id),
        "location_hints": infer_location(),
    }
```

#### 3. Image Prompt Template
```
[Celebrity Persona]: {name}의 시점에서 촬영한 셀카 또는 주변 사진

[Current Context]:
- 시간: {time} ({time_of_day})
- 활동: {activity}
- 장소: {location}

[Style Guidelines]:
- 1인칭 시점 (셀카 또는 내가 보는 풍경)
- 자연스러운 일상 느낌
- 얼굴은 포함하지 않음 (저작권 보호)
- 손, 팔, 주변 환경만 보여줌

[Output]:
{name}이(가) 지금 이 순간 찍어서 보낸 것 같은 사진
```

#### 4. Example Scenarios
| 시간 | 스케줄 | 생성 이미지 |
|------|--------|-------------|
| 오전 9시 | 없음 | 커피와 창문 밖 아침 풍경 |
| 오후 2시 | 녹음 | 녹음실 믹서, 마이크, 헤드폰 |
| 저녁 7시 | 없음 | 저녁 식사 준비 중인 주방 |
| 밤 11시 | 작업 | 어두운 작업실, 모니터 불빛 |
| 새벽 2시 | 없음 | 야경이 보이는 창가, 음료 |

## Alternatives Rejected

### DALL-E 3
- **장점**: 높은 품질
- **단점**: 느림 (10-15초), OpenAI 별도 계약
- **결론**: 실시간 대화에 부적합

### Midjourney
- **장점**: 최고 품질
- **단점**: API 없음, Discord 기반
- **결론**: 통합 불가능

### Stable Diffusion (Self-hosted)
- **장점**: 비용 효율, 커스터마이징
- **단점**: GPU 인프라 필요, 관리 부담
- **결론**: MVP에서는 과도한 복잡성

## Consequences

### Positive
- 혁신적인 사용자 경험 (차별화 포인트)
- Gemini 생태계 통합으로 일관된 API
- 웹 그라운딩으로 실시간성 강화

### Negative
- 이미지 생성 비용 추가
- 부적절한 이미지 생성 리스크
- 연예인 얼굴 생성 시 법적 이슈

### Mitigation
- 얼굴 제외 프롬프트로 저작권 보호
- Safety filter 활성화
- 생성 이미지 모니터링 시스템
- 사용량 제한 (일 N회)

## API Usage Example
```python
import google.generativeai as genai

model = genai.GenerativeModel("gemini-3.1-flash-image-preview")

response = model.generate_content(
    f"""
    Create an image from GD's perspective right now.

    Context:
    - Time: 3:00 PM
    - Activity: Recording session
    - Location: Recording studio

    Style: First-person view, casual selfie angle,
    showing recording equipment, hands on mixer,
    NO face visible, natural lighting.
    """,
    generation_config={
        "response_mime_type": "image/png",
        "image_resolution": "1k",
    }
)

# Response includes both image and optional text
image_data = response.candidates[0].content.parts[0].inline_data
text_caption = response.text  # "녹음 중이야~"
```

## Success Metrics
| Metric | Target |
|--------|--------|
| 이미지 생성 성공률 | > 95% |
| 생성 시간 | < 3초 |
| 사용자 만족도 | > 4.0/5 |
| Safety filter 트리거율 | < 1% |
