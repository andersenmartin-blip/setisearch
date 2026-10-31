"""Seal already closed BZ results and exact dependencies without numerical replay."""
from pathlib import Path
import hashlib, importlib.util, json, shutil, sys
ROOT=Path(__file__).resolve().parents[1];HERE=ROOT/'work_bz'
STAGE=Path('/dev/shm/seti_bz_delivery_20261031');DEST=ROOT.parent/'bz_delivery'
NAME='SETI_FORTSAETTELSE_BZ_2026-10-31_EVIDENCE.zip'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    review=json.loads((HERE/'FINAL_BINDING_REVIEW_BZ.json').read_text())
    assert review['status']=='PASS_FINAL_BZ_REPORT_AND_BINDING'
    for name,digest in review['bound_sha256'].items():assert sha(name)==digest
    plan=json.loads((HERE/'PLAN_BZ.json').read_text())
    STAGE.mkdir(exist_ok=False);contents=STAGE/'contents';contents.mkdir()
    paths=[ROOT/'RADIO_PROGRESS_BZ_DRIFT_GRID_2026-10-31.md',
           ROOT/'work_bt/isolated_worker.py',ROOT/'work_bo/vendor/current/kernel_v.py',
           ROOT/'work_bu/partial_search.py',ROOT/'work_by/inject_recover.py',
           ROOT/'work_by/review_injection.py',ROOT/'work_bw/recovery/RESUME_SPEC_BW.json']
    paths += [Path(item['path']) for item in plan['inputs']]
    paths += [p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts
        and p.name not in ('DELIVERY_BZ.json','PACKAGE_RECEIPT_BZ.json','MAIN_README_BEFORE_BZ.md')]
    for p in sorted(set(paths)):
        assert not p.is_symlink();before=sha(p);target=contents/p.relative_to(ROOT)
        target.parent.mkdir(parents=True,exist_ok=True)
        with p.open('rb') as src,target.open('xb') as dst:shutil.copyfileobj(src,dst)
        assert before==sha(p)==sha(target)
    spec=importlib.util.spec_from_file_location('bz_package',ROOT/'work_bt/isolated_worker.py')
    helper=importlib.util.module_from_spec(spec);sys.modules[spec.name]=helper;spec.loader.exec_module(helper)
    receipt=helper.create_archive(contents,STAGE/NAME);DEST.mkdir(exist_ok=True)
    exported=helper.export_archive(STAGE/NAME,DEST/NAME,receipt)
    result=dict(schema='SETI_BZ_PACKAGE_V1',status='PASS',local_path=str(DEST/NAME),archive=exported,
        scientific_runs_repeated=False,closed_production_and_audit_archives_included=True)
    with (HERE/'PACKAGE_RECEIPT_BZ.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({'status':'PASS','path':str(DEST/NAME),'bytes':exported['bytes'],
        'sha256':exported['sha256'],'members':len(exported['members'])}))
if __name__=='__main__':main()
