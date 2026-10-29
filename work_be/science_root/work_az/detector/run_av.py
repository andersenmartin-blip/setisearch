"""Prospectively pinned AO continuous-normalization full-grid runner."""
from pathlib import Path
import datetime,gc,hashlib,json,os,resource,sys,time
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import numpy as np
import pipeline_v as pipe
import publication
B=Path(__file__).resolve().parent
def sha(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text())
def new(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(x,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def verify(p):
 for rel,h in p['source_sha256'].items():assert sha(Path(p['root'])/rel)==h,rel
 for s in p['scans']:assert sha(Path(p['root'])/s['native_path'])==s['input_sha256']
def pub(out,name,arrays):
 p=out/(name+'.npz');r=publication.publish_npz(arrays,p);new(out/(name+'.publication.json'),r)
 return {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'array_bytes':sum(a.nbytes for a in arrays.values())}
def main():
 action,protocol,outarg=sys.argv[1:4];p=read(protocol);root=Path(p['root']);out=Path(outarg);out.mkdir(parents=True,exist_ok=True)
 verify(p);start=time.perf_counter();c=p['configuration'];publications=[]
 if action=='scan':
  j=int(sys.argv[4]);s=p['scans'][j];raw=np.load(root/s['native_path'],mmap_mode='r',allow_pickle=False)
  assert raw.shape==(16,1048576) and raw.dtype==np.dtype('<f4')
  grid,audit,catalog,summary=pipe.search(raw,s,c,progress=lambda w,ri,n,t,h:print(json.dumps({'scan':j,'width':w,'ri':ri,'rates':n,'seconds':t,'hits':h}),flush=True))
  assert summary['complete'] and not summary['hit_overflow'] and summary['track_trials']==2291315712
  assert len(summary['strict_original_template_checks'])==16 and all(x['strict_5e_5_pass'] for x in summary['strict_original_template_checks'])
  for kind,arrays in [('grid',grid),('audit',audit),('catalog',catalog)]:publications.append(pub(out,f'scan{j}_{kind}',arrays))
  summary.update(normalization_version='ac-native-f32-anchors-f64-linear-center-interpolation-v1',protocol_sha256=sha(protocol),publications=publications)
  new(out/f'scan{j}_summary.json',summary)
 elif action=='triage':
  for s in p['scans']:
   r=read(out/f"scan{s['scan']}_summary.json");assert r['protocol_sha256']==sha(protocol) and r['complete']
   for a in r['publications']:assert sha(a['path'])==a['sha256']
  def arrays(j,kind):
   with np.load(out/f'scan{j}_{kind}.npz',allow_pickle=False) as z:return {k:z[k] for k in z.files}
  triage,ts=pipe.forced_triage(root,out,p['scans'],c,lambda s:arrays(s,'grid'),lambda s:arrays(s,'catalog'),progress=lambda j,n,m:print(json.dumps({'destination':j,'ON_rows':n,'measured':m}),flush=True))
  publications.append(pub(out,'all_ON_forced_triage',triage));new(out/'TRIAGE_SUMMARY.json',ts)
 else:raise ValueError(action)
 verify(p)
 new(out/(f'scan{sys.argv[4]}_RUN_CLOSED.json' if action=='scan' else 'TRIAGE_RUN_CLOSED.json'),{'action':action,'protocol_sha256':sha(protocol),'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'wall_seconds':time.perf_counter()-start,'status':'COMPLETE','publications':publications,'peak_self_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024})
 print(json.dumps({'action':action,'status':'COMPLETE','wall_seconds':time.perf_counter()-start}),flush=True)
if __name__=='__main__':main()
