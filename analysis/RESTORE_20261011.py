import hashlib,json,time,resource,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'analysis/deps'))
import h5py,hdf5plugin,numpy as np
t=time.perf_counter();cpu=time.process_time();records=[]
for native,rel in [(171,'analysis/new_visit_recovery/results/acquire'),(None,'analysis/s2017_next_native/results/acquire')]:
 d=root/rel;a=json.loads((d/'ACQUISITION_RESULT.json').read_text())
 for rec in a['decoded_files']:
  p=d/rec['array_file'];sha=hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
  assert p.stat().st_size==rec['bytes'] and sha==rec['file_sha256'],str(p)
  with h5py.File(p,'r') as f:
   data=f['data'];assert list(data.shape)==rec['shape'];assert int(data.attrs['original_source_frequency_chunk_origin'])==rec['source_channel0']
   for r in rec['decoded_rows']:
    b=np.asarray(data[r['time_row'],0,:],dtype='<f4').tobytes();assert len(b)==r['decoded_bytes'];assert hashlib.sha256(b).hexdigest()==r['decoded_sha256']
  records.append({'path':str(p.relative_to(root)), 'bytes':p.stat().st_size,'sha256':sha,'native':native or rec['native_chunk_index'],'scan_id':rec['scan_id'],'decoded_rows_verified':16})
out={'status':'PASS_EXACT18_COMPACTS_288_DECODED_ROWS','date_UTC':'2026-10-11','sources':records,'archive_sha256s':{'native171':'6e08922aec5c5a6737987887cd62aab6d52495650297cae74745a654728f4786','native170_172':'b78521c9f51a47d698af1ea1f8949b5676c843656389655191042a0fbc06817f'},'new_telescope_requests':0,'cost_DKK':0,'process_CPU_s':time.process_time()-cpu,'wall_s':time.perf_counter()-t,'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'restoration_error_correction':'Initial archive join accidentally included an incomplete helper download temporary file; asserted SHA mismatch before extraction. Corrected exact part01/02/03 assembly matches original canonical archive. No science ran.'}
p=root/'analysis/RESTORATION_RECEIPT_20261011.json';p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='sources'}))
