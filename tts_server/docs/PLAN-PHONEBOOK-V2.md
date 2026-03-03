# 📞 Voice Call Phonebook V2 - 전화번호부 시스템 기획

> **목표**: 단일 캐릭터(GD)에서 멀티 캐릭터 시스템으로 확장
> **첫 화면**: 전화번호부 UI → 연락처 선택 → 해당 캐릭터 음성으로 통화

---

## 🎯 Overview

### 현재 상태 (V1)
- 단일 캐릭터: G-Dragon
- 단일 모델: Fine-tuned GD v5 + ICL Clone
- 단일 페르소나: GD 말투/성격

### 목표 상태 (V2)
- 멀티 캐릭터: G-Dragon, 장현국
- 각 캐릭터별 독립 모델/프롬프트
- 각 캐릭터별 고유 페르소나

---

## 👤 캐릭터 프로필

### 1. G-Dragon (기존)
```yaml
ID: gd
Name: G-Dragon (권지용)
Description: 빅뱅 리더, 아티스트
Persona:
  - 친근하고 쿨한 말투
  - "야~", "뭐야~", "오케이" 등 특유의 표현
  - 장난스럽고 솔직한 성격

Voice_Models:
  - finetuned: gd-voice-v5 (best quality)
  - icl: gd-clone (base model + ICL prompt)

Sample_Audio: sample/gd_sample_12s.wav
Status: ✅ Ready (Fine-tuned + ICL 완료)
```

### 2. 장현국 (신규)
```yaml
ID: jhk
Name: 장현국
Description: 위메이드 전 CEO, 게임 업계 기업인
Persona:
  - 비즈니스 톤, 논리적 화법
  - 게임/블록체인/경영 관련 전문 지식
  - 차분하고 신중한 어조
  - 위믹스, 미르4 등 위메이드 관련 대화 가능

Voice_Models:
  - finetuned: jhk-voice-v1 (TODO: 학습 예정)
  - icl: jhk-clone (base model + ICL prompt)

Sample_Audio: sample/jhk_sample_10s.wav (TODO: 수집 필요)
Status: ⏳ Pending (음성 수집 + 파인튜닝 예정)
```

---

## 📱 UI/UX 설계

### 첫 화면: 전화번호부 (Phonebook)

```
┌─────────────────────────────────────┐
│     📞 Voice Call                   │
│                                     │
│  ┌─────────────────────────────────┐│
│  │  연락처                          ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │  👤 G-Dragon                    ││
│  │  "야~ 뭐야?"                    ││
│  │  🟢 온라인                       ││
│  │                      [📞 전화]  ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │  👤 장현국                       ││
│  │  "네, 말씀하세요"               ││
│  │  🟢 온라인                       ││
│  │                      [📞 전화]  ││
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │  ➕ 연락처 추가 (Coming Soon)   ││
│  └─────────────────────────────────┘│
│                                     │
└─────────────────────────────────────┘
```

### 통화 화면 (기존 유지 + 캐릭터 정보 추가)

```
┌─────────────────────────────────────┐
│     📞 통화 중...                   │
│                                     │
│         ┌───────────┐               │
│         │   👤      │               │
│         │ G-Dragon  │               │
│         └───────────┘               │
│                                     │
│     [상태: 말하는 중...]            │
│                                     │
│         ┌───────────┐               │
│         │    🎤     │               │
│         └───────────┘               │
│                                     │
│  ┌─────────────────────────────────┐│
│  │ [대화 내용]                     ││
│  └─────────────────────────────────┘│
│                                     │
│    [🔴 종료]     [🔄 초기화]        │
│                                     │
└─────────────────────────────────────┘
```

---

## 🏗️ 시스템 아키텍처

### 데이터 구조

```python
# characters.py - 캐릭터 정의

@dataclass
class CharacterProfile:
    id: str                    # "gd", "jhk"
    name: str                  # "G-Dragon", "장현국"
    description: str           # 짧은 설명
    avatar: str                # 아바타 이미지 경로
    greeting_text: str         # 대표 인사말

    # 음성 모델
    voice_model_finetuned: Optional[str]  # 파인튜닝 모델 경로
    voice_model_icl: Optional[str]        # ICL 프롬프트 경로
    sample_audio: str                      # 샘플 오디오 경로
    ref_text: str                          # ICL용 참조 텍스트

    # LLM 페르소나
    system_prompt: str         # 캐릭터별 시스템 프롬프트
    greetings: List[str]       # 인사말 목록

    # 상태
    status: str               # "ready", "pending", "disabled"
```

### 캐릭터 레지스트리

```python
# character_registry.py

CHARACTERS = {
    "gd": CharacterProfile(
        id="gd",
        name="G-Dragon",
        description="빅뱅 리더, 아티스트",
        avatar="/static/avatars/gd.png",
        greeting_text="야~ 뭐야?",
        voice_model_finetuned="gd-voice-v5",
        voice_model_icl="gd-clone",
        sample_audio="sample/gd_sample_12s.wav",
        ref_text="저는 감내하고 있고 감내해야 될 부분이죠...",
        system_prompt=GD_SYSTEM_PROMPT,
        greetings=GD_GREETINGS,
        status="ready",
    ),
    "jhk": CharacterProfile(
        id="jhk",
        name="장현국",
        description="위메이드 전 CEO",
        avatar="/static/avatars/jhk.png",
        greeting_text="네, 말씀하세요",
        voice_model_finetuned=None,  # TODO
        voice_model_icl=None,         # TODO
        sample_audio="sample/jhk_sample_10s.wav",
        ref_text="",  # TODO
        system_prompt=JHK_SYSTEM_PROMPT,
        greetings=JHK_GREETINGS,
        status="pending",
    ),
}
```

### LLM 페르소나 (장현국)

```python
JHK_SYSTEM_PROMPT = """
너는 장현국이야. 위메이드 전 CEO이자 게임 업계 베테랑 기업인이야.

## 말투 특징
- 차분하고 논리적인 어조
- 비즈니스 용어를 자연스럽게 사용
- "네", "그렇습니다", "말씀하신 대로" 등 정중한 표현
- 하지만 친근한 대화에서는 편하게 말하기도 함

## 전문 분야
- 게임 산업 (MMORPG, 모바일 게임)
- 블록체인/가상자산 (위믹스, P2E)
- 경영 전략, 스타트업

## 대화 스타일
- 질문에 명확하고 체계적으로 답변
- 필요시 예시나 비유를 사용
- 복잡한 주제도 쉽게 설명하려고 노력

## 주의사항
- 실제 장현국 개인의 사적인 정보는 언급하지 않음
- 법적 이슈(위믹스 관련)에 대해서는 조심스럽게 답변
- 위메이드의 공식 입장이 아닌 개인 의견임을 명시
"""

JHK_GREETINGS = [
    "네, 말씀하세요.",
    "안녕하세요, 무슨 일이시죠?",
    "네, 듣고 있습니다.",
    "어떤 이야기를 나눠볼까요?",
    "반갑습니다. 무엇을 도와드릴까요?",
]
```

---

## 🔧 구현 계획

### Phase 1: 전화번호부 UI (Frontend)
```yaml
Tasks:
  1. 전화번호부 메인 화면 구현
     - 연락처 카드 컴포넌트
     - 캐릭터별 상태 표시 (온라인/오프라인/준비중)
     - 전화 걸기 버튼

  2. 기존 통화 화면 수정
     - 캐릭터 정보 헤더 추가
     - 뒤로가기 (전화번호부로)

Files:
  - static/phonebook.html (신규)
  - static/voice_call.html (수정)
```

### Phase 2: 백엔드 캐릭터 시스템
```yaml
Tasks:
  1. 캐릭터 레지스트리 구현
     - CharacterProfile 데이터클래스
     - 캐릭터 목록 API

  2. WebSocket 프로토콜 확장
     - start_call에 character_id 추가
     - 캐릭터별 greeting/voice 분기

  3. LLM 페르소나 시스템
     - 캐릭터별 system_prompt 관리
     - 동적 페르소나 전환

Files:
  - services/character_registry.py (신규)
  - api/routes/characters.py (신규)
  - api/websocket/voice_call.py (수정)
  - services/llm_engine.py (수정)
```

### Phase 3: 장현국 음성 모델 (별도 진행)
```yaml
Tasks:
  1. 샘플 음성 수집
     - 인터뷰, 발표 영상에서 추출
     - 최소 10초 이상 클린 오디오

  2. ICL 프롬프트 생성
     - ref_audio + ref_text 준비
     - voice_clone_prompt 캐싱

  3. (Optional) Fine-tuning
     - 충분한 데이터 확보 시
     - GD v5와 동일한 파이프라인

Status: ⏳ 사용자가 진행 예정
```

---

## 📡 API 설계

### REST API

```yaml
# GET /api/v1/characters
# 캐릭터 목록 조회
Response:
  characters:
    - id: "gd"
      name: "G-Dragon"
      description: "빅뱅 리더, 아티스트"
      avatar: "/static/avatars/gd.png"
      greeting_text: "야~ 뭐야?"
      status: "ready"
      voice_modes: ["finetuned", "icl"]
    - id: "jhk"
      name: "장현국"
      description: "위메이드 전 CEO"
      avatar: "/static/avatars/jhk.png"
      greeting_text: "네, 말씀하세요"
      status: "pending"
      voice_modes: []

# GET /api/v1/characters/{id}
# 특정 캐릭터 상세 정보
```

### WebSocket 프로토콜 확장

```yaml
# 기존
{ "type": "start_call", "voice_id": "gd-icl" }

# 확장 (V2)
{
  "type": "start_call",
  "character_id": "gd",      # 캐릭터 ID (필수)
  "voice_mode": "finetuned"  # "finetuned" | "icl" | "auto"
}

# 서버 응답
{
  "type": "call_started",
  "character": {
    "id": "gd",
    "name": "G-Dragon",
    "avatar": "/static/avatars/gd.png"
  },
  "voice_mode": "finetuned"
}
```

---

## 📁 파일 구조 (예상)

```
tts_server/
├── services/
│   ├── character_registry.py   # 캐릭터 레지스트리 (신규)
│   ├── llm_engine.py           # 페르소나 시스템 확장
│   └── ...
├── api/
│   ├── routes/
│   │   ├── characters.py       # 캐릭터 API (신규)
│   │   └── ...
│   └── websocket/
│       └── voice_call.py       # 캐릭터 분기 로직 추가
├── static/
│   ├── phonebook.html          # 전화번호부 UI (신규)
│   ├── voice_call.html         # 통화 UI (수정)
│   └── avatars/
│       ├── gd.png              # GD 아바타
│       └── jhk.png             # 장현국 아바타
├── data/
│   ├── prompts/
│   │   ├── gd-clone.pkl        # GD ICL 프롬프트
│   │   └── jhk-clone.pkl       # 장현국 ICL 프롬프트 (TODO)
│   └── personas/
│       ├── gd_persona.py       # GD 페르소나
│       └── jhk_persona.py      # 장현국 페르소나 (신규)
└── sample/
    ├── gd_sample_12s.wav       # GD 샘플
    └── jhk_sample_10s.wav      # 장현국 샘플 (TODO)
```

---

## 🚀 우선순위 및 일정

| Phase | Task | 예상 시간 | 의존성 |
|-------|------|----------|--------|
| 1-1 | 전화번호부 UI (phonebook.html) | 2-3시간 | 없음 |
| 1-2 | 통화 화면 캐릭터 정보 추가 | 1시간 | 1-1 |
| 2-1 | CharacterRegistry 구현 | 1-2시간 | 없음 |
| 2-2 | Characters API 구현 | 1시간 | 2-1 |
| 2-3 | WebSocket 캐릭터 분기 | 2시간 | 2-1 |
| 2-4 | LLM 페르소나 시스템 | 1-2시간 | 2-1 |
| 3-1 | 장현국 샘플 음성 수집 | 사용자 | 없음 |
| 3-2 | 장현국 ICL 프롬프트 | 30분 | 3-1 |
| 3-3 | 장현국 Fine-tuning | 수 시간 | 3-1 |

---

## ⚠️ 리스크 및 고려사항

### 기술적 리스크
1. **멀티 모델 메모리**: 두 캐릭터 모델 동시 로딩 시 VRAM 부족 가능
   - 해결: Lazy loading 또는 모델 스왑 구현

2. **음성 품질**: 장현국 샘플 품질에 따라 ICL 결과 차이
   - 해결: 충분한 길이(10초+)의 클린 오디오 확보

### 법적/윤리적 고려
1. **초상권/음성권**: 실제 인물의 음성 복제
   - 해결: 개인 사용 목적 명시, 상업적 사용 불가 고지

2. **딥페이크 우려**: 악용 가능성
   - 해결: 워터마킹, 사용 로깅

---

## ✅ 다음 단계

1. **사용자 액션**: 장현국 샘플 음성 수집 (인터뷰/발표 영상)
2. **구현 시작**: Phase 1 (전화번호부 UI) 먼저 진행
3. **병렬 진행**: 장현국 음성 파인튜닝은 사용자가 별도 진행

---

*Generated: 2026-03-03*
*Author: Claude (/da:plan)*
