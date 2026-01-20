"""
Base Agent 클래스
모든 Agent가 상속받는 추상 클래스
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Agent 실행 상태"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    SKIPPED = "SKIPPED"


@dataclass
class AgentResult:
    """Agent 실행 결과"""
    agent_id: str
    agent_type: str
    status: AgentStatus
    data: dict = field(default_factory=dict)
    error: Optional[str] = None
    execution_time_ms: int = 0
    metadata: dict = field(default_factory=dict)

    def is_success(self) -> bool:
        return self.status == AgentStatus.SUCCESS

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata,
        }


class BaseAgent(ABC):
    """
    Agent 추상 클래스

    모든 Agent는 이 클래스를 상속받아 구현:
    - DocumentAgent: 문서 파싱
    - ProfileAgent: 외부 정보 프로파일링
    - SignalAgent: 시그널 추출
    - InsightAgent: 인사이트 생성
    """

    def __init__(self, agent_type: str, timeout_seconds: int = 120):
        self.agent_id = f"{agent_type}-{uuid4().hex[:8]}"
        self.agent_type = agent_type
        self.timeout_seconds = timeout_seconds
        self._start_time: Optional[float] = None

    @abstractmethod
    async def execute(self, context: dict) -> AgentResult:
        """
        Agent 메인 실행 로직 (서브클래스에서 구현)

        Args:
            context: Orchestrator로부터 전달받은 컨텍스트

        Returns:
            AgentResult: 실행 결과
        """
        pass

    async def run(self, context: dict) -> AgentResult:
        """
        Agent 실행 래퍼 (타임아웃, 에러 핸들링, 메트릭 수집)
        """
        self._start_time = time.time()
        logger.info(f"[{self.agent_id}] Starting execution")

        try:
            import asyncio
            result = await asyncio.wait_for(
                self.execute(context),
                timeout=self.timeout_seconds
            )

            execution_time = int((time.time() - self._start_time) * 1000)
            result.execution_time_ms = execution_time

            logger.info(
                f"[{self.agent_id}] Completed: status={result.status.value}, "
                f"time={execution_time}ms"
            )
            return result

        except asyncio.TimeoutError:
            execution_time = int((time.time() - self._start_time) * 1000)
            logger.error(f"[{self.agent_id}] Timeout after {execution_time}ms")

            return AgentResult(
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                status=AgentStatus.TIMEOUT,
                error=f"Agent timeout after {self.timeout_seconds}s",
                execution_time_ms=execution_time,
            )

        except Exception as e:
            execution_time = int((time.time() - self._start_time) * 1000)
            logger.error(f"[{self.agent_id}] Failed: {e}")

            return AgentResult(
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                status=AgentStatus.FAILED,
                error=str(e)[:500],
                execution_time_ms=execution_time,
            )

    def _success(self, data: dict, metadata: Optional[dict] = None) -> AgentResult:
        """성공 결과 생성 헬퍼"""
        return AgentResult(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            status=AgentStatus.SUCCESS,
            data=data,
            metadata=metadata or {},
        )

    def _failed(self, error: str, data: Optional[dict] = None) -> AgentResult:
        """실패 결과 생성 헬퍼"""
        return AgentResult(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            status=AgentStatus.FAILED,
            data=data or {},
            error=error,
        )

    def _skipped(self, reason: str) -> AgentResult:
        """스킵 결과 생성 헬퍼"""
        return AgentResult(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            status=AgentStatus.SKIPPED,
            metadata={"skip_reason": reason},
        )
