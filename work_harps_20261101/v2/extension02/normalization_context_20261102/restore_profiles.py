"""Verify original archive and restore only fixed selected existing profile bytes."""
from pathlib import Path
import csv,hashlib,json,zipfile
OUT=Path(__file__).resolve().parent;EXT=OUT.parent;EPOCH=EXT/'epoch_followup'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 plan=json.loads((OUT/'PLAN.json').read_text());parts=json.loads((EPOCH/'PROFILE_ARRAYS_PARTS.json').read_text())
 for name,h in plan['source_hashes'].items():assert sha(EXT/name)==h,name
 rows=list(csv.DictReader((OUT/'inputs/SELECTED_EPOCH_PROFILES.csv').open()));assert len(rows)==28
 assert sha(OUT/'inputs/SELECTED_EPOCH_PROFILES.csv')==plan['selected_profiles_sha256']
 dest=OUT/'inputs/PROFILE_ARRAYS.zip'
 if not dest.exists():
  with dest.open('xb')as stream:
   for r in parts['parts']:
    p=EPOCH/r['path'];assert p.stat().st_size==r['bytes']and sha(p)==r['sha256'];stream.write(p.read_bytes())
 assert dest.stat().st_size==parts['bytes']and sha(dest)==parts['sha256']
 restored=[]
 with zipfile.ZipFile(dest)as archive:
  assert len(archive.namelist())==4370
  for r in rows:
   data=archive.read(r['profile_path']);assert hashlib.sha256(data).hexdigest()==r['profile_sha256']
   p=OUT/'inputs'/r['profile_path'];p.parent.mkdir(parents=True,exist_ok=True)
   if p.exists():assert p.read_bytes()==data
   else:p.write_bytes(data)
   restored.append({'path':str(p.relative_to(OUT)),'bytes':len(data),'sha256':r['profile_sha256']})
 report={'status':'PASS','archive_bytes':parts['bytes'],'archive_sha256':parts['sha256'],'archive_parts':len(parts['parts']),'archive_profiles':4370,'profiles_restored':28,'restored':restored,'no_array_values_inspected':True}
 (OUT/'PROFILE_RESTORE.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS28verified profiles restored; no arrays interpreted')
if __name__=='__main__':main()
