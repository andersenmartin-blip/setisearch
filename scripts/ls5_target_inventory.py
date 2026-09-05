#!/usr/bin/env python3
"""Bounded metadata-only selection of a fifth LS stellar target."""
import json, hashlib, re
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor
from seti_repeater.light_sail_catalog import resolve_archive_aliases, geometry_planet_inventory, summarize_cadence_records

OUT=Path('results_ls5_inventory')
TARGETS=['HD 3167','HD 191939','HD 106315','HD 108236','HD 110067']
FIELDS='pl_name,hostname,pl_orbper,pl_orbpererr1,pl_orbpererr2,pl_tranmid,pl_tranmiderr1,pl_tranmiderr2,pl_orbsmax,pl_orbsmaxerr1,pl_orbsmaxerr2,pl_orbeccen,pl_orbincl,tran_flag,sy_dist,st_rad,st_raderr1,st_raderr2,rowupdate,pl_refname'
def fetch(url, name):
    path=OUT/(name+'.json')
    if path.exists(): return json.loads(path.read_text())['payload']
    with urlopen(Request(url,headers={'User-Agent':'setisearch-LS5-public-metadata/1.0'}),timeout=90) as r:
        raw=r.read(50_000_001)
        if len(raw)>50_000_000: raise RuntimeError('response limit exceeded')
        payload=json.loads(raw)
        receipt={'url':url,'retrieved_utc':datetime.now(timezone.utc).isoformat(),'status':r.status,'response_sha256':hashlib.sha256(raw).hexdigest(),'payload':payload}
    if isinstance(payload,dict) and payload.get('result') not in (None,'success'): raise RuntimeError(str(payload))
    path.write_text(json.dumps(receipt,indent=2)+'\n')
    return payload

def host_metadata(host):
    key=host.replace(' ','').lower()
    aliases=fetch('https://exoplanetarchive.ipac.caltech.edu/cgi-bin/Lookup/nph-aliaslookup.py?'+urlencode({'objname':host}),key+'_aliases')
    if aliases['manifest']['lookup_status']!='OK': raise RuntimeError('alias lookup failed')
    stars=aliases['system']['objects']['stellar_set']['stars']
    # Use only the requested host's aliases, never companions or planetary aliases.
    star=stars[host]
    names=star['alias_set']['aliases']
    rows=fetch('https://exoplanetarchive.ipac.caltech.edu/TAP/sync?'+urlencode({'query':f"select {FIELDS} from ps where hostname='{host}' and default_flag=1 order by pl_name",'format':'json'}),key+'_planets')
    return {'hostname':host,'aliases':names,'planets':rows,'geometry':geometry_planet_inventory(rows)}

def main():
    OUT.mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        future=pool.submit(fetch,'http://seti.berkeley.edu/opendata/api/list-targets','archive_targets')
        hosts=list(pool.map(host_metadata,TARGETS))
        catalog_response=future.result()
        catalog=catalog_response if isinstance(catalog_response,list) else catalog_response['data']
    for host in hosts:
        host['resolved_archive_aliases']=resolve_archive_aliases(host['aliases'],catalog)
        host['cadences']=[]
        for alias in host['resolved_archive_aliases']:
            query=fetch('http://seti.berkeley.edu/opendata/api/query-files?'+urlencode({'target':alias,'telescope':'GBT','cadence':'True','primaryTarget':'True','limit':'3000'}),alias+'_listing')
            if len(query['data'])>=3000: raise RuntimeError('possible pagination truncation')
            for url in sorted({r['cadence_url'] for r in query['data'] if r.get('cadence_url')}):
                records=fetch(url,alias+'_'+url.rsplit('/',1)[1])['data']
                host['cadences'].append({'cadence_url':url,'archive_target':alias,'summary':summarize_cadence_records(records),'records':records})
        print(host['hostname'],host['resolved_archive_aliases'],'geometry',host['geometry']['eligible_planet_count'],'cadences',[(c['cadence_url'],c['summary']['product_counts']) for c in host['cadences']],flush=True)
    result={'artifact_type':'seti_repeater.ls5_metadata_inventory','target_order':TARGETS,'spectral_values_read':False,'targets':hosts}
    (OUT/'inventory.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
