"""Execute only the two prospectively released metadata requests; never fetch payload URLs."""
import argparse, csv, datetime, hashlib, io, json, math, re, subprocess
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(data): return hashlib.sha256(data).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(name): return json.loads((HERE/name).read_text())
def save(name,obj): (HERE/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def exclusive(name,obj):
    with (HERE/name).open('x') as f: json.dump(obj,f,indent=2);f.write('\n')
def raw_id(value):
    value=str(value or '').strip().split('/')[-1]
    for suffix in ['.fits.Z','.fits.gz','.fits','.Z']:
        if value.endswith(suffix): return value[:-len(suffix)]
    return value
def angular_arcsec(ra,dec,target):
    r1,d1,r2,d2=map(math.radians,[float(ra),float(dec),target['ra_deg'],target['dec_deg']])
    h=math.sin((d1-d2)/2)**2+math.cos(d1)*math.cos(d2)*math.sin((r1-r2)/2)**2
    return math.degrees(2*math.asin(math.sqrt(min(1,max(0,h)))))*3600
def canonical(value): return re.sub(r'\s+','',str(value)).upper()

def parse_votable(body,expected):
    if re.search(br'<!\s*(DOCTYPE|ENTITY)',body,re.I): raise ValueError('DTD/entity declarations forbidden')
    xml=ET.fromstring(body)
    local=lambda e:e.tag.split('}')[-1]
    statuses=[(x.attrib.get('value','').upper(),(x.text or '').strip()) for x in xml.iter() if local(x)=='INFO' and x.attrib.get('name','').upper()=='QUERY_STATUS']
    if not statuses or any(value!='OK' for value,_ in statuses): raise ValueError('TAP QUERY_STATUS is absent/non-OK: '+str(statuses))
    if any(any(k.split('}')[-1].lower()=='href' for k in x.attrib) for x in xml.iter() if local(x)=='STREAM'): raise ValueError('External VOTable STREAM forbidden')
    if len([x for x in xml.iter() if local(x)=='TABLE'])!=1: raise ValueError('Expected one metadata TABLE')
    from astropy.io.votable import parse
    table=parse(io.BytesIO(body),verify='exception').get_first_table().to_table(use_names_over_ids=True)
    if list(table.colnames)!=expected: raise ValueError('Metadata column contract mismatch: '+repr(table.colnames))
    if len(table)>=1000: raise ValueError('Joined row limit reached; incomplete inventory')
    rows=[]
    for row in table:
        out={}
        for key in expected:
            v=row[key]
            if getattr(v,'mask',False): out[key]=None;continue
            if hasattr(v,'item'): v=v.item()
            if isinstance(v,bytes): v=v.decode('utf-8')
            if isinstance(v,float) and not math.isfinite(v): v=None
            out[key]=v
        rows.append(out)
    return rows,statuses

def classify(rows,target,known):
    known_dp={r['dp_id'] for r in known}
    known_raw={raw_id(x) for r in known for x in r['raw_progenitor_ids']}
    groups={}
    for row in rows: groups.setdefault(str(row.get('dp_id')),[]).append(row)
    result=[]
    for dp,rr in groups.items():
        r=rr[0];reasons=[];progenitors=sorted({raw_id(x.get('source_file')) for x in rr})
        if dp in known_dp: reasons.append('existing_DP')
        if set(progenitors)&known_raw: reasons.append('existing_raw_progenitor')
        if len(progenitors)!=1 or not re.fullmatch(r'HARPS\.\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}',progenitors[0]): reasons.append('missing_or_ambiguous_raw_provenance')
        if not dp.startswith('ADP.'): reasons.append('unexpected_DP_namespace')
        consistent_fields=[k for k in r if k!='source_file']
        if any(any(x[k]!=r[k] for k in consistent_fields) for x in rr): reasons.append('inconsistent_product_metadata')
        if r.get('archive_id')!=dp or r.get('eso_category')!='SCIENCE.SPECTRUM': reasons.append('unverified_main_science_category')
        if canonical(r.get('target_name'))!=target['canonical_target']: reasons.append('target_name_identity_unresolved')
        separation=None
        try:
            ra,dec=float(r['s_ra']),float(r['s_dec'])
            if not (math.isfinite(ra) and math.isfinite(dec) and 0<=ra<360 and -90<=dec<=90): raise ValueError('Invalid equatorial coordinate')
            separation=angular_arcsec(ra,dec,target)
            if not math.isfinite(separation) or separation>target['cone_radius_arcsec']: reasons.append('outside_identity_inventory_cone')
        except (TypeError,ValueError): reasons.append('missing_coordinates')
        try:
            start,stop=float(r['t_min']),float(r['t_max'])
            if not all(map(math.isfinite,[start,stop])) or stop<=start or not (stop<=59994 or start>=60005): reasons.append('time_coverage_mismatch')
            exposure=float(r['t_exptime']);nobs=float(r['n_obs'])
            if not math.isfinite(exposure) or exposure<=0 or not math.isfinite(nobs) or nobs!=1 or r['multi_ob']!='S': reasons.append('not_single_positive_exposure')
        except (TypeError,ValueError): reasons.append('invalid_time_metadata')
        if r.get('instrument_name')!='HARPS' or r.get('obs_collection')!='HARPS' or r.get('dataproduct_type')!='spectrum': reasons.append('instrument_product_mismatch')
        date=r.get('obs_release_date')
        try:
            released=datetime.datetime.fromisoformat(str(date).replace('Z','+00:00'))
            if released.tzinfo is None: released=released.replace(tzinfo=datetime.timezone.utc)
            if released>datetime.datetime(2026,11,2,tzinfo=datetime.timezone.utc): reasons.append('not_public_at_fixed_cutoff')
        except ValueError: reasons.append('missing_public_release_date')
        result.append(dict(dp_id=dp,target=target['canonical_target'],source_file_ids=progenitors,query_rows=len(rr),coordinate_separation_arcsec=separation,metadata=r,
                           status='METADATA_CANDIDATE_PENDING_HEADER_IDENTITY_BERV' if not reasons else 'EXCLUDED_METADATA',reasons=reasons))
    # Exact raw identity, not morphology, determines duplicated products.
    seen={}
    for r in sorted(result,key=lambda x:x['dp_id']):
        if r['status'].startswith('METADATA_CANDIDATE'):
            raw=r['source_file_ids'][0]
            if raw in seen:
                r['reasons'].append('duplicate_new_raw_progenitor');r['status']='EXCLUDED_METADATA';r['retained_dp_id']=seen[raw]
            else: seen[raw]=r['dp_id']
    return sorted(result,key=lambda x:(float(x['metadata'].get('t_min') or 0),x['dp_id']))

def acquire(req,plan):
    target=req['target'];prefix='responses/'+target
    exclusive(target+'.ATTEMPT_STARTED.json',dict(started_utc=now(),target=target,attempt=1))
    query=(HERE/req['query_file']).read_bytes()
    assert sha(query)==req['query_sha256']
    form=dict(req['form']);form['QUERY']=query.decode()
    body=urllib.parse.urlencode(form).encode()
    output=HERE/(prefix+'.vot');headers=HERE/(prefix+'.headers')
    args=['curl','--disable','--silent','--show-error','--request','POST','--proto','=https','--proto-redir','=https',
          '--max-redirs','0','--retry','0','--max-time','30','--connect-timeout','15','--max-filesize','4194304',
          '--header','Content-Type: application/x-www-form-urlencoded','--header','Accept: application/x-votable+xml',
          '--header','Accept-Encoding: identity','--user-agent','SETI-HARPS-metadata/1.0',
          '--data-binary','@-','--output',str(output),'--dump-header',str(headers),'--write-out','%{json}',req['endpoint']]
    receipt=dict(target=target,started_utc=now(),endpoint=req['endpoint'],method='POST',attempt=1,request_body_bytes=len(body),request_body_sha256=sha(body),query_sha256=sha(query),limits=plan['limits'],command=args,science_payload_requested=False)
    try:
        proc=subprocess.run(args,input=body,capture_output=True,timeout=35,check=False)
        receipt['curl_returncode']=proc.returncode
        (HERE/(prefix+'.stderr')).write_bytes(proc.stderr)
        (HERE/(prefix+'.curl.json')).write_bytes(proc.stdout)
        stats=json.loads(proc.stdout) if proc.stdout else {}
        receipt['transport']=stats
        if proc.returncode!=0: raise RuntimeError('curl failed with return code '+str(proc.returncode))
        if stats.get('http_code')!=200 or stats.get('num_redirects')!=0 or stats.get('url_effective')!=req['endpoint']: raise RuntimeError('HTTP/status/redirect contract failed')
        response=output.read_bytes()
        if len(response)>=plan['limits']['response_bytes_per_target']: raise RuntimeError('Response byte cap reached; incomplete')
        rows,statuses=parse_votable(response,req['expected_columns'])
        receipt.update(status='COMPLETE_METADATA_RESPONSE',returned_joined_rows=len(rows),tap_status=statuses)
        return rows,receipt
    except Exception as e:
        receipt.update(status='STOPPED_REQUEST_FAILURE',error=type(e).__name__+': '+str(e))
        return None,receipt
    finally:
        receipt['finished_utc']=now()
        if output.exists(): receipt.update(response_bytes=output.stat().st_size,response_sha256=sha(output.read_bytes()))
        save(prefix+'.REQUEST.json',receipt)

def check_release():
    freeze_bytes=(HERE/'PREFLIGHT_FREEZE.json').read_bytes();freeze=json.loads(freeze_bytes)
    for name,rec in freeze['files'].items():
        data=(HERE/name).read_bytes();assert sha(data)==rec['sha256'] and len(data)==rec['bytes'],name
    plan=read('PLAN.json')
    for name,h in plan['source_hashes'].items(): assert sha((ROOT/name).read_bytes())==h,name
    release=read('ROOT_RELEASE.json')
    assert release['freeze_sha256']==sha(freeze_bytes) and release['remote_bytes_verified'] is True
    assert re.fullmatch('[0-9a-f]{40}',release['prospective_commit'])
    curl=subprocess.run(['curl','--disable','--version'],capture_output=True,text=True,check=True).stdout
    version=re.search(r'curl (\d+)\.(\d+)\.(\d+)',curl)
    assert version and tuple(map(int,version.groups()))>=(8,4,0),'curl hard streaming cap requires>=8.4'
    return plan,release,curl

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    if not args.execute: raise SystemExit('No network by default. --execute and a verified ROOT_RELEASE.json are required.')
    plan,release,curl=check_release()
    exclusive('RUN_STARTED.json',dict(started_utc=now(),release=release,curl_version=curl))
    (HERE/'responses').mkdir(exist_ok=False)
    targets={x['canonical_target']:x for x in read('TARGETS.json')};known=read('EXISTING_300.json');results=[];inventory=[]
    for req in plan['requests']:
        rows,receipt=acquire(req,plan);results.append(receipt)
        if rows is None: break
        save('responses/'+req['target']+'.ROWS.json',rows)
        classified=classify(rows,targets[req['target']],known);inventory.extend(classified)
        save('responses/'+req['target']+'.INVENTORY.json',classified)
    candidates=[r for r in inventory if r['status'].startswith('METADATA_CANDIDATE')]
    save('CANDIDATES.json',candidates);save('ALL_RETURNED_PRODUCTS.json',inventory)
    save('SUMMARY.json',dict(status='COMPLETE_BOUNDED_METADATA' if len(results)==2 and all(r['status']=='COMPLETE_METADATA_RESPONSE' for r in results) else 'STOPPED_BOUNDED_METADATA',completed_utc=now(),target_requests=len(results),returned_products=len(inventory),metadata_candidates=len(candidates),per_target={t:dict(returned_products=sum(r['target']==t for r in inventory),metadata_candidates=sum(r['target']==t for r in candidates)) for t in targets},science_payload_bytes=0,original_label_changes=0,request_statuses=[r['status'] for r in results],berv_not_measured=True,next_gate='Freeze bounded header-only identity/BERV retrieval separately if metadata candidates exist; no science acquisition authorized by this result.'))

if __name__=='__main__': main()
