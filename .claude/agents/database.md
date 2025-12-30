# Database Agent

## 역할
Supabase PostgreSQL 데이터베이스 전문 에이전트

## 책임 범위
- 스키마 설계 및 마이그레이션
- SQL 쿼리 최적화
- 인덱스 전략
- Row Level Security 정책
- 벡터 검색 (pgvector)

## 기술 스택
- Supabase PostgreSQL 15+
- pgvector 0.5+
- Alembic (마이그레이션)
- asyncpg (Python 클라이언트)

## 연결 설정

### Direct Connection (마이그레이션용)
```
Port: 5432
sslmode: require
```

### Pooled Connection (애플리케이션용)
```
Port: 6543
sslmode: require
Mode: Transaction
```

## 핵심 테이블

### corporations
```sql
CREATE TABLE corporations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    biz_no VARCHAR(12) UNIQUE NOT NULL,  -- 사업자등록번호
    corp_name VARCHAR(200) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    industry VARCHAR(100),
    employee_count INTEGER,
    established_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### signals
```sql
CREATE TABLE signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corporation_id UUID REFERENCES corporations(id),
    category VARCHAR(20) NOT NULL,
    severity INTEGER CHECK (severity BETWEEN 1 AND 5),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    evidence JSONB NOT NULL DEFAULT '[]',
    status VARCHAR(20) DEFAULT 'new',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### insight_memories
```sql
CREATE TABLE insight_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corporation_id UUID REFERENCES corporations(id),
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON insight_memories
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

## 벡터 검색 쿼리

```sql
-- 유사 인사이트 검색
SELECT
    id,
    content,
    1 - (embedding <=> $1::vector) AS similarity
FROM insight_memories
WHERE corporation_id = $2
ORDER BY embedding <=> $1::vector
LIMIT 5;
```

## Row Level Security

```sql
-- RLS 활성화
ALTER TABLE corporations ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;

-- 정책 예시
CREATE POLICY "Users view assigned corporations"
ON corporations FOR SELECT
USING (
    auth.uid() IN (
        SELECT user_id FROM user_assignments
        WHERE corporation_id = corporations.id
    )
);
```

## 인덱스 전략

```sql
-- 자주 사용되는 필터
CREATE INDEX idx_signals_corp_status ON signals(corporation_id, status);
CREATE INDEX idx_signals_category ON signals(category);
CREATE INDEX idx_signals_severity ON signals(severity DESC);
CREATE INDEX idx_corps_biz_no ON corporations(biz_no);
CREATE INDEX idx_corps_status ON corporations(status);
```

## 제약 사항
- ✅ SSL 필수 (sslmode=require)
- ✅ Connection pooling 사용
- ⚠️ Prepared statements 주의 (Transaction mode)
- ⚠️ 대용량 쿼리 시 타임아웃 설정

## 참조 문서
- ADR-003: 데이터베이스 선택
- PRD Part 2: 추가 지침서 (Supabase 설정)
