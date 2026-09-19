import json, subprocess, sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts/cheops_reference_header_validate.py"

def make_ref(path,start="2020-01-01T00:00:00",stop="2050-01-01T00:00:00"):
    from astropy.io import fits
    p=fits.PrimaryHDU()
    h=fits.ImageHDU(data=None,name="REFERENCE")
    h.header["V_STRT_U"]=start
    h.header["V_STOP_U"]=stop
    fits.HDUList([p,h]).writeto(path,checksum=True)

def test_header_only_inventory(tmp_path):
    names=[
      "CH_TU2018-01-01T00-00-00_REF_APP_CCDLinearisationLUT100_V0104.fits",
      "CH_TU2020-01-29T00-00-00_REF_APP_FlatFieldTeff-PointSource_V0104.fits",
      "CH_TU2020-03-17T12-29-01_REF_APP_DarkFrame_V0201.fits",
      "CH_TU2020-03-17T12-29-01_REF_APP_BadPixelMap_V0201.fits",
    ]
    refroot=tmp_path/"refs"; refroot.mkdir()
    for n in names: make_ref(refroot/n)
    contract={"reference_inputs":[{"filename":n,"sha256":None} for n in names]}
    cp=tmp_path/"contract.json"; cp.write_text(json.dumps(contract))
    op=tmp_path/"out.json"
    p=subprocess.run([sys.executable,str(SCRIPT),"--contract",str(cp),
        "--reference-root",str(refroot),"--output",str(op)],capture_output=True,text=True)
    assert p.returncode==0,p.stdout+p.stderr
    data=json.loads(op.read_text())
    assert data["science_image_arrays_read"] is False
    assert data["present_count"]==4
    assert all(r["has_native_validity_pair"] for r in data["records"])
    assert all(r["sha256_matches_contract"] is None for r in data["records"])

def test_missing_files_are_recorded(tmp_path):
    names=[
      "CH_TU2018-01-01T00-00-00_REF_APP_CCDLinearisationLUT100_V0104.fits",
      "CH_TU2020-01-29T00-00-00_REF_APP_FlatFieldTeff-PointSource_V0104.fits",
      "CH_TU2020-03-17T12-29-01_REF_APP_DarkFrame_V0201.fits",
      "CH_TU2020-03-17T12-29-01_REF_APP_BadPixelMap_V0201.fits",
    ]
    contract={"reference_inputs":[{"filename":n,"sha256":None} for n in names]}
    cp=tmp_path/"contract.json"; cp.write_text(json.dumps(contract))
    rr=tmp_path/"refs"; rr.mkdir()
    op=tmp_path/"out.json"
    p=subprocess.run([sys.executable,str(SCRIPT),"--contract",str(cp),
        "--reference-root",str(rr),"--output",str(op)],capture_output=True,text=True)
    assert p.returncode==0
    data=json.loads(op.read_text())
    assert data["present_count"]==0
    assert all(r["status"]=="MISSING" for r in data["records"])
