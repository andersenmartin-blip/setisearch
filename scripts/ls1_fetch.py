#!/usr/bin/env python3
"""Fetch the six frozen LS1 medium-resolution products with identity checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.request import Request, urlopen


USER_AGENT = "setisearch-ls1-fetch/1.0"


def fetch(scan: dict, destination: Path) -> str:
    expected_size = int(scan["medium_resolution"]["expected_size_bytes"])
    url = scan["medium_resolution"]["url"]
    temporary = destination.with_suffix(destination.suffix + ".part")
    if destination.exists() and destination.stat().st_size == expected_size:
        path = destination
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(1, 5):
            try:
                request = Request(url, headers={"User-Agent": USER_AGENT})
                with urlopen(request, timeout=120) as response, temporary.open("wb") as output:
                    while True:
                        chunk = response.read(8 * 1024 * 1024)
                        if not chunk:
                            break
                        output.write(chunk)
                    output.flush()
                    os.fsync(output.fileno())
                if temporary.stat().st_size != expected_size:
                    raise RuntimeError("downloaded size differs from frozen archive size")
                os.replace(temporary, destination)
                path = destination
                break
            except Exception:
                temporary.unlink(missing_ok=True)
                if attempt == 4:
                    raise
                time.sleep(2**attempt)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--data-dir", type=Path, default=Path("data_ls1"))
    parser.add_argument("--manifest", type=Path, default=Path("DATA_MANIFEST_LS1.sha256"))
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    lines = []
    for scan in config["selected_sequence"]:
        destination = args.data_dir / f"{scan['label']}.0002.h5"
        digest = fetch(scan, destination)
        lines.append(f"{digest}  {destination.as_posix()}")
        print(f"verified {scan['label']} {digest}", flush=True)
    args.manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
