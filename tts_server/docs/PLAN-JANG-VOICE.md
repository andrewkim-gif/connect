# 장(Jang) 음성 TTS 튜닝 및 ICL 적용 기획

**작성일**: 2026-03-03
**버전**: v1.0
**상태**: Draft → 승인 대기

---

## 1. Executive Summary

기존 GD 음성 모델 튜닝 파이프라인을 참조하여 장현국(JHK) 캐릭터의 음성 TTS를 구현합니다.

### 목표
- **Fine-tuned 모델**: 장 음성 전용 Qwen3-TTS 파인튜닝 (93%+ 유사도)
- **ICL 모드**: 즉시 사용 가능한 In-Context Learning 음성 복제
- **tts_test_app 통합**: 캐릭터 선택 UI에서 장 음성 지원

### 소스 데이터
| 항목 | 값 |
|------|-----|
| **파일** | `sample/sample_jang/sample_jang_00.wav` |
| **길이** | 1,761초 (29.4분) |
| **포맷** | WAV, 16-bit PCM, Stereo, 44.1kHz |
| **특징** | GD 데이터(18.8분)보다 1.6배 많은 원본 데이터 |

---

## 2. 기존 GD 파이프라인 분석 (참조)

### 2.1 GD v5 프로덕션 모델 성과

```yaml
훈련_설정:
  모델: Qwen3-TTS-12Hz-1.7B-Base
  데이터: 18.8분 (90개 샘플)
  에폭: 150
  Learning_Rate: 5e-7
  증강: 없음 (원본만)

결과:
  최종_Loss: 9.38
  음성_유사도: 93.9%
  추론_속도: RTF 0.65
  GPU_메모리: 3.89GB
```

### 2.2 핵심 학습 포인트
1. **데이터 품질 > 양**: 깨끗한 음성 18.8분으로 충분
2. **증강 제거**: 원본만 사용 시 음색 보존 우수
3. **Loss ≠ 품질**: 낮은 Loss가 좋은 음성 아님
4. **150 에폭 최적**: 100 이후 큰 변화 없음
5. **LR 5e-7 안정적**: 음성 도메인 최적값

---

## 3. 장 음성 튜닝 기획

### 3.1 데이터 전처리 파이프라인

```
[Phase 1: 데이터 준비]
┌─────────────────────────────────────────────────────────────┐
│ sample_jang_00.wav (1,761s, 29.4분)                         │
│ ↓                                                           │
│ [1] Mono + 리샘플링 (44.1kHz stereo → 24kHz mono)           │
│ ↓                                                           │
│ [2] 무음 기반 청크 분할 (3-12초 단위)                        │
│ ↓                                                           │
│ [3] Whisper large-v3 한국어 전사                             │
│ ↓                                                           │
│ [4] Audio codes 토큰화 (Qwen3-TTS-Tokenizer-12Hz)           │
│ ↓                                                           │
│ [5] Train/Val 분할 (9:1)                                    │
│ ↓                                                           │
│ data_jang/                                                  │
│ ├── chunks/         (예상 ~150개 청크)                      │
│ ├── jang_train.jsonl                                        │
│ ├── jang_val.jsonl                                          │
│ └── dataset_stats.json                                      │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 예상 데이터 규모

| 항목 | GD (참조) | 장 (예상) | 비교 |
|------|-----------|-----------|------|
| 원본 길이 | 1,130초 | 1,761초 | +55% |
| 청크 수 | 99개 | ~150개 | +50% |
| 훈련 샘플 | 90개 | ~135개 | +50% |
| 검증 샘플 | 9개 | ~15개 | +67% |

### 3.3 훈련 설정 (v1 기준)

```yaml
# 장 음성 튜닝 v1 - GD v5 설정 그대로 적용
jang_v1_config:
  base_model: "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
  output_dir: "finetune/models/jang-voice-v1"
  epochs: 150
  learning_rate: 5e-7
  batch_size: 1
  gradient_accumulation_steps: 4
  lr_scheduler: "cosine"
  warmup_ratio: 0.1
  fp16: true
  data_augmentation: false  # 원본만 사용

# 데이터셋
dataset:
  train: "finetune/data_jang/jang_train.jsonl"
  val: "finetune/data_jang/jang_val.jsonl"
  speaker_id: "jang"
```

### 3.4 훈련 단계

```
[Phase 2: 모델 훈련]
┌─────────────────────────────────────────────────────────────┐
│ [1] v1 초기 훈련                                            │
│     - GD v5 설정 그대로 적용                                 │
│     - 목표: Loss < 10.0, 청취 테스트 통과                    │
│                                                             │
│ [2] 평가                                                    │
│     - 음성 유사도 분석 (MFCC, Pitch, Spectral)              │
│     - 새로운 문장에서 자연스러움 테스트                       │
│                                                             │
│ [3] 반복 (필요시)                                           │
│     - v2: LR 조정, 에폭 조정                                │
│     - v3: 데이터 정제, 특정 샘플 제외                        │
└─────────────────────────────────────────────────────────────┘
```

### 3.5 성공 기준

| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| **음성 유사도** | ≥ 90% | MFCC + Pitch + Spectral 가중 평균 |
| **Loss** | < 10.0 | 훈련 종료 시점 |
| **자연스러움** | 청취 통과 | 새 문장 10개 테스트 |
| **RTF** | < 1.0 | 실시간 추론 가능 |

---

## 4. ICL (In-Context Learning) 적용 기획

### 4.1 ICL 모드 개요

Fine-tuning 없이 Base 모델로 즉시 음성 복제 가능한 모드입니다.
훈련 완료 전 또는 백업 용도로 사용합니다.

```
[ICL 방식 음성 복제]
┌─────────────────────────────────────────────────────────────┐
│ [1] Reference Audio 선택                                    │
│     - 12~18초 길이의 깨끗한 샘플                             │
│     - 완전한 문장 포함 (자연스러운 억양)                      │
│                                                             │
│ [2] Voice Clone Prompt 생성                                 │
│     - model.create_voice_clone_prompt(ref_audio, ref_text)  │
│     - 캐시: data/prompts/jang-clone.pkl                     │
│                                                             │
│ [3] 실시간 합성                                             │
│     - model.generate_voice_clone(text, voice_clone_prompt)  │
│     - 새로운 텍스트에 대해 즉시 합성                         │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Reference Audio 선택 기준

| 조건 | 설명 |
|------|------|
| **길이** | 12~18초 (너무 짧으면 음색 학습 부족) |
| **품질** | 배경 소음 최소, 명료한 발화 |
| **내용** | 완전한 문장 2~3개 포함 |
| **억양** | 일반적인 대화 톤 (감정 과잉 X) |

### 4.3 샘플 추출 계획

```bash
# 원본에서 최적 구간 탐색 (수동 또는 자동)
# 1. 전체 청크 분할 후 가장 품질 좋은 청크 선택
# 2. 12-18초 길이, 명료한 발화 구간

# 예상 출력
sample/jang_sample_15s.wav  # ICL용 reference audio
```

### 4.4 ICL Prompt 캐싱

```python
# GD 방식과 동일하게 적용
JANG_ICL_CONFIG = {
    "voice_id": "jang-clone",
    "name": "장현국 (ICL)",
    "mode": "icl",
    "sample_path": "sample/jang_sample_15s.wav",
    "ref_text": "[청취 후 전사 텍스트]",
    "cache_path": "tts_server/data/prompts/jang-clone.pkl"
}
```

---

## 5. 서버 통합 기획

### 5.1 Character Registry 업데이트

현재 상태:
```python
# character_registry.py에 이미 등록됨
CharacterProfile(
    id="jhk",
    name="장현국",
    status="pending",  # ← 음성 모델 없음
    voice_model_finetuned=None,
    voice_model_icl=None,
)
```

목표 상태:
```python
CharacterProfile(
    id="jhk",
    name="장현국",
    status="ready",  # ← 활성화
    voice_model_finetuned="jang-voice-v1",  # Fine-tuned 모델
    voice_model_icl="jang-clone",            # ICL 프롬프트
    sample_audio="sample/jang_sample_15s.wav",
    ref_text="[전사 텍스트]",
)
```

### 5.2 Config 추가 사항

```python
# config.py 추가 예정
JANG_FINETUNED_MODEL_PATH: str = "finetune/models/jang-voice-v1/checkpoint-epoch-final"
JANG_SPEAKER: str = "jang"
JANG_SAMPLE_PATH: str = "sample/jang_sample_15s.wav"
```

### 5.3 Voice Manager 등록

```python
# 서버 시작 시 자동 등록
voice_manager.register_voice(
    voice_id="jang-clone",
    name="장현국 (ICL)",
    mode="icl",
    sample_path=settings.JANG_SAMPLE_PATH,
    ref_text="[전사 텍스트]",
)
```

### 5.4 TTS Engine 확장

```python
# 멀티 캐릭터 지원을 위한 model_manager 확장
# 캐릭터별 Fine-tuned 모델 로드 지원

# Option A: 단일 GPU에서 모델 스왑 (메모리 효율)
# Option B: 다중 모델 동시 로드 (응답 속도)

# 권장: Option A (GPU 메모리 3.89GB × 2 = 7.78GB 필요)
```

---

## 6. tts_test_app 통합

### 6.1 VoiceId 타입 확장

```typescript
// types/call.ts
export type VoiceId =
  | 'gd-default'
  | 'gd-icl'
  | 'jang-default'  // NEW: 장 Fine-tuned
  | 'jang-icl'      // NEW: 장 ICL
  | 'openai-alloy'
  // ...
```

### 6.2 캐릭터 선택 UI

현재 PhonebookScreen에서 캐릭터 목록을 서버 API로 가져옵니다.
장 캐릭터의 `status`가 `"ready"`가 되면 자동으로 선택 가능해집니다.

```typescript
// 서버 응답 예시
{
  "characters": [
    { "id": "gd", "name": "G-Dragon", "status": "ready", ... },
    { "id": "jhk", "name": "장현국", "status": "ready", ... }  // NEW
  ]
}
```

---

## 7. 산출물 목록

### Phase 1: 데이터 준비
| 산출물 | 경로 |
|--------|------|
| 데이터 전처리 스크립트 | `finetune/scripts/prepare_jang_dataset.py` |
| 청크 데이터 | `finetune/data_jang/chunks/` |
| 훈련 데이터 | `finetune/data_jang/jang_train.jsonl` |
| 검증 데이터 | `finetune/data_jang/jang_val.jsonl` |
| 통계 | `finetune/data_jang/dataset_stats.json` |

### Phase 2: ICL 적용
| 산출물 | 경로 |
|--------|------|
| Reference Audio | `sample/jang_sample_15s.wav` |
| ICL Prompt 캐시 | `tts_server/data/prompts/jang-clone.pkl` |

### Phase 3: Fine-tuning
| 산출물 | 경로 |
|--------|------|
| 훈련 스크립트 | `finetune/scripts/train_jang_v1.py` |
| 모델 체크포인트 | `finetune/models/jang-voice-v1/` |
| 훈련 로그 | `finetune/logs/train_jang_v1.log` |

### Phase 4: 서버 통합
| 산출물 | 경로 |
|--------|------|
| Config 업데이트 | `tts_server/config.py` |
| Character Registry | `tts_server/services/character_registry.py` |
| 페르소나 | `tts_server/data/personas/jhk_persona.py` (기존) |

---

## 8. 일정 (예상)

| 단계 | 작업 | 소요 시간 |
|------|------|----------|
| **Phase 1** | 데이터 전처리 | 1시간 |
| **Phase 2** | ICL 샘플 추출 + 프롬프트 생성 | 30분 |
| **Phase 3** | Fine-tuning v1 훈련 | 20~30분 (GPU) |
| **Phase 4** | 서버 통합 + 테스트 | 1시간 |
| **총계** | | ~3시간 |

---

## 9. 리스크 및 완화 전략

| 리스크 | 가능성 | 영향 | 완화 전략 |
|--------|--------|------|----------|
| 음성 품질 부족 | 중 | 높음 | 데이터 정제, 추가 샘플 수집 |
| 과적합 | 중 | 중 | 150 에폭 제한, 검증 Loss 모니터링 |
| GPU 메모리 부족 (듀얼 모델) | 낮음 | 중 | 모델 스왑 방식 채택 |
| 원본 음질 이슈 | 낮음 | 중 | 전처리 시 노이즈 필터링 |

---

## 10. 다음 단계

**승인 후 진행:**
1. `/da:system` - 상세 시스템 설계 (선택적)
2. `/da:dev` - 구현 시작

**즉시 실행 가능 작업:**
1. `prepare_jang_dataset.py` 스크립트 작성
2. 데이터 전처리 실행
3. ICL 샘플 추출

---

## 부록: 참조 파일

```
기존 GD 파이프라인:
- finetune/scripts/prepare_v5_no_augment.py (데이터 전처리)
- finetune/Qwen3-TTS/finetuning/sft_12hz.py (훈련)
- tts_server/docs/GD_Voice_Training_Report.md (분석 보고서)
- tts_server/services/character_registry.py (캐릭터 관리)
- tts_server/services/voice_manager.py (음성 프롬프트)
- tts_server/services/tts_engine.py (합성 엔진)
```
