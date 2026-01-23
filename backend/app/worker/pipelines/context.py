"""
Context Pipeline Stage
Stage 4: Build unified context from snapshot and external data
"""

import logging
from typing import Optional

from sqlalchemy import select

from app.worker.db import get_sync_db
from app.worker.llm.prompts import get_industry_name

logger = logging.getLogger(__name__)


class ContextPipeline:
    """
    Stage 4: UNIFIED_CONTEXT - Build unified context

    Combines internal snapshot data with external events
    to create a unified context for LLM analysis.
    """

    def execute(
        self,
        snapshot_data: dict,
        doc_data: dict,
        external_data: dict,
    ) -> dict:
        """
        Execute context building stage.

        Args:
            snapshot_data: Output from SnapshotPipeline
            doc_data: Output from DocIngestPipeline (placeholder)
            external_data: Output from ExternalSearchPipeline

        Returns:
            dict containing unified context for LLM
        """
        corp_id = snapshot_data.get("corp_id", "")
        corporation = snapshot_data.get("corporation", {})
        snapshot_json = snapshot_data.get("snapshot_json", {})

        logger.info(f"CONTEXT stage starting for corp_id={corp_id}")

        # Get industry name
        industry_code = corporation.get("industry_code", "")
        industry_name = get_industry_name(industry_code)

        # Build unified context
        context = {
            # Corporation info
            "corp_id": corp_id,
            "corp_name": corporation.get("corp_name", ""),
            "corp_reg_no": corporation.get("corp_reg_no", ""),
            "biz_no": corporation.get("biz_no", ""),
            "industry_code": industry_code,
            "industry_name": industry_name,
            "ceo_name": corporation.get("ceo_name", ""),

            # Snapshot data
            "snapshot_version": snapshot_data.get("snapshot_version", 0),
            "snapshot_json": snapshot_json,

            # Document facts (Phase 2+ - currently empty)
            "document_facts": doc_data.get("facts", []),

            # External events (all combined for backward compatibility)
            "external_events": external_data.get("events", []),
            "external_source": external_data.get("source", "none"),

            # Categorized external events (new 3-track search)
            "direct_events": external_data.get("direct_events", []),
            "industry_events": external_data.get("industry_events", []),
            "environment_events": external_data.get("environment_events", []),

            # Profile data for ENVIRONMENT signal grounding
            "profile_data": external_data.get("profile_data", {}),
            # Direct profile reference for InsightPipeline
            "profile": external_data.get("profile_data", {}).get("profile", None),

            # Derived hints from snapshot
            "derived_hints": self._extract_derived_hints(snapshot_json),
        }

        logger.info(
            f"CONTEXT stage completed: corp_name={context['corp_name']}, "
            f"external_events={len(context['external_events'])} "
            f"(direct={len(context['direct_events'])}, "
            f"industry={len(context['industry_events'])}, "
            f"environment={len(context['environment_events'])})"
        )

        return context

    def _extract_derived_hints(self, snapshot_json: dict) -> dict:
        """
        Extract derived hints from snapshot for signal analysis.

        These hints help the LLM focus on important changes.
        """
        hints = {
            "has_loan": False,
            "has_overdue": False,
            "has_collateral": False,
            "risk_grade": None,
            "kyc_completed": False,
            "potential_signals": [],
        }

        if not snapshot_json:
            return hints

        # Check credit status
        credit = snapshot_json.get("credit", {})
        if credit:
            hints["has_loan"] = credit.get("has_loan", False)
            loan_summary = credit.get("loan_summary", {})
            hints["has_overdue"] = loan_summary.get("overdue_flag", False)
            hints["risk_grade"] = loan_summary.get("risk_grade_internal")

            # Potential signals from credit data
            if hints["has_overdue"]:
                hints["potential_signals"].append("OVERDUE_FLAG_ON")
            if hints["risk_grade"] in ["HIGH"]:
                hints["potential_signals"].append("INTERNAL_RISK_GRADE_CHANGE")

        # Check collateral
        collateral = snapshot_json.get("collateral", {})
        if collateral:
            hints["has_collateral"] = collateral.get("has_collateral", False)

        # Check KYC status
        corp_data = snapshot_json.get("corp", {})
        kyc_status = corp_data.get("kyc_status", {})
        if kyc_status:
            hints["kyc_completed"] = kyc_status.get("is_kyc_completed", False)
            internal_grade = kyc_status.get("internal_risk_grade")
            if internal_grade and internal_grade != hints["risk_grade"]:
                hints["potential_signals"].append("INTERNAL_RISK_GRADE_CHANGE")

        # Check derived hints from snapshot
        derived = snapshot_json.get("derived_hints", {})
        if derived:
            hints["potential_signals"].extend(
                derived.get("potential_signals", [])
            )

        return hints
