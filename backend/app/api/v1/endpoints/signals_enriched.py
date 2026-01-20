"""
rKYC Signals Enriched API Endpoints
Extended signal detail with rich analysis data

Endpoints:
- GET /signals/{signal_id}/enriched - 풍부한 시그널 상세
- GET /signals/{signal_id}/similar-cases - 유사 과거 케이스
- GET /signals/{signal_id}/verifications - 검증 결과
- GET /signals/{signal_id}/impact - 영향도 분석
- GET /signals/{signal_id}/related - 관련 시그널
- GET /corporations/{corp_id}/risk-profile - 기업 리스크 프로파일
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, and_, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.signal import (
    SignalIndex,
    Signal,
    Evidence,
    SignalType,
    ImpactDirection,
    ImpactStrength,
)
from app.schemas.signal import SignalStatusEnum
from app.schemas.signal_enriched import (
    SignalEnrichedDetailResponse,
    SimilarCaseResponse,
    VerificationResponse,
    ImpactAnalysisResponse,
    RelatedSignalResponse,
    CorpContextResponse,
    EnrichedEvidenceResponse,
    CorpRiskProfile,
    SourceCredibility,
    VerificationStatus,
)

router = APIRouter()


@router.get("/{signal_id}/enriched", response_model=SignalEnrichedDetailResponse)
async def get_signal_enriched_detail(
    signal_id: UUID,
    include_similar_cases: bool = Query(True, description="유사 케이스 포함"),
    include_verifications: bool = Query(True, description="검증 결과 포함"),
    include_impact: bool = Query(True, description="영향도 분석 포함"),
    include_related: bool = Query(True, description="관련 시그널 포함"),
    db: AsyncSession = Depends(get_db),
):
    """
    풍부한 시그널 상세 조회

    기본 시그널 정보 + 분석 메타데이터 + 컨텍스트 + 유사 케이스 등
    """
    # 1. 기본 시그널 정보 조회 (SignalIndex + Signal JOIN)
    combined_query = (
        select(SignalIndex, Signal)
        .outerjoin(Signal, Signal.signal_id == SignalIndex.signal_id)
        .where(SignalIndex.signal_id == signal_id)
    )
    combined_result = await db.execute(combined_query)
    row = combined_result.one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Signal not found")

    signal_index, signal = row

    # 2. Evidence 조회 (확장된 정보 포함)
    evidence_query = select(Evidence).where(Evidence.signal_id == signal_id).order_by(Evidence.created_at.desc())
    evidence_result = await db.execute(evidence_query)
    evidences_raw = evidence_result.scalars().all()

    # Evidence 변환 (소스 신뢰도 추가)
    evidences = []
    for e in evidences_raw:
        # URL에서 도메인 추출
        source_domain = None
        if e.ref_type == "URL" and e.ref_value:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(e.ref_value)
                source_domain = parsed.netloc
            except:
                pass

        # 소스 신뢰도 결정
        credibility = _determine_source_credibility(e.ref_value, source_domain)

        evidences.append(EnrichedEvidenceResponse(
            evidence_id=e.evidence_id,
            signal_id=e.signal_id,
            evidence_type=e.evidence_type,
            ref_type=e.ref_type,
            ref_value=e.ref_value,
            snippet=e.snippet,
            meta=e.meta,
            created_at=e.created_at,
            source_credibility=credibility,
            verification_status="VERIFIED" if credibility in [SourceCredibility.OFFICIAL, SourceCredibility.MAJOR_MEDIA] else "UNVERIFIED",
            source_domain=source_domain,
            is_primary_source=e.evidence_type == "INTERNAL_FIELD" or credibility == SourceCredibility.OFFICIAL,
        ))

    # 3. 기업 컨텍스트 조회 (Corp Profile)
    corp_context = await _get_corp_context(db, signal_index.corp_id)

    # 4. 유사 과거 케이스 조회
    similar_cases = []
    if include_similar_cases:
        similar_cases = await _get_similar_cases(db, signal_id, signal_index)

    # 5. 검증 결과 조회
    verifications = []
    if include_verifications:
        verifications = await _get_verifications(db, signal_id, evidences)

    # 6. 영향도 분석 조회
    impact_analysis = []
    if include_impact:
        impact_analysis = await _get_impact_analysis(db, signal_id, signal_index, corp_context)

    # 7. 관련 시그널 조회
    related_signals = []
    if include_related:
        related_signals = await _get_related_signals(db, signal_id, signal_index)

    # 8. 인사이트 발췌 조회
    insight_excerpt = await _get_insight_excerpt(db, signal_index.corp_id, signal_index.event_type)

    # 응답 구성
    return SignalEnrichedDetailResponse(
        signal_id=signal_index.signal_id,
        corp_id=signal_index.corp_id,
        corp_name=signal_index.corp_name,
        industry_code=signal_index.industry_code,
        signal_type=signal_index.signal_type,
        event_type=signal_index.event_type,
        impact_direction=signal_index.impact_direction,
        impact_strength=signal_index.impact_strength,
        confidence=signal_index.confidence,
        title=signal_index.title,
        summary=signal.summary if signal else signal_index.summary_short or "",
        summary_short=signal_index.summary_short,
        signal_status=signal.signal_status if signal else SignalStatusEnum.NEW,
        evidence_count=signal_index.evidence_count,
        detected_at=signal_index.detected_at,
        reviewed_at=signal.reviewed_at if signal else None,
        dismissed_at=signal.dismissed_at if signal else None,
        dismiss_reason=signal.dismiss_reason if signal else None,
        evidences=evidences,
        analysis_reasoning=_generate_analysis_reasoning(signal_index, evidences, corp_context),
        llm_model="claude-opus-4-5-20251101",  # 현재 사용 모델
        corp_context=corp_context,
        similar_cases=similar_cases,
        verifications=verifications,
        impact_analysis=impact_analysis,
        related_signals=related_signals,
        insight_excerpt=insight_excerpt,
    )


@router.get("/{signal_id}/similar-cases", response_model=List[SimilarCaseResponse])
async def get_signal_similar_cases(
    signal_id: UUID,
    limit: int = Query(5, ge=1, le=20),
    min_similarity: float = Query(0.6, ge=0, le=1),
    db: AsyncSession = Depends(get_db),
):
    """유사 과거 케이스 조회"""
    # 시그널 존재 확인
    signal_query = select(SignalIndex).where(SignalIndex.signal_id == signal_id)
    signal_result = await db.execute(signal_query)
    signal_index = signal_result.scalar_one_or_none()

    if not signal_index:
        raise HTTPException(status_code=404, detail="Signal not found")

    return await _get_similar_cases(db, signal_id, signal_index, limit, min_similarity)


@router.get("/{signal_id}/related", response_model=List[RelatedSignalResponse])
async def get_related_signals(
    signal_id: UUID,
    relation_types: Optional[List[str]] = Query(None, description="관계 유형 필터"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """관련 시그널 조회"""
    signal_query = select(SignalIndex).where(SignalIndex.signal_id == signal_id)
    signal_result = await db.execute(signal_query)
    signal_index = signal_result.scalar_one_or_none()

    if not signal_index:
        raise HTTPException(status_code=404, detail="Signal not found")

    return await _get_related_signals(db, signal_id, signal_index, limit, relation_types)


# =============================================================================
# Helper Functions
# =============================================================================

def _determine_source_credibility(ref_value: str, domain: str) -> SourceCredibility:
    """소스 신뢰도 결정"""
    if not ref_value:
        return SourceCredibility.UNKNOWN

    # 내부 데이터
    if ref_value.startswith("/"):
        return SourceCredibility.OFFICIAL

    # 공식 소스
    official_domains = [
        "dart.fss.or.kr", "kind.krx.co.kr", "www.fss.or.kr",
        "kostat.go.kr", "mof.go.kr", "motie.go.kr",
    ]
    if domain and any(d in domain for d in official_domains):
        return SourceCredibility.OFFICIAL

    # 주요 언론
    major_media = [
        "mk.co.kr", "hankyung.com", "sedaily.com", "edaily.co.kr",
        "yna.co.kr", "reuters.com", "bloomberg.com", "wsj.com",
    ]
    if domain and any(d in domain for d in major_media):
        return SourceCredibility.MAJOR_MEDIA

    # 일반 뉴스
    if domain:
        return SourceCredibility.MINOR_MEDIA

    return SourceCredibility.UNKNOWN


async def _get_corp_context(db: AsyncSession, corp_id: str) -> Optional[CorpContextResponse]:
    """기업 컨텍스트 조회"""
    # Corp 테이블 + Profile 테이블 조회
    query = text("""
        SELECT
            c.corp_id,
            c.corp_name,
            c.industry_code,
            im.industry_name,
            p.revenue_krw,
            p.employee_count,
            p.export_ratio_pct,
            p.country_exposure,
            p.key_materials,
            p.key_customers,
            p.overall_confidence,
            p.updated_at as profile_updated_at,
            s.snapshot_json
        FROM corp c
        LEFT JOIN industry_master im ON c.industry_code = im.industry_code
        LEFT JOIN rkyc_corp_profile p ON c.corp_id = p.corp_id
        LEFT JOIN rkyc_internal_snapshot_latest sl ON c.corp_id = sl.corp_id
        LEFT JOIN rkyc_internal_snapshot s ON sl.snapshot_id = s.snapshot_id
        WHERE c.corp_id = :corp_id
    """)

    result = await db.execute(query, {"corp_id": corp_id})
    row = result.one_or_none()

    if not row:
        return None

    # Snapshot에서 내부 데이터 추출
    snapshot_json = row.snapshot_json or {}
    credit_data = snapshot_json.get("credit", {}).get("loan_summary", {})
    kyc_data = snapshot_json.get("corp", {}).get("kyc_status", {})

    # country_exposure 파싱
    country_exposure = row.country_exposure
    if isinstance(country_exposure, str):
        try:
            import json
            country_exposure = json.loads(country_exposure)
        except:
            country_exposure = []

    return CorpContextResponse(
        corp_id=row.corp_id,
        corp_name=row.corp_name,
        industry_code=row.industry_code,
        industry_name=row.industry_name,
        revenue_krw=row.revenue_krw,
        employee_count=row.employee_count,
        export_ratio_pct=row.export_ratio_pct,
        country_exposure=country_exposure if isinstance(country_exposure, list) else None,
        key_materials=row.key_materials,
        key_customers=row.key_customers,
        supply_chain_risk=_assess_supply_chain_risk(country_exposure, row.key_materials),
        internal_risk_grade=kyc_data.get("internal_risk_grade"),
        overdue_flag=credit_data.get("overdue_flag"),
        total_exposure_krw=credit_data.get("total_exposure_krw"),
        profile_confidence=row.overall_confidence,
        profile_updated_at=row.profile_updated_at,
    )


def _assess_supply_chain_risk(country_exposure, key_materials) -> str:
    """공급망 리스크 평가"""
    risk_countries = {"중국", "러시아", "북한", "이란", "China", "Russia"}

    if country_exposure:
        if isinstance(country_exposure, list):
            if any(c in risk_countries for c in country_exposure):
                return "HIGH"
        elif isinstance(country_exposure, dict):
            if any(c in risk_countries for c in country_exposure.keys()):
                return "HIGH"

    if key_materials and len(key_materials) > 0:
        # 원자재 의존성이 있으면 중간 리스크
        return "MED"

    return "LOW"


async def _get_similar_cases(
    db: AsyncSession,
    signal_id: UUID,
    signal_index: SignalIndex,
    limit: int = 5,
    min_similarity: float = 0.6,
) -> List[SimilarCaseResponse]:
    """유사 과거 케이스 조회 (같은 업종/이벤트 타입 기반)"""
    # 실제 구현에서는 pgvector 유사도 검색 사용
    # 현재는 같은 업종 + 같은 이벤트 타입의 과거 시그널 조회
    query = (
        select(SignalIndex, Signal)
        .outerjoin(Signal, Signal.signal_id == SignalIndex.signal_id)
        .where(
            and_(
                SignalIndex.signal_id != signal_id,
                or_(
                    SignalIndex.industry_code == signal_index.industry_code,
                    SignalIndex.event_type == signal_index.event_type,
                )
            )
        )
        .order_by(SignalIndex.detected_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    similar_cases = []
    for row in rows:
        idx, sig = row
        # 유사도 계산 (간단한 규칙 기반)
        similarity = 0.5
        if idx.industry_code == signal_index.industry_code:
            similarity += 0.2
        if idx.event_type == signal_index.event_type:
            similarity += 0.2
        if idx.signal_type == signal_index.signal_type:
            similarity += 0.1

        if similarity >= min_similarity:
            similar_cases.append(SimilarCaseResponse(
                id=idx.index_id,
                similarity_score=round(similarity, 3),
                corp_id=idx.corp_id,
                corp_name=idx.corp_name,
                industry_code=idx.industry_code,
                signal_type=idx.signal_type.value if idx.signal_type else None,
                event_type=idx.event_type.value if idx.event_type else None,
                summary=idx.summary_short,
                outcome=None,  # 과거 결과는 별도 저장 필요
            ))

    return sorted(similar_cases, key=lambda x: x.similarity_score, reverse=True)


async def _get_verifications(
    db: AsyncSession,
    signal_id: UUID,
    evidences: List[EnrichedEvidenceResponse],
) -> List[VerificationResponse]:
    """검증 결과 생성 (Evidence 기반)"""
    verifications = []

    # Evidence별 검증 결과 생성
    for i, evidence in enumerate(evidences):
        verification_status = VerificationStatus.VERIFIED
        if evidence.source_credibility == SourceCredibility.UNKNOWN:
            verification_status = VerificationStatus.UNVERIFIED
        elif evidence.source_credibility == SourceCredibility.MINOR_MEDIA:
            verification_status = VerificationStatus.PARTIAL

        verifications.append(VerificationResponse(
            id=evidence.evidence_id,
            verification_type="SOURCE_CHECK",
            source_name=evidence.source_domain or evidence.evidence_type,
            source_url=evidence.ref_value if evidence.ref_type == "URL" else None,
            verification_status=verification_status,
            confidence_contribution=0.3 if verification_status == VerificationStatus.VERIFIED else 0.1,
            details={
                "credibility": evidence.source_credibility.value if evidence.source_credibility else None,
                "is_primary": evidence.is_primary_source,
            },
            verified_at=evidence.created_at,
        ))

    return verifications


async def _get_impact_analysis(
    db: AsyncSession,
    signal_id: UUID,
    signal_index: SignalIndex,
    corp_context: Optional[CorpContextResponse],
) -> List[ImpactAnalysisResponse]:
    """영향도 분석 생성"""
    analyses = []

    # 시그널 유형별 영향도 분석
    if signal_index.impact_direction.value == "RISK":
        # 신용 리스크 분석
        analyses.append(ImpactAnalysisResponse(
            id=signal_id,
            analysis_type="CREDIT",
            metric_name="신용등급 영향",
            current_value=None,
            projected_impact=None,
            impact_direction="DECREASE" if signal_index.impact_strength.value == "HIGH" else "STABLE",
            impact_percentage=-5.0 if signal_index.impact_strength.value == "HIGH" else -2.0,
            industry_avg=None,
            industry_percentile=30 if signal_index.impact_strength.value == "HIGH" else 50,
            reasoning=f"{signal_index.event_type.value} 이벤트로 인한 신용등급 하락 가능성 존재",
            data_source="Signal Analysis",
        ))

    if signal_index.impact_direction.value == "OPPORTUNITY":
        # 성장 기회 분석
        analyses.append(ImpactAnalysisResponse(
            id=signal_id,
            analysis_type="FINANCIAL",
            metric_name="매출 성장 잠재력",
            current_value=corp_context.revenue_krw if corp_context else None,
            projected_impact=None,
            impact_direction="INCREASE",
            impact_percentage=10.0 if signal_index.impact_strength.value == "HIGH" else 5.0,
            industry_avg=None,
            industry_percentile=70 if signal_index.impact_strength.value == "HIGH" else 60,
            reasoning=f"{signal_index.event_type.value} 이벤트로 인한 성장 기회 포착",
            data_source="Signal Analysis",
        ))

    # 규제 영향 (ENVIRONMENT 시그널)
    if signal_index.signal_type.value == "ENVIRONMENT":
        analyses.append(ImpactAnalysisResponse(
            id=signal_id,
            analysis_type="REGULATORY",
            metric_name="규제 영향도",
            current_value=None,
            projected_impact=None,
            impact_direction="INCREASE" if signal_index.impact_direction.value == "RISK" else "DECREASE",
            impact_percentage=None,
            industry_avg=None,
            industry_percentile=None,
            reasoning=f"정책/규제 변화가 {corp_context.industry_name if corp_context else '해당 업종'}에 미치는 영향 분석 필요",
            data_source="Policy Analysis",
        ))

    return analyses


async def _get_related_signals(
    db: AsyncSession,
    signal_id: UUID,
    signal_index: SignalIndex,
    limit: int = 10,
    relation_types: Optional[List[str]] = None,
) -> List[RelatedSignalResponse]:
    """관련 시그널 조회"""
    # 같은 기업의 다른 시그널 + 같은 업종의 유사 시그널
    query = (
        select(SignalIndex, Signal)
        .outerjoin(Signal, Signal.signal_id == SignalIndex.signal_id)
        .where(
            and_(
                SignalIndex.signal_id != signal_id,
                or_(
                    SignalIndex.corp_id == signal_index.corp_id,  # SAME_CORP
                    and_(
                        SignalIndex.industry_code == signal_index.industry_code,
                        SignalIndex.event_type == signal_index.event_type,
                    ),  # SAME_INDUSTRY
                )
            )
        )
        .order_by(SignalIndex.detected_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    related = []
    for row in rows:
        idx, sig = row

        # 관계 유형 결정
        if idx.corp_id == signal_index.corp_id:
            relation_type = "SAME_CORP"
            relation_strength = 0.9
        else:
            relation_type = "SAME_INDUSTRY"
            relation_strength = 0.6

        if relation_types and relation_type not in relation_types:
            continue

        related.append(RelatedSignalResponse(
            signal_id=idx.signal_id,
            relation_type=relation_type,
            relation_strength=relation_strength,
            corp_id=idx.corp_id,
            corp_name=idx.corp_name,
            signal_type=idx.signal_type,
            event_type=idx.event_type,
            impact_direction=idx.impact_direction,
            impact_strength=idx.impact_strength,
            title=idx.title,
            summary_short=idx.summary_short,
            detected_at=idx.detected_at,
            description=f"{'동일 기업' if relation_type == 'SAME_CORP' else '동일 업종'}의 관련 시그널",
        ))

    return related


async def _get_insight_excerpt(
    db: AsyncSession,
    corp_id: str,
    event_type,
) -> Optional[str]:
    """관련 인사이트 발췌"""
    # rkyc_insight 테이블에서 최신 인사이트 조회
    query = text("""
        SELECT content
        FROM rkyc_insight
        WHERE corp_id = :corp_id
        ORDER BY generated_at DESC
        LIMIT 1
    """)

    try:
        result = await db.execute(query, {"corp_id": corp_id})
        row = result.one_or_none()
        if row:
            # 첫 200자만 발췌
            return row.content[:200] + "..." if len(row.content) > 200 else row.content
    except:
        pass

    return None


def _generate_analysis_reasoning(
    signal_index: SignalIndex,
    evidences: List[EnrichedEvidenceResponse],
    corp_context: Optional[CorpContextResponse],
) -> str:
    """분석 근거 생성"""
    reasoning_parts = []

    # 1. 시그널 타입별 분석 근거
    if signal_index.signal_type.value == "DIRECT":
        reasoning_parts.append(
            f"본 시그널은 {signal_index.corp_name}에 직접적으로 영향을 미치는 "
            f"{signal_index.event_type.value} 이벤트입니다."
        )
    elif signal_index.signal_type.value == "INDUSTRY":
        reasoning_parts.append(
            f"본 시그널은 {corp_context.industry_name if corp_context else '해당'} 업종 전반에 "
            f"영향을 미치는 산업 이벤트로, {signal_index.corp_name}에도 영향이 예상됩니다."
        )
    elif signal_index.signal_type.value == "ENVIRONMENT":
        reasoning_parts.append(
            f"본 시그널은 정책/규제 변화로 인한 거시환경 이벤트입니다. "
            f"{signal_index.corp_name}의 사업 영역에 영향을 미칠 수 있습니다."
        )

    # 2. 영향도 분석
    impact_desc = "리스크" if signal_index.impact_direction.value == "RISK" else "기회"
    strength_desc = {"HIGH": "높은", "MED": "중간", "LOW": "낮은"}[signal_index.impact_strength.value]
    reasoning_parts.append(
        f"영향 분석 결과 {strength_desc} 수준의 {impact_desc} 요인으로 판단됩니다."
    )

    # 3. 근거 소스 분석
    official_count = sum(1 for e in evidences if e.source_credibility == SourceCredibility.OFFICIAL)
    major_media_count = sum(1 for e in evidences if e.source_credibility == SourceCredibility.MAJOR_MEDIA)

    if official_count > 0:
        reasoning_parts.append(f"공식 출처 {official_count}건을 포함하여 신뢰도가 높습니다.")
    elif major_media_count > 0:
        reasoning_parts.append(f"주요 언론 {major_media_count}건을 근거로 분석하였습니다.")

    # 4. 기업 컨텍스트 연결
    if corp_context:
        if corp_context.export_ratio_pct and corp_context.export_ratio_pct > 30:
            reasoning_parts.append(
                f"해당 기업의 수출 비중이 {corp_context.export_ratio_pct}%로 높아 "
                "글로벌 환경 변화에 민감할 수 있습니다."
            )
        if corp_context.overdue_flag:
            reasoning_parts.append("현재 연체 이력이 있어 추가적인 리스크 모니터링이 필요합니다.")

    return " ".join(reasoning_parts)
