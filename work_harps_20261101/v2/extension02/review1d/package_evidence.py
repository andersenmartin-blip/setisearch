from pathlib import Path
import zipfile,hashlib,json
O=Path(__file__).resolve().parent;archive=O/'EXTENSION02_REVIEW1D_EVIDENCE.zip'
files=[p for p in sorted(O.rglob('*')) if p.is_file() and p.suffix not in ['.zip','.png','.pyc'] and p.name!='ARCHIVE_VERIFICATION.json' and '__pycache__' not in p.parts]
hashes={p.relative_to(O).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in files:z.write(p,p.relative_to(O).as_posix())
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for member,h in hashes.items():assert hashlib.sha256(z.read(member)).hexdigest()==h
info={'archive':archive.name,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'bytes':archive.stat().st_size,'members':len(files),'npz_profiles':sum(p.suffix=='.npz' for p in files),'all_member_hashes_verified':True,'figures':'All 42 PNG atlas pages are separate files, excluded from this numerical evidence archive.','file_hashes':hashes}
(O/'ARCHIVE_VERIFICATION.json').write_text(json.dumps(info,indent=2)+'\n');print(json.dumps({k:v for k,v in info.items() if k!='file_hashes'}))
