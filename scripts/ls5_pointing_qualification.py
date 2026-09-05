#!/usr/bin/env python3
"""Qualify published Kepler-160 roles while retaining ambiguous header labels."""
import json,math,hashlib
from pathlib import Path
from ls4a_lhs1140_fil_header_preflight import geometry_metrics,atomic_write
from seti_repeater.search_v0p6 import canonical_json_bytes

def angle(v,ra=False):
    sign=1 if v>=0 else -1;v=abs(v)
    return sign*(int(v/10000)+(int(v/100)%100)/60+(v%100)/3600)*(15 if ra else 1)
def separation(header):
    ra,dec=map(math.radians,(angle(header['src_raj'],True),angle(header['src_dej'])))
    r0,d0=map(math.radians,(angle(191105.52,True),angle(425219.12)))
    return math.degrees(math.acos(max(-1,min(1,math.sin(dec)*math.sin(d0)+math.cos(dec)*math.cos(d0)*math.cos(ra-r0)))))
def main():
    original=Path('results_ls5_header/preflight.json')
    result=json.loads(original.read_text());result['artifact_type']='seti_repeater.ls5_pointing_qualified_preflight';result['supersedes_sha256']=hashlib.sha256(original.read_bytes()).hexdigest()
    inventory=next(h for h in json.loads(Path('results_ls5_inventory/expanded_inventory.json').read_text())['targets'] if h['hostname']=='Kepler-160')
    byurl={r['url']:r for c in inventory['cadences'] for r in c['records']}
    for c in result['cadences']:
        scans=c['inputs']['scans'];start={'L':10,'S':25}.get(c['band'])
        roles=bool(start is not None and len(scans)==6 and [int(s['scan_key']) for s in scans]==list(range(start,start+6)) and all(byurl[s['medium']['url']]['target']==('KEPLER-160' if i%2==0 else 'KEPLER-160_OFF') for i,s in enumerate(scans)))
        c['original_header_name_gate_passed']=c['sequence_matches_abacad']
        c['published_sequence_and_catalog_roles_agree']=roles
        c['pointing_verified_on_star']=False
        c['pointing_offsets_deg']=[{'scan_key':s['scan_key'],'catalog_role':'ON' if i%2==0 else 'OFF','separation_deg':separation(c['headers'][s['medium']['url']]['header'])} for i,s in enumerate(scans)]
        c['medium_qualified']=bool(roles and c['medium_complete'] and c['medium_geometry_matches'] and all(c['headers'][s['medium']['url']]['nbits']==32 and c['headers'][s['medium']['url']]['nifs']==1 for s in scans))
        c['fully_followup_capable']=c['medium_qualified'] and c['htr_geometry_matches']
        if c['medium_qualified']:
            f=c['headers'][scans[0]['medium']['url']]
            c['conjunction']=geometry_metrics(f['tstart_mjd']+2400000.5+f['ntime']*f['tsamp_s']/172800,result['ephemeris']['planets'],1.118)
    eligible=[c for c in result['cadences'] if c['medium_qualified'] and c['resource_gate_passes']]
    eligible.sort(key=lambda c:(not c['fully_followup_capable'],c['conjunction']['nominal_projected_separation_stellar_radii'],c['conjunction']['reference_bjd_utc_approximation'],c['cadence_url']))
    result['selected_for_preregistration']={k:eligible[0][k] for k in ['band','cadence_url','conjunction','medium_download_bytes','fully_followup_capable']}
    result['pointing_qualification']='archival sequence only; stellar attribution unresolved'
    result.pop('result_sha256');result['result_sha256']=hashlib.sha256(canonical_json_bytes(result)).hexdigest()
    atomic_write(Path('results_ls5_header/qualified.json'),canonical_json_bytes(result))
    print(json.dumps(result['selected_for_preregistration'],indent=2))
if __name__=='__main__':main()
