#!/usr/bin/env python3
"""Stage 1 live acquisition: Gaia DR3 NSS, Brandt HGCA, Kervella PMa + Gaia BH1/2/3 (Spor N9)."""
from __future__ import annotations

import csv
import json
import math
import socket
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_getaddrinfo(*args: Any, **kwargs: Any) -> Any:
    return [r for r in _orig_getaddrinfo(*args, **kwargs) if r[0] == socket.AF_INET]


socket.getaddrinfo = _ipv4_getaddrinfo

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
INP = ROOT / "inputs_n9_20261127"
MASTER_CSV = ROOT / "setisearch/zenodo_package/tables/table1_master_catalog_1083stars.csv"
GAIA_CSV = ROOT / "inputs_n5_20261127/gaia/gaia_dr3_1096.csv"

BH_BENCHMARKS = [
    {"star": "GAIA_BH1", "common_name": "Gaia BH1 (9.6 Msun Stellar-Mass BH, 478 pc)", "source_id": "4373465352415301632", "dist_pc": "477.6", "within_10pc": "False", "n_exoplanets": "0"},
    {"star": "GAIA_BH2", "common_name": "Gaia BH2 (8.9 Msun Red-Giant + BH, 1.16 kpc)", "source_id": "5870569352746779008", "dist_pc": "1160.0", "within_10pc": "False", "n_exoplanets": "0"},
    {"star": "GAIA_BH3", "common_name": "Gaia BH3 (32.7 Msun Halo BH, 590 pc)", "source_id": "4318465066420528000", "dist_pc": "590.6", "within_10pc": "False", "n_exoplanets": "0"},
]


def _http_post_vizier(params: dict[str, str], timeout: int = 50) -> bytes:
    data = urllib.parse.urlencode(params).encode("utf-8")
    last_err: Exception | None = None
    for i in range(5):
        try:
            req = urllib.request.Request(
                "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "SETI-N9/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last_err = e
            time.sleep(2.0 * (i + 1))
    raise RuntimeError(f"VizieR POST failed {params.get('-source')}: {last_err}")


def parse_vizier_tsv(txt: str) -> list[dict[str, str]]:
    lines = [l for l in txt.splitlines() if l.strip() and not l.startswith("#")]
    for i, ln in enumerate(lines):
        if set(ln.replace("\t", "").strip()).issubset({"-", " "}):
            hdr = [c.strip() for c in lines[0].split("\t")]
            out = []
            for dln in lines[i + 1:]:
                parts = dln.split("\t")
                if len(parts) == len(hdr):
                    out.append({k: v.strip() for k, v in zip(hdr, parts)})
            return out
    return []


def batch_query_by_id(source: str, id_col: str, ids: list[str], out_cols: str, out_csv: Path) -> list[dict[str, str]]:
    if out_csv.exists() and out_csv.stat().st_size > 100:
        return list(csv.DictReader(out_csv.open("r", encoding="utf-8")))
    rows: list[dict[str, str]] = []
    uniq = sorted(set(x for x in ids if x.isdigit()))
    for i in range(0, len(uniq), 60):
        chunk = uniq[i:i + 60]
        raw = _http_post_vizier({
            "-source": source,
            "-out.max": "unlimited",
            id_col: ",".join(chunk),
            "-out": out_cols,
        })
        got = parse_vizier_tsv(raw.decode("utf-8", errors="replace"))
        rows.extend(got)
    hdrs = out_cols.split(",")
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=hdrs)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in hdrs})
    print(f"  {source}: {len(rows)} matched rows", flush=True)
    return rows


def main() -> int:
    for d in ("gaia_nss", "hgca", "kervella", "benchmarks"):
        (INP / d).mkdir(parents=True, exist_ok=True)

    gaia_map = {r["star"]: r for r in csv.DictReader(GAIA_CSV.open("r", encoding="utf-8"))}
    targets: list[dict[str, Any]] = []
    for r in csv.DictReader(MASTER_CSV.open("r", encoding="utf-8")):
        if float(r["dist_pc"]) > 50000.0:
            continue
        g = gaia_map.get(r["star"], {})
        targets.append({
            "star": r["star"],
            "common_name": r["common_name"],
            "is_bh_benchmark": "False",
            "within_10pc": r["within_10pc"],
            "n_exoplanets": r["n_exoplanets"],
            "dist_pc": r["dist_pc"],
            "source_id": g.get("source_id", "").strip(),
            "ra": g.get("ra", r["ra_deg"]),
            "dec": g.get("dec", r["dec_deg"]),
            "parallax": g.get("parallax", ""),
            "phot_g_mean_mag": g.get("phot_g_mean_mag", ""),
            "bp_rp": g.get("bp_rp", ""),
            "ruwe": g.get("ruwe", ""),
            "ipd_frac_multi_peak": g.get("ipd_frac_multi_peak", ""),
            "non_single_star": g.get("non_single_star", ""),
        })

    # Live Gaia DR3 lookup for Gaia BH1, BH2, BH3 positive benchmarks!
    bh_ids = [b["source_id"] for b in BH_BENCHMARKS]
    bh_csv = INP / "benchmarks/gaia_bh_benchmarks.csv"
    bh_rows = batch_query_by_id("I/355/gaiadr3", "Source", bh_ids, "Source,RA_ICRS,DE_ICRS,Plx,Gmag,BP-RP,RUWE,IPDfmp,NSS", bh_csv)
    bh_by_id = {r["Source"]: r for r in bh_rows}
    for b in BH_BENCHMARKS:
        g = bh_by_id.get(b["source_id"], {})
        targets.append({
            "star": b["star"],
            "common_name": b["common_name"],
            "is_bh_benchmark": "True",
            "within_10pc": b["within_10pc"],
            "n_exoplanets": b["n_exoplanets"],
            "dist_pc": b["dist_pc"],
            "source_id": b["source_id"],
            "ra": g.get("RA_ICRS", ""),
            "dec": g.get("DE_ICRS", ""),
            "parallax": g.get("Plx", ""),
            "phot_g_mean_mag": g.get("Gmag", ""),
            "bp_rp": g.get("BP-RP", ""),
            "ruwe": g.get("RUWE", ""),
            "ipd_frac_multi_peak": g.get("IPDfmp", ""),
            "non_single_star": g.get("NSS", ""),
        })

    t_out = INP / "milky_way_astrometry_targets.csv"
    with t_out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(targets[0].keys()))
        w.writeheader()
        w.writerows(targets)

    all_sids = [t["source_id"] for t in targets if t["source_id"].isdigit()]
    print(f"Querying VizieR DR3 NSS / HGCA / Kervella across {len(all_sids)} Gaia DR3 source_ids...", flush=True)
    r_tb = batch_query_by_id("I/357/tbooc", "Source", all_sids, "Source,NSSmodel,Plx,ATI,BTI,FTI,GTI,Per,ecc,amaj,incl,Signi", INP / "gaia_nss/nss_tbooc.csv")
    r_sb = batch_query_by_id("I/357/tbosb1", "Source", all_sids, "Source,NSSmodel,Per,ecc,Vcm,K1,Signi", INP / "gaia_nss/nss_tbosb1.csv")
    r_a7 = batch_query_by_id("I/357/acc7", "Source", all_sids, "Source,NSSmodel,Plx,dpmRA,dpmDE", INP / "gaia_nss/nss_acc7.csv")
    r_a9 = batch_query_by_id("I/357/acc9", "Source", all_sids, "Source,NSSmodel,Plx,dpmRA,dpmDE,ddpmRA,ddpmDE", INP / "gaia_nss/nss_acc9.csv")
    r_hg = batch_query_by_id("J/ApJS/254/42", "Gaia", all_sids, "HIP,Gaia,chi2,dpmRA,dpmDE", INP / "hgca/brandt_hgca.csv")
    r_kv = batch_query_by_id("J/A+A/657/A7/tablea1", "GaiaEDR3", all_sids, "HIP,GaiaEDR3,Name,RUWE,snrPMaHG1,snrPMaH2EG3a,snrPMaH2EG3b,M1,M23au,M210au,M230au", INP / "kervella/kervella_pma.csv")

    man = {
        "pure_mw_targets": sum(1 for t in targets if t["is_bh_benchmark"] == "False"),
        "bh_benchmarks": len(BH_BENCHMARKS),
        "tbooc_matches": len(r_tb),
        "tbosb1_matches": len(r_sb),
        "acc7_matches": len(r_a7),
        "acc9_matches": len(r_a9),
        "hgca_matches": len(r_hg),
        "kervella_matches": len(r_kv),
    }
    (INP / "STAGE1_MANIFEST.json").write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")
    print("STAGE1_N9_DONE:", json.dumps(man))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
