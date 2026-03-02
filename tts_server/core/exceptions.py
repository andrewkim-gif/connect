"""
Custom Exceptions - 커스텀 예외 정의
"""

from models.response import ErrorCode


class TTSException(Exception):
    """TTS 서버 기본 예외"""

    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        detail: str | None = None,
    ):
        self.error_code = error_code
        self.message = message
        self.detail = detail
        super().__init__(message)


class VoiceNotFoundError(TTSException):
    """음성을 찾을 수 없음"""

    def __init__(self, voice_id: str):
        super().__init__(
            error_code=ErrorCode.VOICE_NOT_FOUND,
            message=f"Voice not found: {voice_id}",
            detail=f"Available voices: gd-default, gd-icl",
        )


class TextTooLongError(TTSException):
    """텍스트가 너무 김"""

    def __init__(self, length: int, max_length: int):
        super().__init__(
            error_code=ErrorCode.TEXT_TOO_LONG,
            message=f"Text exceeds maximum length",
            detail=f"Length: {length}, Max: {max_length}",
        )


class ModelError(TTSException):
    """모델 에러"""

    def __init__(self, detail: str):
        super().__init__(
            error_code=ErrorCode.MODEL_ERROR,
            message="TTS synthesis failed",
            detail=detail,
        )


class RateLimitError(TTSException):
    """Rate limit 초과"""

    def __init__(self, retry_after: int):
        super().__init__(
            error_code=ErrorCode.RATE_LIMITED,
            message="Rate limit exceeded",
            detail=f"Retry after {retry_after} seconds",
        )
