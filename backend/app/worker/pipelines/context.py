"""
Context Pipeline Stage
Stage 4: Build unified context from snapshot and external data

PRD v1.1 Banking Data Integration (2026-02-09):
- 은행 내부 데이터 (여신/수신/카드/담보/무역금융/재무제표) 주입
- 리스크/기회 알림을 LLM 컨텍스트에 추가
"""

import logging
from typing import Optional

from sqlalchemy import select

from app.worker.db import get_sync_db
from app.worker.llm.prompts import get_industry_name
from app.models.banking_data import BankingData

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
            # DART 공시 기반 정보 (100% Fact 데이터)
            "dart_corp_code": corporation.get("dart_corp_code"),
            "established_date": corporation.get("established_date"),
            "headquarters": corporation.get("headquarters"),
            "corp_class": corporation.get("corp_class"),
            "homepage_url": corporation.get("homepage_url"),
            "jurir_no": corporation.get("jurir_no"),
            "corp_name_eng": corporation.get("corp_name_eng"),
            "acc_mt": corporation.get("acc_mt"),
            "dart_updated_at": corporation.get("dart_updated_at"),

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

            # PRD v1.1: Banking Data Integration
            "banking_data": self._fetch_banking_data(corp_id),
        }

        # Log banking data summary
        banking = context.get("banking_data", {})
        risk_count = len(banking.get("risk_alerts", []))
        opp_count = len(banking.get("opportunity_signals", []))

        logger.info(
            f"CONTEXT stage completed: corp_name={context['corp_name']}, "
            f"document_facts={len(context['document_facts'])}, "
            f"external_events={len(context['external_events'])} "
            f"(direct={len(context['direct_events'])}, "
            f"industry={len(context['industry_events'])}, "
            f"environment={len(context['environment_events'])}), "
            f"banking_data=(risks={risk_count}, opportunities={opp_count})"
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

    def _fetch_banking_data(self, corp_id: str) -> dict:
        """
        Fetch banking data for signal extraction context.

        PRD v1.1 Banking Data Integration:
        - 여신 현황 (loan_exposure)
        - 수신 추이 (deposit_trend)
        - 법인카드 이용 (card_usage)
        - 담보 현황 (collateral_detail)
        - 무역금융 (trade_finance)
        - 재무제표 (financial_statements)
        - 리스크 알림 (risk_alerts)
        - 영업 기회 (opportunity_signals)
        """
        if not corp_id:
            return {}

        try:
            with get_sync_db() as db:
                query = (
                    select(BankingData)
                    .where(BankingData.corp_id == corp_id)
                    .order_by(BankingData.data_date.desc())
                    .limit(1)
                )
                result = db.execute(query)
                banking_data = result.scalar_one_or_none()

                if not banking_data:
                    logger.debug(f"No banking data found for corp_id={corp_id}")
                    return {}

                return {
                    "data_date": str(banking_data.data_date) if banking_data.data_date else None,
                    "loan_exposure": banking_data.loan_exposure or {},
                    "deposit_trend": banking_data.deposit_trend or {},
                    "card_usage": banking_data.card_usage or {},
                    "collateral_detail": banking_data.collateral_detail or {},
                    "trade_finance": banking_data.trade_finance or {},
                    "financial_statements": banking_data.financial_statements or {},
                    "risk_alerts": banking_data.risk_alerts or [],
                    "opportunity_signals": banking_data.opportunity_signals or [],
                }

        except Exception as e:
            logger.warning(f"Failed to fetch banking data for {corp_id}: {e}")
            return {}
