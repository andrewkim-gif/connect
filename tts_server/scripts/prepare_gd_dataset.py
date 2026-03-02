#!/usr/bin/env python3
"""
GD Voice Fine-Tuning 데이터셋 준비 스크립트

Usage:
    python prepare_gd_dataset.py --input_dir ./sample --output_jsonl gd_train.jsonl

이 스크립트는:
1. 오디오 파일을 24kHz mono로 변환
2. Whisper로 트랜스크립션 생성
3. 긴 오디오를 청크로 분할
4. Fine-tuning용 JSONL 생성
"""

import os
import json
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class AudioSegment:
    """오디오 세그먼트 정보"""
    path: str
    text: str
    start: float
    end: float
    duration: float


def convert_to_24k_mono(input_path: str, output_path: str) -> bool:
    """오디오를 24kHz mono로 변환"""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-ar", "24000", "-ac", "1",
        "-acodec", "pcm_s16le",
        output_path
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"변환 실패: {input_path} -> {e}")
        return False


def transcribe_audio(audio_path: str, language: str = "ko") -> Optional[Dict[str, Any]]:
    """Whisper로 오디오 트랜스크립션"""
    try:
        import whisper

        model = whisper.load_model("large-v3")
        result = model.transcribe(
            audio_path,
            language=language,
            word_timestamps=True,
        )
        return result
    except ImportError:
        print("whisper 패키지가 설치되지 않았습니다. pip install openai-whisper")
        return None
    except Exception as e:
        print(f"트랜스크립션 실패: {audio_path} -> {e}")
        return None


def split_audio_by_segments(
    audio_path: str,
    segments: List[Dict],
    output_dir: str,
    min_duration: float = 3.0,
    max_duration: float = 15.0,
) -> List[AudioSegment]:
    """세그먼트 기반으로 오디오 분할"""
    results = []
    base_name = Path(audio_path).stem

    current_text = ""
    current_start = 0
    current_end = 0
    segment_idx = 0

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
                # 현재까지의 청크 저장
                if current_end - current_start >= min_duration:
                    output_path = os.path.join(
                        output_dir,
                        f"{base_name}_{segment_idx:04d}.wav"
                    )

                    cmd = [
                        "ffmpeg", "-y", "-i", audio_path,
                        "-ss", str(current_start),
                        "-to", str(current_end),
                        "-ar", "24000", "-ac", "1",
                        output_path
                    ]
                    subprocess.run(cmd, capture_output=True, check=True)

                    results.append(AudioSegment(
                        path=output_path,
                        text=current_text.strip(),
                        start=current_start,
                        end=current_end,
                        duration=current_end - current_start,
                    ))
                    segment_idx += 1

                # 새 청크 시작
                current_start = seg_start
                current_text = seg_text
                current_end = seg_end
            else:
                # 현재 청크에 추가
                current_text += " " + seg_text
                current_end = seg_end

    # 마지막 청크 저장
    if current_text and (current_end - current_start >= min_duration):
        output_path = os.path.join(
            output_dir,
            f"{base_name}_{segment_idx:04d}.wav"
        )

        cmd = [
            "ffmpeg", "-y", "-i", audio_path,
            "-ss", str(current_start),
            "-to", str(current_end),
            "-ar", "24000", "-ac", "1",
            output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)

        results.append(AudioSegment(
            path=output_path,
            text=current_text.strip(),
            start=current_start,
            end=current_end,
            duration=current_end - current_start,
        ))

    return results


def find_best_reference(segments: List[AudioSegment]) -> Optional[str]:
    """가장 적합한 레퍼런스 오디오 선택 (5-10초, 깨끗한 발음)"""
    candidates = [s for s in segments if 5.0 <= s.duration <= 10.0]
    if not candidates:
        candidates = segments

    # 중간 길이 선호
    candidates.sort(key=lambda x: abs(x.duration - 7.5))
    return candidates[0].path if candidates else None


def generate_jsonl(
    segments: List[AudioSegment],
    ref_audio: str,
    output_path: str,
) -> int:
    """Fine-tuning용 JSONL 생성"""
    count = 0

    with open(output_path, 'w', encoding='utf-8') as f:
        for seg in segments:
            entry = {
                "audio": seg.path,
                "text": seg.text,
                "ref_audio": ref_audio,
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            count += 1

    return count


def main():
    parser = argparse.ArgumentParser(description="GD Voice Fine-Tuning 데이터셋 준비")
    parser.add_argument("--input_dir", type=str, required=True,
                        help="입력 오디오 디렉토리")
    parser.add_argument("--output_dir", type=str, default="./data/gd_processed",
                        help="출력 디렉토리")
    parser.add_argument("--output_jsonl", type=str, default="gd_train.jsonl",
                        help="출력 JSONL 파일")
    parser.add_argument("--ref_audio", type=str, default=None,
                        help="레퍼런스 오디오 경로 (자동 선택 시 생략)")
    parser.add_argument("--language", type=str, default="ko",
                        help="트랜스크립션 언어")
    parser.add_argument("--min_duration", type=float, default=3.0,
                        help="최소 청크 길이 (초)")
    parser.add_argument("--max_duration", type=float, default=15.0,
                        help="최대 청크 길이 (초)")

    args = parser.parse_args()

    # 출력 디렉토리 생성
    os.makedirs(args.output_dir, exist_ok=True)

    # 오디오 파일 찾기
    input_dir = Path(args.input_dir)
    audio_files = list(input_dir.glob("*.wav")) + list(input_dir.glob("*.mp3"))

    if not audio_files:
        print(f"오디오 파일을 찾을 수 없습니다: {args.input_dir}")
        return

    print(f"발견된 오디오 파일: {len(audio_files)}")

    all_segments = []

    for audio_file in audio_files:
        print(f"\n처리 중: {audio_file.name}")

        # 24kHz mono 변환
        converted_path = os.path.join(args.output_dir, f"converted_{audio_file.stem}.wav")
        if not convert_to_24k_mono(str(audio_file), converted_path):
            continue

        # 트랜스크립션
        print("  트랜스크립션 중...")
        result = transcribe_audio(converted_path, args.language)
        if not result:
            continue

        print(f"  전체 텍스트: {result['text'][:100]}...")

        # 세그먼트 분할
        if "segments" in result:
            print(f"  세그먼트 분할 중... ({len(result['segments'])} 세그먼트)")
            segments = split_audio_by_segments(
                converted_path,
                result["segments"],
                args.output_dir,
                args.min_duration,
                args.max_duration,
            )
            all_segments.extend(segments)
            print(f"  생성된 청크: {len(segments)}")
        else:
            # 세그먼트 없으면 전체를 하나의 청크로
            all_segments.append(AudioSegment(
                path=converted_path,
                text=result["text"],
                start=0,
                end=0,
                duration=0,
            ))

    if not all_segments:
        print("생성된 세그먼트가 없습니다.")
        return

    # 레퍼런스 오디오 선택
    ref_audio = args.ref_audio
    if not ref_audio:
        ref_audio = find_best_reference(all_segments)
        if ref_audio:
            print(f"\n자동 선택된 레퍼런스: {ref_audio}")

    if not ref_audio:
        print("레퍼런스 오디오를 선택할 수 없습니다.")
        return

    # JSONL 생성
    output_jsonl = os.path.join(args.output_dir, args.output_jsonl)
    count = generate_jsonl(all_segments, ref_audio, output_jsonl)

    print(f"\n=== 완료 ===")
    print(f"총 세그먼트: {count}")
    print(f"총 시간: {sum(s.duration for s in all_segments):.1f}초")
    print(f"레퍼런스: {ref_audio}")
    print(f"출력 JSONL: {output_jsonl}")

    # 다음 단계 안내
    print(f"""
=== 다음 단계 ===

1. 오디오 코드 추출:
   python prepare_data.py \\
     --device cuda:0 \\
     --tokenizer_model_path Qwen/Qwen3-TTS-Tokenizer-12Hz \\
     --input_jsonl {output_jsonl} \\
     --output_jsonl gd_train_codes.jsonl

2. Fine-Tuning:
   python sft_12hz.py \\
     --init_model_path Qwen/Qwen3-TTS-12Hz-1.7B-Base \\
     --output_model_path ./models/gd-voice \\
     --train_jsonl gd_train_codes.jsonl \\
     --batch_size 2 \\
     --lr 2e-5 \\
     --num_epochs 10 \\
     --speaker_name gd
""")


if __name__ == "__main__":
    main()
