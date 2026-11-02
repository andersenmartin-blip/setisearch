"""Reconstruct verified JSON evidence from ordered parts; never replace changed files."""
from pathlib import Path,PurePosixPath
import argparse,zipfile,json,hashlib,io
OUT=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def check_path(name):
 p=PurePosixPath(name)
 if p.is_absolute() or '..' in p.parts or '\\' in name:raise RuntimeError('Unsafe evidence path')
 dest=OUT/name
 for parent in [dest,*dest.parents]:
  if parent==OUT.parent:break
  if parent.is_symlink():raise RuntimeError('Symlink evidence destination')
 if not dest.resolve().is_relative_to(OUT.resolve()):raise RuntimeError('Evidence destination outside directory')
 return dest

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--verify-only',action='store_true');args=parser.parse_args()
 parts=json.loads((OUT/'EVIDENCE_PARTS.json').read_text());manifest=json.loads((OUT/'EVIDENCE_ARCHIVE.json').read_text())
 assert (parts['archive'],parts['bytes'],parts['sha256'])==(manifest['archive'],manifest['bytes'],manifest['sha256'])
 data=[]
 for i,part in enumerate(parts['parts'],1):
  assert part['path']==f'evidence_parts/MAPPING_REFERENCE_EVIDENCE.zip.part{i:03d}'
  raw=check_path(part['path']).read_bytes();assert len(raw)==part['bytes'] and sha(raw)==part['sha256'];data.append(raw)
 payload=b''.join(data);assert len(payload)==parts['bytes'] and sha(payload)==parts['sha256']
 expected={m['path']:m for m in manifest['members']};assert len(expected)==manifest['member_count']==20
 assert list(expected)==[f'exposure_{i:02d}/RAW_REFERENCE_DIAGNOSTICS.json' for i in range(1,21)]
 prepared=[]
 with zipfile.ZipFile(io.BytesIO(payload)) as archive:
  assert archive.namelist()==list(expected)
  for name,item in expected.items():
   raw=archive.read(name);assert len(raw)==item['bytes'] and sha(raw)==item['sha256'];dest=check_path(name)
   if dest.exists() and (not dest.is_file() or dest.read_bytes()!=raw):raise RuntimeError('Refusing changed evidence destination: '+name)
   prepared.append((dest,raw))
 if not args.verify_only:
  for dest,raw in prepared:
   if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 print(json.dumps(dict(status='PASS',members=20,archive_sha256=parts['sha256'],mode='verify-only' if args.verify_only else 'restore')))
if __name__=='__main__':main()
