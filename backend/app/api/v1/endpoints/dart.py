"""
DART API Endpoints

주주 정보 검증 및 DART 공시 조회 API
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.dart_api import (
    get_corp_code,
    get_major_shareholders,
    verify_shareholders,
    get_verified_shareholders,
    load_corp_codes,
    _corp_code_loaded,
    # P0: Fact-Based APIs
    get_company_info,
    get_company_info_by_name,
    get_largest_shareholders,
    get_largest_shareholders_by_name,
    get_fact_based_profile,
    CompanyInfo,
    LargestShareholder,
    FactBasedProfileData,
    # P2: Financial Statement APIs
    get_financial_statements,
    get_financial_statements_by_name,
    FinancialStatement,
    # P3: Major Event APIs
    get_major_events,
    get_major_events_by_name,
    MajorEvent,
    MajorEventType,
    # P2/P3: Extended Profile
    get_extended_fact_profile,
    ExtendedFactProfile,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class CorpCodeResponse(BaseModel):
    """기업 고유번호 응답"""
    corp_name: str
    corp_code: Optional[str]
    found: bool


class ShareholderResponse(BaseModel):
    """주주 정보 응답"""
    name: str
    ratio_pct: float
    share_count: int = 0
    type: str
    report_date: Optional[str]
    source: str
    source_url: Optional[str]
    confidence: str


class ShareholdersListResponse(BaseModel):
    """주주 목록 응답"""
    corp_code: str
    shareholders: list[ShareholderResponse]
    count: int


class VerificationRequest(BaseModel):
    """검증 요청"""
    corp_name: str
    perplexity_shareholders: list[dict]


class VerificationResponse(BaseModel):
    """검증 응답"""
    is_verified: bool
    dart_count: int
    perplexity_count: int
    matched_count: int
    dart_only_count: int
    perplexity_only_count: int
    verified_shareholders: list[dict]
    metadata: dict


class DartStatusResponse(BaseModel):
    """DART API 상태 응답"""
    corp_codes_loaded: bool
    corp_code_count: int
    api_available: bool


# ============================================================================
# P0: Fact-Based Models
# ============================================================================

class CompanyInfoResponse(BaseModel):
    """기업개황 응답 (100% Fact)"""
    corp_code: str
    corp_name: str
    corp_name_eng: Optional[str] = None
    stock_name: Optional[str] = None
    stock_code: Optional[str] = None
    ceo_name: Optional[str] = None
    corp_cls: Optional[str] = None
    jurir_no: Optional[str] = None
    bizr_no: Optional[str] = None
    adres: Optional[str] = None
    hm_url: Optional[str] = None
    ir_url: Optional[str] = None
    phn_no: Optional[str] = None
    fax_no: Optional[str] = None
    induty_code: Optional[str] = None
    est_dt: Optional[str] = None
    acc_mt: Optional[str] = None
    source: str = "DART"
    confidence: str = "HIGH"


class LargestShareholderResponse(BaseModel):
    """최대주주 현황 응답 (100% Fact)"""
    name: str
    relate: Optional[str] = None
    stock_knd: Optional[str] = None
    bsis_posesn_stock_co: int = 0
    bsis_posesn_stock_qota_rt: float = 0.0
    trmend_posesn_stock_co: int = 0
    trmend_posesn_stock_qota_rt: float = 0.0
    ratio_pct: float = 0.0  # 호환성 (기말 지분율)
    share_count: int = 0  # 호환성 (기말 주식수)
    rm: Optional[str] = None
    report_date: Optional[str] = None
    source: str = "DART"
    confidence: str = "HIGH"


class FactBasedProfileResponse(BaseModel):
    """Fact 기반 프로필 응답"""
    corp_name: str
    corp_code: Optional[str] = None
    company_info: Optional[CompanyInfoResponse] = None
    largest_shareholders: list[LargestShareholderResponse] = []
    # 편의용 필드
    ceo_name: Optional[str] = None
    headquarters: Optional[str] = None
    founded_year: Optional[int] = None
    shareholders_count: int = 0
    fetch_timestamp: Optional[str] = None
    errors: list[str] = []
    source: str = "DART"
    confidence: str = "HIGH"


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/status", response_model=DartStatusResponse)
async def get_dart_status():
    """
    DART API 상태 확인

    Returns:
        DartStatusResponse: DART API 상태 정보
    """
    from app.services.dart_api import _corp_code_cache, _corp_code_loaded

    return DartStatusResponse(
        corp_codes_loaded=_corp_code_loaded,
        corp_code_count=len(_corp_code_cache),
        api_available=True,  # TODO: 실제 API 헬스체크
    )


@router.post("/initialize")
async def initialize_dart():
    """
    DART API 초기화 (기업 고유번호 목록 로드)

    Returns:
        dict: 초기화 결과
    """
    try:
        success = await load_corp_codes()
        if success:
            from app.services.dart_api import _corp_code_cache
            return {
                "success": True,
                "message": "DART corp codes loaded successfully",
                "count": len(_corp_code_cache),
            }
        else:
            return {
                "success": False,
                "message": "Failed to load DART corp codes",
            }
    except Exception as e:
        logger.error(f"DART initialization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/corp-code", response_model=CorpCodeResponse)
async def lookup_corp_code(
    corp_name: str = Query(..., description="기업명 (예: 삼성전자)"),
    stock_code: Optional[str] = Query(None, description="주식 종목코드 (예: 005930)"),
):
    """
    DART 기업 고유번호 조회

    Args:
        corp_name: 기업명
        stock_code: 주식 종목코드 (선택)

    Returns:
        CorpCodeResponse: 기업 고유번호 정보
    """
    corp_code = await get_corp_code(corp_name=corp_name, stock_code=stock_code)

    return CorpCodeResponse(
        corp_name=corp_name,
        corp_code=corp_code,
        found=corp_code is not None,
    )


@router.get("/shareholders/{corp_code}", response_model=ShareholdersListResponse)
async def get_shareholders(
    corp_code: str,
    limit: int = Query(10, description="최대 반환 주주 수"),
):
    """
    DART 주요주주 소유보고 조회

    Args:
        corp_code: DART 고유번호 (8자리)
        limit: 최대 반환 주주 수

    Returns:
        ShareholdersListResponse: 주주 목록
    """
    if len(corp_code) != 8:
        raise HTTPException(status_code=400, detail="corp_code must be 8 characters")

    shareholders = await get_major_shareholders(corp_code, limit=limit)

    return ShareholdersListResponse(
        corp_code=corp_code,
        shareholders=[
            ShareholderResponse(
                name=s.name,
                ratio_pct=s.ratio_pct,
                share_count=s.share_count,
                type=s.shareholder_type.value,
                report_date=s.report_date,
                source=s.source,
                source_url=s.source_url,
                confidence=s.confidence,
            )
            for s in shareholders
        ],
        count=len(shareholders),
    )


@router.get("/shareholders-by-name")
async def get_shareholders_by_name(
    corp_name: str = Query(..., description="기업명 (예: 삼성전자)"),
    limit: int = Query(10, description="최대 반환 주주 수"),
):
    """
    기업명으로 DART 주요주주 조회

    Args:
        corp_name: 기업명
        limit: 최대 반환 주주 수

    Returns:
        dict: 주주 목록 및 메타데이터
    """
    corp_code = await get_corp_code(corp_name=corp_name)

    if not corp_code:
        return {
            "corp_name": corp_name,
            "corp_code": None,
            "found": False,
            "shareholders": [],
            "message": f"DART에서 '{corp_name}'을(를) 찾을 수 없습니다.",
        }

    shareholders = await get_major_shareholders(corp_code, limit=limit)

    return {
        "corp_name": corp_name,
        "corp_code": corp_code,
        "found": True,
        "shareholders": [s.to_dict() for s in shareholders],
        "count": len(shareholders),
    }


@router.post("/verify", response_model=VerificationResponse)
async def verify_shareholders_endpoint(request: VerificationRequest):
    """
    2-Source Verification: DART + Perplexity 교차 검증

    Perplexity 검색 결과의 주주 정보를 DART 공시와 교차 검증합니다.

    Args:
        request: 검증 요청 (기업명, Perplexity 주주 목록)

    Returns:
        VerificationResponse: 검증 결과
    """
    result = await verify_shareholders(
        corp_name=request.corp_name,
        perplexity_shareholders=request.perplexity_shareholders,
    )

    # Get verified shareholders list
    verified, metadata = await get_verified_shareholders(
        corp_name=request.corp_name,
        perplexity_shareholders=request.perplexity_shareholders,
    )

    return VerificationResponse(
        is_verified=result.is_verified,
        dart_count=len(result.dart_shareholders),
        perplexity_count=len(result.perplexity_shareholders),
        matched_count=len(result.matched_shareholders),
        dart_only_count=len(result.dart_only),
        perplexity_only_count=len(result.perplexity_only),
        verified_shareholders=verified,
        metadata=metadata,
    )


@router.get("/verified-shareholders")
async def get_verified_shareholders_endpoint(
    corp_name: str = Query(..., description="기업명 (예: 삼성전자)"),
    use_dart_only: bool = Query(False, description="DART 데이터만 사용 (검증 없이)"),
):
    """
    검증된 주주 정보 조회 (Corp Profiling 통합용)

    DART 공시로 검증된 주주 정보를 반환합니다.
    검증 실패 시 Perplexity 데이터를 낮은 신뢰도로 반환합니다.

    Args:
        corp_name: 기업명
        use_dart_only: True면 DART 데이터만 사용

    Returns:
        dict: 검증된 주주 목록 및 메타데이터
    """
    verified, metadata = await get_verified_shareholders(
        corp_name=corp_name,
        perplexity_shareholders=None,  # DART only
        use_dart_only=use_dart_only,
    )

    return {
        "corp_name": corp_name,
        "shareholders": verified,
        "count": len(verified),
        "metadata": metadata,
    }


# ============================================================================
# P0: Fact-Based Endpoints (100% Hallucination 제거)
# ============================================================================

@router.get("/company/{corp_code}", response_model=CompanyInfoResponse)
async def get_company_info_endpoint(corp_code: str):
    """
    P0: DART 기업개황 조회 (100% Fact)

    공시대상 기업의 기본 정보를 DART에서 직접 조회합니다.
    CEO 이름, 설립일, 주소, 업종코드 등 100% Fact 기반 데이터를 제공합니다.

    Args:
        corp_code: DART 고유번호 (8자리)

    Returns:
        CompanyInfoResponse: 기업개황 정보
    """
    if len(corp_code) != 8:
        raise HTTPException(status_code=400, detail="corp_code must be 8 characters")

    company_info = await get_company_info(corp_code)

    if not company_info:
        raise HTTPException(status_code=404, detail=f"Company info not found for corp_code={corp_code}")

    return CompanyInfoResponse(
        corp_code=company_info.corp_code,
        corp_name=company_info.corp_name,
        corp_name_eng=company_info.corp_name_eng,
        stock_name=company_info.stock_name,
        stock_code=company_info.stock_code,
        ceo_name=company_info.ceo_name,
        corp_cls=company_info.corp_cls,
        jurir_no=company_info.jurir_no,
        bizr_no=company_info.bizr_no,
        adres=company_info.adres,
        hm_url=company_info.hm_url,
        ir_url=company_info.ir_url,
        phn_no=company_info.phn_no,
        fax_no=company_info.fax_no,
        induty_code=company_info.induty_code,
        est_dt=company_info.est_dt,
        acc_mt=company_info.acc_mt,
        source=company_info.source,
        confidence=company_info.confidence,
    )


@router.get("/company-by-name")
async def get_company_info_by_name_endpoint(
    corp_name: str = Query(..., description="기업명 (예: 삼성전자, 엠케이전자)"),
):
    """
    P0: 기업명으로 DART 기업개황 조회 (100% Fact)

    기업명으로 DART 고유번호를 찾은 후 기업개황을 조회합니다.

    Args:
        corp_name: 기업명

    Returns:
        dict: 기업개황 정보 및 메타데이터
    """
    company_info = await get_company_info_by_name(corp_name)

    if not company_info:
        return {
            "corp_name": corp_name,
            "found": False,
            "company_info": None,
            "message": f"DART에서 '{corp_name}'을(를) 찾을 수 없습니다.",
        }

    return {
        "corp_name": corp_name,
        "found": True,
        "company_info": company_info.to_dict(),
    }


@router.get("/largest-shareholders/{corp_code}")
async def get_largest_shareholders_endpoint(
    corp_code: str,
    bsns_year: Optional[str] = Query(None, description="사업연도 (예: 2024)"),
):
    """
    P0: DART 최대주주 현황 조회 (100% Fact)

    사업보고서에 기재된 최대주주 현황을 조회합니다.
    주요주주 소유보고(elestock.json)보다 더 정확한 최대주주 정보를 제공합니다.

    Args:
        corp_code: DART 고유번호 (8자리)
        bsns_year: 사업연도 (미지정 시 최근 연도)

    Returns:
        dict: 최대주주 현황 목록
    """
    if len(corp_code) != 8:
        raise HTTPException(status_code=400, detail="corp_code must be 8 characters")

    shareholders = await get_largest_shareholders(corp_code, bsns_year=bsns_year)

    return {
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "shareholders": [s.to_dict() for s in shareholders],
        "count": len(shareholders),
        "source": "DART",
        "confidence": "HIGH",
    }


@router.get("/largest-shareholders-by-name")
async def get_largest_shareholders_by_name_endpoint(
    corp_name: str = Query(..., description="기업명 (예: 삼성전자, 엠케이전자)"),
):
    """
    P0: 기업명으로 DART 최대주주 현황 조회 (100% Fact)

    기업명으로 DART 고유번호를 찾은 후 최대주주 현황을 조회합니다.

    Args:
        corp_name: 기업명

    Returns:
        dict: 최대주주 현황 목록 및 메타데이터
    """
    shareholders = await get_largest_shareholders_by_name(corp_name)

    if not shareholders:
        # Corp code 찾기
        corp_code = await get_corp_code(corp_name=corp_name)
        if not corp_code:
            return {
                "corp_name": corp_name,
                "found": False,
                "shareholders": [],
                "message": f"DART에서 '{corp_name}'을(를) 찾을 수 없습니다.",
            }
        else:
            return {
                "corp_name": corp_name,
                "corp_code": corp_code,
                "found": True,
                "shareholders": [],
                "message": f"'{corp_name}'의 최대주주 현황이 없습니다.",
            }

    return {
        "corp_name": corp_name,
        "found": True,
        "shareholders": [s.to_dict() for s in shareholders],
        "count": len(shareholders),
        "source": "DART",
        "confidence": "HIGH",
    }


@router.get("/fact-profile")
async def get_fact_based_profile_endpoint(
    corp_name: str = Query(..., description="기업명 (예: 삼성전자, 엠케이전자)"),
):
    """
    P0: DART Fact 기반 프로필 통합 조회 (100% Hallucination 제거)

    기업개황 + 최대주주 현황을 한 번에 조회하여
    LLM 추출 없이 100% Fact 기반 데이터를 제공합니다.

    이 API를 사용하면 주주 정보, CEO 이름, 설립일 등의
    Hallucination을 100% 제거할 수 있습니다.

    Args:
        corp_name: 기업명

    Returns:
        FactBasedProfileResponse: Fact 기반 프로필 데이터
    """
    profile = await get_fact_based_profile(corp_name)

    # 회사 정보 변환
    company_info_response = None
    if profile.company_info:
        company_info_response = CompanyInfoResponse(
            corp_code=profile.company_info.corp_code,
            corp_name=profile.company_info.corp_name,
            corp_name_eng=profile.company_info.corp_name_eng,
            stock_name=profile.company_info.stock_name,
            stock_code=profile.company_info.stock_code,
            ceo_name=profile.company_info.ceo_name,
            corp_cls=profile.company_info.corp_cls,
            jurir_no=profile.company_info.jurir_no,
            bizr_no=profile.company_info.bizr_no,
            adres=profile.company_info.adres,
            hm_url=profile.company_info.hm_url,
            ir_url=profile.company_info.ir_url,
            phn_no=profile.company_info.phn_no,
            fax_no=profile.company_info.fax_no,
            induty_code=profile.company_info.induty_code,
            est_dt=profile.company_info.est_dt,
            acc_mt=profile.company_info.acc_mt,
        )

    # 주주 정보 변환
    shareholders_response = [
        LargestShareholderResponse(
            name=s.nm,
            relate=s.relate,
            stock_knd=s.stock_knd,
            bsis_posesn_stock_co=s.bsis_posesn_stock_co,
            bsis_posesn_stock_qota_rt=s.bsis_posesn_stock_qota_rt,
            trmend_posesn_stock_co=s.trmend_posesn_stock_co,
            trmend_posesn_stock_qota_rt=s.trmend_posesn_stock_qota_rt,
            ratio_pct=s.trmend_posesn_stock_qota_rt,
            share_count=s.trmend_posesn_stock_co,
            rm=s.rm,
            report_date=s.report_date,
        )
        for s in profile.largest_shareholders
    ]

    return FactBasedProfileResponse(
        corp_name=corp_name,
        corp_code=profile.corp_code,
        company_info=company_info_response,
        largest_shareholders=shareholders_response,
        ceo_name=profile.ceo_name,
        headquarters=profile.headquarters,
        founded_year=profile.founded_year,
        shareholders_count=len(profile.largest_shareholders),
        fetch_timestamp=profile.fetch_timestamp,
        errors=profile.errors,
    )


# ============================================================================
# P2: Financial Statement Endpoints (재무제표 - 100% Fact)
# ============================================================================

class FinancialStatementResponse(BaseModel):
    """재무제표 응답"""
    bsns_year: str
    revenue: Optional[int] = None
    operating_profit: Optional[int] = None
    net_income: Optional[int] = None
    total_assets: Optional[int] = None
    total_liabilities: Optional[int] = None
    total_equity: Optional[int] = None
    debt_ratio: Optional[float] = None
    report_code: Optional[str] = None
    source: str = "DART"
    confidence: str = "HIGH"


@router.get("/financials/{corp_code}")
async def get_financial_statements_endpoint(
    corp_code: str,
    bsns_year: Optional[str] = Query(None, description="사업연도 (예: 2024)"),
    fs_div: str = Query("OFS", description="재무제표 구분 (OFS=개별, CFS=연결)"),
):
    """
    P2: DART 재무제표 주요계정 조회 (100% Fact)

    매출액, 영업이익, 당기순이익, 총자산, 부채비율 등을 조회합니다.

    Args:
        corp_code: DART 고유번호 (8자리)
        bsns_year: 사업연도 (미지정 시 최근 3년)
        fs_div: 재무제표 구분

    Returns:
        dict: 재무제표 목록
    """
    if len(corp_code) != 8:
        raise HTTPException(status_code=400, detail="corp_code must be 8 characters")

    statements = await get_financial_statements(
        corp_code,
        bsns_year=bsns_year,
        fs_div=fs_div,
    )

    return {
        "corp_code": corp_code,
        "financial_statements": [s.to_dict() for s in statements],
        "count": len(statements),
        "source": "DART",
        "confidence": "HIGH",
    }


@router.get("/financials-by-name")
async def get_financial_statements_by_name_endpoint(
    corp_name: str = Query(..., description="기업명 (예: 삼성전자, 엠케이전자)"),
):
    """
    P2: 기업명으로 DART 재무제표 조회 (100% Fact)

    Args:
        corp_name: 기업명

    Returns:
        dict: 재무제표 목록 (최근 3년)
    """
    statements = await get_financial_statements_by_name(corp_name)

    if not statements:
        corp_code = await get_corp_code(corp_name=corp_name)
        if not corp_code:
            return {
                "corp_name": corp_name,
                "found": False,
                "financial_statements": [],
                "message": f"DART에서 '{corp_name}'을(를) 찾을 수 없습니다.",
            }
        else:
            return {
                "corp_name": corp_name,
                "corp_code": corp_code,
                "found": True,
                "financial_statements": [],
                "message": f"'{corp_name}'의 재무제표 정보가 없습니다.",
            }

    return {
        "corp_name": corp_name,
        "found": True,
        "financial_statements": [s.to_dict() for s in statements],
        "count": len(statements),
        "source": "DART",
        "confidence": "HIGH",
    }


# ============================================================================
# P3: Major Event Endpoints (주요사항보고서 - 100% Fact)
# ============================================================================

class MajorEventResponse(BaseModel):
    """주요사항보고서 응답"""
    rcept_no: str
    rcept_dt: str
    report_nm: str
    event_type: str
    corp_name: str
    flr_nm: Optional[str] = None
    rm: Optional[str] = None
    source_url: Optional[str] = None
    source: str = "DART"
    confidence: str = "HIGH"


@router.get("/events/{corp_code}")
async def get_major_events_endpoint(
    corp_code: str,
    bgn_de: Optional[str] = Query(None, description="시작일 (YYYYMMDD)"),
    end_de: Optional[str] = Query(None, description="종료일 (YYYYMMDD)"),
):
    """
    P3: DART 주요사항보고서 조회 (100% Fact)

    인수/합병, 유상증자, 소송, 감사의견 등 중요 이벤트를 조회합니다.

    Args:
        corp_code: DART 고유번호 (8자리)
        bgn_de: 시작일 (미지정 시 1년 전)
        end_de: 종료일 (미지정 시 오늘)

    Returns:
        dict: 주요사항보고서 목록
    """
    if len(corp_code) != 8:
        raise HTTPException(status_code=400, detail="corp_code must be 8 characters")

    events = await get_major_events(corp_code, bgn_de=bgn_de, end_de=end_de)

    return {
        "corp_code": corp_code,
        "major_events": [e.to_dict() for e in events],
        "count": len(events),
        "has_risk_events": any(
            e.event_type in {MajorEventType.LITIGATION, MajorEventType.SANCTION, MajorEventType.DEFAULT, MajorEventType.AUDIT_OPINION}
            for e in events
        ),
        "source": "DART",
        "confidence": "HIGH",
    }


@router.get("/events-by-name")
async def get_major_events_by_name_endpoint(
    corp_name: str = Query(..., description="기업명 (예: 삼성전자, 엠케이전자)"),
):
    """
    P3: 기업명으로 DART 주요사항보고서 조회 (100% Fact)

    Args:
        corp_name: 기업명

    Returns:
        dict: 주요사항보고서 목록 (최근 1년)
    """
    events = await get_major_events_by_name(corp_name)

    if not events:
        corp_code = await get_corp_code(corp_name=corp_name)
        if not corp_code:
            return {
                "corp_name": corp_name,
                "found": False,
                "major_events": [],
                "message": f"DART에서 '{corp_name}'을(를) 찾을 수 없습니다.",
            }
        else:
            return {
                "corp_name": corp_name,
                "corp_code": corp_code,
                "found": True,
                "major_events": [],
                "message": f"'{corp_name}'의 최근 1년 내 주요사항보고서가 없습니다.",
            }

    return {
        "corp_name": corp_name,
        "found": True,
        "major_events": [e.to_dict() for e in events],
        "count": len(events),
        "has_risk_events": any(
            e.event_type in {MajorEventType.LITIGATION, MajorEventType.SANCTION, MajorEventType.DEFAULT, MajorEventType.AUDIT_OPINION}
            for e in events
        ),
        "source": "DART",
        "confidence": "HIGH",
    }


# ============================================================================
# P2/P3: Extended Fact Profile (통합 조회)
# ============================================================================

@router.get("/extended-profile")
async def get_extended_fact_profile_endpoint(
    corp_name: str = Query(..., description="기업명 (예: 삼성전자, 엠케이전자)"),
):
    """
    P2/P3: 확장된 DART Fact 프로필 통합 조회

    기업개황 + 최대주주 + 재무제표(3년) + 주요사항보고서(1년)을
    한 번에 조회하여 100% Fact 기반 데이터를 제공합니다.

    Args:
        corp_name: 기업명

    Returns:
        dict: 확장된 Fact 프로필
    """
    profile = await get_extended_fact_profile(corp_name)

    # 회사 정보 변환
    company_info = None
    if profile.company_info:
        company_info = profile.company_info.to_dict()

    return {
        "corp_name": corp_name,
        "corp_code": profile.corp_code,
        "company_info": company_info,
        "largest_shareholders": [s.to_dict() for s in profile.largest_shareholders],
        "financial_statements": [f.to_dict() for f in profile.financial_statements],
        "major_events": [e.to_dict() for e in profile.major_events],
        # 편의용 필드
        "latest_revenue": profile.latest_revenue,
        "latest_net_income": profile.latest_net_income,
        "has_risk_events": profile.has_risk_events,
        "shareholders_count": len(profile.largest_shareholders),
        "financials_count": len(profile.financial_statements),
        "events_count": len(profile.major_events),
        "fetch_timestamp": profile.fetch_timestamp,
        "errors": profile.errors,
        "source": "DART",
        "confidence": "HIGH",
    }
