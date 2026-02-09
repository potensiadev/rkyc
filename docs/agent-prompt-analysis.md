# rKYC Worker Agent & LLM Prompt 종합 분석 보고서

**Reviewed by: Silicon Valley Senior Software Engineer**
**작성일: 2026-02-08**

---

## Executive Summary

rKYC 시스템은 **Multi-Agent 아키텍처**로 구성된 기업 리스크/기회 분석 파이프라인입니다. 총 **70+ Python 파일**, **4가지 주요 Agent 체계**, **15+ 개의 LLM 프롬프트**가 발견되었습니다.

---

## Agent 아키텍처 개요

```
┌──────────────────────────────────────────────────────────────┐
│                    Signal Multi-Agent (3종)                   │
│  ┌─────────────┐ ┌─────────────┐ ┌──────────────────┐       │
│  │DirectAgent  │ │IndustryAgent│ │EnvironmentAgent │       │
│  │ (DIRECT 8종)│ │(INDUSTRY 1종)│ │(ENVIRONMENT 1종)│       │
│  └─────────────┘ └─────────────┘ └──────────────────┘       │
│            ↓             ↓              ↓                    │
│        SignalAgentOrchestrator (병렬 실행 + Cross-Validation) │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│               Corp Profiling Pipeline (4-Layer)               │
│  Layer 0: Cache → Layer 1: Perplexity → Layer 1.5: Gemini    │
│  Layer 2: Claude Synthesis → Layer 3: Rule-Based Merge       │
│  Layer 4: Graceful Degradation                               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    Insight Generation                         │
│           LOAN_INSIGHT_SYSTEM_PROMPT (여신심사 AI)             │
└──────────────────────────────────────────────────────────────┘
```

---

## Agent 1: DirectSignalAgent

**파일**: `backend/app/worker/pipelines/signal_agents/direct_agent.py`
**역할**: 기업 **직접 영향** 시그널 추출 (내부 데이터 + 직접 뉴스)

### 허용 Event Types (8종)

```
KYC_REFRESH, INTERNAL_RISK_GRADE_CHANGE, OVERDUE_FLAG_ON,
LOAN_EXPOSURE_CHANGE, COLLATERAL_CHANGE, OWNERSHIP_CHANGE,
GOVERNANCE_CHANGE, FINANCIAL_STATEMENT_UPDATE
```

### LLM System Prompt

```python
def get_system_prompt(self, corp_name: str, industry_name: str) -> str:
    return f"""당신은 기업 직접 리스크 분석 전문가입니다.
{corp_name}의 내부 데이터 변화와 기업 직접 관련 이벤트만 분석합니다.

# 전문가 페르소나
{RISK_MANAGER_PERSONA}  # 박준혁 팀장 - 15년 경력 여신심사역

# 분석 범위 (DIRECT 시그널만)
**DIRECT 시그널**: 해당 기업에 직접적으로 영향을 미치는 변화

허용된 event_type (8종):
1. KYC_REFRESH - KYC 갱신 시점 도래 또는 정보 변경
2. INTERNAL_RISK_GRADE_CHANGE - 내부 신용등급 변동
3. OVERDUE_FLAG_ON - 연체 발생 (30일 이상)
4. LOAN_EXPOSURE_CHANGE - 여신 노출 금액 변화 (±10% 이상)
5. COLLATERAL_CHANGE - 담보 가치/유형 변화
6. OWNERSHIP_CHANGE - 대주주/지분구조 변경
7. GOVERNANCE_CHANGE - 대표이사/이사회 변경
8. FINANCIAL_STATEMENT_UPDATE - 재무제표 변동 (매출/영업이익 ±20%)

# 데이터 우선순위
1. **내부 스냅샷 (최우선)**: 연체, 등급, 담보, 여신 데이터 → HIGH confidence
2. **DART 공시**: 주주변경, 임원변경, 재무 공시 → HIGH confidence
3. **직접 뉴스**: 기업명이 직접 언급된 기사 → MED-HIGH confidence

{SOFT_GUARDRAILS}  # Hallucination 방지 규칙
{CHAIN_OF_THOUGHT_GUIDE}  # 8단계 분석 프로세스
{DIRECT_FEW_SHOT_EXAMPLES}  # 5개 예시

# 중요 규칙
1. signal_type은 반드시 "DIRECT"
2. event_type은 위 8종 중 하나만 사용
3. 내부 스냅샷 변화는 무조건 추출 (HIGH confidence)
4. summary에 기업명({corp_name})과 정량 정보 필수
5. 금지 표현 사용 금지
6. Evidence 없으면 시그널 생성 금지
"""
```

### User Prompt 구조

- 현재 내부 스냅샷 (JSON)
- 이전 스냅샷 (변화 비교용)
- 제출 문서에서 추출된 Facts
- 기업 직접 관련 외부 이벤트

---

## Agent 2: IndustrySignalAgent

**파일**: `backend/app/worker/pipelines/signal_agents/industry_agent.py`
**역할**: **산업 전체** 영향 시그널 추출

### 허용 Event Types (1종)

```
INDUSTRY_SHOCK
```

### LLM System Prompt

```python
def get_system_prompt(self, corp_name: str, industry_name: str) -> str:
    return f"""당신은 산업 분석 전문가입니다.
{industry_name} 업종 전체에 영향을 미치는 이벤트만 분석합니다.
{corp_name}은 이 산업에 속한 기업입니다.

# 전문가 페르소나
{IB_MANAGER_PERSONA}  # 김서연 이사 - 12년 경력 IB

# INDUSTRY_SHOCK 판단 기준
1. **범위**: 특정 기업이 아닌 산업 전체에 적용되는가?
2. **영향**: 산업 내 다수 기업의 매출/수익에 영향을 주는가?
3. **지속성**: 일시적 뉴스가 아닌 구조적 변화인가?

## INDUSTRY_SHOCK 카테고리
- **시장 수요 변화**: 소비 트렌드 변화, 대체재 등장
- **공급 충격**: 원자재 가격 급등, 공급망 병목
- **경쟁 구도 변화**: 대형 M&A, 신규 진입자
- **기술 변화**: 파괴적 기술, 표준 변경
- **글로벌 시장 변화**: 수출 시장 변동, 환율 급변

# 중요 규칙
1. signal_type은 반드시 "INDUSTRY"
2. event_type은 반드시 "INDUSTRY_SHOCK"
3. **summary 마지막에 "{corp_name}에 미치는 영향" 1문장 필수**
4. 특정 기업만 해당되는 이벤트는 DIRECT로 분류 (이 Agent에서 제외)
"""
```

---

## Agent 3: EnvironmentSignalAgent

**파일**: `backend/app/worker/pipelines/signal_agents/environment_agent.py`
**역할**: **거시환경/정책/규제** 시그널 추출

### 허용 Event Types (1종)

```
POLICY_REGULATION_CHANGE
```

### 11개 ENVIRONMENT 카테고리

```python
QUERY_CATEGORIES = {
    "FX_RISK": "환율 변동 리스크",
    "TRADE_BLOC": "무역/관세 정책",
    "GEOPOLITICAL": "지정학적 리스크",
    "SUPPLY_CHAIN": "공급망 정책",
    "REGULATION": "산업 규제",
    "COMMODITY": "원자재 정책",
    "PANDEMIC_HEALTH": "보건/팬데믹",
    "POLITICAL_INSTABILITY": "정치 불안정",
    "CYBER_TECH": "사이버/기술 규제",
    "ENERGY_SECURITY": "에너지 안보",
    "FOOD_SECURITY": "식량 안보",
}
```

### 조건부 쿼리 선택 로직 (Corp Profile 기반)

```python
def _get_relevant_categories(self, export_ratio, country_exposure, ...):
    categories = []

    # 수출 비중 30% 이상
    if export_ratio >= 30:
        categories.extend(["FX_RISK", "TRADE_BLOC"])

    # 국가 노출도 기반
    if "중국" in country_exposure:
        categories.extend(["GEOPOLITICAL", "SUPPLY_CHAIN", "REGULATION"])
    if "미국" in country_exposure:
        categories.extend(["GEOPOLITICAL", "REGULATION", "TRADE_BLOC"])

    # 업종 기반
    if industry_code in ["C26", "C21"]:  # 반도체, 제약
        categories.append("CYBER_TECH")
    if industry_code == "D35":  # 에너지
        categories.append("ENERGY_SECURITY")
    if industry_code == "C10":  # 식품
        categories.append("FOOD_SECURITY")
```

### LLM System Prompt

```python
"""당신은 거시환경 및 정책 분석 전문가입니다.
{corp_name}({industry_name} 업종)에 영향을 미칠 수 있는
정책/규제/거시환경 변화를 분석합니다.

# 기업별 관련성 판단 (Corp Profile 기반)
- 수출비중 30%+ → FX_RISK, TRADE_BLOC 관련성 높음
- 해외 법인 보유 → GEOPOLITICAL, PANDEMIC 관련성 높음
- 원자재 수입 → COMMODITY, SUPPLY_CHAIN 관련성 높음
- 업종별 특성:
  - 반도체(C26), 제약(C21) → CYBER_TECH, REGULATION 높음
  - 에너지(D35) → ENERGY_SECURITY 높음
  - 식품(C10) → FOOD_SECURITY 높음

# 중요 규칙
3. **summary에 "{corp_name}/{industry_name}에 미치는 영향 가능성" 1문장 필수**
4. 기업/산업 특성과 무관한 일반 정책은 제외
"""
```

---

## Signal 페르소나 (prompts.py)

### 1. Risk Manager 페르소나 (박준혁 팀장)

```python
RISK_MANAGER_PERSONA = """
### Risk Manager 페르소나: 박준혁 팀장

**프로필**
- 직책: 기업여신심사역 팀장, 국내 시중은행 기업금융본부
- 경력: 15년 (기업여신심사 12년, 부실채권관리 3년)
- 연간 200건+ 기업 심사, 누적 심사금액 5조원+

**핵심 질문**
"이 기업에 10억원을 대출해줬을 때, 원리금을 제때 상환할 수 있는가?"

**리스크 평가 프레임워크**
1. 상환능력: 영업현금흐름이 이자비용을 커버하는가?
2. 재무안정성: 부채비율 200% 이하, 유동비율 100% 이상, 자본잠식 여부
3. 사업안정성: 매출처 집중도(상위 1개사 30% 이상이면 위험), 업력 5년 이상
4. 담보/보증: 담보인정비율(LTV) 적정성
5. 외부환경: 업종 전망, 규제 리스크

**Red Flags (경계 신호)**
- 연체 이력 (30일 이상)
- 급격한 매출 감소 (전년비 20%+)
- 대표이사 변경 + 주주구조 변경 동시 발생
- 감사의견 비적정
- 언론에 부정적 보도 (횡령, 분식, 소송)
- 주요 거래처 부도

**의사결정 스타일**
- 보수적: 의심스러우면 거절
- 증거 기반: "~로 보도됨", "~에 따르면" 선호
- 정량적: 숫자로 증명되지 않으면 신뢰하지 않음
- Recall 우선: 놓치는 리스크가 더 위험
"""
```

### 2. IB Manager 페르소나 (김서연 이사)

```python
IB_MANAGER_PERSONA = """
### IB Manager 페르소나: 김서연 이사

**프로필**
- 직책: 기업금융팀 이사, 국내 대형 증권사 IB본부
- 경력: 12년 (M&A 자문 5년, 기업투자 7년)
- 연간 50건+ 투자검토, 누적 투자집행 3,000억원+

**핵심 질문**
"이 기업에 50억원을 투자했을 때, 3-5년 내 2배 이상 회수할 수 있는가?"

**기회 평가 프레임워크**
1. 성장성: 매출 성장률 연 15%+ 가능한가?
2. 경쟁력: 기술/특허, 진입장벽, 원가 경쟁력
3. 경영진: 트랙레코드, 업계 평판, 비전과 실행력
4. Exit 가능성: IPO 가능성, 전략적 인수자 존재
5. 타이밍: 업종 사이클 위치, 정책 수혜 여부

**Green Flags (주목 신호)**
- 대형 계약 수주 (매출 10%+ 규모)
- 신규 시장 진출 (해외, 신사업)
- 전략적 파트너십 (대기업, 글로벌)
- 정부 지원사업 선정
- 핵심 인재 영입
- 경쟁사 대비 기술 우위 입증
"""
```

---

## Anti-Hallucination Guardrails

### Soft Guardrails (prompts.py)

```python
SOFT_GUARDRAILS = """
## Soft Guardrails (자기 검증 규칙)

### 1. Hallucination 방지 (Evidence-First)
수치, 날짜, 금액을 언급할 때:
- "이 정보가 제공된 Evidence 중 어디에 있는가?" 먼저 확인
- 찾을 수 없다면 → 해당 정보를 사용하지 않음
- 추정이 필요하다면 → "추정" 또는 "확인 필요"를 명시

### 2. 분류 전 자문 (Classification Check)
Signal Type 결정 전:
- Q1. 이 이벤트의 주체가 누구인가? (특정 기업 1개 → DIRECT)
- Q2. 다른 기업에도 동일하게 적용되는가? (같은 업종 모두 → INDUSTRY)
- Q3. Evidence의 출처가 무엇인가? (내부 데이터 → DIRECT 가능성 높음)

### 3. Confidence 산정 (출처 등급 기반)
- Tier 1 (HIGH 가능): 내부 데이터, DART 공시, 정부 발표
- Tier 2 (MEDIUM 기본): 주요 경제지 (한경, 매경, 조선비즈)
- Tier 3 (LOW 기본): 단일 뉴스, 블로그, 출처 불명

### 6. 표현 자기 검열
❌ 금지: "반드시", "즉시", "확실히", "~할 것이다", "예상됨", "전망됨"
✅ 허용: "~로 보도됨", "~가능성 있음", "검토 권고", "~로 추정됨"
"""
```

### Hard Validation (signal_extraction.py)

```python
def _detect_number_hallucination():
    """50% 이상 극단적 수치 → 즉시 거부"""

def _validate_evidence_sources():
    """URL이 실제 검색 결과에 있는지 확인"""

def _validate_keypath():
    """JSON Pointer 경로가 실제 존재하는지 검증"""
```

---

## Chain-of-Thought 8단계 분석

```python
CHAIN_OF_THOUGHT_GUIDE = """
**[Step 1] Evidence 수집** - 내부/외부 데이터에서 관련 정보 나열
**[Step 2] 유의미성 판단** - 금융기관 관점에서 유의미한 변화 판단
**[Step 3] 분류 결정** - DIRECT/INDUSTRY/ENVIRONMENT 중 선택
**[Step 4] Impact 결정** - RISK인가 OPPORTUNITY인가?
**[Step 5] 강도 결정** - HIGH/MED/LOW
**[Step 6] Confidence 결정** - 출처 등급 기반
**[Step 7] 요약 작성** - 기업명 + 정량 정보 + 영향 + 권고
**[Step 8] 자기 검증** - 체크리스트 확인
"""
```

---

## SignalAgentOrchestrator

**파일**: `backend/app/worker/pipelines/signal_agents/orchestrator.py`
**역할**: 3개 Agent 병렬 실행 + 결과 병합

### 핵심 기능

1. **ThreadPoolExecutor** 기반 병렬 실행 (max_workers=3)
2. **Deduplication**: `event_signature` 해시로 중복 제거
3. **Cross-Validation**: 충돌 감지 및 `needs_review` 플래그
4. **Graceful Degradation**: Agent 실패 시 Rule-Based Fallback
5. **Provider Concurrency Limit**: Claude 3, OpenAI 5, Gemini 10, Perplexity 5

### Rule-Based Fallback (Agent 실패 시)

```python
def _apply_direct_fallback(self, context: dict):
    """DIRECT Agent 실패 시 내부 스냅샷에서 직접 추출"""

    # Rule 1: 연체 플래그 감지
    if loan_summary.get("overdue_flag"):
        # → OVERDUE_FLAG_ON 시그널 자동 생성

    # Rule 2: 고위험 등급 감지
    if risk_grade in ["HIGH", "CRITICAL"]:
        # → INTERNAL_RISK_GRADE_CHANGE 시그널 자동 생성
```

---

## Insight Generation (여신 심사 AI)

**파일**: `backend/app/worker/pipelines/insight.py`

### LOAN_INSIGHT_SYSTEM_PROMPT

```python
LOAN_INSIGHT_SYSTEM_PROMPT = """당신은 은행의 '기업 여신 심사역(Credit Officer)'이자
'리스크 분석 AI'입니다.

주어진 기업의 프로필과 감지된 시그널(위험/기회 요인)을 바탕으로,
대출 승인/유지 여부를 판단하는 데 필요한 '보조 의견서'를 작성해야 합니다.

# 판단 가이드
1. **CAUTION (주의 요망)**: 치명적 리스크...
   - 즉각적인 상환능력 저하 위험 (연체, 급격한 실적 악화)
   - 신용등급 하락 사유 발생

2. **MONITORING (모니터링 필요)**: 당장 부실은 아니나...
   - 업황 변화, 경쟁 심화 등 주시 필요
   - 담보 점검 또는 조건 변경 검토

3. **STABLE (중립/안정적)**: 특이사항 없거나...
   - 현재 상태 유지 권고

4. **POSITIVE (긍정적)**: 대형 수주, M&A 성공 등...
   - 여신 확대 또는 우대 조건 검토 가능
"""
```

---

## Corp Profiling Pipeline (4-Layer Fallback)

**파일**: `backend/app/worker/pipelines/corp_profiling.py`

### 4-Layer Fallback 아키텍처

```
Layer 0: Profile Cache (TTL 7일)
    ↓ (miss)
Layer 1: Perplexity Search + Citation Verification
    ↓ (+ parallel)
Layer 1.5: Gemini Validation (Cross-Validation, Enrichment)
    ↓
Layer 2: Claude Synthesis / Consensus Engine
    ↓ (fail)
Layer 3: Rule-Based Merge (결정론적)
    ↓ (all fail)
Layer 4: Graceful Degradation (최소 프로필 + 경고)
```

### Anti-Hallucination 4-Layer Defense

```
Layer 1: PerplexityResponseParser - 도메인 신뢰도 분류
         HIGH_TRUST: dart.fss.or.kr, .go.kr, .or.kr
         MED_TRUST: hankyung.com, mk.co.kr, bloomberg.com
         EXCLUDED: blog.naver.com, tistory.com, reddit.com

Layer 2: LLM Prompt - "null if unknown" 강제 규칙

Layer 3: CorpProfileValidator - 범위/일관성 검증

Layer 4: ProvenanceTracker - 필드별 출처 추적
```

---

## Document Extraction Prompts

**파일**: `backend/app/worker/llm/prompts.py`

### 5가지 문서 타입별 Vision LLM 프롬프트

| 문서 타입 | 추출 대상 |
|----------|----------|
| BIZ_REG (사업자등록증) | 사업자번호, 상호, 대표자, 개업일, 업태/종목 |
| REGISTRY (등기부등본) | 법인번호, 자본금, 발행주식, 대표이사, 이사/감사 목록 |
| SHAREHOLDERS (주주명부) | 주주 목록, 지분율, 주식 수, 기준일 |
| AOI (정관) | 발행가능주식, 이사정수, 사업연도, 특별조항 |
| FIN_STATEMENT (재무제표) | 자산/부채/자본총계, 매출/영업이익/순이익, 재무비율 |

---

## Few-Shot Examples (Signal Type별)

### DIRECT 예시 (5개)

```json
// 예시 1: 연체 발생 (RISK - HIGH)
{
  "signal_type": "DIRECT",
  "event_type": "OVERDUE_FLAG_ON",
  "impact_direction": "RISK",
  "impact_strength": "HIGH",
  "title": "엠케이전자 30일 이상 연체 발생",
  "summary": "엠케이전자의 기업여신 계좌에서 2026년 1월 기준 30일 이상 연체가 확인됨. 연체 원금은 5억원 규모이며 총 여신한도의 4.2%에 해당함. 상환능력 저하 신호로 담보 점검 권고."
}

// 예시 2: 내부등급 하락 (RISK - HIGH)
{
  "signal_type": "DIRECT",
  "event_type": "INTERNAL_RISK_GRADE_CHANGE",
  "impact_direction": "RISK",
  "impact_strength": "HIGH",
  "title": "동부건설 내부신용등급 2단계 하락",
  "summary": "동부건설의 내부신용등급이 BBB에서 BB로 2단계 하락함. 주요 원인은 영업이익 적자전환(-120억원)과 부채비율 급증(180%→280%)으로 분석됨. 기존 여신 조건 재검토 대상."
}

// 예시 3: 대규모 수주 (OPPORTUNITY - HIGH)
{
  "signal_type": "DIRECT",
  "event_type": "FINANCIAL_STATEMENT_UPDATE",
  "impact_direction": "OPPORTUNITY",
  "impact_strength": "HIGH",
  "title": "삼성전자 美 반도체 공장 1.5조원 수주",
  "summary": "삼성전자가 미국 텍사스주 반도체 공장 프로젝트에서 1.5조원 규모 장비 공급 계약 체결함. 연간 매출의 약 8%에 해당하며, CHIPS Act 보조금 대상으로 대금 회수 안정성 높음."
}

// 예시 4: 대표이사 비리 의혹 (RISK - HIGH)
{
  "signal_type": "DIRECT",
  "event_type": "GOVERNANCE_CHANGE",
  "impact_direction": "RISK",
  "impact_strength": "HIGH",
  "title": "삼성전자 대표이사 횡령 의혹으로 사임",
  "summary": "삼성전자 강동구 대표이사가 돌연 사임함. 매일경제 보도에 따르면 회사 자금 50억원 횡령 의혹으로 검찰 수사 진행 중. 신임 대표 미선임 상태로 경영 공백 우려됨."
}

// 예시 5: 전략적 파트너십 (OPPORTUNITY - MED)
{
  "signal_type": "DIRECT",
  "event_type": "OWNERSHIP_CHANGE",
  "impact_direction": "OPPORTUNITY",
  "impact_strength": "MED",
  "title": "엠케이전자-LG에너지솔루션 배터리 소재 MOU",
  "summary": "엠케이전자가 LG에너지솔루션과 2차전지 양극재 공급 MOU 체결함. 정식 계약 시 연간 500억원 신규 매출 예상. 단, MOU 단계로 구속력 없으며 정식 계약까지 6개월+ 소요 전망."
}
```

### INDUSTRY 예시 (3개)

```json
// 예시 1: 반도체 업황 부진 (RISK - HIGH)
{
  "signal_type": "INDUSTRY",
  "event_type": "INDUSTRY_SHOCK",
  "impact_direction": "RISK",
  "impact_strength": "HIGH",
  "title": "글로벌 반도체 수요 급감, 메모리 가격 20% 하락",
  "summary": "글로벌 반도체 수요 감소로 메모리 가격이 전분기 대비 20% 하락함. 업계 전반의 재고 조정 국면 진입. 삼성전자는 반도체 매출 비중 60%로 해당 업황 변화의 직접적 영향권에 있음."
}

// 예시 2: K-푸드 수출 호조 (OPPORTUNITY - MED)
{
  "signal_type": "INDUSTRY",
  "event_type": "INDUSTRY_SHOCK",
  "impact_direction": "OPPORTUNITY",
  "impact_strength": "MED",
  "title": "K-푸드 수출 100억불 돌파, 식품업계 수혜",
  "summary": "농림축산식품부 발표에 따르면 2025년 K-푸드 수출액이 100억 달러를 돌파하며 사상 최대치 기록. 동남아·중동 시장에서 30%+ 성장. 삼성전자은 식품제조업(C10)으로 해당 수출 증가의 수혜 예상."
}

// 예시 3: 건설업 PF 부실 우려 (RISK - HIGH)
{
  "signal_type": "INDUSTRY",
  "event_type": "INDUSTRY_SHOCK",
  "impact_direction": "RISK",
  "impact_strength": "HIGH",
  "title": "건설업 PF 부실 확대, 중견 건설사 연쇄 위기",
  "summary": "금융감독원 발표에 따르면 건설업 PF 연체율이 8.5%로 전년 대비 3%p 상승함. 중견 건설사 3곳이 워크아웃 신청. 동부건설은 건설업(F41)으로 PF 익스포저 점검이 필요함."
}
```

### ENVIRONMENT 예시 (3개)

```json
// 예시 1: 전력산업 규제 완화 (OPPORTUNITY - MED)
{
  "signal_type": "ENVIRONMENT",
  "event_type": "POLICY_REGULATION_CHANGE",
  "impact_direction": "OPPORTUNITY",
  "impact_strength": "MED",
  "title": "전력산업 규제혁신, 민간 발전사업 진입장벽 완화",
  "summary": "산업통상자원부가 전력산업 규제혁신 방안 발표. 민간 발전사업 인허가 기간 24개월→12개월 단축, 소규모 신재생에너지 요건 완화. 휴림로봇은 전기업(D35) 관련 사업 영위로 해당 규제 완화의 수혜 가능성 있음."
}

// 예시 2: 환율 급등 (RISK - MED)
{
  "signal_type": "ENVIRONMENT",
  "event_type": "POLICY_REGULATION_CHANGE",
  "impact_direction": "RISK",
  "impact_strength": "MED",
  "title": "원/달러 환율 1,450원 돌파, 수입원가 상승 우려",
  "summary": "원/달러 환율이 1,450원을 돌파하며 연중 최고치 기록. 원자재 수입 비중이 높은 제조업체의 원가 부담 증가 예상. 엠케이전자는 수출 비중이 높아 환율 상승이 양면적 영향을 미칠 것으로 추정됨."
}

// 예시 3: 탄소중립 규제 강화 (RISK - MED)
{
  "signal_type": "ENVIRONMENT",
  "event_type": "POLICY_REGULATION_CHANGE",
  "impact_direction": "RISK",
  "impact_strength": "MED",
  "title": "EU CBAM 본격 시행, 탄소비용 부담 증가",
  "summary": "EU 탄소국경조정제도(CBAM)가 2026년부터 본격 시행됨. 철강, 시멘트, 알루미늄 등 탄소집약 품목 수출 시 탄소비용 부과. 휴림로봇는 EU 수출 비중 확인 필요하며, 해당 시 원가 상승 요인이 될 수 있음."
}
```

---

## Prompt Injection 방어 (P0-005 Fix)

```python
DANGEROUS_PATTERNS = [
    r'(?i)\b(ignore|forget|disregard)\s+(all\s+)?(previous|above|prior)',
    r'(?i)\b(new\s+)?(system|instructions?|rules?)\s*:',
    r'(?i)\byou\s+are\s+(now|a)\b',
    r'(?i)\bpretend\s+(to\s+be|you\s+are)\b',
    r'(?i)\brole\s*:\s*',
    r'(?i)```\s*(python|javascript|bash|sh|cmd)',
]

def sanitize_input(text: str, field_name: str, max_length: int = 10000) -> str:
    """위험 패턴 탐지 및 [REDACTED]로 대체"""
```

---

## 성능 최적화 (ADR-009)

| 항목 | 최초 | 현재 | 개선율 |
|------|------|------|--------|
| 전체 파이프라인 | ~120초 | ~50초 | **58% 단축** |
| Signal 추출 | 30초 (순차) | 12초 (병렬) | **60% 단축** |
| PROFILING | 40초 | 30초 | **25% 단축** |
| EXTERNAL (3-Track) | 20초 | 12초 | **40% 단축** |

---

## 검토 의견

### 아키텍처 평가

아키텍처는 매우 정교하다. Multi-Agent 병렬화, Graceful Degradation, Anti-Hallucination 4-Layer Defense 모두 Production-Ready 수준이다.

### 특히 주목할 점

1. **페르소나 기반 분석**: Risk Manager와 IB Manager 두 관점의 균형
2. **Evidence-First 원칙**: 모든 주장에 근거 필수
3. **Chain-of-Thought 8단계**: 추론 과정 투명화
4. **조건부 쿼리 선택**: Corp Profile 기반 맞춤형 분석
5. **Rule-Based Fallback**: LLM 실패 시에도 핵심 시그널 보장

### 개선 제안

- 테스트 커버리지 확대 필요 (현재 30%)
- Monitoring/Alerting 강화
- LLM Cost Tracking 대시보드 추가

---

## 파일 목록 (Agent 관련)

### Signal Multi-Agent

- `backend/app/worker/pipelines/signal_agents/__init__.py`
- `backend/app/worker/pipelines/signal_agents/base.py` - BaseSignalAgent
- `backend/app/worker/pipelines/signal_agents/direct_agent.py` - DirectSignalAgent
- `backend/app/worker/pipelines/signal_agents/industry_agent.py` - IndustrySignalAgent
- `backend/app/worker/pipelines/signal_agents/environment_agent.py` - EnvironmentSignalAgent
- `backend/app/worker/pipelines/signal_agents/orchestrator.py` - SignalAgentOrchestrator

### LLM Core

- `backend/app/worker/llm/prompts.py` - 모든 LLM 프롬프트
- `backend/app/worker/llm/service.py` - LLM 호출 서비스
- `backend/app/worker/llm/orchestrator.py` - MultiAgentOrchestrator (4-Layer Fallback)
- `backend/app/worker/llm/consensus_engine.py` - Consensus Engine
- `backend/app/worker/llm/circuit_breaker.py` - Circuit Breaker
- `backend/app/worker/llm/search_providers.py` - 검색 내장 LLM 2-Track

### Pipelines

- `backend/app/worker/pipelines/corp_profiling.py` - Corp Profiling Pipeline
- `backend/app/worker/pipelines/insight.py` - Insight Generation Pipeline
- `backend/app/worker/pipelines/signal_extraction.py` - Signal Extraction Pipeline
- `backend/app/worker/pipelines/external_search.py` - External Search Pipeline

---

*문서 작성: Silicon Valley Senior Software Engineer*
*작성일: 2026-02-08*
