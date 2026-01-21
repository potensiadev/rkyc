"""
Debug Script: Analyze why Dongbu Construction signals are missed.
"""
import os
import sys
import json
import asyncio
from datetime import datetime

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.worker.pipelines.signal_extraction import SignalExtractionPipeline
from app.worker.llm.external_llm import ExternalLLMService

def debug_dongbu():
    print("=" * 60)
    print("Debug: Dongbu Construction Signal Detection")
    print("=" * 60)

    # 1. Test External Search
    print("\n[Step 1] Testing External News Search...")
    ext_llm = ExternalLLMService()
    
    query = "동부건설"
    industry = "건설업"
    
    try:
        events = ext_llm.search_external_news(query, industry, days=30)
        print(f"Found {len(events)} events.")
        for e in events:
            print(f"- {e.get('title')} ({e.get('published_at')})")
    except Exception as e:
        print(f"Search failed: {e}")
        events = []

    # 2. Test Signal Extraction with Mocked Snapshot (from User Image)
    print("\n[Step 2] Testing Signal Extraction with Snapshot...")
    
    # Data from User Image
    mock_snapshot = {
        "corp_id": "debug_dongbu",
        "corp_name": "동부건설",
        "industry_name": "건설업",
        "snapshot_json": {
            "financials": {
                "year": 2024,
                "revenue": 1563200000000, 
                "net_income": -160900000000, # Net Loss 160.9bn
                "operating_income": -99500000000,
                "comment": "2023년 순이익 428억원에서 적자전환"
            }
        },
        "external_events": events, # Use found events
        "direct_events": [],
        "industry_events": [],
        "environment_events": []
    }

    pipeline = SignalExtractionPipeline()
    try:
        signals = pipeline.execute(mock_snapshot)
        print(f"\n[Result] Extracted {len(signals)} signals.")
        for s in signals:
            print(f"\n[Signal] {s.get('title')}")
            print(f"Type: {s.get('signal_type')} / {s.get('event_type')}")
            print(f"Impact: {s.get('impact_direction')} / {s.get('impact_strength')}")
            print(f"Summary: {s.get('summary')}")
    except Exception as e:
        print(f"Extraction failed: {e}")

if __name__ == "__main__":
    debug_dongbu()
