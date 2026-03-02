#!/usr/bin/env python3
"""GD Voice v7 Test - Longer sentences with padding"""

import os
import sys
import torch
import soundfile as sf
import numpy as np

sys.path.insert(0, '/home/nexus/connect/server/finetune/Qwen3-TTS')

MODEL_PATH = "/home/nexus/connect/server/finetune/models/gd-voice-v7/checkpoint-epoch-final"
OUTPUT_DIR = "/home/nexus/connect/server/finetune/output/v7_long_test"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Longer test sentences
TEST_TEXTS = [
    "안녕하세요, 저는 지드래곤입니다. 오늘 여러분과 함께 이야기를 나눌 수 있어서 정말 기쁩니다.",
    "음악은 저에게 있어서 삶 그 자체입니다. 무대 위에서 노래할 때 가장 행복하고 자유로움을 느낍니다.",
    "빅뱅의 리더로서 항상 최선을 다하고 있습니다. 팬들에게 좋은 음악과 무대를 보여드리고 싶습니다.",
    "창작의 과정은 때로는 힘들지만, 그 결과물이 팬들에게 감동을 줄 때 모든 노력이 보상받는 느낌입니다.",
]

def add_tail_padding(audio, sr, padding_sec=0.3):
    """Add fade-out padding at the end"""
    padding_samples = int(sr * padding_sec)
    padding = np.zeros(padding_samples)

    # Create fade-out for last 100ms of audio
    fade_samples = int(sr * 0.1)
    if len(audio) > fade_samples:
        fade = np.linspace(1, 0, fade_samples)
        audio[-fade_samples:] = audio[-fade_samples:] * fade

    return np.concatenate([audio, padding])

def main():
    print("=" * 60)
    print("GD Voice v7 Test - Long Sentences")
    print("=" * 60)

    from qwen_tts import Qwen3TTSModel

    print(f"Loading model from {MODEL_PATH}...")
    tts = Qwen3TTSModel.from_pretrained(
        MODEL_PATH,
        device_map="cuda:0",
        dtype=torch.bfloat16,
        attn_implementation="flash_attention_2",
    )

    print(f"\nGenerating {len(TEST_TEXTS)} test samples...")

    for i, text in enumerate(TEST_TEXTS):
        print(f"\n[{i+1}] {text[:50]}...")

        wavs, sr = tts.generate_custom_voice(
            text=text,
            speaker="gd",
            language="Korean",
        )

        audio = wavs[0]

        # Save original
        output_path = os.path.join(OUTPUT_DIR, f"test_{i+1}.wav")
        sf.write(output_path, audio, sr)
        print(f"    Original: {output_path} ({len(audio)/sr:.2f}s)")

        # Save with padding
        audio_padded = add_tail_padding(audio, sr, padding_sec=0.3)
        output_path_padded = os.path.join(OUTPUT_DIR, f"test_{i+1}_padded.wav")
        sf.write(output_path_padded, audio_padded, sr)
        print(f"    Padded:   {output_path_padded} ({len(audio_padded)/sr:.2f}s)")

    print(f"\n{'=' * 60}")
    print(f"Test complete! Output: {OUTPUT_DIR}")
    print("=" * 60)

if __name__ == "__main__":
    main()
