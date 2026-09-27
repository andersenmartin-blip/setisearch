#!/usr/bin/env python3
"""Independent arithmetic/receipt reconciliation of this new acquisition only."""
import base64
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = "results_radio_alternate_2026-09-27/"
GEOM = "results_radio_hd189733_geometry_2026-09-27/"


def read(path):
    return json.loads((ROOT / path).read_text())


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def unit(ra, dec):
    a, d = math.radians(ra), math.radians(dec)
    return (math.cos(d) * math.cos(a), math.cos(d) * math.sin(a), math.sin(d))


def main():
    acquired = read(BASE + "attempt01/result.json")
    receipts = read(BASE + "attempt01/transport_receipts.json")
    snapshot = read(BASE + "attempt01/source_snapshot.json")
    qualification = read(BASE + "source_qualification.json")
    for path, expected in snapshot["sha256"].items():
        published = subprocess.check_output(["git", "show", snapshot["freeze_commit"] + ":" + path], cwd=ROOT)
        assert hashlib.sha256(published).hexdigest() == sha(path) == expected
    for path, expected in qualification["old_frozen_input_pins_unchanged"].items():
        assert sha(path) == expected
    for path, expected in read(GEOM + "input_pins.json").items():
        assert sha(path) == expected
    count = Counter()
    body_bytes = 0
    for r in receipts:
        body = base64.b64decode(r["body_base64"], validate=True)
        assert hashlib.sha256(body).hexdigest() == r["body_sha256"]
        assert len(body) == r["body_bytes_observed"] == r["bytes_charged"]
        assert r["state"] == "RESPONSE_RETAINED" and r["url"] == r["final_url"]
        body_bytes += len(body)
        count[str(r["status"]) + " " + r["method"]] += 1
    assert count == {"200 GET": 2, "200 HEAD": 6, "206 GET": 72}
    assert len(receipts) == acquired["new_metadata_usage"]["requests"] == 80
    assert body_bytes == acquired["new_metadata_usage"]["bytes_charged"] == 55841
    assert acquired["combined_source_screen_usage"]["bytes_charged"] == body_bytes + 263066
    assert acquired["combined_source_screen_usage"]["requests"] == len(receipts) + 83
    rows = read(BASE + "attempt01/85030/headers.json")
    official = read(BASE + "attempt01/85030/official_metadata.json")[0]
    reference = unit(official["ra"], official["dec"])
    separations = []
    for h, retained in zip(rows[::2], qualification["pointing_checks"]):
        a = h["data_attributes"]
        vec = unit(a["src_raj"] * 15, a["src_dej"])
        cross = (vec[1]*reference[2]-vec[2]*reference[1],
                 vec[2]*reference[0]-vec[0]*reference[2],
                 vec[0]*reference[1]-vec[1]*reference[0])
        separation = math.degrees(math.atan2(math.sqrt(sum(v*v for v in cross)),
                                           sum(x*y for x,y in zip(vec, reference))))*3600
        assert abs(separation - retained["separation_arcsec"]) < 1e-6
        separations.append(separation)
    # A direct phase witness is stronger evidence of insufficiency than comparing
    # a loose upper bound alone. This is still conditional, nominal model arithmetic.
    geometry = read(GEOM + "result.json")
    a = rows[0]["data_attributes"]
    c = 299792458.0
    period = official["pl_orbper"] * 86400
    speed = 2 * math.pi * official["pl_orbsmax"] * 149597870700.0 / period
    phase = math.pi * a["tsamp"] / period
    integration_witness = geometry["reference_frequency_hz"] * speed * (
        math.sin(phase) - math.sin(-phase)) / c
    old_width_hz = 129 * abs(a["foff"]) * 1e6
    assert integration_witness > old_width_hz
    assert integration_witness < geometry["continuous_phase_integration_sweep_bound_hz"]
    assert max(abs(t) for t in geometry["relative_clock_extent_seconds"]) < period / 2
    contract = read(GEOM + "window_identity_contract_v2.json")
    assert contract["distinct_native_chunk_identities"] == 288
    assert contract["spectral_access_authorized"] is False
    result = {
        "schema": "radio-alternate-postflight-v1", "status": "PASS_WITH_EXPLICIT_SCIENTIFIC_HOLDS",
        "metadata_freeze_commit": snapshot["freeze_commit"], "published_input_pins_verified": len(snapshot["sha256"]),
        "old_frozen_input_pins_unchanged": len(qualification["old_frozen_input_pins_unchanged"]),
        "receipt_body_hashes_verified": len(receipts), "http_response_counts": dict(count),
        "response_body_bytes_reconciled": body_bytes, "total_wire_bytes_known": False,
        "independent_vector_separations_arcsec": separations,
        "conditional_nominal_integration_phase_zero_sweep_hz": integration_witness,
        "old_129_channel_width_hz": old_width_hz,
        "conditional_model_sweep_witness_exceeds_old_width": True,
        "continuous_time_bound_uses_monotonic_abs_sine_before_half_period": True,
        "formal_outward_rounded_physical_certificate": False,
        "actual_source_coverage_qualified": False,
        "unexecuted_reserve": 73005, "network_requests": 0, "scientific_trials": 0,
        "spectral_values_read": False, "spectral_access_authorized": False,
        "script_sha256": sha("scripts/radio_alternate_postflight_20260927.py")}
    with (ROOT / (BASE + "postflight_verification.json")).open("x") as f:
        json.dump(result, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
