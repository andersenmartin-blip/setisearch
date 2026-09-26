"""Reproduce the identity-only cross-window contract package."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results_radio_cross_window_2026-09-26"


def main():
    OUT.mkdir(exist_ok=True)
    commands = [
        [sys.executable, "-m", "unittest", "discover", "-s", "tests",
         "-p", "test_radio_cross_window_contract.py", "-v"],
        [sys.executable, "-m", "unittest", "discover", "-s", "tests",
         "-p", "test_radio_fresh_control_freeze.py", "-v"],
        [sys.executable, "scripts/radio_cross_window_contract.py"],
        [sys.executable, "scripts/radio_fresh_control_freeze.py"],
    ]
    logs = []; test_count = 0
    for command in commands:
        run = subprocess.run(command, cwd=ROOT, env=os.environ.copy(),
                             capture_output=True, text=True, timeout=120)
        logs += ["$ " + " ".join(command), run.stdout, run.stderr]
        (OUT / "qualification.log").write_text("\n".join(logs).rstrip() + "\n")
        if run.returncode:
            raise RuntimeError("cross-window contract qualification failed")
        match = re.search(r"Ran (\d+) tests? in", run.stderr)
        if match:
            test_count += int(match.group(1))
    paths = [
        "src/seti_repeater/calibration_transfer_radio.py",
        "src/seti_repeater/control_freeze_radio.py",
        "scripts/radio_cross_window_contract.py",
        "scripts/radio_fresh_control_freeze.py",
        "scripts/radio_cross_window_qualification.py",
        "tests/test_radio_cross_window_contract.py",
        "tests/test_radio_fresh_control_freeze.py",
        "config/radio_cross_window_contract_engineering_20260926.json",
        "config/radio_fresh_control_freeze_20260926.json",
        "results_radio_motion_2026-09-26/prospective_design.json",
        "RADIO_CROSS_WINDOW_CONTRACT_2026-09-26_RESULT.md",
    ]
    record = {
        "schema": "radio-cross-window-contract-test-qualification-v1",
        "new_tests_passed": test_count,
        "pinned_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                          for p in paths},
        "output_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in OUT.iterdir() if p.name != "qualification.json"},
        "closed_downstream_panel_rerun": False,
        "numeric_cross_window_transfer_executed": False,
        "scientific_evaluation": False,
        "telescope_values_opened": False,
    }
    qualification = OUT / "qualification.json"
    qualification.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    manifest_paths = [ROOT / p for p in paths]
    manifest_paths += sorted(p for p in OUT.iterdir() if p.is_file())
    lines = []
    for path in manifest_paths:
        relative = path.relative_to(ROOT)
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}")
    (ROOT / "RESULTS_MANIFEST_RADIO_CROSS_WINDOW_2026-09-26.sha256").write_text(
        "\n".join(lines) + "\n")
    print(json.dumps({"status": "PASS_IDENTITY_CONTRACT_ONLY",
                      "new_tests": test_count}))


if __name__ == "__main__":
    main()
