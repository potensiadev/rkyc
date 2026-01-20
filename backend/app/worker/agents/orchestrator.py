"""
New KYC Multi-Agent Orchestrator
신규 법인 KYC 분석을 위한 Multi-Agent 오케스트레이터

Architecture:
    ┌─────────────────────────────────────────────────┐
    │              NewKycOrchestrator                 │
    │  (Coordinator - 전체 흐름 제어 및 상태 관리)     │
    └─────────────────────┬───────────────────────────┘
                          │
    ┌─────────────────────┼─────────────────────────┐
    │                     │                         │
    ▼                     ▼                         ▼
┌──────────┐      ┌──────────┐              ┌──────────┐
│  Doc     │      │  Doc     │   ...        │ Profile  │
│  Agent   │      │  Agent   │   (병렬)      │  Agent   │
│(BIZ_REG) │      │(FINANCIAL)│              │(External)│
└──────────┘      └──────────┘              └──────────┘
    │                     │                         │
    └─────────────────────┼─────────────────────────┘
                          │ (Phase 1 완료 대기)
                          ▼
                  ┌──────────────┐
                  │ Signal Agent │
                  │ (LLM 추출)   │
                  └──────────────┘
                          │
                          ▼
                  ┌──────────────┐
                  │ Insight Agent│
                  │ (종합 분석)  │
                  └──────────────┘
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Optional, Callable, Any

from app.worker.agents.base import AgentResult, AgentStatus
from app.worker.agents.document_agent import DocumentAgentPool
from app.worker.agents.profile_agent import ProfileAgent, LightProfileAgent
from app.worker.agents.signal_agent import SignalAgent
from app.worker.agents.insight_agent import InsightAgent, QuickInsightAgent

logger = logging.getLogger(__name__)


class OrchestratorPhase(str, Enum):
    """오케스트레이터 실행 단계"""
    INIT = "INIT"
    DOC_PARSE = "DOC_PARSE"           # Phase 1: 문서 파싱 (병렬)
    PROFILE = "PROFILE"                # Phase 1: 프로파일링 (병렬)
    SIGNAL = "SIGNAL"                  # Phase 2: 시그널 추출
    INSIGHT = "INSIGHT"                # Phase 3: 인사이트 생성
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


@dataclass
class OrchestratorConfig:
    """오케스트레이터 설정"""
    # 타임아웃 설정
    doc_parse_timeout: int = 60          # 문서 파싱 타임아웃 (초)
    profile_timeout: int = 120           # 프로파일링 타임아웃 (초)
    signal_timeout: int = 90             # 시그널 추출 타임아웃 (초)
    insight_timeout: int = 60            # 인사이트 생성 타임아웃 (초)
    total_timeout: int = 300             # 전체 타임아웃 (초)

    # 동작 설정
    parallel_doc_parse: bool = True      # 문서 병렬 파싱
    skip_profile_on_unknown: bool = True # 기업명 미상 시 프로파일 스킵
    use_light_profile: bool = False      # 경량 프로파일 사용 (데모용)
    use_quick_insight: bool = False      # 빠른 인사이트 사용 (데모용)

    # 재시도 설정
    max_retries: int = 2
    retry_delay: float = 1.0


@dataclass
class OrchestratorState:
    """오케스트레이터 상태"""
    phase: OrchestratorPhase = OrchestratorPhase.INIT
    start_time: Optional[float] = None
    phase_start_time: Optional[float] = None

    # Phase 결과
    doc_results: dict = field(default_factory=dict)
    profile_result: Optional[AgentResult] = None
    signal_result: Optional[AgentResult] = None
    insight_result: Optional[AgentResult] = None

    # 에러 추적
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def elapsed_ms(self) -> int:
        if self.start_time:
            return int((time.time() - self.start_time) * 1000)
        return 0


@dataclass
class OrchestratorOutput:
    """오케스트레이터 최종 출력"""
    job_id: str
    corp_info: dict
    financial_summary: Optional[dict]
    shareholders: list
    signals: list
    insight: str
    created_at: str

    # 메타데이터
    phase: OrchestratorPhase
    execution_time_ms: int
    agent_stats: dict
    errors: list
    warnings: list

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "corp_info": self.corp_info,
            "financial_summary": self.financial_summary,
            "shareholders": self.shareholders,
            "signals": self.signals,
            "insight": self.insight,
            "created_at": self.created_at,
            "_meta": {
                "phase": self.phase.value,
                "execution_time_ms": self.execution_time_ms,
                "agent_stats": self.agent_stats,
                "errors": self.errors,
                "warnings": self.warnings,
            }
        }


class NewKycOrchestrator:
    """
    신규 법인 KYC Multi-Agent Orchestrator

    Usage:
        orchestrator = NewKycOrchestrator(config=OrchestratorConfig())
        result = await orchestrator.execute(job_id, job_dir, corp_name)
    """

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig()
        self.state = OrchestratorState()
        self._progress_callback: Optional[Callable[[str, int], None]] = None

    def set_progress_callback(self, callback: Callable[[str, int], None]):
        """진행 상황 콜백 설정 (Job 상태 업데이트용)"""
        self._progress_callback = callback

    def _update_progress(self, step: str, percent: int):
        """진행 상황 업데이트"""
        if self._progress_callback:
            try:
                self._progress_callback(step, percent)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

    async def execute(
        self,
        job_id: str,
        job_dir: str,
        corp_name: Optional[str] = None,
    ) -> OrchestratorOutput:
        """
        Multi-Agent 파이프라인 실행

        Args:
            job_id: Job ID
            job_dir: 업로드 파일 디렉토리
            corp_name: 기업명 (없으면 문서에서 추출)

        Returns:
            OrchestratorOutput: 최종 결과
        """
        self.state = OrchestratorState()
        self.state.start_time = time.time()

        logger.info(f"[Orchestrator] Starting job={job_id}")

        try:
            # ═══════════════════════════════════════════════════════════
            # Phase 1: 문서 파싱 + 프로파일링 (병렬)
            # ═══════════════════════════════════════════════════════════
            self.state.phase = OrchestratorPhase.DOC_PARSE
            self._update_progress("DOC_INGEST", 10)

            # 병렬 실행
            phase1_results = await self._execute_phase1(job_dir, corp_name)

            # 결과에서 corp_name 추출 (미제공 시)
            merged_docs = phase1_results["merged_docs"]
            if not corp_name or corp_name == "Unknown":
                corp_name = merged_docs.get("corp_info", {}).get("corp_name", "Unknown")

            self._update_progress("DOC_INGEST", 30)

            # ═══════════════════════════════════════════════════════════
            # Phase 2: 시그널 추출
            # ═══════════════════════════════════════════════════════════
            self.state.phase = OrchestratorPhase.SIGNAL
            self._update_progress("SIGNAL", 50)

            signal_context = self._build_signal_context(
                job_id=job_id,
                corp_name=corp_name,
                merged_docs=merged_docs,
                profile_result=phase1_results.get("profile_result"),
            )

            signal_agent = SignalAgent(timeout_seconds=self.config.signal_timeout)
            self.state.signal_result = await signal_agent.run(signal_context)

            signals = []
            if self.state.signal_result.is_success():
                signals = self.state.signal_result.data.get("signals", [])
            else:
                self.state.warnings.append(f"Signal extraction issue: {self.state.signal_result.error}")

            self._update_progress("SIGNAL", 75)

            # ═══════════════════════════════════════════════════════════
            # Phase 3: 인사이트 생성
            # ═══════════════════════════════════════════════════════════
            self.state.phase = OrchestratorPhase.INSIGHT
            self._update_progress("INSIGHT", 85)

            insight_context = {
                "signals": signals,
                "corp_info": merged_docs.get("corp_info", {}),
                "profile": phase1_results.get("profile_result", {}).data.get("profile") if phase1_results.get("profile_result") else None,
                "financial_summary": merged_docs.get("financial_summary"),
            }

            if self.config.use_quick_insight:
                insight_agent = QuickInsightAgent()
            else:
                insight_agent = InsightAgent(timeout_seconds=self.config.insight_timeout)

            self.state.insight_result = await insight_agent.run(insight_context)

            insight_text = ""
            if self.state.insight_result.is_success():
                insight_text = self.state.insight_result.data.get("insight", "")

            self._update_progress("INSIGHT", 95)

            # ═══════════════════════════════════════════════════════════
            # 완료
            # ═══════════════════════════════════════════════════════════
            self.state.phase = OrchestratorPhase.COMPLETE
            self._update_progress("INSIGHT", 100)

            return OrchestratorOutput(
                job_id=job_id,
                corp_info=merged_docs.get("corp_info", {}),
                financial_summary=merged_docs.get("financial_summary"),
                shareholders=merged_docs.get("shareholders", []),
                signals=signals,
                insight=insight_text,
                created_at=datetime.now(UTC).isoformat(),
                phase=self.state.phase,
                execution_time_ms=self.state.elapsed_ms(),
                agent_stats=self._collect_agent_stats(),
                errors=self.state.errors,
                warnings=self.state.warnings,
            )

        except asyncio.TimeoutError:
            self.state.phase = OrchestratorPhase.FAILED
            self.state.errors.append("Orchestrator timeout")
            raise

        except Exception as e:
            self.state.phase = OrchestratorPhase.FAILED
            self.state.errors.append(str(e))
            logger.error(f"[Orchestrator] Failed: {e}")
            raise

    async def _execute_phase1(self, job_dir: str, corp_name: Optional[str]) -> dict:
        """
        Phase 1: 문서 파싱 + 프로파일링 병렬 실행
        """
        tasks = []

        # Task 1: 문서 파싱 (병렬)
        doc_pool = DocumentAgentPool(job_dir)
        doc_pool.create_agents()

        async def run_doc_parse():
            results = await doc_pool.run_parallel()
            return doc_pool.merge_results(results), results

        tasks.append(run_doc_parse())

        # Task 2: 프로파일링 (corp_name 있을 때만)
        async def run_profile():
            if not corp_name or corp_name == "Unknown":
                if self.config.skip_profile_on_unknown:
                    return None

            if self.config.use_light_profile:
                agent = LightProfileAgent(timeout_seconds=self.config.profile_timeout)
            else:
                agent = ProfileAgent(timeout_seconds=self.config.profile_timeout)

            context = {
                "corp_name": corp_name,
                "corp_id": f"new-{job_dir.split('/')[-1]}",
            }
            return await agent.run(context)

        tasks.append(run_profile())

        # 병렬 실행
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 처리
        doc_result = results[0]
        if isinstance(doc_result, Exception):
            self.state.errors.append(f"Doc parse failed: {doc_result}")
            merged_docs, doc_results = {}, {}
        else:
            merged_docs, doc_results = doc_result
            self.state.doc_results = {
                k: v.to_dict() if hasattr(v, 'to_dict') else v
                for k, v in doc_results.items()
            }

        profile_result = results[1]
        if isinstance(profile_result, Exception):
            self.state.warnings.append(f"Profile failed: {profile_result}")
            profile_result = None
        self.state.profile_result = profile_result

        return {
            "merged_docs": merged_docs,
            "doc_results": doc_results,
            "profile_result": profile_result,
        }

    def _build_signal_context(
        self,
        job_id: str,
        corp_name: str,
        merged_docs: dict,
        profile_result: Optional[AgentResult],
    ) -> dict:
        """Signal Agent를 위한 컨텍스트 구성"""
        context = {
            "job_id": job_id,
            "corp_id": f"new-{job_id}",
            "corp_info": merged_docs.get("corp_info", {}),
            "doc_summaries": merged_docs.get("doc_summaries", {}),
            "shareholders": merged_docs.get("shareholders", []),
            "financial_summary": merged_docs.get("financial_summary"),
        }

        # 프로파일 데이터 추가
        if profile_result and profile_result.is_success():
            profile_data = profile_result.data
            context["profile"] = profile_data.get("profile")
            context["profile_data"] = {
                "profile": profile_data.get("profile"),
                "selected_queries": profile_data.get("selected_queries", []),
            }

        # corp_name 보장
        if not context["corp_info"].get("corp_name"):
            context["corp_info"]["corp_name"] = corp_name

        return context

    def _collect_agent_stats(self) -> dict:
        """Agent 실행 통계 수집"""
        stats = {
            "doc_agents": {},
            "profile_agent": None,
            "signal_agent": None,
            "insight_agent": None,
        }

        # Document Agents
        for doc_type, result in self.state.doc_results.items():
            if isinstance(result, dict):
                stats["doc_agents"][doc_type] = {
                    "status": result.get("status"),
                    "execution_time_ms": result.get("execution_time_ms"),
                }

        # Profile Agent
        if self.state.profile_result:
            stats["profile_agent"] = {
                "status": self.state.profile_result.status.value,
                "execution_time_ms": self.state.profile_result.execution_time_ms,
            }

        # Signal Agent
        if self.state.signal_result:
            stats["signal_agent"] = {
                "status": self.state.signal_result.status.value,
                "execution_time_ms": self.state.signal_result.execution_time_ms,
                "signal_count": len(self.state.signal_result.data.get("signals", [])),
            }

        # Insight Agent
        if self.state.insight_result:
            stats["insight_agent"] = {
                "status": self.state.insight_result.status.value,
                "execution_time_ms": self.state.insight_result.execution_time_ms,
            }

        return stats


# Factory function
def get_new_kyc_orchestrator(config: Optional[OrchestratorConfig] = None) -> NewKycOrchestrator:
    """NewKycOrchestrator 인스턴스 생성"""
    return NewKycOrchestrator(config=config)
