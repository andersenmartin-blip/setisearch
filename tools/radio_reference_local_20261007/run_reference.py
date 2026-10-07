#!/usr/bin/env python3
"""Bounded second-route Voyager engineering analysis, not scientific validation.

SIGPROC token types follow the BSD-licensed blimpy io/sigproc.py specification
at UCBerkeleySETI/blimpy 3ebf04342227a95405aa32e5bc75832d1dd17f28.
See upstream_blimpy_LICENSE. No HDF5/native runtime reconstruction is needed.
"""
from pathlib import Path
import argparse, csv, datetime, hashlib, json, os, platform, resource, struct, sys, time, urllib.request
COMMAND_WALL_START = time.monotonic()
COMMAND_CPU_START = time.process_time()
import numpy as np
import scipy
from scipy.ndimage import median_filter, maximum_filter1d
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
INT_KEYS = set("telescope_id machine_id data_type barycentric pulsarcentric nbits nsamples nchans nifs nbeams ibeam".split())
FLOAT_KEYS = set("az_start za_start tstart tsamp fch1 foff refdm period src_raj src_dej".split())
STRING_KEYS = {"rawdatafile", "source_name"}

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")

def exact_read(f, n):
    b = f.read(n)
    if len(b) != n:
        raise ValueError("Incomplete SIGPROC header")
    return b

def read_string(f):
    n = struct.unpack("<i", exact_read(f, 4))[0]
    if not 0 < n <= 4096:
        raise ValueError("Invalid SIGPROC string length")
    return exact_read(f, n).decode("ascii")

def read_header(path):
    header = {}
    with path.open("rb") as f:
        if read_string(f) != "HEADER_START":
            raise ValueError("Missing HEADER_START")
        while True:
            k = read_string(f)
            if k == "HEADER_END":
                break
            if k in header:
                raise ValueError(f"Duplicate header key {k}")
            if k in INT_KEYS:
                header[k] = struct.unpack("<i", exact_read(f, 4))[0]
            elif k in FLOAT_KEYS:
                header[k] = struct.unpack("<d", exact_read(f, 8))[0]
            elif k in STRING_KEYS:
                header[k] = read_string(f)
            else:
                raise ValueError(f"Unsupported header key {k}")
        offset = f.tell()
    for k in ("nbits", "nifs", "nchans", "fch1", "foff", "tsamp", "tstart"):
        if k not in header:
            raise ValueError(f"Missing required header key {k}")
    if header["nbits"] != 32 or header["nifs"] != 1:
        raise ValueError("Only little-endian float32 one-IF data supported")
    if header["nchans"] <= 0 or header["tsamp"] <= 0 or header["foff"] == 0:
        raise ValueError("Invalid dimensions/channel spacing/time step")
    nrow, remainder = divmod(path.stat().st_size - offset, 4 * header["nchans"])
    if remainder or nrow < 2:
        raise ValueError("Incomplete spectrum rows or fewer than two rows")
    return header, offset, nrow

def drift_grid(df_hz, span_s, max_drift):
    n = int(np.ceil(max_drift * span_s / abs(df_hz)))
    return np.linspace(-max_drift, max_drift, 2*n+1)

def scan(z, relative_times, df_hz, base_indices, drifts):
    best = np.full(len(base_indices), -np.inf)
    best_drift = np.zeros(len(base_indices))
    for drift in drifts:
        shifts = np.rint(drift * relative_times / df_hz).astype(int)
        idx = base_indices[None, :] + shifts[:, None]
        if idx.min() < 0 or idx.max() >= z.shape[1]:
            raise ValueError("A search carrier lacks full drift halo")
        score = z[np.arange(z.shape[0])[:, None], idx].sum(axis=0) / np.sqrt(z.shape[0])
        improve = score > best
        best[improve] = score[improve]
        best_drift[improve] = drift
    return best, best_drift

def synthetic_engineering_check():
    # Numeric index/sign check only: this is not fresh scientific validation.
    times = np.arange(16, dtype=float)
    df = -2.0
    grid = drift_grid(df, times[-1], 4.0)
    rows = []
    for known in (-2.0, 2.0):
        z = np.zeros((16, 128))
        shifts = np.rint(known * times / df).astype(int)
        z[np.arange(16), 64 + shifts] = 10.0
        score, drift = scan(z, times, df, np.array([64]), grid)
        assert abs(drift[0] - known) <= abs(df)/times[-1]
        assert score[0] == 40.0
        rows.append({"injected_hz_s":known,"recovered_hz_s":float(drift[0]),"score":float(score[0])})
    return {"role":"engineering_numeric_sign_and_grid_only", "count":2, "passed":True, "cases":rows}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, default=ROOT / "Voyager1.single_coarse.fine_res.fil")
    p.add_argument("--output", type=Path, default=ROOT / "results")
    p.add_argument("--download", action="store_true", help="Download pinned public source if absent; no retry")
    a = p.parse_args()
    c = json.loads((ROOT / "config.json").read_text())
    a.output.mkdir(parents=True, exist_ok=False)
    wall_start = COMMAND_WALL_START
    cpu_start = COMMAND_CPU_START
    status = "FAILED_CLOSED"
    log = []
    def say(s):
        log.append(f"{datetime.datetime.now(datetime.timezone.utc).isoformat()} {s}")
        (a.output / "analysis.log").write_text("\n".join(log)+"\n")
        print(s, flush=True)
    try:
        write_json(a.output / "versions.json", {
            "python":sys.version, "numpy":np.__version__, "scipy":scipy.__version__,
            "matplotlib":matplotlib.__version__, "platform":platform.platform(),
            "script_sha256":sha256(Path(__file__)), "config_sha256":sha256(ROOT/"config.json"),
            "prospective_contract_sha256":sha256(ROOT/"PROSPECTIVE_ROUTE.md")})
        write_json(a.output / "synthetic_engineering_check.json", synthetic_engineering_check())
        say("Synthetic engineering sign/grid check passed; telescope values not yet read")
        if not a.source.exists():
            if not a.download:
                raise FileNotFoundError("Source absent; use --download for one bounded ordinary public request")
            a.source.parent.mkdir(parents=True, exist_ok=True)
            received = 0
            download_start = time.monotonic()
            with urllib.request.urlopen(c["source_url"], timeout=30) as response, a.source.open("wb") as f:
                while True:
                    block = response.read(1048576)
                    if not block:
                        break
                    received += len(block)
                    if received > c["max_source_bytes"] or time.monotonic()-download_start > 120:
                        raise ValueError("Download byte or time budget exceeded")
                    f.write(block)
        receipt = {"source_url":c["source_url"], "bytes":a.source.stat().st_size,
                   "sha256":sha256(a.source), "receipt_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "role":c["role"], "array_values_read":False}
        write_json(a.output / "source_receipt.json", receipt)
        say("Source receipt persisted before header/array read")
        if receipt["bytes"] != c["source_bytes"] or receipt["sha256"] != c["source_sha256"]:
            raise ValueError("Pinned source byte-count/SHA256 mismatch")
        header, offset, nrow = read_header(a.source)
        write_json(a.output / "header.json", {"header":header, "data_offset":offset, "n_time_rows":nrow})
        raw = np.memmap(a.source, mode="r", dtype="<f4", offset=offset, shape=(nrow,1,header["nchans"]))
        if not np.isfinite(raw).all() or (raw < 0).any():
            raise ValueError("Non-finite or negative input power")
        freqs = header["fch1"] + np.arange(header["nchans"]) * header["foff"]
        selected = np.flatnonzero((freqs >= c["search_mhz"][0]) & (freqs <= c["search_mhz"][1]))
        if selected.size < 2 or np.any(np.diff(selected) != 1):
            raise ValueError("Search band absent or discontiguous")
        times = np.arange(nrow)*header["tsamp"]
        df_hz = header["foff"] * 1e6
        halo = int(np.ceil(c["max_drift_hz_s"]*times[-1]/abs(df_hz))) + 1 + (c["running_median_channels"]//2) + 1
        lo, hi = int(selected[0])-halo, int(selected[-1])+halo+1
        if lo < 0 or hi > header["nchans"]:
            raise ValueError("Source does not contain prospective full halo/filter margin")
        power = np.array(raw[:,0,lo:hi], dtype=np.float64)
        local = selected-lo
        grid = drift_grid(df_hz, times[-1], c["max_drift_hz_s"])
        mid_mjd = header["tstart"] + (0.5*header["tsamp"])/86400.0
        coverage = {"n_source_values_checked":int(raw.size),"n_reference_channels":int(selected.size),
                    "n_rows":nrow, "decoded_first_channel":lo,"decoded_exclusive_last_channel":hi,
                    "search_first_channel":int(selected[0]),"search_last_channel":int(selected[-1]),
                    "search_mhz_channel_centers":[float(freqs[selected].min()),float(freqs[selected].max())],
                    "decoded_mhz_channel_centers":[float(freqs[lo:hi].min()),float(freqs[lo:hi].max())],
                    "df_hz_signed":df_hz,"tsamp_s":header["tsamp"],"first_to_last_midpoint_s":float(times[-1]),
                    "reference_midpoint_mjd":mid_mjd,"time_reference":"first integration midpoint",
                    "drift_grid_count":int(grid.size),"drift_step_hz_s":float(grid[1]-grid[0]),
                    "max_half_step_displacement_channels":float((grid[1]-grid[0])*times[-1]/(2*abs(df_hz))),
                    "halo_channels_each_side":halo,"complete_track_coverage":True}
        write_json(a.output / "coverage.json", coverage)
        say(f"Authentic power values loaded: {nrow} rows, {selected.size} search channels, full halo")
        # These visual outputs precede detection computation or acceptance judgment.
        fig, ax = plt.subplots(figsize=(10,4), constrained_layout=True)
        ax.plot(freqs[selected], 10*np.log10(np.maximum(power[:,local].mean(axis=0), np.finfo(float).tiny)), linewidth=.7)
        ax.set(xlabel="Frequency (MHz)",ylabel="Mean power (arbitrary dB)",title="GBT Voyager 1: known engineering reference, declared 80 kHz band")
        fig.savefig(a.output/"reference_spectrum.png",dpi=150); plt.close(fig)
        cp = np.flatnonzero((freqs[lo:hi] >= c["carrier_plot_mhz"][0]) & (freqs[lo:hi] <= c["carrier_plot_mhz"][1]))
        x = freqs[lo:hi][cp]
        image = 10*np.log10(np.maximum(power[:,cp],np.finfo(float).tiny))
        if df_hz < 0:
            x=x[::-1]; image=image[:,::-1]
        fig, ax = plt.subplots(figsize=(8,5),constrained_layout=True)
        mesh=ax.imshow(image,origin="lower",aspect="auto",extent=[x[0]-abs(header["foff"])/2,x[-1]+abs(header["foff"])/2,-header["tsamp"]/2,times[-1]+header["tsamp"]/2],cmap="viridis",vmin=np.percentile(image,5),vmax=np.percentile(image,99.8))
        ax.ticklabel_format(useOffset=False,axis="x")
        ax.set(xlabel="Frequency (MHz)",ylabel="Time since first integration midpoint (s)",title="Known Voyager carrier: telescope reference, not a SETI candidate")
        fig.colorbar(mesh,ax=ax,label="Power (arbitrary dB)")
        fig.savefig(a.output/"reference_waterfall.png",dpi=150); plt.close(fig)
        say("Spectrum and carrier waterfall saved before detection/judgment")
        row_median = np.median(power,axis=1)
        if (row_median <= 0).any():
            raise ValueError("Nonpositive row median")
        normalized = power/row_median[:,None]
        residual = normalized - median_filter(normalized,size=(1,c["running_median_channels"]),mode="nearest")
        center = np.median(residual[:,local],axis=1)
        scale=1.4826*np.median(np.abs(residual[:,local]-center[:,None]),axis=1)
        if (scale <= 0).any() or not np.isfinite(scale).all():
            raise ValueError("Invalid empirical residual scale")
        # Contract subtracts running median only; center used to estimate MAD, not a further subtraction.
        z=residual/scale[:,None]
        search_start=time.monotonic()
        score, drift=scan(z,times,df_hz,local,grid)
        search_seconds=time.monotonic()-search_start
        if not np.isfinite(score).all():
            raise ValueError("Nonfinite search output")
        np.savez_compressed(a.output/"all_search_channels.npz",source_channel=selected,frequency_mhz=freqs[selected],max_robust_track_score=score,best_drift_hz_s=drift,drift_grid_hz_s=grid)
        hit=np.flatnonzero(score>=c["threshold_robust_track_score"])
        columns=["source_channel","reference_frequency_mhz","best_drift_hz_s","robust_track_score"]
        with (a.output/"all_threshold_channels.csv").open("w",newline="") as f:
            w=csv.writer(f); w.writerow(columns)
            for j in hit:
                w.writerow([int(selected[j]),f"{freqs[selected[j]]:.12f}",f"{drift[j]:.12f}",f"{score[j]:.9f}"])
        peak=np.flatnonzero((score>=c["threshold_robust_track_score"]) & (score==maximum_filter1d(score,size=17,mode="nearest")))
        with (a.output/"representative_frequency_peaks.csv").open("w",newline="") as f:
            w=csv.writer(f); w.writerow(columns)
            for j in peak:
                w.writerow([int(selected[j]),f"{freqs[selected[j]]:.12f}",f"{drift[j]:.12f}",f"{score[j]:.9f}"])
        top=np.argsort(score)[::-1][:10]
        carrier_hit = hit[(freqs[selected[hit]] >= c["carrier_plot_mhz"][0]) & (freqs[selected[hit]] <= c["carrier_plot_mhz"][1])]
        carrier_demonstrated = bool(carrier_hit.size)
        summary={"role":c["role"],"status":"REFERENCE_ANALYSIS_COMPLETE","threshold_channel_count":int(hit.size),
                 "known_carrier_demonstrated":carrier_demonstrated,"carrier_band_threshold_channel_count":int(carrier_hit.size),
                 "representative_peak_count":int(peak.size),"search_only_wall_s":search_seconds,
                 "threshold":c["threshold_robust_track_score"],"score_definition":"row-MAD-standardized nearest-channel sum/sqrt(N); not turboSETI SNR or calibrated significance",
                 "top_10_channels":[{"channel":int(selected[j]),"frequency_mhz":float(freqs[selected[j]]),"drift_hz_s":float(drift[j]),"score":float(score[j])} for j in top],
                 "single_reference_scan_no_on_off":True,"sky_candidates_claimed":0,"old_failed_ci_disposition":"FAILED_CLOSED"}
        write_json(a.output/"summary.json",summary)
        say(f"Search complete; retained all {hit.size} threshold channels and {peak.size} representative maxima")
        if not carrier_demonstrated:
            raise ValueError("Known-carrier threshold/localization gate failed; computational outputs retained")
        status="REFERENCE_CARRIER_DEMONSTRATED" if carrier_demonstrated else "REFERENCE_COMPLETE_CARRIER_GATE_FAILED"
    except Exception as e:
        say(f"FAILED_CLOSED: {type(e).__name__}: {e}")
        write_json(a.output/"failure.json",{"type":type(e).__name__,"message":str(e),"status":"FAILED_CLOSED"})
        raise
    finally:
        r=resource.getrusage(resource.RUSAGE_SELF)
        wall=time.monotonic()-wall_start
        peak_bytes=int(r.ru_maxrss)*1024 # Linux ru_maxrss is KiB.
        budget_pass=wall<=c["max_wall_seconds"] and peak_bytes<=c["max_rss_bytes"]
        receipt={"status":status if budget_pass else "BUDGET_FAILED_CLOSED","total_wall_s":wall,
                 "process_cpu_s":time.process_time()-cpu_start,"peak_rss_bytes":peak_bytes,
                 "resource_method":"Linux getrusage(RUSAGE_SELF); process-only CPU and peak RSS",
                 "wall_budget_s":c["max_wall_seconds"],"rss_budget_bytes":c["max_rss_bytes"],"budget_pass":budget_pass}
        write_json(a.output/"resource_receipt.json",receipt)
        if not budget_pass:
            raise RuntimeError("Resource budget exceeded; failed closed")

if __name__ == "__main__":
    main()
