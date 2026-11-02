"""Independent, network-free preflight for bounded metadata acquisition."""
from pathlib import Path
import datetime, hashlib, importlib.util, json, socket, tempfile, urllib.error
from unittest.mock import patch

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
plan = json.loads((BASE / 'PLAN.json').read_text())
spec = importlib.util.spec_from_file_location('reviewed_feasibility', BASE / 'feasibility.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
checks = []
def check(name, condition):
    assert condition, name
    checks.append(name)

check('No acquisition started at independent review', not (BASE/'CONE_STARTED.json').exists())
check('Script hash bound to plan', sha(BASE/'feasibility.py') == plan['script_sha256'])
check('Analyzer hash bound to plan', sha(BASE/'analyze_metadata.py') == plan['analyzer_sha256'])
for item in plan['frozen_sources']:
    check('Frozen input: '+item['path'], sha(BASE.parent/item['path']) == item['sha256'])
cfg = json.loads((BASE.parent/'method_review/CONFIG.json').read_text())
method = plan['feasibility_method']
for key, original in [('critical_flags','critical_source_flags'), ('baseline_days','baseline_lookback_days'),
                      ('min_unique_prior_visits','baseline_min_unique_visits'), ('min_earlier_utc_dates','baseline_min_earlier_utc_dates')]:
    check('Method binding '+key, method[key] == cfg[original])
check('Exact time window', method['tai_test_window'] == [cfg['window_start_mjd_tai'],cfg['window_end_mjd_tai_exclusive']])
check('Metadata columns only', not any(x in ','.join(plan['history_columns']).lower() for x in ['scienceflux','psffluxerr','magpsf','snr','reliability']))
check('Cone radius and month fixed', plan['cone_job']['payload']['radius']=='3600' and plan['cone_job']['payload']['startdate']=='2026-10-01' and plan['cone_job']['payload']['stopdate']=='2026-11-01')
check('Bounded caps', plan['history_bounds']['max_objects']==1000 and plan['history_bounds']['max_total_charged_bytes']==20000000 and plan['history_bounds']['max_workers']==2 and plan['cone_bounds']['max_response_bytes']==3000000)
check('Signed 64-bit ID preserved', mod.exact('9223372036854775807') == '9223372036854775807')
for bad in [1, 1.0, '0', '9223372036854775808', None, '1.0']:
    try: mod.exact(bad)
    except ValueError: pass
    else: raise AssertionError('Invalid exact ID admitted')
check('Reject imprecise or invalid IDs', True)
budget = mod.Budget(12,4)
check('Budget reserves full attempts', budget.reserve() and budget.reserve() and budget.reserve() and not budget.reserve())
budget.close(1,False); budget.close(0,True); budget.close(0,True)
check('Unknown reads charged full cap', budget.charged==9 and budget.reserved==0 and not budget.reserve())

class Response:
    def __init__(self, data=b'', status=200, chunks=None, headers=None):
        self.status=status; self.headers=headers or {}; self.data=data; self.chunks=chunks
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def read(self,n):
        if self.chunks is not None:
            if not self.chunks:return b''
            value=self.chunks.pop(0)
            if isinstance(value,Exception):raise value
            return value
        value,self.data=self.data[:n],self.data[n:]
        return value

good = b'[{"r:diaObjectId":9223372036854775806,"r:diaSourceId":9223372036854775805,"r:visit":123}]'
allowed=['r:diaObjectId','r:diaSourceId','r:visit']
oid='9223372036854775806'
def exercise(name, responses, expected_attempts, expected_status, assertions=None, stale=False):
    with tempfile.TemporaryDirectory(prefix='preflight_',dir=OUT) as directory:
        mod.OUT=Path(directory)
        stamp=datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(hours=3 if stale else 0)
        (mod.OUT/'CONE_STARTED.json').write_text(json.dumps({'utc':stamp.isoformat()}))
        calls=[]
        class Opener:
            def open(self, req, timeout):
                calls.append(req)
                response=responses.pop(0)
                if isinstance(response,Exception):raise response
                return response
        b=mod.Budget(1024,512)
        job={'job_id':'synthetic','method':'POST','endpoint':'https://invalid.example.test/never-network',
             'payload':{'columns':','.join(allowed)},'path':'metadata/synthetic.json'}
        with patch.object(mod.urllib.request,'build_opener',return_value=Opener()):
            result=mod.request(job,512,b,allowed,{oid})
        check(name, len(calls)==expected_attempts and result['status']==expected_status)
        if assertions: check(name+' details', assertions(result,b,mod.OUT))

exercise('Valid exact integer-ID response', [Response(good)],1,'COMPLETE',lambda r,b,p:r['returned_objects']==[oid])
exercise('Forbidden science field terminates', [Response(good.replace(b'"r:visit":123',b'"r:visit":123,"r:scienceFlux":1'))],1,'FAILED')
exercise('Out-of-request ID terminates', [Response(good.replace(b'9223372036854775806',b'9223372036854775804'))],1,'FAILED')
exercise('HTTP denial is not retried', [Response(b'denied',403)],1,'FAILED')
exercise('HTTP 503 identical retry allowed', [Response(b'temporary',503),Response(good)],2,'COMPLETE')
exercise('Nontransient URL error terminates', [urllib.error.URLError('name lookup failed')],1,'FAILED')
exercise('Timeout allows bounded retry', [TimeoutError('synthetic'),Response(good)],2,'COMPLETE',lambda r,b,p:b.charged==512+len(good))
exercise('Partial response is preserved', [Response(chunks=[b'partial',TimeoutError('synthetic')]),Response(good)],2,'COMPLETE',lambda r,b,p:(p/'attempts/synthetic_attempt01.body').read_bytes()==b'partial' and b.charged==512+len(good))
exercise('Declared cap is terminal', [Response(headers={'Content-Length':'512'})],1,'FAILED')
exercise('Reached byte cap is terminal', [Response(b'a'*512)],1,'FAILED')
exercise('Two-hour deadline blocks start', [],0,'TWO_HOUR_DEADLINE_STOP', stale=True)
mod.OUT=BASE
report={'status':'PASS_METADATA_ONLY_PREFLIGHT','reviewed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'plan_sha256':sha(BASE/'PLAN.json'),'script_sha256':sha(BASE/'feasibility.py'),
        'analyzer_sha256':sha(BASE/'analyze_metadata.py'),'checks':checks,'check_count':len(checks),
        'network_requests_made_by_review':0,
        'source_review':['Returned cone coordinates checked for valid RA/Dec and recomputed membership within one degree (+1e-9 degree numerical tolerance).',
                        'All initial 433 exact IDs and positions within 2 arcsec excluded; next at most 1000 numeric IDs frozen before history.',
                        'At most ten history jobs of 100 IDs, two workers, full per-attempt reservations, explicit failures and no replacement.',
                        'No redirects or alternative field; retries restricted to specified 5xx and timeout/reset/aborted/broken-pipe errors.',
                        'Final plan/script hashes bind independent receipt; source/config/analyzer hashes checked before acquisition.',
                        'Metadata-only flag, identity, and temporal logic reviewed against fixed detector; no photometric-evaluability claim.'],
        'limits':['Review authorizes only the already scoped metadata feasibility, not a new main science selection.',
                  'Returned-history completeness and n=100 semantics remain unknown; truncation-like counts stop acquisition.',
                  'Gaia, development counterpart checks and all original flux/baseline checks remain prerequisites for any separate follow-up.']}
(OUT/'PREFLIGHT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'checks':len(checks),'plan_sha256':report['plan_sha256']}))
