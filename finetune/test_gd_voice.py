#!/usr/bin/env python3
"""
GD Fine-tuned Voice 테스트 스크립트
"""

import sys
sys.path.insert(0, '/home/nexus/connect/server/finetune/Qwen3-TTS')

import torch
import soundfile as sf
from datetime import datetime

# 모델 경로
MODEL_PATH = "/home/nexus/connect/server/finetune/models/gd-voice/checkpoint-epoch-final"
OUTPUT_DIR = "/home/nexus/connect/server/finetune/outputs"

# 테스트 텍스트
TEST_TEXT = "안녕 난 지디야. 오늘 하루 잘 지냈어?"

def main():
    print("=" * 60)
    print("GD Fine-tuned Voice Test")
    print("=" * 60)

    # 출력 디렉토리 생성
    import os
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"\n[1] Loading model from: {MODEL_PATH}")

    from qwen_tts.inference.qwen3_tts_model import Qwen3TTSModel

    tts = Qwen3TTSModel.from_pretrained(
        MODEL_PATH,
        device_map="cuda:0",  # 핵심! GPU에 명시적 로드
        dtype=torch.bfloat16,
        attn_implementation="flash_attention_2",
    )

    print(f"    Model type: {tts.model.tts_model_type}")
    print(f"    Available speakers: {list(tts.model.talker.config.spk_id.keys())}")

    print(f"\n[2] Generating speech...")
    print(f"    Text: {TEST_TEXT}")
    print(f"    Speaker: gd")
    print(f"    Language: Korean")

    # Custom Voice 생성
    wavs, sr = tts.generate_custom_voice(
        text=TEST_TEXT,
        speaker="gd",
        language="Korean",
        do_sample=True,
        top_k=50,
        top_p=0.9,
        temperature=0.7,
        repetition_penalty=1.1,
        max_new_tokens=2048,
    )

    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"{OUTPUT_DIR}/gd_test_{timestamp}.wav"

    sf.write(output_path, wavs[0], sr)

    duration = len(wavs[0]) / sr
    print(f"\n[3] Output saved!")
    print(f"    Path: {output_path}")
    print(f"    Duration: {duration:.2f}s")
    print(f"    Sample rate: {sr}Hz")

    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)

    return output_path

if __name__ == "__main__":
    output = main()
    print(f"\n>>> Play with: aplay {output}")
