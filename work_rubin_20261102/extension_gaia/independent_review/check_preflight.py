"""Independent frozen-input and network-free Gaia transport preflight."""
from pathlib import Path
import csv,datetime,hashlib,importlib.util,io,json,tempfile,urllib.error
from unittest.mock import patch
OUT=Path(__file__).resolve().parent;G=OUT.parent;B=G.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
plan=json.loads((G/'PLAN.json').read_text());checks=[]
def check(label,value):
    assert value,label
    checks.append(label)
check('Acquisition has not started',not(G/'ACQUISITION_STARTED.json').exists())
check('Acquirer hash',plan['acquire_script_sha256']==sha(G/'acquire_gaia.py'))
check('Matcher hash',plan['match_script_sha256']==sha(G/'match_gaia.py'))
for item in plan['input_files']:check('Frozen input '+item['path'],sha(B.parent/item['path'])==item['sha256'])
rows=lambda p:list(csv.DictReader(Path(p).open()))
candidates=rows(G/'CANDIDATE_METADATA.csv')
expected=sorted([r['object_id'] for r in rows(B/'extension_feasibility/OBJECT_FEASIBILITY.csv') if r['status']=='MEETS_TEMPORAL_QUALITY_NECESSARY_CONDITION'],key=int)
check('Exact104 eligible metadata IDs in fixed order',len(candidates)==104 and [r['r:diaObjectId'] for r in candidates]==expected)
prior=rows(B/'access_pilot/DEVELOPMENT_SELECTION.csv')+rows(B/'access_pilot/MAIN_METADATA_CANDIDATES_UNMATCHED.csv')
check('No initial433 exact IDs in candidates',not({r['r:diaObjectId'] for r in candidates}&{r['r:diaObjectId'] for r in prior}))
old=json.loads((B/'gaia_selection/PLAN.json').read_text())
check('Unchanged stellar evidence',plan['stellar_evidence']==old['stellar_evidence'])
check('Unchanged association guards',all(plan['association'][key]==old['association'][key] for key in ['target_epoch','propagation','match_radius_arcsec','neighbor_ambiguity_radius_arcsec','neighbor_evidence_radius_arcsec','unique_rule']))
check('Field center and margin',plan['gaia_query']['center_deg']==old['gaia_query']['center_deg'] and plan['gaia_query']['radius_deg']==1.1)
check('Row and byte attempt bounds',plan['gaia_query']['row_cap']==50000 and plan['gaia_query']['response_byte_cap']==8000000 and plan['gaia_query']['attempts']==2 and plan['gaia_query']['total_attempt_body_cap']==16000000)
check('Additional and total object bounds',plan['max_additional_selected']==312 and plan['max_total_main']==500 and plan['original_main_count']==188)
query=(G/'QUERY.adql').read_text().strip()
check('Exact query hash',hashlib.sha256(query.encode()).hexdigest()==plan['gaia_query']['query_sha256'])
check('Fixed field-only query',"CIRCLE('ICRS',8.986275,-42.709834,1.1)" in query and query.startswith('SELECT TOP 50000 ') and query.endswith('ORDER BY source_id'))
spec=importlib.util.spec_from_file_location('reviewed_gaia_acquisition',G/'acquire_gaia.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class Response:
    def __init__(self,body=b'',status=200,headers=None,chunks=None):self.body=body;self.status=status;self.headers=headers or {};self.chunks=chunks
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,n):
        if self.chunks is not None:
            if not self.chunks:return b''
            chunk=self.chunks.pop(0)
            if isinstance(chunk,Exception):raise chunk
            return chunk
        chunk,self.body=self.body[:n],self.body[n:]
        return chunk
def make_body(ids=('9223372036854775805','9223372036854775806'),ra=8.986275,dec=-42.709834):
    buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=plan['gaia_query']['columns']);writer.writeheader()
    for sid in ids:
        row={key:'' for key in plan['gaia_query']['columns']};row.update(source_id=sid,ra=ra,dec=dec);writer.writerow(row)
    return buf.getvalue().encode()
good=make_body()
def exercise(name,responses,expected_calls,success,detail=None):
    with tempfile.TemporaryDirectory(prefix='gaia_preflight_',dir=OUT) as directory:
        module.OUT=Path(directory)
        for name_ in ['PLAN.json','QUERY.adql','match_gaia.py']:(module.OUT/name_).write_bytes((G/name_).read_bytes())
        (module.OUT/'independent_review').mkdir()
        (module.OUT/'independent_review/PREFLIGHT.json').write_text(json.dumps({'status':'PASS_SYNTHETIC_ONLY','plan_sha256':sha(G/'PLAN.json'),'acquire_script_sha256':sha(G/'acquire_gaia.py'),'match_script_sha256':sha(G/'match_gaia.py')}))
        calls=[]
        class Opener:
            def open(self,req,timeout):
                calls.append(req)
                response=responses.pop(0)
                if isinstance(response,Exception):raise response
                return response
        with patch.object(module.urllib.request,'build_opener',return_value=Opener()):
            try:module.main();finished=True
            except RuntimeError:finished=False
        receipts=json.loads((module.OUT/'ACQUISITION_RECEIPTS.json').read_text())
        check(name,finished==success and len(calls)==expected_calls)
        check(name+' charge bound',sum(r['charged_bytes'] for r in receipts)<=16000000)
        if detail:check(name+' details',detail(module.OUT,receipts))
        if len(calls)>1:check(name+' identical retries',calls[0].full_url==calls[1].full_url and calls[0].data==calls[1].data)
exercise('Valid exact64bit metadata response',[Response(good)],1,True,lambda p,r:rows(p/'GAIA_DR3_FIELD.csv')[0]['source_id']=='9223372036854775805')
exercise('HTTP denial no retry',[Response(b'denied',403)],1,False)
exercise('Redirect is terminal',[Response(b'redirect',302)],1,False)
exercise('Specified transient HTTP retry',[Response(b'temporary',503),Response(good)],2,True)
exercise('Nontransient URL error no retry',[urllib.error.URLError('DNS failure')],1,False)
exercise('Partial response preserved with bounded retry',[Response(chunks=[b'partial',TimeoutError('synthetic')]),Response(good)],2,True,lambda p,r:(p/'ATTEMPT_01.body').read_bytes()==b'partial' and r[0]['charged_bytes']==8000000)
exercise('Duplicate Gaia IDs terminal',[Response(make_body(ids=('1','1')))],1,False)
exercise('Unexpected CSV schema terminal',[Response(b'source_id,ra,dec\n1,0,0\n2,0,0\n')],1,False)
exercise('Out-of-field response terminal',[Response(make_body(ra=180))],1,False)
exercise('Invalid coordinates terminal',[Response(make_body(dec=91))],1,False)
exercise('Declared byte cap terminal',[Response(headers={'Content-Length':'8000000'})],1,False)
exercise('Reached byte cap terminal',[Response(b'a'*8000000)],1,False)
exercise('Reached row cap terminal',[Response(make_body(ids=(str(i+1) for i in range(50000))))],1,False)
module.OUT=G
protocol=json.loads((OUT/'PROTOCOL_AUDIT.json').read_text())
check('Independent scientific protocol audit passed',protocol['status'].startswith('PASS'))
check('Independent scientific matcher hash bound',protocol['reviewed_hashes']['match_gaia.py']==sha(G/'match_gaia.py'))
report={'status':'PASS_EXTENSION_GAIA_PREFLIGHT','reviewed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'plan_sha256':sha(G/'PLAN.json'),'acquire_script_sha256':sha(G/'acquire_gaia.py'),'match_script_sha256':sha(G/'match_gaia.py'),
        'check_count':len(checks),'checks':checks,'network_requests_made_by_review':0,
        'source_review':['Exact104 metadata-pass identities frozen without flux selection.',
                        'Same original spherical astrometric propagation, all-neighbor guards, stellar criteria and distance ordering.',
                        'Prior exclusion unions all initial433 neighbors within2arcsec, original188 selectedGaia IDs, historicalDEV annotations, and recomputed initial433 neighbors in this catalog.',
                        'Candidate duplicates retain lowest exact numeric DiaObjectID; cap312 plus original188 remains<=500.',
                        'Single1.1degree Gaia cone; row/byte cap reached or denial/redirect/schema/coordinate failure stops; one identical transient retry only.',
                        'Original cohorts and detector/configuration remain immutable.'],
        'limits':['Gaia association/selection only. No permission or scientific claim for new flux evaluation arises from this receipt.',
                  'Exact selected extension must be frozen and published before additional unchanged science run as specified by root.']}
(OUT/'PREFLIGHT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'check_count':len(checks),'plan_sha256':report['plan_sha256']}))
