#!/usr/bin/env python3
"""Execute the frozen LS2D screen through the unchanged LS1 implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from ls1_screen import run as run_inherited_screen
from seti_repeater.search_v0p6 import canonical_json_bytes


def run(config_path: Path, data_dir: Path) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("artifact_type") != "seti_repeater.ls2d_preregistration":
        raise RuntimeError("wrong LS2D configuration artifact")
    if not config["project"]["detector_inherited_unchanged_from_ls1"]:
        raise RuntimeError("LS2D detector inheritance is not frozen")
    result = run_inherited_screen(config_path, data_dir)
    result["artifact_type"] = "seti_repeater.ls2d_medium_resolution_screen"
    result["inherited_detector"] = "LS1 unchanged"
    result["target"] = config["target"]
    result["geometry"] = config["geometry"]
    result["result_sha256"] = hashlib.sha256(canonical_json_bytes({
        key: value for key, value in result.items() if key != "result_sha256"
    })).hexdigest()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--data-dir", type=Path, default=Path("data_ls2d"))
    parser.add_argument(
        "--output", type=Path, default=Path("results_ls2d/screen.json")
    )
    args = parser.parse_args()
    result = run(args.config, args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(f".{args.output.name}.tmp-{os.getpid()}")
    temporary.write_bytes(canonical_json_bytes(result))
    os.replace(temporary, args.output)
    print(canonical_json_bytes(result).decode("utf-8"))


if __name__ == "__main__":
    main()
