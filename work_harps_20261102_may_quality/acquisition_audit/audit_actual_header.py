"""Independent local HTML/card and scalar audit; no production imports, network or arrays."""
import datetime, hashlib, html, json, math, re
from pathlib import Path
HERE=Path(__file__).resolve().parent
ACQ=HERE.parent/'acquisition'
def read(p): return json.loads(p.read_bytes())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
def ck(name, passed):
    checks.append({'check':name,'pass':bool(passed)})
p=read(ACQ/'PLAN.json'); results=read(ACQ/'HEADER_RESULTS.json'); sel=read(ACQ/'SELECTION.json')
row=results['results'][0]; body=ACQ/row['body_path']; rp=ACQ/row['receipt_path']; rec=read(rp)
ck('one completed request',results['status']=='COMPLETE' and results['requests_attempted']==1 and len(results['results'])==1)
ck('plan release and code binding',results['plan_sha256']==sha(ACQ/'PLAN.json') and results['root_release_sha256']==sha(ACQ/'HEADER_RELEASE.json') and results['code_hashes']==p['code_hashes'])
ck('body exact bytes and hashes',0<body.stat().st_size<524288 and body.stat().st_size==rec['bytes']==results['response_bytes'] and sha(body)==row['body_sha256']==rec['sha256'])
ck('receipt exact hash',sha(rp)==row['receipt_sha256'])
t=rec['transport'];ck('HTTP200 no redirect exact URL',rec['status']=='COMPLETE' and rec['curl_returncode']==0 and t['http_code']==200 and t['num_redirects']==0 and t['url_effective']==p['header']['url'])
ck('one attempt no retry',rec['attempts']==1 and rec['retries']==0 and rec['redirects_followed']==0)
ck('header deadline and transfer bytes',t['time_total']<=30 and t['size_download']==body.stat().st_size)
cmd=rec['command'];ck('recorded bounded command',cmd[cmd.index('--max-time')+1]=='30' and cmd[cmd.index('--max-filesize')+1]=='524288' and cmd[cmd.index('--retry')+1]=='0' and cmd[cmd.index('--max-redirs')+1]=='0' and '-L' not in cmd and '--location' not in cmd)
blocks=re.findall(r'<pre\b[^>]*>(.*?)</pre\s*>',body.read_text(),re.I|re.S)
ck('one header PRE',len(blocks)==1)
lines=html.unescape(blocks[0]).splitlines(); cards={}; duplicate=[]; inside=False; ended=False
for line in lines:
    if line.startswith('SIMPLE  ='): inside=True
    if not inside: continue
    if line.strip()=='END': ended=True;break
    if '=' not in line: continue
    key,value=line.split('=',1);key=key.strip();value=value.lstrip()
    if key in {'COMMENT','HISTORY',''}: continue
    if key in cards:duplicate.append(key)
    if value.startswith("'"):
        m=re.match(r"'((?:[^']|'')*)'",value)
        if not m:raise ValueError('Malformed quoted card '+key)
        value=m.group(1).replace("''", "'").rstrip()
    else:
        value=value.split('/',1)[0].strip()
        if value in {'T','F'}:value=value=='T'
        elif re.fullmatch(r'[+-]?\d+',value):value=int(value)
        else:
            try:value=float(value.replace('D','E'))
            except ValueError:pass
    cards[key]=value
ck('primary SIMPLE END unique keys',inside and ended and cards.get('SIMPLE') is True and not duplicate)
job=p['job'];md=job['metadata'];raw=job['source_file_ids'][0]
ck('exact ADP instrument target',cards['ARCFILE']==job['dp_id']+'.fits' and cards['INSTRUME']=='HARPS' and re.sub(r'\s','',cards['OBJECT']).upper()=='HD122640')
ck('single exposure high resolution barycentric',cards['NCOMBINE']==1 and not isinstance(cards['NCOMBINE'],bool) and cards['SPEC_RES']==115000 and cards['SPECSYS']=='BARYCENT' and cards['HIERARCH ESO INS HEFS ST'] is False and cards['NAXIS']==0)
prov={k:v for k,v in cards.items() if re.fullmatch(r'PROV\d+',k)}
ck('complete one raw progenitor',len(prov)==1 and next(iter(prov.values())).removesuffix('.fits')==raw)
ck('valid finite coordinates',all(isinstance(cards[k],(float,int)) and not isinstance(cards[k],bool) and math.isfinite(cards[k]) for k in ['RA','DEC']) and 0<=cards['RA']<360 and -90<=cards['DEC']<=90)
sep=3600*math.hypot((cards['RA']-md['s_ra'])*math.cos(math.radians(md['s_dec'])),cards['DEC']-md['s_dec'])
ck('metadata position tolerance',sep<=1)
dt=datetime.datetime.fromisoformat(cards['DATE-OBS']).replace(tzinfo=datetime.timezone.utc)
rawdt=datetime.datetime.fromisoformat(raw.removeprefix('HARPS.')).replace(tzinfo=datetime.timezone.utc)
mjd=(dt-datetime.datetime(1858,11,17,tzinfo=datetime.timezone.utc)).total_seconds()/86400
ck('raw timestamp and MJD agreement',abs((dt-rawdt).total_seconds())<=.02 and abs(cards['MJD-OBS']-md['t_min'])<=1e-7 and abs(mjd-cards['MJD-OBS'])*86400<=.02)
ck('exposure agreement',abs(cards['EXPTIME']-md['t_exptime'])<=.02)
berv=cards['HIERARCH ESO DRS BERV'];ck('finite sane BERV',isinstance(berv,(float,int)) and not isinstance(berv,bool) and math.isfinite(berv) and abs(berv)<=100)
threshold=10*299792.458/115000; deltas=[]
for event in p['berv_gate']['discovery_events']:
    delta=abs(berv-event['discovery_berv_km_s']);deltas.append({'candidate_id':event['candidate_id'],'delta_km_s':delta,'passes':delta>=threshold})
    observed=next(x for x in row['inspection']['large_shift_gate']['per_event'] if x['candidate_id']==event['candidate_id'])
    ck('independent BERV delta '+event['candidate_id'],delta==observed['absolute_delta_km_s'] and delta>=threshold and observed['passes'] is True)
ck('recorded primary values match independent cards',all(cards.get(k)==v for k,v in row['inspection']['primary_header'].items()))
ck('selection exactly one same released candidate',len(sel['selected'])==1 and sel['selected'][0]['dp_id']==job['dp_id'] and sel['selected'][0]['source_file_ids']==job['source_file_ids'] and sel['selected'][0]['metadata']==md)
i=sel['selected'][0]
ck('selection original evidence bindings',sel['header_results_sha256']==sha(ACQ/'HEADER_RESULTS.json') and sel['header_plan_sha256']==sha(ACQ/'PLAN.json') and i['header_body_sha256']==sha(body) and i['header_receipt_sha256']==sha(rp) and i['berv_km_s']==berv)
report={'schema':'HARPS_MAY_QUALITY_ACTUAL_HEADER_AUDIT_V1','status':'PASS' if all(c['pass'] for c in checks) else 'FAIL','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'implementation':'Independent stdlib HTML-PRE and scalar FITS-card parser, with no production imports. Only saved header and metadata bytes read.','script_sha256':sha(Path(__file__)),'plan_sha256':sha(ACQ/'PLAN.json'),'header_results_sha256':sha(ACQ/'HEADER_RESULTS.json'),'body_sha256':sha(body),'body_bytes':body.stat().st_size,'receipt_sha256':sha(rp),'checks':checks,'check_count':len(checks),'berv_km_s':berv,'threshold_km_s':threshold,'per_event':deltas,'delta_range_km_s':[min(x['delta_km_s'] for x in deltas),max(x['delta_km_s'] for x in deltas)],'pipeline':cards['PROCSOFT'],'network_requests_by_auditor':0,'spectral_arrays_read_by_auditor':0,'representation_status':'PROVISIONAL: actual payload table headers remain required before arrays.'}
(HERE/'ACTUAL_HEADER_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['status','check_count','berv_km_s','delta_range_km_s']}))
assert report['status']=='PASS'
