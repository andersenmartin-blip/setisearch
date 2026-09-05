#!/usr/bin/env python3
"""Freeze exact TRAPPIST-1 four-scan subband pilot inputs."""
import json,hashlib
from pathlib import Path
from datetime import datetime,timezone

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    source=Path('results_ls6_trappist/preflight.json');pre=json.loads(source.read_text())
    detector=json.loads(Path('config/ls1_hd219134_light_sail.json').read_text())['medium_resolution_screen']
    hs=pre['selected_headers'];h=hs[0]
    if any('error' in h for h in hs):raise RuntimeError('incomplete headers')
    detector.update(implementation='Unchanged LS1 core through LS4B SIGPROC adapter; explicit four-scan pilot',product_suffix='gpuspec.0002.fil',science_band_mhz=[h['frequency_low_mhz'],h['frequency_high_mhz']])
    scans=[]
    for i,(r,h,label) in enumerate(zip(pre['selected_products'],hs,['A1','B1','A2','B2'])):
        if r['target']!=h['source_name'] or r['size']!=h['remote_size_bytes']:raise RuntimeError('identity mismatch')
        expected={k:h[k] for k in ['nchans','nifs','nbits','ntime','fch1_mhz','foff_mhz','tsamp_s']};expected['header_bytes']=h['header_bytes_read']
        scans.append({'label':label,'role':'ON' if i%2==0 else 'OFF','adjacent_off_labels':{'A1':['B1'],'A2':['B1','B2']}.get(label,[]),'expected_source_name':h['source_name'],'expected_tstart_mjd':h['tstart_mjd'],'expected_filterbank_header':expected,'medium_resolution':{'url':r['url'],'expected_size_bytes':r['size']}})
    config={'artifact_type':'seti_repeater.ls6_preregistration','frozen_utc':datetime.now(timezone.utc).isoformat(),'target':{'hostname':'TRAPPIST-1','archive_target':'DIAG_TRAPPIST1','scope':'four-scan 187.5 MHz subband pilot; pointing and geometric qualification limited'},'freeze_boundary':{'medium_resolution_values_read_before_freeze':False,'high_time_resolution_values_read_before_freeze':False},'archive_header_result':{'source_path':str(source),'source_sha256':sha(source),'source_result_identity':pre['result_sha256']},'archive_inventory':{'selected_cadence_id':'20170223-X-9920MHz-ABAB','selected_cadence_url':'http://seti.berkeley.edu/opendata/api/query-files?target=DIAG_TRAPPIST1&limit=3000'},'geometry':{'conjunction_ranked':False,'reason':'NASA default transit epochs missing; orbital ranking deferred'},'medium_resolution_screen':detector,'selected_sequence':scans,'resource_policy':{'maximum_science_window_bytes_per_scan':20000000},'implementation_sha256':{p:sha(p) for p in ['scripts/ls6_screen.py','scripts/ls4b_filterbank_screen.py','scripts/ls1_fetch.py','src/seti_repeater/light_sail.py','src/seti_repeater/sigproc.py','config/ls1_hd219134_light_sail.json']},'claim_boundary':{'technosignature_claimed':False,'calibrated_sensitivity_claimed':False,'new_target_six_scan_analysis_completed':False}}
    Path('config/ls6_trappist1_x_subband.json').write_text(json.dumps(config,indent=2)+'\n')
if __name__=='__main__':main()
