#!/usr/bin/env python3
"""Fetch the frozen A1/B1 LS1 high-time-resolution source products."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.request import Request, urlopen


USER_AGENT = "setisearch-ls1-htr-fetch/1.0"


def fetch(source: dict, destination: Path) -> str:
    expected_size = int(source["expected_size_bytes"])
    temporary = destination.with_suffix(destination.suffix + ".part")
    if not destination.exists() or destination.stat().st_size != expected_size:
        destination.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(1, 5):
            try:
                request = Request(source["url"], headers={"User-Agent": USER_AGENT})
                with urlopen(request, timeout=120) as response, temporary.open("wb") as output:
                    while True:
                        chunk = response.read(8 * 1024 * 1024)
                        if not chunk:
                            break
                        output.write(chunk)
                    output.flush()
                    os.fsync(output.fileno())
                if temporary.stat().st_size != expected_size:
                    raise RuntimeError("downloaded HTR size differs from frozen size")
                os.replace(temporary, destination)
                break
            except Exception:
                temporary.unlink(missing_ok=True)
                if attempt == 4:
                    raise
                time.sleep(2**attempt)
    digest = hashlib.sha256()
    with destination.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--data-dir", type=Path, default=Path("data_ls1_htr"))
    parser.add_argument(
        "--manifest", type=Path, default=Path("DATA_MANIFEST_LS1_HTR.sha256")
    )
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    lines = []
    for source in config["sources"]:
        destination = args.data_dir / f"{source['label']}.8.0001.h5"
        digest = fetch(source, destination)
        lines.append(f"{digest}  {destination.as_posix()}")
        print(f"verified {source['label']} {digest}", flush=True)
    args.manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
