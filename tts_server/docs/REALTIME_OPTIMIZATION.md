# 실시간 음성 통화 최적화 가이드

## 현재 성능 (2024-02-28)

| 단계 | 지연시간 | 비중 |
|------|---------|------|
| STT (faster-whisper) | ~200ms | 2% |
| LLM TTFA (Gemini) | ~1,300ms | 13% |
| **TTS TTFA (Davinci Voice)** | **~3,000ms** | **30%** |
| 전체 처리 시간 | ~10,500ms | 100% |

## 적용된 최적화

### 1. 스트리밍 파이프라인 (voice_pipeline_streaming.py)

**기존 방식:**
```
STT → LLM (전체) → TTS (전체) → 오디오 전송
                                   ↑
                            첫 오디오까지 11초
```

**최적화 방식:**
```
STT → LLM (스트리밍) → 청크 분할 → TTS (병렬) → 오디오 스트리밍
       ↓                              ↓
    즉시 전송                     첫 청크 완료 시 전송
                                       ↑
                               첫 오디오까지 3초
```

### 2. 절(clause) 단위 청킹

```python
# 문장 종결뿐 아니라 쉼표/세미콜론에서도 분할
CLAUSE_PATTERN = r'([^,，.。!！?？;；:：~]+[,，.。!！?？;；:：~]?)'

# 청크 길이 제한
MIN_CHUNK_LENGTH = 5   # 너무 짧으면 품질 저하
MAX_CHUNK_LENGTH = 30  # 너무 길면 지연 증가
```

### 3. 병렬 TTS 처리

```python
# 동시에 여러 청크 TTS 처리 (GPU 메모리 주의)
MAX_CONCURRENT_TTS = 3

# asyncio.Semaphore로 동시성 제한
async with self._tts_semaphore:
    audio, sample_rate, tts_ms = await tts_engine.synthesize(...)
```

---

## 환경 변수 설정

```bash
# .env 파일
TTS_VOICE_PIPELINE_STREAMING=true      # 스트리밍 모드 활성화
TTS_VOICE_PIPELINE_MAX_CONCURRENT_TTS=3  # 동시 TTS 수
TTS_VOICE_PIPELINE_MIN_CHUNK_LENGTH=5    # 최소 청크 길이
TTS_VOICE_PIPELINE_MAX_CHUNK_LENGTH=30   # 최대 청크 길이
```

---

## 추가 최적화 방안

### 즉시 적용 가능

1. **LLM 응답 길이 제한**
   ```python
   GEMINI_MAX_TOKENS = 150  # 더 짧은 응답
   ```

2. **TTS 온도 낮추기** (생성 속도 약간 향상)
   ```python
   GEN_TEMPERATURE = 0.5  # 기본 0.7
   GEN_TOP_K = 30         # 기본 50
   ```

3. **더 작은 청크**
   ```python
   MIN_CHUNK_LENGTH = 3
   MAX_CHUNK_LENGTH = 20
   ```

### 하드웨어 업그레이드

1. **더 빠른 GPU**
   - RTX 4090: ~2배 빠른 TTS
   - A100: ~3배 빠른 TTS

2. **다중 GPU**
   - TTS 요청을 여러 GPU에 분산

### 모델 최적화

1. **더 작은 TTS 모델**
   - `Davinci Voice-12Hz-0.6B-Base` (1.7B → 0.6B)
   - 속도 2배, 품질 약간 저하

2. **양자화 (Quantization)**
   - INT8 양자화로 속도 향상
   - bitsandbytes 라이브러리 사용

### 아키텍처 변경

1. **TTS 서버 분리**
   - 별도 TTS 서버에서 처리
   - 로드 밸런싱으로 확장

2. **캐싱**
   - 자주 사용되는 응답 캐싱
   - Redis 기반 오디오 캐시

---

## 성능 목표

| 시나리오 | 현재 | 목표 |
|---------|------|------|
| 첫 음성까지 (TTFA) | 3초 | 1.5초 |
| 전체 처리 시간 | 10초 | 5초 |
| 동시 사용자 | 2-3명 | 10명 |

---

## 모니터링

```python
# 메트릭 예시
{
    "stt_ms": 211,
    "llm_ttfa_ms": 1336,
    "tts_ttfa_ms": 2974,
    "total_ms": 10437,
    "audio_duration": 14.08,
    "chunk_count": 6
}
```

---

## 트러블슈팅

### CUDA OOM (Out of Memory)

```bash
# 동시 TTS 수 줄이기
TTS_VOICE_PIPELINE_MAX_CONCURRENT_TTS=1
```

### 첫 음성이 너무 느림

1. 청크 길이 확인 (MIN_CHUNK_LENGTH 줄이기)
2. LLM 응답 속도 확인 (LLM TTFA)
3. GPU 사용률 확인 (nvidia-smi)

### 음성 품질 저하

1. 청크가 너무 짧으면 문맥 부족
2. MIN_CHUNK_LENGTH를 8-10으로 증가
