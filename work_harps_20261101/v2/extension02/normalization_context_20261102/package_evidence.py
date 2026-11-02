"""Deterministic exact-byte checkpoint of all28 selected profiles and20 derived arrays."""
from pathlib import Path
import hashlib,json,zipfile
OUT=Path(__file__).resolve().parent

def sha(data):return hashlib.sha256(data).hexdigest()
def main():
 files=sorted(list((OUT/'inputs/profiles').glob('*.npz'))+list((OUT/'derived').glob('*.npz')));assert len(files)==48
 members=[{'path':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}for p in files];members.sort(key=lambda r:r['path'])
 archivepath=OUT/'EVIDENCE.zip'
 with zipfile.ZipFile(archivepath,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9)as z:
  for r in members:
   info=zipfile.ZipInfo(r['path'],(1980,1,1,0,0,0));info.create_system=3;info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,(OUT/r['path']).read_bytes(),compresslevel=9)
 data=archivepath.read_bytes()
 with zipfile.ZipFile(archivepath)as z:
  assert z.namelist()==[r['path']for r in members] and z.testzip()is None
  for r in members:assert len(z.read(r['path']))==r['bytes']and sha(z.read(r['path']))==r['sha256']
 manifest={'schema':'SETI_NORMALIZATION_CONTEXT_EVIDENCE_V1','archive_filename':'EVIDENCE.zip','bytes':len(data),'sha256':sha(data),'member_count':48,'archived_profiles':28,'derived_arrays':20,'members':members,'scope':'Exact original28subsetprofiles plus20derivedmerged/native/rawarrays. SourceFITS/TARproducts remain in existing savedinputarchives; no reassignedlabels.','deterministic_zip':{'timestamp':'1980-01-01T00:00:00','compression':'DEFLATE9','order':'lexicographic','mode':'regular0644'}}
 encoded=(json.dumps(manifest,indent=2)+'\n').encode();(OUT/'EVIDENCE_ARCHIVE.json').write_bytes(encoded);(OUT/'evidence_archive_parts').mkdir(exist_ok=True);parts=[]
 for i,start in enumerate(range(0,len(data),2*1024*1024),1):
  block=data[start:start+2*1024*1024];name=f'evidence_archive_parts/EVIDENCE.zip.part{i:03d}';(OUT/name).write_bytes(block);parts.append({'index':i,'path':name,'bytes':len(block),'sha256':sha(block)})
 (OUT/'EVIDENCE_PARTS.json').write_text(json.dumps({'schema':'SETI_NORMALIZATION_CONTEXT_PARTS_V1','archive_manifest':'EVIDENCE_ARCHIVE.json','archive_manifest_sha256':sha(encoded),'output_filename':'EVIDENCE.zip','bytes':len(data),'sha256':sha(data),'parts':parts},indent=2)+'\n');print(json.dumps({'bytes':len(data),'sha256':sha(data),'members':48,'parts':len(parts)},indent=2))
if __name__=='__main__':main()
