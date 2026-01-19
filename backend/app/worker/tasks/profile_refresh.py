"""
Corp Profile Background Refresh Tasks

PRD v1.2:
- 7일 TTL, Background 자동 갱신
- 페이지 방문 시 Background 갱신 트리거
- 새 시그널 감지 시 5분 내 갱신
- 야간 배치 전체 갱신
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from celery import shared_task
from sqlalchemy import text

from app.worker.db import get_sync_db
from app.worker.pipelines.corp_profiling import CorpProfilingPipeline, get_corp_profiling_pipeline
from app.worker.llm.circuit_breaker import get_circuit_breaker_manager

logger = logging.getLogger(__name__)


# ============================================================================
# Profile Refresh Tasks
# ============================================================================


@shared_task(
    name="app.worker.tasks.refresh_corp_profile",
    bind=True,
    max_retries=2,
    soft_time_limit=120,  # 2분 소프트 리밋
)
def refresh_corp_profile(
    self,
    corp_id: str,
    force: bool = False,
    trigger_source: str = "manual",
):
    """
    단일 기업 프로필 갱신

    Args:
        corp_id: 기업 ID
        force: 캐시 무시 강제 갱신
        trigger_source: 트리거 소스 (page_visit, signal, batch, manual)

    Returns:
        dict: 갱신 결과
    """
    logger.info(f"[ProfileRefresh] Starting for {corp_id} (force={force}, source={trigger_source})")

    try:
        with get_sync_db() as session:
            # 기업 정보 조회
            corp_query = text("""
                SELECT c.corp_id, c.corp_nm, c.industry_code, im.industry_nm
                FROM corp c
                LEFT JOIN industry_master im ON c.industry_code = im.industry_code
                WHERE c.corp_id = :corp_id
            """)
            result = session.execute(corp_query, {"corp_id": corp_id})
            corp = result.fetchone()

            if not corp:
                logger.error(f"[ProfileRefresh] Corp not found: {corp_id}")
                return {"success": False, "error": "Corp not found"}

            corp_name = corp.corp_nm
            industry_code = corp.industry_code
            industry_name = corp.industry_nm or f"업종코드 {industry_code}"

            # 캐시 확인 (force가 아닌 경우)
            if not force:
                cache_query = text("""
                    SELECT profile_id, expires_at, profile_confidence
                    FROM rkyc_corp_profile
                    WHERE corp_id = :corp_id
                    AND expires_at > NOW()
                """)
                cache_result = session.execute(cache_query, {"corp_id": corp_id})
                cached = cache_result.fetchone()

                if cached:
                    logger.info(
                        f"[ProfileRefresh] Fresh cache exists for {corp_id}, "
                        f"expires={cached.expires_at}"
                    )
                    return {
                        "success": True,
                        "cached": True,
                        "profile_id": str(cached.profile_id),
                        "confidence": cached.profile_confidence,
                    }

            # Pipeline 실행 (동기 버전 필요)
            pipeline = get_corp_profiling_pipeline()

            # 동기 실행을 위한 wrapper
            import asyncio

            async def run_pipeline():
                return await pipeline.execute(
                    corp_id=corp_id,
                    corp_name=corp_name,
                    industry_code=industry_code,
                    db_session=None,  # 파이프라인 내부에서 별도 세션 사용
                )

            # 이벤트 루프 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(run_pipeline())
            finally:
                loop.close()

            logger.info(
                f"[ProfileRefresh] Completed for {corp_id}: "
                f"cached={result.is_cached}, "
                f"confidence={result.profile.get('profile_confidence', 'UNKNOWN')}"
            )

            return {
                "success": True,
                "cached": result.is_cached,
                "profile_id": result.profile.get("profile_id"),
                "confidence": result.profile.get("profile_confidence"),
                "selected_queries": result.selected_queries,
            }

    except Exception as e:
        logger.error(f"[ProfileRefresh] Failed for {corp_id}: {e}")

        # 재시도
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

        return {"success": False, "error": str(e)}


@shared_task(
    name="app.worker.tasks.refresh_expiring_profiles",
    soft_time_limit=3600,  # 1시간 소프트 리밋
)
def refresh_expiring_profiles():
    """
    만료 임박 프로필 갱신 (매시간 실행)

    PRD v1.2:
    - Profile 나이 > 7일: 1시간 내 갱신
    - Rate limit: 분당 10개, 시간당 100개
    """
    logger.info("[ProfileRefresh] Starting expiring profiles refresh")

    try:
        with get_sync_db() as session:
            # 24시간 내 만료 예정 프로필 조회
            query = text("""
                SELECT corp_id
                FROM rkyc_corp_profile
                WHERE status = 'ACTIVE'
                AND expires_at BETWEEN NOW() AND NOW() + INTERVAL '24 hours'
                ORDER BY expires_at ASC
                LIMIT 100
            """)
            result = session.execute(query)
            expiring = result.fetchall()

            if not expiring:
                logger.info("[ProfileRefresh] No expiring profiles found")
                return {"refreshed": 0, "total": 0}

            logger.info(f"[ProfileRefresh] Found {len(expiring)} expiring profiles")

            refreshed = 0
            failed = 0

            for row in expiring:
                try:
                    # Rate limiting: 6초 간격 (분당 10개)
                    refresh_corp_profile.apply_async(
                        args=[row.corp_id],
                        kwargs={"trigger_source": "batch_expiring"},
                        countdown=refreshed * 6,  # 6초 간격
                    )
                    refreshed += 1
                except Exception as e:
                    logger.warning(f"[ProfileRefresh] Queue failed for {row.corp_id}: {e}")
                    failed += 1

            logger.info(
                f"[ProfileRefresh] Queued {refreshed} profiles for refresh, {failed} failed"
            )

            return {
                "queued": refreshed,
                "failed": failed,
                "total": len(expiring),
            }

    except Exception as e:
        logger.error(f"[ProfileRefresh] Expiring profiles refresh failed: {e}")
        return {"error": str(e)}


@shared_task(
    name="app.worker.tasks.refresh_all_profiles",
    soft_time_limit=14400,  # 4시간 소프트 리밋
)
def refresh_all_profiles():
    """
    전체 기업 프로필 순환 갱신 (야간 배치)

    PRD v1.2:
    - 새벽 3시 실행
    - Rate limit: 일일 500개
    """
    logger.info("[ProfileRefresh] Starting nightly full refresh")

    try:
        with get_sync_db() as session:
            # 최근 갱신 순으로 전체 기업 조회 (오래된 것 우선)
            query = text("""
                SELECT c.corp_id
                FROM corp c
                LEFT JOIN rkyc_corp_profile p ON c.corp_id = p.corp_id
                ORDER BY COALESCE(p.updated_at, '1970-01-01') ASC
                LIMIT 500
            """)
            result = session.execute(query)
            corps = result.fetchall()

            if not corps:
                logger.info("[ProfileRefresh] No corps found")
                return {"refreshed": 0, "total": 0}

            logger.info(f"[ProfileRefresh] Found {len(corps)} corps for nightly refresh")

            queued = 0
            for i, row in enumerate(corps):
                try:
                    # Rate limiting: 30초 간격 (시간당 120개, 4시간 = 480개)
                    refresh_corp_profile.apply_async(
                        args=[row.corp_id],
                        kwargs={"trigger_source": "batch_nightly"},
                        countdown=i * 30,  # 30초 간격
                    )
                    queued += 1
                except Exception as e:
                    logger.warning(f"[ProfileRefresh] Queue failed for {row.corp_id}: {e}")

            logger.info(f"[ProfileRefresh] Queued {queued} profiles for nightly refresh")

            return {
                "queued": queued,
                "total": len(corps),
            }

    except Exception as e:
        logger.error(f"[ProfileRefresh] Nightly refresh failed: {e}")
        return {"error": str(e)}


@shared_task(
    name="app.worker.tasks.trigger_profile_refresh_on_signal",
    soft_time_limit=300,
)
def trigger_profile_refresh_on_signal(corp_id: str, signal_id: str):
    """
    새 시그널 감지 시 프로필 갱신 트리거

    PRD v1.2:
    - 새 시그널 감지 시 5분 내 갱신
    """
    logger.info(f"[ProfileRefresh] Signal-triggered refresh for {corp_id} (signal={signal_id})")

    # 5분 후 갱신 (중복 시그널 방지)
    refresh_corp_profile.apply_async(
        args=[corp_id],
        kwargs={"trigger_source": f"signal:{signal_id}"},
        countdown=300,  # 5분 후
    )

    return {"queued": True, "corp_id": corp_id, "delay": 300}


# ============================================================================
# Celery Beat Schedule
# ============================================================================

# celery_app.conf.beat_schedule에 추가할 스케줄
PROFILE_REFRESH_SCHEDULE = {
    # 만료 임박 Profile 갱신 (매시간)
    "refresh-expiring-profiles": {
        "task": "app.worker.tasks.refresh_expiring_profiles",
        "schedule": 3600,  # 매시간 (crontab(minute=0) 대신 interval 사용)
    },
    # 전체 기업 순환 (새벽 3시)
    "refresh-all-profiles-nightly": {
        "task": "app.worker.tasks.refresh_all_profiles",
        "schedule": {
            "hour": 3,
            "minute": 0,
        },  # crontab 형식은 celery_app.py에서 설정
    },
}
