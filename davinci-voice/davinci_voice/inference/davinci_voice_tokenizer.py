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
DavinciVoiceTokenizer: Wrapper around Qwen3TTSTokenizer.

Provides a rebranded interface for the speech tokenizer.
"""

# Import the underlying Qwen3-TTS tokenizer
from qwen_tts import Qwen3TTSTokenizer as _Qwen3TTSTokenizer

__all__ = ["DavinciVoiceTokenizer"]


class DavinciVoiceTokenizer(_Qwen3TTSTokenizer):
    """
    DavinciVoiceTokenizer: Speech tokenizer for Davinci Voice.

    This is a direct subclass of Qwen3TTSTokenizer with Davinci Voice branding.
    All functionality is inherited from the parent class.

    Usage:
        tokenizer = DavinciVoiceTokenizer.from_pretrained(
            "davinci-voice/davinci-voice-12Hz-1.7B-Base"
        )
    """
    pass
