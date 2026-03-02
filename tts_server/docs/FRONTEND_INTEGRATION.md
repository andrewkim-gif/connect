# GD Voice Call 프론트엔드 연동 가이드

## 성능 특성

| 메트릭 | 값 | 설명 |
|--------|-----|------|
| **TTFA** | ~3초 | 첫 음성까지 걸리는 시간 |
| STT | ~200ms | 음성 인식 |
| LLM | ~1.3초 | 응답 생성 시작 |
| 오디오 길이 | 10-15초 | 일반적인 응답 |

---

## 서버 URL

```javascript
// 프로덕션 (외부 접속)
const WS_URL = 'wss://crossconnect.ngrok.app/ws/voice/call';

// 로컬 개발
// const WS_URL = 'ws://localhost:5002/ws/voice/call';
```

---

## 빠른 시작

### 1. WebSocket 연결

```javascript
const WS_URL = 'wss://crossconnect.ngrok.app/ws/voice/call';
const ws = new WebSocket(WS_URL);

ws.onopen = () => {
  console.log('연결됨');
};

ws.onmessage = (event) => {
  if (event.data instanceof Blob) {
    // 바이너리 = TTS 오디오
    handleAudioChunk(event.data);
  } else {
    // JSON 메시지
    const data = JSON.parse(event.data);
    handleMessage(data);
  }
};

ws.onerror = (error) => {
  console.error('WebSocket 에러:', error);
};

ws.onclose = (event) => {
  console.log('연결 종료:', event.code);
};
```

### 2. 메시지 처리

```javascript
function handleMessage(data) {
  switch (data.type) {
    case 'connected':
      // 연결 성공
      console.log('Client ID:', data.client_id);
      console.log('입력 샘플레이트:', data.sample_rate_in);  // 16000
      console.log('출력 샘플레이트:', data.sample_rate_out); // 24000
      break;

    case 'transcription':
      // STT 결과 (사용자 음성 → 텍스트)
      console.log('인식된 텍스트:', data.text);
      displayUserMessage(data.text);
      break;

    case 'response_start':
      // GD 응답 시작
      startResponseUI();
      break;

    case 'response_text':
      // GD 응답 텍스트 (스트리밍)
      appendResponseText(data.text);
      break;

    case 'response_end':
      // 응답 완료
      console.log('처리 시간:', data.metrics.total_ms, 'ms');
      console.log('전체 응답:', data.metrics.response_text);
      finishResponseUI();
      break;

    case 'error':
      console.error('에러:', data.code, data.message);
      showError(data.message);
      break;

    case 'pong':
      // 핑 응답
      break;
  }
}
```

---

## 마이크 녹음 및 전송

### 녹음 설정 (16kHz, 16-bit, Mono)

```javascript
class VoiceRecorder {
  constructor() {
    this.mediaRecorder = null;
    this.audioContext = null;
    this.stream = null;
  }

  async start() {
    // 마이크 권한 요청
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      }
    });

    // AudioContext로 16kHz 리샘플링
    this.audioContext = new AudioContext({ sampleRate: 16000 });
    const source = this.audioContext.createMediaStreamSource(this.stream);

    // ScriptProcessor로 PCM 데이터 추출
    const processor = this.audioContext.createScriptProcessor(4096, 1, 1);
    this.chunks = [];

    processor.onaudioprocess = (e) => {
      const inputData = e.inputBuffer.getChannelData(0);
      // Float32 → Int16 변환
      const pcm16 = new Int16Array(inputData.length);
      for (let i = 0; i < inputData.length; i++) {
        pcm16[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
      }
      this.chunks.push(pcm16);
    };

    source.connect(processor);
    processor.connect(this.audioContext.destination);
  }

  stop() {
    // 녹음 중지
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
    }
    if (this.audioContext) {
      this.audioContext.close();
    }

    // PCM 데이터 합치기
    const totalLength = this.chunks.reduce((acc, chunk) => acc + chunk.length, 0);
    const pcmData = new Int16Array(totalLength);
    let offset = 0;
    for (const chunk of this.chunks) {
      pcmData.set(chunk, offset);
      offset += chunk.length;
    }

    return pcmData.buffer;
  }
}
```

### 음성 전송

```javascript
async function sendVoice(pcmArrayBuffer) {
  // ArrayBuffer → Base64
  const base64 = arrayBufferToBase64(pcmArrayBuffer);

  ws.send(JSON.stringify({
    type: 'voice_input',
    audio: base64,
    voice_id: 'gd-icl'  // 또는 'gd-default'
  }));
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}
```

---

## TTS 오디오 재생

### AudioContext로 재생

```javascript
class AudioPlayer {
  constructor(sampleRate = 24000) {
    this.sampleRate = sampleRate;
    this.audioContext = new AudioContext({ sampleRate });
    this.queue = [];
    this.isPlaying = false;
  }

  // 바이너리 청크 추가
  addChunk(blob) {
    blob.arrayBuffer().then(buffer => {
      this.queue.push(buffer);
      if (!this.isPlaying) {
        this.playNext();
      }
    });
  }

  async playNext() {
    if (this.queue.length === 0) {
      this.isPlaying = false;
      return;
    }

    this.isPlaying = true;
    const buffer = this.queue.shift();

    // PCM Int16 → Float32
    const pcm16 = new Int16Array(buffer);
    const float32 = new Float32Array(pcm16.length);
    for (let i = 0; i < pcm16.length; i++) {
      float32[i] = pcm16[i] / 32768;
    }

    // AudioBuffer 생성
    const audioBuffer = this.audioContext.createBuffer(1, float32.length, this.sampleRate);
    audioBuffer.getChannelData(0).set(float32);

    // 재생
    const source = this.audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(this.audioContext.destination);
    source.onended = () => this.playNext();
    source.start();
  }

  stop() {
    this.queue = [];
    this.isPlaying = false;
  }
}

// 사용
const player = new AudioPlayer(24000);

function handleAudioChunk(blob) {
  player.addChunk(blob);
}
```

---

## 전체 예제 (React)

```jsx
import { useState, useRef, useEffect, useCallback } from 'react';

export function VoiceChat() {
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [messages, setMessages] = useState([]);
  const [currentResponse, setCurrentResponse] = useState('');

  const wsRef = useRef(null);
  const recorderRef = useRef(null);
  const playerRef = useRef(null);

  // WebSocket 연결
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:5002/ws/voice/call');

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);

    ws.onmessage = (event) => {
      if (event.data instanceof Blob) {
        playerRef.current?.addChunk(event.data);
      } else {
        const data = JSON.parse(event.data);
        handleMessage(data);
      }
    };

    wsRef.current = ws;
    playerRef.current = new AudioPlayer(24000);

    return () => ws.close();
  }, []);

  const handleMessage = useCallback((data) => {
    switch (data.type) {
      case 'transcription':
        setMessages(prev => [...prev, { role: 'user', text: data.text }]);
        break;
      case 'response_text':
        setCurrentResponse(prev => prev + data.text);
        break;
      case 'response_end':
        setMessages(prev => [...prev, {
          role: 'gd',
          text: data.metrics.response_text
        }]);
        setCurrentResponse('');
        break;
      case 'error':
        console.error(data.message);
        break;
    }
  }, []);

  // 녹음 시작
  const startRecording = async () => {
    recorderRef.current = new VoiceRecorder();
    await recorderRef.current.start();
    setIsRecording(true);
  };

  // 녹음 중지 및 전송
  const stopRecording = () => {
    const pcmData = recorderRef.current.stop();
    setIsRecording(false);

    // 전송
    const base64 = arrayBufferToBase64(pcmData);
    wsRef.current?.send(JSON.stringify({
      type: 'voice_input',
      audio: base64,
      voice_id: 'gd-icl'
    }));
  };

  return (
    <div className="voice-chat">
      <div className="status">
        {isConnected ? '🟢 연결됨' : '🔴 연결 안됨'}
      </div>

      <div className="messages">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <strong>{msg.role === 'user' ? '나' : 'GD'}:</strong>
            <p>{msg.text}</p>
          </div>
        ))}
        {currentResponse && (
          <div className="message gd typing">
            <strong>GD:</strong>
            <p>{currentResponse}</p>
          </div>
        )}
      </div>

      <button
        className={`record-btn ${isRecording ? 'recording' : ''}`}
        onMouseDown={startRecording}
        onMouseUp={stopRecording}
        onTouchStart={startRecording}
        onTouchEnd={stopRecording}
        disabled={!isConnected}
      >
        {isRecording ? '🎙️ 녹음 중...' : '🎤 눌러서 말하기'}
      </button>
    </div>
  );
}
```

---

## 유틸리티 함수

### Push-to-Talk 버튼

```javascript
// 버튼을 누르고 있는 동안만 녹음
<button
  onMouseDown={startRecording}
  onMouseUp={stopRecording}
  onMouseLeave={stopRecording}  // 버튼 밖으로 나가면 중지
  onTouchStart={startRecording}
  onTouchEnd={stopRecording}
>
  🎤 눌러서 말하기
</button>
```

### 연결 상태 유지 (Ping)

```javascript
// 30초마다 ping 전송
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'ping' }));
  }
}, 30000);
```

### 대화 초기화

```javascript
function resetConversation() {
  ws.send(JSON.stringify({ type: 'reset' }));
  setMessages([]);
}
```

### 응답 중단

```javascript
function interruptResponse() {
  ws.send(JSON.stringify({ type: 'interrupt' }));
  player.stop();
}
```

---

## 오디오 포맷 요약

| 구분 | 포맷 | 샘플레이트 | 비트 | 채널 |
|------|------|-----------|------|------|
| **입력** (마이크 → 서버) | PCM, Base64 | 16kHz | 16-bit signed | Mono |
| **출력** (서버 → 스피커) | PCM, Binary | 24kHz | 16-bit signed | Mono |

---

## 트러블슈팅

### 마이크 권한 에러
```javascript
navigator.mediaDevices.getUserMedia({ audio: true })
  .catch(err => {
    if (err.name === 'NotAllowedError') {
      alert('마이크 권한을 허용해주세요');
    }
  });
```

### 오디오 재생 안됨
- 브라우저 자동재생 정책: 사용자 인터랙션 후 `AudioContext.resume()` 호출 필요
```javascript
document.addEventListener('click', () => {
  audioContext.resume();
}, { once: true });
```

### WebSocket 연결 실패
- CORS: 같은 도메인이거나 서버에서 CORS 허용 필요
- HTTPS: wss:// 사용 시 SSL 인증서 필요

---

## 음성 ID (voice_id)

| ID | 설명 | 품질 | TTFA |
|----|------|------|------|
| `gd-icl` | In-Context Learning | 높음 | ~3초 (스트리밍 최적화) |
| `gd-default` | X-Vector 방식 | 중간 | ~2초 |

> **Note**: 스트리밍 파이프라인 적용으로 기존 8-10초에서 **3초로 개선**되었습니다.

---

## 서버 URL 설정

```javascript
// 프로덕션 (외부 접속) - 현재 활성화된 URL
const WS_URL = 'wss://crossconnect.ngrok.app/ws/voice/call';

// 로컬 개발
// const WS_URL = 'ws://localhost:5002/ws/voice/call';

// API 키 사용 시
// const WS_URL = 'wss://f0d5-210-97-73-22.ngrok-free.app/ws/voice/call?api_key=YOUR_KEY';
```
