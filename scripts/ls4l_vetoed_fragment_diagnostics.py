#!/usr/bin/env python3
"""Separately authorized review of LS4J-vetoed injections; preserve every veto."""
import gzip
import hashlib
import json
from pathlib import Path
import platform
import shutil
import tempfile
import numpy as np
from ls4i_measured_digital_injections import encoded,write_json,collect_bands,event_band,read_htr,evaluate_htr
from ls4f_v2_native_reanalysis import download_exact,numeric_agreement
from ls4g_synthetic_recovery import verify_manifest

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_ls4l_vetoed_fragment_diagnostics'
KEYS=('frequency_index','window_index','pulse_width_s','medium_amplitude')


def load(name):
    p=ROOT/name;raw=p.read_bytes()
    if p.suffix=='.gz':raw=gzip.decompress(raw)
    return json.loads(raw)


def stage_input(config):
    stage=load('results_ls4j_fragment_association/stage1.json.gz')
    identity=stage.pop('result_sha256')
    if hashlib.sha256(encoded(stage)).hexdigest()!=identity or identity!=config['stage1_result_sha256']:
        raise ValueError('selected stage identity differs')
    matches=[m for t in stage['trials'] for m in t['matched_events']]
    if len(stage['trials'])!=36 or len(stage['baselines'])!=12 or len(matches)!=64:
        raise ValueError('selected inventory differs')
    if any(m['survives_adjacent_off_veto'] or not m['adjacent_off_vetoes'] for m in matches):
        raise ValueError('original veto lost')
    return stage


def review_annotations(result,stage,config,header):
    rows=result['paired_configurations'];lookup={tuple(r[k] for k in KEYS)+(r['htr_amplitude'],):r for r in rows}
    expected={tuple(t[k] for k in KEYS)+(a,) for t in stage['trials'] for a in config['htr_amplitudes']}
    if set(lookup)!=expected or len(rows)!=144:raise ValueError('incomplete or duplicated review grid')
    if len(result['fixed_window_diagnostics'])!=48 or len(result['uninjected_baselines'])!=12:
        raise ValueError('incomplete control grid')
    reviews=[]
    for ti,trial in enumerate(stage['trials']):
        zero=lookup[tuple(trial[k] for k in KEYS)+(0.,)]
        for amplitude in config['htr_amplitudes']:
            row=lookup[tuple(trial[k] for k in KEYS)+(amplitude,)]
            if len(row['events'])!=len(trial['matched_events']) or row['stage1_matched_count']!=len(row['events']):
                raise ValueError('event handoff count differs')
            if len(zero['events'])!=len(row['events']):raise ValueError('zero-level event inventory differs')
            events=[]
            for mi,(event,match,baseline) in enumerate(zip(row['events'],trial['matched_events'],zero['events'])):
                original=match['event']
                if event['event_window_s']!=[original['time_start_s'],original['time_stop_s']] or tuple(event['band_indices'])!=event_band(original,header,config):
                    raise ValueError('detected event window or frequency band changed')
                if event['stage1_off_survives']!=match['survives_adjacent_off_veto'] or event['stage1_off_survives']:
                    raise ValueError('Stage-1 veto changed')
                if event['passed']!=(event['cross_scale_supported'] and not event['off_veto'] and not event['reference_veto']):
                    raise ValueError('residual decision differs')
                if event['truth_associated_pass']!=(event['passed'] and event['matched_truth_pulses']>=3):
                    raise ValueError('truth decision differs')
                events.append({'selected_fragment_index':mi,'review_truth_pass':event['truth_associated_pass'],
                               'same_window_zero_truth_pass':baseline['truth_associated_pass'],
                               'review_pass_absent_at_zero':event['truth_associated_pass'] and not baseline['truth_associated_pass'],
                               'original_stage1_off_vetoes':match['adjacent_off_vetoes'],'sky_candidate_promoted':False})
            if row['joint_digital_pass'] or row['stage1_survivor_count']:
                raise ValueError('original gate was bypassed in scientific endpoint')
            reviews.append({'trial_index':ti,**{k:row[k] for k in KEYS},'htr_amplitude':amplitude,'events':events,
                            'review_truth_pass_any':any(e['review_truth_pass'] for e in events),
                            'review_pass_absent_at_zero_any':any(e['review_pass_absent_at_zero'] for e in events),
                            'original_joint_pass':False,'sky_candidate_promoted':False})
    if sum(len(r['events']) for r in reviews)!=256:raise ValueError('fragment evaluation count differs')
    return reviews


def main():
    verify_manifest(ROOT/'LS4L_FREEZE.sha256')
    config=load('config/ls4l_vetoed_fragment_diagnostics.json')
    for name,expected in config['input_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:raise ValueError('input differs: '+name)
    stage=stage_input(config)
    oldh=load('config/ls4c_lhs1140_x_htr_followup.json');header=oldh['expected_filterbank_header']
    settings=load('config/ls4e_residual_qualification.json')['settings']
    bands=collect_bands(stage['trials'],stage['baselines'],config,header)
    if [list(b) for b in bands]!=stage['htr_band_indices'] or len(bands)!=10:raise ValueError('selected band inventory differs')
    OUT.mkdir(exist_ok=False)
    write_json(OUT/'selection.json',{'stage1_result_sha256':config['stage1_result_sha256'],'matched_fragments':64,
               'paired_configurations':144,'selected_fragment_evaluations':256,'unique_extraction_bands':bands,
               'policy':'review-only-original-stage1-veto-retained'})
    rawdir=Path(tempfile.mkdtemp(prefix='setisearch-ls4l-',dir='/tmp'))
    receipts=[];series={};charged=0
    try:
        for source in config['sources']:
            path=rawdir/'source.fil';errors=[]
            for attempt in range(config['resource']['attempts_per_source']):
                charged+=source['source_size_bytes']
                if charged>config['resource']['max_total_download_bytes']:raise ValueError('download budget exceeded')
                try:
                    receipt=download_exact(source,path,config);break
                except Exception as exc:
                    errors.append(str(exc))
                    if attempt+1==config['resource']['attempts_per_source']:raise
            try:
                series[source['label']]=read_htr(path,source,oldh,bands,config)
            finally:
                path.unlink(missing_ok=True)
            receipts.append({**receipt,'label':source['label'],'product':source['product'],
                             'prior_attempt_errors':errors,'raw_file_deleted':True})
            write_json(OUT/'source_receipts.json',{'sources':receipts,'charged_download_bytes':charged})
            print('Verified, extracted and deleted '+source['label'],flush=True)
        result=evaluate_htr(series['A1'],series['B1'],stage['trials'],stage['baselines'],config,header,settings)
        previous=load('results_ls4i_measured_digital_injections/injections.json.gz')
        if not numeric_agreement(result['fixed_window_diagnostics'],previous['fixed_window_diagnostics'],**config['replay_tolerance']):
            raise ValueError('LS4I fixed-window diagnostic replay differs')
        result['review_configurations']=review_annotations(result,stage,config,header)
        result.update({'status':'veto-preserving-measured-diagnostic-complete','fixed_window_replay_agrees':True,
                       'stage1_result_sha256':config['stage1_result_sha256'],
                       'freeze_sha256':hashlib.sha256((ROOT/'LS4L_FREEZE.sha256').read_bytes()).hexdigest(),
                       'source_bytes_verified':sum(r['bytes'] for r in receipts),'raw_arrays_published':False,
                       'reserved_sources_opened':False,'sky_candidates_promoted':0,'physical_completeness':False,
                       'python_version':platform.python_version(),'numpy_version':np.__version__})
        result['result_sha256']=hashlib.sha256(encoded(result)).hexdigest()
        (OUT/'diagnostics.json.gz').write_bytes(gzip.compress(encoded(result),mtime=0))
        summary={'status':result['status'],'paired_configurations':144,'selected_fragment_evaluations':256,
                 'fixed_window_diagnostics':48,'review_passing_configurations':sum(r['review_truth_pass_any'] for r in result['review_configurations']),
                 'review_pass_absent_at_zero_configurations':sum(r['review_pass_absent_at_zero_any'] for r in result['review_configurations']),
                 'original_joint_passes':sum(r['joint_digital_pass'] for r in result['paired_configurations']),
                 'sky_candidates_promoted':0,'source_bytes_verified':result['source_bytes_verified'],'result_sha256':result['result_sha256']}
        write_json(OUT/'summary.json',summary);print(json.dumps(summary,indent=2),flush=True)
    except Exception as exc:
        write_json(OUT/'abort.json',{'status':'aborted-no-complete-conclusion','error':str(exc),'charged_download_bytes':charged,'sources':receipts})
        raise
    finally:
        shutil.rmtree(rawdir)

if __name__=='__main__':main()
