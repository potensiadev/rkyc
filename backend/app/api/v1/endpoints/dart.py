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
