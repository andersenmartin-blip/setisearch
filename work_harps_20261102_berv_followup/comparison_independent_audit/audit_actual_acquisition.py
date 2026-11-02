"""Actual acquired bytes/receipts and FITS headers only; no .data access."""
from pathlib import Path
import datetime,hashlib,json,math,re
from astropy.io import fits
R=Path(__file__).resolve().parents[2];B=R/'work_harps_20261102_berv_followup';A=B/'science_acquisition';O=Path(__file__).with_name('ACTUAL_ACQUISITION_HEADER_AUDIT.json')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
checks=[]
def ck(v,n):
 if not v:raise AssertionError(n)
 checks.append(n)
def main():
 manifest=read(A/'ACQUISITION_MANIFEST.json');plan=read(A/'PLAN.json');release=read(A/'ROOT_RELEASE.json');pub=read(A/'PUBLICATION_RECEIPT.json');freeze=read(A/'PREFLIGHT_FREEZE.json');header=read(R/plan['header_results_path'])
 ck(manifest['status']=='COMPLETE'and len(manifest['inputs'])==2,'Both selected downloads complete')
 ck(manifest['plan_sha256']==sha(A/'PLAN.json'),'Actual manifest plan hash')
 ck(release['freeze_sha256']==sha(A/'PREFLIGHT_FREEZE.json')and release['remote_bytes_verified']is True,'Root release exact frozen inputs')
 ck(pub['status']=='PASS_EXACT_REMOTE_READBACK'and pub['commit']==release['prospective_commit']=='aae61901226d9329be8f8ce333066fa7c9b85954'and pub['tree']==release['verified_tree'],'Published commit/tree attestation bound')
 ck(release['verified_files']==len(pub['files'])==38,'Exactly38 remote-readback file attestations')
 for rel,e in freeze['files'].items():
  p=R/rel;ck(p.stat().st_size==e['bytes']and sha(p)==e['sha256'],'Frozen input unchanged '+rel)
 ck([(x['target'],x['dp_id'])for x in manifest['inputs']]==[(x['target'],x['dp_id'])for x in plan['inputs']],'All selected slots/order exactly retained')
 evidence=[]
 for entry,planned in zip(manifest['inputs'],plan['inputs']):
  p=R/entry['local_path'];receiptpath=R/entry['acquisition_receipt_path'];receipt=read(receiptpath);transport=receipt['transport'];record=next(h for h in header['results']if h['dp_id']==entry['dp_id'])['inspection']['primary_header']
  ck(entry['status']==receipt['status']=='COMPLETE'and receipt['curl_returncode']==0,'Successful download '+entry['dp_id'])
  ck(receipt['attempt']==1 and transport['http_code']==200 and transport['num_redirects']==0,'HTTP200 first attempt without redirects '+entry['dp_id'])
  ck(transport['url_effective']==receipt['source_url']==entry['source_url']==planned['source_url'],'Exact effective public URL '+entry['dp_id'])
  ck(sha(receiptpath)==entry['acquisition_receipt_sha256'],'Acquisition receipt hash '+entry['dp_id'])
  ck(p.stat().st_size==entry['bytes']==receipt['bytes']==transport['size_download']==5264640 and p.stat().st_size<16777216,'Exact bounded payload bytes '+entry['dp_id'])
  ck(sha(p)==entry['sha256']==receipt['sha256'],'Actual payload SHA256 '+entry['dp_id'])
  ck(transport['time_total']<=60 and receipt['new_arrays_interpreted']==0,'Bounded time/no acquisition array interpretation '+entry['dp_id'])
  command=receipt['command']
  for flag,value in [('--max-redirs','0'),('--retry','0'),('--max-time','60'),('--max-filesize','16777216')]:ck(command[command.index(flag)+1]==value,'Recorded transport bound '+flag+' '+entry['dp_id'])
  with fits.open(p,memmap=True,lazy_load_hdus=False)as hd:
   ck(len(hd)>=2,'Primary plus spectral extension headers '+entry['dp_id']);ph=hd[0].header;eh=hd[1].header
   for key,value in record.items():
    actual=ph.get(key.removeprefix('HIERARCH '))
    equal=(not isinstance(actual,bool)and isinstance(actual,(int,float))and math.isfinite(actual)and abs(actual-value)<=1e-8)if isinstance(value,(int,float))and not isinstance(value,bool)else actual==value
    ck(equal,'Recorded header exact '+key+' '+entry['dp_id'])
   ck(ph['ARCFILE']==entry['dp_id']+'.fits'and re.sub('[^A-Z0-9]','',ph['OBJECT'].upper())==entry['target'],'Payload exact product/target '+entry['dp_id'])
   ck(ph['INSTRUME']=='HARPS'and ph['SPECSYS']=='BARYCENT'and ph['SPEC_RES']==115000 and ph['ESO INS HEFS ST']is False,'Payload required representation '+entry['dp_id'])
   ck(ph['NCOMBINE']==1 and not isinstance(ph['NCOMBINE'],bool),'Payload single exposure '+entry['dp_id'])
   names=[eh['TTYPE'+str(i)]for i in range(1,eh['TFIELDS']+1)];ck(len(names)==len(set(n.casefold()for n in names))and all(n.strip()for n in names),'Unique nonempty spectral field names '+entry['dp_id'])
   ck(all(n in names for n in ['WAVE','FLUX','ERR'])and eh['NAXIS2']==1,'One-row WAVE/FLUX/ERR table '+entry['dp_id'])
   cols={n:i+1 for i,n in enumerate(names)};wu=eh.get('TUNIT'+str(cols['WAVE']));fu=eh.get('TUNIT'+str(cols['FLUX']));eu=eh.get('TUNIT'+str(cols['ERR']));ucd=eh.get('TUCD'+str(cols['WAVE']))
   ck(wu.lower()=='angstrom'and fu.lower()=='adu'and 'obs.atmos'in ucd,'Air-Angstrom WAVE and ADU FLUX '+entry['dp_id'])
   ck(all('data' not in hdu.__dict__ for hdu in hd),'No HDU data property materialized during header audit '+entry['dp_id'])
   evidence.append({'dp_id':entry['dp_id'],'bytes':entry['bytes'],'sha256':entry['sha256'],'date_obs':ph['DATE-OBS'],'berv_km_s':ph['ESO DRS BERV'],'processing_software':ph['PROCSOFT'],'pipeline_difference_from_original_HARPS_3_8':ph['PROCSOFT']!='HARPS_3.8','instrument_mode':ph.get('ESO INS MODE'),'HEFS':ph['ESO INS HEFS ST'],'spectral_columns':names,'wavelength_unit':wu,'flux_unit':fu,'error_unit':eu,'wavelength_ucd':ucd,'table_rows':eh['NAXIS2'],'new_array_read':False})
 ck(sum(x['bytes']for x in manifest['inputs'])==manifest['bytes_saved']==10529280,'Exact two-product total bytes')
 ck(manifest['new_arrays_interpreted']==manifest['original_labels_changed']==0 and manifest['original_survey_exposures']==300,'No acquisition label or survey changes')
 report={'status':'PASS_ACTUAL_ACQUISITION_AND_HEADER_ONLY_COMPATIBILITY','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks_passed':len(checks),'check_labels':checks,'manifest_sha256':sha(A/'ACQUISITION_MANIFEST.json'),'root_release_sha256':sha(A/'ROOT_RELEASE.json'),'publication_commit':release['prospective_commit'],'products':evidence,'network_requests':0,'new_science_arrays_read':0,'independent_production_function_imports':0,'audit_script_sha256':sha(Path(__file__)),'limits':['Header compatibility is established, but no new numeric profile has been evaluated by this audit.','A separate root comparison release/run is still required before the independent numerical audit reads science arrays.','Remote publication evidence is the preserved root readback attestation, not a new remote request by this audit.']}
 with O.open('x')as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps({k:v for k,v in report.items()if k!='check_labels'},indent=2))
if __name__=='__main__':main()
