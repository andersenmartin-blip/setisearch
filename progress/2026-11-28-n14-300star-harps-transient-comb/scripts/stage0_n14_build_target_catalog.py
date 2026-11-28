#!/usr/bin/env python3
"""Stage 0 (Metadata-Only, Zero FITS Download) for Spor N14: Build 268+20 Confirmed Exoplanet Host Catalog."""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
INP = ROOT / "inputs_n14_20261128"
TABLE1 = ROOT / "setisearch/zenodo_package/tables/table1_master_catalog_1083stars.csv"

NEA_TAP = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
ESO_TAP = "https://archive.eso.org/tap_obs/sync"

PRIOR_STARS = {
    "PROXIMACEN", "BARNARDSSTAR", "ROSS128", "GJ1061", "YZCET", "GJ273", "GJ667C", "L9859",
    "EPSERI", "HD217987", "TAUCET", "HD209100", "GJ191", "WOLF1061", "GJ9066", "GJ674",
    "GJ876", "GJ832", "GJ682", "GJ3323", "HD42581", "GJ752A", "HD20794", "GJ581",
    "LTT1445A", "GJ393", "GJ514", "HD115617", "GJ849", "HD192310", "GJ433", "GJ367",
}
PRIOR_ALIASES = (
    "PROXIMA", "BARNARD", "ROSS128", "GJ1061", "YZCET", "GJ273", "GJ667C", "L9859", "TOI175",
    "EPSERI", "HD217987", "GJ887", "TAUCET", "EPSIND", "HD209100", "KAPTEYN", "GJ191",
    "WOLF1061", "GJ628", "GJ9066", "TZARI", "GJ674", "GJ876", "GJ832", "GJ682", "GJ3323",
    "GJ229", "HD42581", "GJ752", "HD20794", "82GERI", "GJ581", "LTT1445", "GJ393", "GJ514",
    "61VIR", "HD115617", "GJ849", "HD192310", "GJ433", "GJ367", "L168-9",
)


def http_json(url: str, timeout: int = 45) -> object:
    last_err: Exception | None = None
    for att in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETIsearch-N14/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:
            last_err = exc
            time.sleep(1.5 * (att + 1))
    raise RuntimeError(f"GET failed ({url[:90]}): {last_err}")


def norm_id(s: str) -> str:
    return "".join(c for c in s.upper() if c.isalnum())


def load_prior_coords() -> list[tuple[str, float, float]]:
    out = []
    with TABLE1.open("r", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["star"] in PRIOR_STARS:
                out.append((r["star"], float(r["ra_deg"]), float(r["dec_deg"])))
    return out


def is_excluded(hostname: str, ra: float, dec: float, prior_coords: list[tuple[str, float, float]]) -> bool:
    hn = norm_id(hostname)
    if hn in PRIOR_STARS or any(al in hn for al in PRIOR_ALIASES):
        return True
    c = max(0.1, abs(math.cos(math.radians(dec))))
    for _st, pra, pdec in prior_coords:
        if abs(dec - pdec) < 0.06 and abs(ra - pra) * c < 0.06:
            return True
    return False


def query_eso_tns(tns: list[str]) -> list[dict[str, str]]:
    in_clause = ", ".join("'" + t.replace("'", "''") + "'" for t in tns)
    sql = (
        "SELECT TOP 20000 dp_id, target_name, t_min, t_exptime, s_ra, s_dec, snr "
        "FROM ivoa.ObsCore "
        f"WHERE instrument_name = 'HARPS' AND dataproduct_type = 'spectrum' AND dp_id LIKE 'ADP.%' AND t_exptime >= 10 AND target_name IN ({in_clause})"
    )
    url = f"{ESO_TAP}?" + urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": sql})
    for att in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETIsearch-N14/1.0"})
            with urllib.request.urlopen(req, timeout=45) as r:
                rows = list(csv.DictReader(r.read().decode("utf-8", errors="replace").splitlines()))
            if len(rows) >= 19500 and len(tns) > 1:
                out: list[dict[str, str]] = []
                for single in tns:
                    out.extend(query_eso_tns([single]))
                return out
            return rows
        except Exception:
            time.sleep(1.0 * (att + 1))
    return []


def resolve_all_strata(pool_cands: list[dict], n_strata: int = 8) -> list[dict]:
    all_tns = sorted({tn for c in pool_cands for tn in c["eso_target_names"]})
    batches = [all_tns[i : i + 12] for i in range(0, len(all_tns), 12)]
    all_rows: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for res_rows in ex.map(query_eso_tns, batches):
            all_rows.extend(res_rows)

    by_tn: dict[str, list[dict[str, str]]] = {}
    for r in all_rows:
        by_tn.setdefault(r.get("target_name") or "", []).append(r)

    resolved: list[dict] = []
    for cand in pool_cands:
        ra, dec = float(cand["ra_deg"]), float(cand["dec_deg"])
        cos_d = max(0.1, abs(math.cos(math.radians(dec))))
        seen: set[str] = set()
        clean: list[dict] = []
        for tn in cand["eso_target_names"]:
            for r in by_tn.get(tn, []):
                dp = (r.get("dp_id") or "").strip()
                if not dp.startswith("ADP.") or dp in seen:
                    continue
                try:
                    era, edec = float(r["s_ra"]), float(r["s_dec"])
                    if abs(edec - dec) > 0.04 or abs(era - ra) * cos_d > 0.04:
                        continue
                    mjd = float(r["t_min"])
                    expt = float(r.get("t_exptime") or 0.0)
                    snr = float(r.get("snr") or 0.0)
                except (ValueError, TypeError):
                    continue
                if expt < 10.0:
                    continue
                seen.add(dp)
                clean.append({"dp_id": dp, "target_name": r.get("target_name") or "", "t_min": mjd, "exptime": expt, "snr": snr})

        pref = [c for c in clean if float(c["snr"]) >= 8.0]
        if len(pref) < n_strata + 4:
            pref = clean
        pref.sort(key=lambda c: float(c["t_min"]))
        if len(pref) < n_strata:
            continue

        tot = len(pref)
        strata: list[list[dict]] = []
        chosen_ids: set[str] = set()
        for k in range(n_strata):
            i0 = (k * tot) // n_strata
            i1 = ((k + 1) * tot) // n_strata
            bucket = sorted(pref[i0:i1], key=lambda c: (float(c["snr"]), float(c["exptime"])), reverse=True)
            strata.append(bucket[:4])
            if bucket:
                chosen_ids.add(str(bucket[0]["dp_id"]))
        fallbacks = sorted([c for c in clean if str(c["dp_id"]) not in chosen_ids], key=lambda c: float(c["snr"]), reverse=True)[:12]
        resolved.append({**cand, "tap_total_valid": len(clean), "strata": strata, "star_fallbacks": fallbacks})
    return resolved


def main() -> int:
    t0 = time.time()
    INP.mkdir(parents=True, exist_ok=True)
    prior_coords = load_prior_coords()
    print(f"[N14 Stage 0] Loaded {len(prior_coords)} prior N11B+N12 exclusion coordinates.", flush=True)

    q_nea = (
        "SELECT hostname, MAX(ra) AS ra, MAX(dec) AS dec, MIN(sy_dist) AS dist_pc, "
        "COUNT(DISTINCT pl_name) AS n_pl, COALESCE(MIN(sy_vmag), MIN(sy_gaiamag), 12.0) AS vmag, "
        "MAX(st_spectype) AS sp "
        "FROM pscomppars WHERE dec <= 25 AND sy_dist IS NOT NULL "
        "GROUP BY hostname ORDER BY dist_pc ASC"
    )
    hosts = http_json(f"{NEA_TAP}?query={urllib.parse.quote(q_nea)}&format=json")
    print(f"[N14 Stage 0] NASA Exoplanet Archive Dec<=+25 hosts: {len(hosts)}", flush=True)

    q_eso = (
        "SELECT target_name, COUNT(*) AS n_exp, AVG(s_ra) AS ra, AVG(s_dec) AS dec "
        "FROM ivoa.ObsCore "
        "WHERE instrument_name = 'HARPS' AND dataproduct_type = 'spectrum' "
        "AND dp_id LIKE 'ADP.%' AND access_url IS NOT NULL "
        "GROUP BY target_name HAVING COUNT(*) >= 8"
    )
    eso_rows = http_json(f"{ESO_TAP}?" + urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "json", "QUERY": q_eso}))["data"]
    print(f"[N14 Stage 0] ESO HARPS >=8-epoch clusters: {len(eso_rows)}", flush=True)

    grid: dict[tuple[int, int], list[tuple[str, int, float, float]]] = {}
    for tn, nexp, ra, dec in eso_rows:
        if ra is None or dec is None:
            continue
        key = (int(round(ra * 10)), int(round(dec * 10)))
        grid.setdefault(key, []).append((tn, int(nexp), float(ra), float(dec)))

    cands: list[dict] = []
    for h in hosts:
        ra, dec = float(h["ra"]), float(h["dec"])
        if is_excluded(h["hostname"], ra, dec, prior_coords):
            continue
        c = max(0.1, abs(math.cos(math.radians(dec))))
        bx, by = int(round(ra * 10)), int(round(dec * 10))
        tot = 0
        tns: list[str] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for tn, nexp, era, edec in grid.get((bx + dx, by + dy), []):
                    if abs(edec - dec) < 0.035 and abs(era - ra) * c < 0.035:
                        tot += nexp
                        tns.append(tn)
        if tot >= 8:
            st_key = norm_id(h["hostname"])
            sp = (h.get("sp") or "").strip() or "G/K"
            cands.append({
                "star": st_key,
                "common_name": h["hostname"],
                "ra_deg": round(ra, 6),
                "dec_deg": round(dec, 6),
                "dist_pc": round(float(h["dist_pc"]), 4),
                "n_exoplanets": int(h["n_pl"]),
                "vmag": round(float(h["vmag"] or 12.0), 3),
                "sp_type": sp,
                "eso_est_epochs": tot,
                "eso_target_names": tns,
            })

    cands.sort(key=lambda x: x["dist_pc"])
    # Deduplicate star keys in case two hostnames sanitize identically
    seen_keys: set[str] = set()
    uniq_cands: list[dict] = []
    for x in cands:
        if x["star"] not in seen_keys:
            seen_keys.add(x["star"])
            uniq_cands.append(x)

    pool_cands = uniq_cands[:300]
    print(f"[N14 Stage 0] Querying ESO 8-strata metadata in 60 batches for top {len(pool_cands)} nearest hosts ...", flush=True)
    resolved = resolve_all_strata(pool_cands, 8)
    resolved.sort(key=lambda x: x["dist_pc"])

    if len(resolved) < 280:
        raise RuntimeError(f"Only resolved {len(resolved)} hosts (< 280)")

    primary = resolved[:268]
    backup = resolved[268:292]
    cat = {
        "campaign": "SPOR_N14_300STAR_HARPS_TRANSIENT_LASER_AND_COMB",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "elapsed_s": round(time.time() - t0, 2),
        "primary_count": len(primary),
        "backup_count": len(backup),
        "epochs_per_star": 8,
        "prior_32_excluded": sorted(PRIOR_STARS),
        "primary_targets": primary,
        "backup_targets": backup,
        "external_contacts": 0,
    }
    out_p = INP / "n14_target_catalog.json"
    out_p.write_text(json.dumps(cat, indent=2), encoding="utf-8")
    print(
        f"[N14 Stage 0] Locked {len(primary)} primary ({primary[0]['common_name']} {primary[0]['dist_pc']} pc .. {primary[-1]['common_name']} {primary[-1]['dist_pc']} pc) "
        f"+ {len(backup)} backup hosts ({sum(x['n_exoplanets'] for x in primary)} exoplanets) in {cat['elapsed_s']}s!",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
