#!/bin/bash
# GD Voice v4 Training - Optimized Hyperparameters
# 데이터: 268 train samples (~56분)
# 하이퍼파라미터 최적화:
#   - LR: 1e-6 (더 안정적)
#   - Epochs: 100 (더 많은 데이터로 충분한 학습)
#   - Gradient Accumulation: 4 (effective batch=8)

cd /home/nexus/connect/server/finetune/Qwen3-TTS/finetuning

python sft_12hz_wandb.py \
    --init_model_path "Qwen/Qwen3-TTS-12Hz-1.7B-Base" \
    --output_model_path "/home/nexus/connect/server/finetune/models/gd-voice-v4" \
    --train_jsonl "/home/nexus/connect/server/finetune/data_v4/gd_train.jsonl" \
    --batch_size 2 \
    --lr 1e-6 \
    --num_epochs 100 \
    --speaker_name "gd" \
    --save_every 20 \
    --wandb_project "gd-voice-finetune" \
    --wandb_run_name "gd-v4-full-lr1e6-ep100" \
    2>&1 | tee /home/nexus/connect/server/finetune/logs/train_v4.log
