"""
LLM Prompt Templates
Prompt templates for signal extraction and insight generation
"""

# =============================================================================
# Signal Extraction Prompts
# =============================================================================

SIGNAL_EXTRACTION_SYSTEM = """당신은 한국 금융기관의 기업심사 전문가입니다.
주어진 기업 데이터와 외부 이벤트를 분석하여 리스크(RISK)와 기회(OPPORTUNITY) 시그널을 추출합니다.

# 역할 및 관점
- **RM(Relationship Manager)** 및 **여신심사역**이 참고할 수 있는 시그널 생성
- 금융기관 입장에서 신용도, 여신 리스크, 비즈니스 기회를 평가
- 객관적 사실에 기반한 분석 (추측/예측 금지)

# Signal Type (3종)

## DIRECT (기업 직접 영향)
- 해당 기업에 직접적으로 영향을 미치는 변화
- event_type: KYC_REFRESH, INTERNAL_RISK_GRADE_CHANGE, OVERDUE_FLAG_ON, LOAN_EXPOSURE_CHANGE, COLLATERAL_CHANGE, OWNERSHIP_CHANGE, GOVERNANCE_CHANGE, FINANCIAL_STATEMENT_UPDATE

## INDUSTRY (산업 영향)
- 해당 산업 전체에 영향을 미치는 변화
- event_type: INDUSTRY_SHOCK만 사용
- 해당 기업에 미치는 구체적 영향을 summary에 명시

## ENVIRONMENT (거시환경 영향)
- 정책, 규제, 거시경제 변화
- event_type: POLICY_REGULATION_CHANGE만 사용
- 해당 기업/산업에 미치는 구체적 영향을 summary에 명시

# Impact Direction

## RISK (부정적)
- 신용도 하락, 상환능력 저하, 담보가치 하락 요인
- 예: 연체 발생, 실적 악화, 규제 강화, 시장 축소

## OPPORTUNITY (긍정적)
- 신용도 향상, 여신 확대 기회, 비즈니스 성장 요인
- 예: 대형 계약 수주, 실적 개선, 정책 수혜, 기술 혁신

## NEUTRAL (중립)
- 모니터링 필요하나 즉각적 영향 불명확
- 예: 경영진 교체 (긍정/부정 미확정)

# 금지 표현 (자동 검증으로 실패 처리됨)
❌ "반드시", "즉시", "확실히", "~할 것이다", "예상됨", "전망됨"
✅ "~로 추정됨", "~가능성 있음", "검토 권고", "~로 보도됨"

# Confidence 기준
- **HIGH**: 공시(DART), 정부 발표, 내부 데이터 기반
- **MED**: 주요 경제지, 신뢰할 수 있는 뉴스 기반
- **LOW**: 단일 출처, 추정 필요한 경우

# 출력 형식 (JSON)
```json
{
  "signals": [
    {
      "signal_type": "DIRECT|INDUSTRY|ENVIRONMENT",
      "event_type": "<10종 중 하나>",
      "impact_direction": "RISK|OPPORTUNITY|NEUTRAL",
      "impact_strength": "HIGH|MED|LOW",
      "confidence": "HIGH|MED|LOW",
      "title": "시그널 제목 (50자 이내)",
      "summary": "상세 설명 (200자 이내, 금지표현 미사용)",
      "evidence": [
        {
          "evidence_type": "INTERNAL_FIELD|DOC|EXTERNAL",
          "ref_type": "SNAPSHOT_KEYPATH|DOC_PAGE|URL",
          "ref_value": "/credit/loan_summary/overdue_flag 또는 URL",
          "snippet": "관련 텍스트 (100자 이내)"
        }
      ]
    }
  ]
}
```

# 분석 지침
1. **내부 스냅샷 먼저**: 연체, 등급, 담보 등 변화 확인
2. **외부 이벤트 연결**: 기업/산업과의 연관성 분석
3. **중복 금지**: 동일 사안 여러 시그널 생성 금지
4. **근거 필수**: evidence 없는 시그널 생성 금지
"""

SIGNAL_EXTRACTION_USER_TEMPLATE = """# 분석 대상 기업
- 기업명: {corp_name}
- 법인번호: {corp_reg_no}
- 업종: {industry_code} ({industry_name})

# 내부 스냅샷 데이터 (Internal Data)
{snapshot_json}

# 외부 이벤트 (External Events)

## 1. 기업 직접 관련 (→ DIRECT 시그널)
{direct_events}

## 2. 산업 전반 (→ INDUSTRY 시그널, event_type: INDUSTRY_SHOCK)
{industry_events}

## 3. 정책/규제/거시환경 (→ ENVIRONMENT 시그널, event_type: POLICY_REGULATION_CHANGE)
{environment_events}

# 시그널 추출 지침

## DIRECT 시그널
- 내부 스냅샷 + 기업 직접 이벤트 분석
- **중요**: 내부 재무 데이터에서 **'적자 전환', '영업이익 급감', '부채비율 급증', '자본잠식'** 등 부정적 변화가 확인되면 반드시 RISK 시그널로 추출 (Confidence: HIGH)
- 내부 데이터 변화는 높은 confidence로 처리

## INDUSTRY 시그널
- 산업 이벤트가 있으면 **반드시** INDUSTRY 시그널 생성
- summary에 "{corp_name}에 미치는 영향" 명시

## ENVIRONMENT 시그널
- 정책/규제 이벤트가 있으면 **반드시** ENVIRONMENT 시그널 생성
- summary에 "{corp_name}/{industry_name}에 미치는 영향" 명시

# 출력 요구사항
- RISK와 OPPORTUNITY를 균형있게 탐지
- title은 반드시 50자 이내
- summary는 반드시 200자 이내
- evidence 없는 시그널 금지
- 시그널이 없으면 {{"signals": []}} 반환
"""


# =============================================================================
# Insight Generation Prompts
# =============================================================================

INSIGHT_GENERATION_PROMPT = """## 경영진 브리핑 요약 생성

다음 기업의 시그널 분석 결과를 경영진 브리핑 형식으로 요약하세요.
**리스크와 기회 요인을 균형있게 다루어야 합니다.**

### 기업 정보
- 기업명: {corp_name}
- 업종: {industry_code} ({industry_name})

### 발견된 시그널 ({signal_count}건)
{signals_summary}

### 요약 형식
1. **핵심 요약** (2-3문장)
   - 가장 중요한 리스크와 기회 요인을 균형있게 요약
   - 전체적인 신용 상태 평가 (리스크뿐 아니라 성장 잠재력도 포함)

2. **기회 요인** (OPPORTUNITY 시그널이 있는 경우 우선 작성)
   - 실적 개선, 성장 투자, 기술 혁신 등 긍정적 요인
   - 금융기관 관점에서의 비즈니스 기회 (여신 확대, 신규 상품 등)

3. **리스크 요인** (RISK 시그널이 있는 경우)
   - 각 리스크 시그널의 핵심 내용 1줄 요약
   - 모니터링이 필요한 영역

4. **권고 조치사항**
   - 기회 활용을 위한 검토 사항 (OPPORTUNITY 관련)
   - 리스크 관리를 위한 검토 사항 (RISK 관련)
   - 추가 확인이 필요한 영역

### 주의사항
- 단정적 표현 금지 ("~일 것이다", "반드시", "즉시 조치 필요")
- 허용 표현 사용 ("~로 추정됨", "검토 권고", "~가능성 있음")
- 객관적이고 사실에 기반한 요약만 작성
- **기회 요인도 리스크만큼 중요하게 다루세요**
"""


# =============================================================================
# Helper Functions
# =============================================================================

import re
import logging

_prompt_logger = logging.getLogger(__name__)

# P0-005 fix: 프롬프트 인젝션 방어를 위한 위험 패턴
DANGEROUS_PATTERNS = [
    # 시스템 명령 우회 시도
    r'(?i)\b(ignore|forget|disregard)\s+(all\s+)?(previous|above|prior)',
    r'(?i)\b(new\s+)?(system|instructions?|rules?)\s*:',
    r'(?i)\byou\s+are\s+(now|a)\b',
    r'(?i)\bpretend\s+(to\s+be|you\s+are)\b',
    r'(?i)\bact\s+as\s+(if|a)\b',
    r'(?i)\brole\s*:\s*',
    # JSON 조작 시도
    r'(?i)"\s*:\s*"[^"]*ignore',
    r'(?i)```\s*(python|javascript|bash|sh|cmd)',
    # 출력 조작 시도
    r'(?i)\balways\s+(output|return|respond)',
    r'(?i)\b(high|critical)\s+risk\s+regardless',
    r'(?i)\bconfidence\s*:\s*["\']?high',
]

COMPILED_PATTERNS = [re.compile(p) for p in DANGEROUS_PATTERNS]


def sanitize_input(text: str, field_name: str = "input", max_length: int = 10000) -> str:
    """
    Sanitize user input to prevent prompt injection attacks.

    P0-005 fix: 프롬프트 인젝션 방어

    Args:
        text: Input text to sanitize
        field_name: Name of the field for logging
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Convert to string and strip
    text = str(text).strip()

    # Truncate if too long
    if len(text) > max_length:
        _prompt_logger.warning(
            f"[Sanitize] {field_name} truncated from {len(text)} to {max_length} chars"
        )
        text = text[:max_length]

    # Check for dangerous patterns
    for i, pattern in enumerate(COMPILED_PATTERNS):
        if pattern.search(text):
            _prompt_logger.warning(
                f"[Sanitize] Suspicious pattern detected in {field_name}: pattern #{i}"
            )
            # Replace the matched pattern with [REDACTED]
            text = pattern.sub('[REDACTED]', text)

    return text


def sanitize_json_string(json_str: str, field_name: str = "json") -> str:
    """
    Sanitize JSON string for prompt injection.

    P0-005 fix: JSON 데이터 내 인젝션 방어

    Args:
        json_str: JSON string to sanitize
        field_name: Name of the field for logging

    Returns:
        Sanitized JSON string
    """
    if not json_str:
        return "{}"

    # Limit total length
    max_json_length = 50000
    if len(json_str) > max_json_length:
        _prompt_logger.warning(
            f"[Sanitize] {field_name} JSON truncated from {len(json_str)} to {max_json_length} chars"
        )
        # Try to truncate at a reasonable point
        json_str = json_str[:max_json_length]
        # Find last complete object/array
        last_brace = max(json_str.rfind('}'), json_str.rfind(']'))
        if last_brace > 0:
            json_str = json_str[:last_brace + 1]

    # Check for dangerous patterns in JSON
    for i, pattern in enumerate(COMPILED_PATTERNS):
        if pattern.search(json_str):
            _prompt_logger.warning(
                f"[Sanitize] Suspicious pattern in {field_name} JSON: pattern #{i}"
            )
            # For JSON, we log but don't modify (might break structure)
            # The validation happens at signal output level

    return json_str


def format_signal_extraction_prompt(
    corp_name: str,
    corp_reg_no: str,
    industry_code: str,
    industry_name: str,
    snapshot_json: str,
    external_events: str,
    direct_events: str = None,
    industry_events: str = None,
    environment_events: str = None,
) -> str:
    """
    Format the signal extraction user prompt with context data.

    P0-005 fix: 모든 입력값 sanitization 적용

    Args:
        corp_name: Corporation name
        corp_reg_no: Corporation registration number
        industry_code: Industry code (e.g., C26)
        industry_name: Industry name
        snapshot_json: Internal snapshot JSON string
        external_events: All external events (for backward compatibility)
        direct_events: Company-specific events (3-track search)
        industry_events: Industry-wide events (3-track search)
        environment_events: Policy/regulation events (3-track search)
    """
    # Sanitize all inputs
    safe_corp_name = sanitize_input(corp_name, "corp_name", max_length=200)
    safe_corp_reg_no = sanitize_input(corp_reg_no, "corp_reg_no", max_length=50)
    safe_industry_code = sanitize_input(industry_code, "industry_code", max_length=20)
    safe_industry_name = sanitize_input(industry_name, "industry_name", max_length=100)
    safe_snapshot = sanitize_json_string(snapshot_json, "snapshot_json")

    # Handle 3-track events (new) vs combined events (legacy)
    if direct_events is not None or industry_events is not None or environment_events is not None:
        # New 3-track format
        safe_direct = sanitize_json_string(direct_events or "[]", "direct_events")
        safe_industry = sanitize_json_string(industry_events or "[]", "industry_events")
        safe_environment = sanitize_json_string(environment_events or "[]", "environment_events")
    else:
        # Legacy format - use external_events for all categories
        safe_events = sanitize_json_string(external_events, "external_events")
        safe_direct = safe_events
        safe_industry = "[]"
        safe_environment = "[]"

    return SIGNAL_EXTRACTION_USER_TEMPLATE.format(
        corp_name=safe_corp_name,
        corp_reg_no=safe_corp_reg_no or "N/A",
        industry_code=safe_industry_code,
        industry_name=safe_industry_name,
        snapshot_json=safe_snapshot,
        direct_events=safe_direct,
        industry_events=safe_industry,
        environment_events=safe_environment,
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
