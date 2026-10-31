"""Package closed BW evidence and exact dependencies without new science."""
from pathlib import Path
import hashlib, json, shutil, zipfile
ROOT=Path(__file__).resolve().parents[1]; BW=ROOT/'work_bw'
def read(p): return json.loads(Path(p).read_text())
def sha(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
summary=read(BW/'SUMMARY_BW.json')
binding=read(BW/'review/SUMMARY_BINDING_REVIEW_BW.json')
assert binding['status']=='PASS_SUMMARY_MATCHES_INDEPENDENT_CLOSURE'
assert binding['summary_sha256']==sha(BW/'SUMMARY_BW.json')
dest=BW/'delivery';dest.mkdir(exist_ok=False)
source=Path(summary['closed_archive']['path'])
assert source.stat().st_size==summary['closed_archive']['bytes'] and sha(source)==summary['closed_archive']['sha256']
target=dest/'SETI_BW_PARTIAL_Q254_2026-10-31.zip';shutil.copyfile(source,target)
assert target.stat().st_size==source.stat().st_size and sha(target)==sha(source)
artifacts=[dict(local_path=str(target),file_name=target.name,bytes=target.stat().st_size,sha256=sha(target),kind='closed_search_batch',q_list=[254])]
paths={str(p.relative_to(ROOT)):p for p in BW.rglob('*') if p.is_file() and 'delivery' not in p.parts and '__pycache__' not in p.parts and p.suffix in ('.json','.py','.md','.log')}
paths['RADIO_PROGRESS_BW_Q254_2026-10-31.md']=ROOT/'RADIO_PROGRESS_BW_Q254_2026-10-31.md'
plan=read(BW/'BW_PARTIAL_PLAN.json')
for name in plan['source_sha256']:
    p=Path(name);paths[str(p.relative_to(ROOT))]=p
for e in plan['metadata_evidence']:
    p=Path(e['path']);key=str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else 'retained_metadata/'+str(p.relative_to(ROOT.parent));paths[key]=p
for s in plan['scans']:
    p=Path(s['header_path']);paths['retained_metadata/'+str(p.relative_to(ROOT.parent))]=p
members=[dict(path=n,bytes=p.stat().st_size,sha256=sha(p)) for n,p in sorted(paths.items())]
meta=dest/'SETI_BW_METADATA_AND_RESUME_2026-10-31.zip'
with zipfile.ZipFile(meta,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for name,path in sorted(paths.items()):z.write(path,name)
    z.writestr('PACKAGE_INVENTORY_BW.json',json.dumps(dict(members=members,batch_archives=artifacts,raw_arrays_and_prior_results_retained_by_exact_parent_references=True),indent=2,sort_keys=True)+'\n')
with zipfile.ZipFile(meta) as z:
    assert z.testzip() is None
    for m in members:
        b=z.read(m['path']);assert len(b)==m['bytes'] and hashlib.sha256(b).hexdigest()==m['sha256'] and sha(paths[m['path']])==m['sha256']
artifacts.append(dict(local_path=str(meta),file_name=meta.name,bytes=meta.stat().st_size,sha256=sha(meta),kind='metadata_source_reviews_receipts_and_resume_spec',verified_members=len(members)+1))
result=dict(schema='SETI_BW_PERSISTENT_PACKAGE_REQUEST_V1',all_closed_archives_verified=True,summary_sha256=sha(BW/'SUMMARY_BW.json'),artifacts=artifacts)
(dest/'PACKAGE_BW.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result))
