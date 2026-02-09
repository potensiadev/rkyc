"""
Banking Data Schemas
PRD: Internal Banking Data Integration v1.1

Pydantic schemas for banking data API
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field


# ============================================================
# Enums
# ============================================================

class TrendEnum(str, Enum):
    INCREASING = "INCREASING"
    STABLE = "STABLE"
    DECREASING = "DECREASING"


class VolatilityEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SeverityEnum(str, Enum):
    HIGH = "HIGH"
    MED = "MED"
    LOW = "LOW"


class RiskCategoryEnum(str, Enum):
    LOAN = "LOAN"
    DEPOSIT = "DEPOSIT"
    CARD = "CARD"
    COLLATERAL = "COLLATERAL"
    TRADE = "TRADE"
    FINANCIAL = "FINANCIAL"


class CollateralTypeEnum(str, Enum):
    REAL_ESTATE = "REAL_ESTATE"
    DEPOSIT = "DEPOSIT"
    SECURITIES = "SECURITIES"


class ImpactEnum(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DevelopmentStatusEnum(str, Enum):
    APPROVED = "APPROVED"
    UNDER_CONSTRUCTION = "UNDER_CONSTRUCTION"
    COMPLETED = "COMPLETED"
    DELAYED = "DELAYED"
    CANCELLED = "CANCELLED"


class FinancialHealthEnum(str, Enum):
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    CAUTION = "CAUTION"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    IMPROVING = "IMPROVING"


# ============================================================
# Loan Exposure Schemas
# ============================================================

class LoanCompositionItem(BaseModel):
    amount: int = Field(..., description="금액 (원)")
    ratio: float = Field(..., description="비율 (%)")


class LoanComposition(BaseModel):
    secured_loan: LoanCompositionItem = Field(..., description="담보대출")
    unsecured_loan: LoanCompositionItem = Field(..., description="신용대출")
    fx_loan: LoanCompositionItem = Field(..., description="외화대출")


class RiskIndicators(BaseModel):
    overdue_flag: bool = Field(False, description="연체 여부")
    overdue_days: int = Field(0, description="연체일수")
    overdue_amount: int = Field(0, description="연체금액")
    watch_list: bool = Field(False, description="Watch List 등재 여부")
    watch_list_reason: Optional[str] = Field(None, description="Watch List 사유")
    internal_grade: str = Field(..., description="내부등급")
    grade_change: Optional[str] = Field(None, description="등급변동 (UP/DOWN)")
    next_review_date: Optional[str] = Field(None, description="차기심사일")


class YearlyTrendItem(BaseModel):
    year: int
    secured: int = Field(..., description="담보대출 (억원)")
    unsecured: int = Field(..., description="신용대출 (억원)")
    fx: int = Field(..., description="외화대출 (억원)")
    total: int = Field(..., description="합계 (억원)")


class LoanExposure(BaseModel):
    as_of_date: str = Field(..., description="기준일")
    total_exposure_krw: int = Field(..., description="총 여신잔액 (원)")
    yearly_trend: List[YearlyTrendItem] = Field(default_factory=list, description="연도별 추이")
    composition: LoanComposition = Field(..., description="여신 구성")
    risk_indicators: RiskIndicators = Field(..., description="리스크 지표")


# ============================================================
# Deposit Trend Schemas
# ============================================================

class MonthlyBalance(BaseModel):
    month: str = Field(..., description="월 (YYYY-MM)")
    balance: int = Field(..., description="잔액 (원)")


class DepositTrend(BaseModel):
    monthly_balance: List[MonthlyBalance] = Field(default_factory=list, description="월별 잔액")
    current_balance: int = Field(..., description="현재 잔액")
    avg_balance_6m: int = Field(..., description="6개월 평균")
    min_balance_6m: Optional[int] = Field(None, description="6개월 최소")
    max_balance_6m: Optional[int] = Field(None, description="6개월 최대")
    trend: TrendEnum = Field(..., description="추세")
    volatility: VolatilityEnum = Field(VolatilityEnum.LOW, description="변동성")
    large_withdrawal_alerts: List[Dict[str, Any]] = Field(default_factory=list, description="대규모 출금 알림")


# ============================================================
# Card Usage Schemas
# ============================================================

class MonthlyUsage(BaseModel):
    month: str = Field(..., description="월 (YYYY-MM)")
    amount: int = Field(..., description="이용액 (원)")
    tx_count: int = Field(..., description="거래건수")


class CategoryBreakdown(BaseModel):
    travel: float = Field(0, description="출장/교통 (%)")
    entertainment: float = Field(0, description="접대비 (%)")
    office_supplies: float = Field(0, description="사무용품 (%)")
    fuel: float = Field(0, description="주유비 (%)")
    others: float = Field(0, description="기타 (%)")


class CardUsage(BaseModel):
    monthly_usage: List[MonthlyUsage] = Field(default_factory=list, description="월별 이용")
    category_breakdown: CategoryBreakdown = Field(..., description="카테고리별 비중")
    card_limit: int = Field(..., description="카드 한도")
    utilization_rate: float = Field(..., description="한도 소진률 (%)")
    avg_monthly_usage: int = Field(..., description="월평균 이용액")
    usage_trend: TrendEnum = Field(TrendEnum.STABLE, description="이용 추세")
    anomaly_flags: List[str] = Field(default_factory=list, description="이상 거래 플래그")


# ============================================================
# Collateral Detail Schemas
# ============================================================

class Coordinates(BaseModel):
    lat: float
    lng: float


class Location(BaseModel):
    address: str
    coordinates: Optional[Coordinates] = None


class Appraisal(BaseModel):
    value: int = Field(..., description="감정가 (원)")
    date: str = Field(..., description="감정일")
    appraiser: str = Field(..., description="감정기관")
    next_appraisal_date: Optional[str] = Field(None, description="차기감정일")
    market_trend: Optional[str] = Field(None, description="시세 추세")


class NearbyDevelopment(BaseModel):
    project_name: str = Field(..., description="프로젝트명")
    distance_km: float = Field(..., description="거리 (km)")
    impact: ImpactEnum = Field(..., description="영향도")
    description: str = Field(..., description="설명")
    expected_completion: Optional[str] = Field(None, description="예상 완공일")
    status: DevelopmentStatusEnum = Field(..., description="진행 상태")


class Collateral(BaseModel):
    id: str = Field(..., description="담보 ID")
    type: CollateralTypeEnum = Field(..., description="담보 유형")
    description: str = Field(..., description="담보 설명")
    location: Location = Field(..., description="위치")
    appraisal: Appraisal = Field(..., description="감정 정보")
    loan_amount: int = Field(..., description="담보 대출금액")
    ltv_ratio: float = Field(..., description="LTV 비율 (%)")
    nearby_development: Optional[NearbyDevelopment] = Field(None, description="인근 개발")
    risk_factors: List[str] = Field(default_factory=list, description="리스크 요인")


class CollateralDetail(BaseModel):
    collaterals: List[Collateral] = Field(default_factory=list, description="담보 목록")
    total_collateral_value: int = Field(..., description="총 담보가치")
    total_loan_against: int = Field(..., description="총 담보대출금액")
    avg_ltv: float = Field(..., description="평균 LTV (%)")
    high_ltv_collaterals: List[str] = Field(default_factory=list, description="고 LTV 담보 ID")
    expiring_appraisals: List[str] = Field(default_factory=list, description="감정 만료 담보 ID")
    reappraisal_opportunities: List[str] = Field(default_factory=list, description="재감정 기회")


# ============================================================
# Trade Finance Schemas
# ============================================================

class MonthlyReceivable(BaseModel):
    month: str
    amount_usd: int


class ExportData(BaseModel):
    monthly_receivables: List[MonthlyReceivable] = Field(default_factory=list)
    current_receivables_usd: int = Field(0)
    avg_collection_days: int = Field(0)
    overdue_receivables_usd: int = Field(0)
    major_countries: List[str] = Field(default_factory=list)
    country_concentration: Dict[str, int] = Field(default_factory=dict)


class ImportData(BaseModel):
    monthly_payables: List[MonthlyReceivable] = Field(default_factory=list)
    current_payables_usd: int = Field(0)
    major_countries: List[str] = Field(default_factory=list)
    country_concentration: Dict[str, int] = Field(default_factory=dict)


class UsanceData(BaseModel):
    limit_usd: int = Field(0)
    utilized_usd: int = Field(0)
    utilization_rate: float = Field(0)
    avg_tenor_days: int = Field(0)
    upcoming_maturities: List[Dict[str, Any]] = Field(default_factory=list)


class FxExposure(BaseModel):
    net_position_usd: int = Field(0)
    hedge_ratio: float = Field(0)
    hedge_instruments: List[str] = Field(default_factory=list)
    var_1d_usd: int = Field(0, description="1일 VaR (USD)")


class TradeFinance(BaseModel):
    export: ExportData = Field(..., description="수출")
    import_data: ImportData = Field(..., alias="import", description="수입")
    usance: UsanceData = Field(..., description="유산스")
    fx_exposure: FxExposure = Field(..., description="환노출")

    class Config:
        populate_by_name = True


# ============================================================
# Financial Statements Schemas
# ============================================================

class YearlyFinancials(BaseModel):
    assets: int = Field(..., description="총자산")
    liabilities: int = Field(..., description="총부채")
    equity: int = Field(..., description="자본")
    revenue: int = Field(..., description="매출액")
    operating_income: int = Field(..., description="영업이익")
    net_income: int = Field(..., description="당기순이익")
    current_assets: Optional[int] = Field(None, description="유동자산")
    current_liabilities: Optional[int] = Field(None, description="유동부채")
    debt_ratio: float = Field(..., description="부채비율 (%)")
    current_ratio: Optional[float] = Field(None, description="유동비율 (%)")
    interest_coverage: Optional[float] = Field(None, description="이자보상배율")


class YoyGrowth(BaseModel):
    revenue: float = Field(..., description="매출 성장률 (%)")
    operating_income: float = Field(..., description="영업이익 성장률 (%)")
    net_income: float = Field(..., description="순이익 성장률 (%)")


class FinancialStatements(BaseModel):
    source: str = Field("DART", description="데이터 출처")
    last_updated: str = Field(..., description="최종 업데이트")
    years: Dict[str, YearlyFinancials] = Field(..., description="연도별 재무제표")
    yoy_growth: YoyGrowth = Field(..., description="전년대비 성장률")
    financial_health: FinancialHealthEnum = Field(..., description="재무건전성")


# ============================================================
# Risk Alert Schema
# ============================================================

class RiskAlert(BaseModel):
    id: str = Field(..., description="알림 ID")
    severity: SeverityEnum = Field(..., description="심각도")
    category: RiskCategoryEnum = Field(..., description="카테고리")
    signal_type: str = Field(..., description="시그널 타입 (DIRECT/INDUSTRY/ENVIRONMENT)")
    title: str = Field(..., description="제목")
    description: str = Field(..., description="설명")
    recommended_action: str = Field(..., description="권장 조치")
    detected_at: str = Field(..., description="탐지 시간")


# ============================================================
# Response Schemas
# ============================================================

class BankingDataResponse(BaseModel):
    """Banking Data 전체 응답"""
    id: UUID
    corp_id: str
    data_date: date
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    loan_exposure: Optional[Dict[str, Any]] = None
    deposit_trend: Optional[Dict[str, Any]] = None
    card_usage: Optional[Dict[str, Any]] = None
    collateral_detail: Optional[Dict[str, Any]] = None
    trade_finance: Optional[Dict[str, Any]] = None
    financial_statements: Optional[Dict[str, Any]] = None

    risk_alerts: List[Dict[str, Any]] = Field(default_factory=list)
    opportunity_signals: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class BankingDataSummary(BaseModel):
    """Banking Data 요약 (리스트용)"""
    corp_id: str
    data_date: date
    total_exposure_krw: Optional[int] = None
    deposit_balance: Optional[int] = None
    risk_count: int = 0
    opportunity_count: int = 0

    class Config:
        from_attributes = True


class RiskAlertListResponse(BaseModel):
    """리스크 알림 목록 응답"""
    corp_id: str
    total: int
    high_count: int
    med_count: int
    low_count: int
    alerts: List[RiskAlert]


class OpportunityListResponse(BaseModel):
    """영업 기회 목록 응답"""
    corp_id: str
    total: int
    opportunities: List[str]


# ============================================================
# Request Schemas
# ============================================================

class BankingDataCreate(BaseModel):
    """Banking Data 생성 요청"""
    corp_id: str
    data_date: date
    loan_exposure: Optional[Dict[str, Any]] = None
    deposit_trend: Optional[Dict[str, Any]] = None
    card_usage: Optional[Dict[str, Any]] = None
    collateral_detail: Optional[Dict[str, Any]] = None
    trade_finance: Optional[Dict[str, Any]] = None
    financial_statements: Optional[Dict[str, Any]] = None


class BankingDataUpdate(BaseModel):
    """Banking Data 업데이트 요청"""
    loan_exposure: Optional[Dict[str, Any]] = None
    deposit_trend: Optional[Dict[str, Any]] = None
    card_usage: Optional[Dict[str, Any]] = None
    collateral_detail: Optional[Dict[str, Any]] = None
    trade_finance: Optional[Dict[str, Any]] = None
    financial_statements: Optional[Dict[str, Any]] = None
