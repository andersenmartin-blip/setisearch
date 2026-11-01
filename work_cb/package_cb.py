"""Create self-contained closed CB evidence and continuation index."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'work_cb';OUT=ROOT.parent/'delivery'
OUT.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
s=json.loads((WORK/'FINAL_SUMMARY_CB.json').read_text())
for p,h in s['bound_files'].items():assert sha((ROOT/p).read_bytes())==h,p
claims=json.loads((WORK/'review/CLAIMS_REVIEW_CB.json').read_text());assert claims['status'].startswith('PASS')
files=[p for p in WORK.rglob('*') if p.is_file() and '__pycache__' not in str(p) and p.suffix!='.pyc']
files.append(ROOT/'RADIO_PROGRESS_CB_HIP35136_2026-11-01.md')
manifest={'schema':'SETI_CB_ARCHIVE_MANIFEST_V1','members':[{'path':str(p.relative_to(ROOT)),
 'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(files)]}
archive=OUT/'SETI_FORTSAETTELSE_CB_2026-11-01_EVIDENCE.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(files):z.write(p,str(p.relative_to(ROOT)))
 z.writestr('ARCHIVE_MANIFEST_CB.json',json.dumps(manifest,indent=2)+'\n')
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for r in manifest['members']:
  b=z.read(r['path']);assert len(b)==r['bytes'] and sha(b)==r['sha256'],r['path']
g=json.loads((WORK/'GITHUB_RECEIPT_CB.json').read_text())
index={'schema':'SETI_CB_DELIVERY_INDEX_V1','stage':'CB','status':s['status'],
 'checkpoint_closed':True,'parent_CA_index_library_file_id':'libfile_00ca405a38548191a6d04fc057765fb9',
 'artifacts':[{'filename':archive.name,'bytes':archive.stat().st_size,'sha256':sha(archive.read_bytes()),
  'verified_manifest_members':len(manifest['members']),'library_resolution':'Resolve by exact filename if not supplied in continuation context.'}],
 'github':g,'summary':s,'restore_path':'work_cb/RESTORE_CB.md','next_action':s['next_action'],
 'raw_original_stellar_file_included':True,'background_processes_running':False}
ip=OUT/'SETI_CB_DELIVERY_INDEX_2026-11-01.json';ip.write_text(json.dumps(index,indent=2)+'\n')
print(json.dumps({'archive':str(archive),'index':str(ip),'bytes':archive.stat().st_size,
 'sha256':sha(archive.read_bytes()),'members':len(manifest['members'])}))
