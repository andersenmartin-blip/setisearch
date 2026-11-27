#!/usr/bin/env python3
"""
Spor N5 Stage 1 Live All-Sky Tier-1 Acquisition across 1,096 Targets (1,083 Master + 13 Benchmarks):
- ARI Gaia DR3 TAP_UPLOAD (gaia_source + vari_summary + nss_two_body_orbit)
- Proper-motion propagation to epoch 2010.5 (AllWISE), 2015.4 (CatWISE2020), 2021.0 (ZTF DR24)
- IRSA Gator fixed-width IPAC table bulk Upload (chunked at 275 targets)
Forces IPv4 (socket.AF_INET).
"""
from __future__ import annotations

import collections
import csv
import datetime
import hashlib
import json
import math
import pathlib
import socket
import time
import urllib.parse
import urllib.request
from typing import Any

# Critical IPv4 force
_orig_gai = socket.getaddrinfo
socket.getaddrinfo = lambda h, p, fam=0, t=0, pr=0, fl=0: _orig_gai(h, p, socket.AF_INET, t, pr, fl)

ROOT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
INP = ROOT / "inputs_n5_20261127"
TABLE1 = ROOT / "setisearch" / "zenodo_package" / "tables" / "table1_master_catalog_1083stars.csv"
BENCH13 = INP / "n5_benchmarks_13.csv"


def _f(v: Any) -> float | None:
    if v is None or v == "" or str(v).strip().lower() in ("nan", "null", "none", "inf", "-inf", "--"):
        return None
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def angsep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    cos_a = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_a)))) * 3600.0


def propagate_coords(ra: float, dec: float, pmra_mas_yr: float | None, pmdec_mas_yr: float | None, dt_yr: float) -> tuple[float, float]:
    if pmra_mas_yr is None or pmdec_mas_yr is None or abs(pmra_mas_yr) > 11000 or abs(pmdec_mas_yr) > 11000:
        return ra, dec
    cosd = max(0.1, math.cos(math.radians(dec)))
    new_dec = max(-89.999, min(89.999, dec + (pmdec_mas_yr / 3.6e6) * dt_yr))
    new_ra = (ra + (pmra_mas_yr / (3.6e6 * cosd)) * dt_yr) % 360.0
    return new_ra, new_dec


def _http_post(url: str, data: bytes, headers: dict[str, str], timeout: int = 60, retries: int = 3) -> bytes:
    last_err: Exception | None = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": "SETI-N5/1.0", **headers})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"HTTP failed {url}: {last_err}")


def _fill_high_pm_gaia(targets: list[dict[str, Any]], out_map: dict[str, dict[str, Any]]) -> None:
    need = []
    for t in targets:
        dpc = _f(t.get("dist_pc")) or 100.0
        if dpc >= 25.0:
            continue
        exp_plx = 1000.0 / max(1.0, dpc)
        cur = out_map.get(t["star"], {})
        cur_plx = _f(cur.get("parallax")) or 0.0
        if (t["star"] not in out_map) or abs(cur_plx - exp_plx) > 0.35 * exp_plx:
            need.append(t)
    if not need:
        return
    print(f"  Resolving {len(need)} high-PM <25pc stars via 12-star Q3C TAP_UPLOAD (plx>25)...", flush=True)
    adql = (
        "SELECT u.star, g.source_id, g.ra, g.dec, g.pmra, g.pmdec, g.parallax, g.phot_g_mean_mag, g.bp_rp, g.ruwe, "
        "ipd_frac_multi_peak, phot_variable_flag, non_single_star "
        "FROM TAP_UPLOAD.stars AS u JOIN gaiadr3.gaia_source AS g "
        "ON 1=CONTAINS(POINT('ICRS',g.ra,g.dec), CIRCLE('ICRS',u.ra,u.dec,0.065)) WHERE g.parallax > 25.0"
    )
    by_s: dict[str, list[dict[str, str]]] = collections.defaultdict(list)
    for i in range(0, len(need), 12):
        chunk = need[i:i + 12]
        trs = "".join(f"<TR><TD>{t['star']}</TD><TD>{float(t['ra_deg']):.6f}</TD><TD>{float(t['dec_deg']):.6f}</TD></TR>" for t in chunk)
        vot = ('<?xml version="1.0"?><VOTABLE version="1.3" xmlns="http://www.ivoa.net/xml/VOTable/v1.3"><RESOURCE><TABLE name="stars"><FIELD name="star" datatype="char" arraysize="*"/><FIELD name="ra" datatype="double"/><FIELD name="dec" datatype="double"/><DATA><TABLEDATA>' + trs + '</TABLEDATA></TABLE></RESOURCE></VOTABLE>').encode("utf-8")
        b = "----N5HPM"
        body = (f"--{b}\r\nContent-Disposition: form-data; name=\"REQUEST\"\r\n\r\ndoQuery\r\n--{b}\r\nContent-Disposition: form-data; name=\"LANG\"\r\n\r\nADQL\r\n--{b}\r\nContent-Disposition: form-data; name=\"FORMAT\"\r\n\r\ncsv\r\n--{b}\r\nContent-Disposition: form-data; name=\"UPLOAD\"\r\n\r\nstars,param:ufile\r\n--{b}\r\nContent-Disposition: form-data; name=\"QUERY\"\r\n\r\n{adql}\r\n--{b}\r\nContent-Disposition: form-data; name=\"ufile\"; filename=\"stars.xml\"\r\nContent-Type: application/x-votable+xml\r\n\r\n").encode("utf-8") + vot + f"\r\n--{b}--\r\n".encode("utf-8")
        raw = _http_post("https://gaia.ari.uni-heidelberg.de/tap/sync", body, {"Content-Type": f"multipart/form-data; boundary={b}"}, timeout=30)
        for c in csv.DictReader(raw.decode("utf-8", errors="replace").splitlines()):
            by_s[c["star"]].append(c)
    for s in need:
        st = s["star"]
        t_ra, t_dec = float(s["ra_deg"]), float(s["dec_deg"])
        exp_plx = 1000.0 / max(1.0, float(s["dist_pc"]))
        best_sc, best_c, best_sep = 1e9, None, 999.0
        for c in by_s.get(st, []):
            gra, gdec, plx = _f(c.get("ra")), _f(c.get("dec")), _f(c.get("parallax"))
            if gra is None or gdec is None or plx is None or abs(plx - exp_plx) > 0.35 * exp_plx:
                continue
            pmra, pmdec = _f(c.get("pmra")), _f(c.get("pmdec"))
            ra2000, dec2000 = propagate_coords(gra, gdec, pmra, pmdec, -16.0)
            sep = min(angsep_arcsec(t_ra, t_dec, ra2000, dec2000), angsep_arcsec(t_ra, t_dec, gra, gdec))
            sc = abs(plx - exp_plx) / exp_plx * 20.0 + sep
            if sep <= 15.0 and sc < best_sc:
                best_sc, best_c, best_sep = sc, c, sep
        if best_c is not None:
            best_c.pop("star", None)
            out_map[st] = {
                "star": st, **best_c, "sep_arcsec": f"{best_sep:.4f}",
                "vari_range_g": "", "vari_std_g": "", "vari_skew_g": "", "vari_stetson_g": "", "nss_solution_type": "",
            }


def acquire_gaia(targets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out_p = INP / "gaia" / "gaia_dr3_1096.csv"
    if out_p.exists() and out_p.stat().st_size > 1024:
        out_map = {r["star"]: r for r in csv.DictReader(out_p.open(encoding="utf-8"))}
        _fill_high_pm_gaia(targets, out_map)
        rows = [out_map[t["star"]] for t in targets if t["star"] in out_map]
        with out_p.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"ARI Gaia DR3 high-PM patched: {len(rows)}/{len(targets)}", flush=True)
        return out_map

    # Build VOTable in 2 chunks of 550 targets for ARI TAP_UPLOAD
    all_raw: dict[str, list[dict[str, str]]] = collections.defaultdict(list)
    by_star = {t["star"]: t for t in targets}

    adql = (
        "SELECT u.star, g.source_id, g.ra, g.dec, g.pmra, g.pmdec, g.parallax, "
        "g.phot_g_mean_mag, g.bp_rp, g.ruwe, g.ipd_frac_multi_peak, "
        "g.phot_variable_flag, g.non_single_star "
        "FROM TAP_UPLOAD.stars AS u "
        "JOIN gaiadr3.gaia_source AS g "
        "  ON 1=CONTAINS(POINT('ICRS',g.ra,g.dec), CIRCLE('ICRS',u.ra,u.dec,0.0055))"
    )

    for i in range(0, len(targets), 100):
        chunk = targets[i:i + 100]
        trs = "".join(
            f"<TR><TD>{t['star'].replace('&','&amp;')}</TD><TD>{float(t['ra_deg']):.6f}</TD><TD>{float(t['dec_deg']):.6f}</TD></TR>"
            for t in chunk
        )
        vot = (
            '<?xml version="1.0"?><VOTABLE version="1.3" xmlns="http://www.ivoa.net/xml/VOTable/v1.3"><RESOURCE><TABLE name="stars">'
            '<FIELD name="star" datatype="char" arraysize="*"/><FIELD name="ra" datatype="double"/><FIELD name="dec" datatype="double"/>'
            f"<DATA><TABLEDATA>{trs}</TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>"
        ).encode("utf-8")
        b = "----N5ARIBOUNDARY"
        body = (
            f"--{b}\r\nContent-Disposition: form-data; name=\"REQUEST\"\r\n\r\ndoQuery\r\n"
            f"--{b}\r\nContent-Disposition: form-data; name=\"LANG\"\r\n\r\nADQL\r\n"
            f"--{b}\r\nContent-Disposition: form-data; name=\"FORMAT\"\r\n\r\ncsv\r\n"
            f"--{b}\r\nContent-Disposition: form-data; name=\"UPLOAD\"\r\n\r\nstars,param:ufile\r\n"
            f"--{b}\r\nContent-Disposition: form-data; name=\"QUERY\"\r\n\r\n{adql}\r\n"
            f"--{b}\r\nContent-Disposition: form-data; name=\"ufile\"; filename=\"stars.xml\"\r\nContent-Type: application/x-votable+xml\r\n\r\n"
        ).encode("utf-8") + vot + f"\r\n--{b}--\r\n".encode("utf-8")
        raw = _http_post("https://gaia.ari.uni-heidelberg.de/tap/sync", body, {"Content-Type": f"multipart/form-data; boundary={b}"}, timeout=45)
        for r in csv.DictReader(raw.decode("utf-8", errors="replace").splitlines()):
            all_raw[r["star"]].append(r)
        print(f"  ARI Gaia DR3: {min(i+100, len(targets))}/{len(targets)} stars", flush=True)

    best_rows: list[dict[str, Any]] = []
    out_map: dict[str, dict[str, Any]] = {}
    for t in targets:
        st = t["star"]
        cands = all_raw.get(st, [])
        if not cands:
            continue
        t_ra, t_dec = float(t["ra_deg"]), float(t["dec_deg"])
        dist_pc = _f(t.get("dist_pc")) or 100.0
        scored = []
        for c in cands:
            gra, gdec = _f(c.get("ra")), _f(c.get("dec"))
            if gra is None or gdec is None:
                continue
            pmra, pmdec = _f(c.get("pmra")), _f(c.get("pmdec"))
            ra2000, dec2000 = propagate_coords(gra, gdec, pmra, pmdec, -16.0)
            sep_j2000 = angsep_arcsec(t_ra, t_dec, ra2000, dec2000)
            sep_raw = angsep_arcsec(t_ra, t_dec, gra, gdec)
            sep_best = min(sep_j2000, sep_raw)
            gmag = _f(c.get("phot_g_mean_mag")) or 21.0
            score = sep_best + (2.0 * max(0.0, gmag - 14.0) if dist_pc < 25.0 else 0.0)
            scored.append((score, sep_best, c))
        if not scored:
            continue
        scored.sort(key=lambda x: x[0])
        _, sep_best, best = scored[0]
        if sep_best <= 20.0:
            row_out = {**best, "sep_arcsec": f"{sep_best:.4f}", "vari_range_g": "", "vari_std_g": "", "vari_skew_g": "", "vari_stetson_g": "", "nss_solution_type": ""}
            best_rows.append(row_out)
            out_map[st] = row_out

    # Fast primary-key lookups on vari_summary and nss_two_body_orbit
    sids = [r["source_id"] for r in best_rows if r.get("source_id")]
    vari_map: dict[str, dict[str, str]] = {}
    nss_map: dict[str, str] = {}
    for i in range(0, len(sids), 300):
        sub_ids = ",".join(sids[i:i + 300])
        q_v = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                                      "QUERY": f"SELECT source_id, range_mag_g_fov, std_dev_mag_g_fov, skewness_mag_g_fov, stetson_mag_g_fov FROM gaiadr3.vari_summary WHERE source_id IN ({sub_ids})"}).encode()
        raw_v = _http_post("https://gaia.ari.uni-heidelberg.de/tap/sync", q_v, {}, timeout=30)
        for r in csv.DictReader(raw_v.decode("utf-8", errors="replace").splitlines()):
            vari_map[r["source_id"]] = r
        q_n = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                                      "QUERY": f"SELECT source_id, nss_solution_type FROM gaiadr3.nss_two_body_orbit WHERE source_id IN ({sub_ids})"}).encode()
        raw_n = _http_post("https://gaia.ari.uni-heidelberg.de/tap/sync", q_n, {}, timeout=30)
        for r in csv.DictReader(raw_n.decode("utf-8", errors="replace").splitlines()):
            nss_map[r["source_id"]] = r.get("nss_solution_type", "")

    for r in best_rows:
        sid = r.get("source_id", "")
        if sid in vari_map:
            vr = vari_map[sid]
            r["vari_range_g"] = vr.get("range_mag_g_fov", "")
            r["vari_std_g"] = vr.get("std_dev_mag_g_fov", "")
            r["vari_skew_g"] = vr.get("skewness_mag_g_fov", "")
            r["vari_stetson_g"] = vr.get("stetson_mag_g_fov", "")
        if sid in nss_map:
            r["nss_solution_type"] = nss_map[sid]

    cols = list(best_rows[0].keys())
    with out_p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(best_rows)
    print(f"ARI Gaia DR3 matched: {len(best_rows)}/{len(targets)}", flush=True)
    return out_map


def _parse_ipac_table(raw_text: str) -> list[dict[str, str]]:
    lines = raw_text.splitlines()
    hdr_idx = None
    for idx, ln in enumerate(lines):
        if ln.startswith("|") and not lines[idx + 1:idx + 2] == []:
            hdr_idx = idx
            break
    if hdr_idx is None:
        return []
    # Fixed-width pipe positions determine columns accurately
    hdr_ln = lines[hdr_idx]
    pipes = [pos for pos, ch in enumerate(hdr_ln) if ch == "|"]
    if len(pipes) < 2:
        return []
    colnames = [hdr_ln[pipes[k] + 1:pipes[k + 1]].strip() for k in range(len(pipes) - 1)]
    # Data starts after header lines starting with '|'
    data_start = hdr_idx + 1
    while data_start < len(lines) and (lines[data_start].startswith("|") or not lines[data_start].strip()):
        data_start += 1
    out: list[dict[str, str]] = []
    for ln in lines[data_start:]:
        if not ln.strip() or ln.startswith("\\") or ln.startswith("|"):
            continue
        vals = [ln[pipes[k]:pipes[k + 1]].strip() for k in range(len(pipes) - 1)] if len(ln) >= pipes[-1] else ln.split()
        if len(vals) == len(colnames):
            rec = dict(zip(colnames, vals))
            out.append({k: ("" if v.lower() == "null" else v) for k, v in rec.items()})
    return out


def _gator_upload_query(catalog: str, coords: list[tuple[str, float, float]], selcols: str, rad_arcsec: float, chunk_size: int = 275) -> dict[str, list[dict[str, str]]]:
    by_star: dict[str, list[dict[str, str]]] = collections.defaultdict(list)
    for i in range(0, len(coords), chunk_size):
        chunk = coords[i:i + chunk_size]
        tbl_lines = ["|        ra|       dec|", "|    double|    double|"]
        for _, ra, dec in chunk:
            tbl_lines.append(f" {ra:10.6f} {dec:10.6f} ")
        ipac_tbl = "\n".join(tbl_lines) + "\n"
        b = "----N5GATORUPLOAD"
        parts = [
            ("catalog", catalog), ("spatial", "Upload"), ("uradius", str(rad_arcsec)),
            ("uradunits", "arcsec"), ("outfmt", "1"), ("selcols", selcols), ("one_to_one", "0"),
        ]
        body = b""
        for k, v in parts:
            body += f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode("utf-8")
        body += f"--{b}\r\nContent-Disposition: form-data; name=\"filename\"; filename=\"stars.tbl\"\r\nContent-Type: text/plain\r\n\r\n{ipac_tbl}\r\n--{b}--\r\n".encode("utf-8")
        raw = _http_post("https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query", body, {"Content-Type": f"multipart/form-data; boundary={b}"}, timeout=90)
        txt = raw.decode("utf-8", errors="replace")
        if "[struct stat=\"ERROR\"" in txt[:500]:
            raise RuntimeError(f"Gator error ({catalog}): {txt[:300]}")
        parsed = _parse_ipac_table(txt)
        for r in parsed:
            cidx = int(r["cntr_01"]) - 1
            if 0 <= cidx < len(chunk):
                st = chunk[cidx][0]
                by_star[st].append(r)
        print(f"  {catalog}: chunk {i+1}-{min(i+chunk_size, len(coords))}/{len(coords)} -> {len(parsed)} rows", flush=True)
        time.sleep(0.25)
    return by_star


def acquire_gator_catalogs(targets: list[dict[str, Any]], gaia_map: dict[str, dict[str, Any]]) -> None:
    def epoch_coords(dt_yr: float, dec_min: float = -90.0) -> list[tuple[str, float, float]]:
        pts = []
        for t in targets:
            ra, dec = float(t["ra_deg"]), float(t["dec_deg"])
            if dec < dec_min:
                continue
            g = gaia_map.get(t["star"], {})
            # If matched to Gaia DR3, use Gaia RA/Dec propagated from 2016.0 -> target epoch!
            gra, gdec = _f(g.get("ra")), _f(g.get("dec"))
            pmra, pmdec = _f(g.get("pmra")), _f(g.get("pmdec"))
            if gra is not None and gdec is not None and pmra is not None and pmdec is not None:
                era, edec = propagate_coords(gra, gdec, pmra, pmdec, (2000.0 + dt_yr) - 2016.0)
            else:
                era, edec = ra, dec
            pts.append((t["star"], era, edec))
        return pts

    # 1. AllWISE (epoch 2010.5)
    p_aw = INP / "allwise" / "allwise_1096.csv"
    if not p_aw.exists():
        pts_aw = epoch_coords(10.5)
        raw_aw = _gator_upload_query("allwise_p3as_psd", pts_aw, "designation,ra,dec,w1mpro,w1sigmpro,w2mpro,w2sigmpro,w3mpro,w4mpro,var_flg,cc_flags", 12.0)
        rows = []
        for st, ra_e, dec_e in pts_aw:
            cands = raw_aw.get(st, [])
            if not cands:
                continue
            cands.sort(key=lambda r: float(r.get("dist_x") or 999.0))
            best = cands[0]
            rows.append({"star": st, "sep_arcsec": best.get("dist_x", ""), **best})
        with p_aw.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"AllWISE saved: {len(rows)}/{len(targets)}", flush=True)

    # 2. CatWISE2020 (epoch 2015.4)
    p_cw = INP / "catwise" / "catwise2020_1096.csv"
    if not p_cw.exists():
        pts_cw = epoch_coords(15.4)
        raw_cw = _gator_upload_query("catwise_2020", pts_cw, "source_id,ra,dec,w1mpro,w2mpro,w1sigmpro,w2sigmpro,w1rchi2,w2rchi2,pmra,pmdec,ab_flags", 12.0)
        rows = []
        for st, ra_e, dec_e in pts_cw:
            cands = raw_cw.get(st, [])
            if not cands:
                continue
            cands.sort(key=lambda r: float(r.get("dist_x") or 999.0))
            best = cands[0]
            rows.append({"star": st, "sep_arcsec": best.get("dist_x", ""), **best})
        with p_cw.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"CatWISE2020 saved: {len(rows)}/{len(targets)}", flush=True)

    # 3. ZTF DR24 (epoch 2021.0, Dec >= -31 deg)
    p_ztf = INP / "ztf" / "ztf_dr24_1096.csv"
    if not p_ztf.exists():
        pts_ztf = epoch_coords(21.0, dec_min=-31.0)
        raw_ztf = _gator_upload_query("ztf_objects_dr24", pts_ztf, "oid,filtercode,ra,dec,ngoodobs,medianmag,medmagerr,magrms,lineartrend,minmag,maxmag,skewness,stetsonj,vonneumannratio,chisq", 6.0)
        rows = []
        for st, ra_e, dec_e in pts_ztf:
            cands = raw_ztf.get(st, [])
            if not cands:
                continue
            # Prefer objects with >= 20 obs and closest distance; pick highest ngoodobs among close matches
            cands.sort(key=lambda r: (-(int(float(r.get("ngoodobs") or 0)) if float(r.get("dist_x") or 99) <= 2.5 else 0), float(r.get("dist_x") or 999.0)))
            best = cands[0]
            rows.append({"star": st, "sep_arcsec": best.get("dist_x", ""), **best})
        with p_ztf.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"ZTF DR24 saved: {len(rows)}/{len(pts_ztf)} northern stars", flush=True)


def main() -> int:
    targets = list(csv.DictReader(TABLE1.open(encoding="utf-8")))
    if BENCH13.exists():
        targets.extend(list(csv.DictReader(BENCH13.open(encoding="utf-8"))))
    assert len(targets) == 1096, f"Expected 1096 targets, got {len(targets)}"

    gaia_map = acquire_gaia(targets)
    acquire_gator_catalogs(targets, gaia_map)

    manifest = {"acquired_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "targets": len(targets), "files": {}}
    for p in sorted(INP.rglob("*")):
        if p.is_file() and p.name != "STAGE1_MANIFEST.json":
            manifest["files"][str(p.relative_to(INP))] = {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    (INP / "STAGE1_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("STAGE 1 COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
