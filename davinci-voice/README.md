---
license: apache-2.0
language:
  - ko
  - en
  - zh
  - ja
tags:
  - tts
  - text-to-speech
  - voice-cloning
  - korean
  - speech-synthesis
pipeline_tag: text-to-speech
---

# Davinci Voice

**High-quality Korean Text-to-Speech with Voice Cloning**

Davinci Voice는 한국어에 최적화된 고품질 음성 합성 라이브러리입니다.
3초의 레퍼런스 오디오만으로 음성 클로닝이 가능하며, 실시간 스트리밍을 지원합니다.

## 특징

- 🎯 **한국어 네이티브 지원**: 한국어에 최적화된 발음과 운율
- 🎙️ **3초 음성 클로닝**: 짧은 레퍼런스로 빠른 음성 복제
- ⚡ **97ms 레이턴시**: 실시간 대화에 적합한 빠른 응답
- 🌍 **다국어 지원**: 한국어, 영어, 중국어, 일본어 등 10개 언어
- 📜 **Apache 2.0 라이선스**: 상업적 사용 가능

## 설치

\`\`\`bash
pip install davinci-voice
\`\`\`

## 빠른 시작

\`\`\`python
import torch
from davinci_voice import DavinciVoiceModel

# 모델 로드
model = DavinciVoiceModel.from_pretrained(
    "andrewkim80/davinci-voice",
    device_map="cuda:0",
    dtype=torch.bfloat16,
    attn_implementation="flash_attention_2",
)

# 음성 클로닝
audio_list, sample_rate = model.generate_voice_clone(
    text="안녕하세요, 다빈치 보이스입니다.",
    ref_audio="path/to/reference.wav",
    x_vector_only_mode=True,
)

# 저장
import soundfile as sf
sf.write("output.wav", audio_list[0], sample_rate)
\`\`\`

## 성능

| 지표 | 값 |
|-----|-----|
| TTFA (Time To First Audio) | ~97ms |
| RTF (Real-Time Factor) | < 1.0 |
| MOS (Mean Opinion Score) | 4.6 |
| WER (Word Error Rate) | 1.8% |

## 라이선스

Apache License 2.0

## 감사의 말

이 프로젝트는 [Qwen3-TTS](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base)를 기반으로 합니다.
