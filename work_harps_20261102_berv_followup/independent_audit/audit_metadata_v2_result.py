"""Independent TABLEDATA decoding and classification check; no production imports."""
from pathlib import Path
import collections,datetime,hashlib,json,math,re,urllib.parse,xml.etree.ElementTree as ET
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;ROOT=OUT.parents[1];M=BASE/'metadata_search_v2';OLD=BASE/'metadata_search'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
def check(name,value):
    assert value,name
    checks.append(name)
local=lambda e:e.tag.split('}')[-1]
plan=read(M/'PLAN.json');freeze=read(M/'PREFLIGHT_FREEZE.json');release=read(M/'ROOT_RELEASE.json');summary=read(M/'SUMMARY.json')
check('Exact released newfreeze',release['freeze_sha256']==sha(M/'PREFLIGHT_FREEZE.json')=='156584f21aeba1039cc0d34e8ec228786061e476a113f42075f95a3bc6265fd0')
check('Exact prospective publication',release['prospective_commit']=='4ee21b47d332ab467dbb4c3d452f07a71882dddb' and release['remote_bytes_verified'] is True)
for path,record in freeze['files'].items():check('Frozen amended input unchanged '+path,sha(M/path)==record['sha256'] and (M/path).stat().st_size==record['bytes'])
for path,digest in plan['source_hashes'].items():check('Historical and failure provenance unchanged '+path,sha(ROOT/path)==digest)
check('Two new attempts only',sorted(p.name for p in M.glob('*.ATTEMPT_STARTED.json'))==['HD122640.ATTEMPT_STARTED.json','HD135204.ATTEMPT_STARTED.json'])
check('Total continuation requests exactly3',read(OLD/'SUMMARY.json')['target_requests']==1 and summary['target_requests']==2 and len(list(OLD.glob('*.ATTEMPT_STARTED.json')))+len(list(M.glob('*.ATTEMPT_STARTED.json')))==3)
targets={r['canonical_target']:r for r in read(M/'TARGETS.json')};known=read(M/'EXISTING_300.json');known_dp={r['dp_id'] for r in known};known_raw={x for r in known for x in r['raw_progenitor_ids']}
allrows=[];counts={};bytes_total=0;times={}
for request in plan['requests']:
    target=request['target'];prefix=M/'responses'/target
    receipt=read(Path(str(prefix)+'.REQUEST.json'));response=Path(str(prefix)+'.vot');body=response.read_bytes();stats=read(Path(str(prefix)+'.curl.json'))
    query=(M/request['query_file']).read_bytes();form={**request['form'],'QUERY':query.decode()};encoded=urllib.parse.urlencode(form).encode()
    check('Exact request body '+target,len(encoded)==receipt['request_body_bytes'] and hashlib.sha256(encoded).hexdigest()==receipt['request_body_sha256'])
    check('Frozen query '+target,sha(M/request['query_file'])==receipt['query_sha256'])
    check('One successful bounded HTTPS request '+target,receipt['attempt']==1 and receipt['curl_returncode']==0 and stats['http_code']==200 and stats['num_redirects']==0 and stats['url_effective']==request['endpoint'] and stats['time_total']<=30)
    check('Exact response bytes/hash '+target,len(body)==receipt['response_bytes']==stats['size_download'] and sha(response)==receipt['response_sha256'] and len(body)<4194304)
    check('No spectrum request '+target,receipt['science_payload_requested'] is False)
    xml=ET.fromstring(body);statuses=[e.attrib.get('value') for e in xml.iter() if local(e)=='INFO' and e.attrib.get('name')=='QUERY_STATUS']
    check('All TAP statuses explicitly OK '+target,bool(statuses) and set(statuses)=={'OK'})
    tables=[e for e in xml.iter() if local(e)=='TABLE'];check('Exactly one metadata table '+target,len(tables)==1)
    fields=[e for e in tables[0] if local(e)=='FIELD'];check('Exact returned columns '+target,[e.attrib['name'] for e in fields]==request['expected_columns'])
    check('No remote stream or binary parser needed '+target,len([e for e in xml.iter() if local(e)=='TABLEDATA'])==1 and not any(local(e)=='STREAM' for e in xml.iter()))
    decoded=[]
    for tr in [e for e in tables[0].iter() if local(e)=='TR']:
        cells=[e.text for e in tr if local(e)=='TD'];check('Complete metadata row '+target,len(cells)==len(fields))
        row={}
        for field,text in zip(fields,cells,strict=True):
            kind=field.attrib['datatype'];name=field.attrib['name']
            if kind=='char':value=text or ''
            elif text is None or not text.strip():value=None
            elif kind in ['int','long','short']:value=int(text)
            elif kind in ['double','float']:
                value=float(text)
                if not math.isfinite(value):value=None
            else:raise AssertionError('Unexpected metadata type '+kind)
            row[name]=value
        decoded.append(row)
    check('Returned row cap '+target,len(decoded)<1000)
    normalized=read(Path(str(prefix)+'.ROWS.json'));check('Exact row accounting '+target,len(decoded)==len(normalized)==receipt['returned_joined_rows'])
    for i,(a,b) in enumerate(zip(decoded,normalized,strict=True)):
        for key in request['expected_columns']:check('Independent XML value '+target+' '+str(i)+' '+key,a[key]==b[key])
    allrows.extend((target,row) for row in decoded);counts[target]=len(decoded);bytes_total+=len(body);times[target]=stats['time_total']

# Recompute all eligibility predicates independently for this returned population.
groups=collections.defaultdict(list)
for target,row in allrows:groups[target,row['dp_id']].append(row)
expected=[];raw_seen={};max_separation_error=0.;details=[]
reported={r['dp_id']:r for r in read(M/'ALL_RETURNED_PRODUCTS.json')}
for (target,dp),group in groups.items():
    r=group[0];targetmeta=targets[target]
    check('Complete product metadata consistent '+dp,all({k:v for k,v in x.items() if k!='source_file'}=={k:v for k,v in r.items() if k!='source_file'} for x in group))
    raws={re.sub(r'(?:\.fits(?:\.Z|\.gz)?|\.Z)$','',str(x['source_file'] or '').strip().rsplit('/',1)[-1]) for x in group}
    check('New single exact raw provenance '+dp,len(raws)==1 and all(re.fullmatch(r'HARPS\.\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}',x) for x in raws) and not(raws&known_raw))
    check('New exact DP main science product '+dp,dp not in known_dp and dp.startswith('ADP.') and r['archive_id']==dp and r['eso_category']=='SCIENCE.SPECTRUM')
    check('Exact target and public HARPS spectrum '+dp,''.join(r['target_name'].split()).upper()==target and r['instrument_name']=='HARPS' and r['obs_collection']=='HARPS' and r['dataproduct_type']=='spectrum')
    a,d=map(math.radians,[r['s_ra'],r['s_dec']]);ar,dr=map(math.radians,[targetmeta['ra_deg'],targetmeta['dec_deg']])
    v=[math.cos(d)*math.cos(a),math.cos(d)*math.sin(a),math.sin(d)];w=[math.cos(dr)*math.cos(ar),math.cos(dr)*math.sin(ar),math.sin(dr)]
    cross=[v[1]*w[2]-v[2]*w[1],v[2]*w[0]-v[0]*w[2],v[0]*w[1]-v[1]*w[0]]
    separation=math.degrees(math.atan2(math.sqrt(sum(x*x for x in cross)),sum(x*y for x,y in zip(v,w))))*3600
    check('Valid coordinate and inventory cone '+dp,0<=r['s_ra']<360 and -90<=r['s_dec']<=90 and separation<=120)
    check('Finite positive single observation '+dp,all(math.isfinite(float(r[k])) for k in ['t_min','t_max','t_exptime','n_obs']) and r['t_max']>r['t_min'] and r['t_exptime']>0 and r['n_obs']==1 and r['multi_ob']=='S')
    check('Whole exposure outside frozen calendar interval '+dp,r['t_max']<=59994 or r['t_min']>=60005)
    released=datetime.datetime.fromisoformat(r['obs_release_date'].replace('Z','+00:00'))
    check('Public at fixed cutoff '+dp,released<=datetime.datetime(2026,11,2,tzinfo=datetime.timezone.utc))
    check('No repeated new raw across products '+dp,not(raws&set(raw_seen)))
    for raw in raws:raw_seen[raw]=dp
    observed=reported[dp];delta=abs(separation-observed['coordinate_separation_arcsec']);max_separation_error=max(max_separation_error,delta)
    check('Independent vector separation agrees '+dp,delta<1e-8)
    check('Exact recorded raw and normalized source '+dp,observed['source_file_ids']==sorted(raws) and observed['query_rows']==len(group) and observed['metadata']==r)
    check('Independent eligible classification '+dp,observed['status']=='METADATA_CANDIDATE_PENDING_HEADER_IDENTITY_BERV' and observed['reasons']==[])
    expected.append(dp);date=datetime.datetime(1858,11,17,tzinfo=datetime.timezone.utc)+datetime.timedelta(days=r['t_min'])
    details.append({'target':target,'dp_id':dp,'observation_utc':date.isoformat(),'month_number':date.month,'t_min':r['t_min']})
check('Every returned product independently classified',set(expected)==set(reported) and len(expected)==18)
check('Exact candidate set',set(expected)=={r['dp_id'] for r in read(M/'CANDIDATES.json')} and len(read(M/'CANDIDATES.json'))==18)
check('Reported per-target counts',counts=={'HD122640':18,'HD135204':0} and summary['per_target']=={'HD122640':{'returned_products':18,'metadata_candidates':18},'HD135204':{'returned_products':0,'metadata_candidates':0}})
check('Completed bounded metadata summary',summary['status']=='COMPLETE_BOUNDED_METADATA' and summary['returned_products']==summary['metadata_candidates']==18 and summary['science_payload_bytes']==0 and summary['original_label_changes']==0 and summary['berv_not_measured'] is True)
latest={}
for r in details:
    key=r['target'],r['month_number'];rank=(-r['t_min'],r['dp_id'])
    if key not in latest or rank<(-latest[key]['t_min'],latest[key]['dp_id']):latest[key]=r
report={'status':'PASS_INDEPENDENT_AMENDED_METADATA_RESULTS','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'checks_passed':len(checks),'checks':checks,'new_requests':2,'total_continuation_requests':3,'response_bytes_total':bytes_total,
        'transport_seconds_by_target':times,'independently_decoded_joined_rows':counts,'metadata_candidates_by_target':counts,
        'independent_latest_calendar_month_number_choices':[latest[k] for k in sorted(latest)],
        'maximum_vector_separation_difference_arcsec':max_separation_error,
        'archive_queries_by_audit':0,'production_classifier_imported':False,'science_arrays_read':0,'labels_changed':0,
        'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in [M/'PLAN.json',M/'PREFLIGHT_FREEZE.json',M/'ROOT_RELEASE.json',M/'SUMMARY.json',M/'CANDIDATES.json',M/'ALL_RETURNED_PRODUCTS.json']},
        'auditor_script_sha256':sha(Path(__file__)),
        'interpretation':'18 new HD122640 metadata candidates and zero HD135204 rows in this bounded query. BERV has not been measured; no origin or archive-exhaustiveness conclusion. The fixed latest-per-month-number rule yields two prospective header jobs, January and May, both HD122640.'}
(OUT/'METADATA_V2_RESULT_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'checks_passed':len(checks),'response_bytes':bytes_total,'header_month_choices':report['independent_latest_calendar_month_number_choices']}))
