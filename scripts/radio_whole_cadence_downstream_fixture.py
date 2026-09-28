#!/usr/bin/env python3
"""Persist the new deterministic interface scenarios, all triggers and failures."""
import hashlib
import json
from pathlib import Path
import resource
import time
import traceback
import numpy as np
from seti_repeater import search_v0p6 as core
from seti_repeater.empty_null_radio import canonical
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater.whole_cadence_reference_radio import Family, digest, reduce_fixture
from seti_repeater.whole_cadence_downstream_radio import bind_threshold, execute_fixture, IncompleteRetention, operator_binding
from radio_receiver_adapter_common import context

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_radio_whole_cadence_handoff_2026-09-28/downstream01'
NS='radio-whole-cadence-handoff-engineering-20260928/durable-score-fixtures'


def write(name,value):
    with (OUT/name).open('x') as stream:
        json.dump(value,stream,sort_keys=True,indent=2,allow_nan=False);stream.write('\n')


def main():
    started=time.monotonic();OUT.mkdir(exist_ok=False)
    try:
        grid=core.make_proxy_carrier_grid(1400.,2.8,2,9);family=Family('a'*64,'b'*64,2,grid)
        law={'kind':'fixed-score-fixtures','namespace':NS,'random_draws':0,'independent_cadences':False};law_sha=digest(law)
        identity=lambda name:hashlib.sha256((NS+'/'+name).encode()).hexdigest()
        def store(name,edits=()):
            arrays={(k,t,w):np.zeros((3,grid.support_bin_count),dtype='<f4') for k in ('on','off')
                for t in range(2) for w in core.M37_SPECTRAL_WIDTHS}
            for k,t,w,q,values in edits:arrays[k,t,w][:,q+9]=values
            return ScoreStore(arrays,{'context_sha256':family.context_sha256,
                'case_identity':identity(name),'source_domain':'deterministic-score-fixture'})
        names=[f'reference/{i:03d}' for i in range(127)]
        # First unit fixed finite; the other 126 are fully computed EMPTY.
        units=[reduce_fixture(family,store(name,[('on',0,1,2,(8,8,8))] if i==0 else ()),
            case_identity=identity(name),noise_law_sha256=law_sha) for i,name in enumerate(names)]
        threshold=bind_threshold(units,source_family=family,destination_family=family,
            expected_case_identities=[identity(n) for n in names],noise_law_sha256=law_sha)
        write('reference_units.json',[u.record() for u in units]);write('threshold.json',threshold.record());write('law.json',law)
        cases=[('empty',[],{}),('tie',[('on',1,129,2,(8,8,8))],{}),
            ('complete_members',[(k,t,w,q,(20,20,20)) for k in ('on','off') for t in range(2)
                for w in core.M37_SPECTRAL_WIDTHS for q in (0,2,4)],{}),
            ('record_capacity',[('on',0,1,2,(20,20,20))],{'maximum_records':2}),
            ('record_byte_capacity',[('off',1,129,4,(20,20,20))],{'maximum_evidence_bytes':1}),
            ('off_overflow',[('off',1,129,2,(float(np.finfo(np.float32).max),)*3)],{})]
        write('fixed_scenarios_before_execution.json',[{'name':n,'edits':edits,'caps':caps} for n,edits,caps in cases])
        outcomes=[]
        for name,edits,caps in cases:
            values=store('observation/'+name,edits)
            np.savez_compressed(OUT/(name+'_scores.npz'),**{f'{k}_{t:03d}_{w:03d}':v for (k,t,w),v in sorted(values.arrays.items())})
            write(name+'_source.json',{'provenance':values.provenance,'ids':[[*k,v] for k,v in sorted(values.expected_ids.items())]})
            try:
                report=execute_fixture(family,values,threshold,case_identity=identity('observation/'+name),noise_law_sha256=law_sha,**caps)
                if name in ('record_capacity','record_byte_capacity','off_overflow'):raise AssertionError('Expected fail-closed result missing')
                write(name+'_result.json',report)
                outcomes.append({'name':name,'status':'COMPLETE','on':len(report['retained']['on']),'off':len(report['retained']['off'])})
                if name=='complete_members':
                    expected=[(t,wi,w,list(subset),q) for t in range(2) for wi,w in enumerate(core.M37_SPECTRAL_WIDTHS)
                              for subset in core.M37_ACTIVITY_SUBSETS for q in (0,2,4)]
                    for k in ('on','off'):
                        got=[(r['template_index'],r['spectral_width_index'],r['spectral_width_channels'],r['active_epochs_zero_based'],r['proxy_carrier_index']) for r in report['retained'][k]]
                        if got!=expected:raise AssertionError('Exhaustive order differs')
                    if any(not r['rank']['meets_rank_cut'] for r in report['retained']['on']):raise AssertionError('Expected arithmetic rank')
                if name=='tie' and (len(report['retained']['on'])!=1 or report['retained']['on'][0]['rank']['meets_rank_cut']):raise AssertionError('Tie treatment')
            except IncompleteRetention as error:
                if name not in ('record_capacity','record_byte_capacity','off_overflow'):raise
                write(name+'_expected_failure.json',error.evidence)
                outcomes.append({'name':name,'status':'EXPECTED_INCOMPLETE_FAILURE','reason':str(error),
                    'partial_on':len(error.evidence['retained']['on']),'partial_off':len(error.evidence['retained']['off']),
                    'first_capacity_crossing_trigger_retained':'first_unstored_trigger' in error.evidence.get('failure',{})})
        contexts=(context('calibration'),context('validation'))
        families=tuple(Family(c.identity,c.factor_contract.factors.identity,len(c.bank),c.grid) for c in contexts)
        proof=(ROOT/'results_radio_hd189733_score_map_2026-09-28/result.json').read_bytes()
        write('published_translation_binding.json',operator_binding(*families,proof,contexts))
        elapsed=time.monotonic()-started;rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if elapsed>600 or rss>512*1024**2:raise RuntimeError('Interface fixture resource cap')
        write('result.json',{'schema':'radio-whole-cadence-downstream-fixture-result-v1','status':'FIXED_INTERFACE_SCENARIOS_PASS',
            'engineering_reference_receipts':127,'new_independent_scientific_references':0,
            'scenarios':outcomes,'complete_triggers_preserved':385,'capacity_crossing_triggers_preserved':2,
            'partial_triggers_preserved':2,'active_seconds':elapsed,'peak_process_rss_bytes':rss,
            'physical_vetoes_evaluated':False,'scientific_allocations_charged':0,'new_source_requests':0,
            'telescope_values_opened':False,'telescope_admission_authorized':False})
        print(json.dumps(outcomes,indent=2),flush=True)
    except BaseException as error:
        write('error.json',{'error':repr(error),'traceback':traceback.format_exc()});raise


if __name__=='__main__':main()
