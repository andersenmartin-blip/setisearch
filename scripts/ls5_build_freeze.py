#!/usr/bin/env python3
"""Build exact LS5 S-band six-scan preregistration from qualified headers."""
import copy,hashlib,json
from pathlib import Path
from datetime import datetime,timezone

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    p=Path('results_ls5_header/qualified.json');pre=json.loads(p.read_text());selection=pre['selected_for_preregistration']
    c=next(c for c in pre['cadences'] if c['cadence_url']==selection['cadence_url'])
    base=json.loads(Path('config/ls1_hd219134_light_sail.json').read_text())
    detector=copy.deepcopy(base['medium_resolution_screen']);detector.update(implementation='Unchanged LS1 detector via LS4B SIGPROC adapter',product_suffix='rawspec.0002.fil',science_band_mhz=[1800.0,2800.0])
    sequence=[]
    for i,(label,s) in enumerate(zip(['A1','B1','A2','C1','A3','D1'],c['inputs']['scans'])):
        h=c['headers'][s['medium']['url']]
        expected={k:h[k] for k in ['nchans','nifs','nbits','ntime','fch1_mhz','foff_mhz','tsamp_s']};expected['header_bytes']=h['header_bytes_read']
        sequence.append({'label':label,'role':'ON' if i%2==0 else 'OFF','adjacent_off_labels':{'A1':['B1'],'A2':['B1','C1'],'A3':['C1','D1']}.get(label,[]),'expected_source_name':h['source_name'],'expected_tstart_mjd':h['tstart_mjd'],'expected_filterbank_header':expected,'medium_resolution':s['medium'],'high_time_resolution':s['htr'],'header_pointing_offset_deg':c['pointing_offsets_deg'][i]['separation_deg']})
    config={'artifact_type':'seti_repeater.ls5_preregistration','frozen_utc':datetime.now(timezone.utc).isoformat(),'project':{'id':'LS5','branch':'ls5-new-target-selection','detector_inherited_unchanged_from_ls1':True},'target':{'hostname':'Kepler-160','archive_target':'KEPLER-160','distance_pc':937.013,'scope':'published archival ON/OFF sequence; target centering unresolved for final ON'},'freeze_boundary':{'medium_resolution_values_read_before_freeze':False,'high_time_resolution_values_read_before_freeze':False,'header_only_metadata_read_before_freeze':True},'archive_header_result':{'source_path':str(p),'source_sha256':sha(p),'source_result_identity':pre['result_sha256']},'archive_inventory':{'selected_cadence_url':selection['cadence_url'],'selected_cadence_id':'--813641','selected_band':'S'},'geometry':{**selection['conjunction'],'caveat':'linear ephemerides omit known Kepler-160 c TTVs; not a close conjunction or calibrated interval'},'medium_resolution_screen':detector,'selected_sequence':sequence,'resource_policy':{'maximum_science_window_bytes_per_scan':600000000,'minimum_free_headroom_bytes_after_download':2000000000,'download_one_scan_at_a_time':True,'delete_raw_after_checkpoint':True},'followup':{'requires_surviving_event_and_no_retention_truncation':True,'requires_separate_preregistration':True,'pointing_verification_required_before_stellar_attribution':True},'claim_boundary':{'technosignature_claimed':False,'calibrated_sensitivity_claimed':False,'first_SETI_search_of_system_claimed':False,'raw_spectral_payload_may_be_published':False},'implementation_sha256':{p:sha(p) for p in ['scripts/ls5_screen.py','scripts/ls4b_filterbank_screen.py','scripts/ls1_fetch.py','src/seti_repeater/light_sail.py','src/seti_repeater/sigproc.py','config/ls1_hd219134_light_sail.json']}}
    Path('config/ls5_kepler160_s_light_sail.json').write_text(json.dumps(config,indent=2)+'\n')
if __name__=='__main__':main()
