import unittest

from lib.policy_enforcement import evaluate_decision_action_closure


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


if __name__ == "__main__":
    unittest.main()
