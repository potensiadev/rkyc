# ADR-003: 데이터베이스 선택 (Supabase PostgreSQL)

## 상태
Accepted

## 날짜
2025-01-XX

## 컨텍스트
rKYC 시스템은 기업 정보, 시그널, 분석 결과, 벡터 임베딩 등 다양한 데이터를 저장해야 한다.
데이터베이스 선택 시 다음 요소를 고려해야 한다:

1. 벡터 검색 지원 (인사이트 메모리)
2. 실시간 구독 기능 (UI 업데이트)
3. 인증 시스템 통합
4. 관리 부담 최소화
5. 한국 리전 지원 (지연시간)

## 결정
**Supabase PostgreSQL (Tokyo ap-northeast-1)을 선택한다.**

### 연결 설정
```python
# Direct Connection (migrations, admin)
DATABASE_URL = "postgresql://postgres.[project-ref]:password@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres?sslmode=require"

# Pooled Connection (application)
DATABASE_URL_POOLED = "postgresql://postgres.[project-ref]:password@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres?sslmode=require"
```

### 핵심 기능 활용

| 기능 | 용도 | 활성화 |
|-----|------|--------|
| pgvector | 인사이트 메모리 벡터 검색 | Extension |
| Realtime | 시그널 상태 변경 구독 | Built-in |
| Auth | 사용자 인증/인가 | Built-in |
| Row Level Security | 데이터 접근 제어 | Policy |

## 결과

### 긍정적 결과
1. **벡터 검색**: pgvector로 유사도 검색 네이티브 지원
2. **인증 통합**: Supabase Auth로 JWT 기반 인증
3. **실시간 업데이트**: Realtime으로 UI 자동 새로고침
4. **관리 편의**: 대시보드, 백업, 모니터링 내장
5. **지연시간**: Tokyo 리전으로 한국 사용자 최적

### 부정적 결과
1. **벤더 종속**: Supabase 특화 기능 사용 시
2. **비용**: 무료 티어 한계 (500MB)
3. **커스터마이징**: 일부 PostgreSQL 설정 제한

### 확장 설정
```sql
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable Row Level Security
ALTER TABLE corporations ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;

-- Create vector index
CREATE INDEX ON insight_memories
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

## 스키마 개요

### 핵심 테이블
```
corporations          - 기업 정보
├── signals          - 리스크 시그널 (1:N)
├── analysis_jobs    - 분석 작업 (1:N)
├── snapshots        - 재무 스냅샷 (1:N)
└── insight_memories - 인사이트 벡터 (1:N)
```

### 벡터 검색 쿼리 예시
```sql
SELECT
    id,
    content,
    1 - (embedding <=> query_embedding) AS similarity
FROM insight_memories
WHERE corporation_id = $1
ORDER BY embedding <=> query_embedding
LIMIT 5;
```

## 대안 검토

### 대안 1: AWS RDS PostgreSQL
- 장점: 완전 관리형, 높은 가용성
- 단점: 벡터 검색 별도 구성, 인증 시스템 없음
- **기각 사유**: 초기 설정 복잡성

### 대안 2: MongoDB Atlas
- 장점: 문서 DB 유연성, Vector Search 지원
- 단점: SQL 미지원, 스키마 변경 추적 어려움
- **기각 사유**: 관계형 데이터 모델이 더 적합

### 대안 3: Pinecone + PostgreSQL 분리
- 장점: 벡터 검색 특화, 스케일링 우수
- 단점: 2개 DB 관리, 데이터 동기화 복잡
- **기각 사유**: 운영 복잡성 증가

### 대안 4: SQLite (개발용)
- 장점: 설정 불필요, 로컬 개발 용이
- 단점: 동시성 제한, 벡터 미지원
- **기각 사유**: 프로덕션 불가

## Connection Pooling 전략

### Transaction Mode (Port 6543)
- 애플리케이션 연결에 사용
- 요청 단위로 연결 재사용
- PREPARED STATEMENTS 사용 불가

### Session Mode (Port 5432)
- 마이그레이션, 관리 작업에 사용
- 세션 유지 필요한 작업용

```python
# SQLAlchemy 설정
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    DATABASE_URL_POOLED.replace("postgresql://", "postgresql+asyncpg://"),
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)
```

## 보안 설정

### Row Level Security 정책
```sql
-- 사용자는 자신이 담당하는 기업만 조회
CREATE POLICY "Users can view assigned corporations"
ON corporations FOR SELECT
USING (
    auth.uid() IN (
        SELECT user_id FROM user_corporation_assignments
        WHERE corporation_id = corporations.id
    )
);
```

### SSL 필수
```python
# sslmode=require 필수
connect_args={"ssl": "require"}
```

## 참조
- PRD 추가 지침서 - Section 4.1 Supabase 설정
- Supabase 공식 문서: https://supabase.com/docs
- pgvector: https://github.com/pgvector/pgvector
