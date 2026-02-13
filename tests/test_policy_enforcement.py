import unittest
from datetime import datetime, timedelta, timezone

from lib.policy_enforcement import (
    check_phase_state,
    evaluate_calibration_label_staleness,
    evaluate_decision_action_closure,
)


class PolicyEnforcementTests(unittest.TestCase):
    def test_closure_ok_when_actions_executed(self) -> None:
        decision = {
            "mandatory_actions": ["AUTO_HOLD_AND_OPEN_INCIDENT"],
            "phase_hold": True,
            "provenance": {"decision_hash": "h1"},
            "explain": {"machine": {"override_status": {"present": False, "valid": False, "applied": False}}},
        }
        report = evaluate_decision_action_closure(
            decision,
            executed_actions=["AUTO_HOLD_AND_OPEN_INCIDENT"],
            action_artifacts=[{"artifact_id": "inc1", "artifact_type": "incident", "decision_hash": "h1"}],
            observed_operations=[{"operation": "INCIDENT_OPENED", "operation_id": "o1", "decision_hash": "h1"}],
        )
        self.assertTrue(report["closure_ok"])
        self.assertEqual(report["decision_without_action_rate"], 0.0)
        self.assertEqual(report["out_of_band_action_count"], 0)
        self.assertEqual(report["provenance_linkage_coverage"], 1.0)

    def test_detects_missing_action_and_oob(self) -> None:
        decision = {
            "mandatory_actions": ["BLOCK_PROMOTION_UNTIL_RESOLVED"],
            "phase_hold": True,
            "provenance": {"decision_hash": "h1"},
            "explain": {"machine": {"override_status": {"present": False, "valid": False, "applied": False}}},
        }
        report = evaluate_decision_action_closure(
            decision,
            executed_actions=[],
            action_artifacts=[{"artifact_id": "rel1", "artifact_type": "release", "decision_hash": "other"}],
            observed_operations=[{"operation": "PROMOTION_EXECUTED", "operation_id": "o1", "decision_hash": "other"}],
        )
        self.assertFalse(report["closure_ok"])
        self.assertEqual(report["decision_without_action_rate"], 1.0)
        self.assertEqual(report["promotion_during_hold_count"], 1)
        self.assertEqual(report["out_of_band_action_count"], 1)

    def test_override_ttl_violation_rejected_by_phase_state_check(self) -> None:
        payload = {
            "published_videos": 12,
            "ctr_weekly": [0.05, 0.05, 0.05, 0.05],
            "avd_weekly": [45.0, 45.0, 45.0, 45.0],
            "geo_readiness_warning_count_weekly": [1, 1, 1, 1],
            "source_contract_ready": True,
            "source_linkage_pass_rate": 0.99,
            "research_source_coverage": 0.97,
            "incident_open": False,
            "override_record": {
                "actor_id": "ops-1",
                "approved_by": "cto",
                "justification": "Emergency",
                "created_at": "2026-01-01T00:00:00+00:00",
                "expires_at": "2026-01-20T00:00:00+00:00",
                "signature": "sig",
                "scope": "phase_b_promotion",
            },
            "executed_actions": [],
            "action_artifacts": [],
            "observed_operations": [],
        }

        report = check_phase_state(payload)
        self.assertTrue(report["phase_hold"])
        self.assertIn("OVERRIDE_REJECTED", report["explain"]["reason_codes"])
        self.assertEqual(report["override_audit_violations"], 1)

    def test_calibration_label_staleness_weekly_governance(self) -> None:
        now = datetime(2026, 1, 10, tzinfo=timezone.utc)
        stale = (now - timedelta(days=9)).isoformat()
        fresh = (now - timedelta(days=2)).isoformat()
        report = evaluate_calibration_label_staleness(
            [{"label": "correct_hold", "labeled_at": stale}, {"label": "false_promote", "labeled_at": fresh}],
            reference_time=now,
        )

        self.assertEqual(report["stale_label_count"], 1)
        self.assertEqual(report["fresh_label_count"], 1)
        self.assertFalse(report["governance_ok"])


if __name__ == "__main__":
    unittest.main()
