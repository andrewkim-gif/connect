#!/usr/bin/env python3
"""
GD Voice Similarity Analysis
원본 GD 음성과 생성된 TTS 음성의 유사도를 분석합니다.
"""

import os
import json
import numpy as np
import librosa
from pathlib import Path

# 분석 대상 파일들
ORIGINAL_CHUNKS_DIR = "/home/nexus/connect/server/finetune/data_v5/chunks"
GENERATED_DIR = "/home/nexus/connect/server/finetune/output"

def extract_features(audio_path, sr=24000):
    """음성에서 특징을 추출합니다."""
    try:
        y, sr = librosa.load(audio_path, sr=sr)

        features = {}

        # 1. MFCC (Mel-Frequency Cepstral Coefficients)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        features['mfcc_mean'] = np.mean(mfcc, axis=1).tolist()
        features['mfcc_std'] = np.std(mfcc, axis=1).tolist()

        # 2. Pitch (F0) 분석
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        pitch_values = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                pitch_values.append(pitch)

        if pitch_values:
            features['pitch_mean'] = float(np.mean(pitch_values))
            features['pitch_std'] = float(np.std(pitch_values))
            features['pitch_min'] = float(np.min(pitch_values))
            features['pitch_max'] = float(np.max(pitch_values))
        else:
            features['pitch_mean'] = 0
            features['pitch_std'] = 0
            features['pitch_min'] = 0
            features['pitch_max'] = 0

        # 3. Spectral Centroid (음색 밝기)
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        features['spectral_centroid_mean'] = float(np.mean(spectral_centroids))
        features['spectral_centroid_std'] = float(np.std(spectral_centroids))

        # 4. Spectral Bandwidth
        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
        features['spectral_bandwidth_mean'] = float(np.mean(spectral_bandwidth))
        features['spectral_bandwidth_std'] = float(np.std(spectral_bandwidth))

        # 5. RMS Energy (음량)
        rms = librosa.feature.rms(y=y)[0]
        features['rms_mean'] = float(np.mean(rms))
        features['rms_std'] = float(np.std(rms))

        # 6. Zero Crossing Rate
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        features['zcr_mean'] = float(np.mean(zcr))
        features['zcr_std'] = float(np.std(zcr))

        # 7. Duration
        features['duration'] = float(len(y) / sr)

        return features
    except Exception as e:
        print(f"Error processing {audio_path}: {e}")
        return None

def calculate_similarity(ref_features, gen_features):
    """두 음성 특징 간의 유사도를 계산합니다."""
    if ref_features is None or gen_features is None:
        return 0

    similarities = {}

    # MFCC 코사인 유사도
    ref_mfcc = np.array(ref_features['mfcc_mean'])
    gen_mfcc = np.array(gen_features['mfcc_mean'])
    mfcc_sim = np.dot(ref_mfcc, gen_mfcc) / (np.linalg.norm(ref_mfcc) * np.linalg.norm(gen_mfcc))
    similarities['mfcc_similarity'] = float(mfcc_sim)

    # Pitch 유사도 (상대적 차이)
    if ref_features['pitch_mean'] > 0 and gen_features['pitch_mean'] > 0:
        pitch_diff = abs(ref_features['pitch_mean'] - gen_features['pitch_mean']) / ref_features['pitch_mean']
        similarities['pitch_similarity'] = float(max(0, 1 - pitch_diff))
    else:
        similarities['pitch_similarity'] = 0

    # Spectral Centroid 유사도
    sc_diff = abs(ref_features['spectral_centroid_mean'] - gen_features['spectral_centroid_mean']) / ref_features['spectral_centroid_mean']
    similarities['spectral_similarity'] = float(max(0, 1 - sc_diff))

    # 전체 유사도 (가중 평균)
    weights = {'mfcc': 0.5, 'pitch': 0.3, 'spectral': 0.2}
    overall = (
        weights['mfcc'] * similarities['mfcc_similarity'] +
        weights['pitch'] * similarities['pitch_similarity'] +
        weights['spectral'] * similarities['spectral_similarity']
    )
    similarities['overall'] = float(overall)

    return similarities

def main():
    print("=" * 60)
    print("GD Voice Similarity Analysis")
    print("=" * 60)

    # 1. 원본 GD 음성 분석 (여러 청크의 평균)
    print("\n[1] 원본 GD 음성 분석...")
    original_features_list = []
    chunk_files = sorted(Path(ORIGINAL_CHUNKS_DIR).glob("chunk_*.wav"))[:10]  # 첫 10개

    for chunk_file in chunk_files:
        features = extract_features(str(chunk_file))
        if features:
            original_features_list.append(features)
            print(f"  - {chunk_file.name}: duration={features['duration']:.2f}s, pitch={features['pitch_mean']:.1f}Hz")

    if not original_features_list:
        print("Error: No original features extracted")
        return

    # 원본의 평균 특징
    ref_features = {
        'mfcc_mean': np.mean([f['mfcc_mean'] for f in original_features_list], axis=0).tolist(),
        'pitch_mean': np.mean([f['pitch_mean'] for f in original_features_list]),
        'pitch_std': np.mean([f['pitch_std'] for f in original_features_list]),
        'spectral_centroid_mean': np.mean([f['spectral_centroid_mean'] for f in original_features_list]),
    }

    print(f"\n원본 GD 음성 평균 특징:")
    print(f"  - Pitch Mean: {ref_features['pitch_mean']:.1f} Hz")
    print(f"  - Pitch Std: {ref_features['pitch_std']:.1f} Hz")
    print(f"  - Spectral Centroid: {ref_features['spectral_centroid_mean']:.1f} Hz")

    # 2. 생성된 TTS 음성 분석
    print("\n[2] 생성된 TTS 음성 분석...")

    generated_files = [
        ("v5 finetuned", f"{GENERATED_DIR}/comparison/finetuned_v5.wav"),
        ("v5 hello", f"{GENERATED_DIR}/v5_hello_gd.wav"),
        ("v5 test 1", f"{GENERATED_DIR}/v5_test/test_1.wav"),
        ("v5 test 2", f"{GENERATED_DIR}/v5_test/test_2.wav"),
        ("v5 long 1", f"{GENERATED_DIR}/v5_long_test/test_1.wav"),
        ("v5 long 2", f"{GENERATED_DIR}/v5_long_test/test_2.wav"),
        ("base clone", f"{GENERATED_DIR}/gd_baseline_clone.wav"),
        ("base zeroshot", f"{GENERATED_DIR}/comparison/base_zeroshot.wav"),
    ]

    results = []
    for name, filepath in generated_files:
        if os.path.exists(filepath):
            gen_features = extract_features(filepath)
            if gen_features:
                sim = calculate_similarity(ref_features, gen_features)
                results.append({
                    'name': name,
                    'path': filepath,
                    'features': gen_features,
                    'similarity': sim
                })
                print(f"\n  {name}:")
                print(f"    - Duration: {gen_features['duration']:.2f}s")
                print(f"    - Pitch Mean: {gen_features['pitch_mean']:.1f} Hz")
                print(f"    - MFCC Similarity: {sim['mfcc_similarity']*100:.1f}%")
                print(f"    - Pitch Similarity: {sim['pitch_similarity']*100:.1f}%")
                print(f"    - Spectral Similarity: {sim['spectral_similarity']*100:.1f}%")
                print(f"    - Overall Similarity: {sim['overall']*100:.1f}%")

    # 3. 결과 요약
    print("\n" + "=" * 60)
    print("유사도 분석 요약")
    print("=" * 60)

    print("\n샘플별 유사도:")
    print("-" * 50)
    print(f"{'샘플':<20} {'MFCC':>10} {'Pitch':>10} {'Overall':>10}")
    print("-" * 50)

    for r in sorted(results, key=lambda x: x['similarity']['overall'], reverse=True):
        sim = r['similarity']
        print(f"{r['name']:<20} {sim['mfcc_similarity']*100:>9.1f}% {sim['pitch_similarity']*100:>9.1f}% {sim['overall']*100:>9.1f}%")

    # 4. JSON 결과 저장
    output_data = {
        'original_features': ref_features,
        'results': [
            {
                'name': r['name'],
                'similarity': r['similarity'],
                'pitch_mean': r['features']['pitch_mean'],
                'duration': r['features']['duration']
            }
            for r in results
        ]
    }

    output_path = f"{GENERATED_DIR}/similarity_analysis.json"
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    print(f"\n결과 저장됨: {output_path}")

    # 5. 평균 유사도 계산
    if results:
        finetuned_results = [r for r in results if 'v5' in r['name'].lower()]
        baseline_results = [r for r in results if 'base' in r['name'].lower()]

        if finetuned_results:
            avg_finetuned = np.mean([r['similarity']['overall'] for r in finetuned_results])
            print(f"\n파인튜닝 모델 평균 유사도: {avg_finetuned*100:.1f}%")

        if baseline_results:
            avg_baseline = np.mean([r['similarity']['overall'] for r in baseline_results])
            print(f"베이스라인(클론) 평균 유사도: {avg_baseline*100:.1f}%")

if __name__ == "__main__":
    main()
