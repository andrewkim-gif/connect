#!/usr/bin/env python3
"""장 음성 v1 모델 테스트"""

import sys
sys.path.insert(0, '/home/nexus/connect/server/finetune/Qwen3-TTS')

import torch
import soundfile as sf
from qwen_tts.inference.qwen3_tts_model import Qwen3TTSModel

MODEL_PATH = "/home/nexus/connect/server/finetune/models/jang-voice-v1/checkpoint-epoch-final"
OUTPUT_DIR = "/home/nexus/connect/server/finetune/output"

def main():
    print("=" * 60)
    print("장(Jang) Voice v1 테스트")
    print("=" * 60)

    print("\n[1] Loading model...")
    model = Qwen3TTSModel.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch.bfloat16,
        attn_implementation="flash_attention_2",
        device_map="cuda:0",
    )
    print("    Model loaded.")

    # 테스트 문장들
    test_texts = [
        "안녕하세요. 테스트입니다.",
        "위믹스는 블록체인 게임 플랫폼입니다.",
        "오늘 날씨가 정말 좋네요. 산책하기 딱 좋은 날이에요.",
    ]

    print("\n[2] Generating test audio...")
    for i, text in enumerate(test_texts):
        print(f"\n    [{i+1}] {text}")

        result = model.generate_custom_voice(
            text=text,
            speaker="jang",
            language="Korean",
        )

        audio_list, sr = result
        audio = audio_list[0]

        output_path = f"{OUTPUT_DIR}/jang_v1_test_{i+1}.wav"
        sf.write(output_path, audio, sr)
        print(f"        → {output_path} ({len(audio)/sr:.2f}s)")

    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)

if __name__ == "__main__":
    main()
