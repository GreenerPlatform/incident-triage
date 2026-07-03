#!/usr/bin/env python3
"""Unit tests for incident-triage correlation logic."""

import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import incident_triage as it  # noqa: E402


FIXTURES = os.path.join(ROOT, "tests", "fixtures")


class TestChronicHygiene(unittest.TestCase):
    def test_memory_limits_are_hygiene(self):
        msg = "129 pod(s) have containers with no memory limit"
        self.assertTrue(it._is_chronic_hygiene(msg))

    def test_pvc_pending_is_not_hygiene(self):
        msg = "PVC cybertron/datadir-mongodb-0: phase Pending"
        self.assertFalse(it._is_chronic_hygiene(msg))


class TestResourceLinking(unittest.TestCase):
    def test_pvc_links_to_mongodb_pod(self):
        pvc = "PVC cybertron/datadir-mongodb-0: phase Pending"
        pod = "Pod cybertron/mongodb-0: Pending — unbound PersistentVolumeClaims [datadir-mongodb-0]"
        root = {"section": "PVCS", "message": pvc}
        cand = {"section": "PODS", "message": pod}
        alert = {"service": "mongodb", "namespace": "cybertron"}
        self.assertTrue(it._is_causally_linked(root, cand, alert))

    def test_memory_limits_do_not_link_to_pvc(self):
        root = {"section": "PVCS", "message": "PVC cybertron/datadir-mongodb-0: phase Pending"}
        cand = {"section": "PODS", "message": "129 pod(s) have containers with no memory limit"}
        alert = {"namespace": "cybertron"}
        self.assertFalse(it._is_causally_linked(root, cand, alert))


class TestStorageNoiseFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(FIXTURES, "storage-noise-report.json")) as f:
            cls.sentinel = json.load(f)
        cls.alert = it.parse_alert(os.path.join(FIXTURES, "storage-alert.json"))
        cls.alert_type = it.classify_alert_type(
            cls.alert["alert_name"] + " " + cls.alert.get("raw_body", "")
        )
        cls.matched = it.score_findings(cls.sentinel, cls.alert, cls.alert_type)
        cls.output = it.build_output(cls.alert, cls.sentinel, cls.matched, cls.alert_type)

    def test_primary_root_is_pvc(self):
        chain = self.output["causation_chain"]
        self.assertEqual(chain[0]["label"], "root_cause")
        self.assertIn("datadir-mongodb-0", chain[0]["description"])

    def test_hygiene_not_in_chain(self):
        chain_msgs = " ".join(s["description"] for s in self.output["causation_chain"])
        self.assertNotIn("memory limit", chain_msgs.lower())
        self.assertNotIn("cpu request", chain_msgs.lower())

    def test_mongodb_pod_is_contributing_or_chain_intermediate(self):
        matched_msgs = [f["message"] for f in self.output["correlation"]["matched_findings"]]
        pod_msg = next(m for m in matched_msgs if "mongodb-0" in m)
        finding = next(
            f for f in self.output["correlation"]["matched_findings"] if f["message"] == pod_msg
        )
        self.assertIn(finding["relevance"], ("contributing", "direct"))

    def test_peep_v1_suppressed(self):
        matched_msgs = " ".join(f["message"] for f in self.output["correlation"]["matched_findings"])
        self.assertNotIn("peep-v1", matched_msgs)

    def test_what_changed_not_memory_limits(self):
        wc = self.output["what_changed"]
        if wc.get("detected"):
            summary = wc.get("summary", "").lower()
            self.assertNotIn("memory limit", summary)
            self.assertIn("storage", summary.lower())

    def test_failed_job_is_parallel(self):
        parallel = self.output.get("parallel_findings", [])
        self.assertTrue(any("bumblebee" in p["message"] for p in parallel))


class TestPaymentsSmokeFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(FIXTURES, "sample-report.json")) as f:
            cls.sentinel = json.load(f)
        cls.alert = it.parse_alert(os.path.join(FIXTURES, "sample-alert.json"))
        cls.alert_type = it.classify_alert_type(
            cls.alert["alert_name"] + " " + cls.alert.get("raw_body", "")
        )
        cls.matched = it.score_findings(cls.sentinel, cls.alert, cls.alert_type)
        cls.output = it.build_output(cls.alert, cls.sentinel, cls.matched, cls.alert_type)

    def test_payments_api_is_root(self):
        chain = self.output["causation_chain"]
        self.assertIn("payments-api", chain[0]["description"])

    def test_worker_is_parallel_not_intermediate(self):
        chain_msgs = " ".join(s["description"] for s in self.output["causation_chain"])
        self.assertNotIn("payments-worker", chain_msgs)
        parallel = self.output.get("parallel_findings", [])
        self.assertTrue(any("payments-worker" in p["message"] for p in parallel))

    def test_deployment_in_chain(self):
        chain_msgs = " ".join(s["description"] for s in self.output["causation_chain"])
        self.assertIn("payments-api", chain_msgs)
        self.assertIn("0/3 replicas", chain_msgs)


class TestRestartClassification(unittest.TestCase):
    """G1: singular 'restart' phrasings must classify as crash_loop, not fall to unknown."""

    def test_container_restart_singular(self):
        self.assertEqual(
            it.classify_alert_type("[P4][P4D] - ERROR - Container restart above 3 in 30mins"),
            "crash_loop",
        )

    def test_restarted_variants(self):
        for text in ("pod restarted 5 times", "container restart above threshold",
                     "restart count high"):
            self.assertEqual(it.classify_alert_type(text), "crash_loop", text)


class TestRestartResolvedRegression(unittest.TestCase):
    """
    The p4d-fdplan false positive. A restart alert triaged against a snapshot with
    no pod-restart evidence (alert already resolved) must NOT pin the root cause on
    an unrelated failed batch Job that merely shares the namespace. Honest absence
    (Unknown root, low confidence) with the Job surfaced as a parallel finding.
    """

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

    def test_classified_as_crash_loop(self):
        self.assertEqual(self.alert_type, "crash_loop")

    def test_failed_job_is_not_root_cause(self):
        root = self.output["causation_chain"][0]
        self.assertEqual(root["label"], "root_cause")
        self.assertNotIn("bumblebee-billing", root["description"])
        self.assertTrue(root["description"].startswith("Unknown"), root["description"])

    def test_no_direct_match(self):
        directs = [f for f in self.output["correlation"]["matched_findings"]
                   if f["relevance"] == "direct"]
        self.assertEqual(directs, [], "a resolved restart snapshot has no direct cause")

    def test_confidence_low(self):
        self.assertEqual(self.output["confidence"], "low")

    def test_failed_jobs_surface_as_parallel(self):
        parallel = self.output.get("parallel_findings", [])
        self.assertTrue(any("bumblebee-billing" in p["message"] for p in parallel),
                        "unrelated failed Jobs should be surfaced as parallel, not dropped")

    def test_hygiene_not_in_chain(self):
        chain_msgs = " ".join(s["description"] for s in self.output["causation_chain"]).lower()
        self.assertNotIn("missing liveness", chain_msgs)
        self.assertNotIn("non-standard node condition", chain_msgs)


class TestClassifierRobustness(unittest.TestCase):
    """Classification must survive phrasing, morphology, and vendor-format variety."""

    def test_restart_morphology(self):
        for text in ("pod restart above 3", "pods restarting repeatedly",
                     "container restarted 5x", "high restart count"):
            self.assertEqual(it.classify_alert_type(text), "crash_loop", text)

    def test_numeric_keyword_is_whole_word(self):
        # "500" must NOT match "5000ms" — that alert should stay latency_spike.
        self.assertEqual(it.classify_alert_type("p99 latency 5000ms"), "latency_spike")
        # A genuine HTTP 500 still classifies as high_error_rate.
        self.assertEqual(it.classify_alert_type("HTTP 500 error rate spike"), "high_error_rate")

    def test_vendor_style_names(self):
        self.assertEqual(it.classify_alert_type("KubePodCrashLooping firing"), "kube_app_health")
        self.assertEqual(it.classify_alert_type("KubePersistentVolumeFillingUp"), "kube_storage")

    def test_scoring_prefers_more_evidence(self):
        self.assertEqual(it.classify_alert_type("latency p95 timeout slow"), "latency_spike")

    def test_user_config_extends_keywords(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"crash_loop": ["bouncing"]}, f)
            path = f.name
        try:
            os.environ["INCIDENT_TRIAGE_ALERT_TYPES"] = path
            kmap = it.load_alert_type_keywords()
            self.assertIn("bouncing", kmap["crash_loop"])
            self.assertEqual(it.classify_alert_type("service keeps bouncing", kmap), "crash_loop")
        finally:
            os.environ.pop("INCIDENT_TRIAGE_ALERT_TYPES", None)
            os.unlink(path)

    def test_unknown_alert_has_no_namespace_only_root(self):
        sentinel = {
            "schema_version": "1.0",
            "sections": [
                {"section": "JOBS", "findings": [
                    {"severity": "CRITICAL",
                     "message": "Job team-x/nightly-export: Failed (DeadlineExceeded)",
                     "recommendation": None, "last_event": None}]},
            ],
        }
        alert = {"alert_name": "weird custom signal xyz", "namespace": "team-x",
                 "service": None, "raw_body": "weird custom signal xyz"}
        atype = it.classify_alert_type(alert["alert_name"])
        self.assertEqual(atype, "unknown")
        matched = it.score_findings(sentinel, alert, atype)
        directs = [f for f in matched if f["relevance"] == "direct"]
        self.assertEqual(directs, [], "unknown alert must not pin a root cause on namespace overlap")
        self.assertTrue(any(f["relevance"] == "parallel" for f in matched),
                        "the CRITICAL should still be surfaced as a parallel finding")


class TestCliSmoke(unittest.TestCase):
    def test_cli_sample_fixture_exit_zero(self):
        proc = subprocess.run(
            [
                sys.executable,
                os.path.join(ROOT, "incident_triage.py"),
                "--sentinel-json",
                os.path.join(FIXTURES, "sample-report.json"),
                "--alert",
                os.path.join(FIXTURES, "sample-alert.json"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["schema_version"], "1.2")


if __name__ == "__main__":
    unittest.main()
