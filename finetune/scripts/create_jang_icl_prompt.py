#!/usr/bin/env python3
"""
장(Jang) ICL Voice Clone Prompt 생성
- jang_sample_icl.wav를 사용하여 voice clone prompt 생성
- tts_server/data/prompts/jang-clone.pkl에 캐싱
"""

import os
import sys
import json
import pickle

sys.path.insert(0, '/home/nexus/connect/server/finetune/Qwen3-TTS')

from qwen_tts.inference.qwen3_tts_model import Qwen3TTSModel
import torch

# 설정
SAMPLE_PATH = "/home/nexus/connect/server/sample/jang_sample_icl.wav"
ICL_INFO_PATH = "/home/nexus/connect/server/finetune/data_jang/icl_sample_info.json"
OUTPUT_DIR = "/home/nexus/connect/server/tts_server/data/prompts"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "jang-clone.pkl")


def main():
    print("=" * 60)
    print("장(Jang) ICL Voice Clone Prompt 생성")
    print("=" * 60)

    # ICL 정보 로드
    with open(ICL_INFO_PATH, 'r', encoding='utf-8') as f:
        icl_info = json.load(f)

    ref_text = icl_info["text"]
    print(f"\n[1] Reference Audio: {SAMPLE_PATH}")
    print(f"    Duration: {icl_info['duration']:.1f}s")
    print(f"    Text: {ref_text[:80]}...")

    # 모델 로드
    print(f"\n[2] Loading Base Model...")
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        torch_dtype=torch.bfloat16,
        attn_implementation="flash_attention_2",
        device_map="cuda:0",
    )
    print("    Model loaded.")

    # Voice Clone Prompt 생성
    print(f"\n[3] Creating Voice Clone Prompt...")
    prompt = model.create_voice_clone_prompt(
        ref_audio=SAMPLE_PATH,
        ref_text=ref_text,
    )
    print("    Prompt created.")

    # 저장
    print(f"\n[4] Saving to {OUTPUT_FILE}...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, 'wb') as f:
        pickle.dump(prompt, f)
    print("    Saved.")

    # 테스트 합성
    print(f"\n[5] Test synthesis...")
    test_text = "안녕하세요. 테스트입니다."
    result = model.generate_voice_clone(
        text=test_text,
        voice_clone_prompt=prompt,
        language="Korean",
    )
    audio, sr = result
    print(f"    Generated: {len(audio[0])/sr:.2f}s audio")

    # 테스트 오디오 저장
    test_output = "/home/nexus/connect/server/finetune/output/jang_icl_test.wav"
    os.makedirs(os.path.dirname(test_output), exist_ok=True)
    import soundfile as sf
    sf.write(test_output, audio[0], sr)
    print(f"    Test audio saved: {test_output}")

    print(f"\n" + "=" * 60)
    print(f"ICL Voice Clone Prompt 생성 완료!")
    print(f"  Output: {OUTPUT_FILE}")
    print(f"  Test: {test_output}")
    print("=" * 60)


if __name__ == "__main__":
    main()
