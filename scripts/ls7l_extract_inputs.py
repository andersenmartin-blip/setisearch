#!/usr/bin/env python3
"""Frozen LS7L engineering selections and calibration-array accounting."""
from contextlib import ExitStack
import csv
import hashlib
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
import numpy as np
from astropy.io import fits
from astropy.time import Time
from astropy.utils import iers

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT.parent / "ls7l-engineering-cache"
OUT = ROOT / "results_ls7l_inputs"
CONFIG = ROOT / "config/ls7l_engineering.json"
iers.conf.auto_download = False

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(4*1024*1024):
            h.update(block)
    return h.hexdigest()

def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")

def selected_indices(times, intervals, padding):
    mask = np.zeros(len(times), dtype=bool)
    for lo, hi in intervals:
        mask |= (times >= lo-padding) & (times <= hi+padding)
    return np.flatnonzero(mask)

def describe(values):
    values = np.asarray(values)
    good = values[np.isfinite(values)]
    return {"rows": int(values.size), "finite": int(good.size),
            "minimum": float(np.min(good)) if good.size else None,
            "maximum": float(np.max(good)) if good.size else None}

def ensure_sources(config):
    CACHE.mkdir(exist_ok=True)
    for source in config["raw_sources"]:
        path = CACHE / source["name"]
        if not path.exists():
            partial = path.with_suffix(".partial")
            with urlopen(Request(source["url"]), timeout=30) as response, partial.open("wb") as out:
                assert response.status == 200
                assert int(response.headers["Content-Length"]) == source["bytes"]
                total = 0
                while block := response.read(4*1024*1024):
                    total += len(block)
                    assert total <= source["bytes"]
                    out.write(block)
                assert total == source["bytes"]
            partial.replace(path)
        assert path.stat().st_size == source["bytes"]
        assert digest(path) == source["sha256"]

def utc_comparisons(header):
    pairs = []
    for key, date_key in (("TSTART", "DATE-OBS"), ("TSTOP", "DATE-END")):
        if key not in header or date_key not in header:
            continue
        date = Time(header[date_key].rstrip("Z"), format="isot", scale="utc")
        differences = {}
        for scale in ("utc", "tt", "tdb"):
            stamp = Time(2457000.0, float(header[key]), format="jd", scale=scale)
            differences[scale] = float((stamp-date).to_value("sec"))
        pairs.append({"numeric_key": key, "numeric": header[key], "date_key": date_key,
                      "date": header[date_key], "numeric_minus_calendar_seconds": differences})
    return pairs

def main():
    config = json.loads(CONFIG.read_text())
    assert not OUT.exists(), "refuse to overwrite an earlier input result"
    # Boundary, duplicate, NaN and unsorted-time known answers.
    probe = np.array([3., 1., 2., 2., np.nan, 4.])
    assert selected_indices(probe, [(1., 3.)], 0).tolist() == [0,1,2,3]
    assert selected_indices(probe, [(1.5, 2.5)], .5).tolist() == [0,1,2,3]
    ensure_sources(config)
    OUT.mkdir()
    (OUT / "arrays").mkdir()
    (OUT / "documentation").mkdir()
    padding = config["padding_seconds"] / 86400.0
    table_records, cadence_rows, time_records = [], [], []
    with ExitStack() as stack:
        opened = {s["name"]: stack.enter_context(fits.open(CACHE/s["name"], memmap=True))
                  for s in config["raw_sources"]}
        for sector in config["sectors"]:
            timing = np.load(ROOT/"results_ls7k_inputs"/sector["timing_file"], allow_pickle=False)
            cadences = timing["cadence"].reshape(10,401)
            centers = timing["time_spacecraft_btjd"].reshape(10,401)
            assert np.all(np.isfinite(centers))
            intervals = sector["context_ranges"]
            assert all(intervals[i][1]+padding < intervals[i+1][0]-padding for i in range(9))
            np.testing.assert_array_equal(centers[:,[0,-1]], np.asarray(intervals))
            for spec in sector["tables"]:
                hdu = opened[spec["source_name"]][spec["hdu_index"]]
                assert hdu.name == spec["hdu_name"]
                assert hdu.columns.names == [f["TTYPE"] for f in spec["fields"]]
                all_time = np.asarray(hdu.data["TIME"])
                indices = selected_indices(all_time, intervals, padding)
                values = {name: np.array(hdu.data[name][indices]) for name in hdu.columns.names}
                contexts = np.full(indices.size, -1, dtype=np.int16)
                for k,(lo,hi) in enumerate(intervals):
                    mask = (values["TIME"] >= lo-padding) & (values["TIME"] <= hi+padding)
                    contexts[mask] = k
                assert np.all(contexts >= 0)
                filename = f'arrays/s{sector["sector"]:03d}_{spec["hdu_index"]:03d}.npz'
                np.savez_compressed(OUT/filename, source_row=indices, context_index=contexts, **values)
                record = {"sector":sector["sector"], "kind":spec["kind"], "table":spec["hdu_name"],
                    "file":filename, "selected_rows":int(indices.size),
                    "source_nonfinite_time_rows":int(np.sum(~np.isfinite(all_time))),
                    "fields":{name:describe(value) for name,value in values.items()},
                    "contexts":[]}
                for k in range(10):
                    t = values["TIME"][contexts == k]
                    delta = np.diff(t)*86400
                    record["contexts"].append({"context":k, "rows":int(t.size),
                        "duplicates":int(np.sum(delta == 0)), "decreasing_steps":int(np.sum(delta < 0)),
                        "median_spacing_seconds":float(np.median(delta)) if delta.size else None,
                        "max_spacing_seconds":float(np.max(delta)) if delta.size else None})
                table_records.append(record)
                if spec["kind"] == "quat":
                    time_records.append({"sector":sector["sector"],"table":hdu.name,
                        "TIME_unit":hdu.columns["TIME"].unit,
                        "TIMESYS":hdu.header.get("TIMESYS"),"TIMEREF":hdu.header.get("TIMEREF"),
                        "calendar_checks":utc_comparisons(hdu.header)})
                    for k in range(10):
                        m = contexts == k
                        t = values["TIME"][m]
                        for cadence,center in zip(cadences[k],centers[k],strict=True):
                            in_bin = (t >= center-10/86400) & (t < center+10/86400)
                            fom = describe(values["C4_FOM"][m][in_bin])
                            guides = describe(values["C4_NUM_GSUSED"][m][in_bin])
                            cadence_rows.append({"sector":sector["sector"],"context":k,
                                "cadence":int(cadence),"time_spacecraft_btjd":float(center),
                                "quaternion_rows":int(in_bin.sum()),
                                "finite_fom_rows":fom["finite"],"minimum_fom":fom["minimum"],
                                "finite_guide_count_rows":guides["finite"],
                                "minimum_guides_used":guides["minimum"]})
                elif spec == sector["tables"][0]:
                    time_records.append({"sector":sector["sector"],"table":hdu.name,
                        "TIME_unit":hdu.columns["TIME"].unit,
                        "TIMESYS":hdu.header.get("TIMESYS"),"TIMEREF":hdu.header.get("TIMEREF"),
                        "calendar_checks":utc_comparisons(hdu.header)})
    with (OUT/"cadence_coverage.csv").open("w",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(cadence_rows[0]))
        writer.writeheader(); writer.writerows(cadence_rows)
    phase_rows, phase_summary = [], []
    inv=json.loads((ROOT/"results_ls7k_inputs/inventory.json").read_text())
    for model in inv["prf_models"]:
        path=ROOT/"results_ls7k_inputs"/model["path"]
        assert digest(path)==model["sha256"]
        with fits.open(path,memmap=True) as hdus:
            image,unc=hdus[0].data,hdus[1].data
            assert image.shape==unc.shape==(117,117)
            sums=[]
            for row in range(9):
                for col in range(9):
                    flux=float(np.sum(image[row::9,col::9]))
                    sums.append(flux)
                    phase_rows.append({"name":model["name"],"camera":model["camera"],"ccd":model["ccd"],
                        "grid_row":model["grid_row"],"grid_col":model["grid_col"],
                        "row_residue":row,"column_residue":col,"phase_sum":flux,
                        "uncertainty_entry_sum":float(np.sum(unc[row::9,col::9]))})
            assert abs(sum(sums)-float(np.sum(image)))<1e-10
            phase_summary.append({"name":model["name"],"ccd":model["ccd"],
                "minimum_phase_sum":min(sums),"maximum_phase_sum":max(sums),
                "complete_array_sum":float(np.sum(image))})
    with (OUT/"prf_phase_accounting.csv").open("w",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(phase_rows[0]))
        writer.writeheader();writer.writerows(phase_rows)
    for doc in config["documentation"]:
        with urlopen(Request(doc["url"]),timeout=30) as response:
            assert response.status==200
            raw=response.read(65537)
        assert len(raw)==doc["bytes"]
        assert hashlib.sha256(raw).hexdigest()==doc["sha256"]
        (OUT/"documentation"/doc["name"]).write_bytes(raw)
    summary={"study":config["study"],"source_commit":os.environ.get("GITHUB_SHA"),
        "source_manifest_commit":config["schema_commit"],"input_config_sha256":digest(CONFIG),
        "context_count":20,"cadence_rows":len(cadence_rows),
        "quaternion_rows":sum(r["selected_rows"] for r in table_records if r["kind"]=="quat"),
        "thermal_rows":sum(r["selected_rows"] for r in table_records if r["kind"]=="eng"),
        "selected_tables":len(table_records),"prf_phase_images":len(phase_rows),
        "minimum_prf_phase_sum":min(r["phase_sum"] for r in phase_rows),
        "maximum_prf_phase_sum":max(r["phase_sum"] for r in phase_rows),
        "cadences_without_quaternion_rows":sum(r["quaternion_rows"]==0 for r in cadence_rows),
        "quaternion_count_range":[min(r["quaternion_rows"] for r in cadence_rows),
                                  max(r["quaternion_rows"] for r in cadence_rows)],
        "exact_engineering_time_reference_established":False,
        "upstream_target_exclusion_established":False,
        "native_response_comparisons":0,"new_detector_decisions":0,"added_observing_days":0}
    dump(OUT/"summary.json",summary)
    dump(OUT/"tables.json",table_records)
    dump(OUT/"timing_metadata.json",time_records)
    dump(OUT/"prf_summary.json",phase_summary)
    print(json.dumps(summary),flush=True)

if __name__=="__main__":
    main()
