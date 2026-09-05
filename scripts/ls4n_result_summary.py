#!/usr/bin/env python3
"""Verify all retained policy decisions, input joins, scenario keys and clones."""
import gzip
import hashlib
import itertools
import json
from ls4n_reference_policy import ROOT,OUT,load,encoded,write_json,verify_manifest,measured,totals,policies,CLONES


def verified():
    verify_manifest(ROOT/'LS4N_FREEZE.sha256')
    c=load('config/ls4n_reference_policy.json')
    for name,expected in c['input_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:raise ValueError('changed input '+name)
    summary=load('results_ls4n_reference_policy/summary.json');identity=summary.pop('result_sha256')
    if hashlib.sha256(encoded(summary)).hexdigest()!=identity:raise ValueError('result hash differs')
    if summary['freeze_sha256']!=hashlib.sha256((ROOT/'LS4N_FREEZE.sha256').read_bytes()).hexdigest():raise ValueError('freeze hash differs')
    data=gzip.decompress((OUT/'scenarios.jsonl.gz').read_bytes())
    if hashlib.sha256(data).hexdigest()!=summary['synthetic_ledger_sha256']:raise ValueError('ledger hash differs')
    synthetic=[json.loads(line) for line in data.splitlines()]
    mr=load('results_ls4n_reference_policy/measured.json.gz')
    if hashlib.sha256(encoded(mr)).hexdigest()!=summary['measured_sha256']:raise ValueError('measured hash differs')
    expected=measured(load('results_ls4l_v2_vetoed_fragment_diagnostics/diagnostics.json.gz'),load('results_ls4m_control_morphology/morphology.json.gz'))
    if mr!=expected:raise ValueError('measured decisions or joins differ')
    fields=('family','seed','background','width_s','amplitude_sigma')
    lookup={tuple(r[k] for k in fields):r for r in synthetic}
    expected_keys=set(itertools.product(c['families'],c['seeds'],c['backgrounds'],c['widths_s'],c['amplitudes_sigma']))
    if len(synthetic)!=1296 or len(lookup)!=1296 or set(lookup)!=expected_keys:raise ValueError('synthetic grid differs')
    for row in synthetic:
        decisions=policies(row['supported'],row['on_reference_veto'],any(row['off_inside_counts']),any(row['off_reference_counts']),row['matched_truth_pulses'])
        if any(row[k]!=v for k,v in decisions.items()):raise ValueError('synthetic decision differs')
        if row['family'] in CLONES:
            key=(CLONES[row['family']],)+tuple(row[k] for k in fields[1:]);other=lookup[key]
            if {k:v for k,v in row.items() if k!='family'}!={k:v for k,v in other.items() if k!='family'}:raise ValueError('clone differs')
    counts=totals(mr,synthetic)
    if any(summary[k]!=v for k,v in counts.items()):raise ValueError('summary count differs')
    if summary['distinct_synthetic_waveforms']!=len({r['waveform_sha256'] for r in synthetic}):raise ValueError('waveform count differs')
    if summary['synthetic_residual_evaluations']!=len({(r['waveform_sha256'],encoded(r['on_truth'])) for r in synthetic}):raise ValueError('evaluation count differs')
    if any(summary[k] for k in ('new_raw_spectral_bytes_read','reserved_sources_opened','operational_veto_changed','original_joint_passes','sky_candidates_promoted','false_alarm_probability_calibrated')):raise ValueError('scientific boundary differs')
    checkpoint=load('results_ls4n_reference_policy/checkpoint.json')
    if checkpoint['completed_rows']!=1296 or checkpoint['uncompressed_ledger_sha256']!=summary['synthetic_ledger_sha256']:raise ValueError('checkpoint differs')
    summary['result_sha256']=identity
    return summary,mr,synthetic


def main():
    summary,mr,synthetic=verified();grid=[]
    for fi,medium,htr in itertools.product(range(2),(1.,4.,16.),(0.,4.,8.,16.)):
        rows=[r for r in mr if r['frequency_index']==fi and r['medium_amplitude']==medium and r['htr_amplitude']==htr]
        if len(rows)!=6:raise ValueError('incomplete measured cell')
        grid.append({'band_ghz':[8.5,10.5][fi],'medium_amplitude':medium,'htr_amplitude':htr,'configurations':len(rows),
            'selected_configurations':sum(bool(r['events']) for r in rows),
            'original_truth_passes':sum(r['original_truth_pass_any'] for r in rows),
            'counterfactual_truth_passes':sum(r['counterfactual_truth_pass_any'] for r in rows),
            'counterfactual_absent_at_zero':sum(r['counterfactual_truth_pass_absent_at_zero_any'] for r in rows)})
    synthetic_grid=[]
    c=load('config/ls4n_reference_policy.json')
    for family,background,width,amplitude in itertools.product(c['families'],c['backgrounds'],c['widths_s'],c['amplitudes_sigma']):
        rows=[r for r in synthetic if (r['family'],r['background'],r['width_s'],r['amplitude_sigma'])==(family,background,width,amplitude)]
        if len(rows)!=8:raise ValueError('incomplete synthetic cell')
        synthetic_grid.append({'family':family,'background':background,'width_s':width,'amplitude_sigma':amplitude,
            'labelled_rows':8,'original_htr_passes':sum(r['original_htr_pass'] for r in rows),
            'counterfactual_htr_passes':sum(r['counterfactual_htr_pass'] for r in rows),
            'counterfactual_truth_passes':sum(r['counterfactual_truth_pass'] for r in rows)})
    write_json(OUT/'recovery_grid.json',{'measured':grid,'synthetic':synthetic_grid})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
