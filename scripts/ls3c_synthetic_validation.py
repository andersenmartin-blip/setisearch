#!/usr/bin/env python3
"""Re-run the unchanged LS1 broadband injection as the LS3C detector gate."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

from ls1_synthetic_validation import run_validation as run_inherited_validation
from seti_repeater.search_v0p6 import canonical_json_bytes


def run_validation() -> dict:
    result = run_inherited_validation()
    result["artifact_type"] = "seti_repeater.ls3c_synthetic_validation"
    result["inherited_detector"] = "LS1 unchanged"
    result["result_sha256"] = hashlib.sha256(
        canonical_json_bytes({key: value for key, value in result.items() if key != "result_sha256"})
    ).hexdigest()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("results_ls3c/synthetic_validation.json"))
    args = parser.parse_args()
    result = run_validation()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(f".{args.output.name}.tmp-{os.getpid()}")
    temporary.write_bytes(canonical_json_bytes(result))
    os.replace(temporary, args.output)
    print(canonical_json_bytes(result).decode("utf-8"))


if __name__ == "__main__":
    main()
