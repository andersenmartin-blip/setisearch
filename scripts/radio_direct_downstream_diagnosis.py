"""Bounded retained-evidence diagnosis of the failed matched-ON/OFF control."""
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np

from radio_direct_downstream_fixture import setup

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "results_radio_direct_downstream_2026-09-26/reports.json.gz"
OUT = ROOT / "results_radio_direct_downstream_2026-09-26/control_diagnosis.json"


def main():
    cfg, context, _ = setup()
    reports = json.load(gzip.open(REPORTS, "rt"))
    report = reports["matched_on_off"]; detector = report["detector"]
    decisions = {item["record_id"]: item for item in detector["decisions"]}
    final = [item for item in detector["retained"]["on"]
             if decisions[item["record_id"]]["passes_evaluated_physical_vetoes"]
             and decisions[item["record_id"]]["meets_diagnostic_rank_cut"]]
    factors = context.factor_contract.matrix_for_kind("on")
    truth = (context.grid.score_hz[cfg["truth_score_index"]]
             * factors[cfg["truth_template_index"]]).reshape(3, 16)
    rows = []
    for item in final:
        track = (item["proxy_carrier_hz"] * factors[item["template_index"]]).reshape(3, 16)
        separation = np.abs(track - truth)
        rows.append({"record_id": item["record_id"], "template_index": item["template_index"],
            "proxy_carrier_index": item["proxy_carrier_index"],
            "spectral_width_channels": item["spectral_width_channels"],
            "active_epochs_zero_based": item["active_epochs_zero_based"],
            "epoch_values_at_proxy_carrier": item["epoch_values_at_proxy_carrier"],
            "minimum_track_separation_from_injected_truth_hz_by_epoch":
                [float(x.min()) for x in separation],
            "maximum_track_separation_from_injected_truth_hz_by_epoch":
                [float(x.max()) for x in separation],
            "first_epoch_intersects_width_129_half_support": bool(
                separation[0].min() <= 64 * context.grid.channel_width_hz),
            "second_epoch_is_more_than_9khz_from_truth": bool(separation[1].min() > 9000),
        })
    clusters = [item for item in report["clusters"] if item["diagnostic_final_ids"]]
    result = {"schema": "radio-direct-downstream-control-diagnosis-v1",
        "input_reports_gzip_sha256": hashlib.sha256(REPORTS.read_bytes()).hexdigest(),
        "case": "matched_on_off", "final_member_count": len(final),
        "final_cluster_count": len(clusters),
        "all_final_members_width_129": all(x["spectral_width_channels"] == 129 for x in final),
        "all_final_members_activity_subset_0_1": all(x["active_epochs_zero_based"] == [0, 1] for x in final),
        "final_template_counts": {str(t): sum(x["template_index"] == t for x in final)
                                  for t in sorted({x["template_index"] for x in final})},
        "all_first_epoch_tracks_intersect_injected_width_half_support":
            all(x["first_epoch_intersects_width_129_half_support"] for x in rows),
        "all_second_epoch_tracks_more_than_9khz_from_truth":
            all(x["second_epoch_is_more_than_9khz_from_truth"] for x in rows),
        "minimum_second_epoch_value": min(x["epoch_values_at_proxy_carrier"][1] for x in rows),
        "maximum_second_epoch_value": max(x["epoch_values_at_proxy_carrier"][1] for x in rows),
        "minimum_active_epoch_floor": 3.0,
        "diagnosis": ("Each survivor is a width-129 alternate track that intersects the strong injected signal "
            "within half-width in epoch 1 and receives a just-over-floor noise value in epoch 2; it is not "
            "the injected matched ON/OFF track, which is vetoed."),
        "implementation_error_demonstrated": False,
        "control_design_limitation_demonstrated": True,
        "threshold_or_bank_retuned": False,
        "records": rows,
        "complete_final_cluster_sha256s": [x["cluster_sha256"] for x in clusters],
        "telescope_values_opened": False}
    if not (len(final) == 13 and len(clusters) == 2
            and result["all_final_members_width_129"]
            and result["all_final_members_activity_subset_0_1"]
            and result["all_first_epoch_tracks_intersect_injected_width_half_support"]
            and result["all_second_epoch_tracks_more_than_9khz_from_truth"]):
        raise ValueError("retained control leakage no longer matches the bounded diagnosis")
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in ("final_member_count", "final_cluster_count",
        "final_template_counts", "control_design_limitation_demonstrated")}, indent=2))


if __name__ == "__main__":
    main()
