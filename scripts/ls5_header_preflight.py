#!/usr/bin/env python3
"""Kepler-160 header-only filterbank feasibility and b/c geometry ranking."""
import json,hashlib,re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from ls4a_lhs1140_fil_header_preflight import remote_filterbank_header,qualify_cadence,atomic_write
from seti_repeater.search_v0p6 import canonical_json_bytes

OUT=Path('results_ls5_header')
def main():
    OUT.mkdir(exist_ok=True)
    host=next(h for h in json.loads(Path('results_ls5_inventory/expanded_inventory.json').read_text())['targets'] if h['hostname']=='Kepler-160')
    config=json.loads(Path('config/ls4a_lhs1140_fil_header_preflight.json').read_text())
    config['target']={'hostname':'Kepler-160','archive_source_name':'KEPLER-160','stellar_radius_solar':1.118}
    config['ephemeris']={'planets':host['planets'],'reference':'Heller et al. (2020), NASA PS default rows retrieved 2026-09-05'}
    config['network']={'user_agent':'setisearch-LS5-header/1.0','timeout_s':60}
    inputs=[]
    for cadence in host['cadences']:
        groups={}
        for r in cadence['records']:
            url=r['url']
            if not url.endswith(('.rawspec.0002.fil','.rawspec.8.0001.fil')):continue
            key=re.search(r'_(\d{4})\.rawspec',url).group(1)
            scan=groups.setdefault(key,{'scan_key':key,'listing_mjd':r['mjd'],'medium':None,'htr':None})
            kind='medium' if url.endswith('.rawspec.0002.fil') else 'htr'
            if scan[kind] is not None:raise RuntimeError('duplicate product')
            scan[kind]={'url':url,'expected_size_bytes':r['size']}
        inputs.append({'band':{'--813610':'L','--813641':'S','--813675':'C'}[cadence['cadence_url'].rsplit('/',1)[1]],'cadence_url':cadence['cadence_url'],'scans':sorted(groups.values(),key=lambda s:s['listing_mjd'])})
    def read(product):
        key=hashlib.sha256(product['url'].encode()).hexdigest()
        p=OUT/(key+'.json')
        if p.exists():return json.loads(p.read_text())
        r=remote_filterbank_header(product['url'],product['expected_size_bytes'],config)
        atomic_write(p,canonical_json_bytes(r));return r
    results=[]
    for cadence in inputs:
        products=[s[k] for s in cadence['scans'] for k in ['medium','htr'] if s[k]]
        with ThreadPoolExecutor(max_workers=3) as pool:headers={r['url']:r for r in pool.map(read,products)}
        result=qualify_cadence(cadence,headers,config)
        compatible=all(h.get('nbits')==32 and h.get('nifs')==1 for h in headers.values() if h['url'].endswith('.0002.fil'))
        result['medium_qualified'] &= compatible
        result['fully_followup_capable'] &= compatible
        result['inputs']=cadence
        results.append(result)
        print(cadence['band'],result['medium_qualified'],result['fully_followup_capable'],result['conjunction'],flush=True)
    eligible=[r for r in results if r['medium_qualified'] and r['resource_gate_passes']]
    eligible.sort(key=lambda r:(not r['fully_followup_capable'],r['conjunction']['nominal_projected_separation_stellar_radii'],r['conjunction']['reference_bjd_utc_approximation'],r['cadence_url']))
    selected={k:eligible[0][k] for k in ['band','cadence_url','conjunction','medium_download_bytes','fully_followup_capable']} if eligible else None
    result={'artifact_type':'seti_repeater.ls5_header_preflight','target':config['target'],'ephemeris':config['ephemeris'],'cadences':results,'selected_for_preregistration':selected,'spectral_values_read':False}
    result['result_sha256']=hashlib.sha256(canonical_json_bytes(result)).hexdigest()
    atomic_write(OUT/'preflight.json',canonical_json_bytes(result))
    print('SELECTED',selected,flush=True)
if __name__=='__main__':main()
