"""Derive saved winning-path geometry at an injected pulse time; no scoring.

Only standard-library file/hash/JSON/CSV/statistics operations are used. The
frozen generator and detector are read for hashes but never imported or run.
Run only through the root's admitted whole-job resource wrapper.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FIXED_POINT_TOLERANCE = 18.5


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_bytes())


def close(actual: float, expected: float, tolerance: float = 1e-8) -> None:
    assert math.isfinite(actual) and math.isfinite(expected)
    assert abs(actual - expected) <= tolerance, (actual, expected)


def absolute_stats(values: list[float]) -> dict:
    assert values
    return {
        "minimum": min(values),
        "median": statistics.median(values),
        "maximum": max(values),
        "count": len(values),
    }


def main() -> None:
    evidence_path = OUT / "DIAGNOSTIC_EVIDENCE.json"
    csv_path = OUT / "transient_original_carriers.csv"
    evidence = read(evidence_path)
    assert evidence["status"] == "COMPLETE_RETAINED_DIAGNOSTIC_ANALYSIS"
    contract_path = ROOT / "pilot_controls_20261008/control_contract.json"
    for relative, expected in evidence["original_code_sha256"].items():
        assert sha(ROOT / relative) == expected, relative
    contract = read(contract_path)
    scans = contract["geometry"]["scan_metadata"]
    reference_time = contract["geometry"]["tref_relative_first_scan_start_s"]
    first_mjd = contract["geometry"]["first_scan_start_mjd"]
    original_bindings = {item["directory"]: item for item in evidence["original_case_bindings"]}
    with csv_path.open(newline="") as stream:
        original_csv = list(csv.DictReader(stream))
    csv_by_key = {}
    for row in original_csv:
        key = (row["case_id"], row["ON_scan"], int(row["carrier"]))
        assert key not in csv_by_key
        csv_by_key[key] = row

    output_rows = []
    summaries = []
    bindings = []
    consumed = set()
    for index in range(118, 130):
        relative = f"results/radio_pilot_val_b_20261008/case_{index:03d}"
        directory = ROOT / relative
        prior = original_bindings[relative]
        manifest_path = directory / "artifact_manifest.json"
        marker_path = directory / "COMMITTED.json"
        manifest = read(manifest_path)
        marker = read(marker_path)
        assert marker["status"] == "COMPLETED_CASE_ONLY"
        assert marker["no_retry_or_redraw"] and marker["caps_passed"]
        assert sha(manifest_path) == marker["artifact_manifest_SHA256"] == prior["manifest_sha256"]
        assert sha(marker_path) == prior["COMMITTED_sha256"]
        names = {
            "case_definition.json": "case_definition_sha256",
            "truth.json": "truth_sha256",
            "all_ON_threshold_carriers.json": "raw_hits_sha256",
            "scan_map_metadata.json": "map_metadata_sha256",
        }
        verified = {}
        for name, key in names.items():
            path = directory / name
            digest = sha(path)
            assert digest == manifest[name]["SHA256"] == prior[key]
            assert path.stat().st_size == manifest[name]["size_bytes"]
            verified[name] = {"sha256": digest, "bytes": path.stat().st_size}
        case = read(directory / "case_definition.json")
        truth = read(directory / "truth.json")
        hits = read(directory / "all_ON_threshold_carriers.json")
        metas = read(directory / "scan_map_metadata.json")
        assert case["family"] == truth["family"] == "single_row_transient"
        assert case["case_id"] == truth["case_id"] == marker["case_id"]
        assert not case["eligibility_case"]
        assert case["active_scan_indices"] == truth["active_scan_indices"]
        assert len(case["active_scan_indices"]) == 1
        active_index = case["active_scan_indices"][0]
        scan = scans[active_index]
        meta = metas[active_index]
        assert scan["role"] == "on" and meta["role"] == "ON"
        assert scan["scan_id"] == meta["scan_id"] == truth["active_ON_scan_ids"][0]
        pulse_row = case["transient_row"]
        assert pulse_row in (0, 15) and scan["nrows"] == 16
        assert case["drift_hz_s"] == truth["drift_hz_s"]
        assert (case["intrinsic_width_channels"], case["drift_hz_s"]) in ((1, -4.0), (3, 4.0))
        first_time = meta["scan_first_time_from_tref_s"]
        last_time = meta["scan_last_time_from_tref_s"]
        # Independently bind the retained midpoint coordinate to frozen headers.
        header_first = (scan["tstart_mjd"] - first_mjd) * 86400.0 + 0.5 * scan["tsamp_s"] - reference_time
        close(first_time, header_first, 1e-7)
        close(last_time - first_time, (scan["nrows"] - 1) * scan["tsamp_s"], 1e-7)
        pulse_time = first_time + pulse_row * scan["tsamp_s"]
        close(pulse_time, first_time if pulse_row == 0 else last_time, 1e-7)
        oracle = truth["flux_by_scan"][scan["scan_id"]]["injection_oracle_width_channels"]
        assert oracle in contract["box_width_bank"]
        per_case = []
        for hit in hits:
            assert hit["scan_id"] == scan["scan_id"], "Unexpected carrier in an uninjected ON"
            key = (case["case_id"], hit["scan_id"], hit["reference_carrier_index"])
            assert key not in consumed
            consumed.add(key)
            prior_csv = csv_by_key[key]
            assert prior_csv["disposition"] == hit["disposition"] == "SURVIVOR_EXPLORATORY"
            assert int(prior_csv["winning_width_channels"]) == hit["width_channels"]
            assert float(prior_csv["winning_drift_hz_s"]) == hit["drift_hz_s"]
            assert float(prior_csv["frequency_hz_at_tref"]) == hit["reference_frequency_hz"]
            assert float(prior_csv["ON_score"]) == hit["ON_robust_score"]
            close(hit["scan_first_time_from_tref_s"], first_time)
            close(hit["scan_last_time_from_tref_s"], last_time)
            df = abs(hit["df_hz"])
            close(df, abs(scan["df_hz"]))
            delta_frequency = hit["reference_frequency_hz"] - truth["reference_frequency_hz"]
            delta_drift = hit["drift_hz_s"] - truth["drift_hz_s"]
            errors = [(delta_frequency + delta_drift * t) / df for t in (first_time, pulse_time, last_time)]
            tolerance = 2 + max(hit["width_channels"], oracle) / 2
            full_localized = max(abs(errors[0]), abs(errors[2])) <= tolerance
            point_localized = abs(errors[1]) <= tolerance
            point_fixed = abs(errors[1]) <= FIXED_POINT_TOLERANCE
            assert full_localized == (prior_csv["truth_localized"] == "True")
            close(errors[0], float(prior_csv["first_ON_truth_error_channel_widths"]))
            close(errors[2], float(prior_csv["last_ON_truth_error_channel_widths"]))
            close(tolerance, float(prior_csv["truth_tolerance_channel_widths"]))
            row = {
                "case_index": index,
                "case_id": case["case_id"],
                "ON_scan": hit["scan_id"],
                "carrier": hit["reference_carrier_index"],
                "original_disposition": hit["disposition"],
                "original_ON_score": hit["ON_robust_score"],
                "winning_width_channels": hit["width_channels"],
                "winning_drift_hz_s": hit["drift_hz_s"],
                "injected_intrinsic_width_channels": case["intrinsic_width_channels"],
                "injected_drift_hz_s": truth["drift_hz_s"],
                "injection_oracle_width_channels": oracle,
                "injected_pulse_row": pulse_row,
                "pulse_midpoint_time_from_tref_s": pulse_time,
                "first_ON_time_from_tref_s": first_time,
                "last_ON_time_from_tref_s": last_time,
                "winning_frequency_hz_at_tref": hit["reference_frequency_hz"],
                "true_frequency_hz_at_tref": truth["reference_frequency_hz"],
                "winning_path_frequency_hz_at_pulse_midpoint": hit["reference_frequency_hz"] + hit["drift_hz_s"] * pulse_time,
                "true_path_frequency_hz_at_pulse_midpoint": truth["reference_frequency_hz"] + truth["drift_hz_s"] * pulse_time,
                "signed_first_ON_frequency_error_over_abs_df": errors[0],
                "signed_pulse_midpoint_frequency_error_over_abs_df": errors[1],
                "signed_last_ON_frequency_error_over_abs_df": errors[2],
                "absolute_pulse_midpoint_frequency_error_over_abs_df": abs(errors[1]),
                "frozen_recovery_tolerance_over_abs_df": tolerance,
                "original_full_ON_endpoint_truth_localized": full_localized,
                "pulse_point_within_widthwise_oracle_tolerance": point_localized,
                "pulse_point_within_fixed_18_5_channel_widths": point_fixed,
                "point_comparison_is_not_an_original_recovery_gate": True,
            }
            output_rows.append(row)
            per_case.append(row)
        assert per_case
        summaries.append({
            "case_index": index,
            "case_id": case["case_id"],
            "active_ON_scan": scan["scan_id"],
            "transient_row": pulse_row,
            "pulse_midpoint_time_from_tref_s": pulse_time,
            "intrinsic_width_channels": case["intrinsic_width_channels"],
            "injected_drift_hz_s": truth["drift_hz_s"],
            "reference_native_offset": case["reference_native_offset"],
            "injection_oracle_width_channels": oracle,
            "original_surviving_carriers": len(per_case),
            "original_full_endpoint_localized_carriers": sum(row["original_full_ON_endpoint_truth_localized"] for row in per_case),
            "pulse_point_within_widthwise_oracle_tolerance_carriers": sum(row["pulse_point_within_widthwise_oracle_tolerance"] for row in per_case),
            "pulse_point_within_fixed_18_5_carriers": sum(row["pulse_point_within_fixed_18_5_channel_widths"] for row in per_case),
            "absolute_pulse_point_error_over_abs_df": absolute_stats([row["absolute_pulse_midpoint_frequency_error_over_abs_df"] for row in per_case]),
            "maximum_absolute_other_ON_endpoint_error_over_abs_df": max(abs(row["signed_last_ON_frequency_error_over_abs_df"] if pulse_row == 0 else row["signed_first_ON_frequency_error_over_abs_df"]) for row in per_case),
            "saved_winning_width_counts": dict(sorted(Counter(row["winning_width_channels"] for row in per_case).items())),
            "saved_winning_drift_hz_s_range": [min(row["winning_drift_hz_s"] for row in per_case), max(row["winning_drift_hz_s"] for row in per_case)],
        })
        bindings.append({
            "directory": relative,
            "manifest_sha256": sha(manifest_path),
            "COMMITTED_sha256": sha(marker_path),
            "verified_relevant_artifact_count": len(verified),
            "verified_relevant_artifacts": verified,
        })

    assert consumed == set(csv_by_key), "Not all retained transient CSV carriers were covered"
    counts = {
        "cases": len(summaries),
        "original_surviving_carriers": len(output_rows),
        "original_full_ON_endpoint_localized_carriers": sum(row["original_full_ON_endpoint_truth_localized"] for row in output_rows),
        "pulse_point_within_widthwise_oracle_tolerance_carriers": sum(row["pulse_point_within_widthwise_oracle_tolerance"] for row in output_rows),
        "pulse_point_within_fixed_18_5_carriers": sum(row["pulse_point_within_fixed_18_5_channel_widths"] for row in output_rows),
        "widthwise_point_match_but_not_original_full_endpoint_localization": sum(row["pulse_point_within_widthwise_oracle_tolerance"] and not row["original_full_ON_endpoint_truth_localized"] for row in output_rows),
    }
    assert counts["cases"] == evidence["counts"]["transient_cases"] == 12
    assert counts["original_surviving_carriers"] == evidence["counts"]["transient_original_carriers"] == evidence["counts"]["transient_final_carriers"]
    assert counts["original_full_ON_endpoint_localized_carriers"] == evidence["counts"]["transient_truth_localized_final_carriers"]
    assert all(row["pulse_point_within_widthwise_oracle_tolerance"] for row in output_rows if row["original_full_ON_endpoint_truth_localized"])
    result = {
        "status": "COMPLETE_RETAINED_WINNING_PATH_PULSE_GEOMETRY_ONLY",
        "source_commit": evidence["source_commit"],
        "input_sha256": {
            "DIAGNOSTIC_EVIDENCE.json": sha(evidence_path),
            "transient_original_carriers.csv": sha(csv_path),
            "pilot_controls_20261008/control_contract.json": sha(contract_path),
            "analyze_pulse_geometry.py": sha(Path(__file__)),
        },
        "original_frozen_code_sha256": evidence["original_code_sha256"],
        "original_case_bindings": bindings,
        "definitions": {
            "pulse_time": "retained active-ON first integration-centre time plus transient_row times frozen tsamp_s",
            "signed_error": "(saved_winning_reference_frequency - true_reference_frequency + (saved_winning_drift - true_drift) times selected_time) / abs(df_hz)",
            "signed_error_orientation": "physical frequency sign divided by positive channel width; not the signed native channel-index difference",
            "fixed_point_tolerance_channel_widths": FIXED_POINT_TOLERANCE,
            "widthwise_point_tolerance": "(2 + max(saved_winning_width, frozen_injection_oracle_width)/2) channel widths; applied to pulse time descriptively",
            "original_localization": "both full-ON integration-centre endpoints within the frozen widthwise tolerance",
        },
        "counts": counts,
        "absolute_pulse_point_error_over_abs_df": absolute_stats([row["absolute_pulse_midpoint_frequency_error_over_abs_df"] for row in output_rows]),
        "cases": summaries,
        "limitations": [
            "Only retained winning linear paths are compared; raw power, standardized residuals and row-level score contributions are not retained.",
            "A path crossing the known injected pulse time does not identify the cause or fraction of its score and is not a new detection/localization gate.",
            "Adjacent carriers and hypotheses are correlated responses to 12 injected events, not independent trials.",
            "Intrinsic width 1 is coupled to input drift -4, and width 3 to +4; placement and row effects are also not independently replicated here.",
            "The broad oracle tolerance includes within-integration frequency smearing; pulse time denotes the integration midpoint rather than an instantaneous point source measurement.",
        ],
        "qualification": False,
        "new_draws": 0,
        "new_scores": 0,
        "new_telescope_payloads": 0,
        "A_B_remain_FAIL_CLOSED": True,
    }
    with (OUT / "pulse_geometry.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)
    (OUT / "PULSE_GEOMETRY.json").write_text(json.dumps(result, indent=2) + "\n")
    total = counts["original_surviving_carriers"]
    full = counts["original_full_ON_endpoint_localized_carriers"]
    point = counts["pulse_point_within_widthwise_oracle_tolerance_carriers"]
    fixed = counts["pulse_point_within_fixed_18_5_carriers"]
    lines = [
        "# Geometri for gemte enkeltintegrationspulser",
        "",
        f"De 12 oprindelige B-transienter gav {total:,} overlevende ON-responser. {full:,} af dem opfyldte den oprindelige sandhedslokalisering ved begge ender af hele ON-scannet ({full / total:.1%}). Ved den kendte indsprøjtede integrations midtpunkt ligger {point:,} gemte vinderbaner inden for den samme breddeafhængige geometriske tolerance; med en fast tolerance på 18,5 kanalbredder er tallet {fixed:,}.",
        "",
        "Sammenligningen viser, hvor de allerede gemte rette vinderbaner passerer i forhold til den kendte puls. Den måler ikke pulsens tidsprofil eller bidrag til scoren: råeffekt, standardiserede residualer og scorebidrag pr. række er ikke gemt. Et punktmatch er en beskrivende geometri og erstatter ikke den oprindelige lokalisering over hele ON-scannet.",
        "",
        "Pulsen blev indsprøjtet i første eller sidste integration; derfor er dens midtpunkt også en af de to tidskoordinater i den oprindelige lokalisering. En bane kan ligge tæt på pulsen ved dette tidspunkt og afvige ved den anden ende. Mange nabocarrieres responser er korrelerede og udgør ikke selvstændige hændelser.",
        "",
        "| B-case | ON | Pulsrække | Gemte overlevere | Hele ON lokaliseret | Ved pulstid, breddeafhængig tolerance | Absolut fejl ved pulstid: min / median / maks, kanalbredder |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for item in summaries:
        stat = item["absolute_pulse_point_error_over_abs_df"]
        lines.append(f"| {item['case_id'].rsplit(':', 1)[1]} | {item['active_ON_scan']} | {item['transient_row']} | {item['original_surviving_carriers']} | {item['original_full_endpoint_localized_carriers']} | {item['pulse_point_within_widthwise_oracle_tolerance_carriers']} | {stat['minimum']:.4f} / {stat['median']:.4f} / {stat['maximum']:.4f} |")
    lines.extend([
        "",
        "Fortegnet i CSV-tabellen er en fysisk frekvensforskel divideret med den positive kanalbredde. Det er ikke den native kanalindeksforskel, eftersom frekvensaksen er faldende. Bredden 1 er koblet til indsprøjtet drift -4 Hz/s, og bredden 3 til +4 Hz/s; disse data giver ikke en selvstændig effektmåling af bredde, drift, placering eller rækkenummer.",
        "",
        "Inddata er kontrolleret mod de oprindelige case-manifester og COMMITTED-markører samt hashbindingerne i DIAGNOSTIC_EVIDENCE.json. Ingen effektdata er genskabt eller scorer beregnet. A og B forbliver fejlede; denne analyse er ikke en ny kvalifikation.",
    ])
    (OUT / "PULSE_GEOMETRY.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"status": result["status"], "counts": counts, "absolute_pulse_point_error_over_abs_df": result["absolute_pulse_point_error_over_abs_df"]}))


if __name__ == "__main__":
    main()
