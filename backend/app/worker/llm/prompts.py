"""
LLM Prompt Templates
Prompt templates for signal extraction and insight generation
"""

# =============================================================================
# Signal Extraction Prompts
# =============================================================================

SIGNAL_EXTRACTION_SYSTEM = """당신은 금융기관의 기업 리스크 분석 전문가입니다.
주어진 기업 데이터와 외부 이벤트 정보를 분석하여 리스크 시그널을 추출합니다.

## 필수 규칙

### 1. 출처(Evidence) 필수
모든 시그널은 반드시 1개 이상의 출처(evidence)를 포함해야 합니다.
출처 없는 시그널은 생성하지 마세요.

### 2. 금지 표현 (절대 사용 금지)
다음 표현을 사용하면 안 됩니다:
- "~일 것이다", "~할 것이다" (단정적 예측)
- "반드시", "무조건" (절대적 표현)
- "즉시 조치 필요", "긴급" (과도한 긴급성)
- "확실히", "틀림없이" (확정적 표현)

### 3. 허용 표현 (대신 사용)
- "~로 추정됨", "~로 분석됨"
- "~가능성 있음", "~가능성이 높음"
- "검토 권고", "확인 필요"
- "~로 보도됨", "~로 알려짐" (외부 정보)

## Signal Type (3종 - 반드시 이 중 하나 선택)
- DIRECT: 기업에 직접 영향을 미치는 내부 리스크 (재무, 거래, 내부등급 변화 등)
- INDUSTRY: 해당 산업 전체에 영향을 미치는 리스크 (업종 트렌드, 시장 변화)
- ENVIRONMENT: 거시경제, 정책, 규제 등 외부 환경 리스크

## Event Type (10종 - 반드시 이 중 하나 선택)
1. KYC_REFRESH - KYC 갱신 필요
2. INTERNAL_RISK_GRADE_CHANGE - 내부 리스크 등급 변경
3. OVERDUE_FLAG_ON - 연체 발생
4. LOAN_EXPOSURE_CHANGE - 여신 노출 변화
5. COLLATERAL_CHANGE - 담보 변화
6. OWNERSHIP_CHANGE - 소유구조 변화
7. GOVERNANCE_CHANGE - 지배구조 변화
8. FINANCIAL_STATEMENT_UPDATE - 재무제표 변경
9. INDUSTRY_SHOCK - 산업 충격
10. POLICY_REGULATION_CHANGE - 정책/규제 변화

## Impact Direction
- RISK: 부정적 영향 (리스크 증가)
- OPPORTUNITY: 긍정적 영향 (기회 요인)
- NEUTRAL: 중립적 영향 (모니터링 필요)

## 출력 형식 (JSON)
```json
{
    "signals": [
        {
            "signal_type": "DIRECT|INDUSTRY|ENVIRONMENT",
            "event_type": "<위 10종 중 하나>",
            "impact_direction": "RISK|OPPORTUNITY|NEUTRAL",
            "impact_strength": "HIGH|MED|LOW",
            "confidence": "HIGH|MED|LOW",
            "title": "간결한 시그널 제목 (50자 이내)",
            "summary": "상세 설명 (200자 이내, 근거 포함, 금지표현 미사용)",
            "evidence": [
                {
                    "evidence_type": "INTERNAL_FIELD|DOC|EXTERNAL",
                    "ref_type": "SNAPSHOT_KEYPATH|DOC_PAGE|URL",
                    "ref_value": "/credit/loan_summary/overdue_flag 또는 URL",
                    "snippet": "관련 텍스트 스니펫 (100자 이내)"
                }
            ]
        }
    ]
}
```

## 분석 지침
1. 스냅샷 데이터의 변화를 먼저 확인하세요 (연체, 등급, 담보 등)
2. 외부 이벤트와 기업/산업의 연관성을 분석하세요
3. 불필요한 시그널을 남발하지 마세요. 실제 의미 있는 변화만 추출하세요.
4. 동일한 사안에 대해 중복 시그널을 생성하지 마세요.
5. 시그널이 없으면 빈 배열을 반환하세요: {"signals": []}
"""

SIGNAL_EXTRACTION_USER_TEMPLATE = """## 분석 대상 기업
- 기업명: {corp_name}
- 법인번호: {corp_reg_no}
- 업종코드: {industry_code} ({industry_name})

## 내부 스냅샷 데이터
{snapshot_json}

## 관련 외부 이벤트
{external_events}

위 정보를 분석하여 리스크 시그널을 JSON 형식으로 추출하세요.
시그널이 없으면 {{"signals": []}}를 반환하세요.
"""


# =============================================================================
# Insight Generation Prompts
# =============================================================================

INSIGHT_GENERATION_PROMPT = """## 경영진 브리핑 요약 생성

다음 기업의 리스크 시그널 분석 결과를 경영진 브리핑 형식으로 요약하세요.

### 기업 정보
- 기업명: {corp_name}
- 업종: {industry_code} ({industry_name})

### 발견된 시그널 ({signal_count}건)
{signals_summary}

### 요약 형식
1. **핵심 요약** (2-3문장)
   - 가장 중요한 리스크/기회 요인 요약
   - 전체적인 리스크 수준 평가

2. **주요 시그널** (우선순위순)
   - 각 시그널의 핵심 내용 1줄 요약

3. **권고 조치사항**
   - 담당자가 검토해야 할 사항
   - 추가 확인이 필요한 영역

### 주의사항
- 단정적 표현 금지 ("~일 것이다", "반드시", "즉시 조치 필요")
- 허용 표현 사용 ("~로 추정됨", "검토 권고", "~가능성 있음")
- 객관적이고 사실에 기반한 요약만 작성
"""


# =============================================================================
# Helper Functions
# =============================================================================

def format_signal_extraction_prompt(
    corp_name: str,
    corp_reg_no: str,
    industry_code: str,
    industry_name: str,
    snapshot_json: str,
    external_events: str,
) -> str:
    """Format the signal extraction user prompt with context data"""
    return SIGNAL_EXTRACTION_USER_TEMPLATE.format(
        corp_name=corp_name,
        corp_reg_no=corp_reg_no or "N/A",
        industry_code=industry_code,
        industry_name=industry_name,
        snapshot_json=snapshot_json,
        external_events=external_events,
    )


def format_insight_prompt(
    corp_name: str,
    industry_code: str,
    industry_name: str,
    signals: list[dict],
) -> str:
    """Format the insight generation prompt"""
    # Format signals summary
    if not signals:
        signals_summary = "발견된 시그널이 없습니다."
    else:
        lines = []
        for i, sig in enumerate(signals, 1):
            line = (
                f"{i}. [{sig.get('signal_type', 'N/A')}] {sig.get('event_type', 'N/A')}\n"
                f"   - 제목: {sig.get('title', 'N/A')}\n"
                f"   - 영향: {sig.get('impact_direction', 'N/A')} / 강도: {sig.get('impact_strength', 'N/A')}\n"
                f"   - 신뢰도: {sig.get('confidence', 'N/A')}"
            )
            lines.append(line)
        signals_summary = "\n".join(lines)

    return INSIGHT_GENERATION_PROMPT.format(
        corp_name=corp_name,
        industry_code=industry_code,
        industry_name=industry_name,
        signal_count=len(signals),
        signals_summary=signals_summary,
    )


# =============================================================================
# Document Extraction Prompts (Vision LLM)
# =============================================================================

DOC_EXTRACTION_SYSTEM = """당신은 금융기관의 문서 분석 전문가입니다.
기업이 제출한 문서 이미지에서 구조화된 정보를 추출합니다.

## 필수 규칙

### 1. 근거 필수
모든 추출 정보는 문서에서 실제로 확인된 내용만 포함합니다.
추정, 보간, 예측은 절대 금지입니다.

### 2. 신뢰도(confidence) 기준
- HIGH: 명확하게 읽을 수 있고 확실한 정보
- MED: 읽을 수 있으나 일부 불확실한 부분 존재
- LOW: 읽기 어렵거나 추정이 필요한 정보

### 3. 금지 행위
- 문서에 없는 정보 생성 금지
- 숫자 추측 금지
- 날짜 보간 금지

## 출력 형식 (JSON)
```json
{
    "doc_type": "<문서 타입>",
    "facts": [
        {
            "fact_type": "<팩트 타입>",
            "field_key": "<필드명>",
            "field_value": "<추출값 (문자열/숫자/객체)>",
            "confidence": "HIGH|MED|LOW",
            "evidence_snippet": "<근거 텍스트 스니펫 (최대 100자)>"
        }
    ]
}
```
"""

# 사업자등록증 추출 프롬프트
EXTRACT_BIZ_REG_PROMPT = """## 문서 타입: 사업자등록증 (BIZ_REG)

이 사업자등록증 이미지에서 다음 정보를 추출하세요:

### 추출 대상 필드
| fact_type | field_key | 설명 |
|-----------|-----------|------|
| BIZ_INFO | biz_no | 사업자등록번호 (XXX-XX-XXXXX) |
| BIZ_INFO | corp_name | 상호(법인명) |
| BIZ_INFO | ceo_name | 대표자 성명 |
| BIZ_INFO | corp_reg_no | 법인등록번호 (있는 경우) |
| BIZ_INFO | biz_address | 사업장 소재지 |
| BIZ_INFO | head_office_address | 본점 소재지 (있는 경우) |
| BIZ_INFO | biz_type | 업태 |
| BIZ_INFO | biz_item | 종목 |
| BIZ_INFO | open_date | 개업연월일 (YYYY-MM-DD) |
| BIZ_INFO | issue_date | 발급일자 (YYYY-MM-DD) |
| BIZ_INFO | tax_office | 관할세무서 |

### 주의사항
- 사업자등록번호는 반드시 XXX-XX-XXXXX 형식으로 추출
- 날짜는 YYYY-MM-DD 형식으로 변환
- 읽을 수 없는 필드는 생략

문서에서 읽을 수 있는 정보만 JSON 형식으로 추출하세요.
"""

# 법인 등기부등본 추출 프롬프트
EXTRACT_REGISTRY_PROMPT = """## 문서 타입: 법인 등기부등본 (REGISTRY)

이 법인 등기부등본 이미지에서 다음 정보를 추출하세요:

### 추출 대상 필드
| fact_type | field_key | 설명 |
|-----------|-----------|------|
| CORP_INFO | corp_reg_no | 법인등록번호 |
| CORP_INFO | corp_name | 상호 |
| CORP_INFO | head_office | 본점 소재지 |
| CORP_INFO | establishment_date | 설립연월일 |
| CORP_INFO | purpose | 목적 (사업목적) |
| CAPITAL | total_capital | 자본금 총액 (숫자) |
| CAPITAL | issued_shares | 발행주식 총수 (숫자) |
| CAPITAL | par_value | 1주의 금액 (숫자) |
| OFFICER | ceo_name | 대표이사 성명 |
| OFFICER | ceo_address | 대표이사 주소 |
| OFFICER | directors | 이사 목록 (JSON 배열) |
| OFFICER | auditors | 감사 목록 (JSON 배열) |

### 임원 목록 형식
```json
{
    "field_value": [
        {"name": "홍길동", "position": "이사", "reg_date": "2024-01-15"},
        {"name": "김철수", "position": "감사", "reg_date": "2024-01-15"}
    ]
}
```

### 주의사항
- 금액은 숫자만 추출 (단위 제외)
- 날짜는 YYYY-MM-DD 형식
- 등기사항 중 말소된 항목은 제외

문서에서 읽을 수 있는 정보만 JSON 형식으로 추출하세요.
"""

# 주주명부 추출 프롬프트
EXTRACT_SHAREHOLDERS_PROMPT = """## 문서 타입: 주주명부 (SHAREHOLDERS)

이 주주명부 이미지에서 다음 정보를 추출하세요:

### 추출 대상 필드
| fact_type | field_key | 설명 |
|-----------|-----------|------|
| SUMMARY | total_shares | 발행주식 총수 |
| SUMMARY | total_shareholders | 주주 수 |
| SUMMARY | record_date | 기준일 |
| SHAREHOLDER | shareholders | 주주 목록 (JSON 배열) |

### 주주 목록 형식
```json
{
    "field_value": [
        {
            "name": "홍길동",
            "shares": 50000,
            "share_ratio": 50.0,
            "share_type": "보통주"
        },
        {
            "name": "(주)ABC홀딩스",
            "shares": 30000,
            "share_ratio": 30.0,
            "share_type": "보통주"
        }
    ]
}
```

### 주의사항
- 지분율은 소수점 1자리까지
- 주식 수는 정수
- 법인주주는 법인명 그대로 추출

문서에서 읽을 수 있는 정보만 JSON 형식으로 추출하세요.
"""

# 정관 추출 프롬프트
EXTRACT_AOI_PROMPT = """## 문서 타입: 정관 (AOI - Articles of Incorporation)

이 정관 이미지에서 다음 정보를 추출하세요:

### 추출 대상 필드
| fact_type | field_key | 설명 |
|-----------|-----------|------|
| GENERAL | corp_name | 상호 |
| GENERAL | purpose | 목적/사업목적 |
| GENERAL | head_office | 본점 소재지 |
| CAPITAL | authorized_shares | 발행할 주식 총수 |
| CAPITAL | par_value | 1주의 금액 |
| GOVERNANCE | board_size | 이사 정수 |
| GOVERNANCE | auditor_required | 감사 설치 여부 |
| GOVERNANCE | fiscal_year_end | 사업연도 종료일 |
| SPECIAL | special_clauses | 특별 조항 (JSON 배열) |

### 특별 조항 예시
- 주식양도제한
- 의결권 제한
- 신주인수권 관련 조항

### 주의사항
- 정관 전문을 읽을 필요 없음
- 핵심 조항만 추출
- 개정 이력이 있으면 최신 내용 기준

문서에서 읽을 수 있는 정보만 JSON 형식으로 추출하세요.
"""

# 재무제표 추출 프롬프트
EXTRACT_FIN_STATEMENT_PROMPT = """## 문서 타입: 재무제표 요약 (FIN_STATEMENT)

이 재무제표 이미지에서 다음 정보를 추출하세요:

### 추출 대상 필드 (금액 단위: 원)
| fact_type | field_key | 설명 |
|-----------|-----------|------|
| PERIOD | fiscal_year | 사업연도 (예: 2024) |
| PERIOD | period_start | 기초일 (YYYY-MM-DD) |
| PERIOD | period_end | 기말일 (YYYY-MM-DD) |
| BS | total_assets | 자산총계 |
| BS | total_liabilities | 부채총계 |
| BS | total_equity | 자본총계 |
| BS | current_assets | 유동자산 |
| BS | non_current_assets | 비유동자산 |
| BS | current_liabilities | 유동부채 |
| BS | non_current_liabilities | 비유동부채 |
| IS | revenue | 매출액 |
| IS | operating_income | 영업이익 |
| IS | net_income | 당기순이익 |
| IS | ebitda | EBITDA (있는 경우) |
| RATIO | debt_ratio | 부채비율 (%) |
| RATIO | current_ratio | 유동비율 (%) |
| RATIO | roe | ROE (%) |

### 주의사항
- 금액은 원 단위 숫자만 (천원, 백만원 단위면 환산)
- 음수는 마이너스 기호 포함
- 전기/당기 구분되어 있으면 당기 기준
- 비율은 소수점 2자리까지

문서에서 읽을 수 있는 정보만 JSON 형식으로 추출하세요.
"""

# 문서 타입별 프롬프트 매핑
DOC_EXTRACTION_PROMPTS = {
    "BIZ_REG": EXTRACT_BIZ_REG_PROMPT,
    "REGISTRY": EXTRACT_REGISTRY_PROMPT,
    "SHAREHOLDERS": EXTRACT_SHAREHOLDERS_PROMPT,
    "AOI": EXTRACT_AOI_PROMPT,
    "FIN_STATEMENT": EXTRACT_FIN_STATEMENT_PROMPT,
}


def get_doc_extraction_prompt(doc_type: str) -> str:
    """Get document extraction prompt by document type"""
    return DOC_EXTRACTION_PROMPTS.get(doc_type, EXTRACT_BIZ_REG_PROMPT)


# Industry code to name mapping
INDUSTRY_CODE_MAP = {
    "C10": "식품제조업",
    "C21": "의약품제조업",
    "C26": "전자부품제조업",
    "C29": "기계장비제조업",
    "D35": "전기업",
    "F41": "건설업",
    "G45": "자동차판매업",
    "G46": "도매업",
    "G47": "소매업",
    "H49": "육상운송업",
    "J58": "출판업",
    "J62": "소프트웨어개발업",
    "K64": "금융업",
    "L68": "부동산업",
    "M70": "경영컨설팅업",
    "N74": "전문서비스업",
}


def get_industry_name(industry_code: str) -> str:
    """Get industry name from code"""
    return INDUSTRY_CODE_MAP.get(industry_code, f"기타 ({industry_code})")
