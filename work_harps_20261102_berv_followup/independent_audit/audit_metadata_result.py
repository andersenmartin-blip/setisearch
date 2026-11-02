"""Independent examination of the first saved metadata response; no requests."""
from pathlib import Path
import datetime,hashlib,json,urllib.parse,xml.etree.ElementTree as ET
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];M=OUT.parent/'metadata_search'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=read(M/'PLAN.json');summary=read(M/'SUMMARY.json');release=read(M/'ROOT_RELEASE.json');freeze=read(M/'PREFLIGHT_FREEZE.json');checks=[]
def check(label,condition):
    assert condition,label
    checks.append(label)
check('Exact prospective freeze released',release['freeze_sha256']==sha(M/'PREFLIGHT_FREEZE.json')=='0c4777125917f2dd8076ea663582acd15316cad96abc92a56abe5e666b83c005')
check('Published prospective commit recorded',release['prospective_commit']=='234562d3619ea894bfd4c8a9b58e7dd002f6f2e8' and release['remote_bytes_verified'] is True)
for name,record in freeze['files'].items():check('Frozen input unchanged '+name,sha(M/name)==record['sha256'] and (M/name).stat().st_size==record['bytes'])
for name,digest in plan['source_hashes'].items():check('Historical source unchanged '+name,sha(ROOT/name)==digest)
markers=list(M.glob('*.ATTEMPT_STARTED.json'));check('Exactly one attempted target',[p.name for p in markers]==['HD122640.ATTEMPT_STARTED.json'])
check('Second target never started',not(M/'HD135204.ATTEMPT_STARTED.json').exists() and not list((M/'responses').glob('HD135204*')))
request=plan['requests'][0];receipt=read(M/'responses/HD122640.REQUEST.json');stats=read(M/'responses/HD122640.curl.json')
query=(M/request['query_file']).read_bytes();form={**request['form'],'QUERY':query.decode()};body=urllib.parse.urlencode(form).encode()
check('Exact request body length',len(body)==receipt['request_body_bytes'])
check('Exact request body hash',hashlib.sha256(body).hexdigest()==receipt['request_body_sha256'])
check('Exact frozen query hash',sha(M/request['query_file'])==receipt['query_sha256'])
check('Exact endpoint and single POST',receipt['endpoint']=='https://archive.eso.org/tap_obs/sync' and receipt['method']=='POST' and receipt['attempt']==1)
check('Recorded curl diagnostics identical',stats==receipt['transport'])
check('No redirects',stats['num_redirects']==0 and stats['url_effective']==request['endpoint'])
check('Transport completed within30seconds',stats['time_total']<=30)
response=M/'responses/HD122640.vot';raw=response.read_bytes()
check('Exact preserved response bytes',len(raw)==receipt['response_bytes']==stats['size_download']==370)
check('Exact preserved response hash',sha(response)==receipt['response_sha256'])
check('Response below4MiB cap',len(raw)<4194304)
check('Observed HTTP400 transport succeeded',receipt['curl_returncode']==0 and stats['http_code']==400)
xml=ET.fromstring(raw);status=[(e.attrib.get('value'),(e.text or '').strip()) for e in xml.iter() if e.tag.split('}')[-1]=='INFO' and e.attrib.get('name')=='QUERY_STATUS']
check('Archive explicit query error',len(status)==1 and status[0][0]=='ERROR')
check('No astronomical result table',not any(e.tag.split('}')[-1]=='TABLE' for e in xml.iter()))
check('Correct failed-request disposition',receipt['status']=='STOPPED_REQUEST_FAILURE')
check('Main route stopped after first failure',summary['status']=='STOPPED_BOUNDED_METADATA' and summary['target_requests']==1 and summary['request_statuses']==['STOPPED_REQUEST_FAILURE'])
check('No astronomical records or candidates inferred',summary['returned_products']==summary['metadata_candidates']==0 and read(M/'CANDIDATES.json')==read(M/'ALL_RETURNED_PRODUCTS.json')==[])
check('No normalized rows or classifications manufactured',not list((M/'responses').glob('*.ROWS.json')) and not list((M/'responses').glob('*.INVENTORY.json')))
check('No BERV or science payload claim',summary['science_payload_bytes']==0 and summary['berv_not_measured'] is True and receipt['science_payload_requested'] is False)
report={'status':'PASS_SAFE_STOP_WITH_QUERY_CONTRACT_FAILURE','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'checks_passed':len(checks),'checks':checks,'observed_http_status':400,'response_bytes':len(raw),'transport_seconds':stats['time_total'],
        'query_status':status,'targets_attempted':['HD122640'],'targets_not_attempted':['HD135204'],
        'astronomical_records_received':0,'metadata_classifications_performed':0,'science_arrays_read':0,'network_requests_by_audit':0,
        'scientific_conclusion':'No statement about availability of new epochs is supported: the first query failed syntactically before returning an astronomical table.',
        'failure_diagnosis':'The error context (dot where end/comma/ASC/DESC expected) points to qualified ORDER BY references. This is an inference from the server error, not a separately tested archive query.',
        'preflight_limit':'Static schema and mocked runtime review did not detect this remote ADQL ordering-syntax incompatibility. The failure remains preserved; this audit does not recast it as an empty astronomical result.',
        'root_amendment_decision':'After reviewing this failure, root explicitly authorized a separate metadata_search_v2 with only unqualified ORDER BY t_min,dp_id,source_file, at most two new one-attempt requests and total continuation cap three including this failed request. Original route remains stopped and immutable; publication/release required again.',
        'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in [M/'PLAN.json',M/'PREFLIGHT_FREEZE.json',M/'ROOT_RELEASE.json',M/'SUMMARY.json',M/'responses/HD122640.REQUEST.json',response,M/'CANDIDATES.json',M/'ALL_RETURNED_PRODUCTS.json']},
        'auditor_script_sha256':sha(Path(__file__))}
(OUT/'RESULT_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'checks_passed':len(checks),'target_requests':1,'http_status':400,'bytes':370}))
