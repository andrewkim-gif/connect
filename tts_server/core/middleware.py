"""
Middleware - Request ID, Logging, Security Headers
"""

import uuid
import time
import logging
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Request ID 미들웨어

    - 각 요청에 고유 ID 부여
    - 요청/응답 헤더에 X-Request-ID 추가
    - 로깅에 request_id 포함
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 기존 Request ID 사용 또는 새로 생성
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())[:8]

        # request state에 저장 (다른 곳에서 접근 가능)
        request.state.request_id = request_id

        # 응답 생성
        response = await call_next(request)

        # 응답 헤더에 추가
        response.headers["X-Request-ID"] = request_id

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    요청/응답 로깅 미들웨어
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Request ID 가져오기
        request_id = getattr(request.state, "request_id", "unknown")

        # 요청 로깅
        logger.info(
            f"[{request_id}] → {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )

        # 요청 처리
        response = await call_next(request)

        # 응답 시간 계산
        process_time = (time.time() - start_time) * 1000

        # 응답 로깅
        logger.info(
            f"[{request_id}] ← {response.status_code} ({process_time:.0f}ms)"
        )

        # 응답 헤더에 처리 시간 추가
        response.headers["X-Process-Time"] = f"{process_time:.0f}ms"

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    보안 헤더 미들웨어

    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Strict-Transport-Security (HTTPS 환경에서만)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # 보안 헤더 추가
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # HTTPS 환경에서만 HSTS 추가
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response
