"""Read only FITS header blocks; hash opaque product bytes, never interpret arrays."""
import datetime,hashlib,json,math,re
from pathlib import Path
from astropy.io.fits import Header
HERE=Path(__file__).resolve().parent; REPO=HERE.parents[1];ACQ=HERE.parent/'acquisition'
def read(p):return json.loads(p.read_bytes())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
checks=[]
def ck(k,v):checks.append({'check':k,'pass':bool(v)})
def header_blocks(f):
 chunks=[]
 while True:
  b=f.read(2880)
  if len(b)!=2880:raise ValueError('Truncated FITS header')
  chunks.append(b)
  if any(b[i:i+8]==b'END     ' for i in range(0,2880,80)):break
  if sum(map(len,chunks))>524288:raise ValueError('Header cap exceeded')
 return Header.fromstring(b''.join(chunks).decode('ascii'),sep=''),sum(map(len,chunks))
p=read(ACQ/'PLAN.json');m=read(ACQ/'ACQUISITION_MANIFEST.json');s=read(ACQ/'SELECTION.json');rel=read(ACQ/'PAYLOAD_RELEASE.json');x=m['inputs'][0];product=REPO/x['product_path'];recpath=REPO/x['acquisition_receipt_path'];rec=read(recpath)
ck('one complete exact selected product',m['status']=='COMPLETE' and len(m['inputs'])==1 and x['status']=='COMPLETE' and x['dp_id']==s['selected'][0]['dp_id']==p['job']['dp_id'])
ck('opaque file hash and bounded bytes',0<product.stat().st_size<16777216 and product.stat().st_size==x['bytes']==m['bytes_saved']==rec['bytes'] and sha(product)==x['sha256']==x['product_sha256']==rec['sha256'])
ck('receipt binding',sha(recpath)==x['acquisition_receipt_sha256'])
ck('plan result release bindings',m['plan_sha256']==sha(ACQ/'PLAN.json') and m['payload_release_sha256']==sha(ACQ/'PAYLOAD_RELEASE.json') and m['header_results_sha256']==sha(ACQ/'HEADER_RESULTS.json') and m['selection_sha256']==sha(ACQ/'SELECTION.json'))
ck('separate published payload release',rel['schema']=='HARPS_MAY_QUALITY_PAYLOAD_RELEASE_V1' and rel['approved'] is True and rel['remote_bytes_verified'] is True and rel['header_release_sha256']==sha(ACQ/'HEADER_RELEASE.json') and rel['header_results_sha256']==sha(ACQ/'HEADER_RESULTS.json') and rel['selection_sha256']==sha(ACQ/'SELECTION.json'))
pub=REPO/rel['publication_receipt_path'];pubdoc=read(pub)
ck('publication receipt original bytes',sha(pub)==rel['publication_receipt_sha256'] and pubdoc['status']=='PASS_EXACT_REMOTE_READBACK' and pubdoc['commit']==rel['prospective_commit'])
t=rec['transport'];ck('single HTTP200 no redirect exactURL',rec['status']=='COMPLETE' and rec['attempts']==1 and rec['retries']==0 and rec['redirects_followed']==0 and rec['curl_returncode']==0 and t['http_code']==200 and t['num_redirects']==0 and t['url_effective']==p['payload']['url'])
ck('bounded elapsed and transfer bytes',t['time_total']<=60 and t['size_download']==product.stat().st_size)
cmd=rec['command'];ck('bounded command',cmd[cmd.index('--max-time')+1]=='60' and cmd[cmd.index('--max-filesize')+1]=='16777216' and cmd[cmd.index('--retry')+1]=='0' and cmd[cmd.index('--max-redirs')+1]=='0' and '-L' not in cmd and '--location' not in cmd)
with product.open('rb') as f:
 primary,primarybytes=header_blocks(f)
 if primary['NAXIS']!=0:raise ValueError('Primary has data; do not access')
 extension,extensionbytes=header_blocks(f)
 header_end=f.tell()
keys=[c.keyword for c in primary.cards if c.keyword not in {'COMMENT','HISTORY',''}]
ck('unique primary cards',len(keys)==len(set(keys)))
ck('header-only primary',primary['SIMPLE'] is True and primary['NAXIS']==0 and not isinstance(primary['NAXIS'],bool))
for k,v in s['selected'][0]['primary_header'].items():
 actual=primary.get(k.removeprefix('HIERARCH ')); ok=actual==v
 if isinstance(v,(int,float)) and not isinstance(v,bool):ok=isinstance(actual,(int,float)) and not isinstance(actual,bool) and math.isfinite(actual) and abs(actual-v)<=1e-8
 ck('recorded primary '+k,ok)
prov={k:primary[k] for k in keys if re.fullmatch(r'PROV\d+',k)}
ck('complete exact single raw provenance',len(prov)==1 and next(iter(prov.values())).removesuffix('.fits')==p['job']['source_file_ids'][0])
ck('HARPS single high resolution barycentric',primary['INSTRUME']=='HARPS' and primary['NCOMBINE']==1 and primary['SPEC_RES']==115000 and primary['SPECSYS']=='BARYCENT' and primary['ESO INS HEFS ST'] is False)
ck('one-row BINTABLE',extension['XTENSION']=='BINTABLE' and extension['NAXIS']==2 and extension['NAXIS2']==1 and extension['GCOUNT']==1)
names=[extension['TTYPE'+str(i)] for i in range(1,extension['TFIELDS']+1)];ck('valid unique field names',all(isinstance(n,str) and n.strip() for n in names) and len(set(n.strip().casefold() for n in names))==len(names))
fields={n:i for i,n in enumerate(names,1)};ck('wave flux err present',all(n in fields for n in ['WAVE','FLUX','ERR']))
formats=[re.fullmatch(r'([1-9][0-9]*)([BIJKED])',extension['TFORM'+str(fields[n])]) for n in ['WAVE','FLUX','ERR']]
ck('same positive real vector lengths',all(formats) and len({int(z.group(1)) for z in formats if z})==1)
w=fields['WAVE'];fl=fields['FLUX'];ck('air Angstrom WAVE and ADU FLUX',extension['TUNIT'+str(w)].lower()=='angstrom' and 'obs.atmos' in extension['TUCD'+str(w)].lower() and extension['TUNIT'+str(fl)].lower()=='adu')
data_bytes=extension['NAXIS1']*extension['NAXIS2']+extension.get('PCOUNT',0);expected=header_end+((data_bytes+2879)//2880)*2880
ck('file structure exactly primary plus table',expected==product.stat().st_size)
production=read(ACQ/'PAYLOAD_HEADER_VALIDATION.json');ck('production validation matches independent outcome',production['status']=='PASS_COMPATIBLE_HEADERS' and all(production['checks'].values()) and production['new_arrays_interpreted']==0)
out={'schema':'HARPS_MAY_QUALITY_ACTUAL_PAYLOAD_HEADER_AUDIT_V1','status':'PASS' if all(c['pass'] for c in checks) else 'FAIL','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'script_sha256':sha(Path(__file__)),'method':'Manual 2880-byte FITS header block reads plus astropy Header.fromstring; no HDU object/data access. Whole file bytes hashed as opaque bytes only.','manifest_sha256':sha(ACQ/'ACQUISITION_MANIFEST.json'),'payload_sha256':sha(product),'payload_bytes':product.stat().st_size,'primary_header_bytes':primarybytes,'extension_header_bytes':extensionbytes,'array_interpretation_offset_not_read':header_end,'checks':checks,'check_count':len(checks),'representation':{'frame':primary['SPECSYS'],'resolving_power':primary['SPEC_RES'],'pipeline':primary['PROCSOFT'],'berv_km_s':primary['ESO DRS BERV'],'columns':{n:{'format':extension['TFORM'+str(fields[n])],'unit':extension.get('TUNIT'+str(fields[n])),'ucd':extension.get('TUCD'+str(fields[n]))} for n in ['WAVE','FLUX','ERR']}},'network_requests_by_auditor':0,'spectral_arrays_interpreted_by_auditor':0,'scope_limit':'Product identity/representation only; no claim of local continuum quality, line outcome, origin or sensitivity.'}
(HERE/'ACTUAL_PAYLOAD_HEADER_AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k] for k in ['status','check_count','payload_sha256','primary_header_bytes','extension_header_bytes']}));assert out['status']=='PASS'
