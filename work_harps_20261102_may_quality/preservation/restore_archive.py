"""Restore committed exact evidence parts; refuse differing files and unsafe paths."""
import argparse,hashlib,io,json,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
ALLOWED=('acquisition/products/','comparison/results/profiles/')
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('manifest',choices=['SCIENCE_INPUTS_MANIFEST.json','PROFILE_EVIDENCE_MANIFEST.json']);ap.add_argument('--verify-only',action='store_true');a=ap.parse_args()
 m=json.loads((HERE/a.manifest).read_bytes());chunks=[]
 for part in m['parts']:
  p=(HERE/part['path']).resolve();assert p.is_relative_to(HERE) and not p.is_symlink();data=p.read_bytes()
  assert len(data)==part['bytes'] and sha(data)==part['sha256'];chunks.append(data)
 data=b''.join(chunks);assert len(data)==m['bytes'] and sha(data)==m['sha256'];expected={x['path']:x for x in m['members']};pending=[]
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  assert len(z.namelist())==len(expected) and set(z.namelist())==set(expected)
  for name,x in expected.items():
   dest=ROOT/name;assert name.startswith(ALLOWED) and not dest.is_symlink() and dest.resolve().is_relative_to(ROOT)
   raw=z.read(name);assert len(raw)==x['bytes'] and sha(raw)==x['sha256']
   if dest.exists() and dest.read_bytes()!=raw:raise FileExistsError('Preserve differing existing file: '+name)
   pending.append((dest,raw))
 if not a.verify_only:
  for dest,raw in pending:
   dest.parent.mkdir(parents=True,exist_ok=True)
   if not dest.exists():
    with dest.open('xb') as f:f.write(raw)
 print(json.dumps({'status':'PASS_EXACT_ARCHIVE_AND_MEMBERS','manifest':a.manifest,'members':len(expected),'parts':len(chunks),'sha256':m['sha256'],'mode':'verify_only' if a.verify_only else 'restore'}))
if __name__=='__main__':main()
