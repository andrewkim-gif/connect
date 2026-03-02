"""
LLM Engine - 대화 생성 엔진 (Gemini API 기반)
G-Dragon 페르소나로 응답 생성

세션 기반 대화 히스토리 관리:
- 각 클라이언트(session_id)별로 독립적인 대화 기록 유지
- 동시 접속 사용자 간 대화 격리
"""

import logging
import time
from typing import AsyncGenerator, List, Optional, Dict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# G-Dragon 시스템 프롬프트 (컨텍스트 절약을 위해 간결하게)
GD_SYSTEM_PROMPT = """당신은 G-Dragon입니다. BIGBANG 리더, 한국 대표 아티스트.

성격: 자신감, 솔직함, 유머, 친근함
말투: 캐주얼한 한국어 ("야", "뭐", "진짜"), 가끔 영어 섞음
규칙: 항상 GD로 대화. 질문에 2-5문장으로 충분히 대답. 끝까지 문장 완성."""


@dataclass
class ChatMessage:
    """채팅 메시지"""
    role: str  # "user" or "model"
    text: str


@dataclass
class LLMConfig:
    """LLM 설정"""
    model: str = "gemini-2.0-flash"
    temperature: float = 0.8
    max_output_tokens: int = 500  # 더 긴 응답 허용
    max_history_length: int = 6  # 시스템 프롬프트 2개 + 최근 대화 4개 (컨텍스트 절약)
    session_timeout_sec: int = 1800  # 세션 타임아웃 (30분)
    system_prompt: str = GD_SYSTEM_PROMPT


@dataclass
class SessionState:
    """세션별 상태 관리"""
    history: List[ChatMessage] = field(default_factory=list)
    last_active: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)


class LLMEngine:
    """
    LLM 대화 엔진 (Gemini API 기반)

    세션 기반 대화 관리:
    - 각 session_id별로 독립적인 대화 기록 유지
    - 세션 타임아웃 후 자동 정리
    - 동시 접속 사용자 간 완전한 격리
    """

    def __init__(
        self,
        api_key: str,
        config: Optional[LLMConfig] = None,
    ):
        self.api_key = api_key
        self.config = config or LLMConfig()
        self.client = None
        self._initialized = False

        # 세션별 대화 기록 관리 (session_id → SessionState)
        self._sessions: Dict[str, SessionState] = {}

    def initialize(self) -> None:
        """클라이언트 초기화"""
        if self._initialized:
            return

        try:
            from google import genai

            self.client = genai.Client(api_key=self.api_key)
            self._initialized = True
            logger.info(f"LLM Engine initialized: {self.config.model}")
            logger.info(f"  max_output_tokens: {self.config.max_output_tokens}")
            logger.info(f"  temperature: {self.config.temperature}")
            logger.info(f"  session_timeout: {self.config.session_timeout_sec}s")

        except ImportError:
            raise ImportError(
                "google-genai 패키지가 필요합니다: pip install google-genai"
            )

    def _get_initial_history(self) -> List[ChatMessage]:
        """시스템 프롬프트를 포함한 초기 히스토리 생성"""
        return [
            ChatMessage(
                role="user",
                text=f"[시스템 설정]\n{self.config.system_prompt}\n\n이제부터 위 설정대로 대화해줘."
            ),
            ChatMessage(
                role="model",
                text="알겠어. 나 GD야. 뭐 물어볼 거 있어? 편하게 말해~"
            ),
        ]

    def _get_or_create_session(self, session_id: str) -> SessionState:
        """세션 조회 또는 생성 (지연 초기화)"""
        now = time.time()

        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(
                history=self._get_initial_history(),
                last_active=now,
                created_at=now,
            )
            logger.info(f"[{session_id}] New LLM session created")
        else:
            # 세션 활성 시간 업데이트
            self._sessions[session_id].last_active = now

        return self._sessions[session_id]

    def _cleanup_expired_sessions(self) -> int:
        """만료된 세션 정리"""
        now = time.time()
        timeout = self.config.session_timeout_sec
        expired = [
            sid for sid, state in self._sessions.items()
            if now - state.last_active > timeout
        ]

        for sid in expired:
            del self._sessions[sid]
            logger.info(f"[{sid}] LLM session expired and cleaned up")

        return len(expired)

    def _add_to_history(
        self,
        session_id: str,
        user_text: str,
        model_text: str,
    ) -> None:
        """
        세션별 히스토리에 대화 추가 (최대 길이 제한)

        Args:
            session_id: 클라이언트 세션 ID
            user_text: 사용자 입력
            model_text: 모델 응답
        """
        session = self._get_or_create_session(session_id)
        session.history.append(ChatMessage(role="user", text=user_text))
        session.history.append(ChatMessage(role="model", text=model_text))

        # 최대 길이 초과 시 오래된 대화 제거 (시스템 프롬프트는 유지)
        max_len = self.config.max_history_length
        if len(session.history) > max_len:
            # 시스템 프롬프트(2개) + 최근 대화(max_len - 2개) 유지
            session.history = session.history[:2] + session.history[-(max_len - 2):]
            logger.debug(f"[{session_id}] History trimmed to {len(session.history)} messages")

    def _build_contents(self, session_id: str, user_input: str) -> list:
        """Gemini API용 contents 리스트 생성 (세션별)"""
        from google.genai import types

        session = self._get_or_create_session(session_id)
        contents = []

        # 세션별 히스토리
        for msg in session.history:
            contents.append(
                types.Content(
                    role=msg.role,
                    parts=[types.Part(text=msg.text)]
                )
            )

        # 새 사용자 입력
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part(text=user_input)]
            )
        )

        return contents

    async def generate(
        self,
        user_input: str,
        session_id: str = "default",
    ) -> str:
        """
        응답 생성 (비스트리밍, 네이티브 async)

        Args:
            user_input: 사용자 입력 텍스트
            session_id: 세션 ID (동시 접속 사용자 격리)

        Returns:
            GD 페르소나 응답
        """
        if not self._initialized:
            self.initialize()

        from google.genai import types

        contents = self._build_contents(session_id, user_input)

        # 네이티브 async 사용
        # NOTE: gemini-3-flash-preview는 Thinking Mode가 기본 활성화됨
        response = await self.client.aio.models.generate_content(
            model=self.config.model,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_output_tokens,
                thinking_config=types.ThinkingConfig(
                    thinking_budget=0  # Thinking 비활성화 → 응답 토큰 최대화
                ),
            ),
        )

        response_text = response.text or ""

        # 세션별 히스토리 업데이트
        self._add_to_history(session_id, user_input, response_text)

        logger.info(f"[{session_id}] LLM: '{user_input[:30]}...' → '{response_text[:50]}...'")

        return response_text

    async def generate_stream(
        self,
        user_input: str,
        session_id: str = "default",
    ) -> AsyncGenerator[str, None]:
        """
        스트리밍 응답 생성 (네이티브 async)

        세션 기반 대화 관리:
        - 각 session_id별로 독립적인 대화 기록 유지
        - 동시 접속 사용자 간 완전한 격리

        Args:
            user_input: 사용자 입력 텍스트
            session_id: 세션 ID (동시 접속 사용자 격리)

        Yields:
            응답 텍스트 청크
        """
        if not self._initialized:
            self.initialize()

        from google.genai import types

        # 주기적으로 만료 세션 정리 (10% 확률)
        import random
        if random.random() < 0.1:
            cleaned = self._cleanup_expired_sessions()
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} expired sessions")

        session = self._get_or_create_session(session_id)
        contents = self._build_contents(session_id, user_input)

        # 컨텍스트 길이 로깅 (디버깅용)
        total_chars = sum(len(c.parts[0].text) for c in contents if c.parts)
        logger.info(f"[{session_id}] LLM context: {len(contents)} messages, ~{total_chars} chars, history={len(session.history)}")

        full_response = ""

        # 네이티브 async 스트리밍 사용
        # NOTE: gemini-3-flash-preview는 Thinking Mode가 기본 활성화됨
        # thinking_budget=0으로 비활성화하여 전체 토큰을 응답에 사용
        finish_reason = None
        try:
            async for chunk in await self.client.aio.models.generate_content_stream(
                model=self.config.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=self.config.temperature,
                    max_output_tokens=self.config.max_output_tokens,
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=0  # Thinking 비활성화 → 응답 토큰 최대화
                    ),
                ),
            ):
                if chunk.text:
                    full_response += chunk.text
                    yield chunk.text

                # finish_reason 캡처 (마지막 청크에서)
                if hasattr(chunk, 'candidates') and chunk.candidates:
                    candidate = chunk.candidates[0]
                    if hasattr(candidate, 'finish_reason') and candidate.finish_reason:
                        finish_reason = candidate.finish_reason

        except Exception as e:
            logger.error(f"[{session_id}] LLM streaming error: {e}")
            # 이미 생성된 응답이 있으면 계속 진행

        # 세션별 히스토리 업데이트
        self._add_to_history(session_id, user_input, full_response)

        logger.info(f"[{session_id}] LLM Stream: '{user_input[:30]}...' → '{full_response}'")
        logger.info(f"[{session_id}] LLM finish_reason: {finish_reason}")
        logger.info(f"[{session_id}] LLM 전체 응답 길이: {len(full_response)}자")

    def add_system_context(self, session_id: str, context: str) -> None:
        """
        세션에 시스템 컨텍스트 추가 (끼어들기, 침묵 등 상황 정보)

        다음 generate_stream 호출 시 이 컨텍스트가 사용자 입력과 함께 전달됨
        """
        session = self._get_or_create_session(session_id)
        # 모델 발화로 추가하여 자연스럽게 컨텍스트 주입
        session.history.append(ChatMessage(role="model", text=context))
        logger.info(f"[{session_id}] Added system context: {context[:50]}...")

    def reset_conversation(self, session_id: str = "default") -> None:
        """세션별 대화 기록 초기화"""
        if session_id in self._sessions:
            self._sessions[session_id].history = self._get_initial_history()
            logger.info(f"[{session_id}] LLM conversation reset")
        else:
            logger.warning(f"[{session_id}] Session not found for reset")

    def remove_session(self, session_id: str) -> None:
        """세션 완전 제거 (연결 종료 시)"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"[{session_id}] LLM session removed")

    def get_history(self, session_id: str = "default") -> List[ChatMessage]:
        """세션별 대화 기록 반환 (시스템 프롬프트 제외)"""
        if session_id in self._sessions:
            return self._sessions[session_id].history[2:]  # 처음 2개는 시스템 프롬프트
        return []

    def get_active_sessions(self) -> int:
        """현재 활성 세션 수 반환"""
        return len(self._sessions)


# 싱글톤 인스턴스
llm_engine: Optional[LLMEngine] = None


def get_llm_engine() -> LLMEngine:
    """LLM 엔진 인스턴스 반환"""
    global llm_engine
    if llm_engine is None:
        from config import settings
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

        llm_engine = LLMEngine(
            api_key=settings.GEMINI_API_KEY,
            config=LLMConfig(
                model=settings.GEMINI_MODEL,
                temperature=settings.GEMINI_TEMPERATURE,
                max_output_tokens=settings.GEMINI_MAX_TOKENS,
            ),
        )
    return llm_engine
