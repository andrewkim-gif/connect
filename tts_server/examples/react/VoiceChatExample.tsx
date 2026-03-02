/**
 * GD Voice Chat 컴포넌트 예제
 *
 * 사용법:
 * 1. useVoiceChat.ts를 프로젝트에 복사
 * 2. 이 컴포넌트를 참고하여 커스텀
 */

import React from 'react';
import { useVoiceChat } from './useVoiceChat';

// 스타일 (Tailwind CSS 기준, 일반 CSS로 변환 가능)
const styles = {
  container: 'flex flex-col h-screen bg-gray-900 text-white',
  header: 'p-4 border-b border-gray-700 flex items-center justify-between',
  status: 'flex items-center gap-2',
  statusDot: 'w-3 h-3 rounded-full',
  messages: 'flex-1 overflow-y-auto p-4 space-y-4',
  message: 'max-w-[80%] p-3 rounded-lg',
  userMessage: 'ml-auto bg-blue-600',
  gdMessage: 'mr-auto bg-gray-700',
  typing: 'animate-pulse',
  controls: 'p-4 border-t border-gray-700',
  recordBtn: 'w-full py-4 rounded-lg font-bold text-lg transition-all',
  recordBtnIdle: 'bg-red-600 hover:bg-red-500',
  recordBtnRecording: 'bg-red-400 animate-pulse',
  recordBtnDisabled: 'bg-gray-600 cursor-not-allowed',
};

export function VoiceChatExample() {
  const {
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
  } = useVoiceChat({
    // 서버 URL (기본값: 프로덕션 ngrok URL)
    // serverUrl: 'wss://crossconnect.ngrok.app/ws/voice/call',
    voiceId: 'gd-icl',
    onError: (error) => {
      console.error('Voice Chat Error:', error);
      alert(error);
    },
    onMetrics: (metrics) => {
      console.log('처리 완료:', {
        totalMs: metrics.total_ms,
        audioSec: metrics.audio_duration,
      });
    },
  });

  // 버튼 상태
  const getButtonState = () => {
    if (!isConnected) return 'disabled';
    if (isRecording) return 'recording';
    return 'idle';
  };

  const getButtonText = () => {
    if (!isConnected) return '연결 중...';
    if (isRecording) return '🎙️ 녹음 중... (손 떼면 전송)';
    if (isProcessing) return '⏳ GD가 대답 중...';
    return '🎤 눌러서 말하기';
  };

  return (
    <div className={styles.container}>
      {/* 헤더 */}
      <header className={styles.header}>
        <div>
          <h1 className="text-xl font-bold">GD Voice Call</h1>
          <p className="text-sm text-gray-400">G-Dragon과 음성 대화</p>
        </div>
        <div className={styles.status}>
          <span
            className={`${styles.statusDot} ${
              isConnected ? 'bg-green-500' : 'bg-red-500'
            }`}
          />
          <span className="text-sm">
            {isConnected ? `연결됨 (${clientId})` : '연결 안됨'}
          </span>
        </div>
      </header>

      {/* 메시지 목록 */}
      <div className={styles.messages}>
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-10">
            <p className="text-4xl mb-4">🎤</p>
            <p>아래 버튼을 눌러 GD에게 말해보세요</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`${styles.message} ${
              msg.role === 'user' ? styles.userMessage : styles.gdMessage
            }`}
          >
            <div className="text-xs text-gray-300 mb-1">
              {msg.role === 'user' ? '나' : 'GD'}
            </div>
            <p>{msg.text}</p>
          </div>
        ))}

        {/* 타이핑 중인 응답 */}
        {currentResponse && (
          <div className={`${styles.message} ${styles.gdMessage} ${styles.typing}`}>
            <div className="text-xs text-gray-300 mb-1">GD</div>
            <p>{currentResponse}</p>
          </div>
        )}
      </div>

      {/* 컨트롤 */}
      <div className={styles.controls}>
        {/* 녹음 버튼 */}
        <button
          className={`${styles.recordBtn} ${
            getButtonState() === 'disabled'
              ? styles.recordBtnDisabled
              : getButtonState() === 'recording'
              ? styles.recordBtnRecording
              : styles.recordBtnIdle
          }`}
          onMouseDown={startRecording}
          onMouseUp={stopRecording}
          onMouseLeave={() => isRecording && stopRecording()}
          onTouchStart={startRecording}
          onTouchEnd={stopRecording}
          disabled={!isConnected || isProcessing}
        >
          {getButtonText()}
        </button>

        {/* 추가 버튼들 */}
        <div className="flex gap-2 mt-2">
          <button
            className="flex-1 py-2 bg-gray-700 rounded hover:bg-gray-600 disabled:opacity-50"
            onClick={resetConversation}
            disabled={!isConnected || messages.length === 0}
          >
            🔄 대화 초기화
          </button>
          <button
            className="flex-1 py-2 bg-gray-700 rounded hover:bg-gray-600 disabled:opacity-50"
            onClick={interruptResponse}
            disabled={!isProcessing}
          >
            ⏹️ 응답 중단
          </button>
        </div>
      </div>
    </div>
  );
}

export default VoiceChatExample;
