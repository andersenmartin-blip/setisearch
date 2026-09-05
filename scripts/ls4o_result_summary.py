#!/usr/bin/env python3
"""Verify and report scoped metadata feasibility without network access."""
import hashlib
import json
from urllib.parse import urlencode
from ls4o_control_feasibility import ROOT,OUT,load,encoded,verify_manifest,known_geometry,inventory,queries


def verified():
    verify_manifest(ROOT/'LS4O_FREEZE.sha256');c=load('config/ls4o_control_feasibility.json')
    r=load('results_ls4o_control_feasibility/feasibility.json');identity=r.pop('result_sha256')
    if hashlib.sha256(encoded(r)).hexdigest()!=identity:raise ValueError('result identity differs')
    if r['freeze_sha256']!=hashlib.sha256((ROOT/'LS4O_FREEZE.sha256').read_bytes()).hexdigest():raise ValueError('freeze differs')
    paths=sorted(OUT.glob('query_*.json'))
    if len(paths)!=11:raise ValueError('incomplete query receipts')
    receipts=[]
    for path,expected in zip(paths,queries(c)):
        receipt=json.loads(path.read_text())
        if any(receipt[k]!=v for k,v in expected.items()):raise ValueError('query identity differs')
        if receipt['requested_url']!=c['network']['endpoint']+'?'+urlencode(expected['params']):raise ValueError('query URL differs')
        if 'response_text' in receipt:
            data=receipt['response_text'].encode()
            if hashlib.sha256(data).hexdigest()!=receipt['payload_sha256'] or len(data)!=receipt['response_bytes']:raise ValueError('metadata payload differs')
        if receipt['successful']:
            if json.loads(receipt['response_text'])!=receipt['response'] or receipt['http_status']!=200:raise ValueError('response differs')
            if receipt['record_limit_reached']!=(len(receipt['response']['data'])>=c['network']['record_limit']):raise ValueError('limit annotation differs')
        receipts.append(receipt)
    inv=inventory(receipts,c)
    if any(r[k]!=v for k,v in inv.items()):raise ValueError('inventory differs')
    geometry=known_geometry(c)
    if geometry!=r['known_geometry'] or geometry!=load('results_ls4o_control_feasibility/known_geometry.json'):raise ValueError('geometry differs')
    complete=inv['successful_queries']==11 and not inv['record_limit_reached_queries'] and not inv['metadata_conflicts'] and not inv['restricted_products_missing_from_target_queries']
    expected_status='scoped-metadata-feasibility-complete' if complete else 'incomplete-metadata-feasibility'
    if r['status']!=expected_status or any(r[k] for k in ('new_spectral_bytes_read','reserved_htr_opened','sky_candidates_promoted','independent_confirmation_obtained')):raise ValueError('status or boundary differs')
    checkpoint=load('results_ls4o_control_feasibility/checkpoint.json')
    if checkpoint!={'completed_queries':11,'successful_queries':r['successful_queries']}:raise ValueError('checkpoint differs')
    r['result_sha256']=identity
    return r,receipts


def main():
    r,_=verified()
    print(json.dumps({k:v for k,v in r.items() if k not in ('known_geometry','scan_groups')},indent=2))


if __name__=='__main__':main()
