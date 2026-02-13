import unittest

from scripts.policy_calibration_report import build_report


class PolicyCalibrationReportTests(unittest.TestCase):
    def test_build_report_rates(self) -> None:
        report = build_report(
            [
                {"label": "correct_hold"},
                {"label": "false_hold"},
                {"label": "false_promote"},
                {"label": "correct_promote"},
            ]
        )
        self.assertEqual(report["total"], 4)
        self.assertEqual(report["false_hold_rate"], 0.25)
        self.assertEqual(report["false_promote_rate"], 0.25)

    def test_invalid_label_raises(self) -> None:
        with self.assertRaises(ValueError):
            build_report([{"label": "bad_label"}])


if __name__ == "__main__":
    unittest.main()
