"""
Signal Extraction Pipeline Test
Tests INDUSTRY and DIRECT signal extraction for 엠케이전자
"""
import os
import sys
import asyncio
import json
from datetime import datetime

sys.path.insert(0, '.')
os.chdir('d:/rkyc/backend')

from dotenv import load_dotenv
load_dotenv()


def test_signal_extraction():
    """Test signal extraction using real LLM APIs"""
    from app.worker.pipelines.signal_extraction import SignalExtractionPipeline
    from app.worker.llm.external_llm import ExternalLLMService
    
    print("=" * 60)
    print("Signal Extraction Pipeline Test")
    print("=" * 60)
    
    # 엠케이전자 테스트 컨텍스트 - DIRECT 리스크 시나리오
    # 1. 단기연체 발생 (OVERDUE_FLAG_ON)
    # 2. 신용등급 하락 (INTERNAL_RISK_GRADE_CHANGE)
    test_context = {
        "corp_id": "8001-3719240",
        "corp_name": "엠케이전자",
        "corp_reg_no": "134-81-00000",
        "industry_code": "C26",
        "industry_name": "전자부품 제조업",
        "snapshot_version": 2,  # 버전 증가
        "snapshot_json": {
            "credit_rating": {
                "current_grade": "B+",  # 기존 A-에서 하락 가정
                "previous_grade": "A-",
                "change_date": "2026-01-19",
                "reason": "단기 유동성 악화 우려"
            },
            "financials": {
                "total_assets": 140000000000,  # 자산 감소
                "total_debt": 90000000000,     # 부채 증가
                "revenue": 180000000000,       # 매출 감소
                "net_income": -2000000000,     # 적자 전환
                "debt_ratio": 64.2,
            },
            "loan_exposure": {
                "total_credit": 50000000000,
                "overdue_flag": "Y",           # 연체 발생!
                "overdue_amount": 500000000,   # 5억 연체
                "overdue_start_date": "2026-01-18"
            },
            "external_events": [],  # snapshot 내부가 아님
        },
        "external_events": [],  # 루트 레벨에 위치해야 함
    }
    
    print(f"\n[Context]")
    print(f"  corp_name: {test_context['corp_name']}")
    print(f"  industry: {test_context['industry_name']}")
    print(f"  external_events: {len(test_context['external_events'])} events")
    
    # Execute signal extraction
    print(f"\n[Executing Signal Extraction...]")
    
    pipeline = SignalExtractionPipeline()
    
    try:
        signals = pipeline.execute(test_context)
        
        print(f"\n[RESULT] Extracted {len(signals)} signals")
        print("=" * 60)
        
        for i, signal in enumerate(signals, 1):
            print(f"\n--- Signal {i} ---")
            print(f"  signal_type: {signal.get('signal_type')}")
            print(f"  event_type: {signal.get('event_type')}")
            print(f"  impact_direction: {signal.get('impact_direction')}")
            print(f"  impact_strength: {signal.get('impact_strength')}")
            print(f"  confidence: {signal.get('confidence')}")
            print(f"  title: {signal.get('title', 'N/A')[:80]}")
            
            summary = signal.get('summary', '')
            if len(summary) > 150:
                summary = summary[:150] + "..."
            print(f"  summary: {summary}")
            
            evidence = signal.get('evidence', [])
            print(f"  evidence_count: {len(evidence)}")
        
        # Categorize by signal_type
        print("\n" + "=" * 60)
        print("[Signal Type Summary]")
        type_counts = {}
        for s in signals:
            st = s.get('signal_type', 'UNKNOWN')
            type_counts[st] = type_counts.get(st, 0) + 1
        
        for st, count in type_counts.items():
            print(f"  {st}: {count}")
            
        return signals
        
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_external_news_search():
    """Test external news search using Perplexity"""
    from app.worker.llm.external_llm import ExternalLLMService
    
    print("\n" + "=" * 60)
    print("External News Search Test (Perplexity)")
    print("=" * 60)
    
    external_llm = ExternalLLMService()
    
    try:
        print("\n[Searching news for: 엠케이전자 반도체 소재]")
        events = external_llm.search_external_news(
            query="엠케이전자 반도체 소재 본딩와이어",
            industry_name="전자부품 제조업",
            days=30,
        )
        
        print(f"\n[RESULT] Found {len(events)} events")
        
        for i, event in enumerate(events[:5], 1):  # Show first 5
            print(f"\n--- Event {i} ---")
            print(f"  title: {event.get('title', 'N/A')[:80]}")
            print(f"  date: {event.get('date', 'N/A')}")
            print(f"  source: {event.get('source', 'N/A')}")
            
            summary = event.get('summary', '')
            if len(summary) > 100:
                summary = summary[:100] + "..."
            print(f"  summary: {summary}")
            
        return events
        
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return []


if __name__ == "__main__":
    print("=" * 60)
    print("rKYC Signal Pipeline Test")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Test 1: External news search
    events = test_external_news_search()
    
    # Test 2: Signal extraction
    signals = test_signal_extraction()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
