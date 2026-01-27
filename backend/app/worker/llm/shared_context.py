"""
SharedContextStore for rKYC Multi-Agent System

Agent 간 컨텍스트 공유 저장소:
- Redis 기반 공유 상태 관리
- Agent 간 중복 작업 방지
- 중간 결과물 재사용
- 파이프라인 단계 간 데이터 전달

Usage:
    from app.worker.llm.shared_context import SharedContextStore, get_shared_context

    store = get_shared_context()

    # 작업 시작 전 락 획득
    async with store.acquire_lock("signal_extraction", corp_id):
        # 캐시된 결과 확인
        cached = await store.get_step_result("signal_extraction", corp_id)
        if cached:
            return cached

        # 작업 수행
        result = await extract_signals(...)

        # 결과 저장
        await store.set_step_result("signal_extraction", corp_id, result)
"""

import asyncio
import json
import hashlib
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta
from enum import Enum
from typing import Any, Optional

import redis.asyncio as redis

from app.worker.tracing import get_logger, LogEvents

logger = get_logger("SharedContextStore")


class ContextScope(str, Enum):
    """컨텍스트 스코프"""
    JOB = "job"           # Job 단위 (분석 작업 1회)
    CORP = "corp"         # 기업 단위 (기업별 캐시)
    GLOBAL = "global"     # 전역 (업종 정보 등)


class PipelineStep(str, Enum):
    """파이프라인 단계"""
    SNAPSHOT = "snapshot"
    DOC_INGEST = "doc_ingest"
    PROFILING = "profiling"
    EXTERNAL = "external"
    CONTEXT = "context"
    SIGNAL = "signal"
    VALIDATION = "validation"
    INDEX = "index"
    INSIGHT = "insight"


@dataclass
class ContextEntry:
    """컨텍스트 엔트리"""
    key: str
    value: Any
    scope: ContextScope
    step: Optional[PipelineStep]
    created_at: str
    expires_at: Optional[str]
    metadata: dict = field(default_factory=dict)


@dataclass
class LockInfo:
    """락 정보"""
    key: str
    holder: str
    acquired_at: str
    expires_at: str


# ============================================================================
# TTL Configuration
# ============================================================================


STEP_TTL_SECONDS: dict[PipelineStep, int] = {
    PipelineStep.SNAPSHOT: 3600,       # 1시간
    PipelineStep.DOC_INGEST: 86400,    # 24시간 (문서는 자주 안 변함)
    PipelineStep.PROFILING: 604800,    # 7일 (프로필은 오래 캐시)
    PipelineStep.EXTERNAL: 3600,       # 1시간 (외부 정보는 빨리 변함)
    PipelineStep.CONTEXT: 1800,        # 30분
    PipelineStep.SIGNAL: 3600,         # 1시간
    PipelineStep.VALIDATION: 3600,     # 1시간
    PipelineStep.INDEX: 86400,         # 24시간
    PipelineStep.INSIGHT: 3600,        # 1시간
}

SCOPE_TTL_SECONDS: dict[ContextScope, int] = {
    ContextScope.JOB: 3600,            # 1시간 (Job 완료 후 정리)
    ContextScope.CORP: 86400,          # 24시간
    ContextScope.GLOBAL: 604800,       # 7일
}

LOCK_TTL_SECONDS = 300  # 5분 (락 타임아웃)
LOCK_RETRY_DELAY = 0.5  # 500ms


# ============================================================================
# SharedContextStore
# ============================================================================


class SharedContextStore:
    """
    Redis 기반 공유 컨텍스트 저장소

    Features:
    - 파이프라인 단계별 중간 결과 캐싱
    - Agent 간 데이터 공유
    - 분산 락으로 중복 작업 방지
    - TTL 기반 자동 정리
    """

    KEY_PREFIX = "rkyc:context"
    LOCK_PREFIX = "rkyc:lock"

    def __init__(self, redis_url: Optional[str] = None):
        self._redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
        self._initialized = False
        self._local_cache: dict[str, ContextEntry] = {}  # Local fallback

    async def initialize(self) -> None:
        """Redis 연결 초기화"""
        if self._initialized:
            return

        if self._redis_url is None:
            from app.core.config import settings
            # Context store용 별도 DB (DB 3)
            base_url = settings.REDIS_URL.rstrip("/0123456789")
            self._redis_url = f"{base_url}/3"

        try:
            self._redis = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._redis.ping()
            self._initialized = True
            logger.info("shared_context_initialized", redis_url=self._redis_url)
        except Exception as e:
            logger.warning(
                "shared_context_redis_unavailable",
                error=str(e),
                fallback="local_memory",
            )
            self._redis = None
            self._initialized = True

    def _make_key(
        self,
        scope: ContextScope,
        step: Optional[PipelineStep],
        identifier: str,
    ) -> str:
        """키 생성"""
        parts = [self.KEY_PREFIX, scope.value]
        if step:
            parts.append(step.value)
        parts.append(identifier)
        return ":".join(parts)

    def _make_lock_key(self, step: PipelineStep, identifier: str) -> str:
        """락 키 생성"""
        return f"{self.LOCK_PREFIX}:{step.value}:{identifier}"

    async def get(
        self,
        scope: ContextScope,
        identifier: str,
        step: Optional[PipelineStep] = None,
    ) -> Optional[Any]:
        """
        컨텍스트 조회

        Args:
            scope: 스코프 (JOB, CORP, GLOBAL)
            identifier: 식별자 (job_id, corp_id 등)
            step: 파이프라인 단계 (optional)

        Returns:
            저장된 값 또는 None
        """
        await self.initialize()

        key = self._make_key(scope, step, identifier)

        if self._redis:
            try:
                value = await self._redis.get(key)
                if value:
                    entry = json.loads(value)
                    logger.debug(
                        "context_get_hit",
                        key=key,
                        scope=scope.value,
                        step=step.value if step else None,
                    )
                    return entry.get("value")
            except Exception as e:
                logger.warning("context_get_error", key=key, error=str(e))

        # Local fallback
        if key in self._local_cache:
            entry = self._local_cache[key]
            if entry.expires_at:
                if datetime.fromisoformat(entry.expires_at) > datetime.now(UTC):
                    return entry.value
                else:
                    del self._local_cache[key]

        logger.debug(
            "context_get_miss",
            key=key,
            scope=scope.value,
            step=step.value if step else None,
        )
        return None

    async def set(
        self,
        scope: ContextScope,
        identifier: str,
        value: Any,
        step: Optional[PipelineStep] = None,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> bool:
        """
        컨텍스트 저장

        Args:
            scope: 스코프
            identifier: 식별자
            value: 저장할 값
            step: 파이프라인 단계
            ttl_seconds: TTL (None이면 기본값 사용)
            metadata: 추가 메타데이터

        Returns:
            성공 여부
        """
        await self.initialize()

        key = self._make_key(scope, step, identifier)

        # TTL 결정
        if ttl_seconds is None:
            if step:
                ttl_seconds = STEP_TTL_SECONDS.get(step, 3600)
            else:
                ttl_seconds = SCOPE_TTL_SECONDS.get(scope, 3600)

        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=ttl_seconds)

        entry = ContextEntry(
            key=key,
            value=value,
            scope=scope,
            step=step,
            created_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
            metadata=metadata or {},
        )

        if self._redis:
            try:
                entry_json = json.dumps({
                    "value": value,
                    "scope": scope.value,
                    "step": step.value if step else None,
                    "created_at": entry.created_at,
                    "expires_at": entry.expires_at,
                    "metadata": entry.metadata,
                }, ensure_ascii=False, default=str)

                await self._redis.setex(key, ttl_seconds, entry_json)
                logger.debug(
                    "context_set",
                    key=key,
                    scope=scope.value,
                    step=step.value if step else None,
                    ttl=ttl_seconds,
                )
                return True
            except Exception as e:
                logger.warning("context_set_error", key=key, error=str(e))

        # Local fallback
        self._local_cache[key] = entry
        return True

    async def delete(
        self,
        scope: ContextScope,
        identifier: str,
        step: Optional[PipelineStep] = None,
    ) -> bool:
        """컨텍스트 삭제"""
        await self.initialize()

        key = self._make_key(scope, step, identifier)

        if self._redis:
            try:
                await self._redis.delete(key)
            except Exception as e:
                logger.warning("context_delete_error", key=key, error=str(e))

        if key in self._local_cache:
            del self._local_cache[key]

        return True

    async def get_step_result(
        self,
        step: PipelineStep,
        corp_id: str,
        job_id: Optional[str] = None,
    ) -> Optional[Any]:
        """
        파이프라인 단계 결과 조회

        Args:
            step: 파이프라인 단계
            corp_id: 기업 ID
            job_id: Job ID (optional, JOB 스코프용)

        Returns:
            캐시된 결과 또는 None
        """
        # Job 스코프 먼저 확인
        if job_id:
            result = await self.get(ContextScope.JOB, f"{job_id}:{corp_id}", step)
            if result:
                return result

        # Corp 스코프 확인
        return await self.get(ContextScope.CORP, corp_id, step)

    async def set_step_result(
        self,
        step: PipelineStep,
        corp_id: str,
        result: Any,
        job_id: Optional[str] = None,
        scope: ContextScope = ContextScope.CORP,
    ) -> bool:
        """
        파이프라인 단계 결과 저장

        Args:
            step: 파이프라인 단계
            corp_id: 기업 ID
            result: 저장할 결과
            job_id: Job ID
            scope: 저장 스코프

        Returns:
            성공 여부
        """
        identifier = f"{job_id}:{corp_id}" if job_id and scope == ContextScope.JOB else corp_id
        return await self.set(scope, identifier, result, step)

    @asynccontextmanager
    async def acquire_lock(
        self,
        step: PipelineStep,
        identifier: str,
        holder: Optional[str] = None,
        timeout_seconds: int = LOCK_TTL_SECONDS,
        retry_count: int = 3,
    ):
        """
        분산 락 획득 컨텍스트 매니저

        Args:
            step: 파이프라인 단계
            identifier: 리소스 식별자 (corp_id 등)
            holder: 락 홀더 식별자
            timeout_seconds: 락 타임아웃
            retry_count: 재시도 횟수

        Usage:
            async with store.acquire_lock("signal", corp_id):
                # 독점적 작업 수행
                ...
        """
        await self.initialize()

        lock_key = self._make_lock_key(step, identifier)
        holder = holder or f"worker-{id(asyncio.current_task())}"

        lock_acquired = False

        try:
            for attempt in range(retry_count):
                if self._redis:
                    try:
                        # SET NX EX 패턴으로 락 획득
                        acquired = await self._redis.set(
                            lock_key,
                            json.dumps({
                                "holder": holder,
                                "acquired_at": datetime.now(UTC).isoformat(),
                            }),
                            nx=True,  # Only if not exists
                            ex=timeout_seconds,
                        )
                        if acquired:
                            lock_acquired = True
                            logger.debug(
                                "lock_acquired",
                                key=lock_key,
                                holder=holder,
                            )
                            break
                    except Exception as e:
                        logger.warning("lock_acquire_error", key=lock_key, error=str(e))

                if not lock_acquired:
                    logger.debug(
                        "lock_retry",
                        key=lock_key,
                        attempt=attempt + 1,
                    )
                    await asyncio.sleep(LOCK_RETRY_DELAY)

            if not lock_acquired:
                logger.warning(
                    "lock_acquire_failed",
                    key=lock_key,
                    holder=holder,
                )
                # 락 획득 실패해도 작업 진행 (degraded mode)

            yield lock_acquired

        finally:
            if lock_acquired and self._redis:
                try:
                    await self._redis.delete(lock_key)
                    logger.debug("lock_released", key=lock_key)
                except Exception as e:
                    logger.warning("lock_release_error", key=lock_key, error=str(e))

    async def get_job_context(self, job_id: str) -> dict:
        """
        Job 전체 컨텍스트 조회

        Args:
            job_id: Job ID

        Returns:
            모든 단계의 결과를 담은 딕셔너리
        """
        await self.initialize()

        context = {}
        pattern = f"{self.KEY_PREFIX}:job:*:{job_id}:*"

        if self._redis:
            try:
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                    for key in keys:
                        value = await self._redis.get(key)
                        if value:
                            entry = json.loads(value)
                            step = entry.get("step")
                            if step:
                                context[step] = entry.get("value")
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning("get_job_context_error", job_id=job_id, error=str(e))

        return context

    async def cleanup_job(self, job_id: str) -> int:
        """
        Job 완료 후 관련 컨텍스트 정리

        Args:
            job_id: Job ID

        Returns:
            삭제된 키 수
        """
        await self.initialize()

        deleted = 0
        pattern = f"{self.KEY_PREFIX}:job:*:{job_id}*"

        if self._redis:
            try:
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                    if keys:
                        deleted += await self._redis.delete(*keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning("cleanup_job_error", job_id=job_id, error=str(e))

        logger.info("job_context_cleaned", job_id=job_id, deleted=deleted)
        return deleted

    async def get_stats(self) -> dict:
        """저장소 통계 조회"""
        await self.initialize()

        stats = {
            "redis_available": self._redis is not None,
            "local_cache_size": len(self._local_cache),
        }

        if self._redis:
            try:
                # 키 카운트
                context_count = 0
                lock_count = 0

                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(cursor, match=f"{self.KEY_PREFIX}:*", count=100)
                    context_count += len(keys)
                    if cursor == 0:
                        break

                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(cursor, match=f"{self.LOCK_PREFIX}:*", count=100)
                    lock_count += len(keys)
                    if cursor == 0:
                        break

                stats["redis_context_keys"] = context_count
                stats["redis_lock_keys"] = lock_count

            except Exception as e:
                stats["redis_error"] = str(e)

        return stats

    async def close(self) -> None:
        """연결 종료"""
        if self._redis:
            await self._redis.close()
            self._redis = None
            self._initialized = False


# Singleton instance
_shared_context: Optional[SharedContextStore] = None


def get_shared_context() -> SharedContextStore:
    """Get singleton SharedContextStore instance"""
    global _shared_context
    if _shared_context is None:
        _shared_context = SharedContextStore()
    return _shared_context


async def reset_shared_context() -> None:
    """Reset singleton instance"""
    global _shared_context
    if _shared_context:
        await _shared_context.close()
    _shared_context = None
