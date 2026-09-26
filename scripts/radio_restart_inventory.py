#!/usr/bin/env python3
"""Index closed radio candidate decisions and reusable interfaces; no new science."""
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results_radio_restart_2026-09-26"
BASE = "14276c388af320e05d3b853891857f3e090874dc"
MILESTONES = (11, 14, 15, 16, 18, 20, 21, 29, 33)


def pin(path):
    raw = (ROOT / path).read_bytes()
    expected = subprocess.check_output(["git", "show", BASE + ":" + path], cwd=ROOT)
    if raw != expected:
        raise ValueError("Historical input changed: " + path)
    return {"path": path, "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob_sha": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}


def main():
    sources, rows = [], []
    for milestone in MILESTONES:
        path = f"results_m{milestone}_candidate_investigation/candidate_investigation.json"
        sources.append(pin(path))
        data = json.loads((ROOT / path).read_text())
        followups, followup_path = {}, None
        if milestone in (14, 16):
            followup_path = f"results_m{milestone}_independent_followup/independent_followup.json"
            sources.append(pin(followup_path))
            f = json.loads((ROOT / followup_path).read_text())
            followups = {c["original_ordinal"]: c for c in f["candidates"]}
            assert len(followups) == f["candidate_count"]
        assert len(data["candidates"]) == data["candidate_count"]
        for candidate in data["candidates"]:
            ordinal = candidate["ordinal"]
            followup = followups.pop(ordinal, None)
            if followup:
                assert followup["best_hypothesis"] == candidate["best_hypothesis"]
                assert followup["original_posthoc_classification"] == candidate["posthoc_classification"]
            rows.append({
                "milestone": milestone, "ordinal": ordinal,
                "window_id": candidate["window_id"],
                "frequency_mhz": candidate["best_hypothesis"]["frequency_mhz"],
                "frozen_search_disposition": candidate.get("frozen_original_disposition"),
                "investigation_classification": candidate["posthoc_classification"],
                "independent_followup_classification": followup["followup_classification"] if followup else None,
                "latest_recorded_classification": followup["followup_classification"] if followup else candidate["posthoc_classification"],
                "investigation_source": path,
                "followup_source": followup_path if followup else None,
                "m35_possible_detection_count": int(milestone == 16 and ordinal == 1),
            })
        assert not followups
    counts = dict(Counter(r["latest_recorded_classification"] for r in rows))
    result = dict(source_commit=BASE, purpose="Navigation index of every retained M11–M33 dedicated candidate-investigation record, joined to its published follow-up; not a new disposition or full detector-trigger census",
                  candidate_count=len(rows), source_files=sources, classifications=counts, candidates=rows,
                  caveats=["A null frozen_search_disposition means that field was absent in the historical investigation schema, not that the search had a null result.",
                           "Non-redetection is not a physical interference veto.",
                           "M15 GJ 581 and M33 HD 3651 remain unresolved.",
                           "M16 case 1 remains a possible true detection in M35's conservative 1412 MHz count.",
                           "M37's separate 43,883-member retained ledger remains closed, with no unresolved scientific candidate; it is not condensed into these 24 investigation cases.",
                           "No candidate spectrum is reanalysed and no M43AF reserved input is opened."])
    (OUT / "candidate_register.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    interfaces = [
        ("src/seti_repeater/source_m43h.py", "extract_remote; make_scope; normalize_native_row", "Row extraction/normalization reusable arithmetic, but extract_remote/frozen_inputs are bound to the HD156668 M43H config and M43F/G ancestry. A new entry point with independent source pins is required; never rewrite those old configs."),
        ("src/seti_repeater/transfer_m43i.py", "load_telescope_source; build_telescope_cache", "Receipt-bound native filtering and gathering; bind fresh target geometry and source receipts. No old cache identity transfers."),
        ("src/seti_repeater/search_v0p6.py", "make_factor_basis_from_arrays; make_template_factor_table; ExhaustiveRetentionLedger", "Generic geometry/retention primitives available. Defaults and M37-prefixed wrappers contain old target identities, fixed widths and activity subsets; each must be explicitly accounted for in the new protocol."),
        ("src/seti_repeater/detector_m43u.py", "calibrate; execute", "Integrated diagnostic mask, calibration, exhaustive ON/OFF retention, receiver alias and rank-p pipeline; supply a new store, geometry and sealed calibration. execute explicitly labels outputs diagnostic."),
        ("src/seti_repeater/attribution_m43ab.py", "POLICIES; apply_controls", "Named centered_receiver_off_match_aggregate reference available. Not automatically qualified and not selected by a new outcome."),
        ("src/seti_repeater/confirmation_m43z.py", "POLICIES; apply_controls", "neighbor9 reference and historical confirmation compositions; preserve endpoint semantics."),
        ("scripts/m43ae_joint_response.py", "context; upstream", "Historical integrated orchestration is bound to M43 source arrays and calibration; use as interface documentation, not a new-source runner."),
        ("scripts/m43ai_native_validation.py", "run", "Closed failed validation; do not rerun, retune or adopt it as the new primary rule."),
    ]
    records = [{**pin(p), "entry_points": entry, "transfer_boundary": boundary} for p, entry, boundary in interfaces]
    (OUT / "detector_entrypoints.json").write_text(json.dumps(dict(source_commit=BASE, interfaces=records), indent=2, sort_keys=True) + "\n")
    print(json.dumps(dict(candidate_count=len(rows), classifications=counts, pinned_historical_sources=len(sources), interfaces=len(records)), indent=2))


if __name__ == "__main__":
    main()
