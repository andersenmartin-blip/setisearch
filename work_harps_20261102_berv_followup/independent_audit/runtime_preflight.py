"""Network-free parser, classification, transport and release-boundary audit."""
from pathlib import Path
import copy,datetime,hashlib,importlib.util,io,json,subprocess,tempfile
from unittest.mock import patch
from astropy.io.votable import from_table,writeto
from astropy.table import Table

OUT=Path(__file__).resolve().parent;M=OUT.parent/'metadata_search';ROOT=OUT.parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
plan=json.loads((M/'PLAN.json').read_text());targets=json.loads((M/'TARGETS.json').read_text());known=json.loads((M/'EXISTING_300.json').read_text())
spec=importlib.util.spec_from_file_location('reviewed_metadata_search',M/'search_metadata.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
checks=[]
def check(name,value):
    assert value,name
    checks.append(name)
check('No target execution yet',not(M/'RUN_STARTED.json').exists() and not(M/'responses').exists())
check('Prior state baseline passed',json.loads((OUT/'STATE_BASELINE_AUDIT.json').read_text())['status'].startswith('PASS'))
check('Query contract passed',json.loads((OUT/'QUERY_CONTRACT_AUDIT.json').read_text())['status'].startswith('PASS'))
check('Query contract bound to current plan',json.loads((OUT/'QUERY_CONTRACT_AUDIT.json').read_text())['plan_sha256']==sha(M/'PLAN.json'))
check('Target provenance audit passed',json.loads((OUT/'TARGET_PROVENANCE_AUDIT.json').read_text())['status'].startswith('PASS'))

columns=plan['requests'][0]['expected_columns'];target=targets[0]
base={key:'' for key in columns}
base.update(dp_id='ADP.2008-01-03T01:02:03.001',obs_publisher_did='ivo://eso.org/ID?ADP.2008-01-03T01:02:03.001',obs_id='123',target_name='HD 122640',s_ra=target['ra_deg'],s_dec=target['dec_deg'],instrument_name='HARPS',obs_collection='HARPS',dataproduct_type='spectrum',t_min=54467.,t_max=54467.+30/86400,t_exptime=30.,n_obs=1,multi_ob='S',obs_release_date='2009-01-01T00:00:00Z',archive_id='ADP.2008-01-03T01:02:03.001',eso_category='SCIENCE.SPECTRUM',source_file='HARPS.2008-01-02T00:00:00.000',access_url='https://invalid.example.test/NEVER_FETCH_SPECTRUM')
def candidate(row):return mod.classify([row],target,known)[0]['status'].startswith('METADATA_CANDIDATE')
check('Valid metadata only candidate',candidate(base))
for name,update in [
    ('RA NaN',{'s_ra':'nan'}),('RA outside range',{'s_ra':target['ra_deg']+360}),('Dec outside range',{'s_dec':target['dec_deg']+360}),
    ('Missing coordinate',{'s_ra':None}),('Outside identity cone',{'s_dec':target['dec_deg']+1}),
    ('Wrong canonical target',{'target_name':'HD 135204'}),('Nonfinite exposure',{'t_exptime':'nan'}),('Zero exposure',{'t_exptime':0}),
    ('Fractional observation count',{'n_obs':1.2}),('Multiple observations',{'n_obs':2}),('Multiple OBs',{'multi_ob':'M'}),
    ('Nonpositive observation duration',{'t_max':54466}),('Excluded calendar interval',{'t_min':59995.,'t_max':59995.1}),
    ('Straddles excluded interval start',{'t_min':59993.99,'t_max':59994.01}),
    ('Wrong instrument',{'instrument_name':'FEROS'}),('Wrong collection',{'obs_collection':'OTHER'}),('Wrong product type',{'dataproduct_type':'image'}),
    ('Missing raw provenance',{'source_file':None}),('NonHARPS provenance',{'source_file':'UVES.2008-01-02T00:00:00.000'}),
    ('Old raw progenitor',{'source_file':known[0]['raw_progenitor_ids'][0]+'.fits'}),
    ('Future proprietary release',{'obs_release_date':'2027-01-01T00:00:00Z'}),('Missing release',{'obs_release_date':None}),
    ('Non-science category',{'eso_category':'ANCILLARY.SPECTRUM'})]:
    check('Reject '+name,not candidate({**base,**update}))
check('Exposure ending exactly at excluded start is outside',candidate({**base,'t_min':59993.99,'t_max':59994.}))
check('Exposure beginning exactly at excluded end is outside',candidate({**base,'t_min':60005.,'t_max':60005.01}))
check('Exposure straddling excluded end is excluded',not candidate({**base,'t_min':60004.99,'t_max':60005.01}))
old=known[0]['raw_progenitor_ids'][0]
group=mod.classify([base,{**base,'source_file':old}],target,known)[0]
check('Entire product rejects any old progenitor in joined group','existing_raw_progenitor' in group['reasons'] and not group['status'].startswith('METADATA_CANDIDATE'))
group=mod.classify([base,{**base,'source_file':'HARPS.2008-01-03T00:00:00.000'}],target,known)[0]
check('Multiple new raw progenitors excluded','missing_or_ambiguous_raw_provenance' in group['reasons'])
group=mod.classify([base,{**base,'target_name':'HD 135204'}],target,known)[0]
check('Conflicting product metadata excluded','inconsistent_product_metadata' in group['reasons'])
other={**base,'dp_id':'ADP.2008-01-03T01:02:03.002','archive_id':'ADP.2008-01-03T01:02:03.002'}
dups=mod.classify([other,base],target,known)
check('Repeated new raw kept once by lexical DP ID',[r['dp_id'] for r in dups if r['status'].startswith('METADATA_CANDIDATE')]==[base['dp_id']])

def votable(records):
    table=Table(rows=[[str(r.get(k,'')) for k in columns] for r in records],names=columns,dtype=['U150']*len(columns))
    buf=io.BytesIO();writeto(from_table(table),buf)
    return buf.getvalue().replace(b'<RESOURCE type="results">',b'<RESOURCE type="results"><INFO name="QUERY_STATUS" value="OK"/>')
good=votable([base]);empty=votable([])
check('Valid metadata VOTable parser',len(mod.parse_votable(good,columns)[0])==1)
check('Empty valid VOTable parser',mod.parse_votable(empty,columns)[0]==[])
def parser_reject(name,body):
    try:mod.parse_votable(body,columns)
    except Exception:check(name,True)
    else:check(name,False)
parser_reject('Overflow status rejected',good.replace(b'value="OK"',b'value="OVERFLOW"'))
parser_reject('Missing status rejected',good.replace(b'<INFO name="QUERY_STATUS" value="OK"/>',b''))
parser_reject('Trailing error status rejected',good.replace(b'</RESOURCE>',b'<INFO name="QUERY_STATUS" value="ERROR">failure</INFO></RESOURCE>'))
parser_reject('DTD rejected',b'<!DOCTYPE VOTABLE>'+good)
parser_reject('Entity declaration rejected',b'<!ENTITY unsafe SYSTEM "https://invalid.example.test/never">'+good)
parser_reject('External stream rejected',b'<VOTABLE><RESOURCE><INFO name="QUERY_STATUS" value="OK"/><TABLE><DATA><BINARY><STREAM href="https://invalid.example.test/never"/></BINARY></DATA></TABLE></RESOURCE></VOTABLE>')
parser_reject('Exact1000 row cap rejected',votable([base]*1000))
parser_reject('Column contract mismatch rejected',good.replace(b'name="snr"',b'name="unrequested_spectrum"'))

def exercise_transport(name,returncode=0,http=200,body=good,redirects=0,timeout=False):
    with tempfile.TemporaryDirectory(prefix='transport_',dir=OUT) as directory:
        mod.HERE=Path(directory);(mod.HERE/'responses').mkdir()
        req=plan['requests'][0]
        (mod.HERE/req['query_file']).write_bytes((M/req['query_file']).read_bytes())
        calls=[]
        def run(args,**kwargs):
            calls.append(args)
            check(name+' curl configuration disabled first',args[:2]==['curl','--disable'])
            for option,value in [('--retry','0'),('--max-redirs','0'),('--max-time','30'),('--max-filesize','4194304'),('--proto','=https')]:check(name+' '+option,args[args.index(option)+1]==value)
            check(name+' no follow flag','--location' not in args and '-L' not in args)
            check(name+' fixed metadata endpoint',args[-1]=='https://archive.eso.org/tap_obs/sync')
            check(name+' bounded parent subprocess',kwargs['timeout']==35 and kwargs['check'] is False)
            Path(args[args.index('--output')+1]).write_bytes(body)
            Path(args[args.index('--dump-header')+1]).write_text('HTTP/2 '+str(http)+'\n')
            if timeout:raise subprocess.TimeoutExpired(args,35)
            return subprocess.CompletedProcess(args,returncode,json.dumps({'http_code':http,'num_redirects':redirects,'url_effective':req['endpoint']}).encode(),b'')
        with patch.object(mod.subprocess,'run',side_effect=run):rows,receipt=mod.acquire(req,plan)
        expected=returncode==0 and http==200 and redirects==0 and not timeout and len(body)<4194304
        check(name+' completion vs failure',(rows is not None)==expected)
        check(name+' exactly one subprocess call',len(calls)==1)
        check(name+' attempt marker preserved',(mod.HERE/'HD122640.ATTEMPT_STARTED.json').exists())
        check(name+' exact partial bytes preserved',(mod.HERE/'responses/HD122640.vot').read_bytes()==body)
        check(name+' receipt preserved',(mod.HERE/'responses/HD122640.REQUEST.json').exists())
exercise_transport('Valid transport')
exercise_transport('No retry on HTTP503',http=503,body=b'temporary')
exercise_transport('Redirect response stops',http=302,body=b'redirect')
exercise_transport('Curl timeout stops',returncode=28,body=b'partial')
exercise_transport('Parent timeout preserves partial bytes',timeout=True,body=b'partial')
exercise_transport('Exact byte cap stops',body=b'x'*4194304)
mod.HERE=M

# Execute main control flow only with mocked acquire/check_release: no subprocess.
for name,failure_first,expected_calls in [('First failure prevents second query',True,1),('Empty first response allows fixed second query',False,2)]:
    with tempfile.TemporaryDirectory(prefix='control_',dir=OUT) as directory:
        mod.HERE=Path(directory)
        for filename in ['TARGETS.json','EXISTING_300.json']:(mod.HERE/filename).write_bytes((M/filename).read_bytes())
        calls=[]
        def acquire(req,_plan):
            calls.append(req['target'])
            return (None,{'status':'STOPPED_REQUEST_FAILURE'}) if failure_first else ([],{'status':'COMPLETE_METADATA_RESPONSE'})
        with patch.object(mod,'check_release',return_value=(plan,{'synthetic':True},'synthetic-curl')),patch.object(mod,'acquire',side_effect=acquire),patch('sys.argv',['search_metadata.py','--execute']):mod.main()
        check(name,len(calls)==expected_calls and calls==['HD122640','HD135204'][:expected_calls])
        check(name+' exclusive overall marker',(mod.HERE/'RUN_STARTED.json').exists())
        with patch.object(mod,'check_release',return_value=(plan,{'synthetic':True},'synthetic-curl')),patch.object(mod,'acquire',side_effect=acquire),patch('sys.argv',['search_metadata.py','--execute']):
            try:mod.main()
            except FileExistsError:check(name+' replay blocked',True)
            else:check(name+' replay blocked',False)
mod.HERE=M
check('No true execution markers after review',not(M/'RUN_STARTED.json').exists() and not(M/'responses').exists())
report={'status':'PASS_INDEPENDENT_RUNTIME_PREFLIGHT','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'checks_passed':len(checks),'checks':checks,'network_requests_made':0,'science_arrays_read':0,'original_labels_changed':0,
        'plan_sha256':sha(M/'PLAN.json'),'script_sha256':sha(M/'search_metadata.py'),'auditor_script_sha256':sha(Path(__file__)),
        'source_review':['Release guard rehashes every prospective frozen file and historical source before execution; requires root-confirmed remote commit and freeze digest.',
                        'Exclusive overall and per-target markers prevent repeat execution; only fixed metadata POST endpoints are used.',
                        'curl8.4+ required for hard streaming byte limit; installed curl8.5.0 supports it. Curl30-second transport limit and35-second subprocess cleanup guard are distinct.',
                        'Parser rejects absent/non-OK TAP status, overflow,1000rows, changed columns, DTD/entity and external streams.',
                        'All raw-provenance rows grouped before300raw exclusion; missing/ambiguous/conflicting identities remain excluded.',
                        'Coordinates/time/exposure count require valid finite values; labels, thresholds and spectral arrays untouched.'],
        'release_state':'REVIEW_ONLY_ROOT_PUBLICATION_AND_ROOT_RELEASE_STILL_REQUIRED'}
(OUT/'RUNTIME_PREFLIGHT_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'checks_passed':len(checks),'script_sha256':report['script_sha256']}))
