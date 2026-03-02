#!/usr/bin/env python3
"""
SPEAKER_02.wav 단일 파일로 학습 데이터셋 준비
- 3-12초 청크로 분할
- Whisper로 전사
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

# 경로 설정
sys.path.insert(0, '/home/nexus/connect/server/finetune/Qwen3-TTS')

SOURCE_AUDIO = "/home/nexus/connect/server/sample/SPEAKER_02.wav"
OUTPUT_DIR = "/home/nexus/connect/server/finetune/data_v3"
CHUNK_MIN_SEC = 3.0
CHUNK_MAX_SEC = 12.0
SAMPLE_RATE = 24000

def load_and_resample(audio_path: str) -> tuple:
    """오디오 로드 및 24kHz 리샘플링"""
    import librosa
    audio, sr = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)
    return audio, sr

def split_audio_by_silence(audio: np.ndarray, sr: int) -> list:
    """무음 기반으로 오디오 청크 분할"""
    import librosa

    # 무음 구간 탐지
    intervals = librosa.effects.split(audio, top_db=25, frame_length=2048, hop_length=512)

    chunks = []
    current_chunk_start = 0
    current_chunk_end = 0

    for start, end in intervals:
        segment_duration = (end - start) / sr
        current_duration = (current_chunk_end - current_chunk_start) / sr if current_chunk_end > current_chunk_start else 0

        # 현재 청크에 추가했을 때 최대 길이 초과하면 저장하고 새로 시작
        if current_duration + segment_duration > CHUNK_MAX_SEC and current_duration >= CHUNK_MIN_SEC:
            chunks.append((current_chunk_start, current_chunk_end))
            current_chunk_start = start
            current_chunk_end = end
        else:
            if current_chunk_start == 0 and current_chunk_end == 0:
                current_chunk_start = start
            current_chunk_end = end

    # 마지막 청크 추가
    if (current_chunk_end - current_chunk_start) / sr >= CHUNK_MIN_SEC:
        chunks.append((current_chunk_start, current_chunk_end))

    return chunks

def main():
    print("=" * 60)
    print("SPEAKER_02.wav 데이터셋 준비")
    print("=" * 60)

    # 출력 디렉토리 생성
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    chunks_dir = os.path.join(OUTPUT_DIR, "chunks")
    os.makedirs(chunks_dir, exist_ok=True)

    # 1. 오디오 로드
    print(f"\n[1] Loading audio: {SOURCE_AUDIO}")
    audio, sr = load_and_resample(SOURCE_AUDIO)
    duration = len(audio) / sr
    print(f"    Duration: {duration:.1f}s, Sample rate: {sr}Hz")

    # 2. 청크 분할
    print(f"\n[2] Splitting into {CHUNK_MIN_SEC}-{CHUNK_MAX_SEC}s chunks...")
    chunks = split_audio_by_silence(audio, sr)
    print(f"    Found {len(chunks)} chunks")

    # 3. 청크 저장
    print(f"\n[3] Saving chunks...")
    chunk_files = []
    for i, (start, end) in enumerate(chunks):
        chunk_audio = audio[start:end]
        chunk_duration = len(chunk_audio) / sr
        chunk_path = os.path.join(chunks_dir, f"chunk_{i:03d}.wav")
        sf.write(chunk_path, chunk_audio, sr)
        chunk_files.append((chunk_path, chunk_duration))
        print(f"    chunk_{i:03d}.wav: {chunk_duration:.2f}s")

    # 4. Whisper 전사
    print(f"\n[4] Transcribing with Whisper...")
    whisper = WhisperModel("large-v3", device="cuda", compute_type="float16")

    transcriptions = []
    for chunk_path, chunk_duration in chunk_files:
        segments, info = whisper.transcribe(
            chunk_path,
            language="ko",
            beam_size=5,
            vad_filter=True
        )
        text = " ".join([s.text.strip() for s in segments])
        transcriptions.append(text)
        print(f"    {os.path.basename(chunk_path)}: {text[:50]}...")

    # 5. Audio codes 생성
    print(f"\n[5] Generating audio codes...")
    from qwen_tts import Qwen3TTSTokenizer

    # 12Hz 토크나이저 로드
    tokenizer = Qwen3TTSTokenizer.from_pretrained(
        "Qwen/Qwen3-TTS-Tokenizer-12Hz",
        device_map="cuda:0",
    )

    # 학습 데이터 생성
    train_data = []
    for i, ((chunk_path, chunk_duration), text) in enumerate(zip(chunk_files, transcriptions)):
        if not text.strip():
            print(f"    Skipping chunk_{i:03d} (no transcription)")
            continue

        # 오디오 코드 생성 (파일 경로로 직접 인코딩)
        enc = tokenizer.encode(chunk_path)
        codes_list = enc.audio_codes[0].cpu().tolist()

        train_item = {
            "audio_path": chunk_path,
            "text": text,
            "speaker": "gd",
            "language": "Korean",
            "audio_codes": codes_list,
            "duration": chunk_duration
        }
        train_data.append(train_item)
        print(f"    chunk_{i:03d}: {len(codes_list)} codes, {len(text)} chars")

    # 6. JSONL 저장
    jsonl_path = os.path.join(OUTPUT_DIR, "gd_speaker02_train.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"\n" + "=" * 60)
    print(f"Dataset prepared!")
    print(f"  Total samples: {len(train_data)}")
    print(f"  Total duration: {sum(d for _, d in chunk_files):.1f}s")
    print(f"  Output: {jsonl_path}")
    print("=" * 60)

    return jsonl_path

if __name__ == "__main__":
    main()
