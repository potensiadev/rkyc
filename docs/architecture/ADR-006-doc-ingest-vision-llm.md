# ADR-006: DOC_INGEST Vision LLM 기반 문서 처리

## 상태
**승인됨** (2026-01-02)

## 컨텍스트
rKYC 시스템의 2단계 파이프라인(DOC_INGEST)에서 기업이 제출한 문서(사업자등록증, 등기부등본, 주주명부 등)를 자동으로 처리하여 구조화된 정보를 추출해야 합니다.

### 요구사항
- 5가지 문서 타입 지원 (PRD 6.2)
  - BIZ_REG: 사업자등록증
  - REGISTRY: 법인 등기부등본
  - SHAREHOLDERS: 주주명부
  - AOI: 정관
  - FIN_STATEMENT: 재무제표 요약
- 높은 추출 정확도
- 문서 변경 감지 (file_hash)
- 추출 근거(evidence) 필수

## 결정

### Vision LLM 선택
**Primary: Claude Opus 4.5 (claude-opus-4-5-20251101)**
- Vision 기능 지원
- 한국어 문서 인식 우수
- 구조화된 JSON 출력 안정성

**Fallback: GPT-5.2 Pro (gpt-5.2-pro-2025-12-11)**
- Vision 기능 지원
- 대체 옵션으로 안정성 확보

### 추출 전략

#### 1. 문서 타입별 프롬프트
각 문서 타입에 최적화된 프롬프트 정의:
- 추출 필드 명세 (fact_type, field_key)
- 값 형식 지정 (날짜: YYYY-MM-DD, 금액: 숫자)
- 신뢰도 기준 (HIGH/MED/LOW)

#### 2. 추출 결과 저장 구조
```
rkyc_document
├── doc_id (PK)
├── corp_id (FK)
├── doc_type
├── file_hash (변경 감지)
├── ingest_status (PENDING/RUNNING/DONE/FAILED)
└── last_ingested_at

rkyc_fact
├── fact_id (PK)
├── doc_id (FK)
├── fact_type (BIZ_INFO, CAPITAL, SHAREHOLDER, etc.)
├── field_key
├── field_value_text / field_value_num / field_value_json
├── confidence
├── evidence_snippet
└── evidence_page_no
```

### 에러 처리 정책

1. **Vision LLM 실패 시**
   - Claude 실패 → GPT-4o 자동 전환
   - 모든 Provider 실패 → 해당 문서만 FAILED 처리
   - 전체 파이프라인은 계속 진행

2. **재처리 정책**
   - file_hash 변경 시에만 재처리
   - 이미 DONE인 문서는 스킵

3. **최대 재시도**
   - Provider별 3회 (지수 백오프)

## 대안 검토

### Option A: 전통적 OCR (Tesseract + 규칙 기반)
- 장점: 비용 낮음, 오프라인 처리 가능
- 단점: 정확도 낮음, 문서 형식 변경에 취약, 개발 비용 높음

### Option B: 전용 문서 AI (AWS Textract, Google Document AI)
- 장점: 한국어 특화 모델 가능
- 단점: 추가 비용, 통합 복잡성, 유연성 제한

### Option C: Vision LLM (선택)
- 장점: 높은 정확도, 유연한 추출 규칙, 기존 LLM 인프라 활용
- 단점: API 비용, 처리 시간

## 결과

### 구현된 컴포넌트
- `DocIngestPipeline` (pipelines/doc_ingest.py)
- Vision LLM 서비스 확장 (service.py)
- 문서 타입별 프롬프트 (prompts.py)
- Documents API 엔드포인트 (endpoints/documents.py)

### 성능 고려사항
- 문서당 평균 처리 시간: 3-5초
- 배치 처리 미지원 (문서별 개별 처리)
- 대용량 문서 처리 시 비용 최적화 필요

## 참고
- PRD 6장: 제출 문서 처리
- PRD 14.3-14.4: 문서 및 팩트 테이블 스키마
