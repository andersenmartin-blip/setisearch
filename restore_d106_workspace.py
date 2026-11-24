#!/usr/bin/python3 -S
"""
Clean-Room Verification & Full 32-Archive Restoration Script for Phases D069-D106
(Companion Archives A-Z, AA-AF).

Usage:
  Verify all 32 Companion Archives cleanly with pure stdlib Python 3:
    /usr/bin/python3 -S restore_d106_workspace.py --archives-dir /path/to/archives --check-only

  Restore all 32 Companion Archives into a clean directory and recompute D106 from bounded inputs:
    /path/to/.venv/bin/python3 restore_d106_workspace.py --archives-dir /path/to/archives --destination /tmp/d106_clean_restore --recompute
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import zipfile

ROOT_DEFAULT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS106_DIRNAME = "work_v6_4_20261124_d106_vhe_tev_gamma_hess_magic_veritas_hawc_60octave"

COMPANION_ARCHIVES = [
    ("A",  "SETI_D069_D074_FEROS_VELOCITY_CONTEXT_RESULTS_2026-11-13.zip",                           45920303, "b9bd142de7bdbf98b88d87dd5889cee3b1f1b43d93c17c4e711e6ed8a2e11820"),
    ("B",  "SETI_D075_D076_FEROS_ORDERS_AND_DIRECTION_RESULTS_2026-11-13.zip",                        28329072, "2b7c5b48ee2f3b62ec7c3b6b65c150af4fed80b1930355d4d6b212b0d262fa31"),
    ("C",  "SETI_D077_FEROS_WLC_METADATA_GATE_RESULTS_2026-11-14.zip",                                  659654, "828466e2c8ede7897be98d38d247fb18def0e5acdb40754656c8d2517c27c818"),
    ("D",  "SETI_D078_FEROS_RESTFRAME_AND_HD43629_SYNTHESIS_RESULTS_2026-11-14.zip",                  11427944, "83132e0a43903a26ba6808b8bcca34f39850088d0aee05f0bdfb93b5d5ea6069"),
    ("E",  "SETI_D079_V3_CALIBRATED_OPTICAL_SEARCH_RESULTS_2026-11-14.zip",                            5770342, "ae7ec48fc51522c823c06940c60b661725430f632ba6f048402d9cf66ce07af3"),
    ("F",  "SETI_D080_V3_1_EXOPLANET_AND_HARPS_ESPRESSO_RESULTS_2026-11-14.zip",                       7736372, "0c663b2b65e340deedf629cea069cee5092230a954ad56b6c39bf79684f00133"),
    ("G",  "SETI_D081_V3_2_TRANSIT_KINEMATICS_AND_10PC_RESULTS_2026-11-15.zip",                        8045722, "12b951d77993cae116b8b7e8968866c13a374a23bd06ac1e96610ac63ee713a9"),
    ("H",  "SETI_D082_V3_3_NIRPS_NEAR_IR_AND_PANCHROMATIC_RESULTS_2026-11-15.zip",                    29473205, "d5f73f0c93e6e6381441896e0457ea18d3baa05fadd7a8c569b60361f88a2457"),
    ("I",  "SETI_D083_V3_4_CRIRES_KBAND_AND_100STAR_RESULTS_2026-11-15.zip",                           5549428, "f60cf9d63b457c5246dcb14c5b4064376ef709118b5b325360d0d6c1686adf19"),
    ("J",  "SETI_D084_V3_5_NORTHERN_10PC_AND_125STAR_RESULTS_2026-11-16.zip",                         10117107, "d13c6f409047d9b8a16c74f26098c44d4808d9f6a96a2e79dba34395f99d77cc"),
    ("K",  "SETI_D085_V3_6_SPIROU_YJHK_AND_COMB_V4_RESULTS_2026-11-17.zip",                           17448033, "2d27e24d9b943af3ff8d4796155ab0bbf97e87540b265f7cef5df56dba0685cb"),
    ("L",  "SETI_D086_V3_7_UVES_NUV_PANCHROM_AND_COMB_V4_1_RESULTS_2026-11-17.zip",                   22587203, "b37d27ac6269e6671fb341b98514b27edad5b2dbbc392bec75eaeaa63073aea1"),
    ("M",  "SETI_D087_V3_8_SPACE_UV_STIS_FARRED_AND_200STAR_RESULTS_2026-11-18.zip",                  19262628, "95b35e2a8b93b536c07b3c47c6c70f2ab1712455613059d66c7a00fe9591671c"),
    ("N",  "SETI_D088_V3_9_NORTHERN_RADIO23_AND_ALLSKY_COMB_V4_1_RESULTS_2026-11-18.zip",              9492762, "c0210250b925df3bebb1710c2bf7333a64ed767ebdc1f38a496d6a9454f7d45d"),
    ("O",  "SETI_D089_V4_0_SPACE_LYMAN_FUV_NUV_RESULTS_2026-11-19.zip",                                4262551, "4864dd3b5c0e958e428e1af815e1a378a37824d6bc87a89de9c223d89bccd723"),
    ("P",  "SETI_D090_V4_1_JWST_SPACE_THERMAL_IR_RESULTS_2026-11-19.zip",                              8610790, "2940839e8613b0d388c9b922743ba8244852806411f28586696e59eb8d73841a"),
    ("Q",  "SETI_D091_V4_2_ESO_TRIPLE_3ARM_RESULTS_2026-11-20.zip",                                   22923782, "9da4739bdb413d675b9bc1f17dc9d60d5abc7944622714017cf1889a097b51d0"),
    ("R",  "SETI_D092_V5_0_RPCA_RARITY_ELLIPSOID_PPO_MIRI_CCF_RESULTS_2026-11-20.zip",                27934528, "845f0186a6a793ece2b62f9a2e7caaca5181a9b5a12f8db39326376a58a1d8dd"),
    ("S",  "SETI_D093_V5_1_DEDOPPLER_DRIFT_ELLIPSOID_GRACES_CORALIE_CARMENES_RESULTS_2026-11-21.zip", 25934814, "2588057cbd611686d50ced7f4432dce623b16609bc62de01d6460c91c504979a"),
    ("T",  "SETI_D094_V5_2_MULTIEPOCH_DRIFT_APOGEE2_CRIRESJH_MIRILRS_RESULTS_2026-11-21.zip",         16641712, "fea863077ae837b6741d5837990fd357158e00f6a5e3d9adde51f0c81e8ccefc"),
    ("U",  "SETI_D095_V5_3_CURVED_PERIODIC_DRIFT_GHOST_SPITZER_IRS_APOGEE2_RESULTS_2026-11-21.zip",    16898458, "24f5a73a4299d697a198e91e3e15b5b7ddce838f6d055cebe66ddd812520c21d"),
    ("V",  "SETI_D096_V5_4_SOFIA_EXES_MIDIR_ECHELLE_COHERENT_DRIFT_JWST_RESULTS_2026-11-21.zip",      15941580, "a134e4d5d0b6e0cb4e17763dc729203218cac9265c7db75db719135cb01c5158"),
    ("W",  "SETI_D097_V5_5_HERSCHEL_THZ_FARIR_STIS_E140H_OPTICAL_JERK_RESULTS_2026-11-22.zip",        11687103, "aa296f9c72faefcacbd4f4fedb73c7c3f2b1377823fad3e308fd6a9844f6fed8"),
    ("X",  "SETI_D098_V5_6_SOFIA_GREAT_ISO_SWS_FORCAST_OPTICAL_JERK_RESULTS_2026-11-22.zip",          22898406, "f57f48355df2b92257f39d76e83f2d850ae6d9164ea10ef1539bede1ca8fb838"),
    ("Y",  "SETI_D099_V5_7_JCMT_MM_SOFIA_EXES_IRTF_SPEX_KEPLERIAN_DRIFT_RESULTS_2026-11-22.zip",       15546915, "77b187f3509a704978096c14b97f83a13d3eebb6b2fc9d53a8c3b296b362df0b"),
    ("Z",  "SETI_D100_V5_8_JCMT_3MM_SOFIA_FIFILS_IUE_ECCENTRIC_KEPLERIAN_RESULTS_2026-11-22.zip",      13186766, "f8900c1aee6db352b6317c1dd6bf308d286bab2c0c0b367e8863383438446bd2"),
    ("AA", "SETI_D101_V5_9_ALMA_MM_BAND1_GAP_CLOSURE_DRIFTING_COMB_RESULTS_2026-11-23.zip",            18094897, "848a2ade7fdb46ed4e4f067e729ccf796a5181501f6e0ed18f573ff871fa8b20"),
    ("AB", "SETI_D102_V6_0_XRAY_EUV_POISSON_CHANDRA_EUVE_ALMA_UNBROKEN_MM_RESULTS_2026-11-23.zip",     22236761, "684d6828063cf17b8adcd666932633c07196e8764038dbbdd3a48bdd5433ca2c"),
    ("AC", "SETI_D103_V6_1_HARD_XRAY_NUSTAR_XMM_RGS_ALMA_B9B10_700STAR_RESULTS_2026-11-23.zip",        20006424, "d0155c0b3c98625c0e8f9cff5f55ccb89d7477e6ada6b3fd18a0ba8cc6615de4"),
    ("AD", "SETI_D104_V6_2_SOFT_GAMMA_SUZAKU_GSO_XRISM_NICER_200STAR_10PC_RESULTS_2026-11-24.zip",     18980731, "08169d98eb4313ea15610b8c4367f85a717cacdc10263ebd0a21e2a503cfad06"),
    ("AE", "SETI_D105_V6_3_MEV_GEV_GAMMA_OSSE_COMPTEL_FERMI_LAT_800STAR_RESULTS_2026-11-24.zip",       21288611, "74ee4b760a0b585ba6b6d7a2e0edbfe623258aa170a507fe577189247749778a"),
    ("AF", "SETI_D106_V6_4_VHE_TEV_GAMMA_HESS_MAGIC_VERITAS_HAWC_60OCTAVE_RESULTS_2026-11-24.zip",     22232278, "5a5a04924333472d1775f5d6fd843e4712e1d39da824f2a8c6555741a09e0553"),
]


def _sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def verify_archives(archives_dir: pathlib.Path) -> int:
    n_pass = 0
    for lbl, fname, exp_bytes, exp_sha in COMPANION_ARCHIVES:
        p = archives_dir / fname
        if not p.exists():
            print(f"[FAIL] Archive {lbl}: missing {fname}")
            continue
        sz = p.stat().st_size
        sh = _sha256(p)
        if sz != exp_bytes or sh != exp_sha:
            print(f"[FAIL] Archive {lbl}: size/sha mismatch ({sz} vs {exp_bytes}, {sh[:12]} vs {exp_sha[:12]})")
            continue
        with zipfile.ZipFile(p, "r") as zf:
            bad = zf.testzip()
        if bad is not None:
            print(f"[FAIL] Archive {lbl}: corrupt zip entry {bad}")
            continue
        n_pass += 1
        print(f"[PASS] Archive {lbl:2s}: {fname} ({sz:,} B, sha256={sh[:12]}...)")
    print(f"ARCHIVE_VERIFICATION: {n_pass}/{len(COMPANION_ARCHIVES)} PASS")
    return n_pass


def _safe_extract_zip(zpath: pathlib.Path, dest_dir: pathlib.Path) -> None:
    dest_root = dest_dir.resolve()
    with zipfile.ZipFile(zpath, "r") as zf:
        for zi in zf.infolist():
            mode = (zi.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise RuntimeError(f"Refusing symlink inside archive {zpath.name}: {zi.filename}")
            rel = pathlib.PurePosixPath(zi.filename)
            if rel.is_absolute() or ".." in rel.parts:
                raise RuntimeError(f"Unsafe archive entry path {zi.filename}")
            target = (dest_root / rel).resolve()
            if target != dest_root and dest_root not in target.parents:
                raise RuntimeError(f"Path traversal blocked: {zi.filename}")
            if zi.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(zi.filename))


def restore_all(archives_dir: pathlib.Path, destination: pathlib.Path) -> pathlib.Path:
    ws_parent = destination.resolve() / "analysis_workspace"
    ws_parent.mkdir(parents=True, exist_ok=True)
    for _, fname, _, _ in COMPANION_ARCHIVES:
        _safe_extract_zip(archives_dir / fname, ws_parent)
    return ws_parent / WS106_DIRNAME


def recompute_and_verify(ws106: pathlib.Path, archives_dir: pathlib.Path, py_exe: str) -> int:
    out_cmp = ws106.parent.parent / "recompute_d106_check"
    out_cmp.mkdir(parents=True, exist_ok=True)
    cmd = [
        py_exe,
        str(ws106 / "analyze.py"),
        "--from-bounded-inputs",
        "--workspace-dir", str(ws106),
        "--out-dir", str(out_cmp),
        "--archives-dir", str(archives_dir),
    ]
    subprocess.run(cmd, check=True)

    man = json.loads((ws106 / "RESULTS_MANIFEST_SHA256.json").read_text(encoding="utf-8"))
    diffs = []
    for rel, meta in sorted(man["files"].items()):
        if not rel.startswith("results/"):
            continue
        sub_rel = rel[len("results/"):]
        if rel.startswith("results/figures/") or rel == "results/VISUAL_REVIEW.json":
            f_chk = ws106 / rel
        else:
            f_chk = out_cmp / sub_rel
        if not f_chk.exists():
            diffs.append(f"MISSING {sub_rel}")
            continue
        if _sha256(f_chk) != meta["sha256"]:
            diffs.append(f"SHA_DIFF {sub_rel}")
    print(f"Recompute diff check: {len(diffs)} diffs")
    if diffs:
        for d in diffs:
            print(" ", d)
        return 1

    audit_cmd = ["/usr/bin/python3", "-S", str(ws106 / "audit.py"), "--workspace", str(ws106), "--archives-dir", str(archives_dir)]
    subprocess.run(audit_cmd, check=True)
    print("CLEAN_ROOM_32_RECOMPUTE_PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archives-dir", type=pathlib.Path, default=ROOT_DEFAULT / "archives")
    ap.add_argument("--destination", type=pathlib.Path, default=None)
    ap.add_argument("--recompute", action="store_true")
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--python", default=sys.executable)
    args = ap.parse_args()

    archives_dir = args.archives_dir.resolve()
    n_pass = verify_archives(archives_dir)
    if n_pass != len(COMPANION_ARCHIVES):
        return 1

    if args.check_only:
        return 0

    if args.destination is None:
        print("[ERROR] Specify --destination PATH or --check-only")
        return 2

    ws106 = restore_all(archives_dir, args.destination)
    print(f"[RESTORE] Extracted 32/32 Companion Archives A-Z, AA-AF -> {ws106}")

    if args.recompute:
        return recompute_and_verify(ws106, archives_dir, args.python)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
