#!/bin/bash
# GD Voice v7 Training - Aggressive Learning
#
# 이전 결과:
# - v5: Loss 9.38 (LR 5e-7, 150ep) - 좋은 품질
# - v6: Loss 8.62 (LR 8e-7, 300ep) - 개선 불분명
#
# v7 전략: 더 강한 학습
# - LR: 2e-6 (v6의 2.5배)
# - Epochs: 500
# - 목표: Loss 7.x대

cd /home/nexus/connect/server/finetune/Qwen3-TTS/finetuning

nohup python sft_12hz_wandb.py \
    --init_model_path "Qwen/Qwen3-TTS-12Hz-1.7B-Base" \
    --output_model_path "/home/nexus/connect/server/finetune/models/gd-voice-v7" \
    --train_jsonl "/home/nexus/connect/server/finetune/data_v5/gd_train.jsonl" \
    --batch_size 2 \
    --lr 2e-6 \
    --num_epochs 500 \
    --speaker_name "gd" \
    --save_every 100 \
    --wandb_project "gd-voice-finetune" \
    --wandb_run_name "gd-v7-lr2e6-ep500" \
    > /home/nexus/connect/server/finetune/logs/train_v7.log 2>&1 &

echo "Training started with PID: $!"
echo "Log: /home/nexus/connect/server/finetune/logs/train_v7.log"
echo "W&B: Check wandb.ai/gybryce/gd-voice-finetune"
echo ""
echo "Settings:"
echo "  LR: 2e-6 (aggressive)"
echo "  Epochs: 500"
echo "  Target Loss: < 8.0"
