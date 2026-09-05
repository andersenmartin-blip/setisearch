#!/usr/bin/env python3
"""Public metadata qualification of planet-labelled archive targets."""
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode
import ls5_target_inventory as inherited
from seti_repeater.light_sail_catalog import geometry_planet_inventory,summarize_cadence_records
OUT=Path('results_ls6_inventory')
inherited.OUT=OUT
fetch=inherited.fetch
TARGETS=[('Kepler-446','KEPLER446B'),('Kepler-732','KEPLER732C')]
def host(item):
    name,alias=item;key=name.replace('-','').lower()
    aliases=fetch('https://exoplanetarchive.ipac.caltech.edu/cgi-bin/Lookup/nph-aliaslookup.py?'+urlencode({'objname':name}),key+'_aliases')
    query=f"select {inherited.FIELDS},ra,dec from ps where hostname='{name}' and default_flag=1 order by pl_name"
    planets=fetch('https://exoplanetarchive.ipac.caltech.edu/TAP/sync?'+urlencode({'query':query,'format':'json'}),key+'_planets')
    result={'hostname':name,'archive_target':alias,'planets':planets,'geometry':geometry_planet_inventory(planets),'cadences':[]}
    for mode,params in [('cadence',{'target':alias,'telescope':'GBT','cadence':'True','primaryTarget':'True','limit':3000}),('target_only',{'target':alias,'limit':3000})]:
        d=fetch('http://seti.berkeley.edu/opendata/api/query-files?'+urlencode(params),key+'_'+mode)
        rows=d if isinstance(d,list) else d['data']
        if len(rows)>=3000:raise RuntimeError('possible truncation')
        result[mode]={'records':rows,'summary':summarize_cadence_records(rows)}
        if mode=='cadence':
            for url in sorted({r['cadence_url'] for r in rows if r.get('cadence_url')}):
                d=fetch(url,key+'_'+url.rsplit('/',1)[1]);records=d if isinstance(d,list) else d['data']
                result['cadences'].append({'cadence_url':url,'records':records,'summary':summarize_cadence_records(records)})
    print(name,'geometry',result['geometry']['eligible_planet_count'],'cadences',len(result['cadences']),'products',result['target_only']['summary'],flush=True)
    return result

def main():
    OUT.mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(host,TARGETS))
    (OUT/'inventory.json').write_text(json.dumps({'spectral_values_read':False,'targets':results},indent=2)+'\n')
if __name__=='__main__':main()
