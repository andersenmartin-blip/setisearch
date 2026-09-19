#!/usr/bin/env python3
"""Header-only validator for delivered CHEOPS reference FITS files.

The validator hashes whole files but reads FITS headers only. It does not read
science-image arrays and does not decide scientific applicability. It records
the native validity cards and basic structure needed by the hard input gate.
"""
import argparse, hashlib, json
from pathlib import Path

REQUIRED = {
    "CH_TU2018-01-01T00-00-00_REF_APP_CCDLinearisationLUT100_V0104.fits",
    "CH_TU2020-01-29T00-00-00_REF_APP_FlatFieldTeff-PointSource_V0104.fits",
    "CH_TU2020-03-17T12-29-01_REF_APP_DarkFrame_V0201.fits",
    "CH_TU2020-03-17T12-29-01_REF_APP_BadPixelMap_V0201.fits",
}

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--contract", required=True, type=Path)
    ap.add_argument("--reference-root", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args=ap.parse_args()

    from astropy.io import fits
    contract=json.loads(args.contract.read_text())
    refs={r["filename"]:r for r in contract.get("reference_inputs",[])}
    missing=REQUIRED-set(refs)
    if missing:
        raise SystemExit("contract missing definitions: "+", ".join(sorted(missing)))

    records=[]
    for name in sorted(REQUIRED):
        path=args.reference_root/name
        if not path.is_file():
            records.append({"filename":name,"status":"MISSING"})
            continue
        rec={"filename":name,"status":"PRESENT","bytes":path.stat().st_size,"sha256":sha256(path)}
        expected=refs[name].get("sha256")
        rec["contract_sha256"]=expected
        rec["sha256_matches_contract"]=(expected==rec["sha256"]) if expected else None
        hdus=[]
        with fits.open(path, mode="readonly", memmap=True, lazy_load_hdus=True,
                       do_not_scale_image_data=True) as h:
            for i,hdu in enumerate(h):
                hdr=hdu.header
                row={
                    "index":i,
                    "extname":hdr.get("EXTNAME"),
                    "extver":hdr.get("EXT_VER",hdr.get("EXTVER")),
                    "v_strt_u":hdr.get("V_STRT_U"),
                    "v_stop_u":hdr.get("V_STOP_U"),
                    "checksum":hdr.get("CHECKSUM"),
                    "datasum":hdr.get("DATASUM"),
                    "naxis":hdr.get("NAXIS"),
                    "shape":[hdr.get(f"NAXIS{k}") for k in range(1,int(hdr.get("NAXIS",0))+1)],
                    "bunit":hdr.get("BUNIT"),
                }
                hdus.append(row)
        rec["hdus"]=hdus
        starts=[x["v_strt_u"] for x in hdus if x["v_strt_u"] is not None]
        stops=[x["v_stop_u"] for x in hdus if x["v_stop_u"] is not None]
        rec["native_validity_start_candidates"]=starts
        rec["native_validity_stop_candidates"]=stops
        rec["has_native_validity_pair"]=bool(starts and stops)
        records.append(rec)

    out={
      "operation":"CHEOPS reference header-only inspection",
      "science_image_arrays_read":False,
      "required_reference_count":len(REQUIRED),
      "present_count":sum(r["status"]=="PRESENT" for r in records),
      "records":records,
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"present":out["present_count"],"required":len(REQUIRED),
                      "output":str(args.output)},indent=2))

if __name__=="__main__":
    main()
