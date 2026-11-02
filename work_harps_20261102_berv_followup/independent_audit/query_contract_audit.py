"""Inspect frozen prospective ADQL and metadata provenance; no requests."""
from pathlib import Path
import datetime,hashlib,json,math,re,xml.etree.ElementTree as ET
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];M=OUT.parent/'metadata_search'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=read(M/'PLAN.json');targets=read(M/'TARGETS.json');existing=read(M/'EXISTING_300.json');baseline=read(OUT/'STATE_BASELINE_AUDIT.json')
checks=[]
def check(name,condition):
    assert condition,name
    checks.append(name)
check('Exact ordered targets',[r['target'] for r in plan['requests']]==['HD122640','HD135204']==[r['canonical_target'] for r in targets])
check('Fixed limits',plan['limits']=={'target_requests_max':2,'attempts_per_target':1,'wall_seconds_per_target':30,'response_bytes_per_target':4194304,'rows_per_target':1000,'redirects':0,'retries':0,'science_payload_bytes':0})
check('No new execution marker',not(M/'RUN_STARTED.json').exists())
check('All300 DP exclusions',len(existing)==300 and sorted(r['dp_id'] for r in existing)==baseline['existing_main_dp_ids_to_exclude'])
check('All300 raw exclusions',sorted(x for r in existing for x in r['raw_progenitor_ids'])==baseline['existing_main_raw_ids_to_exclude'])
for path,digest in plan['source_hashes'].items():check('Current plan source hash '+path,sha(ROOT/path)==digest)
for r in existing:
    source=next(x for x in read(ROOT/r['source_manifest']) if x['dp_id']==r['dp_id'])
    check('Exclusion identity and recorded product hash '+r['dp_id'],r['raw_progenitor_ids']==source['raw_progenitor_ids'] and r['canonical_target']==source['canonical_target'] and r['input_sha256']==source['sha256'])
epoch=datetime.datetime(1858,11,17,tzinfo=datetime.timezone.utc)
window=plan['observation_time_exclusion']
check('Whole UTC calendar interval',window['utc_half_open']==['2023-02-19T00:00:00Z','2023-03-02T00:00:00Z'])
check('Independent date-MJD conversion',[(datetime.datetime.fromisoformat(x.replace('Z','+00:00'))-epoch).total_seconds()/86400 for x in window['utc_half_open']]==[59994,60005]==window['mjd_half_open'])
root=ET.fromstring((M/'sources/ESO_TAP_TABLES.xml').read_bytes());schema={}
for table in root.iter():
    if table.tag.split('}')[-1]!='table':continue
    name=next((x.text for x in table if x.tag.split('}')[-1]=='name'),None)
    if name not in ['ivoa.ObsCore','phase3v2.product_files','phase3v2.provenance']:continue
    schema[name]={}
    for column in table:
        if column.tag.split('}')[-1]!='column':continue
        d={x.tag.split('}')[-1]:x.text for x in column}
        schema[name][d['name']]={'type':d.get('dataType'),'description':d.get('description')}
check('Schema contract matches official saved tables',schema==read(M/'SCHEMA_CONTRACT.json'))
for target,request in zip(targets,plan['requests'],strict=True):
    name=target['canonical_target'];query=(M/request['query_file']).read_text()
    check('Frozen query hash '+name,sha(M/request['query_file'])==request['query_sha256'])
    check('One approved POST endpoint '+name,request['endpoint']=='https://archive.eso.org/tap_obs/sync' and request['method']=='POST')
    check('Only fixed TAP metadata parameters '+name,request['form']=={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'votable','MAXREC':'1000'})
    selected=re.search(r'^SELECT (.*?)\nFROM ',query,re.S).group(1).split(', ')
    check('Exact metadata columns '+name,[x.split('.')[-1] for x in selected]==request['expected_columns'])
    tables={'o':'ivoa.ObsCore','f':'phase3v2.product_files','p':'phase3v2.provenance'}
    check('Selected fields exist in official schema '+name,all(field.split('.')[1] in schema[tables[field.split('.')[0]]] for field in selected))
    check('No TOP or pagination '+name,not re.search(r'\b(TOP|OFFSET|LIMIT)\b',query,re.I))
    check('Complete main-product and provenance joins '+name,'LEFT OUTER JOIN phase3v2.product_files AS f ON o.dp_id=f.product_id AND f.archive_id=f.product_id' in query and 'LEFT OUTER JOIN phase3v2.provenance AS p ON f.internal_file_id=p.product_file' in query)
    check('HARPS public single-exposure conditions '+name,"o.instrument_name='HARPS' AND o.obs_collection='HARPS' AND o.dataproduct_type='spectrum'" in query and "o.n_obs=1 AND o.multi_ob='S' AND o.t_exptime>0" in query and "o.obs_release_date<='2026-11-02T00:00:00Z'" in query)
    check('Entire observation outside frozen interval '+name,'AND (o.t_max<=59994 OR o.t_min>=60005)' in query)
    block=re.search(r'AND o.dp_id NOT IN \((.*?)\)\nORDER BY',query,re.S).group(1)
    ids=re.findall(r"'([^']*)'",block)
    check('Every old DP excluded once server-side '+name,len(ids)==300 and sorted(ids)==baseline['existing_main_dp_ids_to_exclude'])
    where=query.split('WHERE ',1)[1].split('ORDER BY',1)[0]
    check('No individual raw progenitor filtered out of join '+name,'p.source_file' not in where)
    aliases=', '.join("'"+x+"'" for x in target['exact_name_aliases'])
    condition=f"AND (o.target_name IN ({aliases}) OR 1=CONTAINS(POINT('J2000',o.s_ra,o.s_dec),CIRCLE('J2000',{target['ra_deg']:.12f},{target['dec_deg']:.12f},{120/3600:.12f})))"
    check('Name OR cone correctly parenthesized '+name,condition in query)
    check('Stable observation-time ordering '+name,query.rstrip().endswith('ORDER BY o.t_min ASC, o.dp_id ASC, p.source_file ASC'))
    check('No SNR/flux selection '+name,not re.search(r'\b(snr|scienceFlux|flux)\b',where,re.I))
    check('Recorded target source hash '+name,sha(ROOT/target['source_manifest'])==target['source_manifest_sha256'])
    source=next(x for x in read(ROOT/target['source_manifest']) if x['dp_id']==target['coordinate_source_dp_id'])
    check('Exact intended-header provenance '+name,source['intended_target_header']==target['intended_header'] and source['sha256']==target['source_product_sha256'])
    alpha=abs(float(target['intended_header']['HIERARCH ESO TEL TARG ALPHA']));delta=float(target['intended_header']['HIERARCH ESO TEL TARG DELTA'])
    def sexagesimal(value):
        a=abs(value);major=math.floor(a/10000);minute=math.floor((a-major*10000)/100);second=a-major*10000-minute*100
        return math.copysign(major+minute/60+second/3600,value)
    check('Independent sexagesimal intended-coordinate conversion '+name,abs(target['ra_deg']-15*sexagesimal(alpha))<1e-10 and abs(target['dec_deg']-sexagesimal(delta))<1e-10)
    check('Correct internal coordinate frame '+name,target['coordinate_frame']=='FK5/J2000' and target['intended_header']['RADECSYS']=='FK5' and target['intended_header']['EQUINOX']==2000)
    check('120arcsec inventory radius only '+name,target['cone_radius_arcsec']==120 and 'not independent' in target['identity_limit'] and 'not propagated' in target['identity_limit'])
report={'status':'PASS_PROSPECTIVE_METADATA_QUERY_CONTRACT','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'checks_passed':len(checks),'checks':checks,'network_requests':0,'science_arrays_read':0,
        'plan_sha256':sha(M/'PLAN.json'),'auditor_script_sha256':sha(Path(__file__)),
        'reviewed_files':{p.name:sha(p) for p in [M/'PLAN.json',M/'TARGETS.json',M/'EXISTING_300.json',M/'SCHEMA_CONTRACT.json',M/'HD122640.adql',M/'HD135204.adql']},
        'limitations':['Preflight query/schema/identity review only; execution and parsing still require independent transport review and root release.',
                      'ESO target_name is PI-assigned and coordinates are internal FK5/J2000 metadata. The120arcsec condition does not independently verify physical target identity.',
                      'multi_ob=S permits combinations within a visit; n_obs=1 and unique raw provenance are additionally required.',
                      'No BERV inference is made from dates, and all300 exact raw exclusions must be applied to complete product groups after retrieval.']}
(OUT/'QUERY_CONTRACT_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'checks_passed':len(checks)}))
