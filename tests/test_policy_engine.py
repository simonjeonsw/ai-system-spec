import unittest

from lib.policy_engine import PhaseEvaluationInput, evaluate_phase_state


class PolicyEngineTests(unittest.TestCase):
    def test_phase_b_promotable_when_all_thresholds_pass(self) -> None:
        result = evaluate_phase_state(
            PhaseEvaluationInput(
                published_videos=12,
                ctr_weekly=[0.051, 0.049, 0.05, 0.052],
                avd_weekly=[44.0, 45.0, 46.0, 45.0],
                geo_readiness_warning_count_weekly=[1, 1, 1, 1],
                source_contract_ready=True,
                source_linkage_pass_rate=0.99,
                research_source_coverage=0.97,
                incident_open=False,
            )
        )
        self.assertTrue(result["explain"]["can_promote"])
        self.assertEqual(result["geo_readiness"]["level"], "green")
        self.assertFalse(result["phase_hold"])
        self.assertIn("decision_hash", result["provenance"])
        self.assertIn("human", result["explain"])

    def test_phase_hold_when_geo_red_escalates(self) -> None:
        result = evaluate_phase_state(
            PhaseEvaluationInput(
                published_videos=12,
                ctr_weekly=[0.051, 0.049, 0.05, 0.052],
                avd_weekly=[44.0, 45.0, 46.0, 45.0],
                geo_readiness_warning_count_weekly=[4, 5, 6, 7],
                source_contract_ready=True,
                source_linkage_pass_rate=0.99,
                research_source_coverage=0.97,
                incident_open=False,
            )
        )
        self.assertFalse(result["explain"]["can_promote"])
        self.assertTrue(result["phase_hold"])
        self.assertIn("GEO_WARN_RED_THRESHOLD", result["explain"]["reason_codes"])
        self.assertIn("AUTO_HOLD_AND_OPEN_INCIDENT", result["mandatory_actions"])

    def test_phase_hold_pending_info_on_insufficient_data(self) -> None:
        result = evaluate_phase_state(
            PhaseEvaluationInput(
                published_videos=12,
                ctr_weekly=[0.051],
                avd_weekly=[44.0],
                geo_readiness_warning_count_weekly=[1, 1, 1, 1],
                source_contract_ready=True,
                source_linkage_pass_rate=0.99,
                research_source_coverage=0.97,
                incident_open=False,
            )
        )
        self.assertFalse(result["explain"]["can_promote"])
        self.assertIn("decision_hold_pending_info", result["explain"]["reason_codes"])
        self.assertIn("HOLD_PENDING_INFO_COLLECTION", result["mandatory_actions"])

    def test_phase_hold_for_source_contract_gap(self) -> None:
        result = evaluate_phase_state(
            PhaseEvaluationInput(
                published_videos=15,
                ctr_weekly=[0.051, 0.049, 0.05, 0.052],
                avd_weekly=[44.0, 45.0, 46.0, 45.0],
                geo_readiness_warning_count_weekly=[1, 1, 1, 1],
                source_contract_ready=False,
                source_linkage_pass_rate=0.9,
                research_source_coverage=0.85,
                incident_open=False,
            )
        )
        self.assertFalse(result["explain"]["can_promote"])
        self.assertIn("SOURCE_CONTRACT_NOT_READY", result["explain"]["reason_codes"])
        self.assertIn("SOURCE_LINKAGE_PASS_RATE_FAIL", result["explain"]["reason_codes"])

    def test_invalid_override_counts_audit_violation(self) -> None:
        result = evaluate_phase_state(
            PhaseEvaluationInput(
                published_videos=12,
                ctr_weekly=[0.051, 0.049, 0.05, 0.052],
                avd_weekly=[44.0, 45.0, 46.0, 45.0],
                geo_readiness_warning_count_weekly=[1, 1, 1, 1],
                source_contract_ready=True,
                source_linkage_pass_rate=0.99,
                research_source_coverage=0.97,
                incident_open=False,
                override_record={"actor_id": "cto"},
            )
        )
        self.assertEqual(result["override_audit_violations"], 1)
        self.assertFalse(result["explain"]["machine"]["override_status"]["valid"])


if __name__ == "__main__":
    unittest.main()
