#!/usr/bin/env python3
"""Synthetic policy-level evidence: existing OFF gate versus diagnostic deferral."""
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import platform
import time
import numpy as np
from seti_repeater.light_sail import apply_abacad_veto
from ls4g_synthetic_recovery import background_pair, inject, evaluate, encoded, verify_manifest

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_ls4k_off_policy'
CLONES={'rfi_clone_clean':'signal_clean','rfi_clone_smooth_off':'signal_smooth_off'}


def configuration():
    return json.loads((ROOT/'config/ls4k_off_policy.json').read_text())


def specs(config):
    for family,background,width,amplitude in itertools.product(config['families'],config['backgrounds'],config['widths_s'],config['amplitudes_sigma']):
        yield dict(family=family,background=background,width_s=width,amplitude_sigma=amplitude)


def build(base,times,spec,config):
    family=CLONES.get(spec['family'],spec['family'])
    if family not in config['families']: raise ValueError('unknown scenario')
    pair=base.copy(); dt=config['sample_time_s']; centers=(np.arange(pair.shape[1])+.5)*dt
    start,stop=config['envelope_s']
    pair[0,(centers>=start)&(centers<stop)]+=config['on_plateau_height_sigma']
    truth=[]
    if family.startswith('signal_'):
        truth=inject(pair[0],times,spec['width_s'],spec['amplitude_sigma'],dt)
    elif family=='isolated_on_smooth_off':
        truth=inject(pair[0],[config['control_time_s']],spec['width_s'],spec['amplitude_sigma'],dt)
    elif family!='null_smooth_off': raise ValueError(family)
    if family!='signal_clean':
        smooth=config['smooth_off']
        pair[1]+=smooth['height_sigma']*np.exp(-.5*((centers-smooth['center_s'])/smooth['sigma_s'])**2)
    if family=='signal_pulsed_off':
        inject(pair[1],[config['control_time_s']],config['control_width_s'],config['control_amplitude_sigma'],dt)
    if family=='signal_reference_pulse':
        inject(pair[0],[config['reference_time_s']],config['control_width_s'],config['control_amplitude_sigma'],dt)
    return pair,truth


def stage1_evidence(family,config):
    family=CLONES.get(family,family)
    if family not in config['families']:raise ValueError('unknown scenario')
    # Stipulated retained-event inputs: no medium search or physical transfer is simulated.
    off=[] if family=='signal_clean' else [config['stipulated_off_event']]
    scans=[{'label':'A1','role':'ON','adjacent_off_labels':['B1'],'search':{'events':[config['stipulated_on_event']]}},
           {'label':'B1','role':'OFF','adjacent_off_labels':[],'search':{'events':off}}]
    detector=config['stage1_settings']
    c=apply_abacad_veto(scans,on_threshold=detector['on_score_threshold'],off_threshold=detector['off_veto_score_threshold'],minimum_frequency_overlap=detector['off_veto_frequency_overlap'])
    if len(c)!=1:raise ValueError('stipulated ON candidate not retained')
    return c[0]


def decisions(stage1_survives,metrics):
    return {'current_gate_pass':bool(stage1_survives and metrics['passed']),
            'current_truth_recovery':bool(stage1_survives and metrics['recovered']),
            'diagnostic_admission':bool(metrics['passed']),
            'diagnostic_truth_recovery':bool(metrics['recovered']),
            'off_vetoed_diagnostic_admission':bool(not stage1_survives and metrics['passed']),
            'sky_candidate_promoted':False}


def main():
    verify_manifest(ROOT/'LS4K_FREEZE.sha256')
    c=configuration()
    settings=json.loads((ROOT/'config/ls4e_residual_qualification.json').read_text())['settings']
    cases=list(specs(c))
    if len(cases)*len(c['seeds'])!=c['expected_scenario_rows']:raise ValueError('grid differs')
    OUT.mkdir(exist_ok=False)
    started=time.monotonic(); rows=[]; evaluations=0
    try:
        for seed in c['seeds']:
            for background in c['backgrounds']:
                base,times=background_pair(seed,background,c); cache={}
                for cell,spec in enumerate(cases):
                    if spec['background']!=background:continue
                    pair,truth=build(base,times,spec,c)
                    waveform_sha=hashlib.sha256(pair.astype('<f8',copy=False).tobytes()).hexdigest()
                    key=(waveform_sha,hashlib.sha256(encoded(truth)).hexdigest())
                    if key not in cache:
                        cache[key]=evaluate(pair,truth,c,settings);evaluations+=1
                    metrics=cache[key]
                    evidence=stage1_evidence(spec['family'],c)
                    rows.append({'cell':cell,'seed':seed,**spec,'waveform_sha256':waveform_sha,
                                 'injected_on_truth':truth,'stage1_off_survives':evidence['survives_adjacent_off_veto'],
                                 'stage1_off_vetoes':evidence['adjacent_off_vetoes'],
                                 **metrics,**decisions(evidence['survives_adjacent_off_veto'],metrics)})
            print(f'seed {seed}: {len(rows)}/{c["expected_scenario_rows"]} scenario rows',flush=True)
        if len(rows)!=c['expected_scenario_rows']:raise ValueError('incomplete grid')
        # Every explicit RFI clone is observationally identical to its signal counterpart.
        lookup={(r['family'],r['background'],r['width_s'],r['amplitude_sigma'],r['seed']):r for r in rows}
        for r in rows:
            if r['family'] in CLONES:
                original=lookup[(CLONES[r['family']],r['background'],r['width_s'],r['amplitude_sigma'],r['seed'])]
                for k in ('waveform_sha256','injected_on_truth','stage1_off_survives','passed','recovered','current_gate_pass','diagnostic_admission'):
                    if r[k]!=original[k]:raise ValueError('clone equivalence failed: '+k)
        raw=b''.join(encoded(r) for r in rows)
        (OUT/'scenarios.jsonl.gz').write_bytes(gzip.compress(raw,mtime=0))
        totals=[]
        for family in c['families']:
            subset=[r for r in rows if r['family']==family]
            keys=('current_gate_pass','current_truth_recovery','diagnostic_admission','diagnostic_truth_recovery','off_vetoed_diagnostic_admission','supported','off_veto','reference_veto')
            totals.append({'family':family,'scenario_rows':len(subset),**{k:sum(r[k] for r in subset) for k in keys}})
        summary={'status':'synthetic-policy-audit-complete','scenario_rows':len(rows),'residual_evaluations':evaluations,
                 'distinct_waveform_pairs':len({r['waveform_sha256'] for r in rows}),'families':totals,
                 'clone_equivalence_verified':True,'raw_spectral_data_read':False,'medium_search_executed':False,
                 'new_sky_candidates_promoted':0,'operational_veto_changed':False,'end_to_end_completeness':False,
                 'ledger_sha256':hashlib.sha256(raw).hexdigest(),'freeze_sha256':hashlib.sha256((ROOT/'LS4K_FREEZE.sha256').read_bytes()).hexdigest(),
                 'elapsed_s':time.monotonic()-started,'python_version':platform.python_version(),'numpy_version':np.__version__}
        summary['result_sha256']=hashlib.sha256(encoded(summary)).hexdigest()
        (OUT/'summary.json').write_bytes(encoded(summary));print(json.dumps(summary,indent=2),flush=True)
    except Exception as exc:
        (OUT/'abort.json').write_bytes(encoded({'status':'aborted-no-complete-conclusion','error':str(exc),'completed_rows':len(rows)}))
        raise

if __name__=='__main__':main()
