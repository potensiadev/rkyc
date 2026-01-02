# ADR-008: 보안 아키텍처 - External/Internal LLM 분리

## 상태
**승인됨** (2026-01-02)

## 컨텍스트

### 문제 정의
rKYC 시스템의 현재 아키텍처에서 모든 데이터(내부 KYC 정보, 여신/담보 정보, 외부 뉴스)가 동일한 외부 LLM API(Claude/GPT-4o)로 전송됩니다. 이는 금융 규제 준수 관점에서 다음과 같은 리스크가 있습니다:

| 규제 | 조항 | 이슈 |
|------|------|------|
| 금융위 클라우드 가이드라인 | 3.2 | 중요 정보가 통제 불가능한 환경으로 전송 |
| 개인정보보호법 | 제17조 | 제3자 제공 시 정보주체 동의 필요 |
| 신용정보법 | 제32조 | 신용정보 처리 시 안전성 확보 조치 부재 |
| 전자금융감독규정 | 제14조의2 | 클라우드 이용 시 사전 보고 미이행 |

### 기존 아키텍처 (AS-IS)
```
┌─────────────────────────────────────────────────────────────────┐
│   [은행 내부]                        [외부 클라우드]              │
│   ┌──────────────┐                  ┌──────────────────┐        │
│   │ 법인 KYC 정보 │ ──────────────▶ │ Claude/GPT-4     │        │
│   │ 여신/담보 정보│    ⚠️ 민감정보    │ (외부 API)        │        │
│   │ 거래 내역    │    외부 전송     │                  │        │
│   └──────────────┘                  └──────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

## 결정

### 2-Track LLM 아키텍처 도입

**External LLM**과 **Internal LLM**을 분리하여 데이터 분류에 따라 적절한 LLM을 사용합니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     2-Track LLM Architecture                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ═══════════════════════════════════════════════════════════════════    │
│  ║  Track 1: External LLM (공개 데이터 전용)                        ║    │
│  ═══════════════════════════════════════════════════════════════════    │
│                                                                         │
│   [외부 공개 데이터]                    [External LLM]                   │
│   ┌──────────────────┐                ┌──────────────────┐              │
│   │ 뉴스/기사         │                │ Claude Sonnet 4  │              │
│   │ DART 공시        │ ──────────────▶│ Perplexity       │              │
│   │ 정책/규제        │   ✅ 공개정보    │ GPT-4o           │              │
│   │ 산업 리포트      │   외부 전송 OK  │                  │              │
│   └──────────────────┘                └────────┬─────────┘              │
│                                                │                        │
│                                     ┌──────────▼─────────┐              │
│                                     │ External Intel DB  │              │
│                                     │ (적재 테이블)       │              │
│                                     └──────────┬─────────┘              │
│                                                │                        │
│  ══════════════════════════════════════════════╪════════════════════    │
│  ║  Track 2: Internal LLM (내부 데이터 전용)   ║                    ║    │
│  ══════════════════════════════════════════════╪════════════════════    │
│                                                │                        │
│   [은행 내부 데이터]                           ▼                        │
│   ┌──────────────────┐         ┌──────────────────────────┐             │
│   │ 법인 KYC 정보    │         │     Internal LLM          │             │
│   │ 여신/담보 정보   │ ───────▶│  (MVP: GPT-3.5/Haiku)    │             │
│   │ 거래 내역        │         │  (Phase 2: Azure/Bedrock) │             │
│   │ 내부 신용등급    │         │  (Phase 3: On-Premise)    │             │
│   └──────────────────┘         └──────────────────────────┘             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 데이터 분류 기준

| 분류 | 데이터 종류 | 처리 LLM | 근거 |
|------|------------|----------|------|
| **PUBLIC** | 뉴스, DART 공시, 정책/규제, 산업 리포트 | External LLM | 이미 공개된 정보 |
| **INTERNAL** | KYC 정보, 여신/담보, 거래 내역, 내부 등급 | Internal LLM | 고객 민감정보 |
| **SEMI_PUBLIC** | 기업 재무제표 (공시 vs 제출본) | 상황별 판단 | 공시 여부에 따라 |

### Internal LLM 로드맵

| Phase | 기간 | 구현 방식 | 모델 |
|-------|------|----------|------|
| **Phase 1: MVP** | 대회 기간 | 외부 API + 인터페이스 추상화 | GPT-3.5, Claude Haiku |
| **Phase 2: Pilot** | 대회 후 3~6개월 | Private Cloud | Azure OpenAI, AWS Bedrock |
| **Phase 3: Production** | 1년 이후 | On-Premise | Llama 3, Solar |

### 인터페이스 설계

```python
class InternalLLMBase(ABC):
    """Internal LLM 추상 인터페이스 - 구현체만 교체하면 됨"""

    @abstractmethod
    def analyze_snapshot(self, snapshot_json: dict) -> dict:
        """내부 Snapshot 분석"""
        pass

    @abstractmethod
    def extract_document_facts(self, image_base64: str, doc_type: str, ...) -> dict:
        """문서 OCR 및 구조화"""
        pass

    @abstractmethod
    def generate_signals(self, internal_context: dict, external_intel: list[dict], ...) -> list[dict]:
        """시그널 생성 (Internal + External 결합)"""
        pass
```

### External Intel 테이블

```sql
-- 외부 뉴스/이벤트 원본
CREATE TABLE rkyc_external_news (
    news_id UUID PRIMARY KEY,
    source_type VARCHAR(20),  -- NEWS, DART, POLICY, REPORT
    title VARCHAR(500),
    content_raw TEXT,
    published_at TIMESTAMPTZ,
    url_hash VARCHAR(64) UNIQUE
);

-- External LLM 분석 결과
CREATE TABLE rkyc_external_analysis (
    analysis_id UUID PRIMARY KEY,
    news_id UUID REFERENCES rkyc_external_news,
    summary_ko TEXT,
    industry_codes VARCHAR(10)[],
    sentiment VARCHAR(20),
    impact_level VARCHAR(10),
    is_signal_candidate BOOLEAN,
    signal_type_hint VARCHAR(20)
);

-- 업종별 인텔리전스 집계
CREATE TABLE rkyc_industry_intel (
    intel_id UUID PRIMARY KEY,
    industry_code VARCHAR(10),
    period_start DATE,
    period_end DATE,
    period_summary TEXT,
    key_events JSONB,
    risk_factors JSONB
);

-- LLM 감사 로그
CREATE TABLE rkyc_llm_audit_log (
    log_id UUID PRIMARY KEY,
    llm_type VARCHAR(20),  -- EXTERNAL, INTERNAL
    data_classification VARCHAR(20),  -- PUBLIC, INTERNAL
    operation_type VARCHAR(50),
    success BOOLEAN,
    created_at TIMESTAMPTZ
);
```

## 결과

### 긍정적 결과

1. **규제 준수**: 민감 데이터가 외부로 전송되지 않음 (Phase 2/3)
2. **보안 강화**: 데이터 분류 기반 접근 제어
3. **감사 추적**: 모든 LLM 호출 로깅
4. **확장성**: 인터페이스 추상화로 Provider 교체 용이
5. **비용 최적화**: Internal은 저비용 모델 사용 가능

### 부정적 결과

1. **복잡성 증가**: 2개 트랙 관리 필요
2. **초기 비용**: Phase 2/3 인프라 구축 비용
3. **개발 지연**: MVP에서는 논리적 분리만 (실제 분리는 Phase 2)

### 보안 체크리스트

| 항목 | MVP | Phase 2 | Phase 3 |
|------|-----|---------|---------|
| 데이터 분류 적용 | ✅ | ✅ | ✅ |
| 가상 데이터 사용 | ✅ | ⚠️ 제한적 실데이터 | ✅ 실데이터 |
| Internal LLM 분리 | ✅ 논리적 | ✅ Private Cloud | ✅ On-Premise |
| 데이터 외부 전송 | ⚠️ MVP만 허용 | ✅ 국내 리전만 | ✅ 내부망만 |
| 감사 로그 | ✅ 기본 | ✅ 상세 | ✅ SIEM 연동 |
| PII 마스킹 | ❌ | ✅ | ✅ |

## 구현된 컴포넌트

### 파일 목록

| 파일 | 설명 |
|------|------|
| `backend/sql/migration_v6_security_architecture.sql` | External Intel 테이블 DDL |
| `backend/app/worker/llm/internal_llm.py` | InternalLLMBase 인터페이스 + MVP 구현 |
| `backend/app/worker/llm/external_llm.py` | ExternalLLMService 구현 |
| `backend/app/models/external_intel.py` | SQLAlchemy 모델 |

### 환경 변수

```bash
# Internal LLM 설정
INTERNAL_LLM_PROVIDER=mvp_openai  # mvp_openai | azure_openai | onprem_llama
INTERNAL_LLM_OPENAI_KEY=sk-...    # MVP용
INTERNAL_LLM_ANTHROPIC_KEY=sk-... # MVP 백업용

# External LLM 설정
EXTERNAL_LLM_ANTHROPIC_KEY=sk-... # External용 (기본 키와 분리 가능)
EXTERNAL_LLM_OPENAI_KEY=sk-...
EXTERNAL_LLM_PERPLEXITY_KEY=pplx-...

# Phase 2 (추후)
# INTERNAL_LLM_AZURE_ENDPOINT=...
# INTERNAL_LLM_AZURE_DEPLOYMENT=...

# Phase 3 (추후)
# INTERNAL_LLM_ONPREM_ENDPOINT=...
```

## 대안 검토

### Option A: 단일 LLM 유지 + 데이터 마스킹
- 장점: 구현 단순
- 단점: 마스킹 실패 리스크, 규제 준수 불확실
- **기각 사유**: 규제 요구사항 미충족

### Option B: 완전 On-Premise 즉시 도입
- 장점: 최고 수준 보안
- 단점: 높은 초기 비용, 긴 구축 기간
- **기각 사유**: 대회 일정에 맞지 않음

### Option C: 2-Track 점진적 도입 (선택)
- 장점: MVP 빠른 구현, 점진적 보안 강화
- 단점: Phase 2/3까지 완전한 분리 지연
- **선택 사유**: 현실적 일정 + 명확한 로드맵

## 참조

- PRD 2.3: 보안 및 규제 요구사항
- ADR-001: 아키텍처 분리 원칙
- ADR-002: LLM Provider 전략
- 금융위 클라우드 이용 가이드라인 (2024)
