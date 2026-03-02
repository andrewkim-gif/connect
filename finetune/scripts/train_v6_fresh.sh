#!/bin/bash
# GD Voice v6 Training - Fresh Start with Extended Training
#
# v5 결과: Loss 9.38 (150 epochs, LR 5e-7)
# v6 목표: 더 낮은 loss 달성
#
# 변경사항:
# - 베이스 모델에서 시작 (speaker_encoder 필요)
# - LR: 8e-7 (v5보다 약간 높여서 수렴 촉진)
# - Epochs: 300 (더 충분한 학습)
# - 동일 데이터: v5 (증강 없음)

cd /home/nexus/connect/server/finetune/Qwen3-TTS/finetuning

nohup python sft_12hz_wandb.py \
    --init_model_path "Qwen/Qwen3-TTS-12Hz-1.7B-Base" \
    --output_model_path "/home/nexus/connect/server/finetune/models/gd-voice-v6" \
    --train_jsonl "/home/nexus/connect/server/finetune/data_v5/gd_train.jsonl" \
    --batch_size 2 \
    --lr 8e-7 \
    --num_epochs 300 \
    --speaker_name "gd" \
    --save_every 50 \
    --wandb_project "gd-voice-finetune" \
    --wandb_run_name "gd-v6-lr8e7-ep300" \
    > /home/nexus/connect/server/finetune/logs/train_v6.log 2>&1 &

echo "Training started with PID: $!"
echo "Log: /home/nexus/connect/server/finetune/logs/train_v6.log"
echo "W&B: Check wandb.ai/gybryce/gd-voice-finetune"
