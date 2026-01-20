# rKYC Implementation Plan: 코드베이스 불일치 사항 해결

## 개요

현재 코드베이스와 PRD/아키텍처 문서 간 불일치 사항을 해결하기 위한 구현 계획서입니다.
Claude Code가 순차적으로 작업할 수 있도록 우선순위와 상세 태스크를 정의합니다.

---

## 불일치 항목 요약

| # | 항목 | 현재 상태 | 목표 상태 | 우선순위 |
|---|------|----------|----------|----------|
| 1 | DOC_INGEST | Vision LLM | pdfplumber + 정규식 + LLM 보완 | 🔴 P0 |
| 2 | LLM Fallback | 2단계 (Claude → GPT-4o) | 3단계 (+ Gemini 1.5 Pro) | 🟡 P1 |
| 3 | Embedding/pgvector | 파일만 존재, 미사용 | 인사이트 메모리 벡터 검색 | 🟢 P2 |
| 4 | Celery Worker | 설정만 존재 | Railway 배포 또는 동기 실행 확인 | 🟢 P2 |

---

## Task 1: DOC_INGEST 파이프라인 재구현 (P0)

### 1.1 목표
Vision LLM 기반 문서 처리를 **PDF 텍스트 파싱 + 정규식 + LLM 보완** 방식으로 변경

### 1.2 변경 이유
- 비용 절감: Vision LLM 대비 1/10 이하
- 속도 향상: 정규식은 밀리초 단위
- 정확도: 정형화된 KYC 문서는 규칙 기반이 더 일관됨

### 1.3 파일 변경 목록

```
backend/
├── requirements.txt                    # pdfplumber 추가
├── app/worker/pipelines/
│   ├── doc_ingest.py                  # 전면 재작성
│   └── doc_parsers/                   # 신규 디렉토리
│       ├── __init__.py
│       ├── base.py                    # 베이스 파서 클래스
│       ├── biz_reg_parser.py          # 사업자등록증 파서
│       ├── registry_parser.py         # 등기부등본 파서
│       ├── shareholders_parser.py     # 주주명부 파서
│       ├── aoi_parser.py              # 정관 파서
│       └── fin_statement_parser.py    # 재무제표 파서
└── app/worker/llm/
    └── prompts.py                     # DOC_EXTRACTION 프롬프트 수정
```

### 1.4 구현 상세

#### Step 1: requirements.txt 수정
```txt
# Document Parsing
pdfplumber>=0.10.0
```

#### Step 2: 베이스 파서 클래스 생성
```python
# backend/app/worker/pipelines/doc_parsers/base.py

from abc import ABC, abstractmethod
from typing import Optional
import pdfplumber
import re

class BaseDocParser(ABC):
    """문서 파서 베이스 클래스"""
    
    def __init__(self, llm_service=None):
        self.llm = llm_service
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """PDF에서 텍스트 추출"""
        text_content = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)
        return "\n".join(text_content)
    
    def extract_tables_from_pdf(self, pdf_path: str) -> list[list]:
        """PDF에서 표 추출"""
        tables = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)
        return tables
    
    @abstractmethod
    def parse(self, pdf_path: str) -> dict:
        """문서 파싱 - 하위 클래스에서 구현"""
        pass
    
    @abstractmethod
    def get_regex_patterns(self) -> dict:
        """정규식 패턴 반환 - 하위 클래스에서 구현"""
        pass
    
    def extract_with_regex(self, text: str, patterns: dict) -> dict:
        """정규식으로 필드 추출"""
        results = {}
        failed_fields = []
        
        for field_name, pattern in patterns.items():
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                results[field_name] = match.group(1).strip()
            else:
                failed_fields.append(field_name)
        
        return results, failed_fields
    
    def fallback_to_llm(self, text: str, failed_fields: list, doc_type: str) -> dict:
        """실패한 필드만 LLM으로 보완"""
        if not failed_fields or not self.llm:
            return {}
        
        prompt = f"""다음 {doc_type} 문서에서 아래 필드를 추출해주세요.
        
추출할 필드: {', '.join(failed_fields)}

문서 내용:
{text[:3000]}

JSON 형식으로 응답해주세요:
{{"field_name": "value", ...}}

찾을 수 없는 필드는 null로 표시하세요."""

        messages = [{"role": "user", "content": prompt}]
        result = self.llm.call_with_json_response(messages)
        return result
```

#### Step 3: 사업자등록증 파서 구현 (예시)
```python
# backend/app/worker/pipelines/doc_parsers/biz_reg_parser.py

from .base import BaseDocParser

class BizRegParser(BaseDocParser):
    """사업자등록증 파서"""
    
    DOC_TYPE = "BIZ_REG"
    
    def get_regex_patterns(self) -> dict:
        return {
            "biz_no": r"사업자\s*등록번호[:\s]*(\d{3}-\d{2}-\d{5})",
            "corp_name": r"상\s*호[:\s]*(.+?)(?:\n|법인명)",
            "ceo_name": r"대\s*표\s*자[:\s]*(.+?)(?:\n|주민)",
            "address": r"사업장\s*소재지[:\s]*(.+?)(?:\n|업)",
            "biz_type": r"업\s*태[:\s]*(.+?)(?:\n|종목)",
            "biz_item": r"종\s*목[:\s]*(.+?)(?:\n|$)",
            "open_date": r"개업\s*연월일[:\s]*(\d{4}[.\-/]\d{2}[.\-/]\d{2})",
        }
    
    def parse(self, pdf_path: str) -> dict:
        """사업자등록증 파싱"""
        # Step 1: 텍스트 추출
        text = self.extract_text_from_pdf(pdf_path)
        
        # Step 2: 정규식으로 추출
        patterns = self.get_regex_patterns()
        results, failed_fields = self.extract_with_regex(text, patterns)
        
        # Step 3: 실패한 필드만 LLM 보완
        if failed_fields:
            llm_results = self.fallback_to_llm(text, failed_fields, "사업자등록증")
            results.update({k: v for k, v in llm_results.items() if v is not None})
        
        # Step 4: fact 형식으로 변환
        facts = []
        for field_key, field_value in results.items():
            facts.append({
                "fact_type": "BIZ_REG",
                "field_key": field_key,
                "field_value": field_value,
                "confidence": "HIGH" if field_key not in failed_fields else "MED",
                "evidence_snippet": self._get_snippet(text, field_value),
            })
        
        return {"facts": facts, "raw_text": text[:500]}
    
    def _get_snippet(self, text: str, value: str, context_chars: int = 50) -> str:
        """값 주변 텍스트 스니펫 추출"""
        if not value or value not in text:
            return ""
        idx = text.find(value)
        start = max(0, idx - context_chars)
        end = min(len(text), idx + len(value) + context_chars)
        return text[start:end]
```

#### Step 4: doc_ingest.py 수정
```python
# backend/app/worker/pipelines/doc_ingest.py 주요 변경사항

from app.worker.pipelines.doc_parsers import (
    BizRegParser,
    RegistryParser,
    ShareholdersParser,
    AoiParser,
    FinStatementParser,
)

class DocIngestPipeline:
    """Stage 2: DOC_INGEST - PDF 텍스트 파싱 기반 문서 처리"""
    
    def __init__(self):
        self.llm = LLMService()
        
        # 문서 타입별 파서 매핑
        self.parsers = {
            DocType.BIZ_REG: BizRegParser(self.llm),
            DocType.REGISTRY: RegistryParser(self.llm),
            DocType.SHAREHOLDERS: ShareholdersParser(self.llm),
            DocType.AOI: AoiParser(self.llm),
            DocType.FIN_STATEMENT: FinStatementParser(self.llm),
        }
    
    def _process_document(self, db, doc: Document, corp_id: str) -> Optional[dict]:
        """단일 문서 처리 - 텍스트 파싱 방식"""
        parser = self.parsers.get(doc.doc_type)
        if not parser:
            raise DocumentProcessingError(f"No parser for doc_type: {doc.doc_type}")
        
        # PDF 파싱 실행
        result = parser.parse(doc.storage_path)
        
        # facts 저장
        saved_facts = self._save_facts(db, doc, corp_id, result.get("facts", []))
        
        return {
            "doc_type": doc.doc_type.value,
            "facts": saved_facts,
            "extraction_method": "pdf_parser",
        }
```

### 1.5 테스트 계획
```bash
# 단위 테스트
pytest backend/tests/test_doc_parsers.py -v

# 통합 테스트 - 실제 PDF 파일로 테스트
python -m app.worker.pipelines.doc_ingest --test --corp_id=TEST001
```

---

## Task 2: LLM Fallback 3단계 확장 (P1)

### 2.1 목표
현재 2단계 fallback (Claude → GPT-4o)을 3단계 (+ Gemini 1.5 Pro)로 확장

### 2.2 파일 변경 목록
```
backend/
├── .env.example                       # GOOGLE_API_KEY 추가
├── app/core/config.py                 # GOOGLE_API_KEY 설정 추가
└── app/worker/llm/service.py          # Gemini 모델 추가
```

### 2.3 구현 상세

#### Step 1: config.py 수정
```python
# backend/app/core/config.py 추가

class Settings(BaseSettings):
    # ... 기존 설정 ...
    
    # LLM API Keys
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""  # 추가
```

#### Step 2: service.py 수정
```python
# backend/app/worker/llm/service.py

class LLMService:
    # Model configuration - 3단계 fallback
    MODELS = [
        {
            "model": "claude-opus-4-5-20251101",
            "provider": "anthropic",
            "max_tokens": 4096,
        },
        {
            "model": "gpt-5.2-pro-2025-12-11",
            "provider": "openai",
            "max_tokens": 4096,
        },
        {
            "model": "gemini/gemini-3-pro-preview",
            "provider": "google",
            "max_tokens": 4096,
        },
    ]
    
    def _configure_api_keys(self):
        """Set API keys for litellm"""
        if settings.ANTHROPIC_API_KEY:
            litellm.anthropic_key = settings.ANTHROPIC_API_KEY
        if settings.OPENAI_API_KEY:
            litellm.openai_key = settings.OPENAI_API_KEY
        if settings.GOOGLE_API_KEY:  # 추가
            litellm.google_key = settings.GOOGLE_API_KEY
    
    def _get_api_key(self, provider: str) -> str:
        """Get API key for specific provider"""
        if provider == "anthropic":
            return settings.ANTHROPIC_API_KEY
        elif provider == "openai":
            return settings.OPENAI_API_KEY
        elif provider == "google":  # 추가
            return settings.GOOGLE_API_KEY
        return ""
```

### 2.4 테스트 계획
```python
# 각 provider별 개별 테스트
def test_claude_fallback():
    # Claude API key를 임시로 무효화하고 GPT-4o로 fallback 확인
    pass

def test_gpt_fallback():
    # Claude, GPT 둘 다 무효화하고 Gemini로 fallback 확인
    pass
```

---

## Task 3: Embedding & pgvector 인사이트 메모리 구현 (P2)

### 3.1 목표
인사이트 메모리 기능을 위한 벡터 검색 구현

### 3.2 파일 변경 목록
```
backend/
├── sql/
│   └── migration_v5_vector.sql        # 이미 존재, 적용 확인
├── app/worker/llm/embedding.py        # 구현 완성
└── app/worker/pipelines/insight.py    # 벡터 검색 연동
```

### 3.3 구현 상세

#### Step 1: migration 적용 확인
```sql
-- Supabase에서 pgvector 확장 활성화 확인
CREATE EXTENSION IF NOT EXISTS vector;

-- rkyc_case_index에 embedding 컬럼 추가 (migration_v5 참조)
ALTER TABLE rkyc_case_index 
ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- 벡터 검색 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_case_embedding 
ON rkyc_case_index 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

#### Step 2: embedding.py 완성
```python
# backend/app/worker/llm/embedding.py

import numpy as np
from openai import OpenAI
from app.core.config import settings

class EmbeddingService:
    """OpenAI Embedding Service"""

    MODEL = "text-embedding-3-large"
    DIMENSIONS = 2000
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def embed_text(self, text: str) -> list[float]:
        """텍스트를 벡터로 변환"""
        response = self.client.embeddings.create(
            model=self.MODEL,
            input=text,
            dimensions=self.DIMENSIONS,
        )
        return response.data[0].embedding
    
    def embed_signal(self, signal: dict) -> list[float]:
        """시그널을 벡터로 변환"""
        # 시그널 정보를 텍스트로 결합
        text = f"""
        Signal Type: {signal.get('signal_type', '')}
        Event Type: {signal.get('event_type', '')}
        Industry: {signal.get('industry_code', '')}
        Summary: {signal.get('summary', '')}
        """
        return self.embed_text(text)
```

#### Step 3: insight.py 벡터 검색 연동
```python
# backend/app/worker/pipelines/insight.py 수정

from app.worker.llm.embedding import EmbeddingService

class InsightPipeline:
    def __init__(self):
        self.embedding = EmbeddingService()
    
    def find_similar_cases(self, signal: dict, top_k: int = 5) -> list[dict]:
        """유사 케이스 벡터 검색"""
        # 현재 시그널 임베딩
        query_embedding = self.embedding.embed_signal(signal)
        
        # pgvector 유사도 검색
        with get_sync_db() as db:
            result = db.execute(
                text("""
                    SELECT 
                        case_id, corp_id, signal_type, event_type,
                        summary, evidence_refs,
                        1 - (embedding <=> :query_embedding) as similarity
                    FROM rkyc_case_index
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> :query_embedding
                    LIMIT :top_k
                """),
                {"query_embedding": str(query_embedding), "top_k": top_k}
            )
            return [dict(row) for row in result.fetchall()]
```

---

## Task 4: Worker 배포 확인 및 정리 (P2)

### 4.1 목표
Celery Worker 설정 확인 및 Railway 배포 상태 점검

### 4.2 확인 사항

#### Option A: Celery Worker 별도 배포 (권장)
```toml
# backend/railway-worker.toml (신규 생성)
[build]
builder = "nixpacks"

[deploy]
startCommand = "celery -A app.worker.celery_app worker --loglevel=info"
healthcheckPath = ""
```

Railway에서 별도 서비스로 Worker 배포 필요

#### Option B: 동기 실행 (대회용 간소화)
현재 `/jobs/analyze/run` API가 동기로 실행되는지 확인
```python
# backend/app/api/v1/endpoints/jobs.py 확인
# Celery task.delay() 대신 직접 실행하는 방식인지 확인
```

### 4.3 현재 상태 파악 명령
```bash
# Railway 서비스 목록 확인
railway status

# Celery worker 프로세스 확인
ps aux | grep celery

# Redis 연결 확인
redis-cli ping
```

---

## 실행 순서 요약

```
Phase 1 (P0) - 필수
└── Task 1: DOC_INGEST 재구현
    ├── 1.1 requirements.txt에 pdfplumber 추가
    ├── 1.2 doc_parsers/ 디렉토리 생성
    ├── 1.3 BaseDocParser 구현
    ├── 1.4 BizRegParser 구현 (사업자등록증)
    ├── 1.5 FinStatementParser 구현 (재무제표)
    ├── 1.6 doc_ingest.py 수정
    └── 1.7 테스트

Phase 2 (P1) - 권장
└── Task 2: LLM Fallback 확장
    ├── 2.1 config.py에 GOOGLE_API_KEY 추가
    ├── 2.2 service.py에 Gemini 모델 추가
    └── 2.3 테스트

Phase 3 (P2) - 선택
├── Task 3: Embedding/pgvector 구현
│   ├── 3.1 migration 적용
│   ├── 3.2 embedding.py 완성
│   └── 3.3 insight.py 벡터 검색 연동
│
└── Task 4: Worker 배포 확인
    └── 4.1 Railway 배포 상태 점검
```

---

## 예상 소요 시간

| Task | 예상 시간 | 비고 |
|------|----------|------|
| Task 1: DOC_INGEST | 4-6시간 | 5개 파서 구현 포함 |
| Task 2: LLM Fallback | 30분 | 설정 추가만 |
| Task 3: Embedding | 2-3시간 | pgvector 연동 포함 |
| Task 4: Worker | 1시간 | 확인 및 설정 |
| **Total** | **8-11시간** | |

---

## 참고 파일

- PRD: `/docs/prd.md`
- 현재 doc_ingest: `/backend/app/worker/pipelines/doc_ingest.py`
- LLM Service: `/backend/app/worker/llm/service.py`
- Embedding (미완성): `/backend/app/worker/llm/embedding.py`
- DB Schema: `/backend/sql/schema_v2.sql`
