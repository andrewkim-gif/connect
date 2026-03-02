#!/bin/bash
# GD Voice v6 Training - Continue from v5
#
# v5 결과: Loss 9.38 (좋은 품질)
# v6 목표: Loss 더 낮추기
#
# 변경사항:
# - v5 체크포인트에서 시작
# - LR: 1e-6 (v5의 5e-7보다 높여서 loss 감소 촉진)
# - 200 epochs 추가

cd /home/nexus/connect/server/finetune/Qwen3-TTS/finetuning

nohup python sft_12hz_wandb.py \
    --init_model_path "/home/nexus/connect/server/finetune/models/gd-voice-v5/checkpoint-epoch-final" \
    --output_model_path "/home/nexus/connect/server/finetune/models/gd-voice-v6" \
    --train_jsonl "/home/nexus/connect/server/finetune/data_v5/gd_train.jsonl" \
    --batch_size 2 \
    --lr 1e-6 \
    --num_epochs 200 \
    --speaker_name "gd" \
    --save_every 25 \
    --wandb_project "gd-voice-finetune" \
    --wandb_run_name "gd-v6-continue-lr1e6-ep200" \
    > /home/nexus/connect/server/finetune/logs/train_v6.log 2>&1 &

echo "Training started with PID: $!"
echo "Log: /home/nexus/connect/server/finetune/logs/train_v6.log"
echo "W&B: Check wandb.ai/gybryce/gd-voice-finetune"
