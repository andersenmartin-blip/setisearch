#!/usr/bin/env python3
"""Bind the retained widened geometry once; no network or spectral operation."""
import hashlib
import json
from pathlib import Path

from seti_repeater.window_identity_radio_v2 import build

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results_radio_hd189733_geometry_2026-09-27"
SOURCE = "config/radio_hd189733_source_preparation_20260927.json"
DESIGN = "results_radio_hd189733_geometry_2026-09-27/window_geometry.json"
SOURCE_SHA = "98f6ced7e10cabaac139e027e8449e34ddf49024254761217a288ca6dc439cf1"
DESIGN_SHA = "92fb0472203124f0f0a3f05a6a136c410ceaa72a31b66c12fcbbfb1c8c0eebc6"


def save(name, value):
    with (OUT / name).open("x") as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")


def main():
    contract = build((ROOT / SOURCE).read_bytes(), SOURCE_SHA,
                     (ROOT / DESIGN).read_bytes(), DESIGN_SHA)
    save("window_identity_contract_v2.json", contract)
    paths = [SOURCE, DESIGN, "src/seti_repeater/window_identity_radio_v2.py",
             "src/seti_repeater/source_m43h.py", "tests/test_radio_window_identity_v2.py",
             "scripts/radio_hd189733_window_contract_v2.py",
             "RADIO_HD189733_WINDOW_V2_2026-09-27_PROTOCOL.md",
             "results_radio_hd189733_geometry_2026-09-27/window_v2_tests.log",
             "results_radio_hd189733_geometry_2026-09-27/window_identity_contract_v2.json"]
    save("window_v2_verification.json", {
        "schema": "radio-hd189733-window-v2-verification-v1",
        "status": contract["status"],
        "source_and_design_match_external_pins": True,
        "sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
        "new_tests_passed": 8, "unchanged_old_tests_rerun": False,
        "test_execution": "See retained raw unittest log; this builder does not rerun it.",
        "distinct_native_chunk_identities": contract["distinct_native_chunk_identities"],
        "normalization_blocks": contract["normalization_blocks"],
        "network_requests": 0, "spectral_values_read": False,
        "scientific_trials": 0, "spectral_access_authorized": False})
    print(json.dumps({k: contract[k] for k in (
        "contract_sha256", "status", "distinct_native_chunk_identities",
        "normalization_blocks", "spectral_access_authorized")}, indent=2))


if __name__ == "__main__":
    main()
