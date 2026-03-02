#!/usr/bin/env python3
"""
GD Voice v5 Dataset - No Augmentation
- 모든 sample/*.wav 파일 사용
- 속도 증강 제거 (원본만)
- 3-12초 청크 분할
- Whisper 전사
- Audio codes 생성
"""

import os
import sys
import json
import torch
import soundfile as sf
import numpy as np
from pathlib import Path
from faster_whisper import WhisperModel
import librosa

sys.path.insert(0, '/home/nexus/connect/server/finetune/Qwen3-TTS')

SAMPLE_DIR = "/home/nexus/connect/server/sample"
OUTPUT_DIR = "/home/nexus/connect/server/finetune/data_v5"
CHUNK_MIN_SEC = 3.0
CHUNK_MAX_SEC = 12.0
SAMPLE_RATE = 24000


def load_and_resample(audio_path: str) -> tuple:
    audio, sr = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)
    return audio, sr


def split_audio_by_silence(audio: np.ndarray, sr: int) -> list:
    intervals = librosa.effects.split(audio, top_db=25, frame_length=2048, hop_length=512)

    chunks = []
    current_start = 0
    current_end = 0

    for start, end in intervals:
        seg_dur = (end - start) / sr
        cur_dur = (current_end - current_start) / sr if current_end > current_start else 0

        if cur_dur + seg_dur > CHUNK_MAX_SEC and cur_dur >= CHUNK_MIN_SEC:
            chunks.append((current_start, current_end))
            current_start = start
            current_end = end
        else:
            if current_start == 0 and current_end == 0:
                current_start = start
            current_end = end

    if (current_end - current_start) / sr >= CHUNK_MIN_SEC:
        chunks.append((current_start, current_end))

    return chunks


def main():
    print("=" * 70)
    print("GD Voice v5 Dataset - No Augmentation")
    print("=" * 70)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    chunks_dir = os.path.join(OUTPUT_DIR, "chunks")
    os.makedirs(chunks_dir, exist_ok=True)

    # 1. WAV 파일 찾기
    print(f"\n[1] Finding audio files")
    wav_files = sorted([f for f in os.listdir(SAMPLE_DIR) if f.endswith('.wav')])
    print(f"    Found {len(wav_files)} files")

    total_duration = 0
    for f in wav_files:
        path = os.path.join(SAMPLE_DIR, f)
        dur = librosa.get_duration(path=path)
        total_duration += dur
        print(f"      {f}: {dur:.1f}s")
    print(f"    Total: {total_duration:.1f}s ({total_duration/60:.1f} min)")

    # 2. 청크 분할
    print(f"\n[2] Splitting into {CHUNK_MIN_SEC}-{CHUNK_MAX_SEC}s chunks...")
    all_chunks = []

    for wav_file in wav_files:
        wav_path = os.path.join(SAMPLE_DIR, wav_file)
        audio, sr = load_and_resample(wav_path)
        chunks = split_audio_by_silence(audio, sr)
        print(f"    {wav_file}: {len(chunks)} chunks")

        for i, (start, end) in enumerate(chunks):
            chunk_audio = audio[start:end]
            all_chunks.append((chunk_audio, wav_file, i))

    print(f"    Total: {len(all_chunks)} chunks")

    # 3. 청크 저장 (증강 없이 원본만)
    print(f"\n[3] Saving chunks (no augmentation)...")
    chunk_files = []

    for idx, (chunk_audio, source_file, orig_idx) in enumerate(all_chunks):
        duration = len(chunk_audio) / SAMPLE_RATE

        if duration < CHUNK_MIN_SEC or duration > CHUNK_MAX_SEC + 2:
            continue

        base_name = os.path.splitext(source_file)[0]
        chunk_path = os.path.join(chunks_dir, f"chunk_{idx:04d}_{base_name}.wav")
        sf.write(chunk_path, chunk_audio, SAMPLE_RATE)
        chunk_files.append((chunk_path, duration))

    total_dur = sum(d for _, d in chunk_files)
    print(f"    Saved {len(chunk_files)} chunks")
    print(f"    Total duration: {total_dur:.1f}s ({total_dur/60:.1f} min)")

    # 4. Whisper 전사
    print(f"\n[4] Transcribing with Whisper...")
    whisper = WhisperModel("large-v3", device="cuda", compute_type="float16")

    transcriptions = []
    for i, (chunk_path, _) in enumerate(chunk_files):
        if i % 10 == 0:
            print(f"    Progress: {i}/{len(chunk_files)}")

        segments, _ = whisper.transcribe(chunk_path, language="ko", beam_size=5, vad_filter=True)
        text = " ".join([s.text.strip() for s in segments])
        transcriptions.append(text)

    print(f"    Transcribed {len(transcriptions)} chunks")

    # 5. Audio codes 생성
    print(f"\n[5] Generating audio codes...")
    from qwen_tts import Qwen3TTSTokenizer

    tokenizer = Qwen3TTSTokenizer.from_pretrained(
        "Qwen/Qwen3-TTS-Tokenizer-12Hz",
        device_map="cuda:0",
    )

    # 가장 긴 청크를 ref_audio로 (품질이 좋을 가능성)
    longest_idx = max(range(len(chunk_files)), key=lambda i: chunk_files[i][1])
    REF_AUDIO = chunk_files[longest_idx][0]
    print(f"    Reference audio: {REF_AUDIO} ({chunk_files[longest_idx][1]:.1f}s)")

    train_data = []
    skipped = 0

    for i, ((chunk_path, duration), text) in enumerate(zip(chunk_files, transcriptions)):
        if i % 10 == 0:
            print(f"    Progress: {i}/{len(chunk_files)}")

        if not text.strip() or len(text.strip()) < 5:
            skipped += 1
            continue

        enc = tokenizer.encode(chunk_path)
        codes_list = enc.audio_codes[0].cpu().tolist()

        train_data.append({
            "audio": chunk_path,
            "text": text,
            "audio_codes": codes_list,
            "language": "Korean",
            "ref_audio": REF_AUDIO,
            "duration": duration,
        })

    print(f"    Generated {len(train_data)} samples (skipped {skipped})")

    # 6. 저장
    print(f"\n[6] Saving dataset...")

    import random
    random.seed(42)
    random.shuffle(train_data)

    val_size = max(5, len(train_data) // 10)
    val_data = train_data[:val_size]
    train_data = train_data[val_size:]

    with open(os.path.join(OUTPUT_DIR, "gd_train.jsonl"), "w", encoding="utf-8") as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    with open(os.path.join(OUTPUT_DIR, "gd_val.jsonl"), "w", encoding="utf-8") as f:
        for item in val_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    stats = {
        "source_files": wav_files,
        "total_source_duration_sec": total_duration,
        "total_chunks": len(chunk_files),
        "train_samples": len(train_data),
        "val_samples": len(val_data),
        "augmentation": "none",
        "ref_audio": REF_AUDIO,
    }

    with open(os.path.join(OUTPUT_DIR, "dataset_stats.json"), "w") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(f"\n" + "=" * 70)
    print(f"Dataset prepared!")
    print(f"  Source: {total_duration:.1f}s ({total_duration/60:.1f} min)")
    print(f"  Chunks: {len(chunk_files)} (no augmentation)")
    print(f"  Train: {len(train_data)}, Val: {len(val_data)}")
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
