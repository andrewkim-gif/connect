#!/bin/bash
# GD Voice v9 - v5 settings + Average Speaker Embedding
#
# v5 was the best, so we keep its settings:
# - LR: 5e-7
# - Epochs: 150
# - No augmentation
#
# Only improvement: Average speaker embedding (instead of first batch only)

cd /home/nexus/connect/server/finetune/Qwen3-TTS/finetuning

nohup python sft_12hz_v9.py \
    --init_model_path "Qwen/Qwen3-TTS-12Hz-1.7B-Base" \
    --output_model_path "/home/nexus/connect/server/finetune/models/gd-voice-v9" \
    --train_jsonl "/home/nexus/connect/server/finetune/data_v5/gd_train.jsonl" \
    --batch_size 2 \
    --lr 5e-7 \
    --num_epochs 150 \
    --speaker_name "gd" \
    --save_every 25 \
    --wandb_project "gd-voice-finetune" \
    --wandb_run_name "gd-v9-avgspk-lr5e7" \
    > /home/nexus/connect/server/finetune/logs/train_v9.log 2>&1 &

echo "v9 Training started with PID: $!"
echo "Log: /home/nexus/connect/server/finetune/logs/train_v9.log"
echo ""
echo "v9 = v5 settings + average speaker embedding"
