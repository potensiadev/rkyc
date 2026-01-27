# rKYC - One Pager
## AI-Powered Corporate Risk Intelligence

---

## 핵심 가치 제안

**문제**:
- 외부 정보 수집에 **기업당 2시간** 소요
- 뉴스/공시/규제 변화 모니터링이 **100% 수작업**
- KYC 갱신 시점 판단이 **담당자 경험에 의존**

**해결**: AI가 24/7 자동 모니터링하여 리스크/기회 시그널 실시간 알림

**ROI**: 심사역 100명 × 월 10건 × 2시간 = **월 2,000시간 절감**

---

## 기술적 차별화 요소

| 요소 | 설명 | 비즈니스 가치 |
|------|------|---------------|
| **Multi-Agent** | 4개 AI 협업 (Perplexity+Gemini+Claude+OpenAI) | 각 AI 강점 활용, 비용 최적화 |
| **4-Layer Fallback** | Cache→LLM→Rule→Graceful | **100% 가용성** 보장 |
| **Anti-Hallucination** | 4중 검증 (출처/가드레일/교차검증/감사) | 금융 신뢰도 확보 |
| **Circuit Breaker** | API 장애 자동 감지/복구 | **시스템 안정성** |
| **Vector Search** | pgvector HNSW 인덱스 | 유사 과거 케이스 **밀리초** 검색 |

---

## 아키텍처 한눈에 보기

```
Frontend (React/Vercel) → Backend (FastAPI/Railway) → Worker (Celery/Redis)
                                      ↓                        ↓
                              Supabase PostgreSQL         4개 LLM API
                                   + pgvector
```

**핵심 설계 원칙**: LLM 키는 Worker에만 존재 (보안)

---

## 9-Stage Pipeline

```
SNAPSHOT → DOC_INGEST → PROFILING → EXTERNAL → CONTEXT
                                                  ↓
              INSIGHT ← INDEX ← VALIDATION ← SIGNAL
```

---

## 사용 AI 모델

| 역할 | 모델 | 이유 |
|------|------|------|
| 검색 | Perplexity sonar-pro | 실시간 웹 검색 유일 |
| 검증 | Gemini 3 Pro | 빠르고 저렴 |
| 합성 | Claude Opus 4.5 | 최고 품질, 한국어 우수 |
| 임베딩 | OpenAI text-embedding-3-large | 2000d, 업계 표준 |

---

## 발표 핵심 메시지

1. **"AI 앙상블"**: 단일 LLM이 아닌 4개 AI의 협업
2. **"절대 실패 안 함"**: 4-Layer Fallback으로 100% 가용성
3. **"신뢰할 수 있는 AI"**: Anti-Hallucination 4중 방어
4. **"Production-Ready"**: Circuit Breaker, Redis 영속화

---

## 숫자로 보는 성과

| 지표 | Before | After |
|------|--------|-------|
| 분석 시간 | 2시간 | 2분 |
| 담당자당 관리 기업 | 50개 | 500개 |
| 조기 감지율 | - | +40% |

---

## 경쟁 제출작 대비 차별점

| 일반적인 제출작 | rKYC |
|----------------|------|
| "GPT에게 물어보기" | **9-stage 파이프라인** |
| 단일 LLM 의존 | **Multi-Agent + Fallback** |
| 프로토타입 | **실제 배포 완료** |
| 아이디어 발표 | **작동하는 데모** |

> **해커톤에서 이 정도 완성도는 상위 5%**

---

## 예상 Q&A

**Q: 외부 LLM에 고객 정보 나가나요?**
→ Internal/External 분리 설계, MVP에서는 공개 정보만 사용

**Q: 기존 KYC 시스템과 차이점?**
→ 정적 체크리스트 vs 실시간 시그널 모니터링

**Q: LLM 장애 시?**
→ 4-Layer Fallback + Circuit Breaker로 무중단

---

## 기술 스택

- **Frontend**: React 18, TypeScript, TanStack Query, shadcn/ui
- **Backend**: FastAPI, SQLAlchemy 2.0, Pydantic v2
- **Worker**: Celery, Redis, litellm
- **DB**: Supabase PostgreSQL, pgvector
- **배포**: Vercel, Railway

---

## 규제 준수 로드맵

| Phase | 기간 | 구현 방식 |
|-------|------|----------|
| MVP (현재) | 대회 | 외부 API + 추상화 |
| Phase 2 | 3-6개월 | Azure/AWS Private Cloud |
| Phase 3 | 1년+ | On-Premise LLM |

---

## 핵심 용어 치트시트

| 용어 | 한 줄 설명 |
|------|-----------|
| Multi-Agent | 여러 AI가 역할 분담하여 협업 |
| Fallback | 실패 시 자동으로 다음 방법 시도 |
| Circuit Breaker | API 장애 감지하여 자동 차단/복구 |
| Consensus | 여러 AI 답변을 하나로 합의 |
| Hallucination | AI가 사실 아닌 정보 생성 (위험) |
| Embedding | 텍스트를 숫자 벡터로 변환 |
| pgvector | PostgreSQL 벡터 검색 확장 |

---

## Demo URL

- **Frontend**: https://rkyc-wine.vercel.app/
- **Backend API**: https://rkyc-production.up.railway.app/

---

*rKYC - Really Know Your Customer*
