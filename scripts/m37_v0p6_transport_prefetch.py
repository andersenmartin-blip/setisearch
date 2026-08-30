#!/usr/bin/env python3
"""Prefetch and verify one authorized M37 scan without publishing caches."""

from __future__ import annotations

import argparse
import gc
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for item in (str(ROOT / "src"), str(ROOT / "scripts")):
    if item not in sys.path:
        sys.path.insert(0, item)

import m37_v0p6_hdf5_extract as extractor
import m37_v0p6_primary as primary
from seti_repeater import search_v0p6 as core


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scan_label")
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--range-workers", type=int, default=2)
    args = parser.parse_args()
    record = primary._status(args.run_root)
    if not primary._stage_at_least(record, "spectral_access_authorized"):
        raise core.V0P6IncompleteError("prefetch requires an authorized run")
    bundle = primary._bundle(args.run_root, record)
    products = extractor.iter_m37_normalized_scan_products(
        bundle.scans,
        scan_label=args.scan_label,
        window_ids=core.M37_WINDOW_IDS,
        spectral_access_authorized=True,
        range_mirror_root=args.run_root / "ranges",
        range_workers=args.range_workers,
    )
    count = 0
    for product in products:
        count += 1
        primary._emit_progress(
            "transport_prefetch_product_verified",
            scan_label=args.scan_label,
            window_id=product.window_id,
            product_sha256=product.product_sha256,
        )
        del product
        gc.collect()
    if count != len(core.M37_WINDOW_IDS):
        raise core.V0P6IncompleteError("prefetch product inventory is incomplete")
    primary._emit_progress(
        "transport_prefetch_complete",
        scan_label=args.scan_label,
        product_count=count,
    )


if __name__ == "__main__":
    main()
