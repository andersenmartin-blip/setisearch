"""Independent saved-header failure and empty-extrema audit, no requests."""
from pathlib import Path
import datetime,hashlib,json,re
from html.parser import HTMLParser
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];H=OUT.parent/'header_acquisition'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=read(H/'PLAN.json');release=read(H/'ROOT_RELEASE.json');results=read(H/'HEADER_RESULTS.json');selection=read(H/'EXTREME_SELECTION.json');checks=[]
def check(label,value):
    assert value,label
    checks.append(label)
check('Exact reviewed header plan',sha(H/'PLAN.json')==release['plan_sha256']==results['plan_sha256']=='28d9ce9d78a288c72c6a4a6e0ebcb4b6c17108eeaecd4dbee6fdc53b81b40dac')
check('Published exact-byte release',release['approved'] is True and release['remote_bytes_verified'] is True and release['prospective_commit']=='e6b2b790fd8e6e505216a22ef52f8426348b7ddf')
check('Release hash preserved',sha(H/'ROOT_RELEASE.json')==results['root_release_sha256'])
for name,digest in plan['code_hashes'].items():check('Frozen header code unchanged '+name,sha(H/name)==digest==results['code_hashes'][name])
for item in plan['inputs']:check('Frozen input unchanged '+item['path'],sha(ROOT/item['path'])==item['sha256'])
check('Exactly two accounted jobs',[r['job_index'] for r in results['results']]==[0,1] and [r['dp_id'] for r in results['results']]==[r['dp_id'] for r in plan['jobs']])
check('One canary only attempted',results['requests_attempted']==1 and len(list((H/'receipts').glob('*.json')))==1 and len(list((H/'responses').glob('*.body')))==1)
first,second=results['results'];receipt=read(H/first['receipt_path']);body=(H/first['body_path']).read_bytes()
check('Exact saved body hash',sha(H/first['body_path'])==first['body_sha256']==receipt['body_sha256'])
check('Exact saved receipt hash',sha(H/first['receipt_path'])==first['receipt_sha256'])
check('Exact endpoint and job identity',receipt['url']==plan['jobs'][0]['url'] and receipt['dp_id']==plan['jobs'][0]['dp_id'] and receipt['target']=='HD122640')
check('One bounded no-redirect attempt',receipt['attempts']==1 and receipt['retries']==0 and receipt['redirects_followed']==0 and receipt['elapsed_seconds']<=30)
check('Transport complete but content invalid',receipt['http_status']==200 and receipt['complete'] is True and receipt['error'] is None)
check('2639bytes under both caps',len(body)==receipt['bytes_saved']==results['response_bytes']==2639 and len(body)<524288 and results['response_bytes']<12582912)
check('Root release preceded request',datetime.datetime.fromisoformat(release['verified_utc'])<datetime.datetime.fromisoformat(receipt['started_utc']))
class Collector(HTMLParser):
    def __init__(self):super().__init__();self.in_pre=False;self.blocks=[];self.current=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower()=='pre':self.in_pre=True;self.current=[]
    def handle_endtag(self,tag):
        if tag.lower()=='pre':self.blocks.append(''.join(self.current));self.in_pre=False
    def handle_data(self,text):
        if self.in_pre:self.current.append(text)
parser=Collector();parser.feed(body.decode('utf-8'));parser.close()
expected='Invalid format for dp_id ADP.2018-01-21T01%3A01%3A37.761'
check('Provider explicit encoded-ID rejection',parser.blocks==[expected])
check('No primary FITS cards or BERV returned',not re.search(r'^SIMPLE\s*=',body.decode(),re.M) and 'HIERARCH ESO DRS BERV' not in body.decode())
check('Parser correctly refused error HTML',first['status']=='UNRECOGNIZED_HEADER_RESPONSE' and first['reason']=='Expected exactly one primary SIMPLE block')
check('Canary stops May request',second['status']=='NOT_REQUESTED_BATCH_STOPPED' and second['reason']=='HEADER_FORMAT_FAILURE')
check('Correct stopped batch status',results['status']=='COMPLETE_WITH_STOP' and results['stop_reason']=='HEADER_FORMAT_FAILURE')
check('No science payload read claim',results['spectral_arrays_requested_or_read'] is False)
check('Selection bound to exact failed result',selection['header_results_sha256']==sha(H/'HEADER_RESULTS.json') and selection['header_plan_sha256']==sha(H/'PLAN.json'))
check('No extrema or payload proposals',selection['selected']==[] and selection['spectral_payload_acquisition_authorized'] is False)
check('Partial sampling explicit',selection['header_sampling_is_partial'] is True and selection['all_planned_jobs_attempted'] is False)
for target,summary in selection['target_summary'].items():
    old=plan['existing_berv_benchmark'][target];span=old['maximum_berv_km_s']-old['minimum_berv_km_s']
    check('Zero verified new headers '+target,summary['verified_headers']==0 and summary['recorded_berv_span_km_s'] is None and summary['selected_epochs']==0 and summary['candidate_extreme_dp_ids']==[])
    check('Only unchanged existing BERV span reported '+target,summary['combined_span_km_s']==span and summary['combined_span_increase_km_s']==0 and summary['combined_span_resolution_elements_R115000']==span/(299792.458/115000))
    check('No payload-readiness gate passed '+target,summary['payload_readiness_gate_passed'] is False and summary['extends_existing_range'] is False)
report={'status':'PASS_SAFE_STOP_WITH_HEADER_URL_CONTRACT_FAILURE','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'checks_passed':len(checks),'checks':checks,'requests_attempted':1,'unrequested_jobs':1,'http_status':200,'response_bytes':len(body),
        'archive_message':expected,'verified_primary_headers':0,'recorded_new_BERV_values':0,'payload_proposals':0,
        'interpretation':'The legacy header-display endpoint rejected the percent-encoded identifier as invalid. Its HTML error page contains no FITS header, astrometric evidence or BERV. The canary stop was correctly enforced; this does not show absence of useful BERV coverage.',
        'preflight_limit':'Mocked transport/parser review did not establish whether the legacy endpoint decoded colons. The actual failure is preserved and is not converted into a scientific result.',
        'root_amendment_decision':'Root subsequently authorized a separate header_acquisition_v2 with literal-colon URL serialization only, same two jobs/parser/criteria/caps, one attempt each, and at most3totalheaderrequests including this failed canary. A separate prospective publication/release is required.',
        'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in [H/'PLAN.json',H/'ROOT_RELEASE.json',H/'HEADER_RESULTS.json',H/'EXTREME_SELECTION.json',H/first['body_path'],H/first['receipt_path']]},
        'auditor_script_sha256':sha(Path(__file__)),'network_requests_by_audit':0,'production_header_parser_imported':False,'science_arrays_read':0,'labels_changed':0}
(OUT/'HEADER_RESULT_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'checks_passed':len(checks),'verified_headers':0,'new_BERV_values':0}))
