#!/usr/bin/env python3
"""
TTS Tail Silence 비교 테스트

이전 (tail 없음) vs 이후 (tail 있음) 음성 비교
"""

import sys
import os
import time
import numpy as np
import scipy.io.wavfile as wav

# 프로젝트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 테스트 문장
TEST_SENTENCES = [
    "안녕하세요.",
    "네, 그렇습니다.",
    "다음에 또 연락드리겠습니다~",
    "감사합니다!",
]

OUTPUT_DIR = "/home/nexus/connect/server/tts_server/test_output"


def save_wav(audio: np.ndarray, sample_rate: int, filename: str):
    """WAV 파일 저장"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)

    # float32 → int16 변환
    audio_int16 = (audio * 32767).astype(np.int16)
    wav.write(filepath, sample_rate, audio_int16)

    duration = len(audio) / sample_rate
    print(f"  💾 저장: {filename} ({duration:.2f}s, {len(audio)} samples)")
    return filepath


def generate_without_tail(model, text: str, gen_params: dict):
    """원본 TTS (tail 없음)"""
    from config import settings

    result = model.generate_custom_voice(
        text=text,
        speaker=settings.FINETUNED_SPEAKER,
        language=gen_params.get("language", "Korean"),
    )
    audio_list, sample_rate = result
    audio = audio_list[0]

    if isinstance(audio, np.ndarray):
        return audio.astype(np.float32), sample_rate
    return np.array(audio, dtype=np.float32), sample_rate


def generate_with_tail(model, text: str, gen_params: dict):
    """수정된 TTS (tail 포함)"""
    from config import settings

    # 원본 생성
    result = model.generate_custom_voice(
        text=text,
        speaker=settings.FINETUNED_SPEAKER,
        language=gen_params.get("language", "Korean"),
    )
    audio_list, sample_rate = result
    audio = audio_list[0]

    if not isinstance(audio, np.ndarray):
        audio = np.array(audio)
    audio = audio.astype(np.float32)

    # Tail 처리 적용
    FADE_OUT_MS = 50
    TAIL_SILENCE_MS = 150

    # Fade-out
    fade_samples = int(sample_rate * FADE_OUT_MS / 1000)
    if len(audio) > fade_samples:
        fade_curve = np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)
        audio[-fade_samples:] = audio[-fade_samples:] * fade_curve

    # Silence tail
    silence_samples = int(sample_rate * TAIL_SILENCE_MS / 1000)
    silence = np.zeros(silence_samples, dtype=np.float32)
    audio = np.concatenate([audio, silence])

    return audio, sample_rate


def main():
    print("=" * 60)
    print("🎤 TTS Tail Silence 비교 테스트")
    print("=" * 60)

    # 모델 로드
    print("\n📦 모델 로딩...")
    from services.model_manager import model_manager
    from config import settings

    model_manager.load_models()
    model = model_manager.get_model("finetuned")

    gen_params = {
        "language": settings.GEN_LANGUAGE,
    }

    print(f"✅ 모델 준비 완료")
    print(f"📁 출력 디렉토리: {OUTPUT_DIR}")

    # 각 문장 테스트
    for i, text in enumerate(TEST_SENTENCES, 1):
        print(f"\n{'─' * 50}")
        print(f"[{i}] \"{text}\"")
        print(f"{'─' * 50}")

        # 원본 (tail 없음)
        print("\n  🔴 원본 (tail 없음):")
        start = time.time()
        audio_orig, sr = generate_without_tail(model, text, gen_params)
        elapsed_orig = (time.time() - start) * 1000
        save_wav(audio_orig, sr, f"test_{i:02d}_original.wav")
        print(f"     처리 시간: {elapsed_orig:.0f}ms")

        # 수정 (tail 포함)
        print("\n  🟢 수정 (tail 포함):")
        start = time.time()
        audio_tail, sr = generate_with_tail(model, text, gen_params)
        elapsed_tail = (time.time() - start) * 1000
        save_wav(audio_tail, sr, f"test_{i:02d}_with_tail.wav")
        print(f"     처리 시간: {elapsed_tail:.0f}ms")

        # 비교
        orig_duration = len(audio_orig) / sr
        tail_duration = len(audio_tail) / sr
        diff = tail_duration - orig_duration
        print(f"\n  📊 비교: 원본 {orig_duration:.2f}s → 수정 {tail_duration:.2f}s (+{diff*1000:.0f}ms)")

    print(f"\n{'=' * 60}")
    print(f"✅ 테스트 완료!")
    print(f"📁 결과 파일 위치: {OUTPUT_DIR}")
    print(f"\n🎧 파일 비교 방법:")
    print(f"   cd {OUTPUT_DIR}")
    print(f"   # 원본 재생: aplay test_01_original.wav")
    print(f"   # 수정 재생: aplay test_01_with_tail.wav")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
