#!/usr/bin/env python3
"""Retrospective diagnostic counterfactual and explicit synthetic origin clones."""
import gzip
import hashlib
import itertools
import json
import os
from pathlib import Path
import platform

import numpy as np

from ls4g_synthetic_recovery import background_pair, inject, truth_matches, encoded, verify_manifest
from ls4i_measured_digital_injections import write_json
from ls4m_control_morphology import replay_checks
from seti_repeater.light_sail_residual import residual_metrics, compare_residuals

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_ls4n_reference_policy'
CLONES={'rfi_clone_reference_early':'train_off_reference_early',
        'rfi_clone_reference_late':'train_off_reference_late'}
KEYS=('frequency_index','window_index','pulse_width_s','medium_amplitude')


def load(name):
    p=ROOT/name; data=p.read_bytes()
    return json.loads(gzip.decompress(data) if p.suffix=='.gz' else data)


def policies(supported, on_reference, off_inside, off_reference, matched):
    state=('inside_and_reference' if off_reference else 'inside_only') if off_inside else ('reference_only' if off_reference else 'quiet')
    current=bool(supported and not on_reference and not off_inside and not off_reference)
    diagnostic=bool(supported and not on_reference and not off_inside)
    return {'off_state':state,'original_htr_pass':current,'counterfactual_htr_pass':diagnostic,
        'original_truth_pass':bool(current and matched>=3),
        'counterfactual_truth_pass':bool(diagnostic and matched>=3),
        'new_diagnostic_pass':bool(diagnostic and not current),'sky_candidate_promoted':False}


def measured(previous,morphology):
    replay_checks(morphology['records'],previous)
    lookup={}
    for record in morphology['records']:
        scales=record['residual_metrics']['scales']
        inside=any(s['inside_pulses'] for s in scales)
        reference=any(s['reference_pulses'] for s in scales)
        for use in record['uses']:
            key=(use['row_index'],use['event_index'])
            if key in lookup:raise ValueError('duplicate measured use')
            lookup[key]=(record['selection_id'],inside,reference)
    rows=[]
    for ri,row in enumerate(previous['paired_configurations']):
        events=[]
        for ei,event in enumerate(row['events']):
            selection,inside,reference=lookup[(ri,ei)]
            decision=policies(event['cross_scale_supported'],event['reference_veto'],inside,reference,event['matched_truth_pulses'])
            if decision['original_htr_pass']!=event['passed'] or decision['original_truth_pass']!=event['truth_associated_pass'] or event['stage1_off_survives']:
                raise ValueError('original HTR or Stage-1 decision changed')
            events.append({'event_index':ei,'selection_id':selection,'original_stage1_off_veto':True,
                'original_stage1_evidence':previous['review_configurations'][ri]['events'][ei]['original_stage1_off_vetoes'],
                'matched_truth_pulses':event['matched_truth_pulses'],'on_reference_veto':event['reference_veto'],
                'off_inside_veto':inside,'off_reference_veto':reference,**decision})
        if row['joint_digital_pass']:raise ValueError('unexpected original joint pass')
        rows.append({'row_index':ri,**{k:row[k] for k in KEYS},'htr_amplitude':row['htr_amplitude'],
            'events':events,'original_truth_pass_any':any(e['original_truth_pass'] for e in events),
            'counterfactual_truth_pass_any':any(e['counterfactual_truth_pass'] for e in events),
            'original_joint_pass':False,'sky_candidate_promoted':False})
    zero={tuple(r[k] for k in KEYS):r for r in rows if r['htr_amplitude']==0}
    if len(rows)!=144 or len(zero)!=36 or len(lookup)!=256:
        raise ValueError('incomplete measured grid')
    for row in rows:
        baseline=zero[tuple(row[k] for k in KEYS)]
        if len(row['events'])!=len(baseline['events']):raise ValueError('same-fragment inventory differs')
        for event,old in zip(row['events'],baseline['events']):
            if event['selection_id']!=old['selection_id']:raise ValueError('zero geometry differs')
            event['same_fragment_zero_counterfactual_truth_pass']=old['counterfactual_truth_pass']
            event['counterfactual_truth_pass_absent_at_zero']=bool(event['counterfactual_truth_pass'] and not old['counterfactual_truth_pass'])
        row['counterfactual_truth_pass_absent_at_zero_any']=any(e['counterfactual_truth_pass_absent_at_zero'] for e in row['events'])
    return rows


def build(base,times,spec,c):
    family=CLONES.get(spec['family'],spec['family'])
    if family not in c['families']:raise ValueError('unknown family')
    pair=base.copy();dt=c['sample_time_s'];t=(np.arange(pair.shape[1])+.5)*dt
    start,stop=c['envelope_s']
    pair[0,(t>=start)&(t<stop)]+=c['on_plateau_height_sigma']
    truth=[];control=[]
    if family.startswith('train_'):
        truth=inject(pair[0],times,spec['width_s'],spec['amplitude_sigma'],dt)
    elif family=='single_off_reference':
        truth=inject(pair[0],[c['control_time_s']],spec['width_s'],spec['amplitude_sigma'],dt)
    elif family!='null_off_reference':raise ValueError('unknown ON family')
    locations={'train_off_inside':(1,c['control_time_s']),
        'train_off_reference_early':(1,c['reference_time_s']),
        'train_off_reference_late':(1,c['late_reference_time_s']),
        'train_on_reference':(0,c['reference_time_s']),
        'null_off_reference':(1,c['reference_time_s']),
        'single_off_reference':(1,c['reference_time_s'])}
    if family in locations:
        destination,time=locations[family]
        control=inject(pair[destination],[time],c['control_width_s'],c['control_amplitude_sigma'],dt)
    return pair,truth,control


def evaluate(pair,truth,c,settings):
    dt=c['sample_time_s']
    on,off=[residual_metrics(x,dt,*c['envelope_s'],settings) for x in pair]
    comparison=compare_residuals(on,off,settings)
    matches={s['requested_width_s']:truth_matches(s['inside_pulses'],truth,s['effective_width_s'],dt) for s in on['scales']}
    associated=max((len(matches[p['widths_s'][0]] & matches[p['widths_s'][1]]) for p in comparison['supporting_scale_pairs']),default=0)
    inside=[len(s['inside_pulses']) for s in off['scales']]
    reference=[len(s['reference_pulses']) for s in off['scales']]
    supported=bool(comparison['supporting_scale_pairs']);on_reference=comparison['on_reference_pulse_veto']
    decision=policies(supported,on_reference,any(inside),any(reference),associated)
    if decision['original_htr_pass']!=comparison['residual_pulse_pattern_pass']:
        raise ValueError('original residual rule differs')
    return {'supported':supported,'matched_truth_pulses':associated,'on_reference_veto':on_reference,
        'off_inside_counts':inside,'off_reference_counts':reference,**decision}


def synthetic(c,settings):
    rows=[];evaluations=0
    partial=OUT/'partial_scenarios.jsonl'
    with partial.open('xb') as ledger:
        for seed in c['seeds']:
            for background in c['backgrounds']:
                base,times=background_pair(seed,background,c);cache={}
                for family,width,amplitude in itertools.product(c['families'],c['widths_s'],c['amplitudes_sigma']):
                    spec={'family':family,'width_s':width,'amplitude_sigma':amplitude}
                    pair,truth,control=build(base,times,spec,c)
                    digest=hashlib.sha256(pair.astype('<f8',copy=False).tobytes()).hexdigest()
                    key=(digest,hashlib.sha256(encoded(truth)).hexdigest())
                    if key not in cache:
                        cache[key]=evaluate(pair,truth,c,settings);evaluations+=1
                    row={'seed':seed,'background':background,**spec,'waveform_sha256':digest,
                        'on_truth':truth,'control_truth':control,**cache[key]}
                    ledger.write(encoded(row));rows.append(row)
            ledger.flush();os.fsync(ledger.fileno())
            write_json(OUT/'checkpoint.json',{'status':'partial-synthetic-checkpoint','completed_rows':len(rows),'last_completed_seed':seed})
            print(f'seed {seed}: {len(rows)}/{c["expected_scenario_rows"]} synthetic rows saved',flush=True)
    if len(rows)!=c['expected_scenario_rows']:raise ValueError('incomplete synthetic grid')
    lookup={(r['family'],r['seed'],r['background'],r['width_s'],r['amplitude_sigma']):r for r in rows}
    if len(lookup)!=len(rows):raise ValueError('duplicate synthetic case')
    for row in rows:
        if row['family'] in CLONES:
            other=lookup[(CLONES[row['family']],row['seed'],row['background'],row['width_s'],row['amplitude_sigma'])]
            if {k:v for k,v in row.items() if k!='family'}!={k:v for k,v in other.items() if k!='family'}:
                raise ValueError('causal clone differs')
    raw=partial.read_bytes()
    (OUT/'scenarios.jsonl.gz').write_bytes(gzip.compress(raw,mtime=0))
    write_json(OUT/'checkpoint.json',{'status':'complete-synthetic-ledger-checkpoint','completed_rows':len(rows),
        'uncompressed_ledger_sha256':hashlib.sha256(raw).hexdigest()})
    partial.unlink()
    return rows,evaluations,hashlib.sha256(raw).hexdigest()


def totals(measured_rows,synthetic_rows):
    bands=[]
    for fi in (0,1):
        rows=[r for r in measured_rows if r['frequency_index']==fi]
        positive=[r for r in rows if r['htr_amplitude']>0 and r['events']]
        zeros=[e for r in rows if r['htr_amplitude']==0 for e in r['events']]
        bands.append({'band_ghz':[8.5,10.5][fi],'full_grid_configurations':len(rows),
            'selected_positive_configurations':len(positive),
            'original_truth_pass_configurations':sum(r['original_truth_pass_any'] for r in rows),
            'counterfactual_truth_pass_configurations':sum(r['counterfactual_truth_pass_any'] for r in rows),
            'counterfactual_positive_selected_passes':sum(r['counterfactual_truth_pass_any'] for r in positive),
            'counterfactual_truth_pass_absent_at_zero':sum(r['counterfactual_truth_pass_absent_at_zero_any'] for r in rows),
            'zero_fragment_evaluations':len(zeros),'zero_counterfactual_truth_passes':sum(e['counterfactual_truth_pass'] for e in zeros),
            'zero_counterfactual_pulse_passes':sum(e['counterfactual_htr_pass'] for e in zeros)})
    families=[]
    for family in sorted({r['family'] for r in synthetic_rows}):
        rows=[r for r in synthetic_rows if r['family']==family]
        fields=('original_htr_pass','counterfactual_htr_pass','original_truth_pass','counterfactual_truth_pass')
        families.append({'family':family,'labelled_rows':len(rows),**{k:sum(r[k] for r in rows) for k in fields}})
    return {'measured_bands':bands,'synthetic_families':families}


def main():
    verify_manifest(ROOT/'LS4N_FREEZE.sha256')
    c=load('config/ls4n_reference_policy.json')
    for name,expected in c['input_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:raise ValueError('changed input: '+name)
    previous=load('results_ls4l_v2_vetoed_fragment_diagnostics/diagnostics.json.gz')
    morphology=load('results_ls4m_control_morphology/morphology.json.gz')
    for value in (previous,morphology):
        identity=value.pop('result_sha256')
        if hashlib.sha256(encoded(value)).hexdigest()!=identity:raise ValueError('input result identity differs')
    OUT.mkdir(exist_ok=False)
    try:
        measured_rows=measured(previous,morphology)
        (OUT/'measured.json.gz').write_bytes(gzip.compress(encoded(measured_rows),mtime=0))
        settings=load('config/ls4e_residual_qualification.json')['settings']
        rows,evaluations,digest=synthetic(c,settings)
        result={'status':'reference-only-diagnostic-audit-complete',**totals(measured_rows,rows),
            'synthetic_labelled_rows':len(rows),'distinct_synthetic_waveforms':len({r['waveform_sha256'] for r in rows}),
            'synthetic_residual_evaluations':evaluations,'clone_equivalence_verified':True,
            'synthetic_ledger_sha256':digest,'measured_sha256':hashlib.sha256(encoded(measured_rows)).hexdigest(),
            'freeze_sha256':hashlib.sha256((ROOT/'LS4N_FREEZE.sha256').read_bytes()).hexdigest(),
            'new_raw_spectral_bytes_read':0,'reserved_sources_opened':False,'operational_veto_changed':False,
            'original_joint_passes':0,'sky_candidates_promoted':0,'false_alarm_probability_calibrated':False,
            'python_version':platform.python_version(),'numpy_version':np.__version__}
        result['result_sha256']=hashlib.sha256(encoded(result)).hexdigest()
        write_json(OUT/'summary.json',result);print(json.dumps(result,indent=2),flush=True)
    except Exception as exc:
        write_json(OUT/'abort.json',{'status':'aborted-no-complete-conclusion','error':str(exc)})
        raise


if __name__=='__main__':main()
