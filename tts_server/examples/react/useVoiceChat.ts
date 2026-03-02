/**
 * GD Voice Chat React Hook
 *
 * 사용법:
 * ```tsx
 * const { isConnected, isRecording, messages, startRecording, stopRecording } = useVoiceChat();
 * ```
 */

import { useState, useRef, useCallback, useEffect } from 'react';

// ============ Types ============

interface Message {
  role: 'user' | 'gd';
  text: string;
  timestamp: number;
}

interface Metrics {
  stt_ms: number;
  llm_ttfa_ms: number;
  tts_ttfa_ms: number;
  total_ms: number;
  audio_duration: number;
  user_text: string;
  response_text: string;
}

interface UseVoiceChatOptions {
  serverUrl?: string;
  voiceId?: 'gd-icl' | 'gd-default';
  onError?: (error: string) => void;
  onMetrics?: (metrics: Metrics) => void;
}

interface UseVoiceChatReturn {
  // 상태
  isConnected: boolean;
  isRecording: boolean;
  isProcessing: boolean;
  messages: Message[];
  currentResponse: string;
  clientId: string | null;

  // 액션
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  resetConversation: () => void;
  interruptResponse: () => void;
  connect: () => void;
  disconnect: () => void;
}

// ============ Audio Player ============

class AudioPlayer {
  private audioContext: AudioContext;
  private queue: ArrayBuffer[] = [];
  private isPlaying = false;
  private sampleRate: number;

  constructor(sampleRate = 24000) {
    this.sampleRate = sampleRate;
    this.audioContext = new AudioContext({ sampleRate });
  }

  async addChunk(blob: Blob) {
    const buffer = await blob.arrayBuffer();
    this.queue.push(buffer);
    if (!this.isPlaying) {
      this.playNext();
    }
  }

  private async playNext() {
    if (this.queue.length === 0) {
      this.isPlaying = false;
      return;
    }

    this.isPlaying = true;

    // Resume if suspended (autoplay policy)
    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume();
    }

    const buffer = this.queue.shift()!;

    // PCM Int16 → Float32
    const pcm16 = new Int16Array(buffer);
    const float32 = new Float32Array(pcm16.length);
    for (let i = 0; i < pcm16.length; i++) {
      float32[i] = pcm16[i] / 32768;
    }

    // AudioBuffer 생성 및 재생
    const audioBuffer = this.audioContext.createBuffer(1, float32.length, this.sampleRate);
    audioBuffer.getChannelData(0).set(float32);

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

  close() {
    this.audioContext.close();
  }
}

// ============ Voice Recorder ============

class VoiceRecorder {
  private audioContext: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private processor: ScriptProcessorNode | null = null;
  private chunks: Int16Array[] = [];

  async start() {
    this.chunks = [];

    // 마이크 권한 요청
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });

    // AudioContext (16kHz)
    this.audioContext = new AudioContext({ sampleRate: 16000 });
    const source = this.audioContext.createMediaStreamSource(this.stream);

    // ScriptProcessor로 PCM 추출
    this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
    this.processor.onaudioprocess = (e) => {
      const inputData = e.inputBuffer.getChannelData(0);
      const pcm16 = new Int16Array(inputData.length);
      for (let i = 0; i < inputData.length; i++) {
        pcm16[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
      }
      this.chunks.push(pcm16);
    };

    source.connect(this.processor);
    this.processor.connect(this.audioContext.destination);
  }

  stop(): ArrayBuffer {
    // 스트림 정지
    this.stream?.getTracks().forEach((track) => track.stop());
    this.audioContext?.close();

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

// ============ Utilities ============

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

// ============ Hook ============

// 프로덕션 서버 URL
const DEFAULT_SERVER_URL = 'wss://crossconnect.ngrok.app/ws/voice/call';

export function useVoiceChat(options: UseVoiceChatOptions = {}): UseVoiceChatReturn {
  const {
    serverUrl = DEFAULT_SERVER_URL,
    voiceId = 'gd-icl',
    onError,
    onMetrics,
  } = options;

  // State
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentResponse, setCurrentResponse] = useState('');
  const [clientId, setClientId] = useState<string | null>(null);

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const recorderRef = useRef<VoiceRecorder | null>(null);
  const playerRef = useRef<AudioPlayer | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // WebSocket 메시지 핸들러
  const handleMessage = useCallback(
    (data: any) => {
      switch (data.type) {
        case 'connected':
          setClientId(data.client_id);
          break;

        case 'transcription':
          setMessages((prev) => [
            ...prev,
            { role: 'user', text: data.text, timestamp: Date.now() },
          ]);
          setIsProcessing(true);
          break;

        case 'response_start':
          setCurrentResponse('');
          break;

        case 'response_text':
          setCurrentResponse((prev) => prev + data.text);
          break;

        case 'response_end':
          const metrics = data.metrics as Metrics;
          setMessages((prev) => [
            ...prev,
            { role: 'gd', text: metrics.response_text, timestamp: Date.now() },
          ]);
          setCurrentResponse('');
          setIsProcessing(false);
          onMetrics?.(metrics);
          break;

        case 'interrupted':
          setIsProcessing(false);
          setCurrentResponse('');
          break;

        case 'reset_complete':
          setMessages([]);
          break;

        case 'error':
          setIsProcessing(false);
          onError?.(data.message);
          break;
      }
    },
    [onError, onMetrics]
  );

  // 연결
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(serverUrl);

    ws.onopen = () => {
      setIsConnected(true);
      // Ping 인터벌 설정
      pingIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000);
    };

    ws.onclose = () => {
      setIsConnected(false);
      setClientId(null);
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
    };

    ws.onerror = () => {
      onError?.('WebSocket 연결 에러');
    };

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
  }, [serverUrl, handleMessage, onError]);

  // 연결 해제
  const disconnect = useCallback(() => {
    wsRef.current?.close();
    playerRef.current?.close();
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
    }
  }, []);

  // 자동 연결
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  // 녹음 시작
  const startRecording = useCallback(async () => {
    if (!isConnected || isRecording) return;

    try {
      recorderRef.current = new VoiceRecorder();
      await recorderRef.current.start();
      setIsRecording(true);
    } catch (err) {
      onError?.('마이크 권한이 필요합니다');
    }
  }, [isConnected, isRecording, onError]);

  // 녹음 중지 및 전송
  const stopRecording = useCallback(() => {
    if (!isRecording || !recorderRef.current) return;

    const pcmData = recorderRef.current.stop();
    setIsRecording(false);

    // 전송
    const base64 = arrayBufferToBase64(pcmData);
    wsRef.current?.send(
      JSON.stringify({
        type: 'voice_input',
        audio: base64,
        voice_id: voiceId,
      })
    );
  }, [isRecording, voiceId]);

  // 대화 초기화
  const resetConversation = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ type: 'reset' }));
  }, []);

  // 응답 중단
  const interruptResponse = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ type: 'interrupt' }));
    playerRef.current?.stop();
  }, []);

  return {
    isConnected,
    isRecording,
    isProcessing,
    messages,
    currentResponse,
    clientId,
    startRecording,
    stopRecording,
    resetConversation,
    interruptResponse,
    connect,
    disconnect,
  };
}

export default useVoiceChat;
