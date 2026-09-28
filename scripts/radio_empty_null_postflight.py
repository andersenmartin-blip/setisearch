#!/usr/bin/env python3
"""Read-only reconciliation of new method evidence and unchanged old pins."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

from seti_repeater.empty_null_radio import canonical

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'results_radio_empty_null_method_2026-09-28'
CHECKPOINT = 'e5841013b40b069eceb5fb7d5d64fd31a01b8764'


def read(path):
    local=ROOT/path
    return local.read_bytes() if local.exists() else subprocess.check_output(
        ['git','show',CHECKPOINT+':'+path],cwd=ROOT)


def main():
    exact=json.loads((BASE/'exact01/result.json').read_text())
    for key,path in [('scope_sha256','RADIO_EMPTY_NULL_METHOD_2026-09-28_SCOPE.md'),
                     ('module_sha256','src/seti_repeater/empty_null_radio.py'),
                     ('script_sha256','scripts/radio_empty_null_exact.py')]:
        assert hashlib.sha256(read(path)).hexdigest()==exact[key],path
    tests={}
    for path,count in [('tests_attempt01.log',17),('reference_engineering/tests_attempt01.log',18)]:
        text=(BASE/path).read_text()
        assert len(re.findall(r'^test_.* \.\.\. ok$',text,re.M))==count
        assert re.search(rf'Ran {count} tests in .*\n\nOK\s*$',text),path
        tests[path]=count
    cfg_path='config/radio_whole_cadence_null_proposal_20260928.json'
    cfg=json.loads(read(cfg_path)); prop=json.loads((BASE/'proposal01/result.json').read_text())
    assert hashlib.sha256(read(cfg_path)).hexdigest()==prop['config_sha256']
    assert cfg['status']=='PROPOSED_NOT_ACTIVATED'
    assert cfg['new_budget_charged'] is False and cfg['new_values_generated'] is False
    for path,checksum in cfg['pins'].items():
        assert hashlib.sha256(read(path)).hexdigest()==checksum,path
    old=json.loads(read('results_radio_hd189733_receiver_2026-09-28/control_identity_reservation.json'))
    old_eval=[x for x in old['identities'] if x['role']=='evaluation']
    new_eval=[x for x in cfg['cases'] if x['role']=='evaluation']
    nulls=[x for x in cfg['cases'] if x['role']=='calibration']
    assert len(nulls)==127 and len(new_eval)==24
    assert cfg['gates']==old['gates'] and cfg['association_rule']==old['association_rule']
    for previous,current in zip(old_eval,new_eval,strict=True):
        recipe={k:v for k,v in previous['recipe'].items() if k!='renderer_frozen'}
        assert current['recipe']==recipe
        assert current['seed']!=previous['seed']
    assert [x['namespace'] for x in cfg['cases']]==cfg['design']['null_namespaces']+cfg['design']['evaluation_namespaces']
    assert [x['seed'] for x in cfg['cases']]==cfg['design']['control_seeds']
    for case in cfg['cases']:
        assert case['identity']==hashlib.sha256(canonical({k:v for k,v in case.items() if k!='identity'})).hexdigest()
        assert case['executed'] is False and case['budget_charged'] is False
    old_result=json.loads(read('results_radio_hd189733_panel_2026-09-28/postflight.json'))
    for path,checksum in old_result['old_input_pins_unchanged'].items():
        assert hashlib.sha256(read(path)).hexdigest()==checksum,path
    source=read('config/radio_hd189733_source_preparation_20260927.json')
    assert hashlib.sha256(source).hexdigest()==old['source_contract_sha256']
    module_path='src/seti_repeater/whole_cadence_reference_radio.py'
    result={
        'schema':'radio-empty-null-method-postflight-v1',
        'status':'METHOD_AND_REFERENCE_ENGINEERING_COMPLETE_PROPOSAL_INACTIVE',
        'checkpoint':CHECKPOINT,'distinct_new_tests_passed':sum(tests.values()),'test_suites':tests,
        'exact_histograms':exact['histograms'],'exact_rank_bound_checks':exact['exact_rank_bound_inequalities'],
        'exact_rank_bound_violations':exact['rank_bound_violations'],
        'proposal_config_sha256':prop['config_sha256'],'proposal_input_pins_verified':len(cfg['pins']),
        'new_reference_module_sha256':hashlib.sha256(read(module_path)).hexdigest(),
        'new_reference_tests_sha256':hashlib.sha256(read('tests/test_radio_whole_cadence_reference.py')).hexdigest(),
        'new_reference_scope_sha256':hashlib.sha256(read('RADIO_WHOLE_CADENCE_REFERENCE_2026-09-28_SCOPE.md')).hexdigest(),
        'proposed_identity_collisions':prop['identity_collisions'],
        'old_input_pins_unchanged':old_result['old_input_pins_unchanged'],
        'source_preparation_sha256_unchanged':hashlib.sha256(source).hexdigest(),
        'recipes_and_gates_unchanged':True,
        'proposed_reference_cadences':127,'proposed_evaluations':24,
        'new_random_or_native_realizations':0,'new_calibration_attempts':0,
        'new_evaluation_attempt_allocations':0,'old_closed_score_archives_read':False,
        'new_source_requests':0,'pilots':0,'remedies':0,'external_messages':0,
        'detector_certificate_issued':False,'native_success_path_qualified':False,
        'telescope_spectra_opened':False,'plan_extended':False,
        'source_inspection_errors_retained':[
            {'requested':'src/seti_repeater/panel_receiver_radio.py','outcome':'path absent; corrected to receiver_panel_radio.py; no execution'},
            {'requested':'src/seti_repeater/threshold*','outcome':'glob matched no files; threshold code located in search_v0p6.py; no execution'}],
    }
    with (BASE/'postflight.json').open('x') as handle:
        json.dump(result,handle,indent=2,sort_keys=True,allow_nan=False);handle.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='old_input_pins_unchanged'},indent=2))


if __name__=='__main__':main()
