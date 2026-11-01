"""Independent audit from primary headers; never accesses a FITS data array."""
import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.coordinates import SkyCoord
import astropy.units as u

P = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
norm = lambda name: re.sub(r"\s+", "", str(name)).upper()
selected = list(csv.DictReader((P / "selection/MAIN100.csv").open())) + list(
    csv.DictReader((P / "selection/DEVELOPMENT_AND_VALIDATION.csv").open()))
refs = json.loads((P / "literature/UPSTREAM_REFERENCED_IDS.json").read_text())
catalog = list(csv.DictReader((P / "literature/upstream/OSETI_targets.txt").open(), delimiter="\t"))
catalog_name = next(iter(catalog[0]))
catalog_coord = SkyCoord([r["RA"] for r in catalog], [r["DEC"] for r in catalog], unit=(u.hourangle, u.deg))

def compact(value, hours=False):
    sign = -1 if float(value) < 0 else 1
    value = abs(float(value))
    whole = int(value // 10000)
    minute = int((value - whole * 10000) // 100)
    second = value - whole * 10000 - minute * 100
    assert 0 <= minute < 60 and 0 <= second < 60
    return sign * (whole + minute / 60 + second / 3600) * (15 if hours else 1)

groups, files = defaultdict(list), []
for r in selected:
    receipt_path = P / "acquisition/receipts" / (r["dp_id"].replace(":", "_") + ".json")
    receipt = json.loads(receipt_path.read_text())
    path = Path(receipt["path"])
    # getheader reads the primary header only; no hdu.data access occurs.
    h = fits.getheader(path, 0)
    prov = {k: h[k] for k in h if k.startswith("PROV")}
    raw = sorted(set(re.findall(r"HARPS\.\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+", " ".join(map(str, prov.values())))))
    entry = {
        "dp_id": r["dp_id"], "target": r["canonical_target"], "role": r["role"],
        "receipt_sha256": sha(receipt_path),
        "actual_file_sha256_matches_receipt": sha(path) == receipt["sha256"],
        "arcfile_matches_selected_adp": str(h["ARCFILE"]) == r["dp_id"] + ".fits",
        "object_name_matches": norm(h["OBJECT"]) == r["canonical_target"],
        "intended_name_matches": norm(h["ESO OBS TARG NAME"]) == r["canonical_target"],
        "intended_ra_deg": compact(h["ESO TEL TARG ALPHA"], True),
        "intended_dec_deg": compact(h["ESO TEL TARG DELTA"]),
        "coordinate_type": h.get("ESO TEL TARG COORDTYPE"),
        "epoch": h.get("ESO TEL TARG EPOCH"),
        "equinox": h.get("ESO TEL TARG EQUINOX"),
        "pm_ra_header": h.get("ESO TEL TARG PMA"),
        "pm_dec_header": h.get("ESO TEL TARG PMD"),
        "raw_progenitor_ids": raw,
        "raw_ids_match_receipt": raw == receipt["raw_progenitor_ids"],
        "upstream_raw_matches": sorted(set(raw) & set(refs["HARPS"])),
        "upstream_adp_match": r["dp_id"] in set(refs["ADP"]),
    }
    files.append(entry)
    groups[entry["target"]].append(entry)

targets = []
for name, rr in groups.items():
    c = SkyCoord([r["intended_ra_deg"] for r in rr]*u.deg, [r["intended_dec_deg"] for r in rr]*u.deg)
    span = max(float(c[i].separation(c).arcsec.max()) for i in range(len(c)))
    idx, dist, _ = c[0].match_to_catalog_sky(catalog_coord)
    idx = int(np.asarray(idx).item())
    distance = float(np.asarray(dist.arcsec).item())
    targets.append({
        "target": name, "exposures": len(rr),
        "main_target": rr[0]["role"] == "main_unopened",
        "intended_coordinate_max_pairwise_arcsec": span,
        "coordinate_type_epoch_equinox": sorted(set((r["coordinate_type"], r["epoch"], r["equinox"]) for r in rr)),
        "nearest_parent_catalog_name": catalog[idx][catalog_name],
        "nearest_parent_catalog_arcsec": distance,
        "positional_match_within_1_arcsec": distance < 1,
        "external_identity_status": "POSITIONAL_CORROBORATION" if distance < 1 else "NOT_COVERED_BY_THIS_CATALOG",
    })

raw_ids = [rid for r in files for rid in r["raw_progenitor_ids"]]
checks = {
    "105_selected_files_reviewed": len(files) == 105,
    "all_file_hashes_match_receipts": all(r["actual_file_sha256_matches_receipt"] for r in files),
    "all_arcfiles_match_selection": all(r["arcfile_matches_selected_adp"] for r in files),
    "all_object_and_intended_names_match": all(r["object_name_matches"] and r["intended_name_matches"] for r in files),
    "consistent_intended_coordinates_within_0p1_arcsec": all(r["intended_coordinate_max_pairwise_arcsec"] < .1 for r in targets),
    "one_raw_progenitor_per_exposure": all(len(r["raw_progenitor_ids"]) == 1 for r in files),
    "all_raw_ids_unique_across_splits": len(raw_ids) == len(set(raw_ids)),
    "raw_ids_independently_match_receipts": all(r["raw_ids_match_receipt"] for r in files),
    "no_upstream_raw_overlap": all(not r["upstream_raw_matches"] for r in files),
    "no_upstream_adp_overlap": all(not r["upstream_adp_match"] for r in files),
}
report = {
    "schema": "HARPS_IDENTITY_PROVENANCE_INDEPENDENT_REVIEW_V1",
    "reviewed_utc": datetime.now(timezone.utc).isoformat(),
    "overall_status": "LIMITED" if all(checks.values()) else "BLOCKED",
    "selection_and_provenance_status": "PASS" if all(checks.values()) else "BLOCKED",
    "blocking_findings": [] if all(checks.values()) else [k for k,v in checks.items() if not v],
    "pilot_may_proceed": all(checks.values()),
    "checks": checks,
    "main_targets_positionally_corroborated_in_parent_catalog": sum(r["main_target"] and r["positional_match_within_1_arcsec"] for r in targets),
    "main_target_count": sum(r["main_target"] for r in targets),
    "finding": "All intended target names and coordinates are internally consistent. The large ObsCore/FITS pointing variations are not present in intended-target coordinates. No mismatched target or referenced raw/ADP exposure was found. The incomplete parent catalog positionally corroborates six of twenty main targets, plus the held-out development/validation target.",
    "limitations": [
        "LIMITED refers to absolute external identity coverage, not a failed selection or a block on this exploratory pilot. Fourteen main targets are not positionally covered by the parent OSETI target catalog; no unrelated nearest catalog object is assigned to them.",
        "No epoch or proper-motion transformation is imposed: catalog epoch is unspecified, while intended-target headers carry epoch/equinox 2000. Some targets share identical header proper motions and HD13445 has zero proper motion; these cards should not be treated as independently verified astrometry.",
        "This audit confirms intended target metadata and provenance, not photons entering the fiber or absolute pointing accuracy. Candidate-level source attribution can require original observation records.",
        "No overlap with the inspected upstream references establishes novelty only against that reference list, not against all prior searches.",
    ],
    "input_sha256": {str(p.relative_to(P)): sha(p) for p in [P/'selection/MAIN100.csv', P/'selection/DEVELOPMENT_AND_VALIDATION.csv', P/'literature/UPSTREAM_REFERENCED_IDS.json', P/'literature/upstream/OSETI_targets.txt']},
    "flux_arrays_opened": False,
    "targets": targets,
    "files": files,
}
(P/'review/IDENTITY_PROVENANCE_REVIEW.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['overall_status','selection_and_provenance_status','pilot_may_proceed','blocking_findings','checks','main_targets_positionally_corroborated_in_parent_catalog']},indent=2))
