"""One released header, then one separately released optional FITS; no array access."""
import argparse,datetime,hashlib,json,math,re,subprocess
from pathlib import Path
from header_tools import check_identity,parse_header_response

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
PHASE=HERE.parent
DP='ADP.2017-05-21T01:01:50.278'
RAW='HARPS.2017-05-20T02:21:45.847'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_bytes())
def save(path,value,exclusive=False):
    with path.open('x' if exclusive else 'w') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
def relative(path):return str(path.relative_to(REPO))
def repo_path(name):
    if Path(name).is_absolute():raise ValueError('Repository-relative path required')
    p=(REPO/name).resolve();p.relative_to(REPO);return p
def verify_file(path,record):
    if sha(path)!=record['sha256'] or path.stat().st_size!=record['bytes']:raise ValueError('Changed file: '+str(path))
def publication(release,required):
    p=repo_path(release['publication_receipt_path'])
    if sha(p)!=release['publication_receipt_sha256']:raise ValueError('Publication receipt changed')
    doc=read(p)
    if doc.get('status')!='PASS_EXACT_REMOTE_READBACK' or doc.get('commit')!=release.get('prospective_commit'):raise ValueError('Exact remote publication absent')
    entries={r['path']:r for r in doc['files']}
    for path in required:
        name=relative(path)
        if name not in entries:raise ValueError('Publication does not bind '+name)
        verify_file(path,entries[name])
def base_release(stage):
    plan=read(HERE/'PLAN.json');candidate=read(HERE/'CANDIDATE.json')
    if candidate['dp_id']!=DP or candidate['target']!='HD122640' or candidate['source_file_ids']!=[RAW]:raise ValueError('Unexpected candidate')
    if plan['job']['dp_id']!=DP or plan['job']['target']!='HD122640' or plan['job']['source_file_ids']!=[RAW] or plan['job']['metadata']!=candidate['metadata']:raise ValueError('Plan candidate differs')
    if plan['candidate_sha256']!=sha(HERE/'CANDIDATE.json'):raise ValueError('Candidate hash changed')
    for name,h in plan['code_hashes'].items():
        if sha(HERE/name)!=h:raise ValueError('Code changed: '+name)
    for name,h in plan['source_hashes'].items():
        if sha(repo_path(name))!=h:raise ValueError('Historical source changed: '+name)
    gate=plan['berv_gate'];events=gate['discovery_events']
    if len(events)!=6 or len({x['candidate_id'] for x in events})!=6 or gate['minimum_absolute_delta_km_s']!=10*299792.458/115000:raise ValueError('Large-shift gate differs')
    freeze_path=PHASE/'PREFLIGHT_FREEZE.json';freeze=read(freeze_path)
    required=[HERE/'PLAN.json',HERE/'CANDIDATE.json',Path(__file__),HERE/'header_tools.py']
    if not all(relative(p) in freeze['files'] for p in required):raise ValueError('Freeze omits plan/code/candidate')
    for name,record in freeze['files'].items():verify_file(repo_path(name),record)
    release_path=HERE/(stage.upper()+'_RELEASE.json');release=read(release_path)
    if release.get('schema')!='HARPS_MAY_QUALITY_'+stage.upper()+'_RELEASE_V1' or release.get('approved') is not True:raise ValueError('Exact stage release absent')
    if release.get('remote_bytes_verified') is not True or not re.fullmatch('[0-9a-f]{40}',release.get('prospective_commit','')):raise ValueError('Verified publication commit absent')
    for key,path in [('freeze_sha256',freeze_path),('plan_sha256',HERE/'PLAN.json'),('candidate_sha256',HERE/'CANDIDATE.json')]:
        if release.get(key)!=sha(path):raise ValueError('Release binding mismatch: '+key)
    if release.get('code_hashes')!=plan['code_hashes']:raise ValueError('Release code mismatch')
    if stage=='header':
        phase_files=[repo_path(n) for n in freeze['files'] if repo_path(n).is_relative_to(PHASE)]
        publication(release,[freeze_path,*phase_files])
    version=subprocess.run(['curl','--disable','--version'],capture_output=True,text=True,check=True).stdout
    v=re.search(r'curl (\d+)\.(\d+)\.(\d+)',version)
    if not v or tuple(map(int,v.groups()))<(8,4,0):raise ValueError('curl>=8.4 required for streaming byte cap')
    return plan,release,version

def inspect_header(body,mime,plan):
    header,rendering=parse_header_response(body,mime)
    result=check_identity(header,plan['job']);result['parser']=rendering
    extra={}
    ra,dec=header.get('RA'),header.get('DEC')
    extra['finite_valid_equatorial_coordinates']=all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in [ra,dec]) and 0<=ra<360 and -90<=dec<=90
    extra['high_resolution_HEFS_explicit_false']=header.get('HIERARCH ESO INS HEFS ST') is False
    try:
        observed=datetime.datetime.fromisoformat(header['DATE-OBS'].replace('Z','+00:00')).replace(tzinfo=datetime.timezone.utc)
        raw_date=datetime.datetime.fromisoformat(RAW.removeprefix('HARPS.')).replace(tzinfo=datetime.timezone.utc)
        extra['date_obs_matches_exact_raw_within_0p02s']=abs((observed-raw_date).total_seconds())<=.02
    except (KeyError,TypeError,ValueError):extra['date_obs_matches_exact_raw_within_0p02s']=False
    result['checks'].update(extra);result['failures'].extend(k for k,v in extra.items() if not v)
    if result['failures']:result['status']='EXCLUDED_HEADER_VALIDATION'
    berv=result['berv_km_s'];threshold=plan['berv_gate']['minimum_absolute_delta_km_s'];deltas=[]
    for event in plan['berv_gate']['discovery_events']:
        delta=abs(berv-event['discovery_berv_km_s']) if berv is not None else None
        deltas.append(dict(candidate_id=event['candidate_id'],discovery_berv_km_s=event['discovery_berv_km_s'],absolute_delta_km_s=delta,passes=delta is not None and delta>=threshold))
    result['large_shift_gate']={'threshold_km_s':threshold,'comparison':'>=','per_event':deltas,'passes_all_six':all(r['passes'] for r in deltas),'meaning':'Descriptive planning displacement; no classification or power calibration.'}
    return result

def transfer(stage,plan):
    spec=plan[stage];stem=DP.replace(':','_')
    output=HERE/('responses/'+stem+'.body' if stage=='header' else 'products/'+stem+'.fits')
    receipt_path=HERE/'receipts'/(stage+'.json')
    if output.exists() or receipt_path.exists():raise FileExistsError('Preserve existing stage output')
    save(HERE/(stage.upper()+'_STARTED.json'),{'started_utc':now(),'attempt':1,'stage':stage,'dp_id':DP,'plan_sha256':sha(HERE/'PLAN.json'),'release_sha256':sha(HERE/(stage.upper()+'_RELEASE.json'))},exclusive=True)
    output.parent.mkdir(exist_ok=True);receipt_path.parent.mkdir(exist_ok=True)
    args=['curl','--disable','--silent','--show-error','--globoff','--request','GET','--proto','=https','--proto-redir','=https','--max-redirs','0','--retry','0','--max-time',str(spec['timeout_seconds']),'--connect-timeout','15','--max-filesize',str(spec['max_response_bytes']),'--header','Accept-Encoding: identity','--user-agent','SETI-HARPS-May-quality/1.0','--output',str(output),'--dump-header',str(HERE/'receipts'/(stage+'.headers')),'--write-out','%{json}',spec['url']]
    receipt={'stage':stage,'started_utc':now(),'dp_id':DP,'target':'HD122640','url':spec['url'],'attempts':1,'retries':0,'redirects_followed':0,'command':args,'new_arrays_interpreted':0}
    try:
        proc=subprocess.run(args,capture_output=True,timeout=spec['timeout_seconds']+5,check=False)
        (HERE/'receipts'/(stage+'.curl.json')).write_bytes(proc.stdout);(HERE/'receipts'/(stage+'.stderr')).write_bytes(proc.stderr)
        stats=json.loads(proc.stdout) if proc.stdout else {};receipt.update(curl_returncode=proc.returncode,transport=stats)
        if proc.returncode or stats.get('http_code')!=200 or stats.get('num_redirects')!=0 or stats.get('url_effective')!=spec['url']:raise ValueError('Transport/status/redirect contract failed')
        if not output.is_file() or not 0<output.stat().st_size<spec['max_response_bytes']:raise ValueError('Empty or byte-capped response')
        receipt['status']='COMPLETE'
    except Exception as e:receipt.update(status='FAILED',reason=type(e).__name__+': '+str(e))
    receipt['finished_utc']=now()
    if output.is_file():receipt.update(bytes=output.stat().st_size,sha256=sha(output))
    save(receipt_path,receipt,exclusive=True)
    return output,receipt_path,receipt

def header_stage(plan,release):
    if (HERE/'HEADER_RESULTS.json').exists() or (HERE/'SELECTION.json').exists():raise FileExistsError('Preserve completed header stage')
    body_path,receipt_path,receipt=transfer('header',plan)
    row={'job_index':0,'dp_id':DP,'target':'HD122640','month_number':5,'body_path':str(body_path.relative_to(HERE)),'body_sha256':sha(body_path) if body_path.exists() else None,'receipt_path':str(receipt_path.relative_to(HERE)),'receipt_sha256':sha(receipt_path)}
    if receipt['status']!='COMPLETE':row.update(status='REQUEST_FAILED',reason=receipt.get('reason'))
    else:
        try:
            inspection=inspect_header(body_path.read_bytes(),receipt['transport'].get('content_type',''),plan)
            row['inspection']=inspection
            row['status']=inspection['status'] if inspection['status']!='PASS_RECORDED_BERV' or inspection['large_shift_gate']['passes_all_six'] else 'BLOCKED_LARGE_SHIFT_GATE'
        except Exception as e:row.update(status='UNRECOGNIZED_HEADER_RESPONSE',reason=type(e).__name__+': '+str(e))
    passed=row['status']=='PASS_RECORDED_BERV'
    results={'schema':'HARPS_BERV_HEADER_RESULTS_V1','status':'COMPLETE' if passed else 'COMPLETE_WITH_STOP','completed_utc':now(),'plan_sha256':sha(HERE/'PLAN.json'),'root_release_sha256':sha(HERE/'HEADER_RELEASE.json'),'code_hashes':plan['code_hashes'],'requests_attempted':1,'response_bytes':receipt.get('bytes',0),'stop_reason':None if passed else row['status'],'results':[row],'spectral_arrays_requested_or_read':False}
    save(HERE/'HEADER_RESULTS.json',results,exclusive=True)
    selected=[]
    if passed:
        selected=[{'selection_index':0,'header_result_job_index':0,'dp_id':DP,'target':'HD122640','berv_km_s':row['inspection']['berv_km_s'],'source_file_ids':[RAW],'metadata':plan['job']['metadata'],'primary_header':row['inspection']['primary_header'],'header_body_path':row['body_path'],'header_body_sha256':row['body_sha256'],'header_receipt_path':row['receipt_path'],'header_receipt_sha256':row['receipt_sha256']}]
    selection={'schema':'HARPS_MAY_QUALITY_SELECTION_V1','status':'PROPOSED_PENDING_SEPARATE_PAYLOAD_RELEASE' if passed else 'BLOCKED_NO_PAYLOAD','selection_rule':plan['selection_rule'],'header_results_sha256':sha(HERE/'HEADER_RESULTS.json'),'header_plan_sha256':sha(HERE/'PLAN.json'),'header_batch_status':results['status'],'all_planned_jobs_attempted':True,'header_sampling_is_partial':not passed,'selected':selected,'planned_candidate_dp_id':DP,'payload_readiness_gate':plan['berv_gate'],'spectral_payload_acquisition_authorized':False}
    save(HERE/'SELECTION.json',selection,exclusive=True)
    print(json.dumps({'stage':'header','status':results['status'],'selected':len(selected),'bytes':receipt.get('bytes',0)}))

def verify_header_for_payload(plan,release):
    base_release('header')
    required=[HERE/'HEADER_RELEASE.json',HERE/'HEADER_RESULTS.json',HERE/'SELECTION.json']
    for key,path in [('header_release_sha256',required[0]),('header_results_sha256',required[1]),('selection_sha256',required[2])]:
        if release.get(key)!=sha(path):raise ValueError('Payload release mismatch: '+key)
    results=read(required[1]);selection=read(required[2])
    if results['status']!='COMPLETE' or results['plan_sha256']!=sha(HERE/'PLAN.json') or results['root_release_sha256']!=sha(required[0]) or results['code_hashes']!=plan['code_hashes']:raise ValueError('No exact complete header stage')
    if len(results['results'])!=1 or len(selection['selected'])!=1 or selection['header_results_sha256']!=sha(required[1]) or selection['header_plan_sha256']!=sha(HERE/'PLAN.json'):raise ValueError('Exactly one verified selection required')
    row=results['results'][0];item=selection['selected'][0]
    if row['dp_id']!=DP or row['target']!='HD122640' or row['status']!='PASS_RECORDED_BERV' or item['dp_id']!=DP or item['target']!='HD122640' or item['source_file_ids']!=[RAW]:raise ValueError('Header/selection identity mismatch')
    for prefix in ['body','receipt']:
        p=(HERE/row[prefix+'_path']).resolve();p.relative_to(HERE)
        if sha(p)!=row[prefix+'_sha256'] or item['header_'+prefix+'_path']!=row[prefix+'_path'] or item['header_'+prefix+'_sha256']!=row[prefix+'_sha256']:raise ValueError('Header evidence changed')
        required.append(p)
    rec=read(HERE/row['receipt_path'])
    if rec['status']!='COMPLETE' or rec['transport']['http_code']!=200 or rec['transport']['num_redirects']!=0 or rec['transport']['url_effective']!=plan['header']['url']:raise ValueError('Header request not complete')
    body=HERE/row['body_path']
    if rec['sha256']!=sha(body) or rec['bytes']!=body.stat().st_size or not 0<body.stat().st_size<524288:raise ValueError('Header body receipt mismatch')
    fresh=inspect_header(body.read_bytes(),rec['transport'].get('content_type',''),plan)
    if fresh!=row['inspection'] or fresh['status']!='PASS_RECORDED_BERV' or not fresh['large_shift_gate']['passes_all_six']:raise ValueError('Header validation/gate changed')
    if item['berv_km_s']!=fresh['berv_km_s'] or item['primary_header']!=fresh['primary_header'] or item['metadata']!=plan['job']['metadata'] or item['header_result_job_index']!=0:raise ValueError('Selected header metadata changed')
    publication(release,required)
    return item

def payload_headers(path,item,plan):
    from astropy.io import fits
    with fits.open(path,memmap=True,lazy_load_hdus=False,do_not_scale_image_data=True) as hd:
        p=hd[0].header;e=hd[1].header if len(hd)>1 else fits.Header();checks={}
        for key,value in item['primary_header'].items():
            actual=p.get(key.removeprefix('HIERARCH '))
            if isinstance(value,(int,float)) and not isinstance(value,bool):
                checks['recorded_'+key]=isinstance(actual,(int,float)) and not isinstance(actual,bool) and math.isfinite(actual) and abs(float(actual)-float(value))<=1e-8
            elif isinstance(value,bool):checks['recorded_'+key]=actual is value
            else:checks['recorded_'+key]=actual==value
        normalized={};duplicates=[]
        for card in p.cards:
            key=card.keyword
            if key in {'COMMENT','HISTORY',''}:continue
            key='HIERARCH '+key if key.startswith('ESO ') else key
            if key in normalized:duplicates.append(key)
            normalized[key]=card.value
        checks['unique_primary_keywords']=not duplicates
        identity=check_identity(normalized,plan['job'])
        checks['complete_payload_identity_and_provenance']=identity['status']=='PASS_RECORDED_BERV'
        checks['primary_identity']=p.get('ARCFILE') in {DP,DP+'.fits'} and p.get('INSTRUME')=='HARPS'
        checks['header_only_primary']=p.get('NAXIS')==0 and not isinstance(p.get('NAXIS'),bool)
        checks['HEFS_false']=p.get('ESO INS HEFS ST') is False
        checks['one_binary_table']=len(hd)==2 and e.get('XTENSION')=='BINTABLE' and e.get('NAXIS2')==1
        names=[e.get('TTYPE'+str(i)) for i in range(1,int(e.get('TFIELDS',0))+1)]
        checks['valid_unique_field_names']=all(isinstance(n,str) and n.strip() for n in names) and len({str(n).strip().casefold() for n in names})==len(names)
        fields={n:i for i,n in enumerate(names,1)};w=fields.get('WAVE',0);f=fields.get('FLUX',0)
        checks['wave_flux_err_columns']=all(n in fields for n in ['WAVE','FLUX','ERR'])
        formats=[re.fullmatch(r'([1-9][0-9]*)([BIJKED])',str(e.get('TFORM'+str(fields.get(n,0)),''))) for n in ['WAVE','FLUX','ERR']]
        checks['same_positive_fixed_real_vector_lengths']=all(formats) and len({int(m.group(1)) for m in formats if m})==1
        checks['air_angstrom_wave']=str(e.get('TUNIT'+str(w),'')).lower()=='angstrom' and 'obs.atmos' in str(e.get('TUCD'+str(w),'')).lower()
        checks['flux_adu']=str(e.get('TUNIT'+str(f),'')).lower()=='adu'
        failures=[k for k,v in checks.items() if not v]
        return {'status':'PASS_COMPATIBLE_HEADERS' if not failures else 'BLOCKED_INCOMPATIBLE_HEADERS','checks':checks,'failures':failures,'identity_inspection':identity,'new_arrays_interpreted':0}

def payload_stage(plan,release):
    item=verify_header_for_payload(plan,release)
    if (HERE/'ACQUISITION_MANIFEST.json').exists():raise FileExistsError('Preserve payload manifest')
    product,receipt_path,receipt=transfer('payload',plan)
    validation=None;status=receipt['status'];reason=receipt.get('reason')
    if status=='COMPLETE':
        try:
            validation=payload_headers(product,item,plan)
            if validation['status']!='PASS_COMPATIBLE_HEADERS':raise ValueError('Payload header compatibility failed')
        except Exception as e:status='FAILED';reason=type(e).__name__+': '+str(e)
    if validation is not None:save(HERE/'PAYLOAD_HEADER_VALIDATION.json',validation,exclusive=True)
    entry={'target':'HD122640','dp_id':DP,'status':status,'reason':reason,'local_path':relative(product),'product_path':relative(product),'bytes':receipt.get('bytes',0),'sha256':receipt.get('sha256'),'product_sha256':receipt.get('sha256'),'source_url':plan['payload']['url'],'acquisition_receipt_path':relative(receipt_path),'acquisition_receipt_sha256':sha(receipt_path)}
    manifest={'schema':'HARPS_BERV_SCIENCE_ACQUISITION_V1','status':'COMPLETE' if status=='COMPLETE' else 'STOPPED_AFTER_FAILURE','updated_utc':now(),'plan_sha256':sha(HERE/'PLAN.json'),'payload_release_sha256':sha(HERE/'PAYLOAD_RELEASE.json'),'header_results_sha256':sha(HERE/'HEADER_RESULTS.json'),'selection_sha256':sha(HERE/'SELECTION.json'),'inputs':[entry],'bytes_saved':entry['bytes'],'new_arrays_interpreted':0,'original_survey_exposures':300,'original_labels_changed':0}
    save(HERE/'ACQUISITION_MANIFEST.json',manifest,exclusive=True)
    print(json.dumps({'stage':'payload','status':status,'bytes':entry['bytes']}))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['header','payload']);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    if not args.execute:raise SystemExit('No network by default; exact published stage release and --execute required.')
    plan,release,version=base_release(args.stage)
    expected={'header':(30,524288,'https://archive.eso.org/hdr?DpId='+DP),'payload':(60,16777216,'https://dataportal.eso.org/dataPortal/file/'+DP)}
    for stage,(seconds,cap,url) in expected.items():
        spec=plan[stage]
        if (spec['timeout_seconds'],spec['max_response_bytes'],spec['url'],spec['attempts'],spec['retries'],spec['redirects'])!=(seconds,cap,url,1,0,0):raise ValueError('Frozen stage bounds differ')
    if args.stage=='header':header_stage(plan,release)
    else:payload_stage(plan,release)

if __name__=='__main__':main()
