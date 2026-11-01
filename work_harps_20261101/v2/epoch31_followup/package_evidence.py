"""Package numerical evidence; figures remain individual PNGs beside the archive."""
from pathlib import Path
import zipfile,hashlib,json
BASE=Path(__file__).resolve().parent.parent
for name,label in [('epoch64_followup','EPOCH64_EVIDENCE'),('epoch31_followup','EPOCH31_EVIDENCE')]:
 d=BASE/name;dest=d/(label+'.zip');members=[]
 for p in sorted(d.rglob('*')):
  if not p.is_file() or p.suffix in ['.zip','.png'] or p.name=='ARCHIVE_VERIFICATION.json' or '__pycache__' in p.parts:continue
  members.append((p,p.relative_to(d).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest()))
 with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p,arc,h in members:z.write(p,arc)
 with zipfile.ZipFile(dest) as z:
  assert z.testzip() is None
  for p,arc,h in members:assert hashlib.sha256(z.read(arc)).hexdigest()==h
 info={'archive':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'bytes':dest.stat().st_size,'members':len(members),'npz_profiles':sum(p.suffix=='.npz' for p,_,_ in members),'all_members_sha256_verified':True,'figures':'PNG figures excluded from archive and delivered as individual files.','file_hashes':{arc:h for p,arc,h in members}}
 (d/'ARCHIVE_VERIFICATION.json').write_text(json.dumps(info,indent=2)+'\n');print(name,{k:v for k,v in info.items() if k!='file_hashes'})
