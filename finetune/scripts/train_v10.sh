#!/bin/bash
# GD Voice v10 - Regularized Training
#
# Improvements over v5:
# - Label smoothing (0.1): Prevents overconfident predictions
# - EMA speaker embedding: More stable voice representation
# - Warmup (5%): Smoother learning start
# - Gradient accumulation (8): Larger effective batch size
#
# Base: v5 settings (LR 5e-7, 150 epochs) - proven best quality

cd /home/nexus/connect/server/finetune/Qwen3-TTS/finetuning

nohup python sft_12hz_v10.py \
    --init_model_path "Qwen/Qwen3-TTS-12Hz-1.7B-Base" \
    --output_model_path "/home/nexus/connect/server/finetune/models/gd-voice-v10" \
    --train_jsonl "/home/nexus/connect/server/finetune/data_v5/gd_train.jsonl" \
    --batch_size 2 \
    --lr 5e-7 \
    --num_epochs 150 \
    --label_smoothing 0.1 \
    --warmup_ratio 0.05 \
    --grad_accum 8 \
    --speaker_name "gd" \
    --save_every 25 \
    --wandb_project "gd-voice-finetune" \
    --wandb_run_name "gd-v10-regularized" \
    > /home/nexus/connect/server/finetune/logs/train_v10.log 2>&1 &

echo "v10 Training started with PID: $!"
echo "Log: /home/nexus/connect/server/finetune/logs/train_v10.log"
echo ""
echo "v10 Improvements:"
echo "  - Label smoothing (0.1) - prevents overconfidence"
echo "  - EMA speaker embedding - stable voice representation"
echo "  - Warmup (5%) - smoother learning"
echo "  - Gradient accumulation (8) - larger effective batch"
