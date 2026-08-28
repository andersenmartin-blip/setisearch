#!/usr/bin/env python3
"""Create the metadata-only M37 detector-v0.6 runner bootstrap.

This command never contacts a telescope object.  It reproduces the frozen
factor basis, persists the factor bundle, and stops at ``factor_bundle_ready``.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import sys
from typing import Any

import numpy as np

from seti_repeater import runner_v0p6
from seti_repeater.search_v0p6 import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "config/hd156668b_m37_preflight.json"
BANK_RESULT = (
    ROOT / "results_m37_v0p6_bank_preflight/bank_preflight.json"
)
SOURCE_PATHS = {
    "continuous_preflight_config": UPSTREAM,
    "bank_preflight_result": BANK_RESULT,
    "bank_preflight_manifest": ROOT / "RESULTS_MANIFEST_M37_V0P6_BANK_PREFLIGHT.sha256",
    "bank_preflight_provenance": ROOT / "MILESTONE_37_V0P6_BANK_PREFLIGHT_PROVENANCE.json",
    "bank_preflight_plan": ROOT / "MILESTONE_37_DETECTOR_V0P6_BANK_PREFLIGHT_PLAN.md",
    "orbit_module": ROOT / "src/seti_repeater/orbit.py",
    "search_v0p6_module": ROOT / "src/seti_repeater/search_v0p6.py",
    "factor_bundle_v0p6_module": ROOT / "src/seti_repeater/factor_bundle_v0p6.py",
    "run_state_v0p6_module": ROOT / "src/seti_repeater/run_state_v0p6.py",
    "runner_v0p6_module": ROOT / "src/seti_repeater/runner_v0p6.py",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "absent"


def environment_record() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "numpy": np.__version__,
        "astropy": _version("astropy"),
        "astropy_iers_data": _version("astropy-iers-data"),
        "pyerfa": _version("pyerfa"),
        "packaging": _version("packaging"),
        "pyyaml": _version("pyyaml"),
        "purpose": "m37-detector-v0p6-non-spectral-bootstrap-candidate",
        "spectral_access_authorized": False,
        "spectral_dataset_values_read": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results_m37_v0p6_bootstrap_candidate"),
    )
    parser.add_argument(
        "--run-id",
        default="m37-v0p6-bootstrap-candidate-001",
    )
    args = parser.parse_args()
    upstream = json.loads(UPSTREAM.read_text())
    bank_result = json.loads(BANK_RESULT.read_text())
    source_hashes = {
        name: _sha256(path) for name, path in sorted(SOURCE_PATHS.items())
    }
    receipt = runner_v0p6.bootstrap_m37_run(
        args.output_dir,
        run_id=args.run_id,
        upstream_metadata=upstream,
        bank_preflight_result=bank_result,
        environment=environment_record(),
        source_hashes=source_hashes,
    )
    print(canonical_json_bytes(receipt.__dict__).decode(), end="")


if __name__ == "__main__":
    main()
