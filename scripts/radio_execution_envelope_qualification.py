"""Reproduce the prospective execution-envelope evidence package."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results_radio_execution_envelope_2026-09-27"


def main():
    OUT.mkdir(exist_ok=True)
    commands = [
        [sys.executable, "scripts/radio_execution_envelope.py"],
        [sys.executable, "-m", "unittest", "discover", "-s", "tests",
         "-p", "test_radio_execution_envelope.py", "-v"],
    ]
    logs = []; tests = 0
    for command in commands:
        run = subprocess.run(command, cwd=ROOT, env=os.environ.copy(),
                             capture_output=True, text=True, timeout=120)
        logs += ["$ " + " ".join(command), run.stdout, run.stderr]
        (OUT / "qualification.log").write_text("\n".join(logs).rstrip() + "\n")
        if run.returncode:
            raise RuntimeError("execution-envelope qualification failed")
        match = re.search(r"Ran (\d+) tests? in", run.stderr)
        if match:
            tests += int(match.group(1))
    paths = [
        "src/seti_repeater/execution_envelope_radio.py",
        "scripts/radio_execution_envelope.py",
        "scripts/radio_execution_envelope_qualification.py",
        "tests/test_radio_execution_envelope.py",
        "config/radio_execution_envelope_20260927.json",
        "RADIO_EXECUTION_ENVELOPE_2026-09-27_RESULT.md",
    ]
    qualification = {
        "schema": "radio-execution-envelope-qualification-v1",
        "new_tests_passed": tests,
        "pinned_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                          for p in paths},
        "output_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in OUT.iterdir() if p.name != "qualification.json"},
        "closed_acquisition_ledger_rerun_or_reset": False,
        "closed_science_panel_rerun": False,
        "scientific_evaluation": False,
        "telescope_values_opened": False,
    }
    qualification_path = OUT / "qualification.json"
    qualification_path.write_text(
        json.dumps(qualification, indent=2, sort_keys=True) + "\n")
    manifest_paths = [ROOT / p for p in paths]
    manifest_paths += sorted(p for p in OUT.iterdir() if p.is_file())
    lines = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT)}"
             for path in manifest_paths]
    (ROOT / "RESULTS_MANIFEST_RADIO_EXECUTION_ENVELOPE_2026-09-27.sha256").write_text(
        "\n".join(lines) + "\n")
    print(json.dumps({"status": "PASS_BLOCKED_ENVELOPE",
                      "new_tests": tests}))


if __name__ == "__main__":
    main()
