#!/usr/bin/env python3
"""Inspect a pinned acquisition contract offline. Does not open telescope data."""
import argparse
import json
from pathlib import Path
from seti_repeater.source_radio import load_contract


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    _, result = load_contract(root, args.contract, args.sha256)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload)
    print(payload, end="")


if __name__ == "__main__":
    main()
