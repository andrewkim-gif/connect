#!/usr/bin/env python3
"""
장(Jang) Voice Fine-Tuning v1
- GD v5 설정 기반
- W&B 연동
- 150 에폭, LR 5e-7
"""

import argparse
import json
import os
import shutil
import time

import torch
import wandb
from accelerate import Accelerator
from safetensors.torch import save_file
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader
from transformers import AutoConfig

import sys
sys.path.insert(0, '/home/nexus/connect/server/finetune/Qwen3-TTS')
sys.path.insert(0, '/home/nexus/connect/server/finetune/Qwen3-TTS/finetuning')

from dataset import TTSDataset
from qwen_tts.inference.qwen3_tts_model import Qwen3TTSModel

target_speaker_embedding = None


def parse_args():
    parser = argparse.ArgumentParser(description="장(Jang) Voice Fine-Tuning")

    # 모델 설정
    parser.add_argument("--init_model_path", type=str,
                       default="Qwen/Qwen3-TTS-12Hz-1.7B-Base")
    parser.add_argument("--output_model_path", type=str,
                       default="/home/nexus/connect/server/finetune/models/jang-voice-v1")

    # 데이터 설정
    parser.add_argument("--train_jsonl", type=str,
                       default="/home/nexus/connect/server/finetune/data_jang/jang_train.jsonl")
    parser.add_argument("--val_jsonl", type=str,
                       default="/home/nexus/connect/server/finetune/data_jang/jang_val.jsonl")

    # 훈련 설정 (GD v5 최적 설정)
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--lr", type=float, default=5e-7)  # GD v5 최적값
    parser.add_argument("--num_epochs", type=int, default=150)  # GD v5 최적값
    parser.add_argument("--gradient_accumulation_steps", type=int, default=4)

    # 스피커 설정
    parser.add_argument("--speaker_name", type=str, default="jang")

    # 체크포인트
    parser.add_argument("--save_every", type=int, default=50)

    # W&B 설정
    parser.add_argument("--wandb_project", type=str, default="jang-voice-finetune")
    parser.add_argument("--wandb_run_name", type=str, default=None)
    parser.add_argument("--no_wandb", action="store_true", help="Disable W&B logging")

    return parser.parse_args()


def train():
    global target_speaker_embedding

    args = parse_args()

    # W&B 초기화
    if not args.no_wandb:
        run_name = args.wandb_run_name or f"jang-v1-lr{args.lr:.0e}-ep{args.num_epochs}"
        wandb.init(
            project=args.wandb_project,
            name=run_name,
            config={
                "model": args.init_model_path,
                "batch_size": args.batch_size,
                "learning_rate": args.lr,
                "num_epochs": args.num_epochs,
                "speaker_name": args.speaker_name,
                "gradient_accumulation_steps": args.gradient_accumulation_steps,
                "train_data": args.train_jsonl,
            }
        )

    accelerator = Accelerator(
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        mixed_precision="bf16",
    )

    # 모델 로드
    accelerator.print(f"Loading model from {args.init_model_path}...")
    qwen3tts = Qwen3TTSModel.from_pretrained(
        args.init_model_path,
        torch_dtype=torch.bfloat16,
        attn_implementation="flash_attention_2",
    )
    config = AutoConfig.from_pretrained(args.init_model_path)

    # 데이터 로드
    accelerator.print(f"Loading training data from {args.train_jsonl}...")
    train_data = open(args.train_jsonl).readlines()
    train_data = [json.loads(line) for line in train_data]
    accelerator.print(f"  Train samples: {len(train_data)}")

    dataset = TTSDataset(train_data, qwen3tts.processor, config)
    train_dataloader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=dataset.collate_fn,
        num_workers=2,
        pin_memory=True,
    )

    # 옵티마이저 및 스케줄러
    optimizer = AdamW(qwen3tts.model.parameters(), lr=args.lr, weight_decay=0.01)
    total_steps = len(train_dataloader) * args.num_epochs
    scheduler = CosineAnnealingLR(optimizer, T_max=total_steps, eta_min=args.lr * 0.01)

    model, optimizer, train_dataloader, scheduler = accelerator.prepare(
        qwen3tts.model, optimizer, train_dataloader, scheduler
    )

    accelerator.print(f"\n{'='*60}")
    accelerator.print(f"장(Jang) Voice Fine-Tuning v1")
    accelerator.print(f"{'='*60}")
    accelerator.print(f"  Epochs: {args.num_epochs}")
    accelerator.print(f"  Learning Rate: {args.lr}")
    accelerator.print(f"  Batch Size: {args.batch_size}")
    accelerator.print(f"  Total Steps: {total_steps}")
    accelerator.print(f"  Speaker: {args.speaker_name}")
    accelerator.print(f"{'='*60}\n")

    model.train()
    global_step = 0
    best_loss = float('inf')
    start_time = time.time()

    for epoch in range(args.num_epochs):
        epoch_loss = 0.0
        epoch_talker_loss = 0.0
        epoch_sub_loss = 0.0
        epoch_steps = 0

        for step, batch in enumerate(train_dataloader):
            with accelerator.accumulate(model):
                input_ids = batch['input_ids']
                codec_ids = batch['codec_ids']
                ref_mels = batch['ref_mels']
                text_embedding_mask = batch['text_embedding_mask']
                codec_embedding_mask = batch['codec_embedding_mask']
                attention_mask = batch['attention_mask']
                codec_0_labels = batch['codec_0_labels']
                codec_mask = batch['codec_mask']

                # Speaker embedding 계산
                speaker_embedding = model.speaker_encoder(
                    ref_mels.to(model.device).to(model.dtype)
                ).detach()

                if target_speaker_embedding is None:
                    target_speaker_embedding = speaker_embedding

                input_text_ids = input_ids[:, :, 0]
                input_codec_ids = input_ids[:, :, 1]

                input_text_embedding = model.talker.model.text_embedding(input_text_ids) * text_embedding_mask
                input_codec_embedding = model.talker.model.codec_embedding(input_codec_ids) * codec_embedding_mask
                input_codec_embedding[:, 6, :] = speaker_embedding

                input_embeddings = input_text_embedding + input_codec_embedding

                for i in range(1, 16):
                    codec_i_embedding = model.talker.code_predictor.get_input_embeddings()[i - 1](codec_ids[:, :, i])
                    codec_i_embedding = codec_i_embedding * codec_mask.unsqueeze(-1)
                    input_embeddings = input_embeddings + codec_i_embedding

                outputs = model.talker(
                    inputs_embeds=input_embeddings[:, :-1, :],
                    attention_mask=attention_mask[:, :-1],
                    labels=codec_0_labels[:, 1:],
                    output_hidden_states=True
                )

                hidden_states = outputs.hidden_states[0][-1]
                talker_hidden_states = hidden_states[codec_mask[:, 1:]]
                talker_codec_ids = codec_ids[codec_mask]

                _, sub_talker_loss = model.talker.forward_sub_talker_finetune(
                    talker_codec_ids, talker_hidden_states
                )

                loss = outputs.loss + 0.3 * sub_talker_loss

                accelerator.backward(loss)

                if accelerator.sync_gradients:
                    accelerator.clip_grad_norm_(model.parameters(), 1.0)

                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()

                epoch_loss += loss.item()
                epoch_talker_loss += outputs.loss.item()
                epoch_sub_loss += sub_talker_loss.item()
                epoch_steps += 1
                global_step += 1

            # 로깅 (매 10 step)
            if step % 10 == 0:
                current_lr = scheduler.get_last_lr()[0]
                elapsed = time.time() - start_time
                steps_per_sec = global_step / elapsed if elapsed > 0 else 0

                accelerator.print(
                    f"Epoch {epoch+1}/{args.num_epochs} | Step {step} | "
                    f"Loss: {loss.item():.4f} | LR: {current_lr:.2e} | "
                    f"Speed: {steps_per_sec:.2f} steps/s"
                )

                if accelerator.is_main_process and not args.no_wandb:
                    wandb.log({
                        "train/loss": loss.item(),
                        "train/talker_loss": outputs.loss.item(),
                        "train/sub_talker_loss": sub_talker_loss.item(),
                        "train/learning_rate": current_lr,
                        "train/epoch": epoch,
                        "train/global_step": global_step,
                    })

        # Epoch 종료 시 평균 loss 계산
        avg_epoch_loss = epoch_loss / epoch_steps if epoch_steps > 0 else 0
        avg_talker_loss = epoch_talker_loss / epoch_steps if epoch_steps > 0 else 0
        avg_sub_loss = epoch_sub_loss / epoch_steps if epoch_steps > 0 else 0

        if accelerator.is_main_process:
            if not args.no_wandb:
                wandb.log({
                    "epoch/avg_loss": avg_epoch_loss,
                    "epoch/avg_talker_loss": avg_talker_loss,
                    "epoch/avg_sub_talker_loss": avg_sub_loss,
                    "epoch/epoch": epoch,
                })

            accelerator.print(
                f"\n=== Epoch {epoch+1} completed | "
                f"Avg Loss: {avg_epoch_loss:.4f} | "
                f"Talker: {avg_talker_loss:.4f} | "
                f"Sub: {avg_sub_loss:.4f} ===\n"
            )

        # 체크포인트 저장
        if accelerator.is_main_process and (epoch + 1) % args.save_every == 0:
            save_checkpoint(
                accelerator, model, args, epoch + 1,
                avg_epoch_loss, best_loss
            )

            if avg_epoch_loss < best_loss:
                best_loss = avg_epoch_loss
                save_checkpoint(
                    accelerator, model, args, "best",
                    avg_epoch_loss, best_loss
                )

    # 최종 모델 저장
    if accelerator.is_main_process:
        save_checkpoint(
            accelerator, model, args, "final",
            avg_epoch_loss, best_loss
        )
        accelerator.print(f"\n{'='*60}")
        accelerator.print(f"Training completed!")
        accelerator.print(f"  Best Loss: {best_loss:.4f}")
        accelerator.print(f"  Output: {args.output_model_path}")
        accelerator.print(f"{'='*60}")

    if not args.no_wandb:
        wandb.finish()


def save_checkpoint(accelerator, model, args, epoch_label, current_loss, best_loss):
    """체크포인트 저장"""
    output_dir = os.path.join(args.output_model_path, f"checkpoint-epoch-{epoch_label}")

    accelerator.print(f"Saving checkpoint to {output_dir}...")

    # HuggingFace 캐시에서 실제 경로 찾기
    from huggingface_hub import snapshot_download
    cache_dir = snapshot_download(args.init_model_path, local_files_only=True)
    shutil.copytree(cache_dir, output_dir, dirs_exist_ok=True)

    # Config 수정
    input_config_file = os.path.join(cache_dir, "config.json")
    output_config_file = os.path.join(output_dir, "config.json")
    with open(input_config_file, 'r', encoding='utf-8') as f:
        config_dict = json.load(f)

    config_dict["tts_model_type"] = "custom_voice"
    talker_config = config_dict.get("talker_config", {})
    talker_config["spk_id"] = {args.speaker_name: 3000}
    talker_config["spk_is_dialect"] = {args.speaker_name: False}
    config_dict["talker_config"] = talker_config

    with open(output_config_file, 'w', encoding='utf-8') as f:
        json.dump(config_dict, f, indent=2, ensure_ascii=False)

    # 모델 가중치 저장
    unwrapped_model = accelerator.unwrap_model(model)
    state_dict = {k: v.detach().to("cpu") for k, v in unwrapped_model.state_dict().items()}

    # Speaker encoder 제거
    keys_to_drop = [k for k in state_dict.keys() if k.startswith("speaker_encoder")]
    for k in keys_to_drop:
        del state_dict[k]

    # Speaker embedding 추가
    weight = state_dict['talker.model.codec_embedding.weight']
    state_dict['talker.model.codec_embedding.weight'][3000] = \
        target_speaker_embedding[0].detach().to(weight.device).to(weight.dtype)

    save_path = os.path.join(output_dir, "model.safetensors")
    save_file(state_dict, save_path)

    # Training info 저장
    info = {
        "epoch": str(epoch_label),
        "loss": current_loss,
        "best_loss": best_loss,
        "speaker_name": args.speaker_name,
        "learning_rate": args.lr,
        "total_epochs": args.num_epochs,
    }
    with open(os.path.join(output_dir, "training_info.json"), 'w') as f:
        json.dump(info, f, indent=2)

    accelerator.print(f"Checkpoint saved: {output_dir}")


if __name__ == "__main__":
    train()
