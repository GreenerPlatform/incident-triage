"""W5 evidence-integrity contract tests."""
import json
import os
import unittest

import incident_triage as it

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


class TestW5HistoricalGap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(FIXTURES, "restart-resolved-report.json")) as f:
            cls.sentinel = json.load(f)
        cls.alert = it.parse_alert(os.path.join(FIXTURES, "restart-alert.json"))
        cls.alert_type = it.classify_alert_type(
            cls.alert["alert_name"] + " " + cls.alert.get("raw_body", "")
        )
        cls.matched = it.score_findings(cls.sentinel, cls.alert, cls.alert_type)
        cls.output = it.build_output(cls.alert, cls.sentinel, cls.matched, cls.alert_type)

    def test_historical_gap_recorded(self):
        codes = [g["code"] for g in self.output.get("evidence_gaps", [])]
        self.assertIn("historical_incident", codes)

    def test_confidence_stays_low(self):
        self.assertEqual(self.output["confidence"], "low")


class TestW5CollectorGap(unittest.TestCase):
    def test_failed_collector_lowers_confidence(self):
        sentinel = {
            "context": "test",
            "scope": "namespace: demo",
            "summary": {"critical": 0, "warn": 1, "ok": 1},
            "sections": [
                {
                    "section": "HTTP",
                    "findings": [
                        {
                            "id": "HTTP-COLLECT-FAILED",
                            "severity": "WARN",
                            "message": "Could not retrieve services",
                            "collection_status": "failed",
                        }
                    ],
                }
            ],
        }
        alert = it.parse_alert(os.path.join(FIXTURES, "sample-alert.json"))
        alert_type = it.classify_alert_type(alert["alert_name"])
        matched = it.score_findings(sentinel, alert, alert_type)
        out = it.build_output(alert, sentinel, matched, alert_type)
        self.assertTrue(any(g["code"] == "collector_degraded" for g in out["evidence_gaps"]))
        self.assertEqual(out["confidence"], "low")


if __name__ == "__main__":
    unittest.main()
