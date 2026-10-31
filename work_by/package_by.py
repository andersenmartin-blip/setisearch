"""Seal all closed BY evidence, including the declared V2 identity extension."""
from pathlib import Path
import hashlib, importlib.util, json, shutil
ROOT=Path(__file__).resolve().parents[1];HERE=ROOT/'work_by'
STAGE=Path('/dev/shm/seti_by_delivery_20261031');DEST=ROOT.parent/'by_delivery'
NAME='SETI_FORTSAETTELSE_BY_2026-10-31_EVIDENCE.zip'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    review=json.loads((HERE/'FINAL_BINDING_REVIEW_BY.json').read_text())
    assert review['status']=='PASS_FINAL_BY_REPORT_AND_BINDING'
    for name,digest in review['bound_sha256'].items():assert sha(name)==digest
    STAGE.mkdir(exist_ok=False);contents=STAGE/'contents';contents.mkdir()
    paths=[ROOT/'RADIO_PROGRESS_BY_RFI_RECOVERY_2026-10-31.md',ROOT/'work_bt/isolated_worker.py',
           ROOT/'work_bo/vendor/current/kernel_v.py',ROOT/'work_bu/partial_search.py']
    paths += [p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts
              and p.name not in ('DELIVERY_BY.json','PACKAGE_RECEIPT_BY.json')]
    for p in paths:
        assert not p.is_symlink();before=sha(p);target=contents/p.relative_to(ROOT)
        target.parent.mkdir(parents=True,exist_ok=True)
        with p.open('rb') as src,target.open('xb') as dst:shutil.copyfileobj(src,dst)
        assert before==sha(p)==sha(target)
    spec=importlib.util.spec_from_file_location('by_package',ROOT/'work_bt/isolated_worker.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    receipt=helper.create_archive(contents,STAGE/NAME);DEST.mkdir(exist_ok=True)
    exported=helper.export_archive(STAGE/NAME,DEST/NAME,receipt)
    result={'schema':'SETI_BY_PACKAGE_V1','status':'PASS','local_path':str(DEST/NAME),'archive':exported,
            'scientific_runs_repeated':False,'all_closed_production_and_audit_archives_included':True}
    with (HERE/'PACKAGE_RECEIPT_BY.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({'status':'PASS','path':str(DEST/NAME),'bytes':exported['bytes'],
                      'sha256':exported['sha256'],'members':len(exported['members'])}))
if __name__=='__main__':main()
