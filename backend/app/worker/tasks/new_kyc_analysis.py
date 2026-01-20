"""
신규 법인 KYC 분석 파이프라인
서류 기반 신규 고객 분석 (SNAPSHOT 스킵)
"""

import json
import logging
import os
import uuid
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import update, text

from app.worker.celery_app import celery_app
from app.worker.db import get_sync_db
from app.models.job import Job, JobStatus, ProgressStep
from app.worker.pipelines import (
    DocIngestPipeline,
    SignalExtractionPipeline,
    ValidationPipeline,
    deduplicate_within_batch,
)
from app.worker.llm.exceptions import (
    RateLimitError,
    TimeoutError as LLMTimeoutError,
    AllProvidersFailedError,
)
from app.worker.pipelines.corp_profiling import get_corp_profiling_pipeline

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


def _parse_documents_from_dir(job_dir: str) -> dict:
    """Parse uploaded PDF documents using doc parsers"""
    from app.worker.pipelines.doc_parsers import (
        BizRegParser,
        RegistryParser,
        ShareholdersParser,
        AoiParser,
        FinStatementParser,
    )

    results = {
        "corp_info": {},
        "shareholders": [],
        "financial_summary": None,
        "doc_summaries": {},
    }

    parsers = {
        "BIZ_REG": BizRegParser(),
        "REGISTRY": RegistryParser(),
        "SHAREHOLDERS": ShareholdersParser(),
        "AOI": AoiParser(),
        "FINANCIAL": FinStatementParser(),
    }

    for doc_type, parser in parsers.items():
        file_path = os.path.join(job_dir, f"{doc_type}.pdf")
        if os.path.exists(file_path):
            logger.info(f"Parsing {doc_type}: {file_path}")
            try:
                parsed = parser.parse(file_path)
                results["doc_summaries"][doc_type] = parsed

                # Extract corp info from BIZ_REG
                if doc_type == "BIZ_REG" and parsed:
                    results["corp_info"].update({
                        "corp_name": parsed.get("corp_name"),
                        "biz_no": parsed.get("biz_no"),
                        "ceo_name": parsed.get("ceo_name"),
                        "address": parsed.get("address"),
                        "founded_date": parsed.get("founded_date"),
                        "industry": parsed.get("biz_type") or parsed.get("biz_item"),
                    })

                # Extract corp info from REGISTRY
                if doc_type == "REGISTRY" and parsed:
                    results["corp_info"].update({
                        "corp_reg_no": parsed.get("corp_reg_no"),
                        "capital": parsed.get("capital"),
                    })
                    if not results["corp_info"].get("corp_name"):
                        results["corp_info"]["corp_name"] = parsed.get("corp_name")

                # Extract shareholders
                if doc_type == "SHAREHOLDERS" and parsed:
                    shareholders = parsed.get("shareholders", [])
                    results["shareholders"] = shareholders

                # Extract financial summary
                if doc_type == "FINANCIAL" and parsed:
                    results["financial_summary"] = {
                        "year": parsed.get("fiscal_year", datetime.now().year),
                        "revenue": parsed.get("revenue"),
                        "operating_profit": parsed.get("operating_profit"),
                        "debt_ratio": parsed.get("debt_ratio"),
                    }

            except Exception as e:
                logger.warning(f"Failed to parse {doc_type}: {e}")
                results["doc_summaries"][doc_type] = {"error": str(e)}

    return results


def _build_new_kyc_context(doc_results: dict, corp_name: str, profile_data: dict = None) -> dict:
    """Build unified context from parsed documents"""
    context = {
        "corp_info": doc_results.get("corp_info", {}),
        "snapshot": {
            "corp": {
                "corp_id": None,  # 신규 고객이므로 없음
                "corp_name": corp_name or doc_results.get("corp_info", {}).get("corp_name"),
                "biz_no": doc_results.get("corp_info", {}).get("biz_no"),
                "ceo_name": doc_results.get("corp_info", {}).get("ceo_name"),
            },
            "credit": {
                "has_loan": False,  # 신규 고객
            },
        },
        "documents": doc_results.get("doc_summaries", {}),
        "shareholders": doc_results.get("shareholders", []),
        "financial_summary": doc_results.get("financial_summary"),
        "external_events": [],
        "profile_data": profile_data or {},
    }

    # Merge profile data if available
    if profile_data and profile_data.get("profile"):
        profile = profile_data["profile"]
        context["profile"] = profile
        context["snapshot"]["corp"]["industry_code"] = profile.get("industry_code")

    return context


def _extract_signals_for_new_kyc(context: dict, signal_pipeline: SignalExtractionPipeline) -> list:
    """Extract signals using LLM for new KYC"""
    try:
        raw_signals = signal_pipeline.execute(context)
        return raw_signals
    except Exception as e:
        logger.error(f"Signal extraction failed: {e}")
        return []


def _save_new_kyc_result(job_dir: str, result: dict):
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
    신규 법인 KYC 분석 파이프라인

    4-Stage Pipeline (SNAPSHOT 스킵):
    1. DOC_INGEST - 업로드 서류 파싱
    2. PROFILING - 외부 정보 기반 프로파일링
    3. SIGNAL - 리스크/기회 시그널 추출
    4. INSIGHT - 종합 인사이트 생성
    """
    logger.info(f"Starting new KYC pipeline for job={job_id}, job_dir={job_dir}")

    signal_pipeline = SignalExtractionPipeline()
    validation_pipeline = ValidationPipeline()

    try:
        # Stage 1: DOC_INGEST (PDF 파싱)
        update_new_kyc_job_progress(job_id, JobStatus.RUNNING, "DOC_INGEST", 10)
        doc_results = _parse_documents_from_dir(job_dir)
        logger.info(f"DOC_INGEST completed: {list(doc_results['doc_summaries'].keys())}")

        # Update corp_name from parsed documents if not provided
        if not corp_name:
            corp_name = doc_results.get("corp_info", {}).get("corp_name", "Unknown")

        update_new_kyc_job_progress(job_id, JobStatus.RUNNING, "DOC_INGEST", 30)

        # Stage 2: PROFILING (외부 정보 검색)
        update_new_kyc_job_progress(job_id, JobStatus.RUNNING, "PROFILING", 35)
        profile_data = {"profile": None, "selected_queries": [], "query_details": []}

        if corp_name and corp_name != "Unknown":
            import asyncio
            try:
                profiling_pipeline = get_corp_profiling_pipeline()
                industry_code = doc_results.get("corp_info", {}).get("industry_code", "")

                try:
                    loop = asyncio.get_running_loop()
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            profiling_pipeline.execute(
                                corp_id=f"new-{job_id}",
                                corp_name=corp_name,
                                industry_code=industry_code,
                                db_session=None,
                                llm_service=signal_pipeline.llm_service if hasattr(signal_pipeline, 'llm_service') else None,
                            )
                        )
                        profile_result = future.result(timeout=120)
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        profile_result = loop.run_until_complete(
                            profiling_pipeline.execute(
                                corp_id=f"new-{job_id}",
                                corp_name=corp_name,
                                industry_code=industry_code,
                                db_session=None,
                                llm_service=signal_pipeline.llm_service if hasattr(signal_pipeline, 'llm_service') else None,
                            )
                        )
                    finally:
                        loop.close()

                profile_data = {
                    "profile": profile_result.profile,
                    "selected_queries": profile_result.selected_queries,
                    "query_details": profile_result.query_details,
                }
                logger.info(f"PROFILING completed: confidence={profile_result.profile.get('profile_confidence')}")
            except Exception as e:
                logger.warning(f"PROFILING failed (non-fatal): {e}")

        update_new_kyc_job_progress(job_id, JobStatus.RUNNING, "PROFILING", 50)

        # Stage 3: SIGNAL (LLM 시그널 추출)
        update_new_kyc_job_progress(job_id, JobStatus.RUNNING, "SIGNAL", 55)
        context = _build_new_kyc_context(doc_results, corp_name, profile_data)
        raw_signals = _extract_signals_for_new_kyc(context, signal_pipeline)

        # Deduplicate and validate
        deduped_signals = deduplicate_within_batch(raw_signals)
        validated_signals = validation_pipeline.execute(deduped_signals)

        logger.info(f"SIGNAL completed: {len(validated_signals)} signals extracted")
        update_new_kyc_job_progress(job_id, JobStatus.RUNNING, "SIGNAL", 80)

        # Stage 4: INSIGHT (종합 인사이트)
        update_new_kyc_job_progress(job_id, JobStatus.RUNNING, "INSIGHT", 85)
        insight = _generate_new_kyc_insight(validated_signals, context, signal_pipeline)
        update_new_kyc_job_progress(job_id, JobStatus.RUNNING, "INSIGHT", 95)

        # Build final result
        result = {
            "job_id": job_id,
            "corp_info": doc_results.get("corp_info", {}),
            "financial_summary": doc_results.get("financial_summary"),
            "shareholders": doc_results.get("shareholders", []),
            "signals": [_format_signal(s) for s in validated_signals],
            "insight": insight,
            "created_at": datetime.now(UTC).isoformat(),
        }

        # Save result to file
        _save_new_kyc_result(job_dir, result)

        # Update job status to DONE
        update_new_kyc_job_progress(job_id, JobStatus.DONE, "INSIGHT", 100)

        logger.info(f"New KYC pipeline completed: job={job_id}, signals={len(validated_signals)}")

        return {
            "status": "success",
            "job_id": job_id,
            "signals_created": len(validated_signals),
        }

    except Exception as e:
        logger.error(f"New KYC pipeline failed for job={job_id}: {str(e)}")
        update_new_kyc_job_progress(
            job_id,
            JobStatus.FAILED,
            error_code="PIPELINE_ERROR",
            error_message=str(e)[:500],
        )

        # Save error result
        error_result = {
            "job_id": job_id,
            "error": str(e),
            "created_at": datetime.now(UTC).isoformat(),
        }
        _save_new_kyc_result(job_dir, error_result)

        raise


def _generate_new_kyc_insight(signals: list, context: dict, signal_pipeline: SignalExtractionPipeline) -> str:
    """Generate insight summary for new KYC analysis"""
    if not signals:
        return "분석된 시그널이 없습니다. 추가 서류를 제출하시면 더 정확한 분석이 가능합니다."

    try:
        corp_name = context.get("corp_info", {}).get("corp_name", "해당 기업")

        # Count by impact direction
        risk_count = sum(1 for s in signals if s.get("impact_direction") == "RISK")
        opp_count = sum(1 for s in signals if s.get("impact_direction") == "OPPORTUNITY")
        neutral_count = len(signals) - risk_count - opp_count

        # Build signal summary
        signal_summaries = []
        for s in signals[:5]:  # Top 5 signals
            signal_summaries.append(f"- {s.get('title', '')}: {s.get('summary', '')[:100]}")

        signal_text = "\n".join(signal_summaries)

        prompt = f"""
        다음은 신규 기업 KYC 분석 결과입니다. 2-3문장으로 간결하게 종합 인사이트를 작성해주세요.

        기업명: {corp_name}
        분석된 시그널 수: {len(signals)}개 (리스크 {risk_count}, 기회 {opp_count}, 중립 {neutral_count})

        주요 시그널:
        {signal_text}

        인사이트 작성 시 유의사항:
        - 단정적 표현 금지 (예: "반드시", "즉시 조치 필요")
        - 허용 표현 사용 (예: "~로 추정됨", "~가능성 있음", "검토 권고")
        - 금융기관 심사 담당자 관점에서 작성
        """

        if hasattr(signal_pipeline, 'llm_service'):
            insight = signal_pipeline.llm_service.generate(prompt)
            return insight.strip()
        else:
            # Fallback: simple summary
            return f"{corp_name}에 대한 KYC 분석 결과, {len(signals)}개의 시그널이 감지되었습니다. (리스크 {risk_count}건, 기회 {opp_count}건) 세부 내용을 검토하시기 바랍니다."

    except Exception as e:
        logger.warning(f"Insight generation failed: {e}")
        return f"총 {len(signals)}개의 시그널이 감지되었습니다. 세부 내용을 확인해 주세요."


def _format_signal(signal: dict) -> dict:
    """Format signal for API response"""
    return {
        "signal_id": signal.get("signal_id") or str(uuid.uuid4()),
        "signal_type": signal.get("signal_type", "DIRECT"),
        "event_type": signal.get("event_type", ""),
        "impact_direction": signal.get("impact_direction", "NEUTRAL"),
        "impact_strength": signal.get("impact_strength", "MED"),
        "confidence": signal.get("confidence", "MED"),
        "title": signal.get("title", ""),
        "summary": signal.get("summary", ""),
        "evidences": signal.get("evidences", []),
    }
