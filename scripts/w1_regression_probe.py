#!/usr/bin/env python3
"""Prove W1 gate fails when classifier regresses (in-process monkeypatch)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import incident_triage as it
from tests.test_correlation import TestRestartClassification


def main() -> int:
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(
        "test_container_restart_singular", TestRestartClassification
    )
    ok = unittest.TextTestRunner(verbosity=0).run(suite).wasSuccessful()
    if not ok:
        print("FAIL: classifier tests already failing on clean tree", file=sys.stderr)
        return 1

    orig = it.classify_alert_type

    def broken(text: str, keyword_map=None):  # noqa: ARG001
        return "unknown"

    it.classify_alert_type = broken
    suite_bad = loader.loadTestsFromName(
        "test_container_restart_singular", TestRestartClassification
    )
    bad = unittest.TextTestRunner(verbosity=0).run(suite_bad).wasSuccessful()
    it.classify_alert_type = orig

    if bad:
        print("FAIL: unittest did not catch simulated classifier regression", file=sys.stderr)
        return 1

    print("regression probe: unittest catches bad classifier")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
