#!/usr/bin/env python3
"""Freeze or audit the content-addressed v2 archive batch."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from seti_repeater import event_archive_batch_radio as batch
from seti_repeater.empty_null_radio import canonical


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("freeze", "validate", "audit"))
    parser.add_argument("--parent")
    parser.add_argument("--source-commit")
    parser.add_argument("--freeze")
    parser.add_argument("--commit")
    parser.add_argument("--out")
    args = parser.parse_args()
    if args.mode == "freeze":
        result = batch.prepare_freeze(ROOT, args.parent or "HEAD", source_commit=args.source_commit)
    else:
        freeze = json.loads((ROOT / args.freeze).read_bytes())
        if args.mode == "validate":
            result = batch.validate_freeze(ROOT, freeze, require_parent=args.parent)
        else:
            result = batch.verify_readback(ROOT, args.commit, freeze)
    raw = canonical(result)
    if args.out:
        path = ROOT / args.out
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(raw)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
