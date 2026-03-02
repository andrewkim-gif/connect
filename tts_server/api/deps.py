"""
API Dependencies - 의존성 주입 (인증, Rate Limiting)
"""

from fastapi import Header, HTTPException, status, Request
from typing import Optional

from config import settings
from core.rate_limiter import get_rate_limiter


def get_client_id(request: Request) -> str:
    """
    클라이언트 식별자 추출

    우선순위:
    1. X-API-Key 헤더 (인증된 클라이언트)
    2. X-Forwarded-For 헤더 (프록시 뒤의 실제 IP)
    3. 직접 연결 IP
    """
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"key:{api_key[:8]}"

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"

    if request.client:
        return f"ip:{request.client.host}"

    return "unknown"


async def verify_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> str:
    """
    API Key 인증

    - 헤더에서 X-API-Key 추출
    - 설정된 API_KEYS 목록과 비교
    - 개발 모드 (DEBUG=true)에서는 인증 생략 가능
    """
    # 개발 모드에서 API 키가 설정되지 않은 경우 생략
    if settings.DEBUG and not settings.API_KEYS:
        return "dev-mode"

    # API 키가 설정된 경우 검증
    if settings.API_KEYS:
        if not x_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "UNAUTHORIZED",
                    "message": "API key required",
                },
            )

        if x_api_key not in settings.API_KEYS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "UNAUTHORIZED",
                    "message": "Invalid API key",
                },
            )

        return x_api_key

    # API 키가 설정되지 않은 경우 (개발용)
    return "no-auth"


async def check_rate_limit_synthesize(request: Request) -> None:
    """
    합성 요청 Rate Limit 검사

    - 10 requests/minute per client
    - GPU 집약적 작업이므로 엄격한 제한
    """
    rate_limiter = get_rate_limiter()
    client_id = get_client_id(request)

    allowed, retry_after = rate_limiter.check_synthesize(client_id)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "RATE_LIMITED",
                "message": "Rate limit exceeded for synthesis",
                "retry_after": int(retry_after) + 1,
            },
            headers={"Retry-After": str(int(retry_after) + 1)},
        )


async def check_rate_limit_general(request: Request) -> None:
    """
    일반 요청 Rate Limit 검사

    - 60 requests/minute per client
    """
    rate_limiter = get_rate_limiter()
    client_id = get_client_id(request)

    allowed, retry_after = rate_limiter.check_general(client_id)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "RATE_LIMITED",
                "message": "Rate limit exceeded",
                "retry_after": int(retry_after) + 1,
            },
            headers={"Retry-After": str(int(retry_after) + 1)},
        )
