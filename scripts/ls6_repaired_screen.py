#!/usr/bin/env python3
"""Checkpointed LS6 TRAPPIST-1 ABAB pilot through the unchanged LS4B SIGPROC/LS1 detector."""
import argparse,hashlib,json,shutil
from pathlib import Path
from ls1_fetch import fetch
from ls4b_filterbank_screen import screen_scan,verify_detector_inheritance,sha256_file,atomic_write
from seti_repeater.light_sail import apply_abacad_veto
from seti_repeater.search_v0p6 import canonical_json_bytes

def seal(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()

def validate_checkpoint(receipt,scan,config_hash):
    if receipt['config_sha256']!=config_hash:raise RuntimeError('checkpoint config mismatch')
    body={k:v for k,v in receipt.items() if k!='checkpoint_sha256'}
    if receipt['checkpoint_sha256']!=seal(body):raise RuntimeError('checkpoint digest mismatch')
    r=receipt['scan']
    if r['label']!=scan['label'] or r['role']!=scan['role'] or r['adjacent_off_labels']!=scan['adjacent_off_labels']:raise RuntimeError('checkpoint scan mismatch')
    if r['source_url']!=scan['medium_resolution']['url'] or r['source_size_bytes']!=scan['medium_resolution']['expected_size_bytes']:raise RuntimeError('checkpoint source mismatch')
    return r

def run(config_path,out,data_dir):
    raw=config_path.read_bytes();config=json.loads(raw);config_hash=hashlib.sha256(raw).hexdigest()
    if config['artifact_type']!='seti_repeater.ls6_preregistration':raise RuntimeError('invalid configuration')
    repair=config['technical_amendment']
    if repair['kind']!='duration-fit-repair' or repair['prior_exposed_scan_labels']!=['A1']:raise RuntimeError('unexpected amendment')
    if sha256_file(Path(repair['initial_config_path']))!=repair['initial_config_sha256']:raise RuntimeError('initial freeze changed')
    for path,digest in config['implementation_sha256'].items():
        if sha256_file(Path(path))!=digest:raise RuntimeError('frozen implementation changed: '+path)
    if config['medium_resolution_screen']['duration_s']!=[4.0,8.0,16.0,32.0]:raise RuntimeError('unexpected repaired durations')
    inheritance_config={**config,'medium_resolution_screen':{**config['medium_resolution_screen'],'duration_s':[4.0,8.0,16.0,32.0,64.0]}}
    verify_detector_inheritance(inheritance_config,Path('config/ls1_hd219134_light_sail.json'))
    source=config['archive_header_result']
    if sha256_file(Path(source['source_path']))!=source['source_sha256']:raise RuntimeError('preflight changed')
    preflight=json.loads(Path(source['source_path']).read_text())
    if preflight['spectral_values_read'] or [r['url'] for r in preflight['selected_products']]!=[s['medium_resolution']['url'] for s in config['selected_sequence']]:raise RuntimeError('preflight selection mismatch')
    out.mkdir(exist_ok=True);data_dir.mkdir(exist_ok=True);scans=[]
    for scan in config['selected_sequence']:
        checkpoint=out/(scan['label']+'.json')
        if checkpoint.exists():
            scans.append(validate_checkpoint(json.loads(checkpoint.read_text()),scan,config_hash));continue
        destination=data_dir/(scan['label']+'.0002.fil')
        if shutil.disk_usage(data_dir).free < scan['medium_resolution']['expected_size_bytes']+2_000_000_000:raise RuntimeError('insufficient disk space')
        try:
            digest=fetch(scan,destination)
            # SIGPROC source-name lengths can differ between ON and OFF.
            local_config={**config,'expected_filterbank_header':scan['expected_filterbank_header']}
            result=screen_scan(scan,local_config,destination,digest)
            receipt={'config_sha256':config_hash,'scan':result};receipt['checkpoint_sha256']=seal(receipt)
            atomic_write(checkpoint,canonical_json_bytes(receipt));scans.append(result)
            print('screened',scan['label'],'events',len(result['search']['events']),'truncated',result['search']['retention_truncated'],flush=True)
        finally:
            destination.unlink(missing_ok=True);destination.with_suffix('.fil.part').unlink(missing_ok=True)
    d=config['medium_resolution_screen']
    candidates=apply_abacad_veto(scans,on_threshold=d['on_score_threshold'],off_threshold=d['off_veto_score_threshold'],minimum_frequency_overlap=d['off_veto_frequency_overlap'])
    survivors=[c for c in candidates if c['survives_adjacent_off_veto']]
    truncated=any(s['search']['retention_truncated'] for s in scans)
    status='invalid-retention-truncated' if truncated else ('screen-complete-followup-preregistration-required' if survivors else 'screen-complete-no-surviving-events')
    result={'artifact_type':'seti_repeater.ls6_medium_resolution_screen','status':status,'config_sha256':config_hash,'target':config['target'],'selected_cadence_id':config['archive_inventory']['selected_cadence_id'],'science_band_mhz':d['science_band_mhz'],'geometry':config['geometry'],'technical_amendment':config['technical_amendment'],'scans':scans,'candidates':candidates,'on_threshold_event_count':len(candidates),'surviving_event_count':len(survivors),'retention_truncated':truncated,'high_time_resolution_followup_preregistration_required':bool(survivors) and not truncated,'high_time_resolution_values_read':False,'raw_spectral_payload_published':False,'spectral_values_read':True,'technosignature_claimed':False,'score_is_calibrated_significance':False}
    result['result_sha256']=seal(result);atomic_write(out/'screen.json',canonical_json_bytes(result))
    manifest=''.join(s['source_sha256']+'  '+s['source_url']+'\n' for s in scans)
    atomic_write(Path('DATA_MANIFEST_LS6.sha256'),manifest.encode())
    print(status,'ON',len(candidates),'survivors',len(survivors),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('config',type=Path);a=p.parse_args()
    run(a.config,Path('results_ls6_screen'),Path('data_ls6'))
