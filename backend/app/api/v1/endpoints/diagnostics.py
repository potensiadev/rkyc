"""
Diagnostics API Endpoints
파이프라인 진단 및 디버깅용 엔드포인트
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.core.config import settings
from app.worker.pipelines import (
    SnapshotPipeline,
    ContextPipeline,
    ExternalSearchPipeline,
    SignalExtractionPipeline,
    ValidationPipeline,
    DeduplicationPipeline,
    deduplicate_within_batch,
    NoSnapshotError,
    NoCorporationError,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/pipeline-test/{corp_id}")
async def test_pipeline_stages(
    corp_id: str,
    stages: Optional[str] = Query(
        default="snapshot,external,context,signal",
        description="Comma-separated stages to run: snapshot,external,context,signal"
    ),
):
    """
    파이프라인 단계별 테스트

    특정 기업에 대해 파이프라인의 각 단계를 실행하고 결과를 반환합니다.
    LLM 시그널 추출까지 테스트하려면 stages에 'signal'을 포함하세요.

    주의: 이 엔드포인트는 실제 LLM API를 호출할 수 있습니다.
    """
    stages_to_run = [s.strip().lower() for s in stages.split(",")]
    results = {
        "corp_id": corp_id,
        "stages_requested": stages_to_run,
        "stages_completed": [],
        "errors": [],
        "api_keys_status": {
            "perplexity": bool(settings.PERPLEXITY_API_KEY),
            "anthropic": bool(settings.ANTHROPIC_API_KEY),
            "openai": bool(settings.OPENAI_API_KEY),
            "google": bool(settings.GOOGLE_API_KEY),
        }
    }

    snapshot_data = None
    external_data = None
    context_data = None
    raw_signals = None

    # Stage 1: SNAPSHOT
    if "snapshot" in stages_to_run:
        try:
            snapshot_pipeline = SnapshotPipeline()
            snapshot_data = snapshot_pipeline.execute(corp_id)
            results["snapshot"] = {
                "success": True,
                "corp_name": snapshot_data.get("corporation", {}).get("corp_name"),
                "industry_code": snapshot_data.get("corporation", {}).get("industry_code"),
                "snapshot_version": snapshot_data.get("snapshot_version"),
                "has_loan": snapshot_data.get("snapshot_json", {}).get("credit", {}).get("has_loan"),
                "overdue_flag": snapshot_data.get("snapshot_json", {}).get("credit", {}).get("loan_summary", {}).get("overdue_flag"),
            }
            results["stages_completed"].append("snapshot")
        except (NoSnapshotError, NoCorporationError) as e:
            results["snapshot"] = {"success": False, "error": str(e)}
            results["errors"].append(f"snapshot: {e}")
        except Exception as e:
            results["snapshot"] = {"success": False, "error": str(e)}
            results["errors"].append(f"snapshot: {e}")

    # Stage 2: EXTERNAL (Perplexity search)
    if "external" in stages_to_run and snapshot_data:
        try:
            external_pipeline = ExternalSearchPipeline()
            corp_name = snapshot_data.get("corporation", {}).get("corp_name", "")
            industry_code = snapshot_data.get("corporation", {}).get("industry_code", "")

            external_data = external_pipeline.execute(
                corp_name=corp_name,
                industry_code=industry_code,
                corp_id=corp_id,
                profile_data=None,
            )

            results["external"] = {
                "success": True,
                "source": external_data.get("source"),
                "total_events": len(external_data.get("events", [])),
                "direct_events": len(external_data.get("direct_events", [])),
                "industry_events": len(external_data.get("industry_events", [])),
                "environment_events": len(external_data.get("environment_events", [])),
                "sample_events": external_data.get("events", [])[:2],  # First 2 events
            }
            results["stages_completed"].append("external")
        except Exception as e:
            results["external"] = {"success": False, "error": str(e)}
            results["errors"].append(f"external: {e}")

    # Stage 3: CONTEXT
    if "context" in stages_to_run and snapshot_data:
        try:
            context_pipeline = ContextPipeline()
            doc_data = {"documents_processed": 0, "facts_extracted": 0, "doc_summaries": {}}

            if external_data is None:
                external_data = {
                    "events": [],
                    "direct_events": [],
                    "industry_events": [],
                    "environment_events": [],
                    "source": "none",
                }

            context_data = context_pipeline.execute(snapshot_data, doc_data, external_data)

            results["context"] = {
                "success": True,
                "corp_name": context_data.get("corp_name"),
                "industry_name": context_data.get("industry_name"),
                "external_events_count": len(context_data.get("external_events", [])),
                "direct_events_count": len(context_data.get("direct_events", [])),
                "industry_events_count": len(context_data.get("industry_events", [])),
                "environment_events_count": len(context_data.get("environment_events", [])),
                "derived_hints": context_data.get("derived_hints"),
            }
            results["stages_completed"].append("context")
        except Exception as e:
            results["context"] = {"success": False, "error": str(e)}
            results["errors"].append(f"context: {e}")

    # Stage 4: SIGNAL (LLM extraction)
    if "signal" in stages_to_run and context_data:
        try:
            signal_pipeline = SignalExtractionPipeline()
            raw_signals = signal_pipeline.execute(context_data)

            results["signal"] = {
                "success": True,
                "raw_signal_count": len(raw_signals),
                "signals_preview": [
                    {
                        "signal_type": s.get("signal_type"),
                        "event_type": s.get("event_type"),
                        "title": s.get("title"),
                        "impact_direction": s.get("impact_direction"),
                    }
                    for s in raw_signals[:5]  # First 5 signals
                ],
            }
            results["stages_completed"].append("signal")

            # Also test deduplication
            if raw_signals:
                deduped_batch = deduplicate_within_batch(raw_signals)
                dedup_pipeline = DeduplicationPipeline()
                final_signals = dedup_pipeline.execute(deduped_batch, corp_id)

                results["deduplication"] = {
                    "after_batch_dedup": len(deduped_batch),
                    "after_db_dedup": len(final_signals),
                    "duplicates_removed": len(raw_signals) - len(final_signals),
                }

        except Exception as e:
            results["signal"] = {"success": False, "error": str(e)}
            results["errors"].append(f"signal: {e}")

    return results


@router.get("/llm-status")
async def check_llm_status():
    """
    LLM API 키 및 연결 상태 확인
    """
    return {
        "api_keys": {
            "anthropic": {
                "configured": bool(settings.ANTHROPIC_API_KEY),
                "key_prefix": settings.ANTHROPIC_API_KEY[:10] + "..." if settings.ANTHROPIC_API_KEY else None,
            },
            "openai": {
                "configured": bool(settings.OPENAI_API_KEY),
                "key_prefix": settings.OPENAI_API_KEY[:10] + "..." if settings.OPENAI_API_KEY else None,
            },
            "google": {
                "configured": bool(settings.GOOGLE_API_KEY),
                "key_prefix": settings.GOOGLE_API_KEY[:10] + "..." if settings.GOOGLE_API_KEY else None,
            },
            "perplexity": {
                "configured": bool(settings.PERPLEXITY_API_KEY),
                "key_prefix": settings.PERPLEXITY_API_KEY[:10] + "..." if settings.PERPLEXITY_API_KEY else None,
            },
        },
        "llm_verbose": settings.LLM_VERBOSE,
    }
