"""Reproduce only the changed downstream package and its targeted regression."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results_radio_direct_downstream_2026-09-26"


def main():
    OUT.mkdir(exist_ok=True)
    commands = [
        [sys.executable, "-m", "unittest", "discover", "-s", "tests",
         "-p", "test_radio_direct_downstream.py", "-v"],
        [sys.executable, "-m", "unittest", "discover", "-s", "tests",
         "-p", "test_radio_pipeline.py", "-v"],
        [sys.executable, "scripts/radio_direct_downstream_fixture.py"],
        [sys.executable, "scripts/radio_direct_downstream_diagnosis.py"],
    ]
    logs = []; counts = []
    for command in commands:
        run = subprocess.run(command, cwd=ROOT, env=os.environ.copy(),
                             capture_output=True, text=True, timeout=240)
        logs += ["$ " + " ".join(command), run.stdout, run.stderr]
        (OUT / "qualification.log").write_text("\n".join(logs).rstrip() + "\n")
        if run.returncode:
            raise RuntimeError("direct downstream qualification failed")
        match = re.search(r"Ran (\d+) tests? in", run.stderr)
        if match:
            counts.append(int(match.group(1)))
    paths = [
        "src/seti_repeater/direct_contract_radio.py",
        "src/seti_repeater/detector_direct_radio.py",
        "src/seti_repeater/pipeline_direct_radio.py",
        "src/seti_repeater/adjacent_v0p6.py",
        "src/seti_repeater/factors_radio.py",
        "src/seti_repeater/detector_m43u.py",
        "src/seti_repeater/pipeline_radio.py",
        "scripts/radio_direct_downstream_fixture.py",
        "scripts/radio_direct_downstream_qualification.py",
        "scripts/radio_direct_downstream_diagnosis.py",
        "tests/test_radio_direct_downstream.py",
        "tests/test_radio_pipeline.py",
        "config/radio_direct_downstream_engineering_20260926.json",
        "config/radio_direct_factors_engineering_20260926.json",
        "results_radio_direct_factors_2026-09-26/result.json",
    ]
    record = {"schema": "radio-direct-downstream-test-qualification-v1",
        "new_tests_passed": counts[0], "targeted_legacy_regression_tests_passed": counts[1],
        "pinned_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
        "output_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in OUT.iterdir() if p.name != "qualification.json"},
        "closed_science_panels_rerun": False,
        "scientific_evaluation": False, "telescope_values_opened": False}
    (OUT / "qualification.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "PASS_CONNECTOR_WITH_FAILED_CONTROL_GATE",
                      "new_tests": counts[0], "regression_tests": counts[1]}))


if __name__ == "__main__":
    main()
