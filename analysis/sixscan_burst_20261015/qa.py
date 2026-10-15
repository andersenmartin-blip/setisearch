#!/usr/bin/env python3
"""Once-only independent complete-family QA; no detector/generator imports.

Independent native4 grouping uses lexicographic unique rows and explicit alias
membership. Median501 uses a sorted sliding list with nearest edge padding.
Every carrier/width/window/native4 score is reconstructed with the separately
frozen prefix arithmetic, followed by independent full top-five selection.
All OFF >=8 records and their discrete alias witnesses are reconstructed.
"""
from __future__ import annotations
import argparse
from bisect import bisect_left, insort_right
from collections import defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import statistics
import sys
import time
import traceback

STAGE = Path(__file__).resolve().parent
STARTED = time.monotonic()
WIDTHS = (1, 3, 9, 33)
WINDOWS = (0, 2, 4, 6, 8, 10, 12)
NORMAL = ("row_power_median", "row_residual_median", "row_residual_MAD_scale", "row_winsorized_residual_location")
np = None


def require(condition, message):
    if not condition: raise AssertionError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""): h.update(block)
    return h.hexdigest()


def array_sha(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes(order="C")).hexdigest()


def durable(path, value, exclusive=False):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    target = path if exclusive else path.with_name(path.name + ".tmp")
    with target.open("x" if exclusive else "w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False); f.write("\n"); f.flush(); os.fsync(f.fileno())
    if not exclusive: target.replace(path)


def usage():
    r = resource.getrusage(resource.RUSAGE_SELF)
    return {"cpu_s": r.ru_utime + r.ru_stime, "wall_s": time.monotonic() - STARTED,
            "peak_rss_bytes": r.ru_maxrss * 1024}


class Audit:
    def __init__(self): self.checks = 0; self.errors = defaultdict(float)
    def eq(self, got, expected, label):
        require(got == expected, label + ": values differ"); self.checks += 1
    def close(self, got, expected, label, tol=1e-10):
        a = np.asarray(got); b = np.asarray(expected)
        require(a.shape == b.shape, label + ": shapes differ")
        error = float(np.max(np.abs(a.astype(np.float64) - b.astype(np.float64)))) if a.size else 0.
        require(np.isfinite(a).all() and np.isfinite(b).all() and error <= tol, f"{label}: error {error}")
        self.errors[label] = max(self.errors[label], error); self.checks += a.size


def admit():
    go = read(STAGE / "GO.json"); scope = read(STAGE / "SCOPE.json")
    require(go["status"] == "ADMITTED_AFTER_EXACT_PUBLIC_FREEZE_READBACK", "Public exact freeze required")
    require(go["scope_sha256"] == sha(STAGE / "SCOPE.json"), "Scope hash differs")
    observed = {}
    for pin in scope["code_pins"]:
        relative = Path(pin["path"]); require(not relative.is_absolute() and ".." not in relative.parts, "Unsafe pin")
        p = STAGE / relative
        require(p.stat().st_size == pin["bytes"] and sha(p) == pin["sha256"], "Frozen pin differs: " + str(relative))
        observed[str(relative)] = pin["sha256"]
    require(observed.get("qa.py") == sha(Path(__file__)), "Own QA code must be pinned")
    r = scope["resources"]
    require(r["per_case_CPU_s_cap"] == 600, "QA CPU cap differs")
    for var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"): os.environ[var] = "1"
    resource.setrlimit(resource.RLIMIT_AS, (1024 ** 3, 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_CPU, (600, 600))
    def timeout(*_): raise TimeoutError("QA whole-process resource cap; no implicit rerun")
    signal.signal(signal.SIGALRM, timeout); signal.signal(signal.SIGPROF, timeout)
    signal.setitimer(signal.ITIMER_REAL, max(.1, 1800 - (time.monotonic() - STARTED)))
    signal.setitimer(signal.ITIMER_PROF, max(.1, 599 - usage()["cpu_s"]))
    return scope, go, observed


def cdf(x, a, b):
    """Prescribed float64 uniform-convolution arithmetic for byte reproduction."""
    if b == 0: return np.clip((x + a / 2) / a, 0., 1.)
    h = (a + b) / 2; y = np.clip(x, -h, h)
    squares = [np.maximum(y + h, 0.) ** 2, np.maximum(y + (b - a) / 2, 0.) ** 2,
               np.maximum(y + (a - b) / 2, 0.) ** 2, np.maximum(y - h, 0.) ** 2]
    value = ((squares[0] - squares[1]) - squares[2] + squares[3]) / (2 * a * b)
    return np.where(x <= -h, 0., np.where(x >= h, 1., np.clip(value, 0., 1.)))


def reproduce(case, contract, truth, audit):
    identity = case["case_id"]; seed = hashlib.sha256(identity.encode("ascii")).hexdigest()
    audit.eq(seed, case["seed_sha256"], "Independent complete identity seed")
    geo = contract["geometry"]; lo, hi = geo["loaded_source_channel_interval"]
    first = geo["reference_source_channel_interval"][0]; scans = geo["scan_metadata"]
    layers = [[] for _ in scans]; truth_layers = truth["layer_truth"]
    audit.eq(len(case["signal_layers"]), len(truth_layers), "All response layers reproduced")
    primary = []; windows = {}; oracles = {}
    for recipe, saved in zip(case["signal_layers"], truth_layers):
        index = int(recipe["scan_index"]); s = scans[index]
        for field, expected in (("scan_id", s["scan_id"]), ("scan_index", index), ("kind", recipe["kind"]),
                                ("active_source_rows", recipe["active_source_rows"]), ("truth_window_source_rows", recipe["truth_window_source_rows"])):
            audit.eq(saved[field], expected, "Independent layer recipe identity " + field)
        times = np.asarray(s["row_midpoints_seconds_from_tref"], dtype=np.float64)
        centers = first + float(recipe["reference_native_offset"]) + float(recipe["drift_hz_s"]) * times / s["df_hz"]
        b = abs(float(recipe["drift_hz_s"])) * s["tsamp_s"] / abs(s["df_hz"]); a = float(recipe["intrinsic_width_channels"])
        x = np.arange(lo, hi, dtype=np.float64)[None, :] - centers[:, None]
        profile = cdf(x + .5, a, b) - cdf(x - .5, a, b)
        active = recipe["active_source_rows"]; inactive = [r for r in range(16) if r not in active]
        profile[inactive] = 0.
        require(np.isfinite(profile).all() and (profile >= 0).all(), "Independent response finite nonnegative")
        audit.close(profile[active].sum(axis=1), np.ones(len(active)), "Independent unit-area signal profile", 1e-11)
        nearest = np.rint(centers).astype(np.int64); projections = []
        channels = np.arange(lo, hi, dtype=np.int64)
        for w in WIDTHS:
            selected = abs(channels[None, :] - nearest[:, None]) <= w // 2
            projections.append(float(profile[selected].sum() / math.sqrt(4 * w)))
        wi = int(np.argmax(projections)); flux = .25 * float(recipe["nominal_ideal_box_score"]) / projections[wi]
        audit.close(saved["true_continuous_absolute_centers"], centers, "Independent injected continuous centers", 0.)
        audit.eq(saved["true_nearest_even_absolute_centers"], nearest.tolist(), "Independent injected rounded centers")
        audit.close(saved["ideal_box_projection_per_unit_power"], projections[wi], "Independent oracle amplitude", 0.)
        audit.close(saved["mean_integration_frequency_summed_positive_power"], flux, "Independent total raw flux", 0.)
        audit.eq(saved["injection_oracle_width_channels"], WIDTHS[wi], "Independent oracle width")
        if recipe["kind"] == "PRIMARY":
            primary.append(index)
            if s["role"] == "ON":
                windows[s["scan_id"]] = int(recipe["truth_window_source_rows"][0]); oracles[s["scan_id"]] = WIDTHS[wi]
            audit.eq(truth["flux_by_scan"][s["scan_id"]], saved, "Primary flux layer binding")
        layers[index].append(flux * profile)
    audit.eq(primary, case["active_scan_indices"], "Independent prescribed primary activity")
    audit.eq(truth["primary_active_scan_indices"], primary, "Independent primary activity truth")
    audit.eq(truth["active_scan_indices"], primary, "Independent full active scan truth")
    audit.eq(truth["active_ON_scan_ids"], list(windows), "Independent active ON scan identities")
    if windows:
        audit.eq(truth["active_window_start_by_scan"], windows, "Independent truth windows")
        audit.eq(truth["oracle_width_by_scan"], oracles, "Independent truth oracle widths")
        audit.close(truth["reference_source_channel_at_tref"], first + float(case["reference_native_offset"]), "Independent truth reference", 0.)
        audit.close(truth["drift_hz_s"], float(case["drift_hz_s"]), "Independent truth drift", 0.)
    rng = np.random.Generator(np.random.PCG64(int(seed, 16))); arrays = []
    for index in range(6):
        power = rng.gamma(16., .0625, size=(16, hi - lo))
        for added in layers[index]: power += added
        arrays.append(power.astype("<f4"))
    return arrays


def medians_nearest(row):
    """Independent odd-window median with exact nearest-padding semantics."""
    values = row.tolist(); n = len(values); window = sorted([values[0]] * 250 + values[:251])
    result = np.empty(n, dtype=np.float64)
    for center in range(n):
        result[center] = window[250]
        if center + 1 < n:
            outgoing = values[max(0, center - 250)]; pos = bisect_left(window, outgoing)
            require(pos < 501 and window[pos] == outgoing, "Sliding median deletion")
            window.pop(pos); insort_right(window, values[min(n - 1, center + 251)])
    return result


def preprocess(raw):
    normal = np.empty((4, 16), dtype=np.float64); z = np.empty(raw.shape, dtype=np.float64)
    for r in range(16):
        power = raw[r].astype(np.float64); level = float(statistics.median(power[4000:8096].tolist()))
        require(level > 0, "Positive independent row level")
        residual = power / level - medians_nearest(raw[r]) / level
        center = float(statistics.median(residual[4000:8096].tolist()))
        scale = 1.4826 * float(statistics.median(np.abs(residual[4000:8096] - center).tolist()))
        require(scale > 0, "Positive independent MAD")
        location = center + float(np.mean(np.clip(residual[4000:8096] - center, -5 * scale, 5 * scale)))
        normal[:, r] = (level, center, scale, location); z[r] = (residual - location) / scale
    prefix = np.zeros((16, raw.shape[1] + 1), dtype=np.float64)
    prefix[:, 1:] = np.cumsum(z, axis=1, dtype=np.float64)
    boxes = {w: prefix[:, w:] - prefix[:, :-w] for w in WIDTHS}
    return z, normal, boxes


def geometry(contract, corefirst):
    source = contract["geometry"]; scans = source["scan_metadata"]
    anchor = min(s["tstart_mjd"] for s in scans)
    absolute = [(s["tstart_mjd"] - anchor) * 86400. + (np.arange(16, dtype=np.float64) + .5) * s["tsamp_s"] for s in scans]
    span = float(absolute[-1][-1] - absolute[0][0]); tref = float((absolute[0][0] + absolute[-1][-1]) / 2.)
    times = [t - tref for t in absolute]; df = scans[0]["df_hz"]
    n = math.ceil(4 * span / abs(df)); grid = np.linspace(-4., 4., 2 * n + 1, dtype=np.float64); grid[n] = 0.
    step = float(grid[1] - grid[0]); spans = [float(t[w + 3] - t[w]) for t in times for w in WINDOWS]
    mids = [abs(float((t[w] + t[w + 3]) / 2.)) for t in times for w in WINDOWS]
    halo = math.ceil(35 + (70 * abs(df) / min(spans) + 2 * step) * max(mids) / abs(df))
    first = corefirst - halo; tables = []
    for t in times:
        per_scan = {}
        for w in WINDOWS:
            for parity in (0, 1):
                c = first + ((parity - first) % 2)
                all_centers = np.rint(np.float64(c) + grid[:, None] * t[w:w + 4][None, :] / df).astype(np.int64)
                unique, inverse = np.unique(all_centers, axis=0, return_inverse=True)
                minimum = np.full(len(unique), len(grid), dtype=np.int32); maximum = np.full(len(unique), -1, dtype=np.int32)
                indices = np.arange(len(grid), dtype=np.int32)
                np.minimum.at(minimum, inverse, indices); np.maximum.at(maximum, inverse, indices)
                counts = np.bincount(inverse, minlength=len(unique))
                require(np.array_equal(counts, maximum - minimum + 1), "Each discrete alias group is contiguous")
                per_scan[(w, parity)] = {"relative": unique - c, "first": minimum, "last": maximum, "inverse": inverse}
        tables.append(per_scan)
    return times, grid, halo, tables


def stream_search(raw, scan_index, meta, corefirst, loadedfirst, times, grid, halo, tables, audit):
    """Complete independent search. Partial select uses positive kth partition."""
    z, normal, boxes = preprocess(raw)
    first = corefirst if meta["role"] == "ON" else corefirst - halo
    ncar = 4096 if meta["role"] == "ON" else 4096 + 2 * halo
    refs = np.arange(first, first + ncar, dtype=np.int64)
    best_score = np.full((5, ncar), -np.inf); best_width = np.full((5, ncar), 32767, dtype=np.int16)
    best_window = best_width.copy(); best_drift = np.full((5, ncar), 2147483647, dtype=np.int32)
    unique_counts = np.zeros(ncar, dtype=np.int64); records = []; maximum = -np.inf
    for w in WIDTHS:
        for start in WINDOWS:
            for parity in (0, 1):
                columns_all = np.flatnonzero(refs % 2 == parity); table = tables[(start, parity)]
                unique_counts[columns_all] += len(table["first"])
                for clo in range(0, len(columns_all), 256):
                    columns = columns_all[clo:clo + 256]; carrier = refs[columns]
                    for glo in range(0, len(table["first"]), 512):
                        rel = table["relative"][glo:glo + 512]; donors = table["first"][glo:glo + 512]
                        score = np.zeros((len(rel), len(columns)), dtype=np.float64)
                        for r in range(4):
                            local = rel[:, r, None] + carrier[None, :] - loadedfirst - w // 2
                            require(local.min() >= 250 and local.max() + w <= raw.shape[1] - 250, "All raw501/box support")
                            score += boxes[w][start + r, local]
                        score /= math.sqrt(4 * w); maximum = max(maximum, float(score.max()))
                        k = min(5, len(rel)); selected = np.argpartition(score, len(rel) - k, axis=0)[-k:]
                        picked = np.take_along_axis(score, selected, axis=0); cut = picked.min(axis=0)
                        complete_boundary = (score == cut[None, :]).sum(axis=0) == (picked == cut[None, :]).sum(axis=0)
                        for col in np.flatnonzero(~complete_boundary):
                            selected[:, col] = np.lexsort((donors, -score[:, col]))[:k]
                        picked = np.take_along_axis(score, selected, axis=0)
                        values = np.concatenate((best_score[:, columns], picked))
                        widths = np.concatenate((best_width[:, columns], np.full(picked.shape, w, dtype=np.int16)))
                        windows = np.concatenate((best_window[:, columns], np.full(picked.shape, start, dtype=np.int16)))
                        drift = np.concatenate((best_drift[:, columns], donors[selected]))
                        order = np.lexsort((drift, windows, widths, -values), axis=0)[:5]
                        best_score[:, columns] = np.take_along_axis(values, order, axis=0)
                        best_width[:, columns] = np.take_along_axis(widths, order, axis=0)
                        best_window[:, columns] = np.take_along_axis(windows, order, axis=0)
                        best_drift[:, columns] = np.take_along_axis(drift, order, axis=0)
                        if meta["role"] == "OFF":
                            ii, jj = np.nonzero(score >= 8.)
                            for i, j in zip(ii.tolist(), jj.tolist()):
                                group = glo + i; ref = int(carrier[j]); ci = int(columns[j])
                                records.append((ci, ref, w, start, int(donors[i]), int(table["first"][group]), int(table["last"][group]),
                                                float(score[i, j]), (rel[i] + ref).tolist()))
                            require(len(records) <= 2000000, "Complete independent OFF inventory exceeds frozen cap")
    records.sort(key=lambda x: (x[2], x[3], x[0], x[4]))
    maps = {"scores": best_score.T, "widths": best_width.T, "window_starts": best_window.T,
            "drift_grid_indices": best_drift.T, "reference_source_channels": refs, "unique_counts": unique_counts}
    return maps, records, normal, z, maximum


def decode(value, store, audit):
    if isinstance(value, dict) and set(value) == {"array_descriptor"}:
        d = value["array_descriptor"]; a = store[d["npz_key"]]
        audit.eq(list(a.shape), d["shape"], "Persisted array descriptor shape")
        audit.eq(str(a.dtype), d["dtype"], "Persisted array descriptor dtype")
        audit.eq(array_sha(a), d["C_order_bytes_sha256"], "Persisted complete array byte hash")
        return a
    if isinstance(value, dict): return {k: decode(v, store, audit) for k, v in value.items()}
    if isinstance(value, list): return [decode(v, store, audit) for v in value]
    return value


def verify_scan(saved, inventory, certificate, own, records, normal, z, maximum, tables, grid, corefirst, loadedfirst, audit):
    for k in ("widths", "window_starts", "drift_grid_indices", "reference_source_channels"):
        audit.eq(saved[k].tolist(), own[k].tolist(), "Complete independent top-five map " + k)
    audit.close(saved["scores"], own["scores"], "Complete independent top-five scores", 1e-10)
    require(np.isfinite(own["scores"]).all(), "All controlled trajectories valid")
    audit.eq(saved["retained_valid"].tolist(), np.ones(own["scores"].shape, dtype=bool).tolist(), "All finite retained maps")
    originals = np.full(len(own["reference_source_channels"]), len(grid) * 7 * 4, dtype=np.int64)
    for k in ("total_original_hypothesis_count", "valid_original_hypothesis_count"):
        audit.eq(saved[k].tolist(), originals.tolist(), "Complete original-grid hypothesis census")
    for k in ("total_unique_native_hypothesis_count", "valid_unique_native_hypothesis_count"):
        audit.eq(saved[k].tolist(), own["unique_counts"].tolist(), "Complete unique native-path census")
    audit.close(saved["maximum_robust_box_track_score"], own["scores"][:, 0], "Per-carrier complete-family maxima")
    for j, name in enumerate(NORMAL): audit.close(saved["normalization"][name], normal[j], "Independent full-core row normalization")
    audit.eq(saved["normalization"]["normalization_unmasked_counts"], [4096] * 16, "Complete fixed normalization counts")
    audit.eq(saved["normalization"]["normalization_source_channels"], list(range(corefirst, corefirst + 4096)), "Complete normalization coordinates")
    for ci, reference in enumerate(own["reference_source_channels"]):
        for rank in range(5):
            start = int(own["window_starts"][ci, rank]); di = int(own["drift_grid_indices"][ci, rank])
            table = tables[(start, int(reference % 2))]; group = int(table["inverse"][di]); native = reference + table["relative"][group]
            audit.eq(saved["native4_centers"][ci, rank].tolist(), native.tolist(), "Retained complete native identity")
            audit.eq(int(saved["drift_alias_first_index"][ci, rank]), int(table["first"][group]), "Retained full alias first")
            audit.eq(int(saved["drift_alias_last_index"][ci, rank]), int(table["last"][group]), "Retained full alias last")
            w = int(own["widths"][ci, rank]); values = []
            for r, center in enumerate(native): values.extend(z[start + r, int(center) - loadedfirst - w // 2:int(center) - loadedfirst + w // 2 + 1].tolist())
            direct = math.fsum(values) / math.sqrt(4 * w)
            audit.close(own["scores"][ci, rank], direct, "Selected direct-cell sum versus frozen prefix arithmetic", 1e-9)
    if inventory is None: return
    names = ("reference_carrier_index", "reference_source_channel", "width", "window_start", "representative_drift_index", "alias_first_index", "alias_last_index", "score", "native4_centers")
    audit.eq(certificate["complete"], True, "OFF exhaustive inventory complete")
    audit.eq(certificate["inventory_rows"], len(records), "Every OFF threshold identity retained")
    audit.eq(certificate["evaluated_unique_native_hypotheses"], int(own["unique_counts"].sum()), "OFF full unique score census")
    audit.eq(certificate["evaluated_original_grid_hypotheses"], int(originals.sum()), "OFF full alias score census")
    audit.close(certificate["maximum_score_all_evaluated_unique_hypotheses"], maximum, "OFF complete-family maximum")
    for col, name in enumerate(names):
        expected = [row[col] for row in records]
        shape = (len(records), 4) if name == "native4_centers" else (len(records),)
        dtype = np.dtype("float64" if name == "score" else "int64")
        audit.eq(inventory[name].shape, shape, "OFF threshold inventory shape " + name)
        audit.eq(inventory[name].dtype, dtype, "OFF threshold inventory dtype " + name)
        if name == "score": audit.close(inventory[name], expected, "Every OFF >=8 score")
        else: audit.eq(inventory[name].tolist(), expected, "Every OFF >=8 identity/alias " + name)
    independent_arrays = {name: np.asarray([row[col] for row in records], dtype=np.float64 if name == "score" else np.int64).reshape((len(records), 4) if name == "native4_centers" else (len(records),)) for col, name in enumerate(names)}
    calculated = hashlib.sha256(b"".join(np.ascontiguousarray(independent_arrays[name]).tobytes() for name in sorted(independent_arrays))).hexdigest()
    audit.eq(calculated, certificate["inventory_sha256"], "OFF threshold inventory hash")


_ENVELOPE_CACHE = {}


def witness(hit, records, times, grid, df):
    """No interval relaxation: evaluate all discrete pairs in stable order."""
    first = float(times[hit["window_start"]]); last = float(times[hit["window_start"] + 3])
    on = np.arange(hit["drift_alias_first_index"], hit["drift_alias_last_index"] + 1, dtype=np.int32)
    key = id(records)
    if key not in _ENVELOPE_CACHE:
        _ENVELOPE_CACHE[key] = {"reference": np.asarray([r[1] for r in records], dtype=np.float64),
                                "width": np.asarray([r[2] for r in records], dtype=np.float64),
                                "lower": np.asarray([r[5] for r in records], dtype=np.int32),
                                "upper": np.asarray([r[6] for r in records], dtype=np.int32)}
    envelope = _ENVELOPE_CACHE[key]
    delta = envelope["reference"] - hit["reference_source_channel"]
    dlow = grid[envelope["lower"]] - grid[on[-1]]; dhigh = grid[envelope["upper"]] - grid[on[0]]
    tol = (hit["width_channels"] + envelope["width"]) / 2. + 2.
    possible = np.ones(len(records), dtype=bool)
    for endpoint in (first, last):
        e0 = delta + dlow * endpoint / df; e1 = delta + dhigh * endpoint / df
        possible &= (np.minimum(e0, e1) <= tol) & (np.maximum(e0, e1) >= -tol)
    # Only a necessary envelope test; no continuous interval can be a witness.
    for index in np.flatnonzero(possible).tolist():
        record = records[index]
        _, reference, width, start, _, lower, upper, score, native = record
        tolerance = (hit["width_channels"] + width) / 2. + 2.
        off = np.arange(lower, upper + 1, dtype=np.int32)
        delta = float(reference - hit["reference_source_channel"])
        differences = grid[off][None, :] - grid[on][:, None]
        ef = delta + differences * first / df; el = delta + differences * last / df
        valid = (np.abs(ef) <= tolerance) & (np.abs(el) <= tolerance)
        found = np.flatnonzero(valid.ravel())
        if len(found):
            i, j = np.unravel_index(int(found[0]), valid.shape)
            return {"OFF_inventory_index": index, "ON_drift_grid_index": int(on[i]), "OFF_drift_grid_index": int(off[j]),
                    "ON_first_endpoint_error_channels": float(ef[i, j]), "ON_last_endpoint_error_channels": float(el[i, j]),
                    "endpoint_tolerance_channels": tolerance, "OFF_score": score, "OFF_reference_source_channel": reference,
                    "OFF_width_channels": width, "OFF_window_start": start, "OFF_native4_centers": native}
    return None


def verify_hits(output, own_maps, own_inventories, times, grid, scans, tables, audit):
    expected = []
    for si, (meta, own) in enumerate(zip(scans, own_maps)):
        if meta["role"] != "ON": continue
        for ci, rank in zip(*np.nonzero(own["scores"] >= 10.)):
            expected.append((meta["scan_id"], int(ci), int(rank + 1)))
    hits = output["all_ON_threshold_hypotheses"]
    audit.eq([(h["scan_id"], h["reference_carrier_index"], h["retained_rank"]) for h in hits], expected, "Every retained raw ON>=10 hit")
    lookup = {s["scan_id"]: i for i, s in enumerate(scans)}
    for hit in hits:
        si = lookup[hit["scan_id"]]; own = own_maps[si]; ci = hit["reference_carrier_index"]; rank = hit["retained_rank"] - 1
        audit.close(hit["ON_score"], own["scores"][ci, rank], "Raw ON threshold score")
        audit.eq(hit["width_channels"], int(own["widths"][ci, rank]), "Raw ON hit width")
        audit.eq(hit["window_start"], int(own["window_starts"][ci, rank]), "Raw ON hit window")
        reference = int(own["reference_source_channels"][ci]); start = int(own["window_starts"][ci, rank]); di = int(own["drift_grid_indices"][ci, rank])
        table = tables[si][(start, reference % 2)]; group = int(table["inverse"][di])
        for field, expected in (("reference_source_channel", reference), ("representative_drift_grid_index", di),
                                ("drift_alias_first_index", int(table["first"][group])), ("drift_alias_last_index", int(table["last"][group])),
                                ("native4_centers", (reference + table["relative"][group]).tolist()), ("window_start_row", start),
                                ("window_source_rows", list(range(start, start + 4))), ("hit_id", f'{scans[si]["scan_id"]}:carrier{ci:04d}:rank{rank+1}')):
            audit.eq(hit[field], expected, "Raw ON hit independently bound " + field)
        audit.close(hit["representative_drift_hz_s"], grid[di], "Raw ON representative drift", 0.)
        vetoes = []
        audit.eq([r["scan_id"] for r in hit["OFF_comparisons"]], [s["scan_id"] for s in scans if s["role"] == "OFF"], "All three OFF scans tested")
        for receipt in hit["OFF_comparisons"]:
            oi = lookup[receipt["scan_id"]]
            found = witness(hit, own_inventories[oi], times[si], grid, scans[si]["df_hz"])
            audit.eq(receipt["veto"], found is not None, "Exhaustive discrete OFF existential decision")
            audit.eq(receipt["inventory_exhausted_before_query"], True, "Complete inventory before OFF query")
            if found:
                saved = receipt["witness"]
                for k, v in found.items():
                    if isinstance(v, float): audit.close(saved[k], v, "Actual stable OFF witness " + k, 1e-10)
                    else: audit.eq(saved[k], v, "Actual stable OFF witness " + k)
            else:
                audit.eq(receipt["witness"], None, "Absent witness after full discrete search")
                audit.eq(receipt["all_threshold_records_compatibility_checked"], True, "All threshold records checked for negative veto")
            vetoes.append(found is not None)
        audit.eq(hit["disposition"], "OFF_MATCHED" if any(vetoes) else "SURVIVOR_EXPLORATORY", "Raw OFF disposition")
    audit.eq(output["surviving_ON_threshold_hypothesis_count"], sum(h["disposition"] == "SURVIVOR_EXPLORATORY" for h in hits), "All raw after-OFF survivors")


def localized(hit, truth, scan_index, times, grid, df):
    name = hit["scan_id"]
    if name not in truth["active_ON_scan_ids"]: return None
    start = int(truth["active_window_start_by_scan"][name])
    if hit["window_start"] != start: return None
    oracle = int(truth["oracle_width_by_scan"][name]); tolerance = 2. + max(hit["width_channels"], oracle) / 2.
    for donor in range(hit["drift_alias_first_index"], hit["drift_alias_last_index"] + 1):
        delta = hit["reference_source_channel"] - float(truth["reference_source_channel_at_tref"])
        slope = float(grid[donor]) - float(truth["drift_hz_s"])
        ef = delta + slope * float(times[scan_index][start]) / df
        el = delta + slope * float(times[scan_index][start + 3]) / df
        if abs(ef) <= tolerance and abs(el) <= tolerance: return donor
    return None


def verify_recovery(output, truth, times, grid, scans, audit):
    active = truth["active_ON_scan_ids"]; saved = output["recovery"]
    if not active:
        audit.eq(saved["recovery_applicable"], False, "Empty ON activity recovery bypass")
        return {"applicable": False, "any_rank_qualified_localized": False}
    by_scan = {s["scan_id"]: i for i, s in enumerate(scans)}; rows = {}
    for name in active:
        si = by_scan[name]; pre = []; after = []
        for hit in output["all_ON_threshold_hypotheses"]:
            if hit["scan_id"] != name: continue
            donor = localized(hit, truth, si, times, grid, scans[si]["df_hz"])
            if donor is None: continue
            pre.append((hit["hit_id"], donor))
            if hit["disposition"] == "SURVIVOR_EXPLORATORY": after.append((hit["hit_id"], donor))
        observed = saved["by_scan"][name]
        audit.eq(observed["pre_OFF_localized_count"], len(pre), "True-window ANY-alias pre-OFF recovery count")
        audit.eq(observed["final_localized_count"], len(after), "True-window ANY-alias after-OFF recovery count")
        for field, expected in (("pre_OFF_matches", pre), ("final_matches", after)):
            audit.eq([(m["hit_id"], m["matched_donor_drift_grid_index"]) for m in observed[field]], expected, "All actual truth-localized donor matches")
        rows[name] = {"pre_OFF": bool(pre), "after_OFF": bool(after), "after_OFF_hit_ids": [h for h, _ in after]}
    audit.eq(saved["all_active_ON_pre_OFF_recovered"], all(v["pre_OFF"] for v in rows.values()), "All declared active ON recovered pre-OFF")
    audit.eq(saved["all_active_ON_final_recovered"], all(v["after_OFF"] for v in rows.values()), "All declared active ON recovered after-OFF")
    return {"applicable": True, "by_scan": rows}


def main():
    global np
    ap = argparse.ArgumentParser(); pick = ap.add_mutually_exclusive_group(required=True)
    pick.add_argument("--case-index", type=int); pick.add_argument("--exposed-index", type=int)
    ap.add_argument("--output-root", type=Path, required=True); args = ap.parse_args()
    scope, go, pins = admit(); exposed = args.exposed_index is not None
    index = args.exposed_index if exposed else args.case_index; label = ("R" if exposed else "C") + f"{index:04d}"
    root = args.output_root.resolve(); folder = root / ("exposed" if exposed else "cases") / label
    claim_path = STAGE / "claims" / ("QA_" + label + ".json"); receipt_path = root / "qa" / (label + ".json")
    require(not receipt_path.exists(), "No repeated QA receipt")
    durable(claim_path, {"status": "CLAIMED_ONCE", "case_index": index, "exposed": exposed,
                        "exposed_index": index if exposed else None, "scope_sha256": go["scope_sha256"]}, exclusive=True)
    try:
        commit = read(folder / "COMMITTED.json"); require(commit["status"] == "COMPLETED_CASE_ONLY", "Complete producer commit required")
        artifact_path = folder / "artifact_manifest.json"; artifact = read(artifact_path)
        require(sha(artifact_path) == commit["artifact_manifest_sha256"], "Worker commit artifact hash differs")
        for name, pin in artifact.items():
            p = folder / name; require(p.stat().st_size == pin["bytes"] and sha(p) == pin["sha256"], "Worker complete artifact differs: " + name)
        import numpy as numpy
        np = numpy; require(np.__version__ == "2.3.5", "Frozen NumPy version required")
        audit = Audit(); contract = read(STAGE / "contract.json"); metadata = contract["geometry"]["scan_metadata"]
        bank = read(STAGE / ("real_baselines.json" if exposed else "case_bank.json")); bank = bank if isinstance(bank, list) else bank["cases"]
        case = bank[index]; truth = read(folder / "truth.json"); audit.eq(case["case_id"], truth["case_id"], "QA recipe identity")
        with np.load(folder / "maps.npz", allow_pickle=False) as store: output = decode(read(folder / "output.json"), store, audit)
        audit.eq(output["case_id"], case["case_id"], "Worker output identity")
        loadedfirst = contract["geometry"]["loaded_source_channel_interval"][0]
        corefirst = contract["geometry"]["reference_source_channel_interval"][0]
        with np.load(folder / "inputs.npz", allow_pickle=False) as store:
            inputs = [store[s["scan_id"]] for s in metadata]
        if exposed:
            loadedfirst = case["loaded_source_channel_interval"][0]; corefirst = case["reference_source_channel_interval"][0]
            raw_root = STAGE.parent / "checkpoints/SETI_NATIVE_SPOR_2026-10-14/SETI_NATIVE_SPOR_2026-10-14"
            reproduced = []
            for s in case["scans"]:
                for field in ("raw_crop", "normalization"):
                    pin = s[field]; p = raw_root / pin["path"]
                    audit.eq(p.stat().st_size, pin["bytes"], "Exposed source pinned length")
                    audit.eq(sha(p), pin["sha256"], "Exposed source pinned hash")
                with np.load(raw_root / s["raw_crop"]["path"], allow_pickle=False) as store: reproduced.append(store["raw_power"])
            audit.eq(truth["synthetic_injection"], False, "Exposed source has no synthetic injection")
        else:
            reproduced = reproduce(case, contract, truth, audit)
        independent_hashes = {}
        for s, got, expected in zip(metadata, inputs, reproduced):
            require(got.shape == (16, 12096) and got.dtype == np.dtype("<f4") and np.isfinite(got).all() and (got >= 0).all(), "Six complete decoded raw scans")
            independent_hashes[s["scan_id"]] = array_sha(expected)
            audit.eq(array_sha(got), independent_hashes[s["scan_id"]], "Independent complete raw byte reconstruction")
            audit.eq(array_sha(got), truth["authenticated_input_arrays"][s["scan_id"]]["C_order_bytes_sha256"], "Producer raw hash readback")
        del reproduced
        times, grid, halo, tables = geometry(contract, corefirst)
        audit.eq(halo, output["geometry"]["OFF_reference_halo_channels"], "Complete OFF compatibility carrier halo")
        audit.close(output["geometry"]["drift_grid_hz_s"], grid, "Whole global drift grid", 0.)
        for i in range(6): audit.close(output["geometry"]["times_from_tref_s"][i], times[i], "Complete actual midpoint coordinates", 0.)
        for si, meta in enumerate(metadata):
            for key, table in tables[si].items():
                saved = output["alias_geometry"][meta["scan_id"]][str(key)]
                order = np.argsort(table["first"]); rel = table["relative"][order]
                renumber = np.empty(len(order), dtype=np.int32); renumber[order] = np.arange(len(order), dtype=np.int32)
                for field, expected in (("relative_centers", rel), ("alias_first_index", table["first"][order]),
                                         ("alias_last_index", table["last"][order]), ("drift_to_unique_path", renumber[table["inverse"]])):
                    audit.eq(saved[field].tolist(), expected.tolist(), "Complete independent native-group alias geometry")
        own_maps = []; own_inventories = {}; full_search_checks = []
        for si, s in enumerate(metadata):
            own, records, normal, z, maximum = stream_search(inputs[si], si, s, corefirst, loadedfirst, times[si], grid, halo, tables[si], audit)
            inventory = output["OFF_threshold_inventories"].get(s["scan_id"]); certificate = output["OFF_inventory_certificates"].get(s["scan_id"])
            verify_scan(output["scan_maps"][si], inventory, certificate, own, records, normal, z, maximum, tables[si], grid, corefirst, loadedfirst, audit)
            own_maps.append(own); own_inventories[si] = records
            full_search_checks.append({"scan_id": s["scan_id"], "role": s["role"], "unique_scored": int(own["unique_counts"].sum()),
                                       "original_grid_scored": len(own["reference_source_channels"]) * len(grid) * 7 * 4,
                                       "OFF_ge8_inventory_rows": len(records), "maximum": maximum})
            print(json.dumps({"QA_case": label, "scan_complete": s["scan_id"], "CPU_s": usage()["cpu_s"]}), flush=True)
        independent_max = max(float(m["scores"].max()) for s, m in zip(metadata, own_maps) if s["role"] == "ON")
        audit.close(output["maximum_pre_OFF_ON_score"], independent_max, "Complete global pre-OFF ON maximum", 0.)
        verify_hits(output, own_maps, own_inventories, times, grid, metadata, tables, audit)
        recovery = verify_recovery(output, truth, times, grid, metadata, audit)
        rank_audit = {"applied": False, "reason": "Exposed backgrounds are outside the fresh Gamma16 calibration law"}
        if not exposed:
            definitions = read(STAGE / "case_bank.json"); refs = [(i, c) for i, c in enumerate(definitions) if c["calibration_reference"]]
            require(len(refs) == 63, "Exactly 63 independent reference definitions")
            maxima = []; ref_pins = {}
            for ri, recipe in refs:
                rf = root / "cases" / f"C{ri:04d}"
                require(read(rf / "COMMITTED.json")["status"] == "COMPLETED_CASE_ONLY", "Every rank reference committed")
                value = read(rf / "output.json"); require(value["case_id"] == recipe["case_id"], "Rank reference identity")
                maxima.append(float(value["maximum_pre_OFF_ON_score"])); ref_pins[recipe["case_id"]] = sha(rf / "output.json")
            qualified = []; localized_ids = []
            scan_index = {s["scan_id"]: i for i, s in enumerate(metadata)}
            for hit in output["all_ON_threshold_hypotheses"]:
                score = float(hit["ON_score"]); p = (1 + sum(v >= score for v in maxima)) / 64
                require((p <= 1 / 64) == (score > max(maxima)), "Strict maximum rank and >= ties")
                if hit["disposition"] == "SURVIVOR_EXPLORATORY" and score >= 10 and p <= 1 / 64:
                    qualified.append({"hit_id": hit["hit_id"], "p": p, "ON_score": score})
                    if truth["active_ON_scan_ids"] and localized(hit, truth, scan_index[hit["scan_id"]], times, grid, metadata[0]["df_hz"]) is not None: localized_ids.append(hit["hit_id"])
            rank_audit = {"applied": True, "reference_count": 63, "reference_global_maxima": maxima,
                          "reference_output_sha256": ref_pins, "minimum_possible_p": 1 / 64,
                          "raw_ON_hit_count": len(output["all_ON_threshold_hypotheses"]),
                          "post_OFF_count": output["surviving_ON_threshold_hypothesis_count"],
                          "rank_after_OFF_pass_count": len(qualified), "rank_after_OFF_matches": qualified,
                          "strict_above_reference_maximum": True, "all_reference_full_search_QA_required_before_joint_claim": True}
            recovery["rank_qualified_localized_hit_ids"] = localized_ids
            recovery["any_rank_qualified_localized"] = bool(localized_ids)
        r = usage(); require(r["cpu_s"] <= 600 and r["wall_s"] <= 1800 and r["peak_rss_bytes"] <= 1024 ** 3, "Whole independent QA resource cap")
        result = {"status": "PASS", "schema": "SETI_SIXSCAN_COMPLETE_INDEPENDENT_QA_V1", "case_id": case["case_id"],
                  "case_index": index, "exposed": exposed, "exposed_index": index if exposed else None,
                  "scope_sha256": go["scope_sha256"], "qa_sha256": sha(Path(__file__)), "worker_output_sha256": sha(folder / "output.json"),
                  "output_sha256": sha(folder / "output.json"),
                  "truth_sha256": sha(folder / "truth.json"), "artifact_manifest_sha256": sha(artifact_path),
                  "independent_input_hashes": independent_hashes, "checks": audit.checks, "maximum_absolute_errors": dict(audit.errors),
                  "full_search_checks": full_search_checks, "OFF_inventory_checks": {metadata[i]["scan_id"]: len(v) for i, v in own_inventories.items() if metadata[i]["role"] == "OFF"},
                  "independent_global_pre_OFF_ON_maximum": independent_max, "calibration_rank_audit": rank_audit,
                  "independent_rank_recovery": recovery, "resource_usage": r,
                  "method": "Independent raw byte reproduction; sorted nearest-median501; unique-row native grouping; complete streamed maps and >=8 inventories; all discrete OFF aliases; independent max-rank arithmetic",
                  "qualified_SETI_detection": False, "original_A_B": "FAIL_CLOSED", "new_observation": False}
        durable(receipt_path, result, exclusive=True); durable(claim_path, {"status": "PASS", "receipt_sha256": sha(receipt_path), "resources": r})
        signal.setitimer(signal.ITIMER_REAL, 0); signal.setitimer(signal.ITIMER_PROF, 0)
        print(json.dumps({"status": "PASS", "case": label, "checks": audit.checks, "resources": r}), flush=True)
    except BaseException as error:
        signal.setitimer(signal.ITIMER_REAL, 0); signal.setitimer(signal.ITIMER_PROF, 0)
        failure = {"status": "FAIL_CLOSED", "case_index": index, "exposed": exposed, "exposed_index": index if exposed else None,
                   "scope_sha256": go["scope_sha256"], "failure": {"type": type(error).__name__, "message": str(error)}, "resource_usage": usage()}
        if not receipt_path.exists(): durable(receipt_path, failure, exclusive=True)
        durable(claim_path, failure); traceback.print_exc(); raise
if __name__ == "__main__": main()
