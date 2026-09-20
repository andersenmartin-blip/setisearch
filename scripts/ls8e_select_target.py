#!/usr/bin/env python3
"""Metadata-only LS8E CHEOPS target/product selection.

No CHEOPS product download function is called. Selection uses only visit
database metadata and product-name inventories under the public frozen rule.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results_ls8e_selection"

TARGETS = [
    (1, "GJ 876", ["GJ 876", "GJ876"]),
    (2, "HD 219134", ["HD 219134", "HD219134"]),
    (3, "GJ 514", ["GJ 514", "GJ514"]),
    (4, "GJ 849", ["GJ 849", "GJ849"]),
    (5, "GJ 649", ["GJ 649", "GJ649"]),
    (6, "HD 147379", ["HD 147379", "HD147379"]),
    (7, "55 Cnc", ["55 Cnc", "55Cnc"]),
    (8, "47 UMa", ["47 UMa", "47UMa"]),
    (9, "HD 48948", ["HD 48948", "HD48948"]),
    (10, "rho CrB", ["rho CrB", "rhoCrB"]),
]
EXCLUDED = {"55 Cnc"}
REQUIRED_TYPES = {"SCI_CAL_SubArray", "SCI_COR_SubArray"}
MAX_STACKED_EXPOSURE = 60.0


def scalar(value: Any) -> Any:
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, bytes):
        return value.decode()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def dict_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    if not data:
        return []
    lengths = [len(v) for v in data.values() if hasattr(v, "__len__") and not isinstance(v, (str, bytes))]
    if not lengths:
        return []
    n = min(lengths)
    return [{k: scalar(v[i]) for k, v in data.items()} for i in range(n)]


def norm_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def exact_target(row: dict[str, Any], aliases: list[str]) -> bool:
    value = norm_name(str(row.get("obj_id_catname") or ""))
    return value in {norm_name(a) for a in aliases}


def basic_visit_eligibility(row: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons = []
    key = str(row.get("file_key") or "")
    if not key.endswith("_V0300"):
        reasons.append("NOT_V0300")
    if str(row.get("data_pipe_version") or "") != "14.1.2":
        reasons.append("PIPE_NOT_14_1_2")
    if row.get("status_published") is not True:
        reasons.append("NOT_PUBLISHED")
    if row.get("db_lc_available") is not True:
        reasons.append("NO_PUBLIC_LC")
    try:
        exptime = float(row.get("obs_exptime"))
        nexp = int(row.get("obs_nexp"))
        stacked = float(row.get("obs_total_exptime"))
        if not (math.isfinite(exptime) and exptime > 0):
            reasons.append("BAD_EXPTIME")
        if nexp <= 0:
            reasons.append("BAD_NEXP")
        if not (math.isfinite(stacked) and 0 < stacked <= MAX_STACKED_EXPOSURE):
            reasons.append("STACKED_EXPOSURE_OUTSIDE_BOUND")
    except (TypeError, ValueError):
        reasons.append("MISSING_EXPOSURE_METADATA")
    if not key:
        reasons.append("NO_FILE_KEY")
    return not reasons, reasons


def product_flags(products: dict[str, Any]) -> dict[str, Any]:
    rows = dict_rows(products)
    types = {str(r.get("file_ext") or "") for r in rows}
    files = [str(r.get("file") or "") for r in rows]
    default_lc = any("SCI_COR_Lightcurve-DEFAULT" in f and f.endswith("_V0300.fits") for f in files)
    return {
        "product_rows": len(rows),
        "has_default_lightcurve": default_lc,
        "has_cal_subarray": "SCI_CAL_SubArray" in types,
        "has_cor_subarray": "SCI_COR_SubArray" in types,
        "eligible": default_lc and REQUIRED_TYPES <= types,
        "files": files,
        "file_types": sorted(types),
    }


def choose_target(candidate_ledgers: list[dict[str, Any]]) -> dict[str, Any] | None:
    for target in candidate_ledgers:
        if target["target"] in EXCLUDED:
            continue
        eligible = [v for v in target["visits"] if v["eligible"]]
        eligible.sort(key=lambda r: (float(r["date_mjd_start"]), str(r["file_key"])))
        if len(eligible) >= 2:
            return {
                "target_rank": target["rank"],
                "target": target["target"],
                "eligible_visit_count": len(eligible),
                "selected_visits": eligible[:2],
            }
    return None


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main() -> None:
    assert not OUT.exists(), "refuse completed LS8E selection overwrite"
    OUT.mkdir()
    (OUT / "queries").mkdir()
    (OUT / "products").mkdir()

    # Imported here so unit tests for the pure selection functions need no
    # network client or dace-query installation.
    from dace_query import DaceClass
    from dace_query.cheops import CheopsClass

    client = CheopsClass(DaceClass(dace_rc_config_path=Path("/dev/null")))
    ledgers = []

    for rank, target, aliases in TARGETS:
        if target in EXCLUDED:
            ledgers.append({
                "rank": rank, "target": target, "aliases": aliases,
                "excluded_before_query": True, "reason": "PREVIOUS_55_CNC_BRANCH_CLOSED",
                "visits": [],
            })
            continue

        merged: dict[str, dict[str, Any]] = {}
        query_records = []
        for alias in aliases:
            result = client.query_database(
                limit=200,
                filters={"obj_id_catname": {"contains": [alias]}},
                sort={"date_mjd_start": "asc"},
                output_format="dict",
            )
            plain = {k: [scalar(x) for x in v] for k, v in result.items()}
            query_records.append({"alias": alias, "result": plain})
            for row in dict_rows(result):
                if exact_target(row, aliases):
                    key = str(row.get("file_key") or "")
                    if key:
                        merged[key] = row

        save(OUT / "queries" / f"{rank:02d}_{norm_name(target)}.json", {
            "rank": rank, "target": target, "aliases": aliases,
            "query_records": query_records,
        })

        visits = []
        for row in sorted(merged.values(), key=lambda r: (float(r.get("date_mjd_start") or 1e99), str(r.get("file_key") or ""))):
            base_ok, reasons = basic_visit_eligibility(row)
            record = {
                "file_key": str(row.get("file_key") or ""),
                "visit_id": scalar(row.get("visit_id")),
                "obs_id": scalar(row.get("obs_id")),
                "target_name": scalar(row.get("obj_id_catname")),
                "date_mjd_start": scalar(row.get("date_mjd_start")),
                "date_mjd_end": scalar(row.get("date_mjd_end")),
                "data_pipe_version": scalar(row.get("data_pipe_version")),
                "data_arch_rev": scalar(row.get("data_arch_rev")),
                "obs_exptime": scalar(row.get("obs_exptime")),
                "obs_nexp": scalar(row.get("obs_nexp")),
                "obs_total_exptime": scalar(row.get("obs_total_exptime")),
                "status_published": scalar(row.get("status_published")),
                "db_lc_available": scalar(row.get("db_lc_available")),
                "basic_eligible": base_ok,
                "reasons": list(reasons),
            }
            if base_ok:
                products = client.browse_products(
                    filters={"file_key": {"equal": [record["file_key"]]}},
                    file_type="all", output_format="dict",
                )
                flags = product_flags(products)
                save(OUT / "products" / f"{record['file_key']}.json", flags)
                record["products"] = {k: v for k, v in flags.items() if k != "files"}
                if not flags["eligible"]:
                    if not flags["has_default_lightcurve"]:
                        record["reasons"].append("NO_DEFAULT_LIGHTCURVE_PRODUCT")
                    if not flags["has_cal_subarray"]:
                        record["reasons"].append("NO_CAL_SUBARRAY")
                    if not flags["has_cor_subarray"]:
                        record["reasons"].append("NO_COR_SUBARRAY")
            record["eligible"] = base_ok and not record["reasons"]
            visits.append(record)

        ledgers.append({
            "rank": rank, "target": target, "aliases": aliases,
            "excluded_before_query": False,
            "matched_file_keys": len(merged),
            "visits": visits,
        })

    selection = choose_target(ledgers)
    result = {
        "stage": "LS8E_METADATA_ONLY_TARGET_SELECTION",
        "status": "SELECTED" if selection else "NO_ELIGIBLE_TARGET_IN_FROZEN_LIST",
        "frozen_target_order": [t for _, t, _ in TARGETS],
        "excluded_targets": sorted(EXCLUDED),
        "requirements": {
            "visit_version": "V0300",
            "pipeline": "14.1.2",
            "published": True,
            "public_lightcurve_available": True,
            "max_stacked_exposure_seconds": MAX_STACKED_EXPOSURE,
            "required_products": ["SCI_COR_Lightcurve-DEFAULT", "SCI_CAL_SubArray", "SCI_COR_SubArray"],
            "minimum_eligible_visits": 2,
            "pair_rule": "two chronologically earliest eligible visits of first eligible host",
        },
        "candidate_ledgers": ledgers,
        "selection": selection,
        "science_product_bytes_read": 0,
        "fits_table_rows_read": 0,
        "image_pixels_read": 0,
        "lightcurve_values_read": 0,
        "product_download_calls": 0,
    }
    save(OUT / "selection.json", result)

    files = sorted(p for p in OUT.rglob("*") if p.is_file())
    (OUT / "SHA256SUMS").write_text("".join(
        f"{sha(p)}  {p.relative_to(OUT)}\n" for p in files
        if p.name != "SHA256SUMS"
    ))
    print(json.dumps({
        "status": result["status"],
        "selection": selection,
        "targets_queried": sum(not x.get("excluded_before_query", False) for x in ledgers),
        "science_product_bytes_read": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
