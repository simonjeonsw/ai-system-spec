import json
import unittest
from pathlib import Path

from jsonschema import Draft7Validator


SCHEMA_DIR = Path("spec/schemas")


def _load_schema(filename: str) -> dict:
    return json.loads((SCHEMA_DIR / filename).read_text(encoding="utf-8"))


class Slice0ContractFreezeTests(unittest.TestCase):
    def test_authorize_execution_request_schema(self) -> None:
        schema = _load_schema("authorize_execution.request.schema.json")
        validator = Draft7Validator(schema)

        valid = {
            "decision_hash": "dec_0123456789abcdef",
            "attestation_token": "tok_" + "a" * 40,
            "action_scope": "promotion",
            "requested_at": "2026-01-01T00:00:00Z",
            "execution_identity": {
                "agent_id": "agent-1",
                "pipeline_id": "promo-pipeline",
                "region": "ap-northeast-2",
                "env_tier": "prod",
                "spiffe_id": "spiffe://autonomous-os/promotion/adapter-1",
            },
        }
        self.assertEqual(list(validator.iter_errors(valid)), [])

        invalid = dict(valid)
        invalid.pop("decision_hash")
        self.assertNotEqual(list(validator.iter_errors(invalid)), [])

    def test_authorize_execution_response_deny_requires_denial_code(self) -> None:
        schema = _load_schema("authorize_execution.response.schema.json")
        validator = Draft7Validator(schema)

        deny_missing_code = {
            "authorization_id": "auth-1001",
            "verdict": "DENY",
            "decision_hash": "dec_0123456789abcdef",
            "policy_bundle_hash": "pol_0123456789abcdef",
            "enforcement_epoch": {"value": 3, "state": "active"},
            "evaluated_at": "2026-01-01T00:00:05Z",
        }
        self.assertNotEqual(list(validator.iter_errors(deny_missing_code)), [])

        deny_with_code = dict(deny_missing_code)
        deny_with_code["denial_code"] = "TOKEN_INVALID"
        self.assertEqual(list(validator.iter_errors(deny_with_code)), [])

    def test_token_claims_schema_requires_minimal_safe_claims(self) -> None:
        schema = _load_schema("attestation_token_claims.schema.json")
        validator = Draft7Validator(schema)

        valid = {
            "token_schema_version": "1.0",
            "decision_hash": "dec_0123456789abcdef",
            "jti": "jti_123456789012",
            "exp": 1760000000,
            "issued_at": 1759999900,
            "action_scope": "promotion",
            "policy_bundle_hash": "pol_0123456789abcdef",
            "enforcement_epoch": 3,
            "exec_identity_hash": "idh_0123456789abcdef",
            "kid": "kid_2026_01",
        }
        self.assertEqual(list(validator.iter_errors(valid)), [])

        invalid = dict(valid)
        invalid.pop("jti")
        self.assertNotEqual(list(validator.iter_errors(invalid)), [])

    def test_event_schema_requires_correlation_keys(self) -> None:
        schema = _load_schema("enforcement_event.schema.json")
        validator = Draft7Validator(schema)

        valid = {
            "event_id": "evt-1001",
            "event_type": "authorization_denied",
            "occurred_at": "2026-01-01T00:00:05Z",
            "decision_hash": "dec_0123456789abcdef",
            "token_jti": "jti_123456789012",
            "authorization_id": "auth-1001",
            "action_scope": "promotion",
            "region": "ap-northeast-2",
            "agent_id": "agent-1",
            "denial_code": "REVOCATION_UNCERTAIN",
        }
        self.assertEqual(list(validator.iter_errors(valid)), [])

        invalid = dict(valid)
        invalid.pop("token_jti")
        self.assertNotEqual(list(validator.iter_errors(invalid)), [])

    def test_fail_closed_matrix_semantics(self) -> None:
        schema = _load_schema("fail_closed_matrix.schema.json")
        validator = Draft7Validator(schema)
        matrix_path = Path("spec/samples/contracts/fail_closed_matrix.slice0.json")
        payload = json.loads(matrix_path.read_text(encoding="utf-8"))

        self.assertEqual(list(validator.iter_errors(payload)), [])

        promotion_rules = [r for r in payload["rules"] if r["action_scope"] == "promotion"]
        self.assertTrue(promotion_rules)
        self.assertTrue(all(r["mode"] == "fail_closed" for r in promotion_rules))


if __name__ == "__main__":
    unittest.main()
