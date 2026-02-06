"""
Unit tests for Rule-Based Signal Generator

Sprint 5: Internal Snapshot → Deterministic Signal 변환 테스트
"""

import pytest
from datetime import datetime, timedelta

from app.worker.pipelines.signal_agents.rule_based_generator import (
    RuleBasedSignalGenerator,
    get_rule_based_generator,
    reset_rule_based_generator,
)


class TestRuleBasedSignalGenerator:
    """Rule-Based Signal Generator 단위 테스트"""

    def setup_method(self):
        """각 테스트 전 Generator 리셋"""
        reset_rule_based_generator()
        self.generator = get_rule_based_generator()

    # =========================================================================
    # OVERDUE_FLAG_ON 테스트
    # =========================================================================

    def test_overdue_flag_on_detected(self):
        """연체 발생 시 OVERDUE_FLAG_ON 시그널 생성"""
        snapshot = {
            "credit": {
                "loan_summary": {
                    "overdue_flag": True,
                    "overdue_days": 45,
                    "total_exposure_krw": 1_200_000_000,
                    "risk_grade_internal": "고위험",
                }
            }
        }

        signals = self.generator.generate(
            corp_id="8001-3719240",
            corp_name="엠케이전자",
            snapshot=snapshot,
        )

        assert len(signals) == 1
        signal = signals[0]
        assert signal["event_type"] == "OVERDUE_FLAG_ON"
        assert signal["impact_direction"] == "RISK"
        assert signal["impact_strength"] == "HIGH"
        assert signal["confidence"] == "HIGH"
        assert "엠케이전자" in signal["title"]
        assert "45일" in signal["title"]
        assert len(signal["evidence"]) == 1
        assert signal["evidence"][0]["ref_value"] == "/credit/loan_summary/overdue_flag"

    def test_overdue_flag_off_no_signal(self):
        """연체 없으면 시그널 없음"""
        snapshot = {
            "credit": {
                "loan_summary": {
                    "overdue_flag": False,
                    "total_exposure_krw": 1_000_000_000,
                }
            }
        }

        signals = self.generator.generate(
            corp_id="8001-3719240",
            corp_name="엠케이전자",
            snapshot=snapshot,
        )

        # OVERDUE_FLAG_ON 시그널 없음
        overdue_signals = [s for s in signals if s["event_type"] == "OVERDUE_FLAG_ON"]
        assert len(overdue_signals) == 0

    # =========================================================================
    # INTERNAL_RISK_GRADE_CHANGE 테스트
    # =========================================================================

    def test_grade_downgrade_detected(self):
        """등급 하락 시 RISK 시그널 생성"""
        snapshot = {
            "corp": {
                "kyc_status": {
                    "internal_risk_grade": "고위험",  # BB equivalent
                }
            }
        }
        prev_snapshot = {
            "corp": {
                "kyc_status": {
                    "internal_risk_grade": "중위험",  # BBB equivalent
                }
            }
        }

        signals = self.generator.generate(
            corp_id="8001-3719240",
            corp_name="엠케이전자",
            snapshot=snapshot,
            prev_snapshot=prev_snapshot,
        )

        grade_signals = [s for s in signals if s["event_type"] == "INTERNAL_RISK_GRADE_CHANGE"]
        assert len(grade_signals) == 1

        signal = grade_signals[0]
        assert signal["impact_direction"] == "RISK"
        assert "하락" in signal["title"]
        assert "엠케이전자" in signal["title"]

    def test_grade_upgrade_detected(self):
        """등급 상승 시 OPPORTUNITY 시그널 생성"""
        snapshot = {
            "corp": {
                "kyc_status": {
                    "internal_risk_grade": "저위험",  # A equivalent
                }
            }
        }
        prev_snapshot = {
            "corp": {
                "kyc_status": {
                    "internal_risk_grade": "중위험",  # BBB equivalent
                }
            }
        }

        signals = self.generator.generate(
            corp_id="8001-3719240",
            corp_name="엠케이전자",
            snapshot=snapshot,
            prev_snapshot=prev_snapshot,
        )

        grade_signals = [s for s in signals if s["event_type"] == "INTERNAL_RISK_GRADE_CHANGE"]
        assert len(grade_signals) == 1

        signal = grade_signals[0]
        assert signal["impact_direction"] == "OPPORTUNITY"
        assert "상승" in signal["title"]

    def test_grade_no_change_no_signal(self):
        """등급 동일하면 시그널 없음"""
        snapshot = {
            "corp": {
                "kyc_status": {
                    "internal_risk_grade": "중위험",
                }
            }
        }
        prev_snapshot = {
            "corp": {
                "kyc_status": {
                    "internal_risk_grade": "중위험",
                }
            }
        }

        signals = self.generator.generate(
            corp_id="8001-3719240",
            corp_name="엠케이전자",
            snapshot=snapshot,
            prev_snapshot=prev_snapshot,
        )

        grade_signals = [s for s in signals if s["event_type"] == "INTERNAL_RISK_GRADE_CHANGE"]
        assert len(grade_signals) == 0

    def test_grade_change_no_prev_snapshot_no_signal(self):
        """이전 스냅샷 없으면 등급 변경 시그널 없음 (PM 결정 Q1: Option A)"""
        snapshot = {
            "corp": {
                "kyc_status": {
                    "internal_risk_grade": "고위험",
                }
            }
        }

        signals = self.generator.generate(
            corp_id="8001-3719240",
            corp_name="엠케이전자",
            snapshot=snapshot,
            prev_snapshot=None,  # 이전 스냅샷 없음
        )

        grade_signals = [s for s in signals if s["event_type"] == "INTERNAL_RISK_GRADE_CHANGE"]
        assert len(grade_signals) == 0

    # =========================================================================
    # LOAN_EXPOSURE_CHANGE 테스트
    # =========================================================================

    def test_loan_exposure_increase_15pct(self):
        """여신 15% 증가 시 시그널 생성 (10% 임계값 초과)"""
        snapshot = {
            "credit": {
                "loan_summary": {
                    "total_exposure_krw": 1_150_000_000,  # 15% 증가
                }
            }
        }
        prev_snapshot = {
            "credit": {
                "loan_summary": {
                    "total_exposure_krw": 1_000_000_000,
                }
            }
        }

        signals = self.generator.generate(
            corp_id="8001-3719240",
            corp_name="엠케이전자",
            snapshot=snapshot,
            prev_snapshot=prev_snapshot,
        )

        loan_signals = [s for s in signals if s["event_type"] == "LOAN_EXPOSURE_CHANGE"]
        assert len(loan_signals) == 1
        assert "증가" in loan_signals[0]["title"]

    def test_loan_exposure_decrease_20pct(self):
        """여신 20% 감소 시 OPPORTUNITY 시그널 생성"""
        snapshot = {
            "credit": {
                "loan_summary": {
                    "total_exposure_krw": 800_000_000,  # 20% 감소
                }
            }
        }
        prev_snapshot = {
            "credit": {
                "loan_summary": {
                    "total_exposure_krw": 1_000_000_000,
                }
            }
        }

        signals = self.generator.generate(
            corp_id="8001-3719240",
            corp_name="엠케이전자",
            snapshot=snapshot,
            prev_snapshot=prev_snapshot,
        )

        loan_signals = [s for s in signals if s["event_type"] == "LOAN_EXPOSURE_CHANGE"]
        assert len(loan_signals) == 1
        assert loan_signals[0]["impact_direction"] == "OPPORTUNITY"
        assert "감소" in loan_signals[0]["title"]

    def test_loan_exposure_5pct_no_signal(self):
        """여신 5% 변화는 임계값 미달로 시그널 없음"""
        snapshot = {
            "credit": {
                "loan_summary": {
                    "total_exposure_krw": 1_050_000_000,  # 5% 증가
                }
            }
        }
        prev_snapshot = {
            "credit": {
                "loan_summary": {
                    "total_exposure_krw": 1_000_000_000,
                }
            }
        }

        signals = self.generator.generate(
            corp_id="8001-3719240",
            corp_name="엠케이전자",
            snapshot=snapshot,
            prev_snapshot=prev_snapshot,
        )

        loan_signals = [s for s in signals if s["event_type"] == "LOAN_EXPOSURE_CHANGE"]
        assert len(loan_signals) == 0

    # =========================================================================
    # KYC_REFRESH 테스트
    # =========================================================================

    def test_kyc_refresh_needed_400_days(self):
        """KYC 400일 경과 시 KYC_REFRESH 시그널 생성"""
        old_date = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        snapshot = {
            "corp": {
                "kyc_status": {
                    "last_kyc_updated": old_date,
                }
            }
        }

        signals = self.generator.generate(
            corp_id="8001-3719240",
            corp_name="엠케이전자",
            snapshot=snapshot,
        )

        kyc_signals = [s for s in signals if s["event_type"] == "KYC_REFRESH"]
        assert len(kyc_signals) == 1
        assert "엠케이전자" in kyc_signals[0]["title"]
        assert "400일" in kyc_signals[0]["title"]

    def test_kyc_fresh_no_signal(self):
        """KYC 100일 경과 시 시그널 없음 (365일 미만)"""
        recent_date = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
        snapshot = {
            "corp": {
                "kyc_status": {
                    "last_kyc_updated": recent_date,
                }
            }
        }

        signals = self.generator.generate(
            corp_id="8001-3719240",
            corp_name="엠케이전자",
            snapshot=snapshot,
        )

        kyc_signals = [s for s in signals if s["event_type"] == "KYC_REFRESH"]
        assert len(kyc_signals) == 0

    # =========================================================================
    # 복합 시나리오 테스트
    # =========================================================================

    def test_multiple_signals_detected(self):
        """연체 + 등급 하락 동시 발생 시 2개 시그널 생성"""
        snapshot = {
            "credit": {
                "loan_summary": {
                    "overdue_flag": True,
                    "overdue_days": 60,
                    "total_exposure_krw": 2_000_000_000,
                    "risk_grade_internal": "고위험",
                }
            },
            "corp": {
                "kyc_status": {
                    "internal_risk_grade": "고위험",
                }
            }
        }
        prev_snapshot = {
            "corp": {
                "kyc_status": {
                    "internal_risk_grade": "중위험",
                }
            }
        }

        signals = self.generator.generate(
            corp_id="8001-3719240",
            corp_name="엠케이전자",
            snapshot=snapshot,
            prev_snapshot=prev_snapshot,
        )

        event_types = {s["event_type"] for s in signals}
        assert "OVERDUE_FLAG_ON" in event_types
        assert "INTERNAL_RISK_GRADE_CHANGE" in event_types
        assert len(signals) >= 2

    def test_empty_snapshot_no_signals(self):
        """빈 스냅샷은 시그널 없음"""
        signals = self.generator.generate(
            corp_id="8001-3719240",
            corp_name="엠케이전자",
            snapshot={},
        )

        assert len(signals) == 0

    # =========================================================================
    # event_signature 테스트
    # =========================================================================

    def test_event_signature_generated(self):
        """시그널에 event_signature가 생성됨"""
        snapshot = {
            "credit": {
                "loan_summary": {
                    "overdue_flag": True,
                    "overdue_days": 30,
                }
            }
        }

        signals = self.generator.generate(
            corp_id="8001-3719240",
            corp_name="엠케이전자",
            snapshot=snapshot,
        )

        assert len(signals) == 1
        assert "event_signature" in signals[0]
        assert len(signals[0]["event_signature"]) == 32  # SHA256 truncated to 32 chars

    def test_same_input_same_signature(self):
        """동일 입력은 동일 signature 생성"""
        snapshot = {
            "credit": {
                "loan_summary": {
                    "overdue_flag": True,
                    "overdue_days": 30,
                }
            }
        }

        signals1 = self.generator.generate(
            corp_id="8001-3719240",
            corp_name="엠케이전자",
            snapshot=snapshot,
        )
        signals2 = self.generator.generate(
            corp_id="8001-3719240",
            corp_name="엠케이전자",
            snapshot=snapshot,
        )

        # 같은 날 같은 기업, 같은 event_type → 동일 signature
        assert signals1[0]["event_signature"] == signals2[0]["event_signature"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
