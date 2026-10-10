"""Byte-only recovery of already retained SETI archives; no array decoding."""
from pathlib import Path
import hashlib
import json
import resource
import time
import zipfile

ROOT=Path(__file__).resolve().parent.parent/'setisearch_fullpower'
ARCHIVES=Path(__file__).resolve().parent/'recovered'
OUT=ROOT/'results/radio_full_safe_20261010'
EXPECTED={
 'SETI_GAP_STATIC_CONTEXT_2026-10-10.zip':(6206173,'c00195d119596d1cf2a42653754a70bfd39e60262b406e59408c4e1759517146'),
 'SETI_FRESH_BAND151_RAW_2026-10-09.zip':(305428707,'6696fe54086e019ce966816dc818969ca5f1682e3ff9211326f1a68d2323ef1d'),
 'SETI_SIGNAL_FOLLOWUP_2026-10-10.zip':(6418319,'8cde42def9d1d46dfabc12da56fc7778fd796d260e5e9a985e359cfbe6a4eb70')}

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()

def main():
 start=time.monotonic();resource.setrlimit(resource.RLIMIT_CPU,(60,61))
 resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
 OUT.mkdir(parents=True,exist_ok=True)
 archives=[];members=[]
 for name,(size,sha) in EXPECTED.items():
  p=ARCHIVES/name
  assert p.stat().st_size==size and digest(p)==sha,name
  archives.append({'filename':name,'bytes':size,'sha256':sha})
  with zipfile.ZipFile(p) as z:
   for i in z.infolist():
    if i.is_dir():continue
    n=i.filename;rel=Path(n)
    assert not rel.is_absolute() and '..' not in rel.parts,n
    if name=='SETI_FRESH_BAND151_RAW_2026-10-09.zip' and not (
       n.startswith('results/radio_fresh_band_20261009/arrays/') and
       (n.endswith('.compact.h5') or n.endswith('/ACQUISITION_RESULT.json'))):continue
    b=z.read(i);assert len(b)==i.file_size
    dest=ROOT/rel;dest.parent.mkdir(parents=True,exist_ok=True)
    reused=dest.exists()
    if reused:assert dest.read_bytes()==b,'Different existing bytes: '+n
    else:dest.write_bytes(b)
    assert digest(dest)==hashlib.sha256(b).hexdigest(),n
    members.append({'path':n,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),
      'member_CRC_verified':True,'byte_identical_existing_file_reused':reused})
 result={'schema':'SETI_FULL_SAFE_SAVED_INPUT_RECOVERY_V1','status':'PASS_BYTE_EXACT_SAVED_ARCHIVES_AND_MEMBERS',
  'archives':archives,'received_archive_payload_bytes':sum(x['bytes'] for x in archives),
  'members':members,'member_occurrences':len(members),'new_telescope_HTTP_requests':0,
  'new_telescope_BODY_bytes':0,'HDF5_or_NPZ_values_decoded':False,
  'process_CPU_s':time.process_time(),'wall_s':time.monotonic()-start,
  'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'CPU_cap_s':60,
  'activity_charge':'400 CPU-s current-stage preparation allocation, not subscription quota'}
 (OUT/'RECOVERY_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k!='members'}))

if __name__=='__main__':main()
