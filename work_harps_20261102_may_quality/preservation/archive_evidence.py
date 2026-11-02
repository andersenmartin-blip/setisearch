"""Archive exact local bytes without FITS/array interpretation; no network."""
import argparse,hashlib,json,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
REPO=ROOT.parent
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('kind',choices=['inputs','profiles']);a=ap.parse_args()
 if a.kind=='inputs':
  manifest=ROOT/'acquisition/ACQUISITION_MANIFEST.json';source=json.loads(manifest.read_bytes())
  rows=source['inputs'];assert len(rows)==1 and rows[0]['status']=='COMPLETE'
  files=[REPO/x['local_path'] for x in rows]
  for p,x in zip(files,rows):assert len(p.read_bytes())==x['bytes'] and sha(p.read_bytes())==x['sha256']
  name='SCIENCE_INPUTS';expected=1
 else:
  manifest=ROOT/'comparison/results/OUTPUT_HASHES.json';source=json.loads(manifest.read_bytes())
  files=sorted((ROOT/'comparison/results/profiles').glob('*.npz'))
  for p in files:assert sha(p.read_bytes())==source[str(p.relative_to(ROOT/'comparison/results'))]
  name='PROFILE_EVIDENCE';expected=12
 assert len(files)==expected and all(p.is_file() and not p.is_symlink() for p in files)
 archive=HERE/(name+'.zip');members=[]
 with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in files:
   data=p.read_bytes();relative=str(p.relative_to(ROOT));info=zipfile.ZipInfo(relative,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
   z.writestr(info,data);members.append({'path':relative,'bytes':len(data),'sha256':sha(data)})
 data=archive.read_bytes();partdir=HERE/(name+'_parts');partdir.mkdir(exist_ok=False);parts=[]
 for i,start in enumerate(range(0,len(data),900000),1):
  part=partdir/(name+'.zip.part%03d'%i);chunk=data[start:start+900000];part.write_bytes(chunk);parts.append({'path':str(part.relative_to(HERE)),'bytes':len(chunk),'sha256':sha(chunk)})
 out={'schema':'HARPS_MAY_QUALITY_EXACT_ARCHIVE_V1','kind':a.kind,'archive':archive.name,'bytes':len(data),'sha256':sha(data),'members':members,'parts':parts,'source_manifest':str(manifest.relative_to(REPO)),'source_manifest_sha256':sha(manifest.read_bytes()),'restore':'python3 restore_archive.py '+name+'_MANIFEST.json','science_arrays_interpreted_by_archiver':0}
 (HERE/(name+'_MANIFEST.json')).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'archive':name,'members':len(files),'bytes':len(data),'parts':len(parts),'sha256':sha(data)},indent=2))
if __name__=='__main__':main()
