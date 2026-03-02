"""
WebSocket Connection Manager
활성 연결 관리, 메시지 전송, 연결 정리
"""

import uuid
import asyncio
import logging
from typing import Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


@dataclass
class ConnectionInfo:
    """WebSocket 연결 정보"""

    client_id: str
    websocket: WebSocket
    api_key: Optional[str] = None
    connected_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    messages_sent: int = 0
    messages_received: int = 0
    is_synthesizing: bool = False


class ConnectionManager:
    """
    WebSocket 연결 관리자

    기능:
    - 연결 수락 및 인증
    - 활성 연결 추적
    - 메시지/바이너리 전송
    - 연결 정리 및 종료
    - 서버 측 Heartbeat (연결 유지)
    """

    def __init__(
        self,
        max_connections: int = 100,
        heartbeat_interval: int = 30,  # 30초마다 ping
        connection_timeout: int = 300,  # 5분 무응답 시 종료
    ):
        self.max_connections = max_connections
        self.heartbeat_interval = heartbeat_interval
        self.connection_timeout = connection_timeout
        self._connections: Dict[str, ConnectionInfo] = {}
        self._lock = asyncio.Lock()
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False

    async def connect(
        self,
        websocket: WebSocket,
        api_key: Optional[str] = None,
    ) -> Optional[str]:
        """
        WebSocket 연결 수락

        Args:
            websocket: WebSocket 연결
            api_key: 인증된 API 키

        Returns:
            client_id 또는 None (연결 실패)
        """
        async with self._lock:
            # 연결 수 제한 확인
            if len(self._connections) >= self.max_connections:
                logger.warning("Maximum connections reached, rejecting new connection")
                await websocket.close(code=1013, reason="Server overloaded")
                return None

            # 연결 수락
            await websocket.accept()

            # 클라이언트 ID 생성
            client_id = str(uuid.uuid4())[:8]

            # 연결 정보 저장
            self._connections[client_id] = ConnectionInfo(
                client_id=client_id,
                websocket=websocket,
                api_key=api_key,
            )

            logger.info(
                f"[{client_id}] WebSocket connected "
                f"(total: {len(self._connections)})"
            )

            return client_id

    async def register(
        self,
        websocket: WebSocket,
        api_key: Optional[str] = None,
    ) -> Optional[str]:
        """
        이미 accept()된 WebSocket 연결 등록

        Args:
            websocket: 이미 accept()된 WebSocket 연결
            api_key: 인증된 API 키

        Returns:
            client_id 또는 None (연결 실패)
        """
        async with self._lock:
            # 연결 수 제한 확인
            if len(self._connections) >= self.max_connections:
                logger.warning("Maximum connections reached, rejecting connection")
                await websocket.close(code=1013, reason="Server overloaded")
                return None

            # 클라이언트 ID 생성
            client_id = str(uuid.uuid4())[:8]

            # 연결 정보 저장
            self._connections[client_id] = ConnectionInfo(
                client_id=client_id,
                websocket=websocket,
                api_key=api_key,
            )

            logger.info(
                f"[{client_id}] WebSocket registered "
                f"(total: {len(self._connections)})"
            )

            return client_id

    async def disconnect(self, client_id: str) -> None:
        """연결 종료 및 정리"""
        async with self._lock:
            if client_id not in self._connections:
                return

            conn = self._connections.pop(client_id)

            # 연결이 아직 열려있으면 닫기
            if conn.websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await conn.websocket.close()
                except Exception as e:
                    logger.debug(f"[{client_id}] Close error (ignored): {e}")

            duration = (datetime.now() - conn.connected_at).total_seconds()
            logger.info(
                f"[{client_id}] WebSocket disconnected "
                f"(duration: {duration:.0f}s, "
                f"sent: {conn.messages_sent}, "
                f"received: {conn.messages_received})"
            )

    async def send_json(self, client_id: str, data: dict) -> bool:
        """JSON 메시지 전송"""
        conn = self._connections.get(client_id)
        if not conn or conn.websocket.client_state != WebSocketState.CONNECTED:
            return False

        try:
            await conn.websocket.send_json(data)
            conn.messages_sent += 1
            conn.last_activity = datetime.now()
            return True
        except Exception as e:
            logger.error(f"[{client_id}] Failed to send JSON: {e}")
            return False

    async def send_bytes(self, client_id: str, data: bytes) -> bool:
        """바이너리 데이터 전송"""
        conn = self._connections.get(client_id)
        if not conn or conn.websocket.client_state != WebSocketState.CONNECTED:
            return False

        try:
            await conn.websocket.send_bytes(data)
            conn.messages_sent += 1
            conn.last_activity = datetime.now()
            return True
        except Exception as e:
            logger.error(f"[{client_id}] Failed to send bytes: {e}")
            return False

    def get_connection(self, client_id: str) -> Optional[ConnectionInfo]:
        """연결 정보 조회"""
        return self._connections.get(client_id)

    def set_synthesizing(self, client_id: str, value: bool) -> None:
        """합성 중 상태 설정"""
        conn = self._connections.get(client_id)
        if conn:
            conn.is_synthesizing = value

    def is_synthesizing(self, client_id: str) -> bool:
        """합성 중 여부 확인"""
        conn = self._connections.get(client_id)
        return conn.is_synthesizing if conn else False

    def record_received(self, client_id: str) -> None:
        """수신 메시지 카운트"""
        conn = self._connections.get(client_id)
        if conn:
            conn.messages_received += 1
            conn.last_activity = datetime.now()

    @property
    def active_count(self) -> int:
        """활성 연결 수"""
        return len(self._connections)

    @property
    def active_clients(self) -> Set[str]:
        """활성 클라이언트 ID 목록"""
        return set(self._connections.keys())

    async def start_heartbeat(self) -> None:
        """서버 측 heartbeat 시작"""
        if self._running:
            return

        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info(f"Heartbeat started (interval={self.heartbeat_interval}s, timeout={self.connection_timeout}s)")

    async def stop_heartbeat(self) -> None:
        """Heartbeat 중지"""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
        logger.info("Heartbeat stopped")

    async def _heartbeat_loop(self) -> None:
        """Heartbeat 루프 - 연결 유지 및 타임아웃 정리"""
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                if not self._running:
                    break

                now = datetime.now()
                stale_clients = []

                # 모든 연결에 ping 전송 및 타임아웃 체크
                async with self._lock:
                    for client_id, conn in list(self._connections.items()):
                        # 타임아웃 체크
                        idle_seconds = (now - conn.last_activity).total_seconds()

                        if idle_seconds > self.connection_timeout:
                            stale_clients.append(client_id)
                            continue

                        # Ping 전송 (연결 유지)
                        if conn.websocket.client_state == WebSocketState.CONNECTED:
                            try:
                                await conn.websocket.send_json({"type": "ping"})
                            except Exception as e:
                                logger.debug(f"[{client_id}] Heartbeat ping failed: {e}")
                                stale_clients.append(client_id)

                # 타임아웃 연결 정리
                for client_id in stale_clients:
                    logger.info(f"[{client_id}] Connection timed out, disconnecting")
                    await self.disconnect(client_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(5)

    async def close_all(self) -> None:
        """모든 연결 종료 (서버 종료 시)"""
        logger.info(f"Closing all {len(self._connections)} connections...")

        # Heartbeat 중지
        await self.stop_heartbeat()

        async with self._lock:
            for client_id in list(self._connections.keys()):
                conn = self._connections.get(client_id)
                if conn and conn.websocket.client_state == WebSocketState.CONNECTED:
                    try:
                        await conn.websocket.close(code=1001, reason="Server shutdown")
                    except Exception:
                        pass

            self._connections.clear()

        logger.info("All connections closed")

    def get_stats(self) -> dict:
        """연결 통계"""
        return {
            "active_connections": len(self._connections),
            "max_connections": self.max_connections,
            "synthesizing": sum(
                1 for c in self._connections.values() if c.is_synthesizing
            ),
        }


# 싱글톤 인스턴스
connection_manager = ConnectionManager()
