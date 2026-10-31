"""Package closed BU evidence; preserve the four prevalidated search ZIPs."""
from pathlib import Path
import json,hashlib,zipfile,shutil
ROOT=Path(__file__).resolve().parents[1]; BU=ROOT/'work_bu'; dest=BU/'delivery';dest.mkdir(exist_ok=False)
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(p.read_text())
artifacts=[]
for n in range(1,5):
    source=BU/f'execution/batch{n}/payload/EVIDENCE.zip'; target=dest/f'SETI_BU_PARTIAL_BATCH{n:02d}_2026-10-31.zip'
    expected=read(BU/f'execution/batch{n}/payload/RESULT.json')['archive'];assert sha(source)==expected['sha256'];shutil.copyfile(source,target);assert sha(target)==expected['sha256']
    artifacts.append(dict(local_path=str(target),file_name=target.name,bytes=target.stat().st_size,sha256=sha(target),kind='closed_search_batch',batch=n))
paths={str(p.relative_to(ROOT)):p for p in BU.rglob('*') if p.is_file() and 'delivery' not in p.parts and '__pycache__' not in p.parts and p.suffix in ('.json','.py','.md','.log')}
paths['RADIO_PROGRESS_BU_PARTIAL_2026-10-31.md']=ROOT/'RADIO_PROGRESS_BU_PARTIAL_2026-10-31.md'
plan=read(BU/'BU_PARTIAL_PLAN.json')
for value in plan['source_sha256']:
    p=Path(value);paths[str(p.relative_to(ROOT))]=p
for evidence in plan['metadata_evidence']:
    p=Path(evidence['path'])
    if not p.is_relative_to(ROOT):paths['retained_metadata/'+str(p.relative_to(ROOT.parent/'bu_restore'))]=p
for scan in plan['scans']:
    p=Path(scan['header_path']);paths['retained_metadata/'+str(p.relative_to(ROOT.parent/'bu_restore'))]=p
members=[dict(path=n,bytes=p.stat().st_size,sha256=sha(p)) for n,p in sorted(paths.items())]
meta=dest/'SETI_BU_PARTIAL_METADATA_2026-10-31.zip'
with zipfile.ZipFile(meta,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for n,p in sorted(paths.items()):z.write(p,n)
    z.writestr('PACKAGE_INVENTORY_BU.json',json.dumps(dict(members=members,batch_archives=artifacts,canonical_raw_arrays_retained_by_parent_references=True),indent=2,sort_keys=True)+'\n')
with zipfile.ZipFile(meta) as z:
    assert z.testzip() is None
    for m in members:
        b=z.read(m['path']);assert len(b)==m['bytes'] and hashlib.sha256(b).hexdigest()==m['sha256'];assert sha(paths[m['path']])==m['sha256']
artifacts.append(dict(local_path=str(meta),file_name=meta.name,bytes=meta.stat().st_size,sha256=sha(meta),kind='metadata_source_reviews_and_receipts',verified_members=len(members)+1))
manifest=dict(schema='SETI_BU_PERSISTENT_PACKAGE_REQUEST_V1',all_closed_archives_verified=True,artifacts=artifacts)
(dest/'PACKAGE_BU.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
print(json.dumps(manifest))
