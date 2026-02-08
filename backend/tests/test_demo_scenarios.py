"""
Demo Scenario Tests - PRD v2.0 Hackathon Edition

시연 시나리오 자동화 테스트

Run with:
    pytest backend/tests/test_demo_scenarios.py -v

Requirements:
    - Backend API running
    - Database with seed data
    - Worker running (for real analysis)
"""

import os
import re
import json
import time
import pytest
import httpx
from typing import Optional

# =============================================================================
# Configuration
# =============================================================================

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_V1 = f"{API_BASE_URL}/api/v1"

# 9개 시드 기업 (DART 조회 가능 기업만)
SEED_CORPS = {
    # 기존 4개
    "8001-3719240": {"name": "엠케이전자", "min_signals": 3},
    "8000-7647330": {"name": "동부건설", "min_signals": 3},
    "4301-3456789": {"name": "삼성전자", "min_signals": 4},
    "6701-4567890": {"name": "휴림로봇", "min_signals": 3},
    # 신규 5개 (소규모)
    "9001-0000001": {"name": "크라우드웍스", "min_signals": 2},
    "9001-0000002": {"name": "이엘피", "min_signals": 2},
    "9001-0000003": {"name": "팬엔터테인먼트", "min_signals": 2},
    "9001-0000004": {"name": "대한과학", "min_signals": 2},
    "9001-0000005": {"name": "파이오링크", "min_signals": 2},
}

# 의심스러운 수치 패턴 (Hallucination 가능성)
SUSPICIOUS_PATTERNS = [
    r"8[0-9]%\s*(감소|하락|축소)",   # 80%대 급감
    r"9[0-9]%\s*(감소|하락|축소)",   # 90%대 급감
    r"[5-9][0-9]%\s*(증가|상승|성장)",  # 50%+ 급증
]


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def api_client():
    """HTTP client for API calls"""
    return httpx.Client(base_url=API_V1, timeout=60.0)


# =============================================================================
# Helper Functions
# =============================================================================

def check_no_hallucinated_numbers(data: dict) -> list[str]:
    """
    허위 수치 검증

    Returns:
        list of warning messages
    """
    warnings = []
    text = json.dumps(data, ensure_ascii=False)

    for pattern in SUSPICIOUS_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            warnings.append(f"의심 수치 패턴 발견: {pattern} -> {matches}")

    return warnings


def wait_for_job(client: httpx.Client, job_id: str, max_wait: int = 60) -> dict:
    """
    Job 완료 대기

    Args:
        client: HTTP client
        job_id: Job ID
        max_wait: 최대 대기 시간 (초)

    Returns:
        Job status response
    """
    start = time.time()
    while time.time() - start < max_wait:
        response = client.get(f"/jobs/{job_id}")
        if response.status_code == 200:
            job = response.json()
            status = job.get("status")
            if status in ["DONE", "FAILED", "ERROR"]:
                return job
        time.sleep(2)

    return {"status": "TIMEOUT", "job_id": job_id}


# =============================================================================
# Test Cases
# =============================================================================

class TestSystemHealth:
    """시스템 상태 확인"""

    def test_api_health(self, api_client):
        """API 서버 응답 확인"""
        response = api_client.get("/../../health")
        assert response.status_code == 200

    def test_corporations_exist(self, api_client):
        """시드 기업 존재 확인"""
        response = api_client.get("/corporations")
        assert response.status_code == 200

        corps = response.json()
        corp_ids = {c["corp_id"] for c in corps}

        for corp_id in SEED_CORPS.keys():
            assert corp_id in corp_ids, f"Missing seed corp: {corp_id}"


class TestSignalCount:
    """시그널 수 확인 테스트"""

    @pytest.mark.parametrize("corp_id,config", SEED_CORPS.items())
    def test_minimum_signals_exist(self, api_client, corp_id, config):
        """각 기업별 최소 시그널 수 확인"""
        response = api_client.get(f"/signals", params={"corp_id": corp_id})
        assert response.status_code == 200

        signals = response.json()
        signal_count = len(signals) if isinstance(signals, list) else signals.get("total", 0)

        assert signal_count >= config["min_signals"], (
            f"{config['name']} ({corp_id}): "
            f"시그널 부족 ({signal_count} < {config['min_signals']})"
        )


class TestSignalQuality:
    """시그널 품질 확인 테스트"""

    @pytest.mark.parametrize("corp_id,config", SEED_CORPS.items())
    def test_no_hallucinated_numbers(self, api_client, corp_id, config):
        """허위 수치 없음 확인"""
        response = api_client.get(f"/signals", params={"corp_id": corp_id})
        assert response.status_code == 200

        signals = response.json()
        if isinstance(signals, dict):
            signals = signals.get("signals", [])

        warnings = check_no_hallucinated_numbers({"signals": signals})
        assert len(warnings) == 0, (
            f"{config['name']} ({corp_id}): {warnings}"
        )

    @pytest.mark.parametrize("corp_id,config", SEED_CORPS.items())
    def test_all_signals_have_evidence(self, api_client, corp_id, config):
        """모든 시그널에 Evidence 존재 확인"""
        response = api_client.get(f"/signals", params={"corp_id": corp_id})
        assert response.status_code == 200

        signals = response.json()
        if isinstance(signals, dict):
            signals = signals.get("signals", [])

        for signal in signals:
            # 상세 조회로 evidence 확인
            signal_id = signal.get("id") or signal.get("signal_id")
            if signal_id:
                detail_response = api_client.get(f"/signals/{signal_id}/detail")
                if detail_response.status_code == 200:
                    detail = detail_response.json()
                    evidence = detail.get("evidence", [])
                    assert len(evidence) > 0, (
                        f"{config['name']}: Evidence 없음 - {signal.get('title', '')[:30]}"
                    )


class TestDemoScenarios:
    """시연 시나리오 테스트"""

    def test_scenario_1_mkelectronics(self, api_client):
        """시나리오 1: 엠케이전자 분석"""
        corp_id = "8001-3719240"
        config = SEED_CORPS[corp_id]

        # 시그널 조회
        response = api_client.get(f"/signals", params={"corp_id": corp_id})
        assert response.status_code == 200

        signals = response.json()
        signal_count = len(signals) if isinstance(signals, list) else signals.get("total", 0)

        # 최소 시그널 수 확인
        assert signal_count >= config["min_signals"], (
            f"시나리오 1 실패: {config['name']} 시그널 부족"
        )

        # 허위 수치 확인
        warnings = check_no_hallucinated_numbers({"signals": signals})
        assert len(warnings) == 0, f"시나리오 1 실패: {warnings}"

    def test_scenario_2_dongbu(self, api_client):
        """시나리오 2: 동부건설 분석"""
        corp_id = "8000-7647330"
        config = SEED_CORPS[corp_id]

        # 시그널 조회
        response = api_client.get(f"/signals", params={"corp_id": corp_id})
        assert response.status_code == 200

        signals = response.json()
        signal_count = len(signals) if isinstance(signals, list) else signals.get("total", 0)

        # 최소 시그널 수 확인
        assert signal_count >= config["min_signals"], (
            f"시나리오 2 실패: {config['name']} 시그널 부족"
        )

        # 허위 수치 확인
        warnings = check_no_hallucinated_numbers({"signals": signals})
        assert len(warnings) == 0, f"시나리오 2 실패: {warnings}"

    def test_scenario_3_signal_detail(self, api_client):
        """시나리오 3: 시그널 상세 확인"""
        # 첫 번째 시그널 조회
        response = api_client.get("/signals")
        assert response.status_code == 200

        signals = response.json()
        if isinstance(signals, dict):
            signals = signals.get("signals", [])

        assert len(signals) > 0, "시나리오 3 실패: 시그널 없음"

        # 첫 번째 시그널 상세 조회
        first_signal = signals[0]
        signal_id = first_signal.get("id") or first_signal.get("signal_id")

        if signal_id:
            detail_response = api_client.get(f"/signals/{signal_id}/detail")
            assert detail_response.status_code == 200

            detail = detail_response.json()
            assert detail.get("evidence"), "시나리오 3 실패: Evidence 없음"
            assert detail.get("summary"), "시나리오 3 실패: Summary 없음"


class TestFullAnalysisCycle:
    """전체 분석 사이클 테스트 (Worker 필요)"""

    @pytest.mark.skip(reason="Worker 실행 필요 - 시연 전 수동 실행")
    def test_trigger_and_complete_analysis(self, api_client):
        """분석 트리거 및 완료 확인"""
        corp_id = "8001-3719240"  # 엠케이전자

        # 분석 트리거
        response = api_client.post(
            "/jobs/analyze/run",
            json={"corp_id": corp_id}
        )
        assert response.status_code == 200

        job = response.json()
        job_id = job.get("job_id")
        assert job_id, "Job ID 없음"

        # 완료 대기
        result = wait_for_job(api_client, job_id, max_wait=60)
        assert result["status"] == "DONE", f"분석 실패: {result}"

        # 시그널 확인
        signals_response = api_client.get(f"/signals", params={"corp_id": corp_id})
        assert signals_response.status_code == 200

        signals = signals_response.json()
        signal_count = len(signals) if isinstance(signals, list) else signals.get("total", 0)
        assert signal_count >= 3, f"분석 후 시그널 부족: {signal_count}"


# =============================================================================
# Pre-Demo Checklist
# =============================================================================

class TestPreDemoChecklist:
    """시연 전 체크리스트"""

    def test_checklist_complete(self, api_client):
        """전체 체크리스트 실행"""
        issues = []

        # 1. API 응답
        try:
            response = api_client.get("/../../health")
            if response.status_code != 200:
                issues.append("API 서버 비정상")
        except Exception as e:
            issues.append(f"API 연결 실패: {e}")

        # 2. 시드 기업 확인
        try:
            response = api_client.get("/corporations")
            if response.status_code == 200:
                corps = response.json()
                corp_ids = {c["corp_id"] for c in corps}
                missing = set(SEED_CORPS.keys()) - corp_ids
                if missing:
                    issues.append(f"누락된 시드 기업: {missing}")
        except Exception as e:
            issues.append(f"기업 조회 실패: {e}")

        # 3. 각 기업 시그널 확인
        for corp_id, config in SEED_CORPS.items():
            try:
                response = api_client.get(f"/signals", params={"corp_id": corp_id})
                if response.status_code == 200:
                    signals = response.json()
                    count = len(signals) if isinstance(signals, list) else signals.get("total", 0)
                    if count < config["min_signals"]:
                        issues.append(
                            f"{config['name']}: 시그널 부족 ({count} < {config['min_signals']})"
                        )

                    # 허위 수치 확인
                    warnings = check_no_hallucinated_numbers({"signals": signals})
                    if warnings:
                        issues.extend([f"{config['name']}: {w}" for w in warnings])
            except Exception as e:
                issues.append(f"{config['name']}: 조회 실패 - {e}")

        # 결과
        if issues:
            pytest.fail(
                "시연 전 체크리스트 실패:\n" + "\n".join(f"  - {i}" for i in issues)
            )


# =============================================================================
# Quick Smoke Test
# =============================================================================

def test_smoke():
    """빠른 스모크 테스트"""
    client = httpx.Client(base_url=API_V1, timeout=10.0)

    try:
        # API 응답
        response = client.get("/../../health")
        assert response.status_code == 200, "API 비정상"

        # 시그널 목록
        response = client.get("/signals")
        assert response.status_code == 200, "시그널 조회 실패"

        signals = response.json()
        count = len(signals) if isinstance(signals, list) else signals.get("total", 0)
        assert count > 0, "시그널 없음"

        print(f"Smoke test passed: {count} signals found")

    finally:
        client.close()


if __name__ == "__main__":
    # 직접 실행 시 스모크 테스트
    test_smoke()
