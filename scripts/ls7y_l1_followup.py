#!/usr/bin/env python3
"""Run the frozen LS7Y bounded CHEOPS L1 image follow-up."""
import gzip
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
from astropy.io import fits

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results_ls7y_l1_followup"
META = ROOT / "results_ls7x_l2_metadata"
PILOT = ROOT / "results_ls7x_l2_pilot"
BASE = "https://cheops-webapp-pg.obsuksprd2.unige.ch/"
KEY = "CH_PR300024_TG000301_V0300"

PRODUCTS = {
    "SCI_CAL_SubArray": {
        "total": 138343680,
        "etag": '"1678907803.6927166-138343680-354560397"',
        "filename": "CH_PR300024_TG000301_TU2020-03-09T04-59-05_SCI_CAL_SubArray_V0300.fits",
    },
    "SCI_COR_SubArray": {
        "total": 139812480,
        "etag": '"1678908364.0785742-139812480-383003041"',
        "filename": "CH_PR300024_TG000301_TU2020-03-09T04-59-05_SCI_COR_SubArray_V0300.fits",
    },
}
CONTEXTS = [
    {"cluster": 0, "start": 52, "stop": 83, "event_start": 66, "event_stop": 69},
    {"cluster": 1, "start": 171, "stop": 202, "event_start": 185, "event_stop": 188},
]
IMAGE_START = 17280
FRAME_BYTES = 200 * 200 * 8
SMEAR_HEADER_START = 138418560
SMEAR_HEADER_BYTES = 5760
SMEAR_DATA_START = 138424320
XOFF = 715.0
YOFF = 181.0
AP_RADIUS = 25.0
EXCLUDE_RADIUS = 35.0


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def get_url(kind):
    payload = {"fileType": kind, "filters": {"file_key": {"equal": [KEY]}}, "aperture": None}
    with urlopen(Request(
        BASE + "download",
        data=json.dumps(payload).encode(),
        headers={"Accept": "application/json", "User-Agent": "dace-query/3.0.1"},
    ), timeout=45) as r:
        info = json.load(r)
    return BASE + "download/photometry/" + info["key"] + "?compressed=false"


def read_range(kind, url, start, count, label):
    spec = PRODUCTS[kind]
    with urlopen(Request(url, headers={
        "Range": f"bytes={start}-{start+count-1}",
        "If-Match": spec["etag"],
        "Accept": "application/octet-stream",
        "Accept-Encoding": "identity",
    }), timeout=90) as r:
        assert r.status == 206, r.status
        assert r.headers["Content-Range"] == f"bytes {start}-{start+count-1}/{spec['total']}"
        assert int(r.headers["Content-Length"]) == count
        assert r.headers.get("ETag") == spec["etag"]
        assert r.headers.get("Content-Disposition") == f"attachment; filename={spec['filename']}"
        raw = r.read(count + 1)
        assert len(raw) == count
        receipt = {
            "product": kind,
            "label": label,
            "start": start,
            "count": count,
            "sha256": sha(raw),
            "status": r.status,
            "etag": r.headers.get("ETag"),
            "content_range": r.headers.get("Content-Range"),
            "content_disposition": r.headers.get("Content-Disposition"),
            "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        }
    return raw, receipt


def table_dtype(header):
    fields = []
    for i in range(1, header["TFIELDS"] + 1):
        count, code = re.fullmatch(r"(\d*)([ADEJI])", header[f"TFORM{i}"]).groups()
        n = int(count or "1")
        name = header[f"TTYPE{i}"]
        if code == "A":
            fields.append((name, f"S{n}"))
        else:
            typ = {"D": ">f8", "E": ">f4", "J": ">i4", "I": ">i2"}[code]
            fields.append((name, typ, (n,)) if n != 1 else (name, typ))
    result = np.dtype(fields)
    assert result.itemsize == header["NAXIS1"]
    return result


def robust_mad_finite(a):
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    if not len(a):
        return None
    med = np.median(a)
    return float(1.4826 * np.median(np.abs(a - med)))


def finite_median(a):
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    return float(np.median(a)) if len(a) else None


def mask_for(center_x, center_y, radius):
    yy, xx = np.mgrid[0:200, 0:200]
    return (xx - center_x) ** 2 + (yy - center_y) ** 2 <= radius ** 2


def temporal_excess(times, values, side_local, event_local):
    values = np.asarray(values, dtype=object)
    if len(values) != 31 or any(v is None for v in values):
        return {"available": False}
    yall = np.asarray(values, float)
    if not np.isfinite(yall).all():
        return {"available": False}
    t0 = float(np.mean(times[event_local]))
    xs = (times[side_local] - t0) * 86400.0
    xe = (times[event_local] - t0) * 86400.0
    X = np.column_stack([np.ones(len(side_local)), xs])
    XE = np.column_stack([np.ones(len(event_local)), xe])
    beta = np.linalg.lstsq(X, yall[side_local], rcond=None)[0]
    residual = yall[side_local] - X @ beta
    predicted = XE @ beta
    return {
        "available": True,
        "event_sum": float(np.sum(yall[event_local])),
        "baseline_event_sum": float(np.sum(predicted)),
        "event_excess": float(np.sum(yall[event_local] - predicted)),
        "side_median": float(np.median(yall[side_local])),
        "side_sigma_mad": float(1.4826 * np.median(np.abs(residual - np.median(residual)))),
    }


def pixel_excess_map(times, cube, side_local, event_local):
    used = np.r_[side_local, event_local]
    eligible = np.isfinite(cube[used]).all(axis=0)
    result = np.full((200, 200), np.nan, dtype=float)
    if not eligible.any():
        return result, eligible
    t0 = float(np.mean(times[event_local]))
    xs = (times[side_local] - t0) * 86400.0
    xe = (times[event_local] - t0) * 86400.0
    X = np.column_stack([np.ones(len(side_local)), xs])
    XE = np.column_stack([np.ones(len(event_local)), xe])
    y = cube[side_local][:, eligible]
    beta = np.linalg.solve(X.T @ X, X.T @ y)
    predicted_sum = np.sum(XE @ beta, axis=0)
    event_sum = np.sum(cube[event_local][:, eligible], axis=0)
    result[eligible] = event_sum - predicted_sum
    return result, eligible


def column_component(delta_map, common):
    component = np.full_like(delta_map, np.nan, dtype=float)
    for x in range(delta_map.shape[1]):
        m = common[:, x]
        if m.any():
            value = float(np.mean(delta_map[m, x]))
            component[m, x] = value
    return component


def fit_delta_smear(delta, smear, center_x, center_y):
    outside = ~mask_for(center_x, center_y, EXCLUDE_RADIUS)
    smear_image = np.repeat(smear[None, :], 200, axis=0)
    good = outside & np.isfinite(delta) & np.isfinite(smear_image)
    if int(good.sum()) < 3:
        return {"available": False, "pixels": int(good.sum())}
    y = delta[good]
    x = smear_image[good]
    X = np.column_stack([np.ones(len(x)), x])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    resid = y - X @ beta
    return {
        "available": True,
        "alpha": float(beta[0]),
        "beta": float(beta[1]),
        "residual_rms": float(np.sqrt(np.mean(resid * resid))),
        "pixels": int(good.sum()),
    }


def masked_sum(a, mask):
    if not mask.any():
        return None
    values = np.asarray(a, float)[mask]
    if not np.isfinite(values).all():
        return None
    return float(np.sum(values))


def common_sum(a, mask):
    use = mask & np.isfinite(a)
    return float(np.sum(a[use])) if use.any() else None


def main():
    assert not OUT.exists(), "refuse completed LS7Y output overwrite"
    candidates = json.loads((PILOT / "candidates.json").read_text())
    assert len(candidates["clusters"]) == 2
    fixed = [(x["cluster_id"], x["start"], x["duration"]) for x in candidates["clusters"]]
    assert fixed == [(0, 66, 3), (1, 185, 3)], fixed

    l2_header = fits.Header.fromstring(
        (META / "lightcurve_header.bin").read_bytes().decode("ascii"), sep=""
    )
    l2_raw = (PILOT / "lightcurve_table.bin").read_bytes()
    l2 = np.frombuffer(l2_raw, dtype=table_dtype(l2_header), count=432)
    bjd = l2["BJD_TIME"].astype(float)

    OUT.mkdir()
    urls = {kind: get_url(kind) for kind in PRODUCTS}
    receipts = []
    contexts = {}

    for ctx in CONTEXTS:
        n = ctx["stop"] - ctx["start"]
        assert n == 31
        contexts[ctx["cluster"]] = {}
        for kind in ("SCI_CAL_SubArray", "SCI_COR_SubArray"):
            start = IMAGE_START + ctx["start"] * FRAME_BYTES
            count = n * FRAME_BYTES
            raw, rec = read_range(kind, urls[kind], start, count, f"cluster{ctx['cluster']}_frames")
            p = OUT / f"{kind}_cluster{ctx['cluster']}_rows_{ctx['start']}_{ctx['stop']-1}.bin"
            p.write_bytes(raw)
            rec["file"] = p.name
            receipts.append(rec)
            cube = np.frombuffer(raw, dtype=">f8").reshape(n, 200, 200).astype(float)
            contexts[ctx["cluster"]][kind] = cube

    sh, rec = read_range(
        "SCI_COR_SubArray", urls["SCI_COR_SubArray"],
        SMEAR_HEADER_START, SMEAR_HEADER_BYTES, "smearing_header"
    )
    h = fits.Header.fromstring(sh.decode("ascii"), sep="")
    assert h["EXTNAME"] == "SCI_COR_SmearingRow"
    assert h["BITPIX"] == -64
    dims = [h[f"NAXIS{i}"] for i in range(1, h["NAXIS"] + 1)]
    assert np.prod(dims) * 8 == 691200
    assert dims[0] == 200
    assert int(np.prod(dims[1:])) == 432
    (OUT / "SCI_COR_SmearingRow_header.bin").write_bytes(sh)
    rec["file"] = "SCI_COR_SmearingRow_header.bin"
    receipts.append(rec)

    for ctx in CONTEXTS:
        n = ctx["stop"] - ctx["start"]
        start = SMEAR_DATA_START + ctx["start"] * 200 * 8
        count = n * 200 * 8
        raw, rec = read_range(
            "SCI_COR_SubArray", urls["SCI_COR_SubArray"],
            start, count, f"cluster{ctx['cluster']}_smearing_rows"
        )
        p = OUT / f"SCI_COR_SmearingRow_cluster{ctx['cluster']}_rows_{ctx['start']}_{ctx['stop']-1}.bin"
        p.write_bytes(raw)
        rec["file"] = p.name
        receipts.append(rec)
        contexts[ctx["cluster"]]["SMEAR"] = (
            np.frombuffer(raw, dtype=">f8").reshape(n, 200).astype(float)
        )

    save(OUT / "acquisition.json", {
        "file_key": KEY,
        "subarray_science_bytes": 39680000,
        "smearing_data_bytes": 99200,
        "smearing_header_bytes": SMEAR_HEADER_BYTES,
        "products": PRODUCTS,
        "contexts": CONTEXTS,
        "receipts": receipts,
    })

    cluster_results = []
    frame_rows = []
    for ctx in CONTEXTS:
        cid = ctx["cluster"]
        first = ctx["start"]
        event_global = np.arange(ctx["event_start"], ctx["event_stop"])
        left = np.arange(ctx["event_start"] - 2 - 12, ctx["event_start"] - 2)
        right = np.arange(ctx["event_stop"] + 2, ctx["event_stop"] + 2 + 12)
        side_global = np.r_[left, right]
        assert side_global[0] == ctx["start"] and side_global[-1] == ctx["stop"] - 1
        side_local = side_global - first
        event_local = event_global - first

        cal = contexts[cid]["SCI_CAL_SubArray"]
        cor = contexts[cid]["SCI_COR_SubArray"]
        smear = contexts[cid]["SMEAR"]
        delta = cor - cal
        times_local = bjd[first:ctx["stop"]]

        sums = {
            "C0": {"CAL": [], "COR": [], "DELTA": [], "SMEAR": []},
            "C1": {"CAL": [], "COR": [], "DELTA": [], "SMEAR": []},
        }
        fits_diag = []
        finite_counts = {
            "CAL": int(np.isfinite(cal).sum()),
            "COR": int(np.isfinite(cor).sum()),
            "DELTA": int(np.isfinite(delta).sum()),
            "SMEAR": int(np.isfinite(smear).sum()),
        }

        for li, gi in enumerate(range(first, ctx["stop"])):
            cx0 = float(l2["CENTROID_X"][gi]) - XOFF
            cy0 = float(l2["CENTROID_Y"][gi]) - YOFF
            fit = fit_delta_smear(delta[li], smear[li], cx0, cy0)
            fit["row"] = gi
            fits_diag.append(fit)

            row = {
                "cluster": cid,
                "row": gi,
                "finite_pixels": {
                    "CAL": int(np.isfinite(cal[li]).sum()),
                    "COR": int(np.isfinite(cor[li]).sum()),
                    "DELTA": int(np.isfinite(delta[li]).sum()),
                    "SMEAR": int(np.isfinite(smear[li]).sum()),
                },
                "delta_median": finite_median(delta[li]),
                "delta_sigma_mad": robust_mad_finite(delta[li]),
                "smear_fit": fit,
            }
            for name, shift in (("C0", 0.0), ("C1", -1.0)):
                cx, cy = cx0 + shift, cy0 + shift
                m = mask_for(cx, cy, AP_RADIUS)
                weights = np.sum(m, axis=0)
                smear_selected = smear[li][weights > 0]
                vals = {
                    "CAL": masked_sum(cal[li], m),
                    "COR": masked_sum(cor[li], m),
                    "DELTA": masked_sum(delta[li], m),
                    "SMEAR": (
                        float(np.dot(smear[li], weights))
                        if np.isfinite(smear_selected).all() else None
                    ),
                }
                for key, value in vals.items():
                    sums[name][key].append(value)
                row[name] = {
                    **vals,
                    "aperture_pixels": int(m.sum()),
                    "complete_finite": {
                        "CAL": vals["CAL"] is not None,
                        "COR": vals["COR"] is not None,
                        "DELTA": vals["DELTA"] is not None,
                        "SMEAR": vals["SMEAR"] is not None,
                    },
                }
            frame_rows.append(row)

        cal_map, cal_eligible = pixel_excess_map(times_local, cal, side_local, event_local)
        cor_map, cor_eligible = pixel_excess_map(times_local, cor, side_local, event_local)
        common = cal_eligible & cor_eligible
        delta_map = np.full((200, 200), np.nan, dtype=float)
        delta_map[common] = cor_map[common] - cal_map[common]
        col_delta = column_component(delta_map, common)

        mean_cx0 = float(np.mean(l2["CENTROID_X"][event_global])) - XOFF
        mean_cy0 = float(np.mean(l2["CENTROID_Y"][event_global])) - YOFF
        conv = {}
        correction_gate = []
        localized_gate = []
        central_complete = []

        for name, shift in (("C0", 0.0), ("C1", -1.0)):
            m25 = mask_for(mean_cx0 + shift, mean_cy0 + shift, AP_RADIUS)
            m35 = mask_for(mean_cx0 + shift, mean_cy0 + shift, EXCLUDE_RADIUS)
            temporal = {k: temporal_excess(times_local, v, side_local, event_local)
                        for k, v in sums[name].items()}
            complete = bool(common[m25].all()) and all(
                temporal[k].get("available", False) for k in ("CAL", "COR", "DELTA", "SMEAR")
            )
            central_complete.append(complete)

            common_abs_cor = np.abs(cor_map[common])
            denom_l1 = float(np.sum(common_abs_cor)) if len(common_abs_cor) else 0.0
            m25_common = m25 & common
            concentration = (
                float(np.sum(np.abs(cor_map[m25_common])) / denom_l1)
                if denom_l1 > 0 else None
            )
            delta_ap = common_sum(delta_map, m25_common)
            cor_ap = common_sum(cor_map, m25_common)
            col_ap = common_sum(col_delta, m25_common)

            conv[name] = {
                "center_event_mean": [mean_cx0 + shift, mean_cy0 + shift],
                "aperture_pixels": int(m25.sum()),
                "central_common_eligible_pixels": int(common[m25].sum()),
                "central_complete": complete,
                "temporal": temporal,
                "maps": {
                    "cal_r25_sum": common_sum(cal_map, m25_common),
                    "cor_r25_sum": cor_ap,
                    "delta_r25_sum": delta_ap,
                    "cal_r35_sum": common_sum(cal_map, m35 & common),
                    "cor_r35_sum": common_sum(cor_map, m35 & common),
                    "delta_r35_sum": common_sum(delta_map, m35 & common),
                    "cal_full_sum": common_sum(cal_map, common),
                    "cor_full_sum": common_sum(cor_map, common),
                    "delta_full_sum": common_sum(delta_map, common),
                    "cor_l1_concentration_r25": concentration,
                    "delta_column_component_r25_sum": col_ap,
                },
            }

            if complete:
                cor_ex = temporal["COR"]["event_excess"]
                delta_ex = temporal["DELTA"]["event_excess"]
                correction_gate.append(
                    abs(delta_ex) >= 0.5 * abs(cor_ex)
                    or abs(col_ap) >= 0.5 * abs(cor_ex)
                )
                localized_gate.append(
                    cor_ex > 0 and concentration is not None and concentration >= 0.5
                )
            else:
                correction_gate.append(False)
                localized_gate.append(False)

        if not all(central_complete):
            label = "AMBIGUOUS_IMAGE_FOLLOWUP"
        elif all(correction_gate):
            label = "CORRECTION_LINKED"
        elif not any(correction_gate) and all(localized_gate):
            label = "IMAGE_LOCALIZED_NOT_CORRECTION_DOMINATED"
        else:
            label = "AMBIGUOUS_IMAGE_FOLLOWUP"

        denom = float(np.sum(delta_map[common] ** 2)) if common.any() else 0.0
        coherence = (
            float(np.sum(col_delta[common] ** 2) / denom) if denom > 0 else None
        )
        event_fit_beta = [
            fits_diag[x].get("beta") if fits_diag[x].get("available") else None
            for x in event_local
        ]
        side_beta = [
            fits_diag[x]["beta"] for x in side_local if fits_diag[x].get("available")
        ]
        result = {
            "cluster": cid,
            "event_rows": [int(x) for x in event_global],
            "context_rows": [first, ctx["stop"] - 1],
            "ls7x_score": float(candidates["clusters"][cid]["score"]),
            "context_finite_counts": finite_counts,
            "event_map_availability": {
                "cal_eligible_pixels": int(cal_eligible.sum()),
                "cor_eligible_pixels": int(cor_eligible.sum()),
                "common_eligible_pixels": int(common.sum()),
                "common_eligible_fraction": float(common.mean()),
            },
            "conventions": conv,
            "delta_event_map_column_coherence_fraction": coherence,
            "smear_fit_event": event_fit_beta,
            "smear_fit_side_median_beta": (
                float(np.median(side_beta)) if side_beta else None
            ),
            "classification": label,
        }
        cluster_results.append(result)
        np.savez_compressed(
            OUT / f"cluster_{cid}_event_excess_maps.npz",
            cal=cal_map,
            cor=cor_map,
            delta=delta_map,
            delta_column_component=col_delta,
            cal_eligible=cal_eligible,
            cor_eligible=cor_eligible,
            common_eligible=common,
        )

    raw_lines = "".join(
        json.dumps(x, sort_keys=True, allow_nan=False) + "\n" for x in frame_rows
    ).encode()
    (OUT / "frame_metrics.jsonl.gz").write_bytes(gzip.compress(raw_lines, mtime=0))
    save(OUT / "summary.json", {
        "stage": "LS7Y_CHEOPS_L1_IMAGE_FOLLOWUP",
        "status": "COMPLETE_UNAUDITED",
        "parent": "LS7X",
        "finite_pixel_amendment": "LS7Y_FINITE_PIXEL_AMENDMENT.md",
        "clusters": cluster_results,
        "other_l2_apertures_opened": False,
        "raw_imagettes_opened": False,
        "other_subarray_rows_opened": False,
        "artificial_or_astrophysical_classification": False,
    })

    lines = [
        "# LS7Y CHEOPS L1 image-domain follow-up",
        "",
        "Frozen before the two LS7X candidate image contexts were opened; finite-pixel semantics were fixed after the first execution stopped on non-finite pixels and before any LS7Y result was computed.",
        "",
        "| Cluster | LS7X score | Image follow-up label | Common eligible pixels | DELTA column coherence |",
        "|---:|---:|---|---:|---:|",
    ]
    for x in cluster_results:
        cf = x["delta_event_map_column_coherence_fraction"]
        cf_text = f"{cf:.6g}" if cf is not None else "N/A"
        lines.append(
            f"| {x['cluster']} | {x['ls7x_score']:.6f} | {x['classification']} | "
            f"{x['event_map_availability']['common_eligible_pixels']} | {cf_text} |"
        )
    lines += [
        "",
        "These labels describe coupling to the mission CAL->COR image correction only.",
        "They do not classify an excursion as artificial or astrophysical.",
        "",
        "Full numerical result: summary.json. Raw bounded frame ranges and receipts are retained.",
        "Independent publication requires the LS7Y audit.",
        "",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines))
    files = sorted(p for p in OUT.iterdir() if p.is_file() and p.name != "SHA256SUMS")
    (OUT / "SHA256SUMS").write_text(
        "".join(f"{sha(p.read_bytes())}  {p.name}\n" for p in files)
    )
    print(json.dumps(json.loads((OUT / "summary.json").read_text()), indent=2))


if __name__ == "__main__":
    main()
