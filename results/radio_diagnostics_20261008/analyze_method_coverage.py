#!/usr/bin/env python3
"""Describe authenticated, already computed METHOD report products.

This program reads only the three fixed published report products and their
local restoration receipt. It neither imports experiment modules nor opens
maps, generates samples, evaluates templates, or changes experiment claims.
Execute through the scope's run_bounded.py; all arithmetic is descriptive.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import statistics


SOURCE_COMMIT = "13131757641c06d7bfcb10790a79811c750b1178"
INPUT_DIR = Path("results/radio_pilot_method_report_20261008")
RECEIPT_PATH = Path("results/radio_diagnostics_20261008/RESTORED_METHOD_REPORT_INPUTS.json")
EXPECTED_INPUTS = {
    "method_cells.csv": {
        "git_blob_sha1": "ee77abf87b5bd83d69124fc1c5246161cd1a009e",
        "sha256": "59bbd848364ddf68045dd718ab56adeb81ac9322bbc1ecd17ad44d38f44447b7",
        "bytes": 22537,
    },
    "report_data.json": {
        "git_blob_sha1": "c94dd0612988e7ccc3bf45cb6116a058e6bc9773",
        "sha256": "e11b2c892f63e9033468f15aeec8bd57ebfeaf3cae4f789e30260497a4af1ab4",
        "bytes": 284875,
    },
    "report_artifact_manifest.json": {
        "git_blob_sha1": "513a3e1523610962dc6507870a1eeb2084277b1d",
        "sha256": "e71fc66034e86d23bb751d41735203925c6f2ea86b7549006801caea2ed1d640",
        "bytes": 3097,
    },
}
CASE_PREFIX = "SETI_RADIO_PILOT_20261008_METHOD_STUDY:method_signal:"
ON_THRESHOLD = 10.0  # Original frozen threshold, never re-estimated here.
SCANS = ("epoch1_on", "epoch2_on", "epoch3_on")
ACTIVE_SCANS = {
    "single_third_ON": ("epoch3_on",),
    "all_three_ON": SCANS,
}
BOOL_FIELDS = {
    "pre_OFF_all_active_recovered", "pre_OFF_any_active_recovered",
    "final_all_active_recovered", "final_any_active_recovered",
}
INT_FIELDS = {
    "intrinsic_width_channels", "ON_threshold_carrier_count",
    "surviving_ON_carrier_count", "peak_rss_bytes",
}
FLOAT_FIELDS = {
    "nominal_ideal_box_score", "drift_hz_s", "reference_native_offset",
    "cpu_s", "wall_s",
}
JSON_FIELDS = {
    "loss_stage_by_active_ON_scan", "ON_global_maximum_robust_score_by_scan",
}
FIELDS = {"case_id", "activity"} | BOOL_FIELDS | INT_FIELDS | FLOAT_FIELDS | JSON_FIELDS


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(data: bytes) -> dict:
    return {
        "git_blob_sha1": hashlib.sha1(
            b"blob " + str(len(data)).encode("ascii") + b"\0" + data
        ).hexdigest(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


def authenticate(root: Path) -> tuple[list[dict], dict]:
    receipt_bytes = (root / RECEIPT_PATH).read_bytes()
    receipt = json.loads(receipt_bytes)
    require(receipt.get("source_commit") == SOURCE_COMMIT, "Restoration source mismatch")
    require(receipt.get("all_Git_blob_SHA1_verified") is True, "Restoration not authenticated")
    require(receipt.get("new_scores") is False, "Restoration scope mismatch")
    records = receipt.get("records", [])
    record_map = {row["path"]: row for row in records}
    require(len(records) == len(record_map) == 3, "Restoration record set mismatch")
    require(set(record_map) == {str(INPUT_DIR / name) for name in EXPECTED_INPUTS},
            "Unexpected restored input path")
    input_bytes, verified = {}, []
    for name, expected in EXPECTED_INPUTS.items():
        relative = str(INPUT_DIR / name)
        data = (root / relative).read_bytes()
        actual = digest(data)
        require(actual == expected, f"Fixed published input mismatch: {relative}")
        require(all(record_map[relative].get(key) == value for key, value in expected.items()),
                f"Restoration receipt disagrees: {relative}")
        input_bytes[name] = data
        verified.append({"path": relative, **actual})
    manifest = json.loads(input_bytes["report_artifact_manifest.json"])
    for name in ("method_cells.csv", "report_data.json"):
        require(manifest[name]["SHA256"] == EXPECTED_INPUTS[name]["sha256"],
                f"Report manifest digest mismatch: {name}")
        require(manifest[name]["size_bytes"] == EXPECTED_INPUTS[name]["bytes"],
                f"Report manifest byte mismatch: {name}")

    csv_rows = list(csv.DictReader(io.StringIO(input_bytes["method_cells.csv"].decode("utf-8"))))
    cells = json.loads(input_bytes["report_data.json"])["method_cells"]
    require(len(csv_rows) == len(cells) == 64, "Expected exactly 64 retained METHOD cells")
    csv_by_id, json_by_id = {}, {}
    for row in csv_rows:
        require(set(row) == FIELDS, "Unexpected CSV field schema")
        decoded = {}
        for key, value in row.items():
            if key in BOOL_FIELDS:
                require(value in ("True", "False"), f"Invalid CSV boolean: {key}")
                decoded[key] = value == "True"
            elif key in INT_FIELDS:
                decoded[key] = int(value)
            elif key in FLOAT_FIELDS:
                decoded[key] = float(value)
            elif key in JSON_FIELDS:
                decoded[key] = json.loads(value)
            else:
                decoded[key] = value
        require(decoded["case_id"] not in csv_by_id, "Duplicate CSV case")
        csv_by_id[decoded["case_id"]] = decoded
    for cell in cells:
        require(set(cell) == FIELDS, "Unexpected JSON field schema")
        require(cell["case_id"] not in json_by_id, "Duplicate JSON case")
        json_by_id[cell["case_id"]] = cell
    expected_ids = {f"{CASE_PREFIX}{i:03d}" for i in range(64)}
    require(set(csv_by_id) == set(json_by_id) == expected_ids, "Case identity set mismatch")
    require(csv_by_id == json_by_id, "CSV and report JSON disagree field for field")
    cells = [json_by_id[f"{CASE_PREFIX}{i:03d}"] for i in range(64)]
    provenance = {
        "source_commit": SOURCE_COMMIT,
        "verified_inputs": verified,
        "restoration_receipt": {"path": str(RECEIPT_PATH), **digest(receipt_bytes)},
        "script": {"path": str(Path(__file__).resolve().relative_to(root)), **digest(Path(__file__).read_bytes())},
        "validation": {
            "fixed_Git_blob_SHA1_SHA256_and_bytes": True,
            "receipt_record_set_and_hashes": True,
            "report_manifest_csv_and_json_hashes": True,
            "CSV_JSON_exact_field_equality": True,
            "case_identity_set": True,
        },
        "original_map_archives_opened": 0,
        "new_draws": 0,
        "new_scores": 0,
        "thresholds_changed": False,
        "qualification": False,
    }
    return cells, provenance


def distribution(values: list[float]) -> dict:
    require(bool(values), "Empty descriptive distribution")
    require(all(math.isfinite(value) for value in values), "Nonfinite statistic")
    return {
        "count": len(values),
        "minimum": min(values),
        "median": statistics.median(values),
        "maximum": max(values),
    }


def summarize(group_id: str, selected_cells: list[dict], scans: list[dict]) -> dict:
    return {
        "group": group_id,
        "case_denominator": len(selected_cells),
        "final_ALL_cases": sum(cell["final_all_active_recovered"] for cell in selected_cells),
        "final_ANY_cases": sum(cell["final_any_active_recovered"] for cell in selected_cells),
        "active_ON_scan_denominator": len(scans),
        "localized_survivor_active_ON_scans": sum(row["localized_survivor"] for row in scans),
        "NO_ON_THRESHOLD_HIT_active_ON_scans": sum(not row["localized_survivor"] for row in scans),
        "global_maximum_robust_score": distribution([row["global_maximum_robust_score"] for row in scans]),
        "global_maximum_divided_by_nominal_ideal": distribution(
            [row["global_maximum_divided_by_nominal_ideal"] for row in scans]),
        "scan_weighting": "Each active ON scan contributes one saved global maximum; scans within a case are not independent trials.",
    }


def analyze(cells: list[dict]) -> tuple[list[dict], list[dict], list[dict], dict]:
    expected_cells = set(itertools.product(
        (10.0, 12.0, 16.0, 24.0), (-4.0, -1.25, 1.25, 4.0),
        (1, 3), tuple(ACTIVE_SCANS),
    ))
    observed_cells = [
        (cell["nominal_ideal_box_score"], cell["drift_hz_s"],
         cell["intrinsic_width_channels"], cell["activity"])
        for cell in cells
    ]
    require(len(set(observed_cells)) == 64 and set(observed_cells) == expected_cells,
            "Not one observation for every declared four-factor cell")
    placements = (0.25, 1024.25, 3070.75, 4094.75)
    require(all(sum(cell["reference_native_offset"] == p for cell in cells) == 16 for p in placements),
            "Published placement margins not balanced")
    scans, case_rows = [], []
    for cell in cells:
        active = ACTIVE_SCANS[cell["activity"]]
        stages = cell["loss_stage_by_active_ON_scan"]
        maxima = cell["ON_global_maximum_robust_score_by_scan"]
        require(set(stages) == set(active), "Active ON exposure list mismatch")
        require(set(maxima) == set(SCANS), "Saved ON maximum scan set mismatch")
        require(all(math.isfinite(float(value)) for value in maxima.values()), "Nonfinite saved maximum")
        require(all(stage in ("LOCALIZED_SURVIVOR", "NO_ON_THRESHOLD_HIT") for stage in stages.values()),
                "Unexpected originating loss stage")
        localized = [stages[scan] == "LOCALIZED_SURVIVOR" for scan in active]
        require(all(localized) == cell["final_all_active_recovered"], "ALL disagrees with scan dispositions")
        require(any(localized) == cell["final_any_active_recovered"], "ANY disagrees with scan dispositions")
        require(cell["pre_OFF_all_active_recovered"] == cell["final_all_active_recovered"] and
                cell["pre_OFF_any_active_recovered"] == cell["final_any_active_recovered"],
                "Unexpected METHOD OFF loss")
        require(cell["ON_threshold_carrier_count"] == cell["surviving_ON_carrier_count"],
                "Unexpected carrier veto in METHOD")
        case_scans = []
        for scan in active:
            score = float(maxima[scan])
            recovered = stages[scan] == "LOCALIZED_SURVIVOR"
            # This verifies a relationship observed in these saved results only;
            # a global maximum is not a truth-localized test in general.
            require((score >= ON_THRESHOLD) == recovered,
                    "Global threshold crossing and saved disposition differ in this retained panel")
            row = {
                "case_id": cell["case_id"], "scan_id": scan,
                "nominal_ideal_box_score": cell["nominal_ideal_box_score"],
                "drift_hz_s": cell["drift_hz_s"],
                "intrinsic_width_channels": cell["intrinsic_width_channels"],
                "activity": cell["activity"],
                "reference_native_offset": cell["reference_native_offset"],
                "global_maximum_robust_score": score,
                "global_maximum_divided_by_nominal_ideal": score / cell["nominal_ideal_box_score"],
                "margin_above_original_ON_threshold": score - ON_THRESHOLD,
                "original_loss_stage": stages[scan],
                "localized_survivor": recovered,
                "case_final_ALL": cell["final_all_active_recovered"],
                "case_final_ANY": cell["final_any_active_recovered"],
            }
            scans.append(row)
            case_scans.append(row)
        case_rows.append({
            "case_id": cell["case_id"],
            "nominal_ideal_box_score": cell["nominal_ideal_box_score"],
            "drift_hz_s": cell["drift_hz_s"],
            "intrinsic_width_channels": cell["intrinsic_width_channels"],
            "activity": cell["activity"],
            "reference_native_offset": cell["reference_native_offset"],
            "active_ON_scan_denominator": len(active),
            "localized_survivor_active_ON_scans": sum(localized),
            "NO_ON_THRESHOLD_HIT_active_ON_scans": len(active) - sum(localized),
            "final_ALL": cell["final_all_active_recovered"],
            "final_ANY": cell["final_any_active_recovered"],
            "minimum_active_ON_global_maximum": min(row["global_maximum_robust_score"] for row in case_scans),
            "median_active_ON_global_maximum": statistics.median(row["global_maximum_robust_score"] for row in case_scans),
            "maximum_active_ON_global_maximum": max(row["global_maximum_robust_score"] for row in case_scans),
            "ON_threshold_carrier_count": cell["ON_threshold_carrier_count"],
            "surviving_ON_carrier_count": cell["surviving_ON_carrier_count"],
        })
    misses = [row for row in scans if not row["localized_survivor"]]
    require(len(scans) == 128 and len(misses) == 13, "Retained active scan/miss totals changed")
    require(len({row["case_id"] for row in misses}) == 12, "Retained failed-case total changed")
    require(sum(row["final_ALL"] for row in case_rows) == 52, "Retained ALL total changed")
    require(sum(row["final_ANY"] for row in case_rows) == 59, "Retained ANY total changed")
    require(sum(row["ON_threshold_carrier_count"] for row in case_rows) == 7051,
            "Retained METHOD carrier total changed")

    groups = [summarize("ALL_64_CASES", cells, scans)]
    dimensions = (
        "nominal_ideal_box_score", "activity", "drift_hz_s",
        "intrinsic_width_channels", "reference_native_offset",
    )
    for dimension in dimensions:
        for value in sorted({cell[dimension] for cell in cells}):
            selected = [cell for cell in cells if cell[dimension] == value]
            selected_scans = [row for row in scans if row[dimension] == value]
            groups.append(summarize(f"{dimension}={value}", selected, selected_scans))
    for nominal, activity in itertools.product((10.0, 12.0, 16.0, 24.0), ACTIVE_SCANS):
        selected = [cell for cell in cells if cell["nominal_ideal_box_score"] == nominal and cell["activity"] == activity]
        selected_scans = [row for row in scans if row["nominal_ideal_box_score"] == nominal and row["activity"] == activity]
        groups.append(summarize(f"nominal_ideal_box_score={nominal};activity={activity}", selected, selected_scans))
    summary = {
        "case_count": 64,
        "active_ON_scan_count": 128,
        "localized_survivor_active_ON_scans": sum(row["localized_survivor"] for row in scans),
        "NO_ON_THRESHOLD_HIT_active_ON_scans": 13,
        "cases_with_any_missed_active_ON_scan": 12,
        "final_ALL_cases": 52,
        "final_ANY_cases": 59,
        "pre_OFF_to_final_case_recovery_losses": 0,
        "surviving_carriers": 7051,
        "carrier_count_is_not_independent_trial_count": True,
        "original_ON_threshold": ON_THRESHOLD,
        "groups": groups,
    }
    return scans, case_rows, misses, summary


def write_csv(path: Path, rows: list[dict]) -> None:
    require(bool(rows), "Refusing schema-free empty CSV")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def flat_groups(groups: list[dict]) -> list[dict]:
    flattened = []
    for group in groups:
        row = {key: value for key, value in group.items() if not isinstance(value, dict)}
        for metric in ("global_maximum_robust_score", "global_maximum_divided_by_nominal_ideal"):
            for statistic, value in group[metric].items():
                row[f"{metric}_{statistic}"] = value
        flattened.append(row)
    return flattened


def report_text(summary: dict, misses: list[dict], provenance: dict) -> str:
    groups = {row["group"]: row for row in summary["groups"]}
    lines = [
        "# Gemte METHOD-maksima og dækningsgrænser — 8. oktober 2026",
        "",
        "De 64 allerede afsluttede METHOD-forsøg indeholder 128 aktive ON-scans. "
        "I 13 scans fordelt på 12 forsøg ligger det gemte globale maksimum under den oprindelige "
        "ON-grænse på 10. Derfor blev ingen ON-bærer udvalgt i disse scans. Det samlede resultat "
        "er fortsat ALL 52/64 og ANY 59/64; der er ingen yderligere tab gennem OFF-kontrollen i METHOD.",
        "",
        "ALL kræver et sandhedslokaliseret overlevende hit i hvert aktivt ON-scan; ANY kræver mindst "
        "ét aktivt ON-scan med et sådant hit. Single-third-ON har ét aktivt scan per forsøg, "
        "all-three-ON har tre. Scan-tællinger og forsøgs-tællinger har forskellige nævnere.",
        "",
        "Det nominelle idealniveau er generatorens støjfri boksprojektion. De observerede tal her "
        "er det **gemte globale maksimum af den robuste detektorstatistik over de søgte skabeloner** "
        "i hvert aktivt scan. Maksimum er udvalgt efter en søgning og er derfor ikke et ubetinget "
        "estimat af den indsprøjtede linjes amplitude, en sandhedslokaliseret statistik, målt SNR "
        "eller flux. Forholdet maksimum/ideal nedenfor er udelukkende en beskrivende sammenligning "
        "af disse to forskellige størrelser.",
        "",
        "| Nominelt idealniveau | ALL/forsøg | ANY/forsøg | Overlevende aktive ON-scans | Scans under ON=10 | Gemt globalt maksimum, min / median / max | Maksimum/ideal, min / median / max |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for nominal in (10.0, 12.0, 16.0, 24.0):
        group = groups[f"nominal_ideal_box_score={nominal}"]
        score, ratio = group["global_maximum_robust_score"], group["global_maximum_divided_by_nominal_ideal"]
        lines.append(
            f"| {nominal:g} | {group['final_ALL_cases']}/{group['case_denominator']} | "
            f"{group['final_ANY_cases']}/{group['case_denominator']} | "
            f"{group['localized_survivor_active_ON_scans']}/{group['active_ON_scan_denominator']} | "
            f"{group['NO_ON_THRESHOLD_HIT_active_ON_scans']}/{group['active_ON_scan_denominator']} | "
            f"{score['minimum']:.3f} / {score['median']:.3f} / {score['maximum']:.3f} | "
            f"{ratio['minimum']:.3f} / {ratio['median']:.3f} / {ratio['maximum']:.3f} |"
        )
    lines.extend([
        "",
        "Tabene findes ved idealniveau 10 og 12 i dette konkrete panel. Niveaustrinnene 16 og 24 "
        "genfindes i alle deres aktive ON-scans, men 16/16 forsøg er ingen dokumentation for "
        "garanteret genfinding eller en generel detektionssandsynlighed. Tallene forklarer ikke, "
        "hvilken del af forskellen der skyldes støj, skabelonvalg eller behandling af data; "
        "de originale rapportprodukter indeholder ikke en sandhedslokaliseret statistik under ON-grænsen.",
        "",
        "| Aktivitet | ALL/forsøg | ANY/forsøg | Overlevende aktive ON-scans | Scans under ON=10 |",
        "|---|---:|---:|---:|---:|",
    ])
    for activity in ACTIVE_SCANS:
        group = groups[f"activity={activity}"]
        lines.append(f"| {activity} | {group['final_ALL_cases']}/{group['case_denominator']} | "
                     f"{group['final_ANY_cases']}/{group['case_denominator']} | "
                     f"{group['localized_survivor_active_ON_scans']}/{group['active_ON_scan_denominator']} | "
                     f"{group['NO_ON_THRESHOLD_HIT_active_ON_scans']}/{group['active_ON_scan_denominator']} |")
    lines.extend([
        "",
        "De to aktivitetsgrupper er forskellige støjrealiseringer med forskellige eksponeringer; "
        "de er ikke parrede målinger. Der er én realisering per celle af idealniveau × drift × "
        "intrinsisk bredde × aktivitet. De fire frekvensplaceringer er balanceret i marginalerne, "
        "men ikke gentaget fuldt inden for hver celle. Grupper efter drift, bredde, placering og "
        "aktivitet findes med begge nævnere i maskinfilerne; de fastslår ingen kausal effekt. "
        "Scans fra samme forsøg og de 7.051 overlevende bærere er heller ikke uafhængige forsøg.",
        "",
        "De 13 mistede aktive ON-scans:",
        "",
        "| Forsøgsnummer | ON-scan | Idealniveau | Gemt globalt maksimum | Afstand under ON=10 | Drift (Hz/s) | Intrinsisk bredde (kanaler) | Aktivitet |",
        "|---:|---|---:|---:|---:|---:|---:|---|",
    ])
    for row in misses:
        lines.append(
            f"| {row['case_id'].rsplit(':', 1)[1]} | {row['scan_id']} | "
            f"{row['nominal_ideal_box_score']:g} | {row['global_maximum_robust_score']:.6f} | "
            f"{-row['margin_above_original_ON_threshold']:.6f} | {row['drift_hz_s']:g} | "
            f"{row['intrinsic_width_channels']} | {row['activity']} |"
        )
    lines.extend([
        "",
        "Alle 13 dispositioner er oprindeligt NO_ON_THRESHOLD_HIT. I netop dette panel stemmer "
        "globalt maksimum ≥10 overens med den gemte lokaliserede scan-genfinding i de øvrige 115 "
        "aktive ON-scans; dette er en kontrolleret egenskab ved disse resultater og ingen generel "
        "regel, der sidestiller globale og lokaliserede statistikker.",
        "",
        "I en senere, særskilt godkendt plan er prioriteten at skille den støjfri idealprojektion, "
        "en på forhånd fastlagt statistik ved den sande bane og det maksimum, en søgning udvælger. "
        "Friske gentagne realiseringer omkring ON-grænsen bør dække bredde, drift, aktivitet og "
        "placering med fastlagte gentagelser. Det ville kunne undersøge dækningsvariation og "
        "skabelonmismatch uden at kalde et udvalgt maksimum en fluxkalibrering. Denne analyse "
        "ændrer ingen tærskel eller skabelon, og en senere ændring kræver ny separat kvalifikation.",
        "",
        f"Kildecommit: `{provenance['source_commit']}`. De tre inputprodukter er kontrolleret mod "
        "de faste Git-blob-SHA1, SHA256 og byteantal, deres restaureringskvittering og den oprindelige "
        "rapportmanifest. CSV og JSON er sammenlignet felt for felt for alle 64 celler. Ingen "
        "kortarkiver blev åbnet, ingen signaler eller støj blev genereret, og ingen score blev beregnet på ny. "
        "A/B-status forbliver fejlet; METHOD er et eksplorativt metodestudie.",
        "",
        "Maskinfiler: `method_active_ON_scores.csv` (128 scans), `method_case_coverage.csv` "
        "(64 forsøg), `method_coverage_groups.csv` (beskrivende grupper), "
        "`method_missed_active_ON_scans.csv` (13 scans) og `METHOD_COVERAGE.json` "
        "(definitioner, nævnere, proveniens og fulde præcisionsværdier). Medianen er den "
        "almindelige stikprøvemedian: det midterste tal eller gennemsnittet af de to midterste "
        "ved et lige antal; der anvendes ingen kvantiler eller interpolerede detektionskurver.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output-directory", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    root, output = args.project_root.resolve(), args.output_directory.resolve()
    require(output == (root / "results/radio_diagnostics_20261008").resolve(),
            "Output must remain in the new diagnostics directory")
    cells, provenance = authenticate(root)
    scans, case_rows, misses, summary = analyze(cells)
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "status": "DESCRIPTIVE_RETAINED_METHOD_COVERAGE_COMPLETE",
        "provenance": provenance,
        "definitions": {
            "nominal_ideal_box_score": "Original noiseless ideal box projection declared by the generator; not measured robust SNR or flux.",
            "global_maximum_robust_score": "Saved maximum of the robust detector statistic across searched templates in an ON scan, not a truth-localized statistic.",
            "global_maximum_divided_by_nominal_ideal": "Descriptive ratio of a selected search maximum to a noiseless ideal projection; not an estimator of efficiency, SNR recovery or flux calibration.",
            "ALL": "Every active ON scan has an original truth-localized surviving hit.",
            "ANY": "At least one active ON scan has an original truth-localized surviving hit.",
            "median": "statistics.median: middle sorted value or arithmetic mean of the two middle values for even sample size.",
            "independence": "No independence claimed for scans within cases or template/carrier responses.",
            "design": "One realization per level x drift x intrinsic width x activity cell; placement margins balanced but placement interactions not fully replicated.",
        },
        "summary": summary,
        "missed_active_ON_scans": misses,
        "active_ON_scans": scans,
        "case_coverage": case_rows,
    }
    write_csv(output / "method_active_ON_scores.csv", scans)
    write_csv(output / "method_case_coverage.csv", case_rows)
    write_csv(output / "method_coverage_groups.csv", flat_groups(summary["groups"]))
    write_csv(output / "method_missed_active_ON_scans.csv", misses)
    (output / "METHOD_COVERAGE.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "METHOD_COVERAGE.md").write_text(report_text(summary, misses, provenance), encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "cases": 64, "active_ON_scans": 128, "missed_active_ON_scans": 13,
        "missed_cases": 12, "ALL": 52, "ANY": 59,
        "new_scores": 0, "new_draws": 0, "qualification": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
