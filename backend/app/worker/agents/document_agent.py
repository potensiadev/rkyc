"""
Document Agent
PDF 문서 파싱을 담당하는 Agent

각 문서 타입별로 독립적인 Agent 인스턴스가 생성되어 병렬 실행
"""

import logging
import os
from typing import Optional

from app.worker.agents.base import BaseAgent, AgentResult, AgentStatus

logger = logging.getLogger(__name__)


# 문서 타입 정의
DOC_TYPES = {
    "BIZ_REG": {
        "name": "사업자등록증",
        "required": True,
        "parser": "BizRegParser",
        "extracts": ["corp_name", "biz_no", "ceo_name", "address", "founded_date", "biz_type", "biz_item"],
    },
    "REGISTRY": {
        "name": "법인등기부등본",
        "required": False,
        "parser": "RegistryParser",
        "extracts": ["corp_reg_no", "capital", "corp_name", "executives"],
    },
    "SHAREHOLDERS": {
        "name": "주주명부",
        "required": False,
        "parser": "ShareholdersParser",
        "extracts": ["shareholders"],
    },
    "FINANCIAL": {
        "name": "재무제표",
        "required": False,
        "parser": "FinStatementParser",
        "extracts": ["revenue", "operating_profit", "net_income", "total_assets", "total_liabilities", "debt_ratio"],
    },
    "AOI": {
        "name": "정관",
        "required": False,
        "parser": "AoiParser",
        "extracts": ["business_purpose", "share_types", "governance_rules"],
    },
}


class DocumentAgent(BaseAgent):
    """
    단일 문서 파싱 Agent

    Usage:
        agent = DocumentAgent(doc_type="BIZ_REG")
        result = await agent.run({"job_dir": "/tmp/job-123"})
    """

    def __init__(self, doc_type: str, timeout_seconds: int = 60):
        super().__init__(
            agent_type=f"DocumentAgent-{doc_type}",
            timeout_seconds=timeout_seconds
        )
        self.doc_type = doc_type
        self.doc_config = DOC_TYPES.get(doc_type, {})

    async def execute(self, context: dict) -> AgentResult:
        """
        문서 파싱 실행

        Context 필수 키:
            - job_dir: 업로드 파일 경로
        """
        job_dir = context.get("job_dir")
        if not job_dir:
            return self._failed("job_dir is required in context")

        file_path = os.path.join(job_dir, f"{self.doc_type}.pdf")

        # 파일 존재 확인
        if not os.path.exists(file_path):
            if self.doc_config.get("required"):
                return self._failed(f"Required document not found: {self.doc_type}")
            return self._skipped(f"Optional document not uploaded: {self.doc_type}")

        # 파서 로드 및 실행
        try:
            parser = self._get_parser()
            if not parser:
                return self._failed(f"Parser not found for {self.doc_type}")

            parsed_data = parser.parse(file_path)

            if not parsed_data:
                return self._failed(f"Failed to parse {self.doc_type}: empty result")

            # 메타데이터 추가
            metadata = {
                "doc_type": self.doc_type,
                "doc_name": self.doc_config.get("name", self.doc_type),
                "file_path": file_path,
                "file_size": os.path.getsize(file_path),
                "extracted_fields": list(parsed_data.keys()),
            }

            return self._success(
                data={"parsed": parsed_data, "doc_type": self.doc_type},
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"[{self.agent_id}] Parse error: {e}")
            return self._failed(f"Parse error: {str(e)[:200]}")

    def _get_parser(self):
        """문서 타입에 맞는 파서 인스턴스 반환"""
        parser_name = self.doc_config.get("parser")

        if parser_name == "BizRegParser":
            from app.worker.pipelines.doc_parsers import BizRegParser
            return BizRegParser()
        elif parser_name == "RegistryParser":
            from app.worker.pipelines.doc_parsers import RegistryParser
            return RegistryParser()
        elif parser_name == "ShareholdersParser":
            from app.worker.pipelines.doc_parsers import ShareholdersParser
            return ShareholdersParser()
        elif parser_name == "FinStatementParser":
            from app.worker.pipelines.doc_parsers import FinStatementParser
            return FinStatementParser()
        elif parser_name == "AoiParser":
            from app.worker.pipelines.doc_parsers import AoiParser
            return AoiParser()
        else:
            return None


class DocumentAgentPool:
    """
    Document Agent Pool

    여러 문서를 병렬로 파싱하기 위한 Pool 관리자
    """

    def __init__(self, job_dir: str):
        self.job_dir = job_dir
        self.agents: list[DocumentAgent] = []

    def create_agents(self, doc_types: Optional[list[str]] = None) -> list[DocumentAgent]:
        """
        파싱할 문서 타입별 Agent 생성

        Args:
            doc_types: 파싱할 문서 타입 목록. None이면 존재하는 파일만

        Returns:
            생성된 Agent 목록
        """
        if doc_types is None:
            # 업로드된 파일만 확인
            doc_types = []
            for doc_type in DOC_TYPES.keys():
                file_path = os.path.join(self.job_dir, f"{doc_type}.pdf")
                if os.path.exists(file_path):
                    doc_types.append(doc_type)

        self.agents = [DocumentAgent(doc_type) for doc_type in doc_types]
        logger.info(f"Created {len(self.agents)} DocumentAgents: {doc_types}")
        return self.agents

    async def run_parallel(self) -> dict[str, AgentResult]:
        """
        모든 Agent 병렬 실행

        Returns:
            {doc_type: AgentResult} 형태의 결과 딕셔너리
        """
        import asyncio

        context = {"job_dir": self.job_dir}

        # 병렬 실행
        tasks = [agent.run(context) for agent in self.agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 매핑
        result_map = {}
        for agent, result in zip(self.agents, results):
            doc_type = agent.doc_type
            if isinstance(result, Exception):
                result_map[doc_type] = AgentResult(
                    agent_id=agent.agent_id,
                    agent_type=agent.agent_type,
                    status=AgentStatus.FAILED,
                    error=str(result),
                )
            else:
                result_map[doc_type] = result

        return result_map

    def merge_results(self, results: dict[str, AgentResult]) -> dict:
        """
        여러 Agent 결과를 하나의 통합 결과로 병합

        Returns:
            통합된 corp_info, shareholders, financial_summary 등
        """
        merged = {
            "corp_info": {},
            "shareholders": [],
            "financial_summary": None,
            "doc_summaries": {},
            "parse_stats": {
                "total": len(results),
                "success": 0,
                "failed": 0,
                "skipped": 0,
            },
        }

        for doc_type, result in results.items():
            # 통계 업데이트
            if result.status == AgentStatus.SUCCESS:
                merged["parse_stats"]["success"] += 1
            elif result.status == AgentStatus.FAILED:
                merged["parse_stats"]["failed"] += 1
            elif result.status == AgentStatus.SKIPPED:
                merged["parse_stats"]["skipped"] += 1

            # 성공한 결과만 병합
            if not result.is_success():
                continue

            parsed = result.data.get("parsed", {})
            merged["doc_summaries"][doc_type] = parsed

            # BIZ_REG: 기업 기본 정보
            if doc_type == "BIZ_REG":
                merged["corp_info"].update({
                    "corp_name": parsed.get("corp_name"),
                    "biz_no": parsed.get("biz_no"),
                    "ceo_name": parsed.get("ceo_name"),
                    "address": parsed.get("address"),
                    "founded_date": parsed.get("founded_date"),
                    "industry": parsed.get("biz_type") or parsed.get("biz_item"),
                })

            # REGISTRY: 법인 정보
            elif doc_type == "REGISTRY":
                merged["corp_info"].update({
                    "corp_reg_no": parsed.get("corp_reg_no"),
                    "capital": parsed.get("capital"),
                })
                if not merged["corp_info"].get("corp_name"):
                    merged["corp_info"]["corp_name"] = parsed.get("corp_name")

            # SHAREHOLDERS: 주주 정보
            elif doc_type == "SHAREHOLDERS":
                shareholders = parsed.get("shareholders", [])
                merged["shareholders"] = shareholders

            # FINANCIAL: 재무 요약
            elif doc_type == "FINANCIAL":
                from datetime import datetime
                merged["financial_summary"] = {
                    "year": parsed.get("fiscal_year", datetime.now().year),
                    "revenue": parsed.get("revenue"),
                    "operating_profit": parsed.get("operating_profit"),
                    "debt_ratio": parsed.get("debt_ratio"),
                }

        return merged
