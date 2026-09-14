#!/usr/bin/env python3
"""Independent raw-byte audit of LS7L table selections and PRF phase sums."""
import bisect
import csv
import hashlib
import json
import math
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT.parent/"ls7l-engineering-cache"
OUT=ROOT/"results_ls7l_inputs"
TYPES={"D":">f8","I":">i2"}

def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        while data:=stream.read(4*1024*1024):
            h.update(data)
    return h.hexdigest()

def raw_table(spec):
    fields=[]
    for f in spec["fields"]:
        assert f["TFORM"] in TYPES
        assert f["TSCAL"] is None and f["TZERO"] is None and f["TNULL"] is None
        fields.append((f["TTYPE"],TYPES[f["TFORM"]]))
    dtype=np.dtype(fields)
    assert dtype.itemsize==spec["row_bytes"]
    return np.memmap(CACHE/spec["source_name"],mode="r",dtype=dtype,
                     offset=spec["data_offset"],shape=(spec["source_rows"],))

def image_hdus(path):
    """Read only FITS structural cards, then decode original float64 bytes."""
    images=[]
    with path.open("rb") as stream:
        offset=0
        while offset<path.stat().st_size:
            stream.seek(offset)
            cards={}
            nbytes=0
            while True:
                block=stream.read(2880)
                assert len(block)==2880
                nbytes+=2880
                ended=False
                for k in range(0,2880,80):
                    card=block[k:k+80].decode("ascii")
                    key=card[:8].strip()
                    if key=="END":
                        ended=True;break
                    if key in ("BITPIX","NAXIS","NAXIS1","NAXIS2","PCOUNT","GCOUNT"):
                        cards[key]=int(card[10:].split("/")[0].strip())
                if ended:break
                assert nbytes<262144
            assert cards["BITPIX"]==-64 and cards["NAXIS"]==2
            assert cards.get("PCOUNT",0)==0 and cards.get("GCOUNT",1)==1
            shape=(cards["NAXIS2"],cards["NAXIS1"])
            count=math.prod(shape)
            raw=stream.read(count*8)
            assert len(raw)==count*8
            images.append(np.frombuffer(raw,dtype=">f8").reshape(shape))
            offset+=nbytes+((count*8+2879)//2880)*2880
        assert offset==path.stat().st_size
    return images

def verify_manifest(folder):
    count=0
    for line in (folder/"SHA256SUMS").read_text().splitlines():
        expected,name=line.split("  ",1)
        assert digest(folder/name)==expected
        count+=1
    return count

def main():
    config=json.loads((ROOT/"config/ls7l_engineering.json").read_text())
    summary=json.loads((OUT/"summary.json").read_text())
    tables=json.loads((OUT/"tables.json").read_text())
    assert summary["input_config_sha256"]==digest(ROOT/"config/ls7l_engineering.json")
    preserved=verify_manifest(ROOT/"results_ls7k_inputs")+verify_manifest(ROOT/"results_ls7l_engineering")
    for source in config["raw_sources"]:
        assert digest(CACHE/source["name"])==source["sha256"]
    coverage=list(csv.DictReader((OUT/"cadence_coverage.csv").open()))
    assert len(coverage)==8020
    by_cadence={(int(r["sector"]),int(r["cadence"])):r for r in coverage}
    assert len(by_cadence)==8020
    scalar_values=0
    table_audits=[]
    cadence_checks=0
    padding=config["padding_seconds"]/86400.
    for sector in config["sectors"]:
        intervals=[(lo-padding,hi+padding) for lo,hi in sector["context_ranges"]]
        for spec in sector["tables"]:
            raw=raw_table(spec)
            # Scalar row selection is independent of the producer's Boolean union.
            selected=[i for i,t in enumerate(raw["TIME"])
                      if any(lo<=t<=hi for lo,hi in intervals)]
            record=next(r for r in tables if r["sector"]==sector["sector"] and r["table"]==spec["hdu_name"])
            saved=np.load(OUT/record["file"],allow_pickle=False)
            np.testing.assert_array_equal(saved["source_row"],selected)
            assert record["selected_rows"]==len(selected)
            context=[]
            for i in selected:
                matches=[k for k,(lo,hi) in enumerate(intervals) if lo<=raw["TIME"][i]<=hi]
                assert len(matches)==1
                context.append(matches[0])
            np.testing.assert_array_equal(saved["context_index"],context)
            for field in spec["fields"]:
                name=field["TTYPE"]
                np.testing.assert_array_equal(saved[name],raw[name][selected])
                scalar_values+=len(selected)
            table_audits.append({"sector":sector["sector"],"table":spec["hdu_name"],
                                "rows":len(selected),"raw_scalar_values_pass":True})
            if spec["kind"]=="quat":
                timing=np.load(ROOT/"results_ls7k_inputs"/sector["timing_file"],allow_pickle=False)
                ts=sorted(float(raw["TIME"][i]) for i in selected)
                for cadence,t in zip(timing["cadence"].ravel(),timing["time_spacecraft_btjd"].ravel(),strict=True):
                    row=by_cadence[(sector["sector"],int(cadence))]
                    assert float(row["time_spacecraft_btjd"])==float(t)
                    count=bisect.bisect_left(ts,float(t)+10/86400)-bisect.bisect_left(ts,float(t)-10/86400)
                    assert count==int(row["quaternion_rows"])
                    cadence_checks+=1
    phase_rows=list(csv.DictReader((OUT/"prf_phase_accounting.csv").open()))
    assert len(phase_rows)==4050
    phase_map={(r["name"],int(r["row_residue"]),int(r["column_residue"])):r for r in phase_rows}
    inv=json.loads((ROOT/"results_ls7k_inputs/inventory.json").read_text())
    max_difference=0.
    raw_image_values=0
    for model in inv["prf_models"]:
        path=ROOT/"results_ls7k_inputs"/model["path"]
        assert digest(path)==model["sha256"]
        image,unc=image_hdus(path)
        assert image.shape==unc.shape==(117,117)
        assert np.isfinite(image).all() and np.isfinite(unc).all()
        raw_image_values+=image.size+unc.size
        for row in range(9):
            for col in range(9):
                saved=phase_map[(model["name"],row,col)]
                for array,key in ((image,"phase_sum"),(unc,"uncertainty_entry_sum")):
                    total=math.fsum(float(array[row+9*i,col+9*j]) for i in range(13) for j in range(13))
                    difference=abs(total-float(saved[key]))
                    max_difference=max(max_difference,difference)
                    assert difference<1e-12
    for doc in config["documentation"]:
        assert digest(OUT/"documentation"/doc["name"])==doc["sha256"]
    assert summary["quaternion_rows"]==sum(r["rows"] for r in table_audits if r["table"]=="CAMERA4")
    assert summary["thermal_rows"]==sum(r["rows"] for r in table_audits if r["table"]!="CAMERA4")
    result={"pass":True,"selected_scalar_values_checked":scalar_values,
        "cadence_counts_checked":cadence_checks,"raw_prf_uncertainty_values_checked":raw_image_values,
        "phase_sums_checked":8100,"maximum_phase_sum_discrepancy":max_difference,
        "preserved_manifest_entries":preserved,"tables":table_audits}
    (OUT/"AUDIT.json").write_text(json.dumps(result,indent=2)+"\n")
    lines=["# LS7L closed-context engineering and calibration inputs","",
        "**Input extraction and independent raw-byte audit completed.**","",
        f'The packet contains {summary["quaternion_rows"]:,} camera-4 quaternion rows and '
        f'{summary["thermal_rows"]:,} thermal rows from 26 fixed thermal channels across the two sectors.',
        f'All {summary["cadence_rows"]:,} saved cadence coverage counts and {summary["prf_phase_images"]:,} PRF phase images are accounted for.',"",
        "| Quantity | Result |","|---|---:|",
        f'| Saved cadences without quaternion rows in the fixed 20-second bin | {summary["cadences_without_quaternion_rows"]} |',
        f'| Quaternion rows per coverage bin, minimum / maximum | {summary["quaternion_count_range"][0]} / {summary["quaternion_count_range"][1]} |',
        f'| PRF phase flux sum, minimum / maximum | {summary["minimum_prf_phase_sum"]:.12g} / {summary["maximum_prf_phase_sum"]:.12g} |',
        f'| Raw selected scalar values verified | {scalar_values:,} |',
        f'| Raw PRF and uncertainty values decoded | {raw_image_values:,} |',"",
        "Read timing_metadata.json for all UTC/TT/TDB calendar comparisons and tables.json for missing values, quality ranges and sampling.",
        "The numeric join follows the mission support TESSVectors convention; absent TIMESYS/TIMEREF, exact exposure timing and estimator kernels remain explicit limits.",
        "Coverage counts are not exposure averages or proof of guide-star independence.",
        "Phase sums are finite-footprint bookkeeping; no phase image is renormalized and uncertainty-entry sums are not variances.",
        "The original mission README and MATLAB exporter are restored under documentation/ with their LS7K hashes.", "",
        "Next: inspect the exporter, fix absolute detector coordinates and source-phase orientation, then specify the physical response and uncertainty benchmark before native comparison.",
        "There is no detector adoption, added observing coverage, new candidate, or change to prior negative results.", ""]
    (OUT/"REPORT.md").write_text("\n".join(lines))
    print(json.dumps({k:v for k,v in result.items() if k!="tables"}),flush=True)

if __name__=="__main__":
    main()
