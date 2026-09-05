#!/usr/bin/env python3
"""Bounded archive metadata and previously retained pointing/time geometry."""
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen

from ls4g_synthetic_recovery import encoded,verify_manifest
from ls4i_measured_digital_injections import write_json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_ls4o_control_feasibility'


def load(name):return json.loads((ROOT/name).read_text())


def packed_angle(value,ra=False):
    """SIGPROC HHMMSS.S / signed DDMMSS.S, with explicit field validation."""
    if not math.isfinite(value):raise ValueError('nonfinite angle')
    sign=-1 if value<0 else 1;v=abs(value)
    major=int(v//10000);minute=int((v-major*10000)//100);second=v-major*10000-minute*100
    if minute>=60 or not 0<=second<60 or (ra and (sign<0 or major>=24)) or (not ra and (major>90 or (major==90 and (minute or second)))):
        raise ValueError('invalid sexagesimal field')
    return sign*(major+minute/60+second/3600)*(15 if ra else 1)


def separation_deg(ra1,dec1,ra2,dec2):
    a,b=map(math.radians,(dec1,dec2));d=math.radians(ra2-ra1)
    h=math.sin((b-a)/2)**2+math.cos(a)*math.cos(b)*math.sin(d/2)**2
    return math.degrees(2*math.asin(math.sqrt(min(1,max(0,h)))))


def interval_metrics(start1,duration1,start2,duration2):
    if duration1<=0 or duration2<=0:raise ValueError('nonpositive duration')
    end1=start1+duration1;end2=start2+duration2
    return {'overlap_s':max(0.,min(end1,end2)-max(start1,start2)),
            'gap_s':max(0.,max(start1,start2)-min(end1,end2))}


def known_geometry(config):
    preflight=load('results_ls4a_header/preflight.json')
    split=load('config/ls4h_transfer_preflight.json')
    x=next(c for c in preflight['cadences'] if c['band']=='X')
    scans=[];reference=split['scans'][0]['expected_tstart_mjd']
    for scan in split['scans']:
        h=x['headers'][scan['high_time_resolution']['url']]
        if h['source_name']!=scan['expected_source_name'] or abs(h['tstart_mjd']-scan['expected_tstart_mjd'])>1e-9:
            raise ValueError('retained header identity differs')
        scans.append({'label':scan['label'],'role':scan['role'],'source_name':h['source_name'],
            'start_mjd':h['tstart_mjd'],'start_relative_s':(h['tstart_mjd']-reference)*86400,
            'duration_s':h['ntime']*h['tsamp_s'],'ra_deg':packed_angle(h['header']['src_raj'],True),
            'dec_deg':packed_angle(h['header']['src_dej']),
            'partition':scan['ls4h_partition'],'medium_previously_searched':True,
            'htr_previously_read_in_development':scan['label'] in split['development_labels']})
    lookup={s['label']:s for s in scans};pairs=[]
    for original in split['scans']:
        on=lookup[original['label']]
        for label in original['adjacent_off_labels']:
            off=lookup[label]
            pairs.append({'on':on['label'],'off':label,
                'angular_separation_deg':separation_deg(on['ra_deg'],on['dec_deg'],off['ra_deg'],off['dec_deg']),
                **interval_metrics(on['start_relative_s'],on['duration_s'],off['start_relative_s'],off['duration_s'])})
    bands=[]
    for cadence in preflight['cadences']:
        headers=[h for h in cadence['headers'].values() if h.get('nbits')==8]
        bands.append({'band':cadence['band'],'cadence_url':cadence['cadence_url'],
            'start_mjd':min(h['tstart_mjd'] for h in headers),
            'end_mjd':max(h['tstart_mjd']+h['ntime']*h['tsamp_s']/86400 for h in headers),
            'native_center_low_mhz':min(h['frequency_low_mhz'] for h in headers),
            'native_center_high_mhz':max(h['frequency_high_mhz'] for h in headers),
            'contains_8500_mhz':all(h['frequency_low_mhz']<=8500<=h['frequency_high_mhz'] for h in headers),
            'contains_10500_mhz':all(h['frequency_low_mhz']<=10500<=h['frequency_high_mhz'] for h in headers)})
    return {'scans':scans,'adjacent_pairs':pairs,'known_bands':bands,
        'on_start_offsets_s':[s['start_relative_s'] for s in scans if s['role']=='ON'],
        'simultaneous_on_off_pairs':sum(p['overlap_s']>0 for p in pairs),
        'reserved_htr_full_download_bytes':sum(s['high_time_resolution']['expected_size_bytes'] for s in split['scans'] if s['label'] in split['reserved_validation_labels']),
        'reserved_medium_plus_htr_full_download_bytes':sum(s[k]['expected_size_bytes'] for s in split['scans'] if s['label'] in split['reserved_validation_labels'] for k in ('medium_resolution','high_time_resolution'))}


def queries(config):
    result=[{'kind':'target_only','alias':alias,'params':{'target':alias,'limit':str(config['network']['record_limit'])}} for alias in config['aliases']]
    result.append({'kind':'historical_restricted_control','alias':'LHS1140','params':{'target':'LHS1140','limit':str(config['network']['record_limit']),'telescope':'GBT','cadence':'True','primaryTarget':'True'}})
    return result


def fetch(query,config):
    url=config['network']['endpoint']+'?'+urlencode(query['params'])
    record={**query,'requested_url':url,'retrieved_utc':datetime.now(timezone.utc).isoformat(),'spectral_values_read':False}
    try:
        request=Request(url,headers={'User-Agent':'setisearch-ls4o/1.0','Accept':'application/json'})
        with urlopen(request,timeout=config['network']['timeout_s']) as response:
            record['http_status']=response.status;record['final_url']=response.url
            data=response.read(config['network']['max_response_bytes']+1)
        if len(data)>config['network']['max_response_bytes']:raise ValueError('metadata response byte cap exceeded')
        record.update({'response_text':data.decode('utf-8'),'response_bytes':len(data),
            'payload_sha256':hashlib.sha256(data).hexdigest()})
        value=json.loads(data)
        if not isinstance(value,dict) or value.get('result')!='success' or not isinstance(value.get('data'),list):
            raise ValueError('API did not return a successful data list')
        record.update({'response':value,'payload_sha256':hashlib.sha256(data).hexdigest(),'response_bytes':len(data),
            'successful':True,'record_limit_reached':len(value['data'])>=config['network']['record_limit']})
    except Exception as exc:record.update({'successful':False,'error':str(exc)})
    return record


def normalized(value):return ''.join(c for c in str(value).upper() if c.isalnum())


def inventory(receipts,config):
    accepted={normalized(a) for a in config['aliases']};records={};excluded=0;conflicts=[]
    for receipt in receipts:
        if not receipt['successful']:continue
        for r in receipt['response']['data']:
            if normalized(r.get('target','')) not in accepted:excluded+=1;continue
            url=r.get('url')
            if not url:raise ValueError('accepted record has no product URL')
            if url in records:
                for field in ('target','telescope','mjd','size','center_freq'):
                    if r.get(field)!=records[url]['record'].get(field):conflicts.append({'url':url,'field':field})
                records[url]['query_indices'].append(receipts.index(receipt))
            else:records[url]={'record':r,'query_indices':[receipts.index(receipt)]}
    scans={}
    for item in records.values():
        r=item['record'];mjd=float(r['mjd']);freq=float(r['center_freq'])
        key=(r.get('telescope'),normalized(r['target']),mjd,round(freq/100)*100)
        scan=scans.setdefault(key,{'telescope':r.get('telescope'),'target':r['target'],'mjd':mjd,
            'frequency_group_anchor_mhz':key[-1],'products':[]})
        scan['products'].append({'url':r['url'],'size_bytes':r.get('size'),'center_frequency_mhz':freq,'cadence_url':r.get('cadence_url')})
    rows=sorted(scans.values(),key=lambda r:(r['mjd'],r['frequency_group_anchor_mhz'],r['telescope'] or ''))
    for row in rows:
        products=row['products']
        row['has_medium_product']=any(p['url'].endswith(('.gpuspec.0002.fil','.gpuspec.0002.h5')) for p in products)
        row['has_htr_product']=any(p['url'].endswith(('.gpuspec.8.0001.fil','.gpuspec.0001.h5')) for p in products)
        row['x_center_metadata_candidate']=all(8000<=p['center_frequency_mhz']<=12000 for p in products)
        # A >=24-hour separation is a screening criterion, not proof of statistical independence.
        row['separated_by_at_least_one_day']=abs(row['mjd']-config['original_x_start_mjd'])>=config['minimum_epoch_separation_days']
    candidates=[r for r in rows if r['x_center_metadata_candidate'] and r['separated_by_at_least_one_day']]
    target_receipts=[r for r in receipts if r['kind']=='target_only']
    restricted=next(r for r in receipts if r['kind']=='historical_restricted_control')
    expanded_urls={r['url'] for p in target_receipts if p['successful'] for r in p['response']['data'] if r.get('url')}
    restricted_urls={r['url'] for r in restricted.get('response',{}).get('data',[]) if r.get('url')}
    return {'query_count':len(receipts),'successful_queries':sum(r['successful'] for r in receipts),
        'record_limit_reached_queries':sum(r.get('record_limit_reached',False) for r in receipts),
        'unique_accepted_products':len(records),'unique_scan_frequency_groups':len(rows),
        'excluded_nonmatching_records':excluded,'metadata_conflicts':conflicts,
        'target_only_additional_product_urls':len(expanded_urls-restricted_urls),
        'restricted_products_missing_from_target_queries':sorted(restricted_urls-expanded_urls),
        'telescope_names':sorted({r['telescope'] for r in rows}),
        'observing_mjd_range':[min(r['mjd'] for r in rows),max(r['mjd'] for r in rows)] if rows else None,
        'candidate_later_or_earlier_x_scan_groups':candidates,'scan_groups':rows,
        'no_spectral_values_read':True,'metadata_is_not_confirmed_band_coverage':True}


def main():
    verify_manifest(ROOT/'LS4O_FREEZE.sha256');config=load('config/ls4o_control_feasibility.json')
    for name,expected in config['input_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:raise ValueError('input differs '+name)
    OUT.mkdir(exist_ok=False);receipts=[]
    try:
        geometry=known_geometry(config);write_json(OUT/'known_geometry.json',geometry)
        for i,query in enumerate(queries(config)):
            receipt=fetch(query,config);receipts.append(receipt)
            write_json(OUT/f'query_{i:02d}.json',receipt)
            write_json(OUT/'checkpoint.json',{'completed_queries':len(receipts),'successful_queries':sum(r['successful'] for r in receipts)})
            print(f"query {i+1}/{len(queries(config))}: {query['alias']} {query['kind']} success={receipt['successful']} rows={len(receipt.get('response',{}).get('data',[]))}",flush=True)
        result=inventory(receipts,config)
        complete=result['successful_queries']==len(receipts) and not result['record_limit_reached_queries'] and not result['metadata_conflicts'] and not result['restricted_products_missing_from_target_queries']
        result.update({'status':'scoped-metadata-feasibility-complete' if complete else 'incomplete-metadata-feasibility',
            'known_geometry':geometry,'freeze_sha256':hashlib.sha256((ROOT/'LS4O_FREEZE.sha256').read_bytes()).hexdigest(),
            'new_spectral_bytes_read':0,'reserved_htr_opened':False,'sky_candidates_promoted':0,
            'independent_confirmation_obtained':False})
        result['result_sha256']=hashlib.sha256(encoded(result)).hexdigest()
        write_json(OUT/'feasibility.json',result)
        print(json.dumps({k:v for k,v in result.items() if k not in ('known_geometry','scan_groups')},indent=2),flush=True)
    except Exception as exc:
        write_json(OUT/'abort.json',{'status':'aborted-no-complete-conclusion','error':str(exc),'completed_queries':len(receipts)})
        raise


if __name__=='__main__':main()
