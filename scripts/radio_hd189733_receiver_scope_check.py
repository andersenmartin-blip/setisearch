#!/usr/bin/env python3
"""Audit output identity separation and distinguish searched carriers from extraction."""
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results_radio_hd189733_receiver_2026-09-28"


def main():
    read = lambda p: json.loads(p.read_text())
    panel = read(OUT/"control_identity_reservation.json")
    prior = read(OUT/"prior_config_identifier_inventory.json")
    entries = panel["identities"]
    assert len({x["identity"] for x in entries}) == len({x["namespace"] for x in entries}) == len({x["seed"] for x in entries}) == 33
    assert not {x["seed"] for x in entries}.intersection(prior["prior_integer_seeds"])
    assert not {x["namespace"] for x in entries}.intersection(prior["prior_namespaces"])
    assert {role:sum(x["role"]==role for x in entries) for role in ("development","calibration","evaluation")} == {"development":6,"calibration":3,"evaluation":24}
    assert all(x["executed"] is False and x["outcomes_may_select_settings"] is False for x in entries)
    old = read(ROOT/"config/radio_fresh_control_freeze_20260926.json")
    assert panel["gates"] == old["gates"] and panel["association_rule"] == old["association_rule"]
    source = read(ROOT/"config/radio_hd189733_source_preparation_20260927.json")
    design = read(ROOT/"results_radio_hd189733_geometry_2026-09-27/window_geometry.json")
    banks = read(OUT/"bank_records.json")
    df = abs(Q(source["scans"][0]["expected_header"]["foff_mhz"]))*10**6
    scopes = []
    seen = set()
    for w,b in zip(design["windows"],banks):
        assert b["provenance"]["window_identity"] == w["identity"]
        C = Q(w["proposed_first_on_midpoint_carrier_center_hz"])
        qlow, qhigh = C-40*df, C+40*df
        for p in w["payload_keys"]:
            for xyz in p["chunk_coordinates_time_feed_frequency"]:
                key = (p["source_url"],p["etag"],*xyz)
                assert key not in seen
                seen.add(key)
        scopes.append({"role":w["role"],"center_hz":float(C),
                       "carrier_reference_low_hz":float(qlow),"carrier_reference_high_hz":float(qhigh),
                       "carrier_reference_span_hz":float(qhigh-qlow),
                       "extraction_low_hz":w["native_frequency_low_hz"],
                       "extraction_high_hz":w["native_frequency_high_hz"],
                       "rate_label_hz_s":[-4,4],
                       "actual_slope_extrema_hz_s":[float(-4*qhigh/C),float(4*qhigh/C)],
                       "whole_extraction_searched":False,"carrier_scope_at":"first ON midpoint"})
    assert len(seen) == 288
    result = {"schema":"radio-hd189733-receiver-scope-postflight-v1",
              "fresh_identity_count":33,"prior_configuration_files_checked":len(prior["config_sha256"]),
              "native_chunk_identity_count":288,"all_three_roles_disjoint":True,
              "prior_recovery_rfi_null_gates_unchanged":True,"search_scopes":scopes,
              "whole_cadence_linear_requirement":True,"independent_observing_dates":1,
              "scientific_trials":0,"telescope_requests":0,"external_messages_sent":0,
              "script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with (OUT/"scope_postflight.json").open("x") as f:
        json.dump(result,f,indent=2,sort_keys=True,allow_nan=False); f.write("\n")
    print(json.dumps(result,indent=2))


if __name__ == "__main__": main()
