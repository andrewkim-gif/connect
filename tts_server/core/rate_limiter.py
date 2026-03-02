"""
Rate Limiter - Token Bucket 알고리즘 구현
"""

import time
import asyncio
import logging
from typing import Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """Token Bucket 알고리즘"""

    capacity: int  # 버킷 최대 용량
    refill_rate: float  # 초당 토큰 충전량
    tokens: float = field(default=0.0)
    last_refill: float = field(default_factory=time.time)

    def __post_init__(self):
        self.tokens = float(self.capacity)

    def consume(self, tokens: int = 1) -> bool:
        """
        토큰 소비 시도

        Returns:
            True: 토큰 사용 성공
            False: 토큰 부족 (rate limited)
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def _refill(self):
        """시간에 따라 토큰 충전"""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def time_until_available(self, tokens: int = 1) -> float:
        """다음 토큰 사용 가능까지 대기 시간 (초)"""
        self._refill()
        if self.tokens >= tokens:
            return 0.0
        needed = tokens - self.tokens
        return needed / self.refill_rate


class RateLimiter:
    """
    Rate Limiter - 클라이언트별 요청 제한

    엔드포인트별 제한:
    - synthesize: 10 req/min (GPU 집약적)
    - websocket: 30 msg/min
    - general: 60 req/min
    """

    def __init__(
        self,
        synthesize_limit: int = 10,
        websocket_limit: int = 30,
        general_limit: int = 60,
        window: int = 60,
    ):
        self.synthesize_limit = synthesize_limit
        self.websocket_limit = websocket_limit
        self.general_limit = general_limit
        self.window = window

        # 클라이언트별 버킷
        self._synthesize_buckets: Dict[str, TokenBucket] = {}
        self._websocket_buckets: Dict[str, TokenBucket] = {}
        self._general_buckets: Dict[str, TokenBucket] = {}

        # 정리 작업을 위한 락
        self._lock = asyncio.Lock()

    def _get_or_create_bucket(
        self,
        buckets: Dict[str, TokenBucket],
        client_id: str,
        capacity: int,
    ) -> TokenBucket:
        """버킷 조회 또는 생성"""
        if client_id not in buckets:
            buckets[client_id] = TokenBucket(
                capacity=capacity,
                refill_rate=capacity / self.window,
            )
        return buckets[client_id]

    def check_synthesize(self, client_id: str) -> tuple[bool, float]:
        """
        합성 요청 Rate Limit 확인

        Returns:
            (allowed, retry_after)
        """
        bucket = self._get_or_create_bucket(
            self._synthesize_buckets,
            client_id,
            self.synthesize_limit,
        )
        allowed = bucket.consume()
        retry_after = bucket.time_until_available() if not allowed else 0.0
        return allowed, retry_after

    def check_websocket(self, client_id: str) -> tuple[bool, float]:
        """WebSocket 메시지 Rate Limit 확인"""
        bucket = self._get_or_create_bucket(
            self._websocket_buckets,
            client_id,
            self.websocket_limit,
        )
        allowed = bucket.consume()
        retry_after = bucket.time_until_available() if not allowed else 0.0
        return allowed, retry_after

    def check_general(self, client_id: str) -> tuple[bool, float]:
        """일반 요청 Rate Limit 확인"""
        bucket = self._get_or_create_bucket(
            self._general_buckets,
            client_id,
            self.general_limit,
        )
        allowed = bucket.consume()
        retry_after = bucket.time_until_available() if not allowed else 0.0
        return allowed, retry_after

    async def cleanup_old_buckets(self, max_age: int = 3600):
        """오래된 버킷 정리 (1시간 이상 미사용)"""
        async with self._lock:
            now = time.time()
            for buckets in [
                self._synthesize_buckets,
                self._websocket_buckets,
                self._general_buckets,
            ]:
                to_remove = [
                    client_id
                    for client_id, bucket in buckets.items()
                    if now - bucket.last_refill > max_age
                ]
                for client_id in to_remove:
                    del buckets[client_id]

            if to_remove:
                logger.debug(f"Cleaned up {len(to_remove)} old rate limit buckets")

    def get_stats(self) -> dict:
        """Rate Limiter 통계"""
        return {
            "synthesize_clients": len(self._synthesize_buckets),
            "websocket_clients": len(self._websocket_buckets),
            "general_clients": len(self._general_buckets),
            "limits": {
                "synthesize": f"{self.synthesize_limit}/min",
                "websocket": f"{self.websocket_limit}/min",
                "general": f"{self.general_limit}/min",
            },
        }


# 싱글톤 인스턴스
rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Rate Limiter 인스턴스 반환"""
    global rate_limiter
    if rate_limiter is None:
        from config import settings

        rate_limiter = RateLimiter(
            synthesize_limit=settings.RATE_LIMIT_SYNTHESIZE,
            websocket_limit=settings.RATE_LIMIT_WEBSOCKET,
            window=settings.RATE_LIMIT_WINDOW,
        )
    return rate_limiter
