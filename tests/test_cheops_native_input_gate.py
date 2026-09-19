import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts/cheops_native_input_gate.py"
DRAFT = ROOT / "config/cheops_native_study_draft.json"
CONTRACT = ROOT / "CHEOPS_REQUIRED_INPUTS.json"

def run(*args):
    return subprocess.run([sys.executable, str(GATE), *map(str,args)], text=True, capture_output=True)

def test_current_contract_is_blocked():
    p = run("--contract", CONTRACT, "--study", DRAFT)
    assert p.returncode != 0
    assert "NOT_READY: study protocol is not frozen" in (p.stdout + p.stderr)

def test_complete_synthetic_contract_passes(tmp_path):
    study = json.loads(DRAFT.read_text())
    study["state"] = "FROZEN"
    study["target_image_access_authorized"] = True
    study_path = tmp_path / "study.json"
    study_path.write_text(json.dumps(study))

    contract = json.loads(CONTRACT.read_text())
    contract["science_ready"] = True
    contract["new_external_input_received"] = True
    for q in contract["operator_questions"]:
        q["status"] = "VERIFIED"
    contract["already_available_gain"]["physical_convention_adopted"] = True

    root = tmp_path / "refs"
    root.mkdir()
    required = {
        "CH_TU2018-01-01T00-00-00_REF_APP_CCDLinearisationLUT100_V0104.fits",
        "CH_TU2020-01-29T00-00-00_REF_APP_FlatFieldTeff-PointSource_V0104.fits",
        "CH_TU2020-03-17T12-29-01_REF_APP_DarkFrame_V0201.fits",
        "CH_TU2020-03-17T12-29-01_REF_APP_BadPixelMap_V0201.fits",
    }
    for rec in contract["reference_inputs"]:
        if rec["filename"] not in required:
            continue
        data=("fixture:"+rec["filename"]).encode()
        (root/rec["filename"]).write_bytes(data)
        rec["contents_received"]=True
        rec["sha256"]=hashlib.sha256(data).hexdigest()
        rec["native_validity_start_utc"]="2020-01-01T00:00:00Z"
        rec["native_validity_stop_utc"]="2050-01-01T00:00:00Z"
        rec["version_relevant_selection_rule"]="synthetic test fixture only"
    contract_path=tmp_path/"contract.json"
    contract_path.write_text(json.dumps(contract))

    p=run("--contract",contract_path,"--study",study_path,"--reference-root",root)
    assert p.returncode==0, p.stdout+p.stderr
    assert p.stdout.startswith("READY:")
