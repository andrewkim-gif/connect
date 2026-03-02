# coding=utf-8
# Copyright 2026 Davinci Voice Team.
# SPDX-License-Identifier: Apache-2.0

"""
Core components for Davinci Voice.

Re-exports from Qwen3-TTS core for compatibility.
"""

# Re-export core components from qwen_tts
try:
    from qwen_tts.core.models import (
        Qwen3TTSConfig,
        Qwen3TTSForConditionalGeneration,
        Qwen3TTSProcessor,
    )

    # Alias for Davinci Voice branding
    DavinciVoiceConfig = Qwen3TTSConfig
    DavinciVoiceForConditionalGeneration = Qwen3TTSForConditionalGeneration
    DavinciVoiceProcessor = Qwen3TTSProcessor

    __all__ = [
        "DavinciVoiceConfig",
        "DavinciVoiceForConditionalGeneration",
        "DavinciVoiceProcessor",
    ]
except ImportError:
    # Core models may not be directly accessible
    __all__ = []
