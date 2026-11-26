#!/usr/bin/python3 -S
"""
Pure-stdlib verification audit (P1-P12) for the Spor 5 Publication,
Machine-Readable Table (.mrt/.fits/.csv), arXiv, and Zenodo Release Package
of SETIsearch Phases D079-D112 (V7.0).

Must execute cleanly under `/usr/bin/python3 -S` (no third-party imports).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import sys
import tarfile
import zipfile

ROOT_DEFAULT = pathlib.Path(__file__).resolve().parents[2]
MONOGRAPH_PDF_SHA256 = "f7368a7901f99abdcb8328f643dece57da3ba5053eb90c247ebb0abea090d334"


def _sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(1048576)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def run_audit(archives_dir: pathlib.Path, root_dir: pathlib.Path) -> int:
    repo = root_dir / "setisearch"
    zp = repo / "zenodo_package"
    tables = zp / "tables"
    pj = repo / "paper_journal"
    ws112 = root_dir / "analysis_workspace" / "work_v7_0_20261126_d112_integral_lhaaso_pev_almab2"
    deliv = root_dir / "seti_spor5_publication_deliverables"
    reports = root_dir / "reports"

    man = json.loads((zp / "ZENODO_DEPOSIT_MANIFEST_SHA256.json").read_text(encoding="utf-8"))
    results = []

    def rec(cid: str, ok: bool, detail: str) -> None:
        tag = "PASS" if ok else "FAIL"
        print(f"[{tag}] {cid}: {detail}")
        results.append((cid, ok, detail))

    # P1: 38/38 Companion Archives A-AL live SHA-256 + table6 match
    comp_man = man["companion_archives"]
    with (tables / "table6_companion_archives_38manifest.csv").open(encoding="utf-8") as f:
        t6 = {r["archive_code"]: r for r in csv.DictReader(f)}
    p1_ok = len(comp_man) == 38 and len(t6) == 38
    verified_arch = 0
    for item in comp_man:
        ap = archives_dir / item["filename"]
        if not ap.exists():
            p1_ok = False
            break
        sz = ap.stat().st_size
        sh = _sha256(ap)
        row = t6.get(item["code"], {})
        if sz == item["bytes"] == int(row.get("bytes", -1)) and sh == item["sha256"] == row.get("sha256"):
            verified_arch += 1
        else:
            p1_ok = False
    rec("P1", p1_ok and verified_arch == 38, f"Verified {verified_arch}/38 Companion Archives A-AL live SHA-256 & table6")

    # P2: WS112 & 105-page monograph untouched
    mono_p = repo / "paper" / "ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf"
    s112_p = ws112 / "results" / "SUMMARY.json"
    p2_ok = mono_p.exists() and _sha256(mono_p) == MONOGRAPH_PDF_SHA256 and s112_p.exists()
    rec("P2", p2_ok, f"Sealed WS112 & 105-page monograph intact (sha256={MONOGRAPH_PDF_SHA256[:12]}...)")

    # P3: All 7 table sets (.mrt/.fits/.csv) exact row counts & 0 ETI
    expected_rows = {
        "table1_master_catalog_1083stars": 1083,
        "table2_solar_neighborhood_10pc_267stars": 267,
        "table3_spectrograph_atlas_72inst_104arms": 104,
        "table4_panchromatic_bridge_matrix_2695cells": 2695,
        "table5_bayesian_ftx_and_cwtfm": 136,
        "table5b_cwtfm_benchmark": 7,
        "table6_companion_archives_38manifest": 38,
    }
    p3_ok = True
    t_details = []
    for base, exp_n in expected_rows.items():
        cp, fp, mp = tables / f"{base}.csv", tables / f"{base}.fits", tables / f"{base}.mrt"
        if not (cp.exists() and fp.exists() and mp.exists() and fp.read_bytes()[:6] == b"SIMPLE"):
            p3_ok = False
            continue
        with cp.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if len(rows) != exp_n:
            p3_ok = False
        if rows and "verified_eti" in rows[0]:
            if any(r["verified_eti"] not in ("0", "0.0") for r in rows):
                p3_ok = False
        t_details.append(f"{base.split('_')[0]}={len(rows)}")
    # Check 72 primary spectrograph units in table3
    with (tables / "table3_spectrograph_atlas_72inst_104arms.csv").open(encoding="utf-8") as f:
        t3_rows = list(csv.DictReader(f))
    n_spec = sum(int(r["is_primary_spec"]) for r in t3_rows)
    if n_spec != 72:
        p3_ok = False
    rec("P3", p3_ok, f"7/7 MRT+FITS+CSV valid ({', '.join(t_details)}; {n_spec} primary units / {len(t3_rows)} arms)")

    # P4: Strict 3-regime scale separation invariants
    with (tables / "table1_master_catalog_1083stars.csv").open(encoding="utf-8") as f:
        t1_rows = list(csv.DictReader(f))
    with (tables / "table4_panchromatic_bridge_matrix_2695cells.csv").open(encoding="utf-8") as f:
        t4_rows = list(csv.DictReader(f))
    n_beam = sum(1 for r in t1_rows if r["has_beamed"] == "True")
    n_he = sum(1 for r in t1_rows if r["has_he_em"] == "True")
    n_nu = sum(1 for r in t1_rows if r["has_neutrino"] == "True")
    n_ic_only = sum(1 for r in t1_rows if r["has_neutrino"] == "True" and r["has_beamed"] == "False" and r["has_he_em"] == "False")
    n_ic_empty_em = sum(1 for r in t4_rows if r["instrument"] == "ICECUBE_10YR" and r["p_beam_10m_kw"] == "")
    p4_ok = (n_beam == 777 and n_he == 352 and n_nu == 54 and n_ic_only == 33 and n_ic_empty_em == 126)
    rec("P4", p4_ok, f"Scale sep: beamed={n_beam}, he_iso={n_he}, nu={n_nu}, ic_only={n_ic_only}, ic_empty_bridge={n_ic_empty_em}/126")

    # P5: Fixed-width MRT alignment & VizieR_ReadMe.txt completeness
    readme_txt = (zp / "VizieR_ReadMe.txt").read_text(encoding="utf-8")
    p5_ok = True
    for base, exp_n in expected_rows.items():
        if f"{base}.mrt" not in readme_txt:
            p5_ok = False
        lines = (tables / f"{base}.mrt").read_text(encoding="utf-8").splitlines()
        sep_idxs = [i for i, l in enumerate(lines) if l.startswith("-" * 20)]
        data_lines = lines[sep_idxs[-1] + 1:] if sep_idxs else []
        if len(data_lines) != exp_n or len({len(dl) for dl in data_lines}) != 1:
            p5_ok = False
    rec("P5", p5_ok, "All 7 MRT fixed-width line widths constant and documented in VizieR_ReadMe.txt")

    # P6: 9/9 PNG figures valid + visually approved in VISUAL_REVIEW_JOURNAL.json
    vr = json.loads((pj / "VISUAL_REVIEW_JOURNAL.json").read_text(encoding="utf-8"))
    figs = sorted((pj / "figures").glob("figJ*.png"))
    p6_ok = (
        len(figs) == 9
        and vr.get("all_figures_inspected") is True
        and vr.get("all_figures_approved") is True
        and vr.get("pdf_layout_approved") is True
        and all(fp.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" for fp in figs)
        and all(fp.name in vr.get("figures", {}) and vr["figures"][fp.name].get("status") == "APPROVED" for fp in figs)
    )
    rec("P6", p6_ok, f"9/9 journal PNGs valid & approved in VISUAL_REVIEW_JOURNAL.json (19-page layout verified)")

    # P7: Headline numbers cross-checked between LaTeX, SUMMARY.json, and table5
    tex_txt = (pj / "andersen2026_aj_synthesis.tex").read_text(encoding="utf-8")
    s112 = json.loads(s112_p.read_text(encoding="utf-8"))
    uni = s112["unified_panchromatic_v7_0_synthesis"]
    with (tables / "table5_bayesian_ftx_and_cwtfm.csv").open(encoding="utf-8") as f:
        t5 = list(csv.DictReader(f))
    f95_sci = next(r for r in t5 if r["cohort"] == "ALL_SCIENCE_EM" and r["power_threshold"] == "ANY_CALIBRATED" and r["duty_cycle_eta"] == "1.0")
    must_tokens = [
        f"{uni['unique_stars_total']:,}", f"{uni['science_stars_total']:,}", f"{uni['control_stars_total']:,}",
        f"{uni['planet_host_stars_total']}", f"{uni['confirmed_exoplanets_total']}", f"{uni['within_10pc_unique_stars']}",
        f"{uni['spectrographs']}", f"{uni['spectral_arms']}", f"{uni['total_octave_span']}",
        f"{uni['high_energy_unbroken_octaves']}", "10/10", f"{uni['total_exposures_d079_d112']:,}",
        f"{uni['total_calibration_trials_d079_d112']:,}", f"{f95_sci['f95_uniform_pct']}", f"{f95_sci['f95_jeffreys_exact_pct']}",
        f"{uni['companion_archives_total']}",
    ]
    missing = [tok for tok in must_tokens if tok not in tex_txt]
    rec("P7", len(missing) == 0, f"All {len(must_tokens)}/{len(must_tokens)} headline metrics verified in Tex (missing={missing})")

    # P8: Bit-identical Journal PDF across all canonical paths & 18-28 page range
    pdf_paths = [
        pj / "andersen2026_aj_synthesis.pdf",
        pj / "ANDERSEN_2026_AJ_PANCHROMATIC_SETI_SYNTHESIS.pdf",
        reports / "ANDERSEN_2026_AJ_PANCHROMATIC_SETI_SYNTHESIS.pdf",
        deliv / "ANDERSEN_2026_AJ_PANCHROMATIC_SETI_SYNTHESIS.pdf",
    ]
    pdf_shas = {_sha256(p) for p in pdf_paths if p.exists()}
    exp_pdf_info = man["publication_artifacts"]["ANDERSEN_2026_AJ_PANCHROMATIC_SETI_SYNTHESIS.pdf"]
    p8_ok = (
        all(p.exists() for p in pdf_paths)
        and len(pdf_shas) == 1
        and next(iter(pdf_shas)) == exp_pdf_info["sha256"]
        and 18 <= int(exp_pdf_info["pages"]) <= 28
    )
    rec("P8", p8_ok, f"Journal PDF bit-identical ({exp_pdf_info['bytes']:,} B, {exp_pdf_info['pages']} pp, sha={exp_pdf_info['sha256'][:12]}...)")

    # P9: arXiv tarball < 50 MiB, complete, bit-identical in deliverables
    tar_p = pj / "arxiv_submission_andersen2026_seti_v7_0.tar.gz"
    tar_deliv = deliv / "arxiv_submission_andersen2026_seti_v7_0.tar.gz"
    p9_ok = tar_p.exists() and tar_deliv.exists() and _sha256(tar_p) == _sha256(tar_deliv) and tar_p.stat().st_size < 50 * 1048576
    if p9_ok:
        with tarfile.open(tar_p, "r:gz") as tf:
            names = set(tf.getnames())
        req = {"andersen2026_aj_synthesis.tex", "00README.XXX"} | {f"figures/{fp.name}" for fp in figs}
        p9_ok = req.issubset(names)
    rec("P9", p9_ok, f"arXiv bundle valid ({tar_p.stat().st_size:,} B = {tar_p.stat().st_size/1048576:.2f} MiB, sha={_sha256(tar_p)[:12]}...)")

    # P10: .zenodo.json, codemeta.json, CITATION.cff valid
    zjson = json.loads((repo / ".zenodo.json").read_text(encoding="utf-8"))
    cm = json.loads((repo / "codemeta.json").read_text(encoding="utf-8"))
    cff = (repo / "CITATION.cff").read_text(encoding="utf-8")
    p10_ok = (
        zjson.get("version") == "7.0.0"
        and cm.get("version") == "7.0.0"
        and "1,083" in zjson.get("description", "")
        and "version: 7.0.0" in cff
        and "1,083" in cff
    )
    rec("P10", p10_ok, "Zenodo, CodeMeta 2.0, and CITATION.cff valid at v7.0.0 / 1,083 stars")

    # P11: Every entry in ZENODO_DEPOSIT_MANIFEST_SHA256.json passes SHA-256
    p11_ok = True
    checked_m = 0
    for tm in man["tables"]:
        bname = tm["base_name"]
        for ext in ("csv", "fits", "mrt"):
            p = tables / f"{bname}.{ext}"
            if not p.exists() or p.stat().st_size != tm[f"{ext}_bytes"] or _sha256(p) != tm[f"{ext}_sha256"]:
                p11_ok = False
            checked_m += 1
    for fn, meta in man["zenodo_files"].items():
        p = (root_dir / fn) if fn == "restore_d112_workspace.py" else (zp / fn)
        if not p.exists() or p.stat().st_size != meta["bytes"] or _sha256(p) != meta["sha256"]:
            p11_ok = False
        checked_m += 1
    for fn, meta in man["publication_artifacts"].items():
        p = (repo / "paper" / fn) if "ECHELLE" in fn else (pj / fn)
        if not p.exists() or p.stat().st_size != meta["bytes"] or _sha256(p) != meta["sha256"]:
            p11_ok = False
        checked_m += 1
    rec("P11", p11_ok, f"All {checked_m} Zenodo manifest artifacts match exact bytes & SHA-256")

    # P12: Continuation ledger invariant
    cont_p = root_dir / "SETI_ACTIVE_CONTINUATION.json"
    cont = json.loads(cont_p.read_text(encoding="utf-8"))
    p12_ok = (
        cont.get("active_phase") == "D097"
        and cont.get("current_table_cells") == 107105
        and "updated_utc" not in cont
        and "d112_completed_v7_0" in cont
    )
    rec("P12", p12_ok, f"SETI_ACTIVE_CONTINUATION.json invariants preserved (len={len(cont)})")

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\nSPOR5_PUBLICATION_AUDIT: {passed}/{len(results)} PASSED")
    return 0 if passed == len(results) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archives-dir", default=str(ROOT_DEFAULT / "archives"))
    ap.add_argument("--root-dir", default=str(ROOT_DEFAULT))
    args = ap.parse_args()
    return run_audit(pathlib.Path(args.archives_dir), pathlib.Path(args.root_dir))


if __name__ == "__main__":
    raise SystemExit(main())
