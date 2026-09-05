#!/usr/bin/env python3
"""Audit target-only public records where dedicated cadence lookups were empty."""
import json
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode
from ls5_target_inventory import fetch,OUT
from seti_repeater.light_sail_catalog import summarize_cadence_records

def one(host):
    records=[]
    for alias in host['resolved_archive_aliases']:
        d=fetch('http://seti.berkeley.edu/opendata/api/query-files?'+urlencode({'target':alias,'limit':3000}),alias+'_target_only')
        rows=d if isinstance(d,list) else d['data']
        if len(rows)>=3000:raise RuntimeError('possible truncation')
        records.extend(rows)
    result={'hostname':host['hostname'],'records':records,'summary':summarize_cadence_records(records)}
    print(host['hostname'],result['summary'],flush=True)
    return result

def main():
    hosts=json.loads((OUT/'expanded_matches.json').read_text())['targets'][:10]
    with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(one,hosts))
    (OUT/'target_only_audit.json').write_text(json.dumps({'spectral_values_read':False,'targets':results},indent=2)+'\n')
if __name__=='__main__':main()
