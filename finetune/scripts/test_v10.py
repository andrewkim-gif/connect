#!/usr/bin/env python3
"""GD Voice v10 vs v5 Comparison Test"""

import os
import sys
import torch
import soundfile as sf

sys.path.insert(0, '/home/nexus/connect/server/finetune/Qwen3-TTS')

OUTPUT_DIR = "/home/nexus/connect/server/finetune/output/v10_comparison"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TEST_TEXTS = [
    "안녕하세요, 저는 지드래곤입니다.",
    "나? 난 지금 작업실이지. 새로운 음악을 만들고 있어. 넌 뭐하고 있니?",
    "음악은 저에게 있어서 삶 그 자체입니다. 무대 위에서 노래할 때 가장 행복합니다.",
]

def test_model(model_path, version_name):
    from qwen_tts import Qwen3TTSModel

    print(f"\n{'='*50}")
    print(f"Testing {version_name}: {model_path}")
    print(f"{'='*50}")

    tts = Qwen3TTSModel.from_pretrained(
        model_path,
        device_map="cuda:0",
        dtype=torch.bfloat16,
        attn_implementation="flash_attention_2",
    )

    for i, text in enumerate(TEST_TEXTS):
        print(f"\n[{i+1}] {text[:40]}...")

        wavs, sr = tts.generate_custom_voice(
            text=text,
            speaker="gd",
            language="Korean",
        )

        audio = wavs[0]
        output_path = os.path.join(OUTPUT_DIR, f"{version_name}_test_{i+1}.wav")
        sf.write(output_path, audio, sr)
        print(f"    Saved: {output_path} ({len(audio)/sr:.2f}s)")

    del tts
    torch.cuda.empty_cache()

def main():
    print("=" * 60)
    print("GD Voice v10 vs v5 Comparison Test")
    print("=" * 60)

    # Test v10
    test_model(
        "/home/nexus/connect/server/finetune/models/gd-voice-v10/checkpoint-epoch-final",
        "v10"
    )

    # Test v5 for comparison
    test_model(
        "/home/nexus/connect/server/finetune/models/gd-voice-v5/checkpoint-epoch-final",
        "v5"
    )

    print(f"\n{'='*60}")
    print(f"Comparison complete! Output: {OUTPUT_DIR}")
    print(f"{'='*60}")
    print("\nFiles generated:")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        if f.endswith('.wav'):
            print(f"  - {f}")

if __name__ == "__main__":
    main()
