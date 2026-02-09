"""
DART OpenAPI Client for Fact-Based Corp Profiling

DART (Data Analysis, Retrieval and Transfer System) is the official
electronic disclosure system of South Korea's Financial Supervisory Service (FSS).

This module provides:
1. Corp Code lookup (DART 고유번호 조회)
2. Company Info query (기업개황 조회) - CEO, 설립일, 업종 등 100% Fact
3. Largest Shareholder query (최대주주 현황) - 100% Fact
4. Major shareholder ownership query (주요주주 소유보고)
5. 2-Source Verification with Perplexity (교차 검증)

API Endpoints:
- Corp Code List: https://opendart.fss.or.kr/api/corpCode.xml (ZIP)
- Company Info: https://opendart.fss.or.kr/api/company.json (P0)
- Largest Shareholder: https://opendart.fss.or.kr/api/hyslrSttus.json (P0)
- Major Shareholder: https://opendart.fss.or.kr/api/elestock.json

References:
- https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019002 (기업개황)
- https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS002&apiId=2019005 (최대주주)
- https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS004&apiId=2019022 (주요주주)
"""

import asyncio
import logging
import re
import io
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Any, Optional
from functools import lru_cache

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

# DART API Key는 settings에서 가져오거나 기본값 사용
DART_API_KEY = getattr(settings, 'DART_API_KEY', "a5cf6e4eedca9a82191e4ab1bcdeda7f6d6e4861")
DART_BASE_URL = "https://opendart.fss.or.kr/api"
DART_TIMEOUT = 30  # seconds

# Response status codes
DART_STATUS_SUCCESS = "000"
DART_STATUS_NO_DATA = "013"  # 조회된 데이터가 없습니다


class DartError(Exception):
    """DART API Error"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"DART API Error [{code}]: {message}")


class ShareholderType(str, Enum):
    """주주 유형"""
    MAJOR_SHAREHOLDER = "10%이상주주"
    LARGEST_SHAREHOLDER = "최대주주"
    EXECUTIVE = "임원"
    RELATED_PARTY = "특수관계인"
    INSTITUTION = "기관"
    FOREIGN = "외국인"
    UNKNOWN = "기타"


@dataclass
class CompanyInfo:
    """기업개황 정보 (100% Fact - DART 공시)"""
    corp_code: str  # DART 고유번호
    corp_name: str  # 정식 회사명
    corp_name_eng: Optional[str] = None  # 영문명
    stock_name: Optional[str] = None  # 종목명 (상장사)
    stock_code: Optional[str] = None  # 종목코드 (상장사)
    ceo_name: Optional[str] = None  # 대표이사
    corp_cls: Optional[str] = None  # 법인구분 (Y:유가, K:코스닥, N:코넥스, E:기타)
    jurir_no: Optional[str] = None  # 법인등록번호
    bizr_no: Optional[str] = None  # 사업자등록번호
    adres: Optional[str] = None  # 주소
    hm_url: Optional[str] = None  # 홈페이지 URL
    ir_url: Optional[str] = None  # IR 홈페이지 URL
    phn_no: Optional[str] = None  # 전화번호
    fax_no: Optional[str] = None  # 팩스번호
    induty_code: Optional[str] = None  # 업종코드
    est_dt: Optional[str] = None  # 설립일 (YYYYMMDD)
    acc_mt: Optional[str] = None  # 결산월 (MM)
    source: str = "DART"
    confidence: str = "HIGH"  # DART 공시는 100% Fact

    def to_dict(self) -> dict:
        return {
            "corp_code": self.corp_code,
            "corp_name": self.corp_name,
            "corp_name_eng": self.corp_name_eng,
            "stock_name": self.stock_name,
            "stock_code": self.stock_code,
            "ceo_name": self.ceo_name,
            "corp_cls": self.corp_cls,
            "jurir_no": self.jurir_no,
            "bizr_no": self.bizr_no,
            "adres": self.adres,
            "hm_url": self.hm_url,
            "ir_url": self.ir_url,
            "phn_no": self.phn_no,
            "fax_no": self.fax_no,
            "induty_code": self.induty_code,
            "est_dt": self.est_dt,
            "acc_mt": self.acc_mt,
            "source": self.source,
            "confidence": self.confidence,
        }


@dataclass
class LargestShareholder:
    """최대주주 현황 정보 (100% Fact - DART 공시)"""
    nm: str  # 성명
    relate: Optional[str] = None  # 관계 (본인, 친인척 등)
    stock_knd: Optional[str] = None  # 주식 종류 (보통주, 우선주 등)
    bsis_posesn_stock_co: int = 0  # 기초 소유 주식수
    bsis_posesn_stock_qota_rt: float = 0.0  # 기초 소유 지분율
    trmend_posesn_stock_co: int = 0  # 기말 소유 주식수
    trmend_posesn_stock_qota_rt: float = 0.0  # 기말 소유 지분율
    rm: Optional[str] = None  # 비고
    report_date: Optional[str] = None  # 보고서 기준일
    source: str = "DART"
    source_url: Optional[str] = None
    confidence: str = "HIGH"  # DART 공시는 100% Fact

    def to_dict(self) -> dict:
        return {
            "name": self.nm,
            "relate": self.relate,
            "stock_knd": self.stock_knd,
            "bsis_posesn_stock_co": self.bsis_posesn_stock_co,
            "bsis_posesn_stock_qota_rt": self.bsis_posesn_stock_qota_rt,
            "trmend_posesn_stock_co": self.trmend_posesn_stock_co,
            "trmend_posesn_stock_qota_rt": self.trmend_posesn_stock_qota_rt,
            "ratio_pct": self.trmend_posesn_stock_qota_rt,  # 호환성
            "share_count": self.trmend_posesn_stock_co,  # 호환성
            "rm": self.rm,
            "report_date": self.report_date,
            "source": self.source,
            "source_url": self.source_url,
            "confidence": self.confidence,
        }


@dataclass
class Shareholder:
    """주주 정보"""
    name: str
    ratio_pct: float
    share_count: int = 0
    shareholder_type: ShareholderType = ShareholderType.UNKNOWN
    report_date: Optional[str] = None
    source: str = "DART"
    source_url: Optional[str] = None
    confidence: str = "HIGH"  # DART 공시는 HIGH 신뢰도

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "ratio_pct": self.ratio_pct,
            "share_count": self.share_count,
            "type": self.shareholder_type.value,
            "report_date": self.report_date,
            "source": self.source,
            "source_url": self.source_url,
            "confidence": self.confidence,
        }


@dataclass
class VerificationResult:
    """2-Source Verification 결과"""
    is_verified: bool
    dart_shareholders: list[Shareholder]
    perplexity_shareholders: list[dict]
    matched_shareholders: list[Shareholder]
    dart_only: list[Shareholder]
    perplexity_only: list[dict]
    verification_details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "is_verified": self.is_verified,
            "dart_shareholders": [s.to_dict() for s in self.dart_shareholders],
            "perplexity_shareholders": self.perplexity_shareholders,
            "matched_shareholders": [s.to_dict() for s in self.matched_shareholders],
            "dart_only": [s.to_dict() for s in self.dart_only],
            "perplexity_only": self.perplexity_only,
            "verification_details": self.verification_details,
        }


# ============================================================================
# Corp Code Lookup
# ============================================================================

# In-memory cache for corp codes (loaded from DART ZIP file)
_corp_code_cache: dict[str, str] = {}
_corp_code_by_name: dict[str, str] = {}
_corp_code_loaded: bool = False


async def load_corp_codes() -> bool:
    """
    DART 기업 고유번호 목록 다운로드 및 캐시

    DART는 기업별 고유번호(corp_code)를 ZIP 파일로 제공합니다.
    이 함수는 ZIP 파일을 다운로드하고 파싱하여 메모리에 캐시합니다.

    Returns:
        True if successful, False otherwise
    """
    global _corp_code_cache, _corp_code_by_name, _corp_code_loaded

    if _corp_code_loaded and _corp_code_cache:
        logger.debug("[DartAPI] Corp codes already loaded")
        return True

    url = f"{DART_BASE_URL}/corpCode.xml?crtfc_key={DART_API_KEY}"

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            logger.info("[DartAPI] Downloading corp code list from DART...")
            response = await client.get(url)
            response.raise_for_status()

            # Response is a ZIP file containing XML
            zip_buffer = io.BytesIO(response.content)
            with zipfile.ZipFile(zip_buffer, 'r') as zf:
                # The ZIP contains a single XML file
                xml_filename = zf.namelist()[0]
                with zf.open(xml_filename) as xml_file:
                    tree = ET.parse(xml_file)
                    root = tree.getroot()

                    for corp in root.findall('.//list'):
                        corp_code = corp.findtext('corp_code', '')
                        corp_name = corp.findtext('corp_name', '')
                        stock_code = corp.findtext('stock_code', '')  # 상장사만 있음

                        if corp_code and corp_name:
                            _corp_code_cache[corp_code] = corp_name

                            # 이름으로도 검색 가능하게 (정규화된 이름)
                            normalized_name = _normalize_corp_name(corp_name)
                            _corp_code_by_name[normalized_name] = corp_code

                            # 주식코드도 매핑 (상장사)
                            if stock_code and stock_code.strip():
                                _corp_code_cache[f"stock:{stock_code.strip()}"] = corp_code

            _corp_code_loaded = True
            logger.info(f"[DartAPI] Loaded {len(_corp_code_cache)} corp codes")
            return True

    except httpx.HTTPError as e:
        logger.error(f"[DartAPI] Failed to download corp codes: {e}")
        return False
    except Exception as e:
        logger.error(f"[DartAPI] Failed to parse corp codes: {e}")
        return False


def _normalize_corp_name(name: str) -> str:
    """기업명 정규화 (검색용)"""
    # 공백 제거, 소문자 변환, 특수문자 제거
    normalized = re.sub(r'[^\w가-힣]', '', name.lower())
    return normalized


async def get_corp_code(
    corp_name: Optional[str] = None,
    stock_code: Optional[str] = None,
    biz_no: Optional[str] = None,
) -> Optional[str]:
    """
    기업 고유번호(corp_code) 조회

    Args:
        corp_name: 기업명 (예: "삼성전자")
        stock_code: 주식 종목코드 (예: "005930")
        biz_no: 사업자등록번호 (현재 미지원)

    Returns:
        8자리 DART 고유번호 또는 None
    """
    # 캐시 로드 확인
    if not _corp_code_loaded:
        await load_corp_codes()

    # 주식코드로 검색
    if stock_code:
        stock_key = f"stock:{stock_code.strip()}"
        if stock_key in _corp_code_cache:
            return _corp_code_cache[stock_key]

    # 기업명으로 검색
    if corp_name:
        normalized = _normalize_corp_name(corp_name)

        # 정확 매칭
        if normalized in _corp_code_by_name:
            return _corp_code_by_name[normalized]

        # 부분 매칭 (첫 번째 매칭 반환)
        for cached_name, code in _corp_code_by_name.items():
            if normalized in cached_name or cached_name in normalized:
                return code

    return None


# ============================================================================
# P0: Company Info API (기업개황)
# ============================================================================

async def get_company_info(corp_code: str) -> Optional[CompanyInfo]:
    """
    DART 기업개황 조회 (100% Fact)

    공시대상 기업의 기본 정보를 조회합니다.
    CEO 이름, 설립일, 주소, 업종코드 등 기본 정보를 DART에서 직접 가져옵니다.

    API: https://opendart.fss.or.kr/api/company.json

    Args:
        corp_code: DART 고유번호 (8자리)

    Returns:
        CompanyInfo 객체 또는 None
    """
    url = f"{DART_BASE_URL}/company.json"
    params = {
        "crtfc_key": DART_API_KEY,
        "corp_code": corp_code,
    }

    try:
        async with httpx.AsyncClient(timeout=DART_TIMEOUT) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            status = data.get("status", "")
            message = data.get("message", "")

            if status == DART_STATUS_NO_DATA:
                logger.info(f"[DartAPI] No company info for corp_code={corp_code}")
                return None

            if status != DART_STATUS_SUCCESS:
                raise DartError(status, message)

            return CompanyInfo(
                corp_code=data.get("corp_code", corp_code),
                corp_name=data.get("corp_name", ""),
                corp_name_eng=data.get("corp_name_eng"),
                stock_name=data.get("stock_name"),
                stock_code=data.get("stock_code"),
                ceo_name=data.get("ceo_nm"),
                corp_cls=data.get("corp_cls"),
                jurir_no=data.get("jurir_no"),
                bizr_no=data.get("bizr_no"),
                adres=data.get("adres"),
                hm_url=data.get("hm_url"),
                ir_url=data.get("ir_url"),
                phn_no=data.get("phn_no"),
                fax_no=data.get("fax_no"),
                induty_code=data.get("induty_code"),
                est_dt=data.get("est_dt"),
                acc_mt=data.get("acc_mt"),
                source="DART",
                confidence="HIGH",
            )

    except httpx.HTTPError as e:
        logger.error(f"[DartAPI] HTTP error getting company info: {e}")
        return None
    except DartError as e:
        logger.error(f"[DartAPI] {e}")
        return None
    except Exception as e:
        logger.error(f"[DartAPI] Unexpected error getting company info: {e}")
        return None


async def get_company_info_by_name(corp_name: str) -> Optional[CompanyInfo]:
    """
    기업명으로 기업개황 조회

    Args:
        corp_name: 기업명 (예: "삼성전자", "엠케이전자")

    Returns:
        CompanyInfo 객체 또는 None
    """
    corp_code = await get_corp_code(corp_name=corp_name)
    if not corp_code:
        logger.warning(f"[DartAPI] Could not find corp_code for '{corp_name}'")
        return None
    return await get_company_info(corp_code)


# ============================================================================
# P0: Largest Shareholder API (최대주주 현황)
# ============================================================================

async def get_largest_shareholders(
    corp_code: str,
    bsns_year: Optional[str] = None,
    reprt_code: str = "11011",  # 11011: 사업보고서
) -> list[LargestShareholder]:
    """
    DART 최대주주 현황 조회 (100% Fact)

    사업보고서에 기재된 최대주주 현황을 조회합니다.
    elestock.json(주요주주 소유보고)보다 더 정확한 최대주주 정보를 제공합니다.

    API: https://opendart.fss.or.kr/api/hyslrSttus.json

    Args:
        corp_code: DART 고유번호 (8자리)
        bsns_year: 사업연도 (미지정 시 최근 연도)
        reprt_code: 보고서 코드
            - 11011: 사업보고서 (1년 전체)
            - 11012: 반기보고서
            - 11013: 1분기보고서
            - 11014: 3분기보고서

    Returns:
        LargestShareholder 객체 리스트
    """
    url = f"{DART_BASE_URL}/hyslrSttus.json"

    # 사업연도 미지정 시 전년도 사용 (사업보고서는 전년도 기준)
    if not bsns_year:
        bsns_year = str(datetime.now().year - 1)

    params = {
        "crtfc_key": DART_API_KEY,
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
    }

    try:
        async with httpx.AsyncClient(timeout=DART_TIMEOUT) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            status = data.get("status", "")
            message = data.get("message", "")

            if status == DART_STATUS_NO_DATA:
                logger.info(f"[DartAPI] No largest shareholder data for corp_code={corp_code}, year={bsns_year}")
                # 전년도 데이터가 없으면 2년 전 시도
                if bsns_year == str(datetime.now().year - 1):
                    logger.info(f"[DartAPI] Trying previous year...")
                    return await get_largest_shareholders(
                        corp_code,
                        bsns_year=str(datetime.now().year - 2),
                        reprt_code=reprt_code,
                    )
                return []

            if status != DART_STATUS_SUCCESS:
                raise DartError(status, message)

            shareholders = []
            items = data.get("list", [])

            for item in items:
                shareholder = _parse_largest_shareholder_item(item, bsns_year)
                if shareholder:
                    shareholders.append(shareholder)

            # 기말 지분율 기준 정렬
            shareholders.sort(key=lambda s: s.trmend_posesn_stock_qota_rt, reverse=True)

            logger.info(f"[DartAPI] Found {len(shareholders)} largest shareholders for corp_code={corp_code}")
            return shareholders

    except httpx.HTTPError as e:
        logger.error(f"[DartAPI] HTTP error getting largest shareholders: {e}")
        return []
    except DartError as e:
        logger.error(f"[DartAPI] {e}")
        return []
    except Exception as e:
        logger.error(f"[DartAPI] Unexpected error getting largest shareholders: {e}")
        return []


def _parse_largest_shareholder_item(item: dict, bsns_year: str) -> Optional[LargestShareholder]:
    """DART 최대주주 현황 응답 항목을 LargestShareholder 객체로 변환"""
    try:
        nm = item.get("nm", "").strip()
        if not nm or nm == "-":
            return None

        # 지분율 파싱
        def parse_float(val: str) -> float:
            if not val or val == "-":
                return 0.0
            try:
                return float(val.replace(",", ""))
            except ValueError:
                return 0.0

        def parse_int(val: str) -> int:
            if not val or val == "-":
                return 0
            try:
                return int(val.replace(",", ""))
            except ValueError:
                return 0

        return LargestShareholder(
            nm=nm,
            relate=item.get("relate"),
            stock_knd=item.get("stock_knd"),
            bsis_posesn_stock_co=parse_int(item.get("bsis_posesn_stock_co", "0")),
            bsis_posesn_stock_qota_rt=parse_float(item.get("bsis_posesn_stock_qota_rt", "0")),
            trmend_posesn_stock_co=parse_int(item.get("trmend_posesn_stock_co", "0")),
            trmend_posesn_stock_qota_rt=parse_float(item.get("trmend_posesn_stock_qota_rt", "0")),
            rm=item.get("rm"),
            report_date=f"{bsns_year}1231",  # 사업보고서 기준일
            source="DART",
            source_url=None,
            confidence="HIGH",
        )

    except Exception as e:
        logger.warning(f"[DartAPI] Failed to parse largest shareholder item: {e}")
        return None


async def get_largest_shareholders_by_name(corp_name: str) -> list[LargestShareholder]:
    """
    기업명으로 최대주주 현황 조회

    Args:
        corp_name: 기업명 (예: "삼성전자", "엠케이전자")

    Returns:
        LargestShareholder 객체 리스트
    """
    corp_code = await get_corp_code(corp_name=corp_name)
    if not corp_code:
        logger.warning(f"[DartAPI] Could not find corp_code for '{corp_name}'")
        return []
    return await get_largest_shareholders(corp_code)


# ============================================================================
# P0: Fact-Based Profile Data (통합 조회)
# ============================================================================

@dataclass
class FactBasedProfileData:
    """
    DART에서 가져온 Fact 기반 프로필 데이터

    LLM 추출 대신 DART 공시를 사용하여 100% Hallucination 제거
    """
    company_info: Optional[CompanyInfo] = None
    largest_shareholders: list[LargestShareholder] = field(default_factory=list)
    corp_code: Optional[str] = None
    fetch_timestamp: Optional[str] = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "company_info": self.company_info.to_dict() if self.company_info else None,
            "largest_shareholders": [s.to_dict() for s in self.largest_shareholders],
            "corp_code": self.corp_code,
            "fetch_timestamp": self.fetch_timestamp,
            "errors": self.errors,
            "source": "DART",
            "confidence": "HIGH",
        }

    @property
    def ceo_name(self) -> Optional[str]:
        """CEO 이름 (100% Fact)"""
        return self.company_info.ceo_name if self.company_info else None

    @property
    def headquarters(self) -> Optional[str]:
        """본사 주소 (100% Fact)"""
        return self.company_info.adres if self.company_info else None

    @property
    def founded_year(self) -> Optional[int]:
        """설립연도 (100% Fact)"""
        if self.company_info and self.company_info.est_dt:
            try:
                return int(self.company_info.est_dt[:4])
            except (ValueError, IndexError):
                return None
        return None

    @property
    def shareholders(self) -> list[dict]:
        """주주 정보 (100% Fact)"""
        return [s.to_dict() for s in self.largest_shareholders]


async def get_fact_based_profile(corp_name: str) -> FactBasedProfileData:
    """
    DART에서 Fact 기반 프로필 데이터 조회 (통합)

    기업개황 + 최대주주 현황을 한 번에 조회하여
    LLM 추출 없이 100% Fact 기반 데이터를 제공합니다.

    Args:
        corp_name: 기업명

    Returns:
        FactBasedProfileData 객체
    """
    result = FactBasedProfileData(
        fetch_timestamp=datetime.now(UTC).isoformat(),
        errors=[],
    )

    # 1. Corp Code 조회
    corp_code = await get_corp_code(corp_name=corp_name)
    if not corp_code:
        result.errors.append(f"DART 고유번호를 찾을 수 없습니다: {corp_name}")
        logger.warning(f"[DartAPI] Could not find corp_code for '{corp_name}'")
        return result

    result.corp_code = corp_code

    # 2. 기업개황 조회 (비동기)
    try:
        company_info = await get_company_info(corp_code)
        result.company_info = company_info
        if not company_info:
            result.errors.append("기업개황 정보를 찾을 수 없습니다")
    except Exception as e:
        result.errors.append(f"기업개황 조회 실패: {str(e)}")
        logger.error(f"[DartAPI] Failed to get company info: {e}")

    # 3. 최대주주 현황 조회 (비동기)
    try:
        shareholders = await get_largest_shareholders(corp_code)
        result.largest_shareholders = shareholders
        if not shareholders:
            result.errors.append("최대주주 현황 정보를 찾을 수 없습니다")
    except Exception as e:
        result.errors.append(f"최대주주 현황 조회 실패: {str(e)}")
        logger.error(f"[DartAPI] Failed to get largest shareholders: {e}")

    logger.info(
        f"[DartAPI] Fact-based profile for '{corp_name}': "
        f"company_info={'있음' if result.company_info else '없음'}, "
        f"shareholders={len(result.largest_shareholders)}명"
    )

    return result


# ============================================================================
# P2: Financial Statement API (재무제표)
# ============================================================================

@dataclass
class FinancialStatement:
    """재무제표 정보 (100% Fact - DART 공시)"""
    bsns_year: str  # 사업연도
    revenue: Optional[int] = None  # 매출액
    operating_profit: Optional[int] = None  # 영업이익
    net_income: Optional[int] = None  # 당기순이익
    total_assets: Optional[int] = None  # 총자산
    total_liabilities: Optional[int] = None  # 총부채
    total_equity: Optional[int] = None  # 총자본
    retained_earnings: Optional[int] = None  # 이익잉여금 (차익금)
    debt_ratio: Optional[float] = None  # 부채비율
    report_code: Optional[str] = None  # 보고서 코드 (11011=사업보고서)
    source: str = "DART"
    confidence: str = "HIGH"

    def to_dict(self) -> dict:
        return {
            "bsns_year": self.bsns_year,
            "revenue": self.revenue,
            "operating_profit": self.operating_profit,
            "net_income": self.net_income,
            "total_assets": self.total_assets,
            "total_liabilities": self.total_liabilities,
            "total_equity": self.total_equity,
            "retained_earnings": self.retained_earnings,
            "debt_ratio": self.debt_ratio,
            "report_code": self.report_code,
            "source": self.source,
            "confidence": self.confidence,
        }


async def get_financial_statements(
    corp_code: str,
    bsns_year: Optional[str] = None,
    reprt_code: str = "11011",  # 11011: 사업보고서
    fs_div: str = "OFS",  # OFS: 개별재무제표, CFS: 연결재무제표
) -> list[FinancialStatement]:
    """
    P2: DART 재무제표 주요계정 조회 (100% Fact)

    단일회사 주요계정 API를 호출하여 매출액, 영업이익, 순이익 등을 조회합니다.

    API: https://opendart.fss.or.kr/api/fnlttSinglAcnt.json

    Args:
        corp_code: DART 고유번호 (8자리)
        bsns_year: 사업연도 (미지정 시 최근 3년)
        reprt_code: 보고서 코드 (11011=사업보고서, 11012=반기, 11013=1분기, 11014=3분기)
        fs_div: 재무제표 구분 (OFS=개별, CFS=연결)

    Returns:
        FinancialStatement 객체 리스트
    """
    url = f"{DART_BASE_URL}/fnlttSinglAcnt.json"

    # 사업연도 미지정 시 최근 3년 조회
    years = []
    if bsns_year:
        years = [bsns_year]
    else:
        current_year = datetime.now().year
        years = [str(current_year - i) for i in range(1, 4)]  # 전년도, 2년전, 3년전

    all_statements = []

    for year in years:
        params = {
            "crtfc_key": DART_API_KEY,
            "corp_code": corp_code,
            "bsns_year": year,
            "reprt_code": reprt_code,
            "fs_div": fs_div,
        }

        try:
            async with httpx.AsyncClient(timeout=DART_TIMEOUT) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                status = data.get("status", "")
                message = data.get("message", "")

                if status == DART_STATUS_NO_DATA:
                    logger.debug(f"[DartAPI] No financial data for corp_code={corp_code}, year={year}")
                    continue

                if status != DART_STATUS_SUCCESS:
                    logger.warning(f"[DartAPI] Financial API error: {message}")
                    continue

                # 재무 항목 파싱
                items = data.get("list", [])
                statement = _parse_financial_items(items, year, reprt_code)
                if statement:
                    all_statements.append(statement)

        except Exception as e:
            logger.warning(f"[DartAPI] Failed to get financial data for year={year}: {e}")
            continue

    logger.info(f"[DartAPI] Found {len(all_statements)} financial statements for corp_code={corp_code}")
    return all_statements


def _parse_financial_items(items: list[dict], bsns_year: str, reprt_code: str) -> Optional[FinancialStatement]:
    """DART 재무제표 항목 파싱"""
    if not items:
        return None

    def parse_amount(val: str) -> Optional[int]:
        if not val or val == "-":
            return None
        try:
            return int(val.replace(",", ""))
        except ValueError:
            return None

    revenue = None
    operating_profit = None
    net_income = None
    total_assets = None
    total_liabilities = None
    total_equity = None
    retained_earnings = None

    for item in items:
        account_nm = item.get("account_nm", "")
        thstrm_amount = item.get("thstrm_amount", "")  # 당기

        # 주요 계정 매핑
        if "매출액" in account_nm or "수익(매출액)" in account_nm:
            revenue = parse_amount(thstrm_amount)
        elif "영업이익" in account_nm:
            operating_profit = parse_amount(thstrm_amount)
        elif "당기순이익" in account_nm or "당기순손익" in account_nm:
            net_income = parse_amount(thstrm_amount)
        elif account_nm == "자산총계":
            total_assets = parse_amount(thstrm_amount)
        elif account_nm == "부채총계":
            total_liabilities = parse_amount(thstrm_amount)
        elif account_nm == "자본총계":
            total_equity = parse_amount(thstrm_amount)
        elif "이익잉여금" in account_nm or "잉여금" in account_nm:
            retained_earnings = parse_amount(thstrm_amount)

    # 부채비율 계산
    debt_ratio = None
    if total_liabilities and total_equity and total_equity > 0:
        debt_ratio = round((total_liabilities / total_equity) * 100, 2)

    return FinancialStatement(
        bsns_year=bsns_year,
        revenue=revenue,
        operating_profit=operating_profit,
        net_income=net_income,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=total_equity,
        retained_earnings=retained_earnings,
        debt_ratio=debt_ratio,
        report_code=reprt_code,
        source="DART",
        confidence="HIGH",
    )


async def get_financial_statements_by_name(corp_name: str) -> list[FinancialStatement]:
    """
    기업명으로 재무제표 조회

    Args:
        corp_name: 기업명

    Returns:
        FinancialStatement 객체 리스트 (최근 3년)
    """
    corp_code = await get_corp_code(corp_name=corp_name)
    if not corp_code:
        logger.warning(f"[DartAPI] Could not find corp_code for '{corp_name}'")
        return []
    return await get_financial_statements(corp_code)


# ============================================================================
# P3: Major Event Report API (주요사항보고서)
# ============================================================================

class MajorEventType(str, Enum):
    """주요사항보고서 유형"""
    # 경영권 관련
    TAKEOVER = "인수/합병"
    MERGER = "합병"
    SPLIT = "분할"
    STOCK_TRANSFER = "주식양수도"
    # 자본 관련
    CAPITAL_INCREASE = "유상증자"
    CAPITAL_DECREASE = "감자"
    CONVERTIBLE_BOND = "전환사채"
    BOND_WITH_WARRANT = "신주인수권부사채"
    # 사업 관련
    BUSINESS_TRANSFER = "영업양수도"
    NEW_FACILITY = "신규시설투자"
    OVERSEAS_INVESTMENT = "해외투자"
    # 재무/부정
    AUDIT_OPINION = "감사의견"
    LITIGATION = "소송"
    SANCTION = "제재"
    DEFAULT = "채무불이행"
    # 기타
    OTHER = "기타"


@dataclass
class MajorEvent:
    """주요사항보고서 정보 (100% Fact - DART 공시)"""
    rcept_no: str  # 접수번호
    rcept_dt: str  # 접수일자
    report_nm: str  # 보고서명
    event_type: MajorEventType  # 이벤트 유형
    corp_name: str  # 회사명
    flr_nm: Optional[str] = None  # 제출인
    rm: Optional[str] = None  # 비고
    source_url: Optional[str] = None
    source: str = "DART"
    confidence: str = "HIGH"

    def to_dict(self) -> dict:
        return {
            "rcept_no": self.rcept_no,
            "rcept_dt": self.rcept_dt,
            "report_nm": self.report_nm,
            "event_type": self.event_type.value,
            "corp_name": self.corp_name,
            "flr_nm": self.flr_nm,
            "rm": self.rm,
            "source_url": self.source_url or f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={self.rcept_no}",
            "source": self.source,
            "confidence": self.confidence,
        }


def _classify_event_type(report_nm: str) -> MajorEventType:
    """보고서명으로 이벤트 유형 분류"""
    report_nm = report_nm.lower()

    # 경영권 관련
    if "인수" in report_nm or "취득" in report_nm:
        return MajorEventType.TAKEOVER
    if "합병" in report_nm:
        return MajorEventType.MERGER
    if "분할" in report_nm:
        return MajorEventType.SPLIT
    if "양수도" in report_nm and "주식" in report_nm:
        return MajorEventType.STOCK_TRANSFER

    # 자본 관련
    if "유상증자" in report_nm or "증자" in report_nm:
        return MajorEventType.CAPITAL_INCREASE
    if "감자" in report_nm:
        return MajorEventType.CAPITAL_DECREASE
    if "전환사채" in report_nm:
        return MajorEventType.CONVERTIBLE_BOND
    if "신주인수권" in report_nm:
        return MajorEventType.BOND_WITH_WARRANT

    # 사업 관련
    if "영업양수도" in report_nm or "사업양수도" in report_nm:
        return MajorEventType.BUSINESS_TRANSFER
    if "시설투자" in report_nm or "설비투자" in report_nm:
        return MajorEventType.NEW_FACILITY
    if "해외" in report_nm and ("투자" in report_nm or "진출" in report_nm):
        return MajorEventType.OVERSEAS_INVESTMENT

    # 재무/부정
    if "감사" in report_nm and ("의견" in report_nm or "거절" in report_nm):
        return MajorEventType.AUDIT_OPINION
    if "소송" in report_nm:
        return MajorEventType.LITIGATION
    if "제재" in report_nm or "조치" in report_nm:
        return MajorEventType.SANCTION
    if "채무불이행" in report_nm or "부도" in report_nm:
        return MajorEventType.DEFAULT

    return MajorEventType.OTHER


async def get_major_events(
    corp_code: str,
    bgn_de: Optional[str] = None,  # 시작일 (YYYYMMDD)
    end_de: Optional[str] = None,  # 종료일 (YYYYMMDD)
    pblntf_ty: str = "B",  # B: 주요사항보고
) -> list[MajorEvent]:
    """
    P3: DART 주요사항보고서 조회 (100% Fact)

    공시검색 API를 호출하여 주요사항보고서를 조회합니다.
    인수/합병, 유상증자, 소송, 감사의견 등 중요 이벤트를 추적합니다.

    API: https://opendart.fss.or.kr/api/list.json

    Args:
        corp_code: DART 고유번호 (8자리)
        bgn_de: 시작일 (YYYYMMDD, 미지정 시 1년 전)
        end_de: 종료일 (YYYYMMDD, 미지정 시 오늘)
        pblntf_ty: 공시유형 (B=주요사항보고)

    Returns:
        MajorEvent 객체 리스트
    """
    url = f"{DART_BASE_URL}/list.json"

    # 기본 기간: 최근 1년
    if not end_de:
        end_de = datetime.now().strftime("%Y%m%d")
    if not bgn_de:
        bgn_de = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

    params = {
        "crtfc_key": DART_API_KEY,
        "corp_code": corp_code,
        "bgn_de": bgn_de,
        "end_de": end_de,
        "pblntf_ty": pblntf_ty,
        "page_count": 100,  # 최대 100건
    }

    try:
        async with httpx.AsyncClient(timeout=DART_TIMEOUT) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            status = data.get("status", "")
            message = data.get("message", "")

            if status == DART_STATUS_NO_DATA:
                logger.info(f"[DartAPI] No major events for corp_code={corp_code}")
                return []

            if status != DART_STATUS_SUCCESS:
                raise DartError(status, message)

            events = []
            items = data.get("list", [])

            for item in items:
                event = MajorEvent(
                    rcept_no=item.get("rcept_no", ""),
                    rcept_dt=item.get("rcept_dt", ""),
                    report_nm=item.get("report_nm", ""),
                    event_type=_classify_event_type(item.get("report_nm", "")),
                    corp_name=item.get("corp_name", ""),
                    flr_nm=item.get("flr_nm"),
                    rm=item.get("rm"),
                )
                events.append(event)

            logger.info(f"[DartAPI] Found {len(events)} major events for corp_code={corp_code}")
            return events

    except httpx.HTTPError as e:
        logger.error(f"[DartAPI] HTTP error getting major events: {e}")
        return []
    except DartError as e:
        logger.error(f"[DartAPI] {e}")
        return []
    except Exception as e:
        logger.error(f"[DartAPI] Unexpected error getting major events: {e}")
        return []


async def get_major_events_by_name(corp_name: str) -> list[MajorEvent]:
    """
    기업명으로 주요사항보고서 조회

    Args:
        corp_name: 기업명

    Returns:
        MajorEvent 객체 리스트 (최근 1년)
    """
    corp_code = await get_corp_code(corp_name=corp_name)
    if not corp_code:
        logger.warning(f"[DartAPI] Could not find corp_code for '{corp_name}'")
        return []
    return await get_major_events(corp_code)


# ============================================================================
# P4: Executive Dataclass (임원현황) - ExtendedFactProfile에서 사용하므로 먼저 정의
# ============================================================================

@dataclass
class Executive:
    """임원 정보 (100% Fact - DART 공시)"""
    nm: str  # 성명
    sexdstn: Optional[str] = None  # 성별 (남, 여)
    birth_ym: Optional[str] = None  # 출생년월 (YYYY년 MM월)
    ofcps: Optional[str] = None  # 직위
    rgist_exctv_at: Optional[str] = None  # 등기임원여부 (등기임원, 미등기임원)
    fte_at: Optional[str] = None  # 상근여부 (상근, 비상근)
    chrg_job: Optional[str] = None  # 담당업무
    main_career: Optional[str] = None  # 주요약력
    mxmm_shrholdr_relate: Optional[str] = None  # 최대주주와의 관계
    tenure_start: Optional[str] = None  # 임기 시작일
    tenure_end: Optional[str] = None  # 임기 종료일
    report_date: Optional[str] = None  # 보고서 기준일
    source: str = "DART"
    confidence: str = "HIGH"

    def to_dict(self) -> dict:
        return {
            "name": self.nm,
            "gender": self.sexdstn,
            "birth_ym": self.birth_ym,
            "position": self.ofcps,
            "is_registered": self.rgist_exctv_at == "등기임원",
            "is_fulltime": self.fte_at == "상근",
            "job": self.chrg_job,
            "career": self.main_career,
            "relation_to_largest_shareholder": self.mxmm_shrholdr_relate,
            "tenure_start": self.tenure_start,
            "tenure_end": self.tenure_end,
            "report_date": self.report_date,
            "source": self.source,
            "confidence": self.confidence,
        }


# ============================================================================
# P2/P3: Extended Fact-Based Profile (재무 + 주요이벤트 포함)
# ============================================================================

@dataclass
class ExtendedFactProfile:
    """
    확장된 Fact 기반 프로필 (P0 + P2 + P3 + P4)

    - 기업개황 (P0)
    - 최대주주 현황 (P0)
    - 재무제표 (P2)
    - 주요사항보고서 (P3)
    - 임원현황 (P4)
    """
    company_info: Optional[CompanyInfo] = None
    largest_shareholders: list[LargestShareholder] = field(default_factory=list)
    financial_statements: list[FinancialStatement] = field(default_factory=list)
    major_events: list[MajorEvent] = field(default_factory=list)
    executives: list[Executive] = field(default_factory=list)  # P4
    corp_code: Optional[str] = None
    fetch_timestamp: Optional[str] = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "company_info": self.company_info.to_dict() if self.company_info else None,
            "largest_shareholders": [s.to_dict() for s in self.largest_shareholders],
            "financial_statements": [f.to_dict() for f in self.financial_statements],
            "major_events": [e.to_dict() for e in self.major_events],
            "executives": [e.to_dict() for e in self.executives],  # P4
            "corp_code": self.corp_code,
            "fetch_timestamp": self.fetch_timestamp,
            "errors": self.errors,
            "source": "DART",
            "confidence": "HIGH",
        }

    @property
    def latest_revenue(self) -> Optional[int]:
        """최신 매출액"""
        if self.financial_statements:
            return self.financial_statements[0].revenue
        return None

    @property
    def latest_net_income(self) -> Optional[int]:
        """최신 당기순이익"""
        if self.financial_statements:
            return self.financial_statements[0].net_income
        return None

    @property
    def has_risk_events(self) -> bool:
        """위험 이벤트 존재 여부"""
        risk_types = {
            MajorEventType.LITIGATION,
            MajorEventType.SANCTION,
            MajorEventType.DEFAULT,
            MajorEventType.AUDIT_OPINION,
        }
        return any(e.event_type in risk_types for e in self.major_events)

    # FactBasedProfileData와 호환되는 프로퍼티들 (corp_profiling.py에서 사용)
    @property
    def ceo_name(self) -> Optional[str]:
        """CEO 이름 (100% Fact)"""
        return self.company_info.ceo_name if self.company_info else None

    @property
    def headquarters(self) -> Optional[str]:
        """본사 주소 (100% Fact)"""
        return self.company_info.adres if self.company_info else None

    @property
    def founded_year(self) -> Optional[int]:
        """설립연도 (100% Fact)"""
        if self.company_info and self.company_info.est_dt:
            try:
                return int(self.company_info.est_dt[:4])
            except (ValueError, IndexError):
                return None
        return None

    @property
    def shareholders(self) -> list[dict]:
        """주주 정보 (100% Fact)"""
        return [s.to_dict() for s in self.largest_shareholders]


async def get_extended_fact_profile(corp_name: str) -> ExtendedFactProfile:
    """
    확장된 Fact 기반 프로필 조회 (P0 + P2 + P3 + P4)

    기업개황, 최대주주, 재무제표, 주요사항보고서, 임원현황을 한 번에 조회합니다.

    Args:
        corp_name: 기업명

    Returns:
        ExtendedFactProfile 객체
    """
    result = ExtendedFactProfile(
        fetch_timestamp=datetime.now(UTC).isoformat(),
        errors=[],
    )

    # 1. Corp Code 조회
    corp_code = await get_corp_code(corp_name=corp_name)
    if not corp_code:
        result.errors.append(f"DART 고유번호를 찾을 수 없습니다: {corp_name}")
        return result

    result.corp_code = corp_code

    # 2. 병렬 조회 (P0 + P2 + P3 + P4)
    try:
        company_info_task = get_company_info(corp_code)
        shareholders_task = get_largest_shareholders(corp_code)
        financial_task = get_financial_statements(corp_code)
        events_task = get_major_events(corp_code)
        executives_task = get_executives(corp_code)  # P4

        company_info, shareholders, financials, events, executives = await asyncio.gather(
            company_info_task,
            shareholders_task,
            financial_task,
            events_task,
            executives_task,
            return_exceptions=True,
        )

        # 결과 처리
        if isinstance(company_info, Exception):
            result.errors.append(f"기업개황 조회 실패: {str(company_info)}")
        else:
            result.company_info = company_info

        if isinstance(shareholders, Exception):
            result.errors.append(f"최대주주 조회 실패: {str(shareholders)}")
        else:
            result.largest_shareholders = shareholders or []

        if isinstance(financials, Exception):
            result.errors.append(f"재무제표 조회 실패: {str(financials)}")
        else:
            result.financial_statements = financials or []

        if isinstance(events, Exception):
            result.errors.append(f"주요사항 조회 실패: {str(events)}")
        else:
            result.major_events = events or []

        if isinstance(executives, Exception):
            result.errors.append(f"임원현황 조회 실패: {str(executives)}")
        else:
            result.executives = executives or []

    except Exception as e:
        result.errors.append(f"조회 중 오류: {str(e)}")

    logger.info(
        f"[DartAPI] Extended fact profile for '{corp_name}': "
        f"company={'있음' if result.company_info else '없음'}, "
        f"shareholders={len(result.largest_shareholders)}, "
        f"financials={len(result.financial_statements)}, "
        f"events={len(result.major_events)}, "
        f"executives={len(result.executives)}"
    )

    return result


# ============================================================================
# Major Shareholder API (기존 - 주요주주 소유보고)
# ============================================================================

async def get_major_shareholders(
    corp_code: str,
    limit: int = 10,
) -> list[Shareholder]:
    """
    DART 주요주주 소유보고 조회

    임원ㆍ주요주주특정증권등 소유상황보고서 API를 호출하여
    주요 주주 목록을 반환합니다.

    Args:
        corp_code: DART 고유번호 (8자리)
        limit: 최대 반환 주주 수

    Returns:
        Shareholder 객체 리스트
    """
    url = f"{DART_BASE_URL}/elestock.json"
    params = {
        "crtfc_key": DART_API_KEY,
        "corp_code": corp_code,
    }

    try:
        async with httpx.AsyncClient(timeout=DART_TIMEOUT) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            status = data.get("status", "")
            message = data.get("message", "")

            if status == DART_STATUS_NO_DATA:
                logger.info(f"[DartAPI] No shareholder data for corp_code={corp_code}")
                return []

            if status != DART_STATUS_SUCCESS:
                raise DartError(status, message)

            shareholders = []
            items = data.get("list", [])

            for item in items[:limit]:
                shareholder = _parse_shareholder_item(item)
                if shareholder:
                    shareholders.append(shareholder)

            # 지분율 기준 정렬
            shareholders.sort(key=lambda s: s.ratio_pct, reverse=True)

            logger.info(f"[DartAPI] Found {len(shareholders)} shareholders for corp_code={corp_code}")
            return shareholders

    except httpx.HTTPError as e:
        logger.error(f"[DartAPI] HTTP error: {e}")
        return []
    except DartError as e:
        logger.error(f"[DartAPI] {e}")
        return []
    except Exception as e:
        logger.error(f"[DartAPI] Unexpected error: {e}")
        return []


def _parse_shareholder_item(item: dict) -> Optional[Shareholder]:
    """DART API 응답 항목을 Shareholder 객체로 변환"""
    try:
        # 보고자명
        name = item.get("repror", "").strip()
        if not name:
            return None

        # 지분율 파싱 (소수점 이하 2자리)
        ratio_str = item.get("sp_stock_lmp_rate", "0")
        try:
            ratio_pct = float(ratio_str) if ratio_str else 0.0
        except ValueError:
            ratio_pct = 0.0

        # 소유 수량
        count_str = item.get("sp_stock_lmp_cnt", "0")
        try:
            share_count = int(count_str.replace(",", "")) if count_str else 0
        except ValueError:
            share_count = 0

        # 주주 유형 판별
        relation = item.get("isu_main_shrholdr", "")
        shareholder_type = _classify_shareholder_type(relation)

        # 보고일
        report_date = item.get("rcept_dt", None)

        # 접수번호로 공시 URL 생성
        rcept_no = item.get("rcept_no", "")
        source_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}" if rcept_no else None

        return Shareholder(
            name=name,
            ratio_pct=ratio_pct,
            share_count=share_count,
            shareholder_type=shareholder_type,
            report_date=report_date,
            source="DART",
            source_url=source_url,
            confidence="HIGH",
        )

    except Exception as e:
        logger.warning(f"[DartAPI] Failed to parse shareholder item: {e}")
        return None


def _classify_shareholder_type(relation: str) -> ShareholderType:
    """주주 관계 유형 분류"""
    if not relation:
        return ShareholderType.UNKNOWN

    if "10%" in relation or "대량" in relation:
        return ShareholderType.MAJOR_SHAREHOLDER
    if "최대" in relation:
        return ShareholderType.LARGEST_SHAREHOLDER
    if "임원" in relation:
        return ShareholderType.EXECUTIVE
    if "특수" in relation:
        return ShareholderType.RELATED_PARTY
    if "기관" in relation:
        return ShareholderType.INSTITUTION
    if "외국" in relation:
        return ShareholderType.FOREIGN

    return ShareholderType.UNKNOWN


# ============================================================================
# 2-Source Verification
# ============================================================================

def _normalize_shareholder_name(name: str) -> str:
    """주주명 정규화 (비교용)"""
    if not name:
        return ""
    # 공백, 특수문자 제거, 소문자 변환
    normalized = re.sub(r'[^\w가-힣]', '', name.lower())
    # 일반적인 접미사 제거
    suffixes = ["주식회사", "유한회사", "유한책임회사", "inc", "corp", "ltd", "llc"]
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
    return normalized.strip()


def _match_shareholders(
    dart_shareholders: list[Shareholder],
    perplexity_shareholders: list[dict],
    ratio_tolerance: float = 5.0,  # 지분율 허용 오차 (%)
) -> tuple[list[Shareholder], list[Shareholder], list[dict]]:
    """
    DART와 Perplexity 주주 정보 매칭

    Args:
        dart_shareholders: DART API에서 조회한 주주 목록
        perplexity_shareholders: Perplexity 검색 결과의 주주 목록
        ratio_tolerance: 지분율 허용 오차 (퍼센트 포인트)

    Returns:
        (matched, dart_only, perplexity_only)
    """
    matched = []
    dart_only = list(dart_shareholders)  # 복사본
    perplexity_only = list(perplexity_shareholders)  # 복사본

    for dart_sh in dart_shareholders:
        dart_name_norm = _normalize_shareholder_name(dart_sh.name)

        for i, perp_sh in enumerate(perplexity_only):
            perp_name = perp_sh.get("name", "")
            perp_name_norm = _normalize_shareholder_name(perp_name)
            perp_ratio = perp_sh.get("ratio_pct", 0)

            # 이름 매칭 (정규화 후 포함 관계)
            name_match = (
                dart_name_norm in perp_name_norm or
                perp_name_norm in dart_name_norm or
                dart_name_norm == perp_name_norm
            )

            # 지분율 매칭 (허용 오차 내)
            ratio_match = abs(dart_sh.ratio_pct - perp_ratio) <= ratio_tolerance

            # 이름이 매칭되면 (지분율은 참고만)
            if name_match:
                matched.append(dart_sh)
                dart_only.remove(dart_sh)
                perplexity_only.pop(i)
                break

    return matched, dart_only, perplexity_only


async def verify_shareholders(
    corp_name: str,
    perplexity_shareholders: list[dict],
    corp_code: Optional[str] = None,
) -> VerificationResult:
    """
    2-Source Verification: DART + Perplexity 교차 검증

    Perplexity 검색 결과의 주주 정보를 DART 공시와 교차 검증합니다.
    두 소스에서 일치하는 주주 정보만 신뢰할 수 있는 것으로 표시합니다.

    Args:
        corp_name: 기업명
        perplexity_shareholders: Perplexity에서 추출한 주주 정보
        corp_code: DART 고유번호 (없으면 기업명으로 조회)

    Returns:
        VerificationResult 객체
    """
    # 1. Corp Code 조회
    if not corp_code:
        corp_code = await get_corp_code(corp_name=corp_name)

    if not corp_code:
        logger.warning(f"[DartAPI] Could not find corp_code for '{corp_name}'")
        return VerificationResult(
            is_verified=False,
            dart_shareholders=[],
            perplexity_shareholders=perplexity_shareholders,
            matched_shareholders=[],
            dart_only=[],
            perplexity_only=perplexity_shareholders,
            verification_details={
                "error": "corp_code_not_found",
                "message": f"DART 고유번호를 찾을 수 없습니다: {corp_name}",
            },
        )

    # 2. DART 주요주주 조회
    dart_shareholders = await get_major_shareholders(corp_code)

    if not dart_shareholders:
        logger.info(f"[DartAPI] No DART shareholders for '{corp_name}'")
        return VerificationResult(
            is_verified=False,
            dart_shareholders=[],
            perplexity_shareholders=perplexity_shareholders,
            matched_shareholders=[],
            dart_only=[],
            perplexity_only=perplexity_shareholders,
            verification_details={
                "error": "no_dart_data",
                "message": f"DART에서 주주 정보를 찾을 수 없습니다: {corp_name}",
                "corp_code": corp_code,
            },
        )

    # 3. 매칭
    matched, dart_only, perplexity_only = _match_shareholders(
        dart_shareholders, perplexity_shareholders
    )

    # 4. 검증 결과 판정
    # 매칭된 주주가 1명 이상이면 검증 성공
    is_verified = len(matched) >= 1

    verification_details = {
        "corp_code": corp_code,
        "dart_count": len(dart_shareholders),
        "perplexity_count": len(perplexity_shareholders),
        "matched_count": len(matched),
        "dart_only_count": len(dart_only),
        "perplexity_only_count": len(perplexity_only),
        "verification_timestamp": datetime.now(UTC).isoformat(),
    }

    logger.info(
        f"[DartAPI] Verification result for '{corp_name}': "
        f"verified={is_verified}, matched={len(matched)}, "
        f"dart_only={len(dart_only)}, perplexity_only={len(perplexity_only)}"
    )

    return VerificationResult(
        is_verified=is_verified,
        dart_shareholders=dart_shareholders,
        perplexity_shareholders=perplexity_shareholders,
        matched_shareholders=matched,
        dart_only=dart_only,
        perplexity_only=perplexity_only,
        verification_details=verification_details,
    )


# ============================================================================
# Integration Helper
# ============================================================================

async def get_verified_shareholders(
    corp_name: str,
    perplexity_shareholders: Optional[list[dict]] = None,
    use_dart_only: bool = False,
) -> tuple[list[dict], dict]:
    """
    검증된 주주 정보 조회 (Corp Profiling 통합용)

    2-Source Verification을 수행하고, 검증된 주주 정보만 반환합니다.
    DART 데이터가 없거나 검증 실패 시 Perplexity 데이터를 낮은 신뢰도로 반환합니다.

    Args:
        corp_name: 기업명
        perplexity_shareholders: Perplexity에서 추출한 주주 정보
        use_dart_only: True면 DART 데이터만 사용 (검증 없이)

    Returns:
        (shareholders_list, metadata)
        - shareholders_list: 주주 정보 리스트 (검증된 것 우선)
        - metadata: 검증 메타데이터
    """
    metadata = {
        "source": "UNKNOWN",
        "verified": False,
        "dart_available": False,
        "verification_details": {},
    }

    # DART만 사용 모드
    if use_dart_only:
        corp_code = await get_corp_code(corp_name=corp_name)
        if corp_code:
            dart_shareholders = await get_major_shareholders(corp_code)
            if dart_shareholders:
                metadata["source"] = "DART"
                metadata["dart_available"] = True
                return (
                    [s.to_dict() for s in dart_shareholders],
                    metadata,
                )
        return [], metadata

    # Perplexity 데이터가 없으면 DART만 사용
    if not perplexity_shareholders:
        corp_code = await get_corp_code(corp_name=corp_name)
        if corp_code:
            dart_shareholders = await get_major_shareholders(corp_code)
            if dart_shareholders:
                metadata["source"] = "DART"
                metadata["dart_available"] = True
                return (
                    [s.to_dict() for s in dart_shareholders],
                    metadata,
                )
        return [], metadata

    # 2-Source Verification
    result = await verify_shareholders(corp_name, perplexity_shareholders)
    metadata["verification_details"] = result.verification_details
    metadata["dart_available"] = len(result.dart_shareholders) > 0

    if result.is_verified:
        # 검증 성공: 매칭된 주주 + DART only 주주 반환
        metadata["source"] = "DART_VERIFIED"
        metadata["verified"] = True

        verified_list = [s.to_dict() for s in result.matched_shareholders]

        # DART에만 있는 주주도 추가 (공시 데이터이므로 신뢰 가능)
        for s in result.dart_only:
            sh_dict = s.to_dict()
            sh_dict["_note"] = "DART에서만 확인됨"
            verified_list.append(sh_dict)

        return verified_list, metadata

    # 검증 실패: Perplexity 데이터를 낮은 신뢰도로 반환
    metadata["source"] = "PERPLEXITY_UNVERIFIED"
    metadata["verified"] = False

    unverified_list = []
    for sh in perplexity_shareholders:
        sh_copy = dict(sh)
        sh_copy["confidence"] = "LOW"  # 검증되지 않음
        sh_copy["_note"] = "DART 검증 실패 - 신뢰도 낮음"
        unverified_list.append(sh_copy)

    return unverified_list, metadata


# ============================================================================
# P4: Executive API (임원현황 조회 함수)
# Executive dataclass는 상단에 정의됨 (ExtendedFactProfile에서 사용)
# ============================================================================

async def get_executives(
    corp_code: str,
    bsns_year: Optional[str] = None,
    reprt_code: str = "11011",  # 11011: 사업보고서
) -> list[Executive]:
    """
    P4: DART 임원현황 조회 (100% Fact)

    사업보고서에 기재된 임원 현황을 조회합니다.
    대표이사, 이사, 감사 등 임원 정보를 반환합니다.

    API: https://opendart.fss.or.kr/api/exctvSttus.json

    Args:
        corp_code: DART 고유번호 (8자리)
        bsns_year: 사업연도 (미지정 시 전년도)
        reprt_code: 보고서 코드
            - 11011: 사업보고서 (1년 전체)
            - 11012: 반기보고서
            - 11013: 1분기보고서
            - 11014: 3분기보고서

    Returns:
        Executive 객체 리스트
    """
    url = f"{DART_BASE_URL}/exctvSttus.json"

    # 사업연도 미지정 시 전년도 사용
    if not bsns_year:
        bsns_year = str(datetime.now().year - 1)

    params = {
        "crtfc_key": DART_API_KEY,
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
    }

    try:
        async with httpx.AsyncClient(timeout=DART_TIMEOUT) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            status = data.get("status", "")
            message = data.get("message", "")

            if status == DART_STATUS_NO_DATA:
                logger.info(f"[DartAPI] No executive data for corp_code={corp_code}, year={bsns_year}")
                # 전년도 데이터가 없으면 2년 전 시도
                if bsns_year == str(datetime.now().year - 1):
                    logger.info(f"[DartAPI] Trying previous year for executives...")
                    return await get_executives(
                        corp_code,
                        bsns_year=str(datetime.now().year - 2),
                        reprt_code=reprt_code,
                    )
                return []

            if status != DART_STATUS_SUCCESS:
                raise DartError(status, message)

            executives = []
            items = data.get("list", [])

            for item in items:
                executive = _parse_executive_item(item, bsns_year)
                if executive:
                    executives.append(executive)

            logger.info(f"[DartAPI] Found {len(executives)} executives for corp_code={corp_code}")
            return executives

    except httpx.HTTPError as e:
        logger.error(f"[DartAPI] HTTP error getting executives: {e}")
        return []
    except DartError as e:
        logger.error(f"[DartAPI] {e}")
        return []
    except Exception as e:
        logger.error(f"[DartAPI] Unexpected error getting executives: {e}")
        return []


def _parse_executive_item(item: dict, bsns_year: str) -> Optional[Executive]:
    """DART 임원현황 응답 항목을 Executive 객체로 변환"""
    try:
        nm = item.get("nm", "").strip()
        if not nm or nm == "-":
            return None

        return Executive(
            nm=nm,
            sexdstn=item.get("sexdstn"),
            birth_ym=item.get("birth_ym"),
            ofcps=item.get("ofcps"),
            rgist_exctv_at=item.get("rgist_exctv_at"),
            fte_at=item.get("fte_at"),
            chrg_job=item.get("chrg_job"),
            main_career=item.get("main_career"),
            mxmm_shrholdr_relate=item.get("mxmm_shrholdr_relate"),
            tenure_start=item.get("entcondt"),
            tenure_end=item.get("retiradt"),
            report_date=f"{bsns_year}1231",
            source="DART",
            confidence="HIGH",
        )

    except Exception as e:
        logger.warning(f"[DartAPI] Failed to parse executive item: {e}")
        return None


async def get_executives_by_name(corp_name: str) -> list[Executive]:
    """
    기업명으로 임원현황 조회

    Args:
        corp_name: 기업명 (예: "삼성전자", "엠케이전자")

    Returns:
        Executive 객체 리스트
    """
    corp_code = await get_corp_code(corp_name=corp_name)
    if not corp_code:
        logger.warning(f"[DartAPI] Could not find corp_code for '{corp_name}'")
        return []
    return await get_executives(corp_code)


# ============================================================================
# Initialization
# ============================================================================

async def initialize_dart_client():
    """
    DART API 클라이언트 초기화

    서버 시작 시 호출하여 기업 고유번호 목록을 미리 로드합니다.
    """
    logger.info("[DartAPI] Initializing DART API client...")
    success = await load_corp_codes()
    if success:
        logger.info(f"[DartAPI] Initialization complete. {len(_corp_code_cache)} corp codes loaded.")
    else:
        logger.warning("[DartAPI] Failed to initialize. DART features may not work.")
    return success
