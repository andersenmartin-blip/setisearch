#!/usr/bin/env python3
"""Fetch the six frozen LS2D medium-resolution products with identity checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ls1_fetch import fetch


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--data-dir", type=Path, default=Path("data_ls2d"))
    parser.add_argument(
        "--manifest", type=Path, default=Path("DATA_MANIFEST_LS2D.sha256")
    )
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config.get("artifact_type") != "seti_repeater.ls2d_preregistration":
        raise RuntimeError("wrong LS2D configuration artifact")
    lines = []
    for scan in config["selected_sequence"]:
        destination = args.data_dir / f"{scan['label']}.0002.h5"
        digest = fetch(scan, destination)
        lines.append(f"{digest}  {destination.as_posix()}")
        print(f"verified {scan['label']} {digest}", flush=True)
    args.manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
