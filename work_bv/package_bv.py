"""Preserve closed BV search archives and all current metadata without recomputing science."""
from pathlib import Path
import hashlib,json,shutil,zipfile
ROOT=Path(__file__).resolve().parents[1]; BV=ROOT/'work_bv';dest=BV/'delivery'
def read(p):return json.loads(p.read_text())
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
dest.mkdir(exist_ok=False);summary=read(BV/'SUMMARY_BV.json');review=read(BV/'review/SUMMARY_BINDING_REVIEW_BV.json')
assert review['status']=='PASS_SUMMARY_MATCHES_INDEPENDENT_CLOSURE' and sha(BV/'SUMMARY_BV.json')==review['summary_sha256']
artifacts=[]
for b in summary['batches']:
    n=b['batch'];source=Path(b['archive_path']);target=dest/f'SETI_BV_PARTIAL_BATCH{n:02d}_2026-10-31.zip'
    assert source.stat().st_size==b['archive_bytes'] and sha(source)==b['archive_sha256'];shutil.copyfile(source,target)
    assert target.stat().st_size==b['archive_bytes'] and sha(target)==b['archive_sha256']
    artifacts.append(dict(local_path=str(target),file_name=target.name,bytes=target.stat().st_size,sha256=sha(target),kind='closed_search_batch',batch=n,q_list=b['q_list']))
paths={str(p.relative_to(ROOT)):p for p in BV.rglob('*') if p.is_file() and 'delivery' not in p.parts and '__pycache__' not in p.parts and p.suffix in ('.json','.py','.md','.log','.svg','.png')}
paths['RADIO_PROGRESS_BV_REMAINING_2026-10-31.md']=ROOT/'RADIO_PROGRESS_BV_REMAINING_2026-10-31.md'
plan=read(BV/'BV_PARTIAL_PLAN.json')
for value in plan['source_sha256']:
    p=Path(value);paths[str(p.relative_to(ROOT))]=p
for e in plan['metadata_evidence']:
    p=Path(e['path']);key=str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else 'retained_metadata/'+str(p.relative_to(ROOT.parent));paths[key]=p
for s in plan['scans']:
    p=Path(s['header_path']);paths['retained_metadata/'+str(p.relative_to(ROOT.parent))]=p
for name in ['work_bu/DELIVERY_BU.json','work_bu/provenance/INPUT_LINEAGE_BU.json']:
    paths[name]=ROOT/name
members=[dict(path=n,bytes=p.stat().st_size,sha256=sha(p)) for n,p in sorted(paths.items())]
meta=dest/'SETI_BV_PARTIAL_METADATA_2026-10-31.zip'
with zipfile.ZipFile(meta,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for n,p in sorted(paths.items()):z.write(p,n)
    z.writestr('PACKAGE_INVENTORY_BV.json',json.dumps(dict(members=members,batch_archives=artifacts,raw_arrays_and_BU_result_archives_retained_by_exact_parent_references=True),indent=2,sort_keys=True)+'\n')
with zipfile.ZipFile(meta) as z:
    assert z.testzip() is None
    for m in members:
        b=z.read(m['path']);assert len(b)==m['bytes'] and hashlib.sha256(b).hexdigest()==m['sha256'];assert sha(paths[m['path']])==m['sha256']
artifacts.append(dict(local_path=str(meta),file_name=meta.name,bytes=meta.stat().st_size,sha256=sha(meta),kind='metadata_source_reviews_diagnostics_and_receipts',verified_members=len(members)+1))
request=dict(schema='SETI_BV_PERSISTENT_PACKAGE_REQUEST_V1',all_closed_archives_verified=True,summary_sha256=sha(BV/'SUMMARY_BV.json'),artifacts=artifacts)
(dest/'PACKAGE_BV.json').write_text(json.dumps(request,indent=2,sort_keys=True)+'\n')
print(json.dumps(request))
