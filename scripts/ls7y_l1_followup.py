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
    with urlopen(Request(BASE + "download", data=json.dumps(payload).encode(),
                         headers={"Accept": "application/json", "User-Agent": "dace-query/3.0.1"}),
                 timeout=45) as r:
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
            "product": kind, "label": label, "start": start, "count": count,
            "sha256": sha(raw), "status": r.status,
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
    out = np.dtype(fields)
    assert out.itemsize == header["NAXIS1"]
    return out


def robust_mad(a):
    a = np.asarray(a, float)
    med = np.median(a)
    return float(1.4826 * np.median(np.abs(a - med)))


def mask_for(center_x, center_y, radius):
    yy, xx = np.mgrid[0:200, 0:200]
    return (xx - center_x) ** 2 + (yy - center_y) ** 2 <= radius ** 2


def temporal_excess(times, values, side_global, event_global):
    t0 = float(np.mean(times[event_global]))
    xs = (times[side_global] - t0) * 86400.0
    xe = (times[event_global] - t0) * 86400.0
    X = np.column_stack([np.ones(len(xs)), xs])
    XE = np.column_stack([np.ones(len(xe)), xe])
    beta = np.linalg.lstsq(X, values[side_global], rcond=None)[0]
    pred = XE @ beta
    return {
        "event_sum": float(np.sum(values[event_global])),
        "baseline_event_sum": float(np.sum(pred)),
        "event_excess": float(np.sum(values[event_global] - pred)),
        "side_median": float(np.median(values[side_global])),
        "side_sigma_mad": robust_mad(values[side_global] - X @ beta),
    }


def pixel_excess_map(times, cube, side_local, event_local):
    t0 = float(np.mean(times[event_local]))
    xs = (times[side_local] - t0) * 86400.0
    xe = (times[event_local] - t0) * 86400.0
    X = np.column_stack([np.ones(len(xs)), xs])
    XE = np.column_stack([np.ones(len(xe)), xe])
    y = cube[side_local].reshape(len(side_local), -1)
    beta = np.linalg.solve(X.T @ X, X.T @ y)
    pred = XE @ beta
    event = cube[event_local].reshape(len(event_local), -1)
    return np.sum(event - pred, axis=0).reshape(200, 200)


def column_component(a):
    col = np.mean(a, axis=0)
    return np.repeat(col[None, :], a.shape[0], axis=0)


def fit_delta_smear(delta, smear, center_x, center_y):
    outside = ~mask_for(center_x, center_y, EXCLUDE_RADIUS)
    y = delta[outside]
    smear_image = np.repeat(smear[None, :], 200, axis=0)
    x = smear_image[outside]
    good = np.isfinite(x) & np.isfinite(y)
    X = np.column_stack([np.ones(int(good.sum())), x[good]])
    beta = np.linalg.lstsq(X, y[good], rcond=None)[0]
    resid = y[good] - X @ beta
    return {
        "alpha": float(beta[0]),
        "beta": float(beta[1]),
        "residual_rms": float(np.sqrt(np.mean(resid * resid))),
        "pixels": int(good.sum()),
    }


def main():
    assert not OUT.exists(), "refuse completed LS7Y output overwrite"
    candidates = json.loads((PILOT / "candidates.json").read_text())
    assert len(candidates["clusters"]) == 2
    fixed = [(x["cluster_id"], x["start"], x["duration"]) for x in candidates["clusters"]]
    assert fixed == [(0, 66, 3), (1, 185, 3)], fixed

    l2_header = fits.Header.fromstring((META / "lightcurve_header.bin").read_bytes().decode("ascii"), sep="")
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
            contexts[ctx["cluster"]][kind] = np.frombuffer(raw, dtype=">f8").reshape(n, 200, 200).astype(float)
            assert np.isfinite(contexts[ctx["cluster"]][kind]).all()

    # Verify the smearing extension header before reading its selected rows.
    sh, rec = read_range("SCI_COR_SubArray", urls["SCI_COR_SubArray"],
                         SMEAR_HEADER_START, SMEAR_HEADER_BYTES, "smearing_header")
    h = fits.Header.fromstring(sh.decode("ascii"), sep="")
    assert h["EXTNAME"] == "SCI_COR_SmearingRow"
    assert h["BITPIX"] == -64
    dims = [h[f"NAXIS{i}"] for i in range(1, h["NAXIS"] + 1)]
    assert np.prod(dims) * 8 == 691200
    assert sorted(dims) == [200, 432]
    (OUT / "SCI_COR_SmearingRow_header.bin").write_bytes(sh)
    rec["file"] = "SCI_COR_SmearingRow_header.bin"
    receipts.append(rec)

    for ctx in CONTEXTS:
        n = ctx["stop"] - ctx["start"]
        start = SMEAR_DATA_START + ctx["start"] * 200 * 8
        count = n * 200 * 8
        raw, rec = read_range("SCI_COR_SubArray", urls["SCI_COR_SubArray"],
                              start, count, f"cluster{ctx['cluster']}_smearing_rows")
        p = OUT / f"SCI_COR_SmearingRow_cluster{ctx['cluster']}_rows_{ctx['start']}_{ctx['stop']-1}.bin"
        p.write_bytes(raw)
        rec["file"] = p.name
        receipts.append(rec)
        contexts[ctx["cluster"]]["SMEAR"] = np.frombuffer(raw, dtype=">f8").reshape(n, 200).astype(float)
        assert np.isfinite(contexts[ctx["cluster"]]["SMEAR"]).all()

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

        sums = {"C0": {"CAL": [], "COR": [], "DELTA": [], "SMEAR": []},
                "C1": {"CAL": [], "COR": [], "DELTA": [], "SMEAR": []}}
        fits_diag = []
        for li, gi in enumerate(range(first, ctx["stop"])):
            cx0 = float(l2["CENTROID_X"][gi]) - XOFF
            cy0 = float(l2["CENTROID_Y"][gi]) - YOFF
            fit = fit_delta_smear(delta[li], smear[li], cx0, cy0)
            fit.update({"row": gi})
            fits_diag.append(fit)
            med = float(np.median(delta[li]))
            mad = robust_mad(delta[li])
            row = {"cluster": cid, "row": gi, "delta_median": med,
                   "delta_sigma_mad": mad, "smear_fit": fit}
            for name, shift in (("C0", 0.0), ("C1", -1.0)):
                cx, cy = cx0 + shift, cy0 + shift
                m = mask_for(cx, cy, AP_RADIUS)
                weights = np.sum(m, axis=0)
                vals = {
                    "CAL": float(np.sum(cal[li][m])),
                    "COR": float(np.sum(cor[li][m])),
                    "DELTA": float(np.sum(delta[li][m])),
                    "SMEAR": float(np.dot(smear[li], weights)),
                }
                for k, v in vals.items():
                    sums[name][k].append(v)
                row[name] = vals
            frame_rows.append(row)

        # Event excess maps use exact local 24 sidebands and 3 event frames.
        cal_map = pixel_excess_map(times_local, cal, side_local, event_local)
        cor_map = pixel_excess_map(times_local, cor, side_local, event_local)
        delta_map = cor_map - cal_map
        col_delta = column_component(delta_map)

        mean_cx0 = float(np.mean(l2["CENTROID_X"][event_global])) - XOFF
        mean_cy0 = float(np.mean(l2["CENTROID_Y"][event_global])) - YOFF
        conv = {}
        correction_gate = []
        localized_gate = []
        for name, shift in (("C0", 0.0), ("C1", -1.0)):
            m25 = mask_for(mean_cx0 + shift, mean_cy0 + shift, AP_RADIUS)
            m35 = mask_for(mean_cx0 + shift, mean_cy0 + shift, EXCLUDE_RADIUS)
            temporal = {}
            for k in ("CAL", "COR", "DELTA", "SMEAR"):
                arr = np.asarray(sums[name][k], float)
                # temporal_excess indexes local arrays, so convert global side/event to local
                temporal[k] = temporal_excess(times_local, arr, side_local, event_local)
            cor_abs = float(np.sum(np.abs(cor_map)))
            concentration = float(np.sum(np.abs(cor_map[m25])) / cor_abs) if cor_abs else None
            delta_ap = float(np.sum(delta_map[m25]))
            cor_ap = float(np.sum(cor_map[m25]))
            col_ap = float(np.sum(col_delta[m25]))
            conv[name] = {
                "center_event_mean": [mean_cx0 + shift, mean_cy0 + shift],
                "aperture_pixels": int(m25.sum()),
                "temporal": temporal,
                "maps": {
                    "cal_r25_sum": float(np.sum(cal_map[m25])),
                    "cor_r25_sum": cor_ap,
                    "delta_r25_sum": delta_ap,
                    "cal_r35_sum": float(np.sum(cal_map[m35])),
                    "cor_r35_sum": float(np.sum(cor_map[m35])),
                    "delta_r35_sum": float(np.sum(delta_map[m35])),
                    "cal_full_sum": float(np.sum(cal_map)),
                    "cor_full_sum": float(np.sum(cor_map)),
                    "delta_full_sum": float(np.sum(delta_map)),
                    "cor_l1_concentration_r25": concentration,
                    "delta_column_component_r25_sum": col_ap,
                },
            }
            cor_ex = temporal["COR"]["event_excess"]
            delta_ex = temporal["DELTA"]["event_excess"]
            correction_gate.append(
                abs(delta_ex) >= 0.5 * abs(cor_ex) or
                abs(col_ap) >= 0.5 * abs(cor_ex)
            )
            localized_gate.append(
                cor_ex > 0 and concentration is not None and concentration >= 0.5
            )

        if all(correction_gate):
            label = "CORRECTION_LINKED"
        elif not any(correction_gate) and all(localized_gate):
            label = "IMAGE_LOCALIZED_NOT_CORRECTION_DOMINATED"
        else:
            label = "AMBIGUOUS_IMAGE_FOLLOWUP"

        denom = float(np.sum(delta_map * delta_map))
        col_fraction = float(np.sum(col_delta * col_delta) / denom) if denom else None
        result = {
            "cluster": cid,
            "event_rows": [int(x) for x in event_global],
            "context_rows": [first, ctx["stop"] - 1],
            "ls7x_score": float(candidates["clusters"][cid]["score"]),
            "conventions": conv,
            "delta_event_map_column_coherence_fraction": col_fraction,
            "smear_fit_event": [fits_diag[x]["beta"] for x in event_local],
            "smear_fit_side_median_beta": float(np.median([fits_diag[x]["beta"] for x in side_local])),
            "classification": label,
        }
        cluster_results.append(result)
        np.savez_compressed(OUT / f"cluster_{cid}_event_excess_maps.npz",
                            cal=cal_map, cor=cor_map, delta=delta_map,
                            delta_column_component=col_delta)

    raw_lines = "".join(json.dumps(x, sort_keys=True, allow_nan=False) + "\n" for x in frame_rows).encode()
    (OUT / "frame_metrics.jsonl.gz").write_bytes(gzip.compress(raw_lines, mtime=0))
    save(OUT / "summary.json", {
        "stage": "LS7Y_CHEOPS_L1_IMAGE_FOLLOWUP",
        "status": "COMPLETE_UNAUDITED",
        "parent": "LS7X",
        "clusters": cluster_results,
        "other_l2_apertures_opened": False,
        "raw_imagettes_opened": False,
        "other_subarray_rows_opened": False,
        "artificial_or_astrophysical_classification": False,
    })

    lines = [
        "# LS7Y CHEOPS L1 image-domain follow-up", "",
        "Frozen before the two LS7X candidate image contexts were opened.", "",
        "| Cluster | LS7X score | Image follow-up label | DELTA column coherence |",
        "|---:|---:|---|---:|",
    ]
    for x in cluster_results:
        cf = x["delta_event_map_column_coherence_fraction"]
        lines.append(f"| {x['cluster']} | {x['ls7x_score']:.6f} | {x['classification']} | {cf:.6g} |")
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
    (OUT / "SHA256SUMS").write_text("".join(f"{sha(p.read_bytes())}  {p.name}\n" for p in files))
    print(json.dumps(json.loads((OUT / "summary.json").read_text()), indent=2))


if __name__ == "__main__":
    main()
