#!/bin/bash
# GD Voice v5 Training - Optimized
#
# 개선 사항:
# - 데이터 증강 제거 (원본 99개 샘플)
# - LR: 5e-7 (더 섬세한 학습)
# - Early stopping 효과를 위해 더 많은 epoch 관찰
# - 더 자주 체크포인트 저장

cd /home/nexus/connect/server/finetune/Qwen3-TTS/finetuning

nohup python sft_12hz_wandb.py \
    --init_model_path "Qwen/Qwen3-TTS-12Hz-1.7B-Base" \
    --output_model_path "/home/nexus/connect/server/finetune/models/gd-voice-v5" \
    --train_jsonl "/home/nexus/connect/server/finetune/data_v5/gd_train.jsonl" \
    --batch_size 2 \
    --lr 5e-7 \
    --num_epochs 150 \
    --speaker_name "gd" \
    --save_every 25 \
    --wandb_project "gd-voice-finetune" \
    --wandb_run_name "gd-v5-noaug-lr5e7-ep150" \
    > /home/nexus/connect/server/finetune/logs/train_v5.log 2>&1 &

echo "Training started with PID: $!"
echo "Log: /home/nexus/connect/server/finetune/logs/train_v5.log"
echo "W&B: Check wandb.ai/gybryce/gd-voice-finetune"
