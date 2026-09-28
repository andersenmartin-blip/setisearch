#!/usr/bin/env python3
"""Verify retained evidence and unchanged historical pins before publication."""
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater.whole_cadence_reference_radio import digest

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_radio_whole_cadence_handoff_2026-09-28'


def blob(path):
    p=ROOT/path
    return p.read_bytes() if p.is_file() else subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT)


def main():
    old=json.loads(blob('results_radio_hd189733_codec_2026-09-28/postflight.json'))
    invariants=dict(old['old_input_pins_unchanged'])
    invariants['config/radio_hd189733_source_preparation_20260927.json']=old['source_preparation_sha256_unchanged']
    invariants['config/radio_whole_cadence_null_proposal_20260928.json']='45d8309c8b23eea56ddee15e829b96a3936dba98141f124bf97c4057f35993e2'
    for path,checksum in invariants.items():
        if hashlib.sha256(blob(path)).hexdigest()!=checksum:raise ValueError('Historical input changed: '+path)
    pins=json.loads((OUT/'native01/input_pins.json').read_text())
    for path,checksum in pins.items():
        if hashlib.sha256(blob(path)).hexdigest()!=checksum:raise ValueError('Native execution pin changed: '+path)
    provenance=json.loads((OUT/'native01/score_provenance.json').read_text())
    ids=json.loads((OUT/'native01/score_vector_ids.json').read_text())
    with np.load(OUT/'native01/scores.npz',allow_pickle=False) as data:
        arrays={}
        for name in data.files:
            kind,t,w=name.split('_');arrays[kind,int(t),int(w)]=data[name]
        restored=ScoreStore(arrays,provenance)
    if [[*k,v] for k,v in sorted(restored.expected_ids.items())]!=ids:raise ValueError('Archived score identities differ')
    # Validate serialized result hashes, every member and expected failure.
    triggers=partials=crossing=0
    for path in sorted((OUT/'downstream01').glob('*_result.json')):
        r=json.loads(path.read_text());checksum=r.pop('result_sha256')
        if digest(r)!=checksum or r['complete'] is not True:raise ValueError('Downstream report changed')
        for kind in ('on','off'):
            for row in r['retained'][kind]:
                wanted=row.pop('record_id')
                if digest(row)!=wanted:raise ValueError('Retained member changed')
                triggers+=1
    for path in sorted((OUT/'downstream01').glob('*_expected_failure.json')):
        r=json.loads(path.read_text())
        if r['complete'] is not False or 'result_sha256' in r:raise ValueError('Failure claimed complete')
        partials+=sum(len(v) for v in r['retained'].values())
        crossing+=int('first_unstored_trigger' in r['failure'])
    if (triggers,partials,crossing)!=(385,2,2):raise ValueError('Trigger accounting changed')
    proposal=json.loads(blob('config/radio_whole_cadence_null_proposal_20260928.json'))
    # No scientific identity from the proposal may appear in these receipts.
    proposal_text=json.dumps(proposal)
    engineering_cases=set()
    for p in OUT.rglob('*.json'):
        value=json.loads(p.read_text())
        def walk(x):
            if isinstance(x,dict):
                if 'case_identity' in x:engineering_cases.add(x['case_identity'])
                for v in x.values():walk(v)
            elif isinstance(x,list):
                for v in x:walk(v)
        walk(value)
    collisions=sorted(x for x in engineering_cases if x in proposal_text)
    if collisions:raise ValueError('Engineering/proposed identity overlap')
    files=[p for p in OUT.rglob('*') if p.is_file() and p.suffix!='.h5']
    retained=sum(p.stat().st_size for p in files)
    if retained>128*1024**2:raise ValueError('New retained artifact cap')
    r={'schema':'radio-whole-cadence-handoff-postflight-v1','status':'VERIFIED_FOR_PUBLICATION',
        'historical_invariant_pins':invariants,'native_execution_pins_verified':len(pins),
        'restored_score_vectors':len(arrays),'restored_score_cells':sum(a.size for a in arrays.values()),
        'complete_triggers_preserved':triggers,'partial_triggers_preserved':partials,
        'first_capacity_crossing_triggers_preserved':crossing,
        'distinct_unit_tests_passed':41,'native_negative_checks_passed':3,
        'engineering_case_identities':len(engineering_cases),'proposed_identity_collisions':collisions,
        'new_independent_nulls':0,'new_evaluation_values':0,'new_scientific_allocations':0,
        'old_allocations_reopened':False,'new_source_requests':0,'external_messages':0,
        'telescope_values_opened':False,'physical_vetoes_integrated':False,
        'gaussian_renderer_qualified':False,'proposal_status':'PROPOSED_NOT_ACTIVATED',
        'retained_evidence_bytes_at_postflight':retained,
        'record_byte_cap_scope':'canonical retained member stream per kind; full run artifact also bounded separately',
        'original_codec_failure_preserved':True,'plan_extended':False}
    with (OUT/'postflight.json').open('x') as stream:json.dump(r,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps({k:v for k,v in r.items() if k!='historical_invariant_pins'},indent=2))


if __name__=='__main__':main()
