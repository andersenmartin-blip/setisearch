#!/usr/bin/env python3
"""Reproducible expansion feasibility using existing metadata only.

No network functions, FITS imports, science files, or production hits are read.
Proposed CSV files are feasibility scenarios, not an executed or frozen sample.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re


CUTOFF = "2026-11-01T00:00:00Z"
BYTE_CAP = 2_000_000_000


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(name):
    return re.sub(r"\s+", "", name).upper()


def night(row):
    return math.floor(float(row["t_min"]) - 0.5)


def write_csv(path, rows, fields=None):
    fields = fields or list(rows[0])
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def evenly_spread(rows, number):
    rows = sorted(rows, key=lambda row: (float(row["t_min"]), row["dp_id"]))
    if number == 0:
        return []
    if number == 1:
        return [rows[len(rows)//2]]
    assert number <= len(rows)
    return [rows[round(index*(len(rows)-1)/(number-1))] for index in range(number)]


def choose_epochs(rows, number, prior_nights):
    """Maximize distinct nights; prefer new nights; use spaced night ranks."""
    by_night = {}
    for row in sorted(rows, key=lambda row: (float(row["t_min"]), row["dp_id"])):
        by_night.setdefault(night(row), row)
    fresh = [row for key, row in by_night.items() if key not in prior_nights]
    old = [row for key, row in by_night.items() if key in prior_nights]
    output = evenly_spread(fresh, min(number, len(fresh)))
    output += evenly_spread(old, min(number-len(output), len(old)))
    selected = {row["dp_id"] for row in output}
    remaining = [row for row in rows if row["dp_id"] not in selected]
    output += evenly_spread(remaining, number-len(output))
    return sorted(output, key=lambda row: (float(row["t_min"]), row["dp_id"]))


def category_summary(names, groups, summaries):
    occupied = [name for name in names if groups.get(name)]
    qualified = [name for name in occupied if summaries[name]["qualifies_5_epochs_3_nights"]]
    return {
        "target_roster_size": len(names), "targets_with_extra_exposures": len(occupied),
        "extra_exposures": sum(len(groups.get(name, [])) for name in names),
        "qualifying_target_groups": len(qualified), "qualifying_target_names": qualified,
        "exposures_in_qualifying_groups": sum(len(groups[name]) for name in qualified),
        "target_night_pairs": sum(summaries[name]["extra_distinct_nights"] for name in names),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("expansion"))
    args = parser.parse_args()
    root = args.project_root.resolve()
    out = args.output if args.output.is_absolute() else root / args.output
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "metadata": root / "access_probe/harps_post2019_metadata.csv",
        "main_selection": root / "selection/MAIN100.csv",
        "development_validation_selection": root / "selection/DEVELOPMENT_AND_VALIDATION.csv",
        "selection_record": root / "selection/SELECTION.json",
        "upstream_compact_ids": root / "literature/UPSTREAM_REFERENCED_IDS.json",
        "upstream_reference_records": root / "literature/upstream_referenced_exposure_ids.json",
    }
    source = list(csv.DictReader(paths["metadata"].open()))
    selection = json.loads(paths["selection_record"].read_text())
    assert len(source) == 5000 and sha(paths["metadata"]) == selection["metadata_sha256"]
    selected = list(csv.DictReader(paths["main_selection"].open()))
    selected += list(csv.DictReader(paths["development_validation_selection"].open()))
    assert len(selected) == 105
    selected_ids = {row["dp_id"] for row in selected}
    selected_starts = {(canonical(row["target_name"]), float(row["t_min"])) for row in selected}
    prior_nights = defaultdict(set)
    for row in selected:
        prior_nights[canonical(row["target_name"])].add(night(row))
    compact = json.loads(paths["upstream_compact_ids"].read_text())
    references = json.loads(paths["upstream_reference_records"].read_text())
    upstream_adp = set(compact["ADP"]) | {key for key in references["records"] if key.startswith("ADP.")}
    main_names = sorted(selection["main_targets"])
    development_names = sorted(selection["development_targets"])
    reasons = Counter()
    by_key = {}
    for original in source:
        row = dict(original)
        name = canonical(row["target_name"])
        if not re.fullmatch(r"HD\d+[AB]?", name):
            reasons["non_HD_name"] += 1
            continue
        if row["instrument_name"] != "HARPS":
            reasons["not_HARPS"] += 1
            continue
        if not row["obs_release_date"] or row["obs_release_date"] > CUTOFF:
            reasons["not_public_at_cutoff"] += 1
            continue
        if int(row["n_obs"]) != 1 or row["multi_ob"] != "S":
            reasons["not_single_exposure"] += 1
            continue
        if float(row["snr"] or 0) < 50:
            reasons["catalogue_snr_below_50"] += 1
            continue
        if float(row["t_exptime"]) < 300 or float(row["t_min"]) < 58849:
            reasons["time_or_exposure_cut"] += 1
            continue
        if row["dp_id"] in upstream_adp:
            reasons["upstream_referenced_ADP"] += 1
            continue
        key = (name, float(row["t_min"]))
        if row["dp_id"] in selected_ids or key in selected_starts:
            reasons["already_selected_ADP_or_same_target_start"] += 1
            continue
        row["canonical_target"] = name
        row["category"] = "original_main" if name in main_names else (
            "development_reserved" if name in development_names else "other_HD")
        if key in by_key:
            reasons["duplicate_target_start_reprocessing"] += 1
        if key not in by_key or row["dp_id"] > by_key[key]["dp_id"]:
            by_key[key] = row
    groups = defaultdict(list)
    for row in by_key.values():
        groups[row["canonical_target"]].append(row)
    for name in groups:
        groups[name].sort(key=lambda row: (float(row["t_min"]), row["dp_id"]))
    other_names = sorted(set(groups)-set(main_names)-set(development_names))
    summaries = {}
    for name in sorted(set(groups) | set(main_names) | set(development_names)):
        rows = groups.get(name, [])
        nights = {night(row) for row in rows}
        summaries[name] = {
            "canonical_target": name,
            "category": "original_main" if name in main_names else ("development_reserved" if name in development_names else "other_HD"),
            "extra_exposures": len(rows), "extra_distinct_nights": len(nights),
            "nights_absent_from_original_105": len(nights-prior_nights[name]),
            "qualifies_5_epochs_3_nights": len(rows) >= 5 and len(nights) >= 3,
            "exposure_seconds": sum(float(row["t_exptime"]) for row in rows),
            "earliest_mjd": min((float(row["t_min"]) for row in rows), default=None),
            "latest_mjd": max((float(row["t_min"]) for row in rows), default=None),
        }
    categories = {
        "original_main_targets": category_summary(main_names, groups, summaries),
        "other_HD_targets_excluding_development": category_summary(other_names, groups, summaries),
        "development_targets_reserved": category_summary(development_names, groups, summaries),
    }
    allocations = dict.fromkeys(main_names, 0)
    while sum(allocations.values()) < 100:
        progressed = False
        for name in main_names:
            if allocations[name] < len(groups.get(name, [])):
                allocations[name] += 1
                progressed = True
                if sum(allocations.values()) == 100:
                    break
        if not progressed:
            break
    proposal = []
    for name in main_names:
        for row in choose_epochs(groups.get(name, []), allocations[name], prior_nights[name]):
            proposal.append(dict(row, proposal_status="FEASIBILITY_ONLY_NOT_EXECUTED"))
    assert len(proposal) == 100 and len({row["dp_id"] for row in proposal}) == 100
    assert not ({row["dp_id"] for row in proposal} & (selected_ids | upstream_adp))
    assert not ({(row["canonical_target"], float(row["t_min"])) for row in proposal} & selected_starts)
    estimated_bytes = sum(math.ceil(float(row["access_estsize"])*1024) for row in proposal)
    assert estimated_bytes <= BYTE_CAP
    write_csv(out / "TARGET_INVENTORY.csv", list(summaries.values()))
    extra_rows = [row for name in sorted(groups) for row in groups[name]]
    write_csv(out / "EXTRA_ELIGIBLE_METADATA.csv", extra_rows)
    write_csv(out / "PROPOSED_BATCH100.csv", proposal)
    shortfalls = {name: len(groups.get(name, [])) for name in main_names if len(groups.get(name, [])) < 5}
    proposal_report = {
        "status": "FEASIBILITY_ONLY_NOT_EXECUTED_OR_FROZEN", "exposures": len(proposal),
        "targets_represented": sum(number > 0 for number in allocations.values()),
        "allocations": allocations, "five_per_original_target_possible": not shortfalls,
        "fewer_than_five_available": shortfalls, "five_per_target_cap_total": sum(min(5, len(groups.get(name, []))) for name in main_names),
        "exposure_seconds": sum(float(row["t_exptime"]) for row in proposal),
        "estimated_download_bytes_conservative": estimated_bytes,
        "estimated_download_gb_decimal": estimated_bytes / 1e9,
        "estimate_method": "access_estsize multiplied by 1024 per archive size unit, conservatively allowing binary kB interpretation; metadata estimate, not verified payload size.",
        "maximum_new_transfer_bytes_including_retries": BYTE_CAP,
        "selection_rule": "Target-balanced round-robin allocations in fixed alphabetical original-target order until 100, capped by each target's available metadata count; maximize distinct nights, prefer nights absent from the original 105, then evenly space available night ranks; fill any remaining quota using evenly spaced unused exposure ranks.",
        "target_night_pairs": len({(row["canonical_target"], night(row)) for row in proposal}),
        "new_target_night_pairs_vs_original105": len({(row["canonical_target"], night(row)) for row in proposal if night(row) not in prior_nights[row["canonical_target"]]}),
        "original_main_group_requirement_retained": "All original 20 targets qualified before the pilot. Three represented targets have fewer than five extra exposures; the proposal does not claim every extra-only target group meets 5 epochs/3 nights.",
    }
    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(), "status": "METADATA_ONLY_FEASIBILITY",
        "scope": "Existing bounded alphabetical 5000-row snapshot only; no archive refresh, downloads, FITS reads, or use of production hit values.",
        "code_sha256": sha(Path(__file__)),
        "input_hashes": {str(path.relative_to(root)): sha(path) for path in paths.values()},
        "public_release_cutoff_utc": CUTOFF, "input_rows": len(source),
        "quality_cuts": {"instrument": "HARPS", "target_name_regex": r"HD\d+[AB]?", "single_exposure": True,
                         "minimum_catalogue_snr": 50, "minimum_exptime_seconds": 300, "minimum_mjd_obs": 58849,
                         "unique_exposure_proxy": "normalized target plus numeric MJD start, retaining latest ADP ID",
                         "night_key": "floor(MJD-0.5), a noon-UTC boundary"},
        "upstream_adp_ids_excluded": len(upstream_adp), "excluded_selected_exposures": len(selected),
        "first_failing_cut_counts": dict(reasons), "extra_unique_metadata_exposures": len(extra_rows),
        "main_or_other_HD_metadata_candidates_excluding_development": categories["original_main_targets"]["extra_exposures"] + categories["other_HD_targets_excluding_development"]["extra_exposures"],
        "selected_overlap_exclusion": "Both selected ADP IDs and normalized target plus numeric t_min are excluded, removing alternative reprocessings with the same target and start time. Raw-ID identity checks remain PENDING.",
        "categories": categories, "proposed_batch100": proposal_report,
        "limitations": [
            "Raw progenitor matching against the original 105 and upstream references remains pending any future downloads; metadata target/start deduplication is not a proven raw-exposure identity.",
            "Absence from known upstream ADP references does not establish that data were never searched; prior-search coverage remains unknown.",
            "The snapshot's alphabetical order and 5000-row cap remain selection limitations; counts do not estimate all available HARPS data.",
            "Targets use catalog labels, not newly verified physical identities; future header and coordinate checks are required.",
            "Development stars remain a separate reserved category and are not proposed as new main targets.",
            "Future transfer size and scientific quality must be measured; no added exposure has been downloaded or analyzed by this feasibility task.",
        ],
        "network_requests": 0, "science_arrays_opened": 0,
        "output_csv_hashes": {path.name: sha(path) for path in sorted(out.glob("*.csv"))},
    }
    (out / "FEASIBILITY.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    main = categories["original_main_targets"]
    other = categories["other_HD_targets_excluding_development"]
    dev = categories["development_targets_reserved"]
    lines = [
        "# Mulig udvidelse af HARPS-piloten", "",
        "Opgørelsen bruger kun det eksisterende udsnit på 5.000 metadata-rækker og samme kvalitetskrav som piloten. Ingen nye spektre er hentet eller analyseret.", "",
        "| Datagruppe | Ekstra eksponeringer | Mål med ekstra data | Mål med ≥5 ekstra eksponeringer og ≥3 nætter |",
        "|---|---:|---:|---:|",
        f"| De oprindelige 20 hovedmål | {main['extra_exposures']} | {main['targets_with_extra_exposures']} | {main['qualifying_target_groups']} |",
        f"| Andre HD-mål, uden udviklingsstjerner | {other['extra_exposures']} | {other['targets_with_extra_exposures']} | {other['qualifying_target_groups']} |",
        f"| Udviklingsstjerner, holdt særskilt | {dev['extra_exposures']} | {dev['targets_with_extra_exposures']} | {dev['qualifying_target_groups']} |", "",
        f"Et konkret forslag er 100 ekstra eksponeringer fordelt så jævnt som muligt på de 19 oprindelige mål med ekstra data: 2–6 pr. mål. Estimeret overførsel er {estimated_bytes/1e9:.3f} GB, med en foreslået hård grænse på 2,0 GB inklusive gentagne forsøg. Datoer er spredt over de tilgængelige nætter; forslaget dækker {proposal_report['new_target_night_pairs_vs_original105']} nye mål/nat-par i forhold til de oprindelige 105 eksponeringer.", "",
        "Præcis fem ekstra til hvert af de 20 mål er ikke muligt i dette udsnit: HD114082 har 2, HD115031 4, HD119130 2 og HD13445 ingen. Et loft på fem pr. mål giver kun 88 ekstra eksponeringer.", "",
        "De 504 + 455 = 959 ekstra metadata-kandidater er endnu ikke endeligt verificerede eksponeringer. Forslaget er ikke en frosset eller udført ny analyse. Alle 105 tidligere valgte eksponeringer er udelukket både på ADP-ID og på normaliseret målnavn + t_min, så alternative reprocesseringer med samme mål og starttid ikke tælles som nye. Kendte upstream-ADP-referencer er også udelukket. Rå-ID-kontrol er PENDING og afventer eventuelle senere downloads. Tidligere søgninger i de resterende data er ukendte; fravær i referencelisten beviser ikke nyhed.", "",
        "Reproduktion fra projektroden: `python expansion/inventory_metadata.py --output expansion_repeat`. CSV-filerne gemmer måloversigt, alle resterende metadata samt det foreslåede batch på 100 eksponeringer.", "",
    ]
    (out / "FEASIBILITY.md").write_text("\n".join(lines))
    print(json.dumps({"extra_exposures": len(extra_rows), "categories": categories,
                      "proposed_batch100": proposal_report, "output": str(out)}, indent=2))


if __name__ == "__main__":
    main()
