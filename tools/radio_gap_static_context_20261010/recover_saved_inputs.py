from pathlib import Path
import hashlib,json,resource,signal,time,zipfile
start=time.monotonic();cpu=time.process_time()
resource.setrlimit(resource.RLIMIT_CPU,(10,11));resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3));signal.alarm(120)
root=Path('setisearch_checkpoint'); records=[];archives=[]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()
inputs=[('SETI_SIGNAL_FOLLOWUP_2026-10-10.zip',6418319,'8cde42def9d1d46dfabc12da56fc7778fd796d260e5e9a985e359cfbe6a4eb70'),('SETI_FRESH_BAND151_RAW_2026-10-09.zip',305428707,'6696fe54086e019ce966816dc818969ca5f1682e3ff9211326f1a68d2323ef1d')]
for name,size,pin in inputs:
 p=Path('seti_gap_static_work/recovered')/name
 assert p.stat().st_size==size and sha(p)==pin
 archives.append({'file_name':name,'bytes':size,'sha256':pin})
 with zipfile.ZipFile(p) as z:
  for member in z.infolist():
   rel=Path(member.filename)
   assert not rel.is_absolute() and '..' not in rel.parts
   if member.is_dir():continue
   if 'RAW' in name and not (member.filename.startswith('results/radio_fresh_band_20261009/arrays/') and (member.filename.endswith('.compact.h5') or rel.name=='ACQUISITION_RESULT.json')):continue
   dest=root/rel
   dest.parent.mkdir(parents=True,exist_ok=True)
   b=z.read(member);assert len(b)==member.file_size
   reused=dest.exists()
   if reused:assert dest.read_bytes()==b, 'Recovery cannot overwrite different existing bytes: '+str(rel)
   else:dest.write_bytes(b)
   records.append({'path':member.filename,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'member_CRC_verified':True,'byte_identical_existing_file_reused':reused})
elapsed=time.monotonic()-start;used=time.process_time()-cpu
assert used<=10 and elapsed<=120
out=root/'results/radio_gap_static_context_20261010';out.mkdir(parents=True,exist_ok=True)
d={'schema':'SETI_SAVED_STATIC_CONTEXT_RECOVERY_V1','status':'PASS_BYTE_EXACT_ARCHIVES_AND_MEMBERS','archives':archives,'received_archive_payload_bytes':sum(x['bytes']for x in archives),'member_count':len(records),'members':records,'HDF5_or_NPZ_scientific_arrays_decoded':False,'new_telescope_HTTP_requests':0,'new_telescope_BODY_bytes':0,'process_CPU_s':used,'wall_s':elapsed,'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'CPU_cap_s':10,'activity_charge':'40CPU-s preparation reservation','prior_local_attempt':{'status':'STOPPED_EXISTING_FILE_NO_OVERWRITE_GUARD','wall_s':0.848529358,'CPU_not_separately_metered':True,'network_requests_repeated':False,'scientific_arrays_decoded':False,'resolution':'Accept only byte-identical already recovered/fetched metadata; retain different-byte refusal. All archive identities preserved; no telescope or numerical retry.'}}
(out/'RECOVERY_RECEIPT.json').write_text(json.dumps(d,indent=2)+'\n');signal.alarm(0)
print(json.dumps({k:d[k] for k in ['status','member_count','received_archive_payload_bytes','process_CPU_s','wall_s']}))
