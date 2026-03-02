#!/usr/bin/env python3
"""
GD Voice Fine-tuned 모델 테스트 추론
"""

import torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel

# 모델 로드
print("Loading GD fine-tuned model...")
model_path = "/home/nexus/connect/server/finetune/models/gd-voice/checkpoint-epoch-4"

tts = Qwen3TTSModel.from_pretrained(
    model_path,
    device_map="cuda:0",
    dtype=torch.bfloat16,
    attn_implementation="flash_attention_2",
)

print("Model loaded successfully!")
print(f"Model type: {tts.model.tts_model_type}")
print(f"Supported speakers: {tts.get_supported_speakers()}")

# 테스트 문장들
test_texts = [
    "안녕하세요 여러분, 지드래곤입니다.",
    "오늘 날씨가 정말 좋네요.",
    "여러분 모두 행복한 하루 되세요.",
]

print("\n=== Inference Test ===")
for i, text in enumerate(test_texts):
    print(f"\n[{i+1}] Generating: {text}")

    wavs, sr = tts.generate_custom_voice(
        text=text,
        speaker="gd",
        language="Korean",
        max_new_tokens=512,  # 제한
        temperature=0.7,
        top_p=0.9,
    )

    output_path = f"/home/nexus/connect/server/finetune/data/test_output_{i+1}.wav"
    sf.write(output_path, wavs[0], sr)
    print(f"    Saved: {output_path} ({len(wavs[0])/sr:.2f}s)")

print("\n✅ All tests completed!")
