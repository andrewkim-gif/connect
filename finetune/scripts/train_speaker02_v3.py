#!/usr/bin/env python3
"""
GD Voice Fine-Tuning v3 - SPEAKER_02.wav 단일 소스 학습
Qwen 공식 권장 설정 기반
"""

import os
import sys
import json
import torch
from pathlib import Path
from datetime import datetime

# Qwen3-TTS 경로 추가
sys.path.insert(0, '/home/nexus/connect/server/finetune/Qwen3-TTS')

import wandb
from transformers import TrainingArguments, Trainer
from qwen_tts import Qwen3TTSForConditionalGeneration, AutoProcessor

# === 설정 ===
BASE_MODEL = "andrewkim80/davinci-voice"  # 기존 davinci-voice 기반
TRAIN_DATA = "/home/nexus/connect/server/finetune/data_v3/gd_speaker02_train.jsonl"
OUTPUT_DIR = "/home/nexus/connect/server/finetune/models/gd-voice-v3"

# 하이퍼파라미터 (공식 권장 기반)
LEARNING_RATE = 2e-6  # 공식 권장
EPOCHS = 50  # 30개 샘플 × 50 epochs = 1500 steps (적당)
BATCH_SIZE = 2  # GPU 메모리 고려
WARMUP_RATIO = 0.1
WEIGHT_DECAY = 0.01

# W&B 설정
WANDB_PROJECT = "gd-voice-finetune"
WANDB_RUN_NAME = f"gd-v3-speaker02-{datetime.now().strftime('%Y%m%d_%H%M')}"


class TTSDataset(torch.utils.data.Dataset):
    """TTS 학습용 데이터셋"""

    def __init__(self, data_path: str, processor):
        self.processor = processor
        self.samples = []

        with open(data_path, 'r', encoding='utf-8') as f:
            for line in f:
                item = json.loads(line)
                self.samples.append(item)

        print(f"Loaded {len(self.samples)} samples")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]

        # 텍스트와 오디오 코드
        text = sample['text']
        audio_codes = torch.tensor(sample['audio_codes'], dtype=torch.long)
        speaker = sample['speaker']
        language = sample.get('language', 'Korean')

        # 프로세서로 인코딩
        inputs = self.processor(
            text=text,
            speaker=speaker,
            language=language,
            return_tensors="pt"
        )

        # 배치 차원 제거
        input_ids = inputs['input_ids'].squeeze(0)
        attention_mask = inputs['attention_mask'].squeeze(0)

        return {
            'input_ids': input_ids,
            'attention_mask': attention_mask,
            'labels': audio_codes,
            'speaker': speaker,
        }


def collate_fn(batch):
    """배치 collate 함수"""
    # 패딩
    max_input_len = max(len(b['input_ids']) for b in batch)
    max_label_len = max(len(b['labels']) for b in batch)

    input_ids = []
    attention_mask = []
    labels = []

    for b in batch:
        # 입력 패딩
        pad_len = max_input_len - len(b['input_ids'])
        input_ids.append(torch.cat([b['input_ids'], torch.zeros(pad_len, dtype=torch.long)]))
        attention_mask.append(torch.cat([b['attention_mask'], torch.zeros(pad_len, dtype=torch.long)]))

        # 라벨 패딩 (-100으로)
        label_pad_len = max_label_len - len(b['labels'])
        labels.append(torch.cat([b['labels'], torch.full((label_pad_len,), -100, dtype=torch.long)]))

    return {
        'input_ids': torch.stack(input_ids),
        'attention_mask': torch.stack(attention_mask),
        'labels': torch.stack(labels),
    }


def main():
    print("=" * 60)
    print("GD Voice Fine-Tuning v3")
    print("Source: SPEAKER_02.wav (single clean source)")
    print("=" * 60)

    # W&B 초기화
    wandb.init(
        project=WANDB_PROJECT,
        name=WANDB_RUN_NAME,
        config={
            "base_model": BASE_MODEL,
            "learning_rate": LEARNING_RATE,
            "epochs": EPOCHS,
            "batch_size": BATCH_SIZE,
            "train_data": TRAIN_DATA,
        }
    )

    # 출력 디렉토리 생성
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"\n[1] Loading base model: {BASE_MODEL}")

    # 모델 로드
    model = Qwen3TTSForConditionalGeneration.from_pretrained(
        BASE_MODEL,
        device_map="cuda:0",
        torch_dtype=torch.bfloat16,
        attn_implementation="flash_attention_2",
    )

    processor = AutoProcessor.from_pretrained(BASE_MODEL)

    # LoRA 또는 전체 fine-tuning 설정
    # talker 레이어만 학습 (custom voice 방식)
    for name, param in model.named_parameters():
        if "talker" in name:
            param.requires_grad = True
        else:
            param.requires_grad = False

    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"    Trainable params: {trainable_params:,} / {total_params:,} ({100*trainable_params/total_params:.2f}%)")

    print(f"\n[2] Loading dataset: {TRAIN_DATA}")
    dataset = TTSDataset(TRAIN_DATA, processor)

    print(f"\n[3] Setting up training...")

    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        learning_rate=LEARNING_RATE,
        warmup_ratio=WARMUP_RATIO,
        weight_decay=WEIGHT_DECAY,
        logging_steps=10,
        save_strategy="epoch",
        save_total_limit=3,
        report_to="wandb",
        bf16=True,
        dataloader_num_workers=2,
        remove_unused_columns=False,
        gradient_accumulation_steps=4,  # 효과적 배치 사이즈 = 8
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=collate_fn,
    )

    print(f"\n[4] Starting training...")
    print(f"    Epochs: {EPOCHS}")
    print(f"    Batch size: {BATCH_SIZE} × 4 (grad accum) = 8 effective")
    print(f"    Learning rate: {LEARNING_RATE}")
    print(f"    Total steps: ~{len(dataset) * EPOCHS // (BATCH_SIZE * 4)}")

    trainer.train()

    print(f"\n[5] Saving final model...")
    trainer.save_model(os.path.join(OUTPUT_DIR, "checkpoint-epoch-final"))
    processor.save_pretrained(os.path.join(OUTPUT_DIR, "checkpoint-epoch-final"))

    # config에 speaker 추가
    config_path = os.path.join(OUTPUT_DIR, "checkpoint-epoch-final", "config.json")
    with open(config_path, 'r') as f:
        config = json.load(f)

    # gd speaker 추가
    if "talker_config" in config:
        config["talker_config"]["spk_id"] = {"gd": 3000}
        config["talker_config"]["spk_is_dialect"] = {"gd": False}

    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    wandb.finish()

    print("\n" + "=" * 60)
    print("Training completed!")
    print(f"Model saved to: {OUTPUT_DIR}/checkpoint-epoch-final")
    print("=" * 60)


if __name__ == "__main__":
    main()
