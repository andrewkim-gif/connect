# coding=utf-8
# Copyright 2026 Davinci Voice Team.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
DavinciVoiceModel: Wrapper around Qwen3TTSModel for Davinci Voice branding.

This module provides a rebranded interface while using the underlying
Qwen3-TTS implementation for actual TTS synthesis.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import torch

# Import the underlying Qwen3-TTS implementation
from qwen_tts import Qwen3TTSModel as _Qwen3TTSModel
from qwen_tts import VoiceClonePromptItem

# Re-export VoiceClonePromptItem for convenience
__all__ = ["DavinciVoiceModel", "VoiceClonePromptItem"]

# Model name mapping: davinci-voice -> Qwen3-TTS
MODEL_MAPPING = {
    # HuggingFace repo names
    "andrewkim80/davinci-voice": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    "andrewkim80/davinci-voice-voicedesign": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
    # Legacy/alias names
    "davinci-voice/davinci-voice-12Hz-1.7B-Base": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    "davinci-voice/davinci-voice-12Hz-1.7B-VoiceDesign": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
    "davinci-voice/davinci-voice-12Hz-0.6B-Base": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
}


class DavinciVoiceModel:
    """
    DavinciVoiceModel: A HuggingFace-style wrapper for Davinci Voice TTS.

    This is a rebranded wrapper around Qwen3TTSModel that provides:
      - from_pretrained() initialization
      - Voice cloning APIs
      - Consistent output format: (wavs: List[np.ndarray], sample_rate: int)

    Usage:
        model = DavinciVoiceModel.from_pretrained(
            "davinci-voice/davinci-voice-12Hz-1.7B-Base",
            device_map="cuda:0",
            dtype=torch.bfloat16,
        )

        # Voice cloning
        audio, sr = model.generate_voice_clone(
            text="안녕하세요",
            ref_audio="path/to/reference.wav",
        )
    """

    def __init__(self, qwen_model: _Qwen3TTSModel):
        """Initialize with underlying Qwen3TTSModel."""
        self._model = qwen_model
        self.model = qwen_model.model
        self.processor = qwen_model.processor
        self.device = qwen_model.device
        self.generate_defaults = qwen_model.generate_defaults

    @classmethod
    def from_pretrained(
        cls,
        pretrained_model_name_or_path: str,
        **kwargs,
    ) -> "DavinciVoiceModel":
        """
        Load a Davinci Voice model in HuggingFace `from_pretrained` style.

        Args:
            pretrained_model_name_or_path: Model name or path.
                - "davinci-voice/davinci-voice-12Hz-1.7B-Base" (recommended)
                - "davinci-voice/davinci-voice-12Hz-1.7B-VoiceDesign"
                - Or any Qwen3-TTS compatible model path
            **kwargs: Additional arguments passed to the underlying model.
                - device_map: Device to load model on (e.g., "cuda:0")
                - dtype: Model precision (e.g., torch.bfloat16)
                - attn_implementation: Attention implementation (e.g., "flash_attention_2")

        Returns:
            DavinciVoiceModel instance ready for inference.
        """
        # Map davinci-voice model names to Qwen3-TTS
        actual_model_path = MODEL_MAPPING.get(
            pretrained_model_name_or_path,
            pretrained_model_name_or_path
        )

        # Load the underlying Qwen3TTSModel
        qwen_model = _Qwen3TTSModel.from_pretrained(actual_model_path, **kwargs)

        return cls(qwen_model)

    def generate_voice_clone(
        self,
        text: Union[str, List[str]],
        ref_audio: Optional[str] = None,
        ref_text: Optional[str] = None,
        x_vector_only_mode: bool = True,
        voice_clone_prompt: Optional[VoiceClonePromptItem] = None,
        language: Optional[str] = None,
        **generate_kwargs,
    ) -> Tuple[List[np.ndarray], int]:
        """
        Generate speech with voice cloning.

        Args:
            text: Text to synthesize (single string or list).
            ref_audio: Path to reference audio file for voice cloning.
            ref_text: Optional transcript of reference audio (enables ICL mode).
            x_vector_only_mode: Use x-vector only mode (faster, default True).
            voice_clone_prompt: Pre-computed voice clone prompt for faster generation.
            language: Target language (e.g., "Korean", "English").
            **generate_kwargs: Additional generation parameters.

        Returns:
            Tuple of (audio_list, sample_rate):
                - audio_list: List of numpy arrays containing audio waveforms
                - sample_rate: Audio sample rate (typically 24000)
        """
        return self._model.generate_voice_clone(
            text=text,
            ref_audio=ref_audio,
            ref_text=ref_text,
            x_vector_only_mode=x_vector_only_mode,
            voice_clone_prompt=voice_clone_prompt,
            language=language,
            **generate_kwargs,
        )

    def create_voice_clone_prompt(
        self,
        ref_audio: str,
        ref_text: Optional[str] = None,
        x_vector_only_mode: bool = True,
    ) -> VoiceClonePromptItem:
        """
        Create a reusable voice clone prompt from reference audio.

        This is useful for generating multiple outputs with the same voice,
        as the prompt only needs to be computed once.

        Args:
            ref_audio: Path to reference audio file.
            ref_text: Optional transcript of reference audio.
            x_vector_only_mode: Use x-vector only mode.

        Returns:
            VoiceClonePromptItem that can be passed to generate_voice_clone().
        """
        return self._model.create_voice_clone_prompt(
            ref_audio=ref_audio,
            ref_text=ref_text,
            x_vector_only_mode=x_vector_only_mode,
        )

    def generate_voice_design(
        self,
        text: Union[str, List[str]],
        voice_description: str,
        language: Optional[str] = None,
        **generate_kwargs,
    ) -> Tuple[List[np.ndarray], int]:
        """
        Generate speech with voice design (prosody/emotion control).

        Args:
            text: Text to synthesize.
            voice_description: Natural language description of desired voice.
            language: Target language.
            **generate_kwargs: Additional generation parameters.

        Returns:
            Tuple of (audio_list, sample_rate).
        """
        return self._model.generate_voice_design(
            text=text,
            voice_description=voice_description,
            language=language,
            **generate_kwargs,
        )

    def generate_custom_voice(
        self,
        text: Union[str, List[str]],
        speaker: str,
        language: Optional[str] = None,
        **generate_kwargs,
    ) -> Tuple[List[np.ndarray], int]:
        """
        Generate speech with a pre-defined custom voice.

        Args:
            text: Text to synthesize.
            speaker: Pre-defined speaker ID.
            language: Target language.
            **generate_kwargs: Additional generation parameters.

        Returns:
            Tuple of (audio_list, sample_rate).
        """
        return self._model.generate_custom_voice(
            text=text,
            speaker=speaker,
            language=language,
            **generate_kwargs,
        )

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return self._model.model.get_supported_languages()

    def get_supported_speakers(self) -> List[str]:
        """Get list of supported speakers (for custom voice mode)."""
        return self._model.model.get_supported_speakers()

    @property
    def sample_rate(self) -> int:
        """Get the model's output sample rate."""
        return 24000  # Qwen3-TTS uses 24kHz
