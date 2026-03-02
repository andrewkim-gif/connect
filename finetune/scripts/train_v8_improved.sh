#!/bin/bash
# GD Voice v8 Training - Improved
#
# Key improvements over v5:
# - LR: 1e-7 (v5는 5e-7, 5배 낮음)
# - Warmup: 10%
# - Early stopping: 20 epochs patience
# - Average speaker embedding (전체 데이터 평균)
# - Epochs: 100 (과적합 방지)

cd /home/nexus/connect/server/finetune/Qwen3-TTS/finetuning

nohup python sft_12hz_v8.py \
    --init_model_path "Qwen/Qwen3-TTS-12Hz-1.7B-Base" \
    --output_model_path "/home/nexus/connect/server/finetune/models/gd-voice-v8" \
    --train_jsonl "/home/nexus/connect/server/finetune/data_v5/gd_train.jsonl" \
    --batch_size 2 \
    --lr 1e-7 \
    --num_epochs 100 \
    --warmup_ratio 0.1 \
    --patience 20 \
    --speaker_name "gd" \
    --save_every 25 \
    --wandb_project "gd-voice-finetune" \
    --wandb_run_name "gd-v8-lr1e7-warmup-earlystop" \
    > /home/nexus/connect/server/finetune/logs/train_v8.log 2>&1 &

echo "Training started with PID: $!"
echo "Log: /home/nexus/connect/server/finetune/logs/train_v8.log"
echo "W&B: wandb.ai/gybryce/gd-voice-finetune"
echo ""
echo "Improvements:"
echo "  - LR: 1e-7 (5x lower than v5)"
echo "  - Warmup: 10%"
echo "  - Early stopping: 20 epochs patience"
echo "  - Average speaker embedding"
