"""Verify archived exact profile/derived bytes; retain identical files, refuse changed files."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,io,json,zipfile
ROOT=Path(__file__).resolve().parent

def sha(b):return hashlib.sha256(b).hexdigest()
def safe(root,name,part=False):
 p=PurePosixPath(name)
 assert not p.is_absolute() and '\\'not in name and all(s not in('.','..','')for s in p.parts),'Unsafepath'
 if part:assert len(p.parts)==2 and p.parts[0]=='evidence_archive_parts'
 else:assert p.suffix=='.npz'and(p.parts[:-1]==('derived',)or p.parts[:-1]==('inputs','profiles'))
 path=root.joinpath(*p.parts)
 for q in [path,*path.parents]:
  if q==root.parent:break
  assert not q.is_symlink(),'Symlinkrefused'
 assert path.resolve().is_relative_to(root.resolve());return path

def restore(source=ROOT,destination=None,verify_only=False):
 source=Path(source).resolve();destination=source if destination is None else Path(destination).resolve();parts=json.loads((source/'EVIDENCE_PARTS.json').read_text());encoded=(source/'EVIDENCE_ARCHIVE.json').read_bytes();assert sha(encoded)==parts['archive_manifest_sha256'];manifest=json.loads(encoded)
 assert parts['schema']=='SETI_NORMALIZATION_CONTEXT_PARTS_V1'and manifest['schema']=='SETI_NORMALIZATION_CONTEXT_EVIDENCE_V1';assert [r['index']for r in parts['parts']]==list(range(1,len(parts['parts'])+1))
 blocks=[]
 for r in parts['parts']:
  b=safe(source,r['path'],True).read_bytes();assert len(b)==r['bytes']and sha(b)==r['sha256'];blocks.append(b)
 data=b''.join(blocks);assert len(data)==parts['bytes']==manifest['bytes']and sha(data)==parts['sha256']==manifest['sha256'];members=manifest['members'];assert len(members)==manifest['member_count']==48
 with zipfile.ZipFile(io.BytesIO(data))as z:
  assert z.namelist()==[r['path']for r in members]and len(z.namelist())==len(set(z.namelist()))and z.testzip()is None
  for r in members:
   b=z.read(r['path']);assert len(b)==r['bytes']and sha(b)==r['sha256'];p=safe(destination,r['path'])
   if p.exists():assert p.is_file()and sha(p.read_bytes())==r['sha256'],'Existingfilediffers'
  created=0
  if not verify_only:
   for r in members:
    p=safe(destination,r['path'])
    if p.exists():continue
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb')as f:f.write(z.read(r['path']))
    assert sha(p.read_bytes())==r['sha256'];created+=1
 return {'status':'VERIFIED'if verify_only else'RESTORED','members':len(members),'created':created,'archive_sha256':manifest['sha256']}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--destination',type=Path);p.add_argument('--verify-only',action='store_true');a=p.parse_args();print(json.dumps(restore(destination=a.destination,verify_only=a.verify_only),indent=2))
if __name__=='__main__':main()
