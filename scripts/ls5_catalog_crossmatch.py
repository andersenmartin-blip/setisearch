#!/usr/bin/env python3
"""Expanded, metadata-only NASA/BL cross-match after empty five-host shortlist."""
import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlencode
from ls5_target_inventory import fetch,OUT,FIELDS
from seti_repeater.light_sail_catalog import resolve_archive_aliases,geometry_planet_inventory,summarize_cadence_records

def main():
    query=f'select {FIELDS},hd_name,hip_name,tic_id from ps where default_flag=1 and tran_flag=1 and sy_pnum>1 order by hostname,pl_name'
    rows=fetch('https://exoplanetarchive.ipac.caltech.edu/TAP/sync?'+urlencode({'query':query,'format':'json'}),'expanded_planets')
    catalog=json.loads((OUT/'archive_targets.json').read_text())['payload']
    groups=defaultdict(list)
    for row in rows:groups[row['hostname']].append(row)
    excluded=['HD 219134','HD 260655','HD 63433','LHS 1140']
    hosts=[]
    for name,planets in groups.items():
        if len(planets)<2 or name in excluded:continue
        aliases=sorted({v for r in planets for k in ['hostname','hd_name','hip_name','tic_id'] if (v:=r.get(k))})
        matches=resolve_archive_aliases(aliases,catalog)
        if matches:hosts.append({'hostname':name,'aliases':aliases,'resolved_archive_aliases':matches,'planets':planets,'geometry':geometry_planet_inventory(planets)})
    hosts.sort(key=lambda h:(min((float(p['sy_dist']) for p in h['planets'] if p.get('sy_dist') is not None),default=float('inf')),h['hostname']))
    (OUT/'expanded_matches.json').write_text(json.dumps({'queried_planet_count':len(rows),'multi_transit_host_count':sum(len(p)>=2 for p in groups.values()),'excluded_searched_hosts':excluded,'targets':hosts},indent=2)+'\n')
    print('Matched hosts:',[(h['hostname'],h['resolved_archive_aliases'],h['geometry']['eligible_planet_count']) for h in hosts],flush=True)
    # Bounded scope: nearest 10 matched new hosts, retain each outcome.
    for host in hosts[:10]:
        host['cadences']=[]
        for alias in host['resolved_archive_aliases']:
            listing=fetch('http://seti.berkeley.edu/opendata/api/query-files?'+urlencode({'target':alias,'telescope':'GBT','cadence':'True','primaryTarget':'True','limit':'3000'}),alias+'_listing')
            data=listing if isinstance(listing,list) else listing['data']
            if len(data)>=3000:raise RuntimeError('possible truncation')
            for url in sorted({r['cadence_url'] for r in data if r.get('cadence_url')}):
                payload=fetch(url,alias+'_'+url.rsplit('/',1)[1]);records=payload if isinstance(payload,list) else payload['data']
                host['cadences'].append({'cadence_url':url,'archive_target':alias,'records':records,'summary':summarize_cadence_records(records)})
        print(host['hostname'],host['geometry']['eligible_planet_count'],[(c['cadence_url'],c['summary']['product_counts']) for c in host['cadences']],flush=True)
        (OUT/'expanded_inventory.json').write_text(json.dumps({'spectral_values_read':False,'targets':hosts[:10]},indent=2)+'\n')
if __name__=='__main__':main()
