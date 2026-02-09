"""
Hackathon Configuration - PRD v2.0 (Hackathon Edition)

4개 시드 기업 맞춤 튜닝 및 해커톤 모드 설정
(DART API에서 100% Fact 데이터로 검증된 기업만 포함)

시드 기업 목록 (DART 공시 기반):
- 엠케이전자 (8001-3719240) - dart_corp_code: 00121686
- 동부건설 (8000-7647330) - dart_corp_code: 00115612
- 삼성전자 (4301-3456789) - dart_corp_code: 00126380
- 휴림로봇 (6701-4567890) - dart_corp_code: 00540429

Features:
- CORP_SENSITIVITY_CONFIG: 기업별 민감도 설정
- HACKATHON_MODE: 최소 시그널 보장 (Recall 95%)
- Fallback 시그널 생성 로직
"""

import os
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Hackathon Mode Configuration
# =============================================================================

class SignalGenerationMode(Enum):
    PRODUCTION = "production"   # Recall 85%, Precision 우선
    HACKATHON = "hackathon"     # Recall 95%, 데이터 풍부 우선


# 환경 변수로 제어 (기본값: hackathon)
SIGNAL_MODE = SignalGenerationMode(
    os.getenv("SIGNAL_MODE", "hackathon")
)


def get_generation_config() -> dict:
    """모드별 설정 반환"""

    if SIGNAL_MODE == SignalGenerationMode.HACKATHON:
        return {
            "min_confidence": "LOW",           # LOW도 허용
            "allow_monitoring_signals": True,  # "모니터링 권고" 시그널 허용
            "empty_result_fallback": True,     # 빈 결과 시 Fallback 시그널 생성
            "max_signals_per_corp": 10,        # 충분한 시그널
            "min_signals_per_corp": 3,         # 최소 보장
            "recall_target": 0.95,             # 95% Recall 목표
        }
    else:
        return {
            "min_confidence": "MED",           # MED 이상만
            "allow_monitoring_signals": False, # 구체적 시그널만
            "empty_result_fallback": False,    # 없으면 없음
            "max_signals_per_corp": 5,
            "min_signals_per_corp": 0,
            "recall_target": 0.85,             # 85% Recall
        }


def is_hackathon_mode() -> bool:
    """해커톤 모드인지 확인"""
    return SIGNAL_MODE == SignalGenerationMode.HACKATHON


# =============================================================================
# 4개 시드 기업 민감도 설정 (DART API 검증됨)
# =============================================================================

CORP_SENSITIVITY_CONFIG = {
    # =========================================================================
    # 엠케이전자 (8001-3719240) - 반도체/전자부품
    # DART: 00121686, 코스닥 상장, 설립 1982-12-16
    # =========================================================================
    "8001-3719240": {
        "corp_name": "엠케이전자",
        "dart_corp_code": "00121686",
        "industry_code": "C26",
        "industry_name": "반도체 제조업",
        "corp_class": "K",  # 코스닥
        "sensitivity": {
            "수출규제": "HIGH",      # 반도체 수출 규제 민감
            "환율변동": "HIGH",      # 수출 비중 높음
            "원자재가격": "MED",     # 웨이퍼, 가스 등
            "금리정책": "LOW",
            "공급망정책": "HIGH",    # 반도체 공급망
            "무역분쟁": "HIGH",      # 미중 갈등
            "기술정책": "HIGH",      # 반도체 정책
        },
        "expected_signal_types": ["DIRECT", "INDUSTRY", "ENVIRONMENT"],
        "min_signals": 3,
        "max_signals": 6,
        "environment_queries": [
            "반도체 수출 규제 정책 2026",
            "원달러 환율 반도체 영향 2026",
            "미중 반도체 분쟁 한국 기업 영향 2026",
        ],
    },

    # =========================================================================
    # 동부건설 (8000-7647330) - 건설
    # DART: 00115612, 유가증권 상장, 설립 1969-01-24
    # =========================================================================
    "8000-7647330": {
        "corp_name": "동부건설",
        "dart_corp_code": "00115612",
        "industry_code": "F41",
        "industry_name": "건설업",
        "corp_class": "Y",  # 유가증권
        "sensitivity": {
            "금리정책": "HIGH",      # 건설 금융 민감
            "부동산정책": "HIGH",    # 건설 수요
            "환율변동": "LOW",
            "원자재가격": "MED",     # 철강, 시멘트
            "공급망정책": "MED",
        },
        "expected_signal_types": ["DIRECT", "INDUSTRY"],
        "min_signals": 3,
        "max_signals": 5,
        "environment_queries": [
            "한국은행 기준금리 건설업 영향 2026",
            "부동산 정책 건설사 영향 2026",
            "건설 원자재 가격 동향 2026",
        ],
    },

    # =========================================================================
    # 삼성전자 (4301-3456789) - 전자
    # DART: 00126380, 유가증권 상장, 설립 1969-01-13
    # =========================================================================
    "4301-3456789": {
        "corp_name": "삼성전자",
        "dart_corp_code": "00126380",
        "industry_code": "C21",
        "industry_name": "전자부품 제조업",
        "corp_class": "Y",  # 유가증권
        "sensitivity": {
            "무역분쟁": "HIGH",      # 미중 갈등
            "수출규제": "HIGH",      # 반도체 규제
            "환율변동": "HIGH",      # 글로벌 매출
            "기술정책": "HIGH",      # AI, 반도체 정책
            "공급망정책": "HIGH",
        },
        "expected_signal_types": ["DIRECT", "INDUSTRY", "ENVIRONMENT"],
        "min_signals": 4,
        "max_signals": 7,
        "environment_queries": [
            "미중 무역 분쟁 전자업체 영향 2026",
            "AI 반도체 정책 한국 기업 2026",
            "전자부품 수출 규제 동향 2026",
        ],
    },

    # =========================================================================
    # 휴림로봇 (6701-4567890) - 에너지/로봇
    # DART: 00540429, 코스닥 상장, 설립 1998-11-29
    # =========================================================================
    "6701-4567890": {
        "corp_name": "휴림로봇",
        "dart_corp_code": "00540429",
        "industry_code": "D35",
        "industry_name": "에너지 산업",
        "corp_class": "K",  # 코스닥
        "sensitivity": {
            "에너지정책": "HIGH",    # 탄소중립, 재생에너지
            "환경규제": "HIGH",      # ESG 규제
            "기술정책": "MED",       # 로봇/자동화
            "환율변동": "LOW",
        },
        "expected_signal_types": ["DIRECT", "ENVIRONMENT"],
        "min_signals": 3,
        "max_signals": 5,
        "environment_queries": [
            "탄소중립 에너지 정책 2026",
            "ESG 환경 규제 에너지업 2026",
            "재생에너지 지원 정책 2026",
        ],
    },

}


def get_corp_sensitivity(corp_id: str) -> Optional[dict]:
    """기업별 민감도 설정 반환"""
    return CORP_SENSITIVITY_CONFIG.get(corp_id)


def get_environment_queries(corp_id: str) -> list[str]:
    """기업별 ENVIRONMENT 검색 쿼리 반환"""
    config = CORP_SENSITIVITY_CONFIG.get(corp_id, {})
    return config.get("environment_queries", [])


def get_high_sensitivity_topics(corp_id: str) -> list[str]:
    """HIGH 민감도 토픽 목록 반환"""
    config = CORP_SENSITIVITY_CONFIG.get(corp_id, {})
    sensitivity = config.get("sensitivity", {})
    return [topic for topic, level in sensitivity.items() if level == "HIGH"]


# =============================================================================
# Fallback Signal Templates
# =============================================================================

def create_kyc_monitoring_signal(corp_id: str, context: dict) -> dict:
    """KYC 모니터링 시그널 생성 (Fallback)"""

    corp_name = context.get("corp_name", "해당 기업")
    config = CORP_SENSITIVITY_CONFIG.get(corp_id, {})

    return {
        "signal_type": "DIRECT",
        "event_type": "KYC_REFRESH",
        "impact_direction": "NEUTRAL",
        "impact_strength": "LOW",
        "confidence": "LOW",
        "title": f"{corp_name} KYC 정보 점검 권고",
        "summary": f"{corp_name}의 KYC 정보 정기 점검 시점입니다. 최신 재무/비재무 정보 확인을 권고합니다.",
        "evidence": [{
            "evidence_type": "INTERNAL_FIELD",
            "ref_type": "SNAPSHOT_KEYPATH",
            "ref_value": "/corp/kyc_status/last_kyc_updated",
            "snippet": "KYC 정보 정기 점검",
        }],
        "is_fallback": True,
        "fallback_reason": "minimum_signal_guarantee",
    }


def create_industry_monitoring_signal(corp_id: str, context: dict) -> dict:
    """업종 모니터링 시그널 생성 (Fallback)"""

    corp_name = context.get("corp_name", "해당 기업")
    industry_name = context.get("industry_name", "해당 업종")
    config = CORP_SENSITIVITY_CONFIG.get(corp_id, {})

    return {
        "signal_type": "INDUSTRY",
        "event_type": "INDUSTRY_SHOCK",
        "impact_direction": "NEUTRAL",
        "impact_strength": "LOW",
        "confidence": "LOW",
        "title": f"{industry_name} 업황 모니터링",
        "summary": f"{industry_name} 업종 동향 지속 모니터링이 필요합니다. {corp_name}은 해당 업종 주요 기업으로 업황 변화 주시 권고.",
        "evidence": [{
            "evidence_type": "EXTERNAL",
            "ref_type": "URL",
            "ref_value": "industry_monitoring",
            "snippet": f"{industry_name} 업종 동향",
        }],
        "is_fallback": True,
        "fallback_reason": "minimum_signal_guarantee",
    }


def create_policy_monitoring_signal(
    corp_id: str,
    topic: str,
    context: dict
) -> dict:
    """정책 모니터링 시그널 생성 (Fallback)"""

    corp_name = context.get("corp_name", "해당 기업")
    industry_name = context.get("industry_name", "해당 업종")
    config = CORP_SENSITIVITY_CONFIG.get(corp_id, {})

    topic_descriptions = {
        "수출규제": "수출 규제 정책",
        "환율변동": "환율 정책",
        "원자재가격": "원자재 관련 정책",
        "금리정책": "금리 정책",
        "부동산정책": "부동산 정책",
        "식량정책": "농업/식량 정책",
        "공급망정책": "공급망 정책",
        "무역분쟁": "무역 정책",
        "기술정책": "기술/산업 정책",
        "에너지정책": "에너지 정책",
        "환경규제": "환경/ESG 규제",
    }

    policy_desc = topic_descriptions.get(topic, f"{topic} 정책")

    return {
        "signal_type": "ENVIRONMENT",
        "event_type": "POLICY_REGULATION_CHANGE",
        "impact_direction": "NEUTRAL",
        "impact_strength": "LOW",
        "confidence": "LOW",
        "title": f"{policy_desc} 동향 모니터링",
        "summary": f"{policy_desc} 관련 변화 모니터링이 필요합니다. {corp_name}({industry_name})은 해당 정책에 민감도가 높아 지속적인 추적을 권고합니다.",
        "evidence": [{
            "evidence_type": "EXTERNAL",
            "ref_type": "URL",
            "ref_value": "policy_monitoring",
            "snippet": f"{policy_desc} 동향 모니터링",
        }],
        "is_fallback": True,
        "fallback_reason": "minimum_signal_guarantee",
    }


def ensure_minimum_signals(
    signals: list[dict],
    corp_id: str,
    context: dict
) -> list[dict]:
    """
    해커톤 모드: 최소 시그널 수 보장

    빈 화면 방지를 위해 최소 3개 시그널 생성
    """

    if not is_hackathon_mode():
        return signals

    config = get_generation_config()
    min_signals = config.get("min_signals_per_corp", 0)

    # 기업별 설정에서 min_signals 가져오기
    corp_config = CORP_SENSITIVITY_CONFIG.get(corp_id, {})
    corp_min = corp_config.get("min_signals", min_signals)

    if len(signals) >= corp_min:
        return signals

    logger.info(
        f"[HACKATHON MODE] Ensuring minimum signals: "
        f"current={len(signals)}, min={corp_min}, corp_id={corp_id}"
    )

    fallback_signals = []
    existing_types = {s["signal_type"] for s in signals}

    # 1. DIRECT 시그널이 없으면 KYC 모니터링 추가
    if "DIRECT" not in existing_types:
        fallback_signals.append(
            create_kyc_monitoring_signal(corp_id, context)
        )

    # 2. INDUSTRY 시그널이 없으면 업종 모니터링 추가
    if "INDUSTRY" not in existing_types:
        expected_types = corp_config.get("expected_signal_types", [])
        if "INDUSTRY" in expected_types or not expected_types:
            fallback_signals.append(
                create_industry_monitoring_signal(corp_id, context)
            )

    # 3. ENVIRONMENT 시그널이 없으면 정책 모니터링 추가
    if "ENVIRONMENT" not in existing_types:
        high_topics = get_high_sensitivity_topics(corp_id)
        if high_topics:
            fallback_signals.append(
                create_policy_monitoring_signal(corp_id, high_topics[0], context)
            )

    # 필요한 만큼만 추가
    needed = corp_min - len(signals)
    result = signals + fallback_signals[:needed]

    logger.info(
        f"[HACKATHON MODE] Added {len(result) - len(signals)} fallback signals "
        f"for corp_id={corp_id}"
    )

    return result


# =============================================================================
# Demo Scenario Validation
# =============================================================================

def validate_demo_scenario(corp_id: str, signals: list[dict]) -> dict:
    """
    시연 시나리오 검증

    Returns:
        dict with keys:
        - passed: bool
        - issues: list of issue descriptions
    """
    issues = []
    config = CORP_SENSITIVITY_CONFIG.get(corp_id, {})

    if not config:
        issues.append(f"Unknown corp_id: {corp_id}")
        return {"passed": False, "issues": issues}

    corp_name = config.get("corp_name", "Unknown")
    min_signals = config.get("min_signals", 3)
    expected_types = set(config.get("expected_signal_types", []))

    # 1. 최소 시그널 수 확인
    if len(signals) < min_signals:
        issues.append(
            f"{corp_name}: 시그널 부족 ({len(signals)} < {min_signals})"
        )

    # 2. 기대 signal_type 확인
    actual_types = {s.get("signal_type") for s in signals}
    missing_types = expected_types - actual_types
    if missing_types and expected_types:
        issues.append(
            f"{corp_name}: 누락된 signal_type: {missing_types}"
        )

    # 3. Hallucination 패턴 확인
    import re
    suspicious_patterns = [
        r"8[0-9]%\s*(감소|하락|축소)",   # 80%대 급감
        r"9[0-9]%\s*(감소|하락|축소)",   # 90%대 급감
    ]

    for signal in signals:
        summary = signal.get("summary", "")
        title = signal.get("title", "")
        text = f"{title} {summary}"

        for pattern in suspicious_patterns:
            match = re.search(pattern, text)
            if match:
                issues.append(
                    f"{corp_name}: 의심 수치 발견 - '{match.group()}' in '{title[:30]}'"
                )

    # 4. Evidence 존재 확인
    for signal in signals:
        if not signal.get("evidence"):
            issues.append(
                f"{corp_name}: Evidence 없음 - '{signal.get('title', '')[:30]}'"
            )

    return {
        "passed": len(issues) == 0,
        "issues": issues,
    }


def run_all_demo_validations() -> dict:
    """
    모든 시드 기업에 대해 시연 검증 실행

    Note: 실제 signals 데이터가 필요하므로,
    이 함수는 signals 목록을 매개변수로 받는 버전이 필요
    """
    return {
        "corp_ids": list(CORP_SENSITIVITY_CONFIG.keys()),
        "total_corps": len(CORP_SENSITIVITY_CONFIG),
        "message": "Use validate_demo_scenario() with actual signals",
    }
