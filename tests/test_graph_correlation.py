"""P0 evidence graph: subject-based correlation."""
import contextlib
import io
import json
import os
import unittest

import incident_triage as it

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


class TestSubjectDirectMatch(unittest.TestCase):
    def test_deployment_subject_links_alert_service(self):
        with open(os.path.join(FIXTURES, "graph-subject-crashloop.json")) as f:
            sentinel = json.load(f)
        alert = {
            "alert_source": "test",
            "alert_name": "payments api crash loop",
            "service": "api",
            "namespace": "payments",
            "severity": "critical",
            "raw_body": "",
        }
        alert_type = it.classify_alert_type(alert["alert_name"])
        matched = it.score_findings(sentinel, alert, alert_type)
        directs = [m for m in matched if m["relevance"] == "direct"]
        self.assertEqual(len(directs), 1, matched)
        output = it.build_output(alert, sentinel, matched, alert_type)
        self.assertTrue(output["correlation"]["matched_findings"][0]["subjects"])

    def test_current_sentinel_schema_has_no_warning(self):
        path = os.path.join(FIXTURES, "graph-subject-crashloop.json")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            sentinel = it.load_sentinel(path)
        self.assertIsNotNone(sentinel)
        self.assertEqual(stderr.getvalue(), "")


class TestSectionCollectionGap(unittest.TestCase):
    def test_failed_section_surfaces_gap(self):
        with open(os.path.join(FIXTURES, "w5-failed-collector-report.json")) as f:
            sentinel = json.load(f)
        alert = {"alert_name": "test", "namespace": "demo", "alert_source": "test"}
        gaps = it.assess_evidence_gaps(sentinel, alert, "unknown", [])
        self.assertTrue(any(g["code"] == "collector_degraded" for g in gaps))


if __name__ == "__main__":
    unittest.main()
