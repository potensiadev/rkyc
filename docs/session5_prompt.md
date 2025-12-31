# 세션 5: Signal 상태 관리 API 및 Detail 페이지 API 연동

## 현재 상태 요약

**완료된 작업:**
- Phase 1-4 완료 (DB 스키마, Backend API, Frontend 배포, Demo Mode)
- Supabase에 6개 기업, 29개 시그널 데이터
- Railway 배포: https://rkyc-production.up.railway.app
- Vercel 배포: https://rkyc-wine.vercel.app

**배포 환경:**
- Backend: Railway (FastAPI + SQLAlchemy 2.0)
- Frontend: Vercel (React + Vite)
- Database: Supabase PostgreSQL (Tokyo ap-northeast-1)

---

## 이번 세션에서 해결할 문제

### 문제 1: Signal Status 컬럼 누락
`rkyc_signal`과 `rkyc_signal_index` 테이블에 상태 관리 컬럼이 없음

### 문제 2: SignalDetailPage Mock 데이터 사용
`src/pages/SignalDetailPage.tsx`에서 `mockSignalDetails` 하드코딩 사용 중

### 문제 3: CorporateDetailPage Mock 데이터 사용  
`src/pages/CorporateDetailPage.tsx`에서 `@/data/` Mock 파일들 import 중

### 문제 4: Evidence 조회 API 없음
`rkyc_evidence` 테이블은 있으나 조회 API 미구현

### 문제 5: Dashboard Summary API 없음
`rkyc_dashboard_summary` 테이블은 있으나 조회 API 미구현

---

## Phase 1: DB 스키마 마이그레이션 (ALTER TABLE)

Supabase SQL Editor에서 실행할 마이그레이션 SQL을 생성해주세요.

### 1.1 Signal Status ENUM 생성

```sql
-- Signal 상태 ENUM (NEW → REVIEWED → DISMISSED)
CREATE TYPE signal_status_enum AS ENUM ('NEW', 'REVIEWED', 'DISMISSED');
```

### 1.2 rkyc_signal 테이블에 컬럼 추가

```sql
ALTER TABLE rkyc_signal 
ADD COLUMN signal_status signal_status_enum DEFAULT 'NEW',
ADD COLUMN reviewed_at TIMESTAMPTZ,
ADD COLUMN dismissed_at TIMESTAMPTZ,
ADD COLUMN dismiss_reason TEXT;

-- 기존 데이터 NEW로 설정
UPDATE rkyc_signal SET signal_status = 'NEW' WHERE signal_status IS NULL;
```

### 1.3 rkyc_signal_index 테이블에 컬럼 추가 (Denormalized)

```sql
ALTER TABLE rkyc_signal_index 
ADD COLUMN signal_status signal_status_enum DEFAULT 'NEW',
ADD COLUMN reviewed_at TIMESTAMPTZ,
ADD COLUMN dismissed_at TIMESTAMPTZ,
ADD COLUMN dismiss_reason TEXT;

-- 기존 데이터 NEW로 설정
UPDATE rkyc_signal_index SET signal_status = 'NEW' WHERE signal_status IS NULL;
```

### 1.4 인덱스 추가

```sql
CREATE INDEX idx_signal_status ON rkyc_signal(signal_status);
CREATE INDEX idx_signal_index_status ON rkyc_signal_index(signal_status);
```

**출력물:** `backend/sql/migration_v3_signal_status.sql` 파일 생성

---

## Phase 2: Backend API 구현

### 2.1 Signal 모델 업데이트

`backend/app/models/signal.py`에 추가:

```python
class SignalStatus(str, enum.Enum):
    """시그널 상태"""
    NEW = "NEW"
    REVIEWED = "REVIEWED"
    DISMISSED = "DISMISSED"
```

`SignalIndex` 클래스에 컬럼 추가:
```python
signal_status = Column(SQLEnum(SignalStatus, name="signal_status_enum"), default=SignalStatus.NEW)
reviewed_at = Column(TIMESTAMP(timezone=True), nullable=True)
dismissed_at = Column(TIMESTAMP(timezone=True), nullable=True)
dismiss_reason = Column(Text, nullable=True)
```

### 2.2 Signal 원본 모델 추가 (rkyc_signal)

`backend/app/models/signal.py`에 `Signal` 클래스 추가:

```python
class Signal(Base):
    """시그널 원본 테이블 (PRD 14.7.1)"""
    __tablename__ = "rkyc_signal"
    
    signal_id = Column(PGUUID(as_uuid=True), primary_key=True)
    corp_id = Column(String(20), nullable=False)
    signal_type = Column(SQLEnum(SignalType, name="signal_type_enum"), nullable=False)
    event_type = Column(SQLEnum(EventType, name="event_type_enum"), nullable=False)
    event_signature = Column(String(64), nullable=False)
    snapshot_version = Column(Integer, nullable=False)
    impact_direction = Column(SQLEnum(ImpactDirection, name="impact_direction_enum"), nullable=False)
    impact_strength = Column(SQLEnum(ImpactStrength, name="impact_strength_enum"), nullable=False)
    confidence = Column(SQLEnum(ConfidenceLevel, name="confidence_level"), nullable=False)
    summary = Column(Text, nullable=False)
    signal_status = Column(SQLEnum(SignalStatus, name="signal_status_enum"), default=SignalStatus.NEW)
    reviewed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    dismissed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    dismiss_reason = Column(Text, nullable=True)
    last_updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
```

### 2.3 Evidence 모델 추가

`backend/app/models/signal.py`에 추가:

```python
class Evidence(Base):
    """시그널 근거 테이블 (PRD 14.7.2)"""
    __tablename__ = "rkyc_evidence"
    
    evidence_id = Column(PGUUID(as_uuid=True), primary_key=True)
    signal_id = Column(PGUUID(as_uuid=True), nullable=False)
    evidence_type = Column(String(20), nullable=False)  # INTERNAL_FIELD, DOC, EXTERNAL
    ref_type = Column(String(20), nullable=False)  # SNAPSHOT_KEYPATH, DOC_PAGE, URL
    ref_value = Column(Text, nullable=False)
    snippet = Column(Text, nullable=True)
    meta = Column(JSONB, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
```

### 2.4 Pydantic 스키마 추가

`backend/app/schemas/signal.py`에 추가:

```python
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from enum import Enum

class SignalStatusEnum(str, Enum):
    NEW = "NEW"
    REVIEWED = "REVIEWED"
    DISMISSED = "DISMISSED"

# 상태 변경 요청
class SignalStatusUpdate(BaseModel):
    status: SignalStatusEnum

# 기각 요청
class SignalDismissRequest(BaseModel):
    reason: str

# Evidence 응답
class EvidenceResponse(BaseModel):
    evidence_id: str
    signal_id: str
    evidence_type: str
    ref_type: str
    ref_value: str
    snippet: Optional[str] = None
    meta: Optional[dict] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Signal 상세 응답 (Evidence 포함)
class SignalDetailResponse(BaseModel):
    signal_id: str
    corp_id: str
    corp_name: str
    industry_code: str
    signal_type: str
    event_type: str
    impact_direction: str
    impact_strength: str
    confidence: str
    title: str
    summary: str  # 전체 요약 (rkyc_signal.summary)
    summary_short: Optional[str] = None
    signal_status: SignalStatusEnum
    evidence_count: int
    detected_at: datetime
    reviewed_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    dismiss_reason: Optional[str] = None
    evidences: List[EvidenceResponse] = []
    
    class Config:
        from_attributes = True

# Dashboard Summary 응답
class DashboardSummaryResponse(BaseModel):
    total_signals: int
    new_signals: int
    risk_signals: int
    opportunity_signals: int
    by_type: dict  # {"DIRECT": 17, "INDUSTRY": 7, "ENVIRONMENT": 5}
    by_status: dict  # {"NEW": 25, "REVIEWED": 3, "DISMISSED": 1}
    generated_at: datetime
```

### 2.5 Signal API 엔드포인트 추가

`backend/app/api/v1/endpoints/signals.py`에 추가:

```python
from datetime import datetime
from app.models.signal import Signal, Evidence, SignalStatus
from app.schemas.signal import (
    SignalStatusUpdate, 
    SignalDismissRequest, 
    SignalDetailResponse,
    EvidenceResponse,
)

# GET /signals/{signal_id}/detail - 상세 조회 (Evidence 포함)
@router.get("/{signal_id}/detail", response_model=SignalDetailResponse)
async def get_signal_detail(
    signal_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """시그널 상세 조회 (Evidence 포함)"""
    
    # SignalIndex에서 기본 정보
    index_query = select(SignalIndex).where(SignalIndex.signal_id == signal_id)
    index_result = await db.execute(index_query)
    signal_index = index_result.scalar_one_or_none()
    
    if not signal_index:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    # Signal 원본에서 전체 summary
    signal_query = select(Signal).where(Signal.signal_id == signal_id)
    signal_result = await db.execute(signal_query)
    signal = signal_result.scalar_one_or_none()
    
    # Evidence 조회
    evidence_query = select(Evidence).where(Evidence.signal_id == signal_id)
    evidence_result = await db.execute(evidence_query)
    evidences = evidence_result.scalars().all()
    
    return SignalDetailResponse(
        signal_id=str(signal_index.signal_id),
        corp_id=signal_index.corp_id,
        corp_name=signal_index.corp_name,
        industry_code=signal_index.industry_code,
        signal_type=signal_index.signal_type.value,
        event_type=signal_index.event_type.value,
        impact_direction=signal_index.impact_direction.value,
        impact_strength=signal_index.impact_strength.value,
        confidence=signal_index.confidence.value,
        title=signal_index.title,
        summary=signal.summary if signal else signal_index.summary_short or "",
        summary_short=signal_index.summary_short,
        signal_status=signal_index.signal_status or SignalStatus.NEW,
        evidence_count=signal_index.evidence_count,
        detected_at=signal_index.detected_at,
        reviewed_at=signal_index.reviewed_at,
        dismissed_at=signal_index.dismissed_at,
        dismiss_reason=signal_index.dismiss_reason,
        evidences=[EvidenceResponse.model_validate(e) for e in evidences],
    )


# PATCH /signals/{signal_id}/status - 상태 변경
@router.patch("/{signal_id}/status")
async def update_signal_status(
    signal_id: UUID,
    status_update: SignalStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """시그널 상태 변경 (NEW → REVIEWED)"""
    
    now = datetime.utcnow()
    
    # rkyc_signal 업데이트
    signal_query = select(Signal).where(Signal.signal_id == signal_id)
    signal_result = await db.execute(signal_query)
    signal = signal_result.scalar_one_or_none()
    
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    signal.signal_status = status_update.status
    if status_update.status == SignalStatus.REVIEWED:
        signal.reviewed_at = now
    signal.last_updated_at = now
    
    # rkyc_signal_index도 동기화
    index_query = select(SignalIndex).where(SignalIndex.signal_id == signal_id)
    index_result = await db.execute(index_query)
    signal_index = index_result.scalar_one_or_none()
    
    if signal_index:
        signal_index.signal_status = status_update.status
        if status_update.status == SignalStatus.REVIEWED:
            signal_index.reviewed_at = now
        signal_index.last_updated_at = now
    
    await db.commit()
    
    return {"message": "Status updated", "status": status_update.status.value}


# POST /signals/{signal_id}/dismiss - 기각
@router.post("/{signal_id}/dismiss")
async def dismiss_signal(
    signal_id: UUID,
    dismiss_request: SignalDismissRequest,
    db: AsyncSession = Depends(get_db),
):
    """시그널 기각 (사유 포함)"""
    
    now = datetime.utcnow()
    
    # rkyc_signal 업데이트
    signal_query = select(Signal).where(Signal.signal_id == signal_id)
    signal_result = await db.execute(signal_query)
    signal = signal_result.scalar_one_or_none()
    
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    signal.signal_status = SignalStatus.DISMISSED
    signal.dismissed_at = now
    signal.dismiss_reason = dismiss_request.reason
    signal.last_updated_at = now
    
    # rkyc_signal_index도 동기화
    index_query = select(SignalIndex).where(SignalIndex.signal_id == signal_id)
    index_result = await db.execute(index_query)
    signal_index = index_result.scalar_one_or_none()
    
    if signal_index:
        signal_index.signal_status = SignalStatus.DISMISSED
        signal_index.dismissed_at = now
        signal_index.dismiss_reason = dismiss_request.reason
        signal_index.last_updated_at = now
    
    await db.commit()
    
    return {"message": "Signal dismissed", "reason": dismiss_request.reason}
```

### 2.6 Dashboard API 추가

`backend/app/api/v1/endpoints/dashboard.py` 새로 생성:

```python
"""
rKYC Dashboard API Endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from app.core.database import get_db
from app.models.signal import SignalIndex, SignalType, ImpactDirection, SignalStatus
from app.schemas.signal import DashboardSummaryResponse

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """Dashboard 요약 통계"""
    
    # 전체 카운트
    total_query = select(func.count()).select_from(SignalIndex)
    total = (await db.execute(total_query)).scalar_one()
    
    # NEW 상태 카운트
    new_query = select(func.count()).select_from(SignalIndex).where(
        SignalIndex.signal_status == SignalStatus.NEW
    )
    new_count = (await db.execute(new_query)).scalar_one() or 0
    
    # RISK 카운트
    risk_query = select(func.count()).select_from(SignalIndex).where(
        SignalIndex.impact_direction == ImpactDirection.RISK
    )
    risk_count = (await db.execute(risk_query)).scalar_one()
    
    # OPPORTUNITY 카운트
    opp_query = select(func.count()).select_from(SignalIndex).where(
        SignalIndex.impact_direction == ImpactDirection.OPPORTUNITY
    )
    opp_count = (await db.execute(opp_query)).scalar_one()
    
    # Signal Type별 카운트
    type_counts = {}
    for signal_type in SignalType:
        type_query = select(func.count()).select_from(SignalIndex).where(
            SignalIndex.signal_type == signal_type
        )
        type_counts[signal_type.value] = (await db.execute(type_query)).scalar_one()
    
    # Status별 카운트
    status_counts = {}
    for status in SignalStatus:
        status_query = select(func.count()).select_from(SignalIndex).where(
            SignalIndex.signal_status == status
        )
        status_counts[status.value] = (await db.execute(status_query)).scalar_one() or 0
    
    return DashboardSummaryResponse(
        total_signals=total,
        new_signals=new_count,
        risk_signals=risk_count,
        opportunity_signals=opp_count,
        by_type=type_counts,
        by_status=status_counts,
        generated_at=datetime.utcnow(),
    )
```

### 2.7 라우터 등록

`backend/app/api/v1/router.py` 수정:

```python
from app.api.v1.endpoints import corporations, signals, jobs, dashboard

api_router = APIRouter()
api_router.include_router(corporations.router, prefix="/corporations", tags=["corporations"])
api_router.include_router(signals.router, prefix="/signals", tags=["signals"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
```

---

## Phase 3: Frontend API 연동

### 3.1 API 클라이언트 추가

`src/lib/api.ts`에 추가:

```typescript
// Signal Detail 응답 (Evidence 포함)
export interface ApiEvidence {
  evidence_id: string;
  signal_id: string;
  evidence_type: 'INTERNAL_FIELD' | 'DOC' | 'EXTERNAL';
  ref_type: 'SNAPSHOT_KEYPATH' | 'DOC_PAGE' | 'URL';
  ref_value: string;
  snippet: string | null;
  meta: Record<string, unknown> | null;
  created_at: string;
}

export interface ApiSignalDetail extends ApiSignal {
  summary: string;  // 전체 요약
  signal_status: 'NEW' | 'REVIEWED' | 'DISMISSED';
  reviewed_at: string | null;
  dismissed_at: string | null;
  dismiss_reason: string | null;
  evidences: ApiEvidence[];
}

export interface ApiDashboardSummary {
  total_signals: number;
  new_signals: number;
  risk_signals: number;
  opportunity_signals: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
  generated_at: string;
}

// Signal Detail API
export async function getSignalDetail(signalId: string): Promise<ApiSignalDetail> {
  return fetchApi<ApiSignalDetail>(`/api/v1/signals/${signalId}/detail`);
}

// Signal Status Update API
export async function updateSignalStatus(
  signalId: string, 
  status: 'NEW' | 'REVIEWED' | 'DISMISSED'
): Promise<{ message: string; status: string }> {
  return fetchApi(`/api/v1/signals/${signalId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}

// Signal Dismiss API
export async function dismissSignal(
  signalId: string, 
  reason: string
): Promise<{ message: string; reason: string }> {
  return fetchApi(`/api/v1/signals/${signalId}/dismiss`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

// Dashboard Summary API
export async function getDashboardSummary(): Promise<ApiDashboardSummary> {
  return fetchApi<ApiDashboardSummary>('/api/v1/dashboard/summary');
}
```

### 3.2 React Query 훅 추가

`src/hooks/useApi.ts`에 추가:

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  getSignalDetail, 
  updateSignalStatus, 
  dismissSignal,
  getDashboardSummary,
  ApiSignalDetail,
  ApiDashboardSummary,
} from '@/lib/api';

// Signal Detail 훅
export function useSignalDetail(signalId: string) {
  return useQuery<ApiSignalDetail>({
    queryKey: ['signal', signalId],
    queryFn: () => getSignalDetail(signalId),
    enabled: !!signalId,
  });
}

// Signal Status 변경 훅
export function useUpdateSignalStatus() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ signalId, status }: { signalId: string; status: 'NEW' | 'REVIEWED' | 'DISMISSED' }) =>
      updateSignalStatus(signalId, status),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['signal', variables.signalId] });
      queryClient.invalidateQueries({ queryKey: ['signals'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

// Signal 기각 훅
export function useDismissSignal() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ signalId, reason }: { signalId: string; reason: string }) =>
      dismissSignal(signalId, reason),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['signal', variables.signalId] });
      queryClient.invalidateQueries({ queryKey: ['signals'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

// Dashboard Summary 훅
export function useDashboardSummary() {
  return useQuery<ApiDashboardSummary>({
    queryKey: ['dashboard', 'summary'],
    queryFn: getDashboardSummary,
  });
}
```

### 3.3 SignalDetailPage 수정

`src/pages/SignalDetailPage.tsx` 전체 리팩토링:

1. `mockSignalDetails` 삭제
2. `useSignalDetail(signalId)` 훅 사용
3. 로딩/에러 상태 처리
4. Evidence 목록 API 데이터로 표시
5. "검토 완료" / "기각" 버튼 추가

핵심 변경:
```typescript
import { useSignalDetail, useUpdateSignalStatus, useDismissSignal } from '@/hooks/useApi';

export default function SignalDetailPage() {
  const { signalId } = useParams();
  const { data: signal, isLoading, error } = useSignalDetail(signalId || '');
  const updateStatus = useUpdateSignalStatus();
  const dismissMutation = useDismissSignal();
  
  if (isLoading) return <LoadingSpinner />;
  if (error || !signal) return <NotFound />;
  
  // signal.evidences 사용
  // signal.summary (전체 요약) 사용
  // "검토 완료" 버튼 → updateStatus.mutate({ signalId, status: 'REVIEWED' })
  // "기각" 버튼 → dismissMutation.mutate({ signalId, reason: '...' })
}
```

### 3.4 CorporateDetailPage 수정

`src/pages/CorporateDetailPage.tsx` 수정:

1. `@/data/` import 삭제
2. `useCorporation(corpId)` + `useSignals({ corp_id })` 훅 사용
3. API 데이터로 렌더링

---

## Phase 4: 테스트 및 배포

### 4.1 로컬 테스트

```bash
# Backend 실행
cd backend
uvicorn app.main:app --reload

# 테스트 API 호출
curl http://localhost:8000/api/v1/dashboard/summary
curl http://localhost:8000/api/v1/signals/{signal_id}/detail
```

### 4.2 Railway 재배포

```bash
cd backend
git add .
git commit -m "feat: add signal status management and detail API"
git push
```

### 4.3 Vercel 재배포

```bash
git add .
git commit -m "feat: connect SignalDetailPage to API"
git push
```

---

## 체크리스트

### DB 마이그레이션
- [ ] `migration_v3_signal_status.sql` 파일 생성
- [ ] Supabase SQL Editor에서 실행
- [ ] 기존 데이터 signal_status = 'NEW' 확인

### Backend
- [ ] Signal 모델에 status 컬럼 추가
- [ ] Signal 원본 모델 (rkyc_signal) 추가
- [ ] Evidence 모델 추가
- [ ] Pydantic 스키마 추가
- [ ] GET /signals/{id}/detail 구현
- [ ] PATCH /signals/{id}/status 구현
- [ ] POST /signals/{id}/dismiss 구현
- [ ] GET /dashboard/summary 구현
- [ ] 라우터 등록
- [ ] 로컬 테스트 통과
- [ ] Railway 배포

### Frontend
- [ ] API 클라이언트 함수 추가
- [ ] React Query 훅 추가
- [ ] SignalDetailPage API 연동
- [ ] SignalDetailPage 상태 변경 버튼 추가
- [ ] CorporateDetailPage API 연동 (선택)
- [ ] Vercel 배포

---

## 주의사항

1. **인증은 PRD 2.3에 따라 대회 범위 제외** - 구현하지 않음
2. **pgbouncer 호환** - `statement_cache_size=0` 설정 유지
3. **PRD Guardrails 준수**
   - 단정적 표현 금지 ("반드시", "즉시 조치")
   - 모든 시그널에 evidence 필수
4. **rkyc_signal_index는 조인 금지** - Denormalized 유지
5. **Signal 상태 변경 시 양쪽 테이블(rkyc_signal, rkyc_signal_index) 동기화**

---

## 세션 완료 후 CLAUDE.md 업데이트

세션 종료 전 반드시 CLAUDE.md를 업데이트해주세요:
- 완료 항목 체크
- 다음 세션 작업 명시
- 세션 로그 추가

---

*Phase 1 (DB 마이그레이션)부터 순서대로 진행해주세요.*