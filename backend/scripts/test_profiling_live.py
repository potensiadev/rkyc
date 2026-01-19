"""
Corp Profiling Pipeline Real LLM Test (Gemini Bypass)
Tests the pipeline with Perplexity + Rule-Based Fallback (skipping Gemini due to rate limit)
"""
import os
import sys
import asyncio
import json

sys.path.insert(0, '.')
os.chdir('d:/rkyc/backend')

from dotenv import load_dotenv
load_dotenv()

async def test_single_corp(corp_id: str, corp_name: str, industry_code: str):
    """Test profiling for a single corporation"""
    from app.worker.pipelines.corp_profiling import CorpProfilingPipeline
    from app.worker.llm.circuit_breaker import get_circuit_breaker_manager
    
    # Bypass Gemini by opening its circuit breaker
    cb_manager = get_circuit_breaker_manager()
    for _ in range(3):
        cb_manager.record_failure("gemini", "Rate limit exceeded - bypassing")
    
    print(f"[INFO] Gemini circuit breaker opened (rate limit bypass)")
    
    pipeline = CorpProfilingPipeline()
    
    print(f"\n{'='*60}")
    print(f"Testing: {corp_name} ({corp_id})")
    print(f"Industry: {industry_code}")
    print(f"{'='*60}")
    
    try:
        result = await pipeline.execute(
            corp_id=corp_id,
            corp_name=corp_name,
            industry_code=industry_code,
        )
        
        print("\n[SUCCESS]")
        print(f"  is_cached: {result.is_cached}")
        print(f"  selected_queries: {result.selected_queries}")
        
        p = result.profile
        print("\n[PROFILE]")
        
        # Business Summary
        bs = p.get('business_summary', 'N/A')
        if bs and len(bs) > 300:
            bs = bs[:300] + "..."
        print(f"  business_summary: {bs}")
        
        # Key fields
        print(f"\n  export_ratio_pct: {p.get('export_ratio_pct')}")
        
        ce = p.get('country_exposure')
        if ce:
            print(f"  country_exposure: {json.dumps(ce, ensure_ascii=False)}")
        else:
            print(f"  country_exposure: None")
            
        km = p.get('key_materials')
        if km:
            print(f"  key_materials: {km[:5] if len(km) > 5 else km}")
        else:
            print(f"  key_materials: []")
            
        kc = p.get('key_customers')
        if kc:
            print(f"  key_customers: {kc[:5] if len(kc) > 5 else kc}")
        else:
            print(f"  key_customers: []")
        
        oo = p.get('overseas_operations')
        print(f"  overseas_operations: {oo if oo else []}")
        
        # Metadata
        print("\n[METADATA]")
        print(f"  profile_confidence: {p.get('profile_confidence')}")
        print(f"  is_fallback: {p.get('is_fallback')}")
        print(f"  extraction_model: {p.get('extraction_model')}")
        
        return True, result
        
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}")
        print(f"  {str(e)[:500]}")
        import traceback
        traceback.print_exc()
        return False, None


async def main():
    print("=" * 60)
    print("Corp Profiling Pipeline - Real LLM API Test")
    print("(Gemini bypassed due to rate limit)")
    print("=" * 60)
    
    # Test with 엠케이전자
    success, result = await test_single_corp(
        "8001-3719240", "엠케이전자", "C26"
    )
    
    print("\n" + "=" * 60)
    print(f"RESULT: {'SUCCESS' if success else 'FAILED'}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
