"""Independent archived-byte and header-only inventory audit. No pixel-value decoding."""
import ast,datetime,hashlib,io,json,math,struct,subprocess,tarfile,zipfile
from pathlib import Path
from astropy.io.fits import Header
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];I=HERE.parent/'inputs';OLD=REPO/'work_harps_20261101/v2/extension02/raw_followup_batch03'
def read(p):return json.loads(p.read_bytes())
def digest(data):return hashlib.sha256(data).hexdigest()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def head(f):
 blocks=[]
 while True:
  b=f.read(2880)
  if len(b)!=2880:raise ValueError('Truncated header')
  blocks.append(b)
  if any(b[n:n+8]==b'END     ' for n in range(0,2880,80)):break
  if len(blocks)*2880>524288:raise ValueError('Header cap')
 return Header.fromstring(b''.join(blocks).decode('ascii'),sep='')
def fits_headers(path):
 result=[]
 with path.open('rb') as f:
  while f.tell()<path.stat().st_size:
   h=head(f);result.append(h)
   count=math.prod([int(h['NAXIS'+str(j)]) for j in range(1,h['NAXIS']+1)]) if h['NAXIS'] else 0
   size=(count+int(h.get('PCOUNT',0)))*int(h.get('GCOUNT',1))*abs(h['BITPIX'])//8
   f.seek(((size+2879)//2880)*2880,1)
  assert f.tell()==path.stat().st_size
 return result
checks=[]
def ck(k,v):checks.append({'check':k,'pass':bool(v)})
inv=read(I/'INPUT_INVENTORY.json');meta=read(HERE/'INPUT_METADATA_AUDIT.json');trace=read(I/'TRACE_METADATA.json');records=inv['files']
ck('exact seven unique restored paths including header-inspected native B',len(records)==7 and len({x['path'] for x in records})==7)
for x in records:
 p=(REPO/x['path']).resolve();p.relative_to(I)
 ck('restored hash '+p.name,p.stat().st_size==x['bytes'] and sha(p)==x['sha256'])
byname={Path(x['path']).name:REPO/x['path'] for x in records}
archive=Path(inv['archive_local_path_used']);ck('archived package exact original',archive.name==meta['archive']['filename'] and archive.stat().st_size==meta['archive']['bytes'] and sha(archive)==meta['archive']['sha256'])
with zipfile.ZipFile(archive) as z:
 for kind,record in meta['inputs'].items():
  matches=[x for x in z.infolist() if x.filename==record['relative_path']];ck('unique archive member '+kind,len(matches)==1 and matches[0].file_size==record['bytes'])
  data=z.read(record['relative_path']);ck('archive member hash '+kind,digest(data)==record['sha256'] and sha(byname[Path(record['relative_path']).name])==record['sha256'])
parts=read(OLD/'EVIDENCE_PARTS.json');data=b''
for part in parts['parts']:
 raw=(OLD/part['path']).read_bytes();ck('evidence part '+part['path'],len(raw)==part['bytes'] and digest(raw)==part['sha256']);data+=raw
em=read(OLD/'EVIDENCE_ARCHIVE.json');ck('assembled old evidence identity',len(data)==em['bytes'] and digest(data)==em['sha256'])
with zipfile.ZipFile(io.BytesIO(data)) as z:
 for key in ['cutout','reference_grid']:
  r=meta[key];ck('archived '+key+' exact bytes',digest(z.read(r['path']))==r['sha256'] and sha(I/'evidence'/r['path'])==r['sha256'])
raw=byname['HARPS.2023-02-22T07_40_53.531.fits.Z'];decompressed=byname['HARPS.2023-02-22T07_40_53.531.fits'];h=hashlib.sha256();n=0
proc=subprocess.Popen(['gzip','-cd',str(raw)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
for chunk in iter(lambda:proc.stdout.read(1048576),b''):h.update(chunk);n+=len(chunk)
err=proc.stderr.read();rc=proc.wait();ck('decompressed raw opaque bytes exact',rc==0 and n==decompressed.stat().st_size and h.hexdigest()==sha(decompressed))
anc=byname['ADP.2023-02-23T01_01_36.792.tar'];native=byname['HARPS.2023-02-22T07_40_53.531_e2ds_A.fits']
with tarfile.open(anc) as z:
 members=[m for m in z if m.name.endswith('_e2ds_A.fits')];ck('unique expected native A TAR member',len(members)==1 and members[0].name==meta['native_member'] and members[0].isfile());ck('native A exact member bytes',digest(z.extractfile(members[0]).read())==sha(native))
 bm=[m for m in z if m.name.endswith('_e2ds_B.fits')];bp=byname['HARPS.2023-02-22T07_40_53.531_e2ds_B.fits'];ck('unique exact native B TAR bytes',len(bm)==1 and bm[0].name==meta['native_member'].replace('_A.fits','_B.fits') and digest(z.extractfile(bm[0]).read())==sha(bp))
rh=fits_headers(decompressed);nh=fits_headers(native)
ck('raw 3HDU shape and no orientation conversion',len(rh)==3 and rh[0]['NAXIS']==0 and all(h['XTENSION']=='IMAGE' and [h['NAXIS2'],h['NAXIS1']]==[4096,2148] for h in rh[1:]))
ck('native A shape',len(nh)==1 and [nh[0]['NAXIS2'],nh[0]['NAXIS1']]==[72,4096])
ck('header identity dates',rh[0]['ARCFILE']=='HARPS.2023-02-22T07:40:53.531.fits' and rh[0]['DATE-OBS']==nh[0]['DATE-OBS']=='2023-02-22T07:40:53.531' and rh[0]['INSTRUME']==nh[0]['INSTRUME']=='HARPS' and rh[0]['OBJECT'].replace(' ','')==nh[0]['OBJECT'].replace(' ','')=='HD122640')
ck('native science BERV',nh[0]['ESO DRS BERV']==26.7848884193233)
coeff=[nh[0]['ESO DRS CAL LOC CTR'+str(250+j)] for j in range(5)];ck('frozen trace coefficients exact headers',trace['trace_polynomial_degree']==4 and coeff==trace['trace_polynomial_coefficients_ascending'])
ck('header trace coordinate reproduces saved center',abs(sum(c*3139**j for j,c in enumerate(coeff))-meta['axis_contract']['event_center']['raw_stitched_column'])<1e-8)
shapes={};npz=I/'evidence/native/V2E2-0235_o50.npz'
with zipfile.ZipFile(npz) as z:
 for member in z.namelist():
  with z.open(member) as f:
   assert f.read(6)==b'\x93NUMPY';v=tuple(f.read(2));n=struct.unpack('<H' if v==(1,0) else '<I',f.read(2 if v==(1,0) else 4))[0];assert n<=65536;h=ast.literal_eval(f.read(n).decode('latin1' if v[0]<3 else 'utf-8'));shapes[member.removesuffix('.npy')]={'shape':list(h['shape']),'dtype':h['descr'],'fortran_order':h['fortran_order']}
ck('NPY shape metadata agrees inventory',shapes=={r['key']:{k:r[k] for k in ['shape','dtype','fortran_order']} for r in inv['npy_headers_only']})
ck('cutout shapes and control coverage',shapes['raw_cutout']['shape']==[31,33] and shapes['baseline_raw_cutout']['shape']==[21,25] and shapes['native_flux']['shape']==[41] and inv['existing_cutout_control_coverage_available'] is False and inv['full_raw_control_coverage_available'] is True)
for path,r in meta['scientific_sources_preserved'].items():ck('unchanged historical '+path,sha(REPO/path)==r['sha256'] and (REPO/path).stat().st_size==r['bytes'])
source_bytes={str((I/n).relative_to(REPO)):{'sha256':sha(I/n),'bytes':(I/n).stat().st_size} for n in ['INPUT_INVENTORY.json','TRACE_METADATA.json','RESTORE_RECEIPT.json','restore_inputs.py']}
out={'schema':'HARPS_SPATIAL0235_RESTORED_INPUT_AUDIT_V1','status':'PASS' if all(x['pass'] for x in checks) else 'FAIL','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'script_sha256':sha(Path(__file__)),'check_count':len(checks),'checks':checks,'reviewed_input_metadata':source_bytes,'npz_headers_only':shapes,'method':'Whole products and archives read only as opaque bytes for hashes/decompression equivalence; FITS image payloads seek-skipped while headers parsed. NPY member headers only, not ndarray values. No production restore code imported.','network_requests':0,'raw_or_native_pixel_values_interpreted':0,'trace_coordinate_fit_or_orientation_changed':False,'existing_cutout_covers_flanking_controls':False,'restored_full_raw_covers_required_rows':True,'scope_limit':'Input identity, shape, provenance and existing coordinate conventions only; science and new spatial diagnostic remain frozen separately.'}
(HERE/'RESTORED_INPUT_AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'checks':len(checks),'failed':[x['check'] for x in checks if not x['pass']]}));assert out['status']=='PASS'
