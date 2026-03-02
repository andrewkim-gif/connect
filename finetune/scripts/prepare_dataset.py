#!/usr/bin/env python3
"""
GD Voice Fine-Tuning 데이터셋 준비 스크립트
Qwen3-TTS 공식 fine-tuning 형식에 맞춰 데이터 생성
"""

import os
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple
import whisper
import torch


@dataclass
class AudioChunk:
    """오디오 청크 정보"""
    path: str
    text: str
    start: float
    end: float
    duration: float


def convert_to_24k_mono(input_path: str, output_path: str) -> bool:
    """오디오를 24kHz mono PCM으로 변환"""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-ar", "24000", "-ac", "1",
        "-acodec", "pcm_s16le",
        output_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ 변환 실패: {e.stderr.decode()[:200]}")
        return False


def get_audio_duration(path: str) -> float:
    """오디오 길이 가져오기"""
    cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
           "-of", "csv=p=0", path]
    try:
        result = subprocess.run(cmd, capture_output=True, check=True)
        return float(result.stdout.decode().strip())
    except:
        return 0.0


def split_audio_segment(
    input_path: str,
    output_path: str,
    start: float,
    end: float
) -> bool:
    """오디오 세그먼트 추출"""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-ss", str(start), "-to", str(end),
        "-ar", "24000", "-ac", "1",
        "-acodec", "pcm_s16le",
        output_path
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except:
        return False


def transcribe_audio(
    model: whisper.Whisper,
    audio_path: str,
    language: str = "ko"
) -> Optional[dict]:
    """Whisper로 전사"""
    try:
        result = model.transcribe(
            audio_path,
            language=language,
            word_timestamps=True,
            verbose=False,
        )
        return result
    except Exception as e:
        print(f"  ❌ 전사 실패: {e}")
        return None


def create_chunks_from_segments(
    audio_path: str,
    segments: List[dict],
    output_dir: str,
    base_name: str,
    min_duration: float = 3.0,
    max_duration: float = 12.0,
) -> List[AudioChunk]:
    """세그먼트를 청크로 분할"""
    chunks = []

    current_text = ""
    current_start = 0.0
    current_end = 0.0
    chunk_idx = 0

    for seg in segments:
        seg_start = seg.get("start", 0)
        seg_end = seg.get("end", 0)
        seg_text = seg.get("text", "").strip()

        if not seg_text:
            continue

        if not current_text:
            current_start = seg_start
            current_text = seg_text
            current_end = seg_end
        else:
            potential_duration = seg_end - current_start

            if potential_duration > max_duration:
                # 현재 청크 저장
                if current_end - current_start >= min_duration:
                    output_path = os.path.join(
                        output_dir, f"{base_name}_{chunk_idx:04d}.wav"
                    )

                    if split_audio_segment(audio_path, output_path, current_start, current_end):
                        chunks.append(AudioChunk(
                            path=output_path,
                            text=current_text.strip(),
                            start=current_start,
                            end=current_end,
                            duration=current_end - current_start,
                        ))
                        chunk_idx += 1

                # 새 청크 시작
                current_start = seg_start
                current_text = seg_text
                current_end = seg_end
            else:
                current_text += " " + seg_text
                current_end = seg_end

    # 마지막 청크
    if current_text and (current_end - current_start >= min_duration):
        output_path = os.path.join(output_dir, f"{base_name}_{chunk_idx:04d}.wav")
        if split_audio_segment(audio_path, output_path, current_start, current_end):
            chunks.append(AudioChunk(
                path=output_path,
                text=current_text.strip(),
                start=current_start,
                end=current_end,
                duration=current_end - current_start,
            ))

    return chunks


def find_best_reference(chunks: List[AudioChunk]) -> Optional[str]:
    """가장 적합한 레퍼런스 선택 (5-10초, 깨끗한 발음)"""
    candidates = [c for c in chunks if 5.0 <= c.duration <= 10.0]
    if not candidates:
        candidates = [c for c in chunks if c.duration >= 3.0]
    if not candidates:
        return None

    # 중간 길이 선호
    candidates.sort(key=lambda x: abs(x.duration - 7.5))
    return candidates[0].path


def main():
    print("=" * 60)
    print("🎤 GD Voice Fine-Tuning 데이터셋 준비")
    print("=" * 60)

    # 경로 설정
    sample_dir = Path("/home/nexus/connect/server/sample")
    output_dir = Path("/home/nexus/connect/server/finetune/data")
    chunks_dir = output_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    # Whisper 모델 로드
    print("\n📥 Whisper 모델 로딩 중...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"   Device: {device}")
    whisper_model = whisper.load_model("large-v3", device=device)
    print("   ✅ Whisper 로드 완료")

    # 오디오 파일 찾기
    audio_files = list(sample_dir.glob("*.wav"))
    print(f"\n📁 발견된 오디오: {len(audio_files)} 파일")

    all_chunks = []
    total_duration = 0.0

    for audio_file in sorted(audio_files):
        duration = get_audio_duration(str(audio_file))
        print(f"\n🎵 처리: {audio_file.name} ({duration:.1f}초)")

        # 변환된 파일 경로
        converted_path = chunks_dir / f"converted_{audio_file.stem}.wav"

        # 24kHz mono 변환
        print("   → 24kHz mono 변환 중...")
        if not convert_to_24k_mono(str(audio_file), str(converted_path)):
            continue

        # Whisper 전사
        print("   → Whisper 전사 중...")
        result = transcribe_audio(whisper_model, str(converted_path))
        if not result:
            continue

        print(f"   → 텍스트: {result['text'][:80]}...")

        # 세그먼트 분할
        if "segments" in result and result["segments"]:
            print(f"   → 청크 분할 중... ({len(result['segments'])} 세그먼트)")
            chunks = create_chunks_from_segments(
                str(converted_path),
                result["segments"],
                str(chunks_dir),
                audio_file.stem,
                min_duration=3.0,
                max_duration=12.0,
            )
            all_chunks.extend(chunks)
            chunk_duration = sum(c.duration for c in chunks)
            total_duration += chunk_duration
            print(f"   ✅ {len(chunks)} 청크 생성 ({chunk_duration:.1f}초)")
        else:
            # 세그먼트 없으면 전체를 하나의 청크로
            if duration >= 3.0:
                all_chunks.append(AudioChunk(
                    path=str(converted_path),
                    text=result["text"],
                    start=0,
                    end=duration,
                    duration=duration,
                ))
                total_duration += duration
                print(f"   ✅ 단일 청크 생성 ({duration:.1f}초)")

    if not all_chunks:
        print("\n❌ 생성된 청크가 없습니다!")
        return

    # 레퍼런스 오디오 선택
    ref_audio = find_best_reference(all_chunks)
    if not ref_audio:
        ref_audio = all_chunks[0].path

    print(f"\n📌 레퍼런스 오디오: {Path(ref_audio).name}")

    # JSONL 생성
    jsonl_path = output_dir / "gd_train.jsonl"
    with open(jsonl_path, 'w', encoding='utf-8') as f:
        for chunk in all_chunks:
            entry = {
                "audio": chunk.path,
                "text": chunk.text,
                "ref_audio": ref_audio,
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # 결과 요약
    print("\n" + "=" * 60)
    print("✅ 데이터셋 준비 완료!")
    print("=" * 60)
    print(f"   총 청크: {len(all_chunks)}")
    print(f"   총 시간: {total_duration:.1f}초 ({total_duration/60:.1f}분)")
    print(f"   레퍼런스: {Path(ref_audio).name}")
    print(f"   JSONL: {jsonl_path}")

    # 샘플 출력
    print("\n📝 샘플 데이터 (처음 3개):")
    for i, chunk in enumerate(all_chunks[:3]):
        print(f"   [{i+1}] {Path(chunk.path).name}")
        print(f"       텍스트: {chunk.text[:50]}...")
        print(f"       길이: {chunk.duration:.1f}초")

    print(f"""
🚀 다음 단계:

1. 오디오 코드 추출:
   cd /home/nexus/connect/server/finetune
   python -m qwen_tts.finetuning.prepare_data \\
     --device cuda:0 \\
     --tokenizer_model_path Qwen/Qwen3-TTS-Tokenizer-12Hz \\
     --input_jsonl {jsonl_path} \\
     --output_jsonl data/gd_train_codes.jsonl

2. Fine-Tuning 실행:
   python -m qwen_tts.finetuning.sft_12hz \\
     --init_model_path Qwen/Qwen3-TTS-12Hz-1.7B-Base \\
     --output_model_path models/gd-voice \\
     --train_jsonl data/gd_train_codes.jsonl \\
     --batch_size 2 \\
     --lr 2e-5 \\
     --num_epochs 10 \\
     --speaker_name gd
""")


if __name__ == "__main__":
    main()
