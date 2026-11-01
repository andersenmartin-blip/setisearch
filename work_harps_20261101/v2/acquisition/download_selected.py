#!/usr/bin/env python3
"""Acquire the frozen V2 cohorts, inspecting headers only, never science arrays."""
from __future__ import annotations
import concurrent.futures
import csv
import datetime
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import threading
import time
import urllib.error
import urllib.request

V2=Path(__file__).resolve().parents[1]
BASE=V2.parent
OUT=V2/'acquisition'
BYTE_CAP=2_000_000_000
FILE_CAP=12_000_000
LOCK=threading.Lock()
TOTAL_BYTES=0
START=time.monotonic()
PARSER=BASE/'acquisition/download_selected.py'
spec=importlib.util.spec_from_file_location('frozen_header_parser',PARSER)
old=importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,d): p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def norm(v): return re.sub(r'[^A-Z0-9]','',str(v).upper())
def sex(v,hours=False):
    x=abs(float(v));a=int(x//10000);b=int((x-a*10000)//100);c=x-a*10000-b*100
    if b>=60 or c>=60: raise ValueError('Invalid compact coordinate')
    return (-1 if float(v)<0 else 1)*(a+b/60+c/3600)*(15 if hours else 1)
def separation(a,b,c,d):
    ra=((a-c+180)%360-180)*math.cos(math.radians((b+d)/2))
    return 3600*math.hypot(ra,b-d)

def inspect(path,row,context):
    report=old.inspect(path,row,context['upstream'])
    with path.open('rb') as f:
        h=old.read_header(f)
        ext=old.read_header(f)
    target={k:v for k,v in h.items() if 'TARG' in k or k in ('OBJECT','RA','DEC','RADECSYS','EQUINOX','DATE-OBS','MJD-OBS','EXPTIME')}
    ra=sex(h['HIERARCH ESO TEL TARG ALPHA'],True);dec=sex(h['HIERARCH ESO TEL TARG DELTA'])
    prior=context['old_targets'][row['canonical_target']]
    offsets=[separation(ra,dec,x['tel_targ_alpha_decimal_deg'],x['tel_targ_delta_decimal_deg']) for x in prior]
    same_epoch=all(h.get('HIERARCH ESO TEL TARG EQUINOX')==x['header'].get('HIERARCH ESO TEL TARG EQUINOX') and h.get('HIERARCH ESO TEL TARG EPOCH')==x['header'].get('HIERARCH ESO TEL TARG EPOCH') for x in prior)
    prior_raw_matches=sorted(set(report['raw_progenitor_ids']) & context['old_raw_ids'])
    checks=report['checks']
    checks.update({
        'not_old_adp':row['dp_id'] not in context['old_adp_ids'],
        'not_old_target_start':(row['canonical_target'],float(row['t_min'])) not in context['old_time_keys'],
        'not_old_raw_progenitor':not prior_raw_matches,
        'exactly_one_raw_progenitor':len(report['raw_progenitor_ids'])==1,
        'intended_target_name_matches':norm(h.get('HIERARCH ESO OBS TARG NAME'))==norm(row['canonical_target']),
        'intended_coordinate_same_epoch_as_old':same_epoch,
        'intended_coordinate_within_1_arcsec_of_old':min(offsets)<=1.0,
        'barycentric_frame':h.get('SPECSYS')=='BARYCENT',
        'air_wavelength_ucd':ext.get('TUCD1')=='em.wl;obs.atmos',
        'angstrom_wave_unit':str(ext.get('TUNIT1')).lower() in ('angstrom','angstroms','angstroem'),
        'adu_flux_unit':str(ext.get('TUNIT2')).lower()=='adu',
        'uncalibrated_flux':h.get('FLUXCAL')=='UNCALIBRATED',
    })
    report.update(header_status='PASS_METADATA_ONLY' if all(checks.values()) else 'EXCLUDED_PENDING_REVIEW',
        old_raw_matches=prior_raw_matches,intended_target_header=target,
        tel_targ_alpha_decimal_deg=ra,tel_targ_delta_decimal_deg=dec,
        nearest_old_intended_coordinate_arcsec=min(offsets),
        identity_limitation='Internal metadata and intended-coordinate consistency only; no independent absolute pointing or photon-origin verification.')
    return report

def fetch(row,context):
    global TOTAL_BYTES
    folder='main' if row['role']=='v2_main_unopened' else 'validation'
    path=V2/'data'/folder/(row['dp_id'].replace(':','_')+'.fits')
    path.parent.mkdir(parents=True,exist_ok=True)
    rp=OUT/'receipts'/(row['dp_id'].replace(':','_')+'.json')
    url='https://dataportal.eso.org/dataPortal/file/'+row['dp_id']
    rec=dict(dp_id=row['dp_id'],canonical_target=row['canonical_target'],role=row['role'],
             source_url=url,path=str(path),relative_path=str(path.relative_to(BASE)),started_utc=now(),attempts=[])
    if path.exists() or rp.exists():
        raise RuntimeError('Refusing to overwrite existing acquisition: '+str(path))
    for timeout in (20,60):
        if time.monotonic()-START>900:
            rec['download_status']='NOT_RUN_WALL_BOUND';break
        attempt=dict(started_utc=now(),timeout_seconds=timeout);start=time.monotonic()
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'SETI-HARPS-pilot/2.0 (public archive research)'})
            chunks=[];size=0
            with urllib.request.urlopen(req,timeout=timeout) as response:
                attempt['http_status']=response.status
                attempt['response_headers']={k:response.headers.get(k) for k in ('Content-Type','Content-Length','Content-Disposition','Last-Modified')}
                while True:
                    with LOCK:
                        if TOTAL_BYTES>=BYTE_CAP:raise RuntimeError('Total transfer cap reached')
                    block=response.read(1_048_576)
                    if not block:break
                    size+=len(block)
                    with LOCK:
                        TOTAL_BYTES+=len(block)
                        if TOTAL_BYTES>BYTE_CAP:raise RuntimeError('Total transfer cap exceeded')
                    if size>FILE_CAP:raise RuntimeError('Per-file cap exceeded')
                    chunks.append(block)
            payload=b''.join(chunks)
            if not payload.startswith(b'SIMPLE  ') or len(payload)%2880:raise ValueError('Invalid padded FITS response')
            expected=attempt['response_headers']['Content-Length']
            if expected and int(expected)!=len(payload):raise ValueError('Content-Length mismatch')
            partial=path.with_suffix('.part');partial.write_bytes(payload);partial.replace(path)
            rec.update(download_status='DOWNLOADED',bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())
            rec.update(inspect(path,row,context))
            attempt.update(outcome='SUCCESS',elapsed_seconds=time.monotonic()-start)
            rec['attempts'].append(attempt);break
        except Exception as error:
            attempt.update(outcome='FAILED',error_type=type(error).__name__,error=str(error),elapsed_seconds=time.monotonic()-start)
            rec['attempts'].append(attempt);rec['download_status']='FAILED'
            if path.exists():
                rec.update(download_status='DOWNLOADED_HEADER_REVIEW_FAILED',header_status='EXCLUDED_PENDING_REVIEW');break
            if isinstance(error,urllib.error.HTTPError) and error.code in (401,403,404):break
            if 'cap' in str(error).lower():break
    rec['finished_utc']=now();dump(rp,rec)
    print(json.dumps({k:rec.get(k) for k in ('dp_id','role','download_status','header_status')}),flush=True)
    return rec

def main():
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'receipts').mkdir(exist_ok=True)
    freeze_path=V2/'selection/SELECTION_FREEZE.json'
    freeze=json.loads(freeze_path.read_text());rows=[]
    for filename,role in [('VALIDATION4.csv','v2_validation_unopened'),('MAIN100.csv','v2_main_unopened')]:
        p=V2/'selection'/filename
        assert sha(p)==freeze['frozen_selection_hashes'][filename]
        rows.extend(dict(r,role=role) for r in csv.DictReader(p.open()))
    oldrows=list(csv.DictReader((BASE/'selection/MAIN100.csv').open()))+list(csv.DictReader((BASE/'selection/DEVELOPMENT_AND_VALIDATION.csv').open()))
    oldmanifest=json.loads((BASE/'acquisition/DOWNLOAD_MANIFEST.json').read_text())
    targetcontext=json.loads((BASE/'acquisition/TARGET_COORDINATE_HEADERS.json').read_text())['files']
    old_targets={}
    for entry in targetcontext:old_targets.setdefault(entry['canonical_target'],[]).append(entry)
    context=dict(upstream=json.loads((BASE/'literature/UPSTREAM_REFERENCED_IDS.json').read_text()),
        old_adp_ids={r['dp_id'] for r in oldrows},old_time_keys={(r['canonical_target'],float(r['t_min'])) for r in oldrows},
        old_raw_ids={x for r in oldmanifest for x in r['raw_progenitor_ids']},old_targets=old_targets)
    assert len(rows)==104 and len({r['dp_id'] for r in rows})==104
    assert all(r['dp_id'] not in context['old_adp_ids'] and (r['canonical_target'],float(r['t_min'])) not in context['old_time_keys'] for r in rows)
    for name,expected in freeze['input_hashes'].items():assert sha(BASE/name)==expected,name
    scope=dict(status='FROZEN_BEFORE_DOWNLOAD_AND_FLUX_ACCESS',created_utc=now(),selection_freeze_sha256=sha(freeze_path),
        code_sha256=sha(Path(__file__)),header_parser_sha256=sha(PARSER),max_workers=3,attempt_timeouts_seconds=[20,60],
        total_transfer_byte_cap=BYTE_CAP,per_file_byte_cap=FILE_CAP,wall_start_bound_seconds=900,
        selected_files=104,selected_main=100,selected_validation=4,prior_excluded_exposures=105,
        prior_excluded_raw_ids=sorted(context['old_raw_ids']),new_science_arrays_opened=0,
        failure_rule='Keep failed rows without replacements; input/metadata/provenance checks determine usability before any science read.')
    dump(OUT/'ACQUISITION_SCOPE.json',scope)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        receipts=list(pool.map(lambda row:fetch(row,context),rows))
    counts={}
    raw_to_ids={}
    for r in receipts:
        for raw in r.get('raw_progenitor_ids',[]):raw_to_ids.setdefault(raw,[]).append(r['dp_id'])
    duplicates={raw:ids for raw,ids in raw_to_ids.items() if len(ids)>1}
    for r in receipts:
        if 'checks' in r:
            r['checks']['unique_raw_within_v2_cohorts']=all(raw not in duplicates for raw in r.get('raw_progenitor_ids',[]))
            r['header_status']='PASS_METADATA_ONLY' if all(r['checks'].values()) else 'EXCLUDED_PENDING_REVIEW'
            dump(OUT/'receipts'/(r['dp_id'].replace(':','_')+'.json'),r)
        key=r.get('header_status',r['download_status']);counts[key]=counts.get(key,0)+1
    dump(OUT/'DOWNLOAD_MANIFEST.json',receipts)
    fields=['dp_id','canonical_target','role','download_status','header_status','bytes','sha256','path','relative_path','source_url','raw_progenitor_ids','upstream_raw_matches','old_raw_matches']
    with (OUT/'DOWNLOAD_MANIFEST.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for r in receipts:writer.writerow({k:json.dumps(r[k]) if isinstance(r.get(k),(dict,list)) else r.get(k,'') for k in fields})
    summary=dict(finished_utc=now(),elapsed_seconds=time.monotonic()-START,network_payload_bytes=TOTAL_BYTES,
        selected_files=104,result_counts=counts,new_raw_duplicates=duplicates,distinct_new_raw_ids=len(raw_to_ids),
        manifest_sha256=sha(OUT/'DOWNLOAD_MANIFEST.json'),new_science_arrays_opened=0)
    dump(OUT/'ACQUISITION_RESULT.json',summary);print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
