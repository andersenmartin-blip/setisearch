#!/usr/bin/env python3
"""Run only local-source engineering tests and retain the actual test outcome."""
import io
import json
from pathlib import Path
import sys
import unittest
from seti_repeater import source_radio as source
from seti_repeater import source_m43h as rows

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/"results_radio_source_2026-09-26"
CONTRACT = "config/radio_hd1461_source_preparation_20260926.json"


def main():
    suite = unittest.defaultTestLoader.discover(str(ROOT/"tests"), "test_radio_source.py")
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    OUT.mkdir(exist_ok=True)
    (OUT/"test.log").write_text(stream.getvalue())
    _, readiness = source.load_contract(ROOT, CONTRACT, rows.file_hash(ROOT/CONTRACT))
    (OUT/"preparation.json").write_text(json.dumps(readiness, indent=2, sort_keys=True)+"\n")
    paths = [*source.IMPLEMENTATION_PATHS, CONTRACT, "tests/test_radio_source.py",
             "scripts/radio_source_prepare.py", "scripts/radio_source_qualification.py",
             "scripts/m43g_reference.py"]
    report = {"status": "LOCAL_SOFTWARE_CHECKS_PASS" if result.wasSuccessful() else "FAIL",
              "tests_run": result.testsRun, "failures": len(result.failures),
              "errors": len(result.errors), "runtime": source.runtime(),
              "telescope_requests": 0, "telescope_spectral_values_read": False,
              "fixture_codecs": ["gzip", "bitshuffle_lz4"],
              "source_readiness": readiness,
              "claim": "Local engineering checks only; no source-pointing or detector qualification.",
              "implementation_sha256": {p: rows.file_hash(ROOT/p) for p in paths},
              "test_log_sha256": rows.file_hash(OUT/"test.log")}
    (OUT/"qualification.json").write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    print(stream.getvalue(), end="")
    print(json.dumps({k: report[k] for k in ("status", "tests_run", "failures", "errors", "telescope_requests")}))
    if not result.wasSuccessful():
        sys.exit(1)


if __name__ == "__main__":
    main()
