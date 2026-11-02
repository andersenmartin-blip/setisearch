"""Focused synthetic transport-failure audit; no network or science arrays."""
from pathlib import Path
import copy,datetime,hashlib,importlib.util,io,json,subprocess,sys,tempfile
from types import SimpleNamespace
from unittest.mock import patch
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;REPO=BASE.parent;SOURCE=BASE/'science_acquisition/download_inputs.py';checks=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def check(value,label):
 if not value:raise AssertionError(label)
 checks.append(label)
def main():
 start=sha(SOURCE);spec=importlib.util.spec_from_file_location('bounded_acquisition_review',SOURCE);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 with tempfile.TemporaryDirectory(prefix='transport_',dir=OUT)as td:
  root=Path(td)
  # Exact freeze/selection/URL binding, with version query mocked locally.
  prep=root/'preflight';prep.mkdir();dp='ADP.2099-01-01T00:00:00.000';metadata='https://archive.eso.org/datalink/links?ID='+dp
  row={'target':'HD122640','dp_id':dp,'metadata_access_url':metadata,'source_url':'https://dataportal.eso.org/dataPortal/file/'+dp,'local_path':str((prep/'products/one.fits').relative_to(REPO))}
  selection=prep/'selection.json';write(selection,{'selected':[{'target':'HD122640','dp_id':dp,'metadata':{'access_url':metadata}}]})
  def freeze(inputs=None,remove=None,release_extra=None):
   p=prep/'PLAN.json';write(p,{'selection_path':str(selection.relative_to(REPO)),'selection_sha256':sha(selection),'inputs':inputs or[row]});files={str(q.relative_to(REPO)):{'sha256':sha(q),'bytes':q.stat().st_size}for q in[p,SOURCE]}
   if remove:files.pop(str(remove.relative_to(REPO)))
   f=prep/'PREFLIGHT_FREEZE.json';write(f,{'files':files});rel={'freeze_sha256':sha(f),'remote_bytes_verified':True,'prospective_commit':'b'*40}
   if release_extra:rel.update(release_extra)
   write(prep/'ROOT_RELEASE.json',rel)
  def preflight():
   with patch.object(m,'HERE',prep),patch.object(m.subprocess,'run',return_value=SimpleNamespace(stdout='curl 8.10.1 synthetic version')):return m.preflight()
  freeze();check(preflight()[0]['inputs']==[row],'Exact selected URL/destination passes frozen preflight')
  def reject(label):
   try:preflight()
   except (ValueError,KeyError):check(True,label)
   else:raise AssertionError('Accepted '+label)
  for p in [SOURCE,prep/'PLAN.json']:freeze(remove=p);reject('Missing required freeze binding '+p.name)
  freeze(release_extra={'remote_bytes_verified':False});reject('Absent public readback rejected')
  freeze(release_extra={'freeze_sha256':'0'*64});reject('Root freeze hash mismatch rejected')
  altered=dict(row,source_url='https://dataportal.eso.org/dataPortal/file/OTHER');freeze(inputs=[altered]);reject('Wrong direct product URL rejected')
  altered=dict(row,metadata_access_url='https://example.org');freeze(inputs=[altered]);reject('Wrong metadata identity URL rejected')
  # One acquire call per synthetic case; errors preserve partial bytes and receipts.
  cases=[('success',0,200,0,None,b'SIMPLE  = SYNTHETIC HEADER'),('http500',0,500,0,None,b'ERROR'),('timeout',28,0,0,None,b'SIMPLE  = PARTIAL'),('redirect',0,302,0,None,b''),('unexpected_effective_url',0,200,0,'https://example.org',b'SIMPLE  = WRONG'),('not_fits',0,200,0,None,b'not fits'),('bytecap',0,200,0,None,b'')]
  for label,code,http,redirects,effective,body in cases:
   d=root/label;d.mkdir();(d/'receipts').mkdir();(d/'products').mkdir();r=dict(row,local_path=str((d/'products/file.fits').relative_to(REPO)));calls=[]
   def run(args,**kwargs):
    calls.append(args);check(args[0:2]==['curl','--disable'],'curl config disabled '+label)
    for flag,value in [('--max-redirs','0'),('--retry','0'),('--max-time','60'),('--connect-timeout','15'),('--max-filesize','16777216'),('--proto','=https')]:check(args[args.index(flag)+1]==value,'Transport bound '+label+' '+flag)
    p=Path(args[args.index('--output')+1]);p.write_bytes(body)
    if label=='bytecap':
     with p.open('r+b')as f:f.truncate(16777216)
    Path(args[args.index('--dump-header')+1]).write_text('SYNTHETIC HEADERS')
    stats={'http_code':http,'num_redirects':redirects,'url_effective':effective or r['source_url']}
    return SimpleNamespace(returncode=code,stdout=json.dumps(stats).encode(),stderr=b'synthetic stderr')
   with patch.object(m,'HERE',d),patch.object(m.subprocess,'run',side_effect=run):result=m.acquire(r,1)
   check(result['status']==('COMPLETE'if label=='success'else'FAILED'),'Correct transport outcome '+label)
   check(len(calls)==1,'One attempt without retry '+label)
   receipt=REPO/result['acquisition_receipt_path'];check(sha(receipt)==result['acquisition_receipt_sha256'],'Receipt hash bound '+label)
   check(result['sha256']==sha(REPO/r['local_path'])and result['bytes']==(REPO/r['local_path']).stat().st_size,'Saved partial/full bytes retained '+label)
  # Unexpected existing payload is a FAILED slot, not an overwrite or escaping exception.
  d=root/'exists';d.mkdir();(d/'receipts').mkdir();(d/'products').mkdir();p=d/'products/existing';p.write_bytes(b'PRESERVE');r=dict(row,local_path=str(p.relative_to(REPO)))
  with patch.object(m,'HERE',d),patch.object(m.subprocess,'run',side_effect=AssertionError('No request for existing payload')):result=m.acquire(r,1)
  check(result['status']=='FAILED'and p.read_bytes()==b'PRESERVE','Existing payload preserved and failed slot accounted')
  # First failure produces explicit not-attempted records for every remaining selected slot.
  d=root/'run';d.mkdir();write(d/'PLAN.json',{'synthetic':True});inputs=[dict(row,dp_id=f'ADP.2099-01-0{i}T00:00:00.000')for i in range(1,5)];plan={'inputs':inputs};called=[]
  def fail(r,i):called.append(r['dp_id']);return dict(r,status='FAILED',reason='synthetic bounded failure',bytes=0,sha256=None)
  with patch.object(m,'HERE',d),patch.object(m,'preflight',return_value=(plan,{'synthetic':True},'synthetic curl')),patch.object(m,'acquire',side_effect=fail),patch.object(sys,'argv',['audit','--execute']),patch('sys.stdout',new=io.StringIO()):m.main()
  manifest=read(d/'ACQUISITION_MANIFEST.json');check(called==[inputs[0]['dp_id']],'First failure prevents remaining requests')
  check([r['status']for r in manifest['inputs']]==['FAILED']+['NOT_ATTEMPTED']*3,'All four selected statuses retained after first failure')
  check([r['dp_id']for r in manifest['inputs']]==[r['dp_id']for r in inputs],'Exact selected-slot order preserved')
  check(manifest['new_arrays_interpreted']==0 and manifest['status']=='STOPPED_AFTER_FAILURE','Transport never claims array interpretation')
 check(sha(SOURCE)==start,'Transport code unchanged during audit')
 report={'status':'PASS_CONDITIONAL_TRANSPORT_FAILURE_AUDIT','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks_passed':len(checks),'check_labels':checks,'script_sha256':sha(SOURCE),'audit_script_sha256':sha(__file__),'network_requests':0,'new_science_arrays_read':0,'actual_plan_or_release_reviewed':False,'limits':['Synthetic failure paths and conditional script reviewed only. Actual selected-slot PLAN/PREFLIGHT_FREEZE/ROOT_RELEASE require final binding verification before download.','At most4 products,16MiB each,60second curl deadline and1attempt are coded bounds; no assertion that live service availability or future payload compatibility is established.']}
 write(OUT/'TRANSPORT_AUDIT.json',report);print(json.dumps({k:v for k,v in report.items()if k!='check_labels'},indent=2))
if __name__=='__main__':main()
