#!/usr/bin/env python3
"""Preserve handcrafted gate input/output examples; no detector or RNG runs."""
import json
from pathlib import Path
from radio_receiver_adapter_common import context
from test_radio_whole_cadence_evaluation import fixture
from seti_repeater.whole_cadence_evaluation_radio import evaluate

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_radio_whole_cadence_physical_2026-09-28/gates01'


def main():
    OUT.mkdir(exist_ok=False);c=context('validation');results=[]
    cases=[('associated_on',{'rows':((0,1),(0,2),(1,2),(0,1,2)),'merged':True},True),
        ('missed_on',{'finals':[False]},False),('unassociated_on',{'offsets':[3]},False),
        ('empty_null',{'kind':'noise_null','rows':()},True),
        ('null_broad_leakage',{'kind':'noise_null','rows':((0,1),(0,2)),'widths':[65,129]},False),
        ('matched_off_survivor',{'kind':'matched_on_off'},False),
        ('mixed_cluster',{'rows':((0,1),(0,2)),'offsets':[0,3],'merged':True},True),
        ('inactive_epoch',{'kind':'single_adjacent_off','rows':((0,1),)},False)]
    for name,args,expected in cases:
        report,case=fixture(c,**args)
        result=evaluate(report,c,case['recipe'],expected_case_identity=case['identity'],case_definition=case)
        if result['gate_pass']!=expected:raise ValueError('Fixed gate example differs: '+name)
        for suffix,value in [('input',{'case':case,'report':report,'engineering_fixture_not_a_detector_execution':True}),('result',result)]:
            with (OUT/(name+'_'+suffix+'.json')).open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
        results.append({'name':name,'expected_gate_pass':expected,'observed_gate_pass':result['gate_pass'],'counts':result['counts']})
    with (OUT/'summary.json').open('x') as f:json.dump({'schema':'radio-whole-cadence-gate-fixtures-v1','examples':results,
        'scientific_recovery_or_control_rate_measured':False,'new_random_values':0,'new_attempts':0},f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({'examples':len(results),'all_fixed_gates_match':True,'scientific_experiment':False}))


if __name__=='__main__':main()
