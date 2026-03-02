#!/usr/bin/env python3
"""
GD Voice Full Dataset Preparation v4
- 모든 sample/*.wav 파일 사용
- 3-12초 청크 분할
- Whisper 전사
- Audio codes 생성
- 데이터 증강 (Speed Perturbation)
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

# 경로 설정
sys.path.insert(0, '/home/nexus/connect/server/finetune/Qwen3-TTS')

SAMPLE_DIR = "/home/nexus/connect/server/sample"
OUTPUT_DIR = "/home/nexus/connect/server/finetune/data_v4"
CHUNK_MIN_SEC = 3.0
CHUNK_MAX_SEC = 12.0
SAMPLE_RATE = 24000

# 데이터 증강 설정
SPEED_FACTORS = [0.95, 1.0, 1.05]  # 속도 변환으로 3배 증강


def load_and_resample(audio_path: str) -> tuple:
    """오디오 로드 및 24kHz 리샘플링"""
    audio, sr = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)
    return audio, sr


def split_audio_by_silence(audio: np.ndarray, sr: int) -> list:
    """무음 기반으로 오디오 청크 분할"""
    # 무음 구간 탐지
    intervals = librosa.effects.split(audio, top_db=25, frame_length=2048, hop_length=512)

    chunks = []
    current_chunk_start = 0
    current_chunk_end = 0

    for start, end in intervals:
        segment_duration = (end - start) / sr
        current_duration = (current_chunk_end - current_chunk_start) / sr if current_chunk_end > current_chunk_start else 0

        if current_duration + segment_duration > CHUNK_MAX_SEC and current_duration >= CHUNK_MIN_SEC:
            chunks.append((current_chunk_start, current_chunk_end))
            current_chunk_start = start
            current_chunk_end = end
        else:
            if current_chunk_start == 0 and current_chunk_end == 0:
                current_chunk_start = start
            current_chunk_end = end

    if (current_chunk_end - current_chunk_start) / sr >= CHUNK_MIN_SEC:
        chunks.append((current_chunk_start, current_chunk_end))

    return chunks


def apply_speed_perturbation(audio: np.ndarray, sr: int, factor: float) -> np.ndarray:
    """속도 변환 (피치 유지)"""
    if factor == 1.0:
        return audio
    return librosa.effects.time_stretch(audio, rate=factor)


def main():
    print("=" * 70)
    print("GD Voice Full Dataset Preparation v4")
    print("=" * 70)

    # 출력 디렉토리 생성
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    chunks_dir = os.path.join(OUTPUT_DIR, "chunks")
    os.makedirs(chunks_dir, exist_ok=True)

    # 1. 모든 WAV 파일 찾기
    print(f"\n[1] Finding audio files in {SAMPLE_DIR}")
    wav_files = sorted([f for f in os.listdir(SAMPLE_DIR) if f.endswith('.wav')])
    print(f"    Found {len(wav_files)} files:")

    total_duration = 0
    for f in wav_files:
        path = os.path.join(SAMPLE_DIR, f)
        audio, _ = librosa.load(path, sr=None, mono=True)
        dur = len(audio) / librosa.get_samplerate(path)
        total_duration += dur
        print(f"      {f}: {dur:.1f}s")

    print(f"    Total: {total_duration:.1f}s ({total_duration/60:.1f} min)")

    # 2. 모든 파일 청크 분할
    print(f"\n[2] Splitting into {CHUNK_MIN_SEC}-{CHUNK_MAX_SEC}s chunks...")
    all_chunks = []  # (audio_array, source_file, chunk_idx)

    for wav_file in wav_files:
        wav_path = os.path.join(SAMPLE_DIR, wav_file)
        audio, sr = load_and_resample(wav_path)

        chunks = split_audio_by_silence(audio, sr)
        print(f"    {wav_file}: {len(chunks)} chunks")

        for i, (start, end) in enumerate(chunks):
            chunk_audio = audio[start:end]
            all_chunks.append((chunk_audio, wav_file, i))

    print(f"    Total chunks: {len(all_chunks)}")

    # 3. 청크 저장 (속도 변환 포함)
    print(f"\n[3] Saving chunks with speed augmentation...")
    chunk_files = []  # (path, duration, speed_factor)

    chunk_idx = 0
    for chunk_audio, source_file, orig_idx in all_chunks:
        base_name = os.path.splitext(source_file)[0]

        for speed in SPEED_FACTORS:
            # 속도 변환
            augmented = apply_speed_perturbation(chunk_audio, SAMPLE_RATE, speed)
            duration = len(augmented) / SAMPLE_RATE

            # 최소/최대 길이 확인
            if duration < CHUNK_MIN_SEC or duration > CHUNK_MAX_SEC + 2:
                continue

            # 저장
            speed_str = f"sp{int(speed*100)}"
            chunk_path = os.path.join(chunks_dir, f"chunk_{chunk_idx:04d}_{base_name}_{speed_str}.wav")
            sf.write(chunk_path, augmented, SAMPLE_RATE)
            chunk_files.append((chunk_path, duration, speed))
            chunk_idx += 1

    print(f"    Total augmented chunks: {len(chunk_files)}")
    total_aug_duration = sum(d for _, d, _ in chunk_files)
    print(f"    Total duration: {total_aug_duration:.1f}s ({total_aug_duration/60:.1f} min)")

    # 4. Whisper 전사
    print(f"\n[4] Transcribing with Whisper large-v3...")
    whisper = WhisperModel("large-v3", device="cuda", compute_type="float16")

    transcriptions = []
    for i, (chunk_path, duration, speed) in enumerate(chunk_files):
        if i % 20 == 0:
            print(f"    Progress: {i}/{len(chunk_files)}")

        segments, info = whisper.transcribe(
            chunk_path,
            language="ko",
            beam_size=5,
            vad_filter=True
        )
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

    # 첫 번째 청크를 ref_audio로 사용
    REF_AUDIO = chunk_files[0][0]
    print(f"    Reference audio: {REF_AUDIO}")

    train_data = []
    skipped = 0

    for i, ((chunk_path, duration, speed), text) in enumerate(zip(chunk_files, transcriptions)):
        if i % 20 == 0:
            print(f"    Progress: {i}/{len(chunk_files)}")

        if not text.strip() or len(text.strip()) < 5:
            skipped += 1
            continue

        # 오디오 코드 생성
        enc = tokenizer.encode(chunk_path)
        codes_list = enc.audio_codes[0].cpu().tolist()

        train_item = {
            "audio": chunk_path,
            "text": text,
            "audio_codes": codes_list,
            "language": "Korean",
            "ref_audio": REF_AUDIO,
            "duration": duration,
            "speed_factor": speed,
        }
        train_data.append(train_item)

    print(f"    Generated {len(train_data)} samples (skipped {skipped})")

    # 6. Train/Val 분할 및 저장
    print(f"\n[6] Saving dataset...")

    # 셔플 및 분할 (90% train, 10% val)
    import random
    random.seed(42)
    random.shuffle(train_data)

    val_size = max(5, len(train_data) // 10)
    val_data = train_data[:val_size]
    train_data = train_data[val_size:]

    # 저장
    train_path = os.path.join(OUTPUT_DIR, "gd_train.jsonl")
    val_path = os.path.join(OUTPUT_DIR, "gd_val.jsonl")

    with open(train_path, "w", encoding="utf-8") as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    with open(val_path, "w", encoding="utf-8") as f:
        for item in val_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # 통계 저장
    stats = {
        "source_files": wav_files,
        "total_source_duration_sec": total_duration,
        "total_chunks": len(chunk_files),
        "total_augmented_duration_sec": total_aug_duration,
        "train_samples": len(train_data),
        "val_samples": len(val_data),
        "speed_factors": SPEED_FACTORS,
        "ref_audio": REF_AUDIO,
    }

    with open(os.path.join(OUTPUT_DIR, "dataset_stats.json"), "w") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(f"\n" + "=" * 70)
    print(f"Dataset prepared!")
    print(f"  Source duration: {total_duration:.1f}s ({total_duration/60:.1f} min)")
    print(f"  Augmented duration: {total_aug_duration:.1f}s ({total_aug_duration/60:.1f} min)")
    print(f"  Train samples: {len(train_data)}")
    print(f"  Val samples: {len(val_data)}")
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
