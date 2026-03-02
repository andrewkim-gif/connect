#!/usr/bin/env python3
"""GD Voice v6 Test - Generate test audio samples"""

import os
import sys
import torch
import soundfile as sf

sys.path.insert(0, '/home/nexus/connect/server/finetune/Qwen3-TTS')

MODEL_PATH = "/home/nexus/connect/server/finetune/models/gd-voice-v6/checkpoint-epoch-final"
OUTPUT_DIR = "/home/nexus/connect/server/finetune/output/v6_test"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Test sentences
TEST_TEXTS = [
    "안녕하세요, 저는 지드래곤입니다.",
    "오늘 날씨가 정말 좋네요.",
    "빅뱅의 리더로서 항상 최선을 다하고 있습니다.",
]

def main():
    print("=" * 60)
    print("GD Voice v6 Test")
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
        print(f"\n[{i+1}] {text}")

        wavs, sr = tts.generate_custom_voice(
            text=text,
            speaker="gd",
            language="Korean",
        )

        output_path = os.path.join(OUTPUT_DIR, f"test_{i+1}.wav")
        sf.write(output_path, wavs[0], sr)
        print(f"    Saved: {output_path}")

    print(f"\n{'=' * 60}")
    print(f"Test complete! Output: {OUTPUT_DIR}")
    print("=" * 60)

if __name__ == "__main__":
    main()
