#!/usr/bin/env python3
"""Qualify mock row scheduling/source binding; no actual PRNG or experiment."""
import hashlib
import json
from pathlib import Path
import resource
import time
import traceback
from unittest.mock import patch
import numpy as np
from radio_receiver_adapter_common import ROOT, context
from seti_repeater import transfer_m43g as native
from seti_repeater.whole_cadence_reference_radio import digest
from seti_repeater.whole_cadence_render_radio import prepare, render_mock, DrawPlan, NOISE_LAW_SHA256, MOCK_LAW
from seti_repeater.empty_null_radio import canonical

OUT=ROOT/'results_radio_whole_cadence_physical_2026-09-28/render01'


def write(name,value):
    with (OUT/name).open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')


class MockFactory:
    domain='deterministic-renderer-contract-fixture'
    def __init__(self):self.streams=[];self.calls=[]
    def __call__(self,entropy):
        self.streams.append(entropy);i=entropy[1];parent=self
        class Stream:
            row=0
            def normal(self,mean,sigma,channels):
                if (mean,sigma,channels)!=(100.,1.,65536):raise ValueError('Mock generator arguments changed')
                row=self.row;self.row+=1;parent.calls.append([i,row,mean,sigma,channels])
                # Seed is deliberately unused: this is an arithmetic contract
                # fixture, not a random draw from the proposed law.
                return 100.+((np.arange(channels,dtype='<u4')*17+i*31+row*13)%257).astype('<f8')/512.
        return Stream()


def main():
    start=time.monotonic();OUT.mkdir(exist_ok=False)
    try:
        raw=(ROOT/'config/radio_whole_cadence_null_proposal_20260928.json').read_bytes();proposal=json.loads(raw)
        contexts={role:context('calibration' if role=='calibration' else 'validation') for role in ('calibration','evaluation')}
        index=[]
        with patch('numpy.random.Generator',side_effect=AssertionError('No real Gaussian values authorized')):
            for case in proposal['cases']:
                plan=prepare(contexts[case['role']],case,raw).record()
                index.append({'proposed_case_identity':case['identity'],'role':case['role'],
                    'plan_sha256':plan['plan_sha256'],'random_values_generated':False})
            selected=[proposal['cases'][0],next(c for c in proposal['cases'] if
                c['role']=='evaluation' and c['recipe']['kind']=='on_signal' and c['recipe']['injection_width_channels']==129)]
            write('selected_before_execution.json',[{'case_identity':c['identity'],'role':c['role'],'recipe':c['recipe'],
                'purpose':'deterministic mock contract test; no scientific draw'} for c in selected])
            write('bound_draw_plan_index.json',index);results=[]
            def budget():
                if time.monotonic()-start>600:raise RuntimeError('Renderer fixture active-time cap')
                if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>512*1024**2:raise RuntimeError('Renderer fixture RSS cap')
            for ordinal,case in enumerate(selected):
                c=contexts[case['role']];plan=prepare(c,case,raw);factory=MockFactory()
                write(f'case{ordinal}_plan.json',plan.record())
                run,receipt=render_mock(c,plan,factory,budget=budget)
                if factory.streams!=[(case['seed'],i) for i in range(6)] or factory.calls!=[
                        [i,row,100.,1.,65536] for i in range(6) for row in range(16)]:raise ValueError('Mock draw call order differs')
                if receipt['normal_calls']!=96 or receipt['noise_law_sha256']==NOISE_LAW_SHA256:raise ValueError('Mock mislabeled')
                injected=0
                for label,source in run.sources.items():
                    native.validate_source(source);scope=json.loads(source.scope_json)
                    if (scope['case_identity']==case['identity'] or scope['noise_law_sha256']!=digest(MOCK_LAW)
                            or scope['actual_gaussian_draws'] is not False):raise ValueError('Mock source identity contamination')
                for scan in receipt['row_receipts']:
                    for row in scan['rows']:
                        if row['injected']:
                            injected+=1
                            if abs(row['added_total_power_before_float32']-case['recipe']['total_digital_power'])>1e-9:
                                raise ValueError('Mock injection mass mismatch')
                        elif row['added_total_power_before_float32']!=0.:raise ValueError('Unplanned mock injection')
                if injected!=(0 if ordinal==0 else 48):raise ValueError('Mock active scan selection mismatch')
                np.savez_compressed(OUT/f'case{ordinal}_normalized_sources.npz',**{k:v.values for k,v in run.sources.items()})
                write(f'case{ordinal}_receipt.json',receipt);write(f'case{ordinal}_calls.json',{'streams':factory.streams,'calls':factory.calls})
                write(f'case{ordinal}_source_scopes.json',{k:json.loads(v.scope_json) for k,v in run.sources.items()})
                results.append({'ordinal':ordinal,'mock_case_identity':receipt['case_identity'],
                    'intended_proposed_case_identity':case['identity'],'source_count':len(run.sources),
                    'rows':96,'injected_rows':injected,'max_mass_error':receipt['maximum_mass_error']})
                del run;budget()
            # A bad schedule in the final scan must fail before creating the first stream.
            bad=prepare(contexts[selected[0]['role']],selected[0],raw).record();bad.pop('plan_sha256')
            bad['streams'][-1]['normal_calls']=15;bad['plan_sha256']=digest(bad);factory=MockFactory()
            try:render_mock(contexts[selected[0]['role']],DrawPlan(canonical(bad)),factory)
            except ValueError as error:rejection=str(error)
            else:raise ValueError('Bad final schedule was accepted')
            if factory.streams:raise ValueError('Bad schedule touched a stream')
            write('schedule_negative_check.json',{'rejection':rejection,'streams_created':len(factory.streams)})
        result={'schema':'radio-whole-cadence-renderer-binding-result-v1','status':'METADATA_AND_DETERMINISTIC_MOCK_BINDING_PASS',
            'proposed_plans_bound_without_rng':len(index),'mock_cadences':results,
            'source_normalized_cells_preserved':2*6*16*65536,'new_gaussian_draws':0,
            'scientific_allocations_charged':0,'scores_or_scientific_recovery_computed':False,
            'real_rng_entry_available':False,'active_seconds':time.monotonic()-start,
            'peak_process_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'proposal_not_activated':True,'telescope_values_opened':False}
        write('result.json',result);print(json.dumps(result,indent=2),flush=True)
    except BaseException as error:
        write('error.json',{'error':repr(error),'traceback':traceback.format_exc(),'retry_authorized':False});raise


if __name__=='__main__':main()
