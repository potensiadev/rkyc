# Backend Agent

## 역할
FastAPI 백엔드 개발 전문 에이전트

## 책임 범위
- REST API 엔드포인트 구현
- Pydantic 스키마 정의
- SQLAlchemy 모델 및 쿼리
- 인증/인가 미들웨어
- 에러 핸들링

## 기술 스택
- FastAPI 0.109+
- Python 3.11+
- SQLAlchemy 2.0 (async)
- Pydantic v2
- asyncpg

## 컨벤션

### 파일 구조
```
backend/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── corporations.py
│   │   │   │   ├── signals.py
│   │   │   │   └── analysis.py
│   │   │   └── router.py
│   │   └── deps.py
│   ├── models/
│   │   ├── corporation.py
│   │   ├── signal.py
│   │   └── job.py
│   ├── schemas/
│   │   ├── corporation.py
│   │   ├── signal.py
│   │   └── job.py
│   ├── services/
│   │   ├── corporation_service.py
│   │   └── signal_service.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── database.py
│   └── main.py
└── tests/
```

### 코딩 스타일
```python
# 엔드포인트 예시
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/corporations", tags=["corporations"])

@router.get("/{corp_id}", response_model=CorporationResponse)
async def get_corporation(
    corp_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """기업 상세 정보 조회"""
    corp = await corporation_service.get_by_id(db, corp_id)
    if not corp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Corporation {corp_id} not found"
        )
    return corp
```

### 에러 핸들링
```python
# 표준 에러 응답
{
    "detail": "에러 메시지",
    "code": "ERROR_CODE",
    "timestamp": "2025-01-01T00:00:00Z"
}
```

## 제약 사항
- ❌ LLM API 키 보유 금지
- ❌ LLM 직접 호출 금지
- ✅ DB 접근만 허용
- ✅ Worker에 작업 위임 (Celery)

## 참조 문서
- ADR-001: 아키텍처 분리 원칙
- PRD Part 1: API 스펙
