"""Narrow actual two-product metadata/release-readiness audit; no network or arrays."""
from pathlib import Path
from html.parser import HTMLParser
import csv,datetime,hashlib,json,math,re,urllib.parse
R=Path(__file__).resolve().parents[2];B=R/'work_harps_20261102_berv_followup';A=B/'science_acquisition';H=B/'header_acquisition_v2';C=B/'prospective_comparison';O=Path(__file__).with_name('SCIENCE_PLAN_AUDIT.json')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
checks=[]
def ck(value,label):
 if not value:raise AssertionError(label)
 checks.append(label)
class Parser(HTMLParser):
 def __init__(self):super().__init__();self.active=False;self.blocks=[];self.parts=[]
 def handle_starttag(self,t,a):
  if t.lower()=='pre':self.active=True;self.parts=[]
  elif t.lower()=='br'and self.active:self.parts.append('\n')
 def handle_endtag(self,t):
  if t.lower()=='pre'and self.active:self.blocks.append(''.join(self.parts));self.active=False
 def handle_data(self,t):
  if self.active:self.parts.append(t)
def main():
 plan=read(A/'PLAN.json');freeze=read(A/'PREFLIGHT_FREEZE.json');phash=sha(A/'PLAN.json');fhash=sha(A/'PREFLIGHT_FREEZE.json')
 ck(phash=='98842cd2aa09685fa9565a09dcdff3960ea972e9b220a1f701efb870c2da547a','Root-specified actual science plan hash')
 ck(fhash=='d429fdc8c5f9f52865a85bf0a1f84310a1f19cd45fbc8d7689e605b3e64b2ec4','Root-specified24-file freeze hash')
 ck(len(freeze['files'])==24,'Exactly24 frozen files')
 for rel,entry in freeze['files'].items():
  p=R/rel;ck(p.stat().st_size==entry['bytes']and sha(p)==entry['sha256'],'Frozen source '+rel)
 for key in ['selection','header_results','comparison_plan','direct_file_contract']:ck(sha(R/plan[key+'_path'])==plan[key+'_sha256'],'Plan hash link '+key)
 selection=read(R/plan['selection_path']);headers=read(R/plan['header_results_path']);hplan=read(H/'PLAN.json');contract=read(R/plan['direct_file_contract_path']);old=list(csv.DictReader((R/'work_harps_20261101/v2/extension02/next_followup_20261102/EXISTING_TARGET_EXPOSURES.csv').open()))
 ck(selection['header_results_sha256']==sha(H/'HEADER_RESULTS.json')and selection['header_plan_sha256']==headers['plan_sha256']==sha(H/'PLAN.json'),'Selection/results/header-plan crossbinding')
 ck(headers['status']=='COMPLETE'and headers['requests_attempted']==len(headers['results'])==len(hplan['jobs'])==2,'Exactly two completed planned headers')
 ids=['ADP.2017-05-23T01:01:52.459','ADP.2018-01-21T01:01:37.761'];ck([r['dp_id']for r in plan['inputs']]==ids,'Exact expected two products in min/max order')
 ck([(r['target'],r['dp_id'])for r in plan['inputs']]==[(r['target'],r['dp_id'])for r in selection['selected']],'Acquisition slots equal prospective selection')
 ck(all(r['target']=='HD122640'for r in plan['inputs']),'Only HD122640 selected')
 ck(len({r['dp_id']for r in headers['results']})==2,'Unique header identities')
 records=[];total=0
 for row,sel in zip(plan['inputs'],selection['selected']):
  h=next(h for h in headers['results']if h['dp_id']==row['dp_id']);job=next(j for j in hplan['jobs']if j['job_index']==h['job_index']);ins=h['inspection'];body=H/h['body_path'];receiptpath=H/h['receipt_path'];rec=read(receiptpath)
  ck(ins['status']==h['status']=='PASS_RECORDED_BERV'and not ins['failures']and all(ins['checks'].values()),'Passing recorded identity '+row['dp_id'])
  ck(sha(body)==h['body_sha256']==sel['header_body_sha256']and sha(receiptpath)==h['receipt_sha256']==sel['header_receipt_sha256'],'Body/receipt hashes '+row['dp_id'])
  ck(rec['body_sha256']==sha(body)and rec['bytes_saved']==body.stat().st_size and rec['plan_sha256']==sha(H/'PLAN.json'),'Receipt body and plan binding '+row['dp_id'])
  ck(rec['complete']is True and rec['http_status']==200 and rec['attempts']==1 and rec['retries']==rec['redirects_followed']==0,'Bounded successful header receipt '+row['dp_id'])
  ck(body.stat().st_size<rec['effective_byte_cap']<=hplan['limits']['max_response_bytes'],'Header response below cap '+row['dp_id']);total+=body.stat().st_size
  ck(rec['dp_id']==job['dp_id']==row['dp_id']and rec['url']==job['url']and rec['job_index']==sel['header_result_job_index']==h['job_index'],'Exact request/job/header identity '+row['dp_id'])
  parser=Parser();parser.feed(body.read_text());primary=[]
  for block in parser.blocks:
   lines=block.splitlines()
   for start in [i for i,line in enumerate(lines)if re.match(r'^SIMPLE\s*=',line)]:
    end=next(i for i in range(start,len(lines))if lines[i].strip()=='END');primary.append(lines[start:end])
  ck(len(primary)==1,'One independently scoped primary block '+row['dp_id'])
  def token(key):
   found=[line.split('=',1)[1].split('/',1)[0].strip()for line in primary[0]if re.match('^'+re.escape(key)+r'\s*=',line)];ck(len(found)==1,'Unique primary card '+key+' '+row['dp_id']);return found[0]
  berv=float(token('HIERARCH ESO DRS BERV'));ck(math.isfinite(berv)and abs(berv)<=100 and berv==ins['berv_km_s']==sel['berv_km_s']==row['berv_km_s'],'Recorded BERV distinct from BERVMX '+row['dp_id'])
  ck(token('ARCFILE').strip("'")==row['dp_id']+'.fits','Primary ADP identity '+row['dp_id'])
  ck(token('SPECSYS').strip("'")=='BARYCENT'and token('INSTRUME').strip("'")=='HARPS','Primary HARPS barycentric frame '+row['dp_id'])
  ck(float(token('NCOMBINE'))==1 and float(token('SPEC_RES'))==115000 and token('HIERARCH ESO INS HEFS ST')=='F','Primary single-exposure high-resolution mode '+row['dp_id'])
  ck(row['source_file_ids']==sel['source_file_ids']==ins['raw_progenitor_ids']and len(row['source_file_ids'])==1,'Exact single raw provenance '+row['dp_id'])
  ck(row['dp_id']not in {x['dp_id']for x in old}and row['source_file_ids'][0]not in {x['raw_progenitor_id'].removesuffix('.fits')for x in old},'Distinct from existing300 ADP/raw identities '+row['dp_id'])
  ck(row['metadata_access_url']==sel['metadata']['access_url']==job['metadata']['access_url'],'Original DataLink metadata identity retained '+row['dp_id'])
  ck(row['source_url']==contract['direct_url_prefix']+row['dp_id'],'Documented canonical direct-file URL '+row['dp_id'])
  url=urllib.parse.urlsplit(row['source_url']);ck(url.scheme=='https'and url.hostname=='dataportal.eso.org'and not url.query and not url.fragment and not url.username,'Exact public file endpoint '+row['dp_id'])
  dest=(R/row['local_path']).resolve();ck(dest.is_relative_to(A/'products')and not dest.exists(),'Unused intended product path '+row['dp_id'])
  records.append({'dp_id':row['dp_id'],'target':row['target'],'raw_progenitor_id':row['source_file_ids'][0],'berv_km_s':berv,'body_sha256':sha(body),'receipt_sha256':sha(receiptpath),'prospective_source_url':row['source_url']})
 ck(total==headers['response_bytes']==455347,'Complete exact header byte accounting')
 bytarget={}
 for target in ['HD122640','HD135204']:
  eligible=[h for h in headers['results']if h['target']==target and h['inspection']['status']=='PASS_RECORDED_BERV'];expected=[]
  if eligible:
   low=min(eligible,key=lambda h:(h['inspection']['berv_km_s'],h['dp_id']));high=min(eligible,key=lambda h:(-h['inspection']['berv_km_s'],h['dp_id']));expected=[low['dp_id']]+([]if high['dp_id']==low['dp_id']else[high['dp_id']])
  existing=[float(r['berv_km_s'])for r in old if r['target']==target];new=[h['inspection']['berv_km_s']for h in eligible];combined=max(existing+new)-min(existing+new);gate=combined>299792.458/115000;got=selection['target_summary'][target]
  ck(got['combined_span_km_s']==combined and got['payload_readiness_gate_passed']==gate,'Independent span and readiness '+target)
  ck([r['dp_id']for r in plan['inputs']if r['target']==target]==(expected if gate else []),'Independent min/max/tie/readiness selection '+target)
  bytarget[target]={'existing_exposures':len(existing),'passing_new_headers':len(eligible),'selected_epochs':len(expected)if gate else 0,'combined_span_km_s':combined,'combined_resolution_elements':combined/299792.458*115000,'readiness_passed':gate}
 ck(abs(bytarget['HD122640']['combined_span_km_s']-40.3634787209574)<1e-12,'HD122640 exact40.3634787209574km/s span')
 ck(selection['payload_readiness_gate']['combined_span_km_s_threshold']==hplan['payload_readiness_gate']['combined_span_km_s_threshold']==299792.458/115000,'Inherited c/R planning threshold')
 ck(plan['limits']=={'requests':2,'attempts_per_product':1,'timeout_seconds_per_product':60,'response_bytes_per_product':16777216,'total_payload_bytes_upper_bound':33554432,'redirects':0,'retries':0,'first_failure_stops_remaining_jobs':True},'Exact2 requests/1attempt/60s/16MiB each/32MiB total bounds')
 comparison=read(C/'PLAN.json');events=read(C/'EVENTS.json');ck(comparison['events']==10 and comparison['discovery_reference_profiles']==20,'Fixed10events20references')
 ck(sum(e['target']=='HD122640'for e in events)==6 and sum(e['target']=='HD135204'for e in events)==4,'Six covered and four no-new-epoch event records')
 slots=2*sum(sum(e['target']==r['target']for e in events)for r in plan['inputs']);ck(slots==24,'Exactly24 prospective event/epoch/frame slots')
 for name,source,key in [('COMPARISON_AUDIT.json',C/'compare_verified_epochs.py','comparison_script_sha256'),('TRANSPORT_AUDIT.json',A/'download_inputs.py','script_sha256')]:ck(read(B/'comparison_independent_audit'/name)[key]==sha(source),'Previously audited executor unchanged '+name)
 ck(not(A/'RUN_STARTED.json').exists()and not(C/'results').exists(),'No acquisition/comparison run at audit')
 ck(sha(A/'PLAN.json')==phash and sha(A/'PREFLIGHT_FREEZE.json')==fhash,'Frozen actual plan unchanged throughout audit')
 report={'status':'PASS_ACTUAL_TWO_INPUT_SCIENCE_PLAN_AUDIT','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks_passed':len(checks),'check_labels':checks,'science_plan_sha256':phash,'preflight_freeze_sha256':fhash,'frozen_files_verified':24,'comparison_plan_sha256':sha(C/'PLAN.json'),'comparison_script_sha256':sha(C/'compare_verified_epochs.py'),'download_script_sha256':sha(A/'download_inputs.py'),'selected_inputs':records,'target_readiness':bytarget,'prospective_frame_slots':slots,'events_with_selected_new_epochs':6,'events_without_selected_new_epochs':4,'network_requests':0,'new_science_arrays_read':0,'existing_frozen_audit_files_modified':False,'publication_release_verified':False,'audit_script_sha256':sha(Path(__file__)),'limitations':['Readiness for root-controlled publication/release only, not a payload download or comparison result.','Actual acquired bytes and primary/extension WAVE air-Angstrom, ADU FLUX and table compatibility remain mandatory before arrays.','40.363km/s span is a planning displacement, not sensitivity, significance, origin proof or survey coverage.']}
 with O.open('x')as stream:json.dump(report,stream,indent=2);stream.write('\n')
 print(json.dumps({k:v for k,v in report.items()if k!='check_labels'},indent=2))
if __name__=='__main__':main()
