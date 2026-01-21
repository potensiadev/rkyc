# PRD: Corp Profile Bug Fixes & Improvements

**Version**: 1.0
**Date**: 2026-01-21
**Authors**: Senior PM + Senior Engineer Code Review
**Status**: Ready for Implementation

---

## Executive Summary

QA 팀에서 식별한 9개의 이슈(P0 3개, P1 3개, P2 3개)에 대한 해결 방안을 정의합니다.
이 PRD는 코드 리뷰 결과를 바탕으로 각 이슈의 원인, 해결책, 리스크를 상세히 기술합니다.

**Production Readiness**: 현재 55% → 목표 90%

---

## Issue Summary

| Priority | Issue ID | Title | Effort | Risk |
|----------|----------|-------|--------|------|
| 🔴 P0 | P0-1 | SupplyChainSchema single_source_risk 타입 불일치 | 2h | Low |
| 🔴 P0 | P0-2 | NULL confidence 표시 규칙 누락 | 4h | Medium |
| 🔴 P0 | P0-3 | JSON 이중 직렬화 위험 | 2h | High |
| 🟠 P1 | P1-1 | Orchestrator 캐시 히트 시 consensus_metadata=None 에러 | 3h | Medium |
| 🟠 P1 | P1-2 | expires_at NULL 처리 누락 | 2h | Low |
| 🟠 P1 | P1-3 | datetime "Z" suffix 파싱 미지원 | 1h | Low |
| 🟡 P2 | P2-1 | Array JSONB 캐스팅 불일치 | 2h | Low |
| 🟡 P2 | P2-2 | Profile TTL 무한 연장 문제 | 4h | Medium |
| 🟡 P2 | P2-3 | Frontend 프로필 에러 fallback 메시지 누락 | 2h | Low |

---

## P0-1: SupplyChainSchema single_source_risk 타입 불일치

### Problem Definition

**증상**: Frontend에서 `single_source_risk`를 배열로 처리하지만, LLM 추출 프롬프트에서는 boolean으로 정의됨.

**영향**:
- Runtime 타입 에러 발생 가능
- 데이터 불일치로 인한 UI 렌더링 실패

### Root Cause Analysis

**파일 1: Backend Schema** (`backend/app/schemas/profile.py:76`)
```python
class SupplyChainSchema(BaseModel):
    single_source_risk: list[str] = Field(default_factory=list)  # ✅ list[str]
```

**파일 2: LLM Extraction Prompt** (`backend/app/worker/pipelines/corp_profiling.py:388-390`)
```python
"supply_chain": {{
    "value": {{
        ...
        "single_source_risk": "boolean (단일 조달처 위험 여부)",  # ❌ boolean으로 정의
```

**파일 3: Frontend** (`src/pages/CorporateDetailPage.tsx:477-489`)
```tsx
{profile.supply_chain.single_source_risk.map((item, i) => (  // ✅ array 처리
    <span key={i}>{item}</span>
))}
```

### Proposed Solution

**Option A (권장)**: LLM 프롬프트를 `list[str]` 형식으로 수정

```python
# corp_profiling.py 수정
"supply_chain": {{
    "value": {{
        "key_suppliers": ["공급사1", "공급사2"],
        "supplier_countries": {{"국가명": 비중(%)}},
        "single_source_risk": ["단일 조달처 품목1", "단일 조달처 품목2"],  # 변경
        "raw_material_import_ratio": "integer 0-100 (원자재 수입 비율)"
    }} 또는 null,
```

**Option B**: boolean이 들어올 경우 변환 로직 추가

```python
# profiles.py의 _parse_supply_chain() 수정
def _parse_supply_chain(data: dict | None) -> SupplyChainSchema:
    if not data:
        return SupplyChainSchema()

    # single_source_risk 타입 정규화
    single_source_risk = data.get("single_source_risk", [])
    if isinstance(single_source_risk, bool):
        single_source_risk = ["단일 조달처 위험 있음"] if single_source_risk else []
    elif isinstance(single_source_risk, str):
        single_source_risk = [single_source_risk] if single_source_risk else []

    return SupplyChainSchema(
        key_suppliers=data.get("key_suppliers", []),
        supplier_countries=data.get("supplier_countries", {}),
        single_source_risk=single_source_risk,
        material_import_ratio_pct=data.get("material_import_ratio_pct"),
    )
```

### Risks & Disadvantages

| Option | Risk | Disadvantage |
|--------|------|--------------|
| A | 기존 LLM 응답 포맷 변경으로 캐시된 프로필과 불일치 | 새 포맷 학습에 LLM 비용 발생 |
| B | 여러 타입 처리로 코드 복잡도 증가 | 정보 손실 가능 (boolean→string 변환 시) |

**권장**: Option A + Option B 동시 적용 (Defensive Programming)

---

## P0-2: NULL Confidence 표시 규칙 누락

### Problem Definition

**증상**: `profile_confidence`가 NULL인 경우 Frontend에서 에러 발생 또는 "undefined" 표시

**영향**:
- 사용자에게 잘못된 정보 표시
- "NONE" 또는 빈 값이 제대로 처리되지 않음

### Root Cause Analysis

**파일 1: Frontend Helper** (`src/pages/CorporateDetailPage.tsx:36-46`)
```tsx
function getConfidenceBadge(confidence: ProfileConfidence | undefined) {
    const map: Record<ProfileConfidence, ...> = {
        HIGH: ..., MED: ..., LOW: ..., NONE: ..., CACHED: ..., STALE: ...
    };
    return map[confidence || 'NONE'] || map.NONE;  // ✅ fallback 존재
}
```

**파일 2: Backend Response** (`backend/app/api/v1/endpoints/profiles.py:180`)
```python
profile_confidence=ConfidenceLevelEnum(row.profile_confidence or "LOW"),  # NULL→"LOW"
```

**파일 3: Profile Values Display** (`src/pages/CorporateDetailPage.tsx:413-415`)
```tsx
{profile.export_ratio_pct !== null && (
    <div>수출 비중: {profile.export_ratio_pct}%</div>
)}
// 문제: !== null 체크만 하면 0도 falsy하게 처리될 수 있음
```

### Proposed Solution

**1. Backend: NULL 값 통일**

```python
# profiles.py 수정
profile_confidence=ConfidenceLevelEnum(row.profile_confidence) if row.profile_confidence else ConfidenceLevelEnum.NONE,
```

**2. Frontend: 안전한 NULL 체크**

```tsx
// CorporateDetailPage.tsx 수정
// !== null 대신 명시적 체크
{typeof profile.export_ratio_pct === 'number' && (
    <div>수출 비중: {profile.export_ratio_pct}%</div>
)}
```

**3. 빈 값 표시 규칙 (PRD 규칙 추가)**

| Field Type | NULL/undefined 표시 |
|------------|---------------------|
| 숫자 | `-` (대시) |
| 문자열 | `-` 또는 생략 |
| 배열 | 섹션 자체 숨김 |
| 객체 | 섹션 자체 숨김 |

### Risks & Disadvantages

| Item | Risk/Disadvantage |
|------|-------------------|
| 타입 체크 로직 | 코드 복잡도 약간 증가 |
| NULL→NONE 변환 | 기존 "LOW" 기본값과 불일치 가능 |
| 빈 섹션 숨김 | 사용자가 데이터 누락을 인지하지 못할 수 있음 |

**권장**: 빈 섹션에 "정보 없음" 메시지 표시 추가

---

## P0-3: JSON 이중 직렬화 위험

### Problem Definition

**증상**: `_save_profile()`에서 이미 직렬화된 JSON 문자열을 다시 `json.dumps()` 처리하면 이중 인코딩 발생

**영향**:
- DB에 `"{\\"key\\": \\"value\\"}"` 형태로 저장
- 읽기 시 파싱 실패

### Root Cause Analysis

**파일: corp_profiling.py:1651-1668**
```python
await db_session.execute(query, {
    ...
    "country_exposure": json.dumps(profile.get("country_exposure", {})),  # ❌ 이미 dict이면 OK, str이면 이중 직렬화
    ...
})
```

**문제 시나리오**:
1. `_build_final_profile()`에서 `country_exposure`가 이미 dict
2. 그러나 캐시에서 가져온 경우 이미 JSON 문자열일 수 있음
3. `json.dumps(json_string)` → 이중 인코딩

### Proposed Solution

**안전한 JSON 직렬화 헬퍼 함수 추가**

```python
# corp_profiling.py 상단에 추가
def safe_json_dumps(value: Any) -> str:
    """JSON 직렬화 (이미 문자열이면 그대로 반환)"""
    if value is None:
        return '{}'
    if isinstance(value, str):
        # 이미 JSON 문자열인지 확인
        try:
            json.loads(value)
            return value  # 유효한 JSON 문자열이면 그대로 반환
        except (json.JSONDecodeError, ValueError):
            pass  # JSON이 아니면 직렬화 진행
    return json.dumps(value, ensure_ascii=False, default=str)
```

**적용**:
```python
await db_session.execute(query, {
    ...
    "country_exposure": safe_json_dumps(profile.get("country_exposure", {})),
    "executives": safe_json_dumps(profile.get("executives", [])),
    "financial_history": safe_json_dumps(profile.get("financial_history", [])),
    "competitors": safe_json_dumps(profile.get("competitors", [])),
    "macro_factors": safe_json_dumps(profile.get("macro_factors", [])),
    "supply_chain": safe_json_dumps(profile.get("supply_chain", {})),
    "overseas_business": safe_json_dumps(profile.get("overseas_business", {})),
    "shareholders": safe_json_dumps(profile.get("shareholders", [])),
    "consensus_metadata": safe_json_dumps(profile.get("consensus_metadata", {})),
    "field_confidences": safe_json_dumps(profile.get("field_confidences", {})),
    "raw_search_result": safe_json_dumps(profile.get("raw_search_result", {})),
    "field_provenance": safe_json_dumps(profile.get("field_provenance", {})),
    ...
})
```

### Risks & Disadvantages

| Item | Risk/Disadvantage |
|------|-------------------|
| 성능 | 매번 JSON 파싱 시도로 약간의 오버헤드 |
| 엣지 케이스 | JSON처럼 보이지만 아닌 문자열 오처리 가능 |
| 복잡도 | 헬퍼 함수 추가로 코드 이해 난이도 증가 |

**권장**: 근본 원인인 데이터 흐름 정규화도 병행 필요

---

## P1-1: Orchestrator 캐시 히트 시 consensus_metadata=None 에러

### Problem Definition

**증상**: 캐시에서 프로필 반환 시 `consensus_metadata`가 None이어서 `to_dict()` 호출 시 AttributeError

**영향**:
- 캐시 히트 경로에서 500 에러 발생
- 캐시 우회로 불필요한 API 호출 증가

### Root Cause Analysis

**파일: corp_profiling.py:1125-1127**
```python
# Add consensus metadata if available
if orchestrator_result.consensus_metadata:
    profile["consensus_metadata"] = orchestrator_result.consensus_metadata.to_dict()
# 문제: else 케이스에서 빈 dict 할당 없음
```

**파일: orchestrator.py (추정 위치)**
```python
# 캐시 히트 시 consensus_metadata를 None으로 설정
return OrchestratorResult(
    profile=cached_profile,
    fallback_layer=FallbackLayer.CACHE,
    consensus_metadata=None,  # ← 여기가 문제
    ...
)
```

### Proposed Solution

**1. _build_final_profile()에 else 분기 추가**

```python
# corp_profiling.py 수정
if orchestrator_result.consensus_metadata:
    profile["consensus_metadata"] = orchestrator_result.consensus_metadata.to_dict()
else:
    # 캐시 히트 또는 메타데이터 없는 경우 기본값
    profile["consensus_metadata"] = {
        "consensus_at": None,
        "perplexity_success": False,
        "gemini_success": False,
        "claude_success": False,
        "total_fields": 0,
        "matched_fields": 0,
        "discrepancy_fields": 0,
        "enriched_fields": 0,
        "overall_confidence": "CACHED" if orchestrator_result.fallback_layer == FallbackLayer.CACHE else "LOW",
        "fallback_layer": orchestrator_result.fallback_layer.value if orchestrator_result.fallback_layer else 0,
        "retry_count": 0,
        "error_messages": [],
    }
```

**2. ConsensusMetadataSchema에 from_dict() 팩토리 메서드 추가**

```python
# profile.py 수정
class ConsensusMetadataSchema(BaseModel):
    ...

    @classmethod
    def empty(cls, fallback_layer: int = 0) -> "ConsensusMetadataSchema":
        """Create empty metadata for cache hits."""
        return cls(
            fallback_layer=fallback_layer,
            overall_confidence="CACHED" if fallback_layer == 0 else "LOW",
        )
```

### Risks & Disadvantages

| Item | Risk/Disadvantage |
|------|-------------------|
| 기본값 하드코딩 | 스키마 변경 시 동기화 필요 |
| CACHED confidence | 사용자가 캐시 데이터임을 인지하지 못할 수 있음 |
| 복잡도 | 조건부 로직 증가 |

---

## P1-2: expires_at NULL 처리 누락

### Problem Definition

**증상**: `expires_at`이 NULL인 경우 `expires_at < NOW()` 비교에서 NULL 반환

**영향**:
- `is_expired` 계산 실패
- Frontend에서 "Invalid Date" 표시

### Root Cause Analysis

**파일: profiles.py:131**
```sql
CASE WHEN expires_at < NOW() THEN true ELSE false END as is_expired
-- NULL < NOW() = NULL, ELSE 분기로 false 반환
-- 문제없어 보이지만...
```

**파일: CorporateDetailPage.tsx:634**
```tsx
<span>만료: {new Date(profile.expires_at).toLocaleDateString('ko-KR')}</span>
// profile.expires_at이 null이면 Invalid Date
```

### Proposed Solution

**1. Backend: COALESCE 사용**

```sql
-- profiles.py SQL 수정
CASE
    WHEN expires_at IS NULL THEN false  -- NULL은 만료되지 않은 것으로 간주
    WHEN expires_at < NOW() THEN true
    ELSE false
END as is_expired
```

**2. Frontend: NULL 체크**

```tsx
// CorporateDetailPage.tsx 수정
{profile.expires_at && (
    <span>만료: {new Date(profile.expires_at).toLocaleDateString('ko-KR')}</span>
)}
```

### Risks & Disadvantages

| Item | Risk/Disadvantage |
|------|-------------------|
| NULL = 미만료 | 영구 캐시로 오해될 수 있음 |
| UI 숨김 | 만료일 정보 부재를 사용자가 인지 못함 |

**권장**: NULL인 경우 "만료일 없음" 표시

---

## P1-3: datetime "Z" suffix 파싱 미지원

### Problem Definition

**증상**: `datetime.fromisoformat()`가 "Z" suffix (UTC 표시)를 지원하지 않음 (Python 3.10 이하)

**영향**:
- `consensus_at` 등 datetime 필드 파싱 실패
- ValueError 발생

### Root Cause Analysis

**파일: profiles.py:79**
```python
consensus_at=datetime.fromisoformat(data["consensus_at"]) if data.get("consensus_at") else None,
# "2026-01-21T12:00:00Z" → ValueError: Invalid isoformat string
```

**Python 버전 이슈**:
- Python 3.11+: `fromisoformat()`이 "Z" 지원
- Python 3.10 이하: "Z"를 "+00:00"으로 치환 필요

### Proposed Solution

**datetime 파싱 헬퍼 함수 추가**

```python
# profiles.py 상단에 추가
def parse_datetime_safely(dt_string: str | None) -> datetime | None:
    """Parse datetime string with "Z" suffix support."""
    if not dt_string:
        return None
    try:
        # "Z"를 "+00:00"으로 치환 (Python 3.10 호환)
        if dt_string.endswith("Z"):
            dt_string = dt_string[:-1] + "+00:00"
        return datetime.fromisoformat(dt_string)
    except (ValueError, TypeError):
        return None
```

**적용**:
```python
consensus_at=parse_datetime_safely(data.get("consensus_at")),
extraction_date=parse_datetime_safely(prov.get("extraction_date")),
```

### Risks & Disadvantages

| Item | Risk/Disadvantage |
|------|-------------------|
| 성능 | 문자열 조작 오버헤드 (미미) |
| 타임존 | UTC 외 타임존 처리 고려 필요 |

---

## P2-1: Array JSONB 캐스팅 불일치

### Problem Definition

**증상**: `key_materials`, `key_customers` 등 배열 필드가 JSONB로 캐스팅되지 않아 타입 불일치

**영향**:
- PostgreSQL 배열 vs JSONB 혼용으로 쿼리 일관성 저하
- 일부 환경에서 타입 에러

### Root Cause Analysis

**파일: corp_profiling.py:1596-1604**
```python
"key_materials": profile.get("key_materials", []),  # 직접 전달
"key_customers": profile.get("key_customers", []),
"overseas_operations": profile.get("overseas_operations", []),
...
"source_urls": profile.get("source_urls", []),
"validation_warnings": profile.get("validation_warnings", []),
```

**DB 스키마** (추정):
```sql
key_materials TEXT[] DEFAULT '{}',  -- PostgreSQL 배열
-- 또는
key_materials JSONB DEFAULT '[]',  -- JSONB
```

### Proposed Solution

**Option A: PostgreSQL 배열 유지**

```python
# 이미 Python list이므로 asyncpg가 자동 변환
"key_materials": profile.get("key_materials", []),  # OK
```

**Option B: JSONB로 통일 (권장)**

```python
"key_materials": json.dumps(profile.get("key_materials", [])),
```

**스키마 확인 필요**:
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'rkyc_corp_profile'
AND column_name IN ('key_materials', 'key_customers', 'overseas_operations');
```

### Risks & Disadvantages

| Option | Risk/Disadvantage |
|--------|-------------------|
| A (배열) | JSONB 연산자(@>, ?) 사용 불가 |
| B (JSONB) | 기존 배열 쿼리 수정 필요 |

---

## P2-2: Profile TTL 무한 연장 문제

### Problem Definition

**증상**: ON CONFLICT UPDATE에서 `expires_at`을 항상 새 값으로 덮어씀

**영향**:
- 프로필 갱신 시 TTL이 항상 리셋되어 stale 데이터 무한 연장 가능
- 강제 갱신 의도와 불일치

### Root Cause Analysis

**파일: corp_profiling.py:1640-1641**
```python
ON CONFLICT (corp_id) DO UPDATE SET
    ...
    fetched_at = EXCLUDED.fetched_at,
    expires_at = EXCLUDED.expires_at,  -- 항상 새 TTL로 덮어씀
```

### Proposed Solution

**조건부 TTL 업데이트**

```sql
-- 새 데이터가 더 신선한 경우에만 TTL 연장
ON CONFLICT (corp_id) DO UPDATE SET
    ...
    fetched_at = CASE
        WHEN EXCLUDED.profile_confidence > rkyc_corp_profile.profile_confidence
             OR rkyc_corp_profile.is_fallback = true
        THEN EXCLUDED.fetched_at
        ELSE rkyc_corp_profile.fetched_at
    END,
    expires_at = CASE
        WHEN EXCLUDED.profile_confidence > rkyc_corp_profile.profile_confidence
             OR rkyc_corp_profile.is_fallback = true
        THEN EXCLUDED.expires_at
        ELSE rkyc_corp_profile.expires_at
    END,
```

**또는 별도 갱신 로직**:

```python
# 강제 갱신(skip_cache=True)인 경우만 TTL 리셋
if skip_cache:
    profile["expires_at"] = (datetime.now(UTC) + timedelta(days=PROFILE_TTL_DAYS)).isoformat()
else:
    # 기존 TTL 유지
    existing = await self._get_cached_profile(corp_id, db_session)
    if existing and not existing.get("is_expired"):
        profile["expires_at"] = existing.get("expires_at")
```

### Risks & Disadvantages

| Item | Risk/Disadvantage |
|------|-------------------|
| 조건부 로직 | 복잡도 증가, SQL 가독성 저하 |
| TTL 미갱신 | 데이터 품질 향상에도 TTL 유지될 수 있음 |

---

## P2-3: Frontend 프로필 에러 fallback 메시지 누락

### Problem Definition

**증상**: 프로필 API 에러 시 사용자에게 명확한 안내 없음

**영향**:
- 사용자가 데이터 없음과 에러를 구분 못함
- "정보 갱신" 버튼 필요성 인지 어려움

### Root Cause Analysis

**파일: CorporateDetailPage.tsx:388-393**
```tsx
) : profileError ? (
    <div className="...">
        <AlertCircle className="..." />
        <span>외부 정보가 아직 생성되지 않았습니다.</span>
        <span>"정보 갱신" 버튼을 클릭하여 생성해 주세요.</span>
    </div>
```

**문제**:
- 404 (미생성)과 500 (서버 에러)를 구분하지 않음
- 에러 유형별 다른 안내 필요

### Proposed Solution

**에러 유형별 메시지 분기**

```tsx
) : profileError ? (
    <div className="flex flex-col items-center justify-center py-8 text-sm text-muted-foreground">
        {profileError.message?.includes('404') ? (
            <>
                <AlertCircle className="w-5 h-5 mb-2 text-orange-500" />
                <span>외부 정보가 아직 생성되지 않았습니다.</span>
                <span className="text-xs mt-1">"정보 갱신" 버튼을 클릭하여 생성해 주세요.</span>
            </>
        ) : (
            <>
                <AlertCircle className="w-5 h-5 mb-2 text-red-500" />
                <span>외부 정보를 불러오는 중 오류가 발생했습니다.</span>
                <span className="text-xs mt-1">잠시 후 다시 시도해 주세요.</span>
                <Button
                    variant="outline"
                    size="sm"
                    className="mt-3"
                    onClick={() => refetchProfile()}
                >
                    다시 시도
                </Button>
            </>
        )}
    </div>
)
```

### Risks & Disadvantages

| Item | Risk/Disadvantage |
|------|-------------------|
| 에러 메시지 파싱 | 에러 구조 변경 시 조건 깨질 수 있음 |
| UX | 사용자에게 기술적 에러 노출 |

**권장**: 에러 응답에 `error_code` 필드 추가하여 분기

---

## Implementation Plan

### Phase 1: Critical Fixes (Day 1)

| Task | Priority | Owner | Est. |
|------|----------|-------|------|
| P0-3: safe_json_dumps() 헬퍼 추가 | P0 | Backend | 2h |
| P0-1: SupplyChainSchema 타입 정규화 | P0 | Backend | 2h |
| P1-3: parse_datetime_safely() 헬퍼 추가 | P1 | Backend | 1h |
| Deploy & Test | - | DevOps | 1h |

### Phase 2: Data Integrity (Day 2)

| Task | Priority | Owner | Est. |
|------|----------|-------|------|
| P0-2: NULL confidence 표시 규칙 | P0 | Full-stack | 4h |
| P1-1: consensus_metadata 기본값 | P1 | Backend | 3h |
| P1-2: expires_at NULL 처리 | P1 | Full-stack | 2h |

### Phase 3: Polish (Day 3)

| Task | Priority | Owner | Est. |
|------|----------|-------|------|
| P2-1: Array JSONB 통일 (스키마 확인 후) | P2 | Backend | 2h |
| P2-2: TTL 연장 로직 개선 | P2 | Backend | 4h |
| P2-3: Frontend 에러 분기 | P2 | Frontend | 2h |
| E2E 테스트 | - | QA | 4h |

---

## Success Metrics

| Metric | Before | Target |
|--------|--------|--------|
| Profile API 500 에러율 | Unknown | < 0.1% |
| 정상 프로필 로드율 | 55% | 95% |
| JSON 파싱 에러 | Unknown | 0 |
| Frontend "Invalid Date" | Unknown | 0 |

---

## Appendix: Test Cases

### P0-1 Test
```python
def test_single_source_risk_type_normalization():
    # boolean 입력
    data = {"single_source_risk": True}
    result = _parse_supply_chain(data)
    assert isinstance(result.single_source_risk, list)

    # string 입력
    data = {"single_source_risk": "반도체 장비"}
    result = _parse_supply_chain(data)
    assert result.single_source_risk == ["반도체 장비"]

    # list 입력 (정상)
    data = {"single_source_risk": ["반도체", "디스플레이"]}
    result = _parse_supply_chain(data)
    assert result.single_source_risk == ["반도체", "디스플레이"]
```

### P0-3 Test
```python
def test_safe_json_dumps():
    # dict → JSON string
    assert safe_json_dumps({"key": "value"}) == '{"key": "value"}'

    # 이미 JSON string → 그대로 반환
    assert safe_json_dumps('{"key": "value"}') == '{"key": "value"}'

    # None → '{}'
    assert safe_json_dumps(None) == '{}'
```

### P1-3 Test
```python
def test_parse_datetime_safely():
    # Z suffix
    dt = parse_datetime_safely("2026-01-21T12:00:00Z")
    assert dt is not None
    assert dt.tzinfo is not None

    # +00:00 format
    dt = parse_datetime_safely("2026-01-21T12:00:00+00:00")
    assert dt is not None

    # None
    assert parse_datetime_safely(None) is None

    # Invalid
    assert parse_datetime_safely("not-a-date") is None
```

---

*Last Updated: 2026-01-21*
