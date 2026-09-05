#!/usr/bin/env python3
"""TRAPPIST-1 next-target header-only subband feasibility."""
import json,hashlib
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode
import ls5_target_inventory as inherited
from ls4a_lhs1140_fil_header_preflight import remote_filterbank_header,atomic_write
from seti_repeater.search_v0p6 import canonical_json_bytes
OUT=Path('results_ls6_trappist')
def main():
    OUT.mkdir(exist_ok=True);inherited.OUT=Path('results_ls6_inventory')
    nasa=inherited.fetch('https://exoplanetarchive.ipac.caltech.edu/TAP/sync?'+urlencode({'query':f"select {inherited.FIELDS},ra,dec from ps where hostname='TRAPPIST-1' and default_flag=1 order by pl_name",'format':'json'}),'trappist1_planets')
    raw=json.loads(Path('results_ls6_inventory/DIAG_TRAPPIST1_target_only.json').read_text())['payload']['data']
    medium={r['url']:r for r in raw if r['target'] in ['DIAG_TRAPPIST1','DIAG_TRAPPIST1_OFF'] and r['url'].endswith('.gpuspec.0002.fil')}
    scans=defaultdict(list)
    for r in medium.values():scans[r['mjd']].append(r)
    summaries=[{'mjd':mjd,'target':rows[0]['target'],'medium_subband_count':len(rows),'centers_mhz':sorted(r['center_freq'] for r in rows)} for mjd,rows in sorted(scans.items())]
    x=[r for r in medium.values() if r['center_freq']>8000]
    center=min({r['center_freq'] for r in x},key=lambda f:(abs(f-10000),f))
    selected=sorted([r for r in x if r['center_freq']==center],key=lambda r:(r['mjd'],r['url']))
    if len(selected)!=4 or [r['target'] for r in selected]!=['DIAG_TRAPPIST1','DIAG_TRAPPIST1_OFF']*2:raise RuntimeError('not an exact four-scan ABAB subband')
    config={'network':{'user_agent':'setisearch-LS6-TRAPPIST-header/1.0','timeout_s':60},'header_criteria':{'maximum_header_bytes':65536}}
    def read(r):
        p=OUT/(str(r['id'])+'.json')
        if p.exists():return json.loads(p.read_text())
        h=remote_filterbank_header(r['url'],r['size'],config);atomic_write(p,canonical_json_bytes(h));return h
    with ThreadPoolExecutor(max_workers=2) as pool:headers=list(pool.map(read,selected))
    result={'artifact_type':'seti_repeater.ls6_trappist_next_target_preflight','spectral_values_read':False,'target':'TRAPPIST-1','medium_product_count':len(medium),'medium_total_bytes':sum(r['size'] for r in medium.values()),'scan_count':len(scans),'scan_summaries':summaries,'selected_center_mhz':center,'selected_products':selected,'selected_headers':headers,'six_scan_protocol_applicable':False,'ephemeris_default_missing_transit_epochs':sum(p['pl_tranmid'] is None for p in nasa),'next_required_work':'Define an explicit four-scan ABAB subband pilot, verify pointing/epoch identity and adopt published dynamical ephemerides before a geometric claim.'}
    result['result_sha256']=hashlib.sha256(canonical_json_bytes(result)).hexdigest();atomic_write(OUT/'preflight.json',canonical_json_bytes(result))
    print(json.dumps({'center':center,'bytes':sum(r['size'] for r in selected),'headers':[{k:h.get(k) for k in ['source_name','ntime','tsamp_s','frequency_low_mhz','frequency_high_mhz','error']} for h in headers],'missing_epochs':result['ephemeris_default_missing_transit_epochs']},indent=2))
if __name__=='__main__':main()
