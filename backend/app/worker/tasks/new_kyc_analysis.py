"""
신규 법인 KYC 분석 파이프라인 (Multi-Agent 버전)
서류 기반 신규 고객 분석

Architecture:
    NewKycOrchestrator
        ├── Phase 1 (병렬)
        │   ├── DocumentAgent x N (문서별 파싱)
        │   └── ProfileAgent (외부 정보)
        ├── Phase 2
        │   └── SignalAgent (시그널 추출)
        └── Phase 3
            └── InsightAgent (인사이트 생성)
"""

import json
import logging
import os
import uuid
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import update

from app.worker.celery_app import celery_app
from app.worker.db import get_sync_db
from app.models.job import Job, JobStatus
from app.worker.llm.exceptions import (
    RateLimitError,
    TimeoutError as LLMTimeoutError,
    AllProvidersFailedError,
)

logger = logging.getLogger(__name__)


def update_new_kyc_job_progress(
    job_id: str,
    status: JobStatus,
    step: str = None,
    percent: int = 0,
    error_code: str = None,
    error_message: str = None,
):
    """Update new KYC job progress in database"""
    with get_sync_db() as db:
        update_data = {
            "status": status.value,
            "progress_percent": percent,
        }

        if step:
            update_data["progress_step"] = step

        if status == JobStatus.RUNNING:
            job = db.execute(
                Job.__table__.select().where(Job.job_id == uuid.UUID(job_id))
            ).fetchone()
            if job and not job.started_at:
                update_data["started_at"] = datetime.now(UTC)

        if status in (JobStatus.DONE, JobStatus.FAILED):
            update_data["finished_at"] = datetime.now(UTC)

        if error_code:
            update_data["error_code"] = error_code
        if error_message:
            update_data["error_message"] = error_message

        stmt = (
            update(Job)
            .where(Job.job_id == uuid.UUID(job_id))
            .values(**update_data)
        )
        db.execute(stmt)
        db.commit()

        logger.info(f"New KYC Job {job_id} updated: status={status.value}, step={step}, percent={percent}")


def _save_result(job_dir: str, result: dict):
    """Save analysis result to JSON file"""
    result_path = os.path.join(job_dir, "result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"Saved result to {result_path}")


@celery_app.task(
    bind=True,
    name="run_new_kyc_pipeline",
    autoretry_for=(RateLimitError, LLMTimeoutError, AllProvidersFailedError, ConnectionError, TimeoutError),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    retry_backoff=True,
    retry_backoff_max=300,
)
def run_new_kyc_pipeline(self, job_id: str, job_dir: str, corp_name: Optional[str] = None):
    """
    신규 법인 KYC Multi-Agent 분석 파이프라인

    Args:
        job_id: Job ID (UUID string)
        job_dir: 업로드 파일 디렉토리
        corp_name: 기업명 (없으면 문서에서 추출)

    Pipeline:
        Phase 1 (병렬): DocumentAgents + ProfileAgent
        Phase 2: SignalAgent
        Phase 3: InsightAgent
    """
    import asyncio

    logger.info(f"Starting new KYC Multi-Agent pipeline: job={job_id}")

    # Progress callback 정의
    def progress_callback(step: str, percent: int):
        status = JobStatus.RUNNING if percent < 100 else JobStatus.DONE
        update_new_kyc_job_progress(job_id, status, step, percent)

    try:
        # Orchestrator 초기화
        from app.worker.agents.orchestrator import (
            NewKycOrchestrator,
            OrchestratorConfig,
        )

        config = OrchestratorConfig(
            parallel_doc_parse=True,
            skip_profile_on_unknown=True,
            use_light_profile=False,  # Full profile for production
            use_quick_insight=False,   # LLM insight for production
        )

        orchestrator = NewKycOrchestrator(config=config)
        orchestrator.set_progress_callback(progress_callback)

        # 비동기 실행
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # 이미 이벤트 루프가 실행 중인 경우 (테스트 등)
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    orchestrator.execute(job_id, job_dir, corp_name)
                )
                output = future.result(timeout=300)
        else:
            # 새 이벤트 루프 생성
            output = asyncio.run(
                orchestrator.execute(job_id, job_dir, corp_name)
            )

        # 결과 저장
        result = output.to_dict()

        # _meta 제거 (클라이언트에게는 불필요)
        result.pop("_meta", None)

        _save_result(job_dir, result)

        # 최종 상태 업데이트
        update_new_kyc_job_progress(job_id, JobStatus.DONE, "INSIGHT", 100)

        logger.info(
            f"New KYC pipeline completed: job={job_id}, "
            f"signals={len(output.signals)}, "
            f"time={output.execution_time_ms}ms"
        )

        return {
            "status": "success",
            "job_id": job_id,
            "signals_created": len(output.signals),
            "execution_time_ms": output.execution_time_ms,
        }

    except Exception as e:
        logger.error(f"New KYC pipeline failed: job={job_id}, error={e}")

        # 에러 결과 저장
        error_result = {
            "job_id": job_id,
            "corp_info": {},
            "financial_summary": None,
            "shareholders": [],
            "signals": [],
            "insight": f"분석 중 오류가 발생했습니다: {str(e)[:100]}",
            "error": str(e)[:500],
            "created_at": datetime.now(UTC).isoformat(),
        }
        _save_result(job_dir, error_result)

        # 실패 상태 업데이트
        update_new_kyc_job_progress(
            job_id,
            JobStatus.FAILED,
            error_code="PIPELINE_ERROR",
            error_message=str(e)[:500],
        )

        raise


# ============================================================
# Legacy 호환 함수 (기존 코드 지원)
# ============================================================

def _parse_documents_from_dir(job_dir: str) -> dict:
    """
    Legacy: 동기식 문서 파싱 (Multi-Agent로 대체됨)
    """
    import asyncio
    from app.worker.agents.document_agent import DocumentAgentPool

    pool = DocumentAgentPool(job_dir)
    pool.create_agents()

    results = asyncio.run(pool.run_parallel())
    return pool.merge_results(results)


def _build_context(doc_results: dict, corp_name: str) -> dict:
    """
    Legacy: 컨텍스트 빌드 (Orchestrator로 대체됨)
    """
    return {
        "corp_info": doc_results.get("corp_info", {}),
        "snapshot": {
            "corp": {
                "corp_id": None,
                "corp_name": corp_name or doc_results.get("corp_info", {}).get("corp_name"),
            },
            "credit": {"has_loan": False},
        },
        "documents": doc_results.get("doc_summaries", {}),
        "shareholders": doc_results.get("shareholders", []),
        "financial_summary": doc_results.get("financial_summary"),
    }
