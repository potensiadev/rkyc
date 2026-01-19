# QA Report: Corp Profiling Pipeline E2E Testing

**Report Date**: 2026-01-19
**QA Engineer**: Senior QA (Banking/SaaS Specialist)
**Test Scope**: PRD-Corp-Profiling-Pipeline.md v1.2
**Test Status**: COMPLETED WITH FINDINGS

---

## Executive Summary

E2E 테스트 38개 케이스 실행 완료. **1개 버그 발견, 1개 deprecation 경고, 1개 기술 부채 확인**.

| Category | Tests | Passed | Failed | Status |
|----------|-------|--------|--------|--------|
| Fallback Cascade | 5 | 5 | 0 | ✅ |
| Consensus Engine | 6 | 5 | **1** | ⚠️ |
| Cache Timing | 4 | 4 | 0 | ✅ |
| Circuit Breaker | 3 | 3 | 0 | ✅ |
| Data Validation | 5 | 5 | 0 | ✅ |
| Timing & Ordering | 3 | 3 | 0 | ✅ |
| Integration | 3 | N/A | N/A | 🔄 (Needs Live DB) |
| Performance | 4 | 4 | 0 | ✅ |
| **Total** | **38** | **37** | **1** | |

---

## 🔴 BUG-001: Korean Compound Stopwords Not Handled (P1)

### Impact
- **Severity**: P1 (Medium-High)
- **Component**: `consensus_engine.py` - `tokenize()` function
- **Risk**: Consensus Engine 정확도 저하, 잘못된 불일치 감지 가능

### Description
`KOREAN_STOPWORDS` 집합이 단일 조사만 포함하고 복합 조사를 포함하지 않음.

**Current KOREAN_STOPWORDS**:
```python
KOREAN_STOPWORDS = {
    "은", "는", "이", "가", "을", "를", "에", "에서", "로", "으로",
    "의", "와", "과", "도", "만", "까지", "부터", "에게", "한테",
    "및", "등", "또는", "그리고", "하지만", "그러나", "따라서",
    "것", "수", "때", "중", "내", "외",
}
```

**Missing Compound Stopwords**:
- `등의` (등+의)
- `을를` (을+를)
- `은는` (은+는)
- `에서는` (에서+는)
- `로부터` (로+부터)
- `이나` (이+나)

### Test Case
```python
def test_tc007_jaccard_stopwords_only(self):
    """TC-007: 불용어만 있는 텍스트 비교"""
    text_a = "의 및 등의 을를 은는"
    text_b = "와 과 에서는 로부터"

    # Expected: Both become empty → similarity 1.0
    # Actual: Compound stopwords remain → similarity 0.0
    score = jaccard_similarity(text_a, text_b)
    assert score == 1.0  # FAILED
```

### Reproduction
```bash
cd backend
pytest tests/test_corp_profiling_e2e.py::TestJaccardSimilarity::test_tc007_jaccard_stopwords_only -v
```

### Fix Request
**파일**: `backend/app/worker/llm/consensus_engine.py` line 15-24

```python
# 변경 전
KOREAN_STOPWORDS = {
    "은", "는", "이", "가", "을", "를", ...
}

# 변경 후
KOREAN_STOPWORDS = {
    # 단일 조사
    "은", "는", "이", "가", "을", "를", "에", "에서", "로", "으로",
    "의", "와", "과", "도", "만", "까지", "부터", "에게", "한테",
    # 복합 조사
    "등의", "을를", "은는", "에서는", "로부터", "이나", "에게는",
    "까지는", "부터는", "만으로", "으로서", "으로써", "에서의",
    # 접속사/부사
    "및", "등", "또는", "그리고", "하지만", "그러나", "따라서",
    # 일반 단어
    "것", "수", "때", "중", "내", "외",
}
```

### CTO Decision Required
- [ ] 복합 조사 목록 확장 범위 결정 (최소 6개 vs 전체 13개)
- [ ] 형태소 분석기 도입 고려 여부 (konlpy, mecab-ko 등)

---

## 🟡 DEPRECATION-001: datetime.utcnow() Usage (P2)

### Impact
- **Severity**: P2 (Medium)
- **Component**: Multiple files
- **Risk**: Python 3.12+ 에서 DeprecationWarning 발생

### Description
Python 3.12부터 `datetime.utcnow()`가 deprecated됨. `datetime.now(datetime.UTC)` 사용 권장.

### Affected Files
1. `backend/app/worker/llm/consensus_engine.py:65`
2. `backend/app/models/profile.py` (server_default)

### Warning Message
```
DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for
removal in a future version. Use datetime.datetime.now(datetime.UTC) instead.
```

### Fix Request
```python
# 변경 전
from datetime import datetime
fetched_at = datetime.utcnow()

# 변경 후
from datetime import datetime, UTC
fetched_at = datetime.now(UTC)
```

### Action
- **바로 수정 가능**: 단순 치환 작업
- **예상 소요**: 30분

---

## 🟢 LIMITATION-001: Country Code Normalization (P3)

### Impact
- **Severity**: P3 (Low)
- **Component**: `compare_values()` in consensus_engine.py
- **Risk**: 국가명 표기 불일치 시 false negative 발생 가능

### Description
국가 코드 정규화 미구현으로 인해 동일 국가가 다른 표기로 인식됨.

### Example
```python
# 동일한 데이터지만 다르게 인식됨
value_a = {"중국": 30, "일본": 25}
value_b = {"CN": 30, "JP": 25}

# Expected: identical (same countries)
# Actual: different (string mismatch)
```

### Recommendation
Phase 2에서 국가코드 정규화 레이어 추가 고려:
- ISO 3166-1 alpha-2/alpha-3 매핑
- 한글/영문 국가명 매핑 테이블

### Action
- 기술 부채로 문서화
- Phase 2 백로그에 추가

---

## Test Execution Details

### Environment
```
Python: 3.11+
pytest: 8.x
OS: Windows 11
Database: Supabase PostgreSQL (mocked for unit tests)
```

### Commands
```bash
# Full test suite
cd backend
pytest tests/test_corp_profiling_e2e.py tests/test_corp_profiling_advanced.py -v

# Specific bug reproduction
pytest tests/test_corp_profiling_e2e.py::TestJaccardSimilarity::test_tc007_jaccard_stopwords_only -v
```

### Test Results Summary
```
test_corp_profiling_e2e.py: 24 passed, 1 failed
test_corp_profiling_advanced.py: 13 passed, 0 failed
Warnings: 7 (all datetime.utcnow deprecation)
```

---

## Circuit Breaker Configuration Verified ✅

PRD v1.2 설정이 코드에 올바르게 반영됨 확인:

| Provider | failure_threshold | cooldown_seconds | Status |
|----------|-------------------|------------------|--------|
| perplexity | 3 | 300 | ✅ Correct |
| gemini | 3 | 300 | ✅ Correct |
| claude | 2 | 600 | ✅ Correct |

---

## Consensus Engine Thresholds Verified ✅

| Threshold | PRD Value | Code Value | Status |
|-----------|-----------|------------|--------|
| Jaccard Similarity | >= 0.7 | 0.7 | ✅ Correct |
| Numeric Tolerance | 10% | 0.1 | ✅ Correct |

---

## Pending Integration Tests (TC-026 ~ TC-028)

실제 DB 연결 필요한 통합 테스트는 Staging 환경에서 추가 검증 필요:

1. **TC-026**: Full Pipeline Happy Path
2. **TC-027**: Cross-table Consistency
3. **TC-028**: Audit Log Completeness

---

## Action Items Summary

| ID | Item | Priority | Owner | ETA |
|----|------|----------|-------|-----|
| BUG-001 | Korean compound stopwords | P1 | Backend | 1-2h |
| DEP-001 | datetime.utcnow() deprecation | P2 | Backend | 30m |
| LIM-001 | Country code normalization | P3 | Backlog | Phase 2 |

---

## Sign-off

**QA Recommendation**: BUG-001 수정 후 Production 배포 진행 권장

**Attachments**:
- `backend/tests/test_corp_profiling_e2e.py`
- `backend/tests/test_corp_profiling_advanced.py`
- `docs/PRD/E2E-Test-Scenarios-Corp-Profiling-Pipeline.md`

---
*Report Generated: 2026-01-19*
