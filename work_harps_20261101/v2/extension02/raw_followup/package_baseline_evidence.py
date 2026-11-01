"""Package stable baseline only; source binaries and evolving follow-up remain separate."""
from pathlib import Path
import json,hashlib,zipfile,datetime
from common import verify_freeze
O=Path(__file__).resolve().parent;verify_freeze();out=O/'RAW_BASELINE_EVIDENCE.zip';manifest=O/'RAW_BASELINE_EVIDENCE_MANIFEST.json'
assert not out.exists()and not manifest.exists(),'Baseline archive must not be silently replaced'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=[];external=[]
for p in sorted(O.rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(O)
 if '__pycache__'in rel.parts or rel.parts[0]=='mapping_followup':continue
 if p.suffix.lower()=='.png':external.append(dict(path=str(rel),bytes=p.stat().st_size,sha256=sha(p)));continue
 if p.suffix.lower()=='.zip'or p.name.endswith('.part'):continue
 if rel.parts[0]=='products'and p.suffix.lower()!='.json':continue
 files.append(p)
rows=[dict(path=str(p.relative_to(O)),bytes=p.stat().st_size,sha256=sha(p))for p in files]
assert sum(r['path'].startswith('native/')and r['path'].endswith('.npz')for r in rows)==86
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED)as z:
 for p in files:z.write(p,str(p.relative_to(O)))
with zipfile.ZipFile(out)as z:
 assert z.testzip()is None
 for r in rows:assert hashlib.sha256(z.read(r['path'])).hexdigest()==r['sha256']
for r in rows:assert sha(O/r['path'])==r['sha256'],'Source changed during packaging '+r['path']
m=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),archive=out.name,archive_bytes=out.stat().st_size,archive_sha256=sha(out),members=rows,external_individual_figures=external,crc_and_all_member_sha256_verified=True,native_npz_members=86,excluded=['evolving mapping_followup directory','raw/TAR source binaries in separate verified input checkpoints','three preserved partial-prefix binaries in separate non-science checkpoints','PNG pages delivered individually'],baseline_original_catalogs_unchanged=True)
manifest.write_text(json.dumps(m,indent=2)+'\n');print({k:v for k,v in m.items()if k not in ['members','external_individual_figures']});print('MEMBERS',len(rows),'EXTERNAL_PNG',len(external))
