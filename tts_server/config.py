"""
TTS Server Configuration
pydantic-settings 기반 환경 변수 관리
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os


class Settings(BaseSettings):
    """TTS Server 설정"""

    # === Server ===
    HOST: str = "0.0.0.0"
    PORT: int = 5001
    DEBUG: bool = False

    # === Security ===
    # 쉼표로 구분된 API 키 문자열 (빈 문자열이면 인증 비활성화)
    API_KEYS_STR: str = ""
    CORS_ORIGINS_STR: str = "http://localhost:3000"

    @property
    def API_KEYS(self) -> List[str]:
        """API 키 목록"""
        if not self.API_KEYS_STR:
            return []
        return [k.strip() for k in self.API_KEYS_STR.split(",") if k.strip()]

    @property
    def CORS_ORIGINS(self) -> List[str]:
        """CORS origin 목록"""
        if not self.CORS_ORIGINS_STR:
            return ["http://localhost:3000"]
        return [o.strip() for o in self.CORS_ORIGINS_STR.split(",") if o.strip()]

    # === Rate Limiting ===
    RATE_LIMIT_SYNTHESIZE: int = 10  # requests per minute
    RATE_LIMIT_WEBSOCKET: int = 30  # messages per minute
    RATE_LIMIT_WINDOW: int = 60  # seconds

    # === Model ===
    # Dual model support: Fine-tuned (v5) + Base (voice clone)
    DEVICE: str = "cuda:0"
    DTYPE: str = "bfloat16"
    ATTN_IMPL: str = "flash_attention_2"

    # Fine-tuned GD Voice v5 Model (best quality, pre-trained speaker embedding)
    FINETUNED_MODEL_PATH: str = "/home/nexus/connect/server/finetune/models/gd-voice-v5/checkpoint-epoch-final"
    FINETUNED_SPEAKER: str = "gd"  # Speaker ID in fine-tuned model
    ENABLE_FINETUNED: bool = True  # Enable fine-tuned model

    # Base model (runtime voice cloning with ref audio)
    BASE_MODEL_NAME: str = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
    ENABLE_CLONE: bool = True  # Enable voice clone model

    # VoiceDesign 모델 (감정/스타일 제어용)
    VOICE_DESIGN_MODEL: str = "andrewkim80/davinci-voice-voicedesign"
    ENABLE_VOICE_DESIGN: bool = False  # Disabled by default (saves ~4GB VRAM)

    # Default model mode: "finetuned", "clone", or "auto"
    DEFAULT_MODE: str = "finetuned"

    # Legacy compatibility (deprecated, use FINETUNED_MODEL_PATH)
    MODEL_NAME: str = "/home/nexus/connect/server/finetune/models/gd-voice-v5/checkpoint-epoch-final"

    # === Voice ===
    DEFAULT_VOICE_ID: str = "gd-default"
    VOICE_SAMPLES_DIR: str = Field(
        default_factory=lambda: os.path.join(
            os.path.dirname(__file__), "data", "voices"
        )
    )
    VOICE_PROMPTS_DIR: str = Field(
        default_factory=lambda: os.path.join(
            os.path.dirname(__file__), "data", "prompts"
        )
    )
    # GD 음성 샘플 경로 (ICL 클로닝용) - 18초 샘플 v2 사용 (51s-69s 구간, 깨끗한 시작)
    GD_SAMPLE_PATH: str = "/home/nexus/connect/server/sample/gd_sample_icl.wav"

    # === 장(Jang) Voice 설정 ===
    # Fine-tuned 모델 (훈련 완료 후 활성화)
    JANG_FINETUNED_MODEL_PATH: str = "/home/nexus/connect/server/finetune/models/jang-voice-v1/checkpoint-epoch-final"
    JANG_SPEAKER: str = "jang"
    ENABLE_JANG_FINETUNED: bool = True  # Fine-tuning 완료
    # ICL 샘플 경로
    JANG_SAMPLE_PATH: str = "/home/nexus/connect/server/sample/jang_sample_icl.wav"

    # === Audio ===
    SAMPLE_RATE: int = 24000
    CHUNK_SIZE: int = 2400  # 100ms @ 24kHz
    MAX_TEXT_LENGTH: int = 500

    # === Generation Parameters (음성 품질 조절) ===
    # 샘플링 설정 - 목소리 다양성/일관성 조절
    GEN_DO_SAMPLE: bool = True  # 샘플링 사용 (True 권장)
    GEN_TOP_K: int = 50  # top-k 샘플링 (높을수록 다양)
    GEN_TOP_P: float = 0.9  # nucleus 샘플링 (0.9~0.95 권장)
    GEN_TEMPERATURE: float = 0.7  # 온도 (낮을수록 일관성 ↑, 0.6~0.8 권장)
    GEN_REPETITION_PENALTY: float = 1.1  # 반복 억제 (1.0~1.2)

    # 언어 설정 (명시적 지정)
    GEN_LANGUAGE: str = "Korean"  # Korean, English, Chinese, Japanese 등

    # === Performance ===
    WARMUP_ON_START: bool = True
    REQUEST_TIMEOUT: int = 30
    MAX_CONCURRENT_REQUESTS: int = 10

    # === Graceful Shutdown ===
    SHUTDOWN_TIMEOUT: int = 30  # seconds to wait for active requests

    # === STT (faster-whisper) ===
    STT_MODEL_SIZE: str = "large-v3"  # tiny, base, small, medium, large-v3
    STT_DEVICE: str = "cuda"
    STT_COMPUTE_TYPE: str = "float16"
    STT_LANGUAGE: str = "ko"
    STT_BEAM_SIZE: int = 5

    # === LLM (Gemini) ===
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_TEMPERATURE: float = 0.8
    GEMINI_MAX_TOKENS: int = 150  # 실시간 음성통화를 위해 짧은 응답

    # === Voice Pipeline ===
    VOICE_CALL_ENABLED: bool = True
    VOICE_CALL_MAX_AUDIO_LENGTH: int = 30  # 최대 입력 오디오 길이 (초)
    VOICE_CALL_SAMPLE_RATE_IN: int = 16000  # STT 입력 (Whisper 요구사항)
    VOICE_CALL_SAMPLE_RATE_OUT: int = 24000  # TTS 출력

    # === Streaming Pipeline (실시간 최적화 + 자연스러운 음성) ===
    VOICE_PIPELINE_STREAMING: bool = True  # 스트리밍 파이프라인 사용
    VOICE_PIPELINE_MAX_CONCURRENT_TTS: int = 3  # 동시 TTS 처리 수 (GPU 메모리 주의)
    # 청크 길이: 문장 단위로 TTS해야 자연스러운 운율 유지
    # 첫 청크는 8-15자 (빠른 응답), 이후는 이 설정 사용
    VOICE_PIPELINE_MIN_CHUNK_LENGTH: int = 10  # 최소 청크 (한 문장 최소 길이)
    VOICE_PIPELINE_MAX_CHUNK_LENGTH: int = 40  # 최대 청크 (자연스러운 문장)

    model_config = {
        "env_file": ".env",
        "env_prefix": "TTS_",
        "extra": "ignore",
    }


# 전역 설정 인스턴스
settings = Settings()
