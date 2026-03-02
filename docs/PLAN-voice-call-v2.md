# GD Voice Call 2.0 - 자연스러운 대화 시스템

## 구현 상태

| # | 기능 | 상태 |
|---|------|------|
| 1 | 텍스트 끊김 (청크별 덮어쓰기) | ✅ 완료 |
| 2 | "인식된 음성이 없습니다" 오류 | ✅ 완료 |
| 3 | 노이즈로 인한 무한 녹음 | ✅ 완료 |
| 4 | **끼어들기(Barge-in)** | ✅ 완료 |
| 5 | **GD 주도 대화** | ✅ 완료 |

---

## Phase 1: 기본 수정 (✅ 완료)

### 1.1 텍스트 누적 표시
- `showTranscript(text, type, append)` - append 파라미터 추가
- `currentAIText` 변수로 AI 응답 누적
- `response_start`에서 `resetAITranscript()` 호출

### 1.2 노이즈 vs 음성 구분
```javascript
// 2단계 레벨 감지
if (average >= VOICE_THRESHOLD) {  // 12 이상 = 음성
    lastSoundTime = Date.now();
    hasVoiceActivity = true;
} else {
    // 침묵 + 노이즈 모두 타이머 진행 (리셋 안함!)
}
```

---

## Phase 2: Barge-in (끼어들기) (✅ 완료)

### 2.1 동작 방식
1. GD가 말하는 중 (`isGDSpeaking = true`)
2. 별도 마이크 스트림으로 사용자 음성 감지
3. 300ms 이상 음성 감지 시 끼어들기 실행
4. 서버에 `interrupt` 메시지 전송
5. 오디오 재생 중단, 사용자 발화 녹음 시작

### 2.2 클라이언트 설정
```javascript
BARGE_IN_ENABLED: true,
BARGE_IN_THRESHOLD: 15,    // 끼어들기 감지 임계값
BARGE_IN_DURATION: 300,    // 300ms 이상 음성 감지 시
```

### 2.3 서버 처리
```python
# Barge-in인 경우 LLM 컨텍스트에 기록
if reason == "barge_in":
    llm_engine.add_system_context(
        session_id=client_id,
        context="[유저가 끼어들어서 내 말을 끊었습니다. 자연스럽게 대화를 이어가세요.]"
    )
```

---

## Phase 3: GD 주도 대화 (✅ 완료)

### 3.1 동작 방식
1. 마지막 사용자 상호작용 후 5초 타이머 시작
2. 타이머 만료 시 `gd_initiative` 메시지 전송
3. 서버가 GD 발화 생성 (LLM + TTS)
4. GD가 먼저 말 걸기

### 3.2 클라이언트 설정
```javascript
GD_INITIATIVE_ENABLED: true,
GD_INITIATIVE_TIMEOUT: 5000,  // 5초 침묵 후 GD가 먼저 말걸기
```

### 3.3 서버 프롬프트
```python
gd_prompts = [
    "[유저가 5초간 아무 말도 안 합니다. 자연스럽게 대화를 이끌어가세요.]",
    "[유저가 말이 없네요. 궁금한 거 있으면 물어보라고 하거나...]",
]
```

---

## 프로토콜 정리

### 기존 메시지
```yaml
Client → Server:
  - voice_input: 음성 전송
  - reset: 대화 초기화
  - greeting: 인사말 요청
  - ping: 연결 유지

Server → Client:
  - connected: 연결 확인
  - transcription: STT 결과
  - response_start/text/end: LLM 응답
  - [Binary]: TTS 오디오
  - pong: 핑 응답
```

### 새 메시지 (v2.0)
```yaml
Client → Server:
  - interrupt: 끼어들기 (reason: "barge_in" | "manual")
  - gd_initiative: GD 먼저 말걸기 요청

Server → Client:
  - interrupted: 끼어들기 확인 (reason 포함)
```

---

## 테스트 체크리스트

- [x] 텍스트가 전체로 표시되는지
- [x] GD 말하는 중 녹음 안 되는지
- [x] 노이즈로 무한 녹음 안 되는지
- [ ] 끼어들기 시 GD가 멈추는지 (테스트 필요)
- [ ] 5초 침묵 시 GD가 먼저 말하는지 (테스트 필요)
- [ ] 대화 맥락이 유지되는지

---

## 파일 변경 목록

### 클라이언트
- `tts_test_app/index.html`
  - CONFIG: BARGE_IN_*, GD_INITIATIVE_* 설정 추가
  - 상태 변수: bargeIn*, gdInitiative* 추가
  - `startBargeInDetection()`: 끼어들기 감지 시작
  - `detectBargeIn()`: 끼어들기 음성 감지
  - `executeBargeIn()`: 끼어들기 실행
  - `resetGDInitiativeTimer()`: GD Initiative 타이머 관리
  - `triggerGDInitiative()`: GD 먼저 말걸기 트리거

### 서버
- `api/websocket/voice_call.py`
  - `interrupt` 메시지에 reason 파라미터 추가
  - `gd_initiative` 메시지 처리 추가

- `services/llm_engine.py`
  - `add_system_context()`: 세션에 컨텍스트 추가

- `services/voice_pipeline_streaming.py`
  - `process_text()`: 텍스트 입력 처리 (GD Initiative용)
