#!/usr/bin/env python3
"""Persist complete new physical-stage fixtures, all triggers, vetoes and errors."""
import hashlib
import json
from pathlib import Path
import resource
import time
import traceback
import numpy as np
from seti_repeater import search_v0p6 as core
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater.whole_cadence_reference_radio import Family,digest,reduce_fixture
from seti_repeater.whole_cadence_downstream_radio import bind_threshold
from seti_repeater.whole_cadence_physical_radio import run_fixture,IncompletePhysical
from seti_repeater.receiver_v0p6 import _predicted_midpoint_hz

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_radio_whole_cadence_physical_2026-09-28/physical01'
NS='radio-whole-cadence-physical-engineering-20260928/durable'


def write(name,value):
    with (OUT/name).open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')


def main():
    start=time.monotonic();OUT.mkdir(exist_ok=False)
    try:
        identity=lambda name:hashlib.sha256((NS+'/'+name).encode()).hexdigest()
        grid=core.make_proxy_carrier_grid(.0001,10.,4,9);family=Family('a'*64,'b'*64,2,grid)
        law={'kind':'fixed-score-and-signature-fixture','namespace':NS,'independent_cadences':False,'random_draws':0};law_sha=digest(law)
        factors=np.ones((2,48),dtype='<f8')
        def store(name,edits=()):
            arrays={(k,t,w):np.zeros((3,grid.support_bin_count),dtype='<f4') for k in ('on','off') for t in range(2) for w in core.M37_SPECTRAL_WIDTHS}
            for k,t,w,q,v in edits:arrays[k,t,w][:,q+9]=v
            return ScoreStore(arrays,{'context_sha256':family.context_sha256,'case_identity':identity(name),'source_domain':'deterministic-score-fixture'})
        names=[f'reference/{i:03d}' for i in range(127)]
        units=[reduce_fixture(family,store(n),case_identity=identity(n),noise_law_sha256=law_sha) for n in names]
        threshold=bind_threshold(units,source_family=family,destination_family=family,
            expected_case_identities=[identity(n) for n in names],noise_law_sha256=law_sha)
        write('reference_units.json',[u.record() for u in units]);write('threshold.json',threshold.record())
        write('fixture_contract.json',{'family':family.record(),'law':law,'on_factors':factors.tolist(),'off_factors':factors.tolist()})
        on=lambda t,w,q,v=(20,20,0):('on',t,w,q,v)
        off=lambda t,w,q,v=(20,20,0):('off',t,w,q,v)
        cases=[
            ('empty',[],'prediction',{},[]),
            ('same_off',[on(0,1,4),off(0,1,4)],'prediction',{},['rfi_veto_matched_off_same_hypothesis']),
            ('local_off',[on(0,1,2),off(1,3,4)],'prediction',{},['rfi_veto_local_off_track']),
            ('adjacent_masked',[on(0,1,4),off(0,1,4,(20,0,0))],'prediction',{},['rfi_veto_single_adjacent_off']),
            ('receiver_alias',[on(0,1,0),on(1,3,8)],'center',{},['rfi_veto_receiver_frame_alias']*2),
            ('physical_survivor',[on(0,1,4)],'prediction',{},['pending_receiver_alias_evaluation']),
            ('transitive_component',[on(0,1,q) for q in (0,2,4)],'prediction',{},['pending_receiver_alias_evaluation']*3),
            ('off_before_alias',[on(0,1,0),off(0,1,0),on(1,3,8)],'center',{},['rfi_veto_matched_off_same_hypothesis','rfi_veto_receiver_frame_alias']),
            ('off_capacity',[on(0,1,4),off(0,3,3),off(1,5,5)],'prediction',{'off_candidate_visits':1},'OFF candidate'),
            ('alias_capacity',[on(0,1,0),on(1,3,8)],'center',{'alias_candidate_visits':1},'Alias candidate'),
            ('bytes_capacity',[on(0,1,4)],'prediction',{'canonical_bytes_per_stage':1},'byte capacity')]
        write('fixed_scenarios_before_execution.json',[{'name':n,'edits':e,'peak_mode':p,'caps':c,'expected':x} for n,e,p,c,x in cases])
        summaries=[];complete_triggers=partial_triggers=0;dispositions={}
        for name,edits,peak_mode,caps,expected in cases:
            name_id='observation/'+name;values=store(name_id,edits)
            np.savez_compressed(OUT/(name+'_scores.npz'),**{f'{k}_{t:03d}_{w:03d}':v for (k,t,w),v in sorted(values.arrays.items())})
            write(name+'_score_source.json',{'provenance':values.provenance,'vector_ids':[[*k,v] for k,v in sorted(values.expected_ids.items())]})
            def receiver(records):
                signatures={}
                for rec in records:
                    entries=[]
                    for epoch in rec['active_epochs_zero_based']:
                        predicted=_predicted_midpoint_hz(rec['carrier_hz'],factors[rec['template_index'],epoch*16:(epoch+1)*16])/1e6
                        peak=predicted if peak_mode=='prediction' else .0001
                        entries.append({'epoch_zero_based':epoch,'predicted_mid_mhz':predicted,'peak_frequency_mhz':peak,
                            'peak_snr':6.,'offset_from_prediction_hz':(peak-predicted)*1e6})
                    signatures[rec['record_id']]=entries
                return signatures,{'signatures_sha256':digest(signatures),'domain':'fixed-signature-fixture'}
            try:
                result=run_fixture(family,values,threshold,case_identity=identity(name_id),noise_law_sha256=law_sha,
                    on_factors=factors,off_factors=factors,receiver_factory=receiver,caps=caps)
                if isinstance(expected,str):raise AssertionError('Expected capacity failure missing')
                got=[r['physical_disposition'] for r in result['decisions']]
                if got!=expected:raise AssertionError('Unexpected fixed disposition: '+name)
                write(name+'_result.json',result)
                triggers=sum(len(v) for v in result['retention']['retained'].values());complete_triggers+=triggers
                for d in got:dispositions[d]=dispositions.get(d,0)+1
                summaries.append({'name':name,'status':'COMPLETE','retained_on':len(result['retention']['retained']['on']),
                    'retained_off':len(result['retention']['retained']['off']),'clusters':len(result['clusters']),
                    'diagnostic_final_members':sum(d['diagnostic_final'] for d in result['decisions'])})
            except IncompletePhysical as error:
                if not isinstance(expected,str) or expected not in str(error):raise
                write(name+'_expected_failure.json',error.evidence)
                triggers=sum(len(v) for v in error.evidence['retention']['retained'].values());partial_triggers+=triggers
                summaries.append({'name':name,'status':'EXPECTED_INCOMPLETE_FAILURE','reason':str(error),
                    'complete_upstream_triggers_preserved':triggers,'failure_stage':error.evidence['failure']['stage']})
            if time.monotonic()-start>600 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>512*1024**2:
                raise RuntimeError('Physical fixture execution cap')
        write('result.json',{'schema':'radio-whole-cadence-physical-fixture-result-v1','status':'FIXED_PHYSICAL_SCENARIOS_PASS',
            'scenarios':summaries,'complete_run_triggers_preserved':complete_triggers,
            'incomplete_run_upstream_triggers_preserved':partial_triggers,'physical_disposition_counts':dispositions,
            'active_seconds':time.monotonic()-start,'peak_process_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'scientific_recovery_or_rfi_rate_measured':False,'native_full_physical_chain_exercised':False,
            'new_scientific_allocations':0,'new_gaussian_values':0,'telescope_values_opened':False})
        print(json.dumps({'scenarios':summaries,'dispositions':dispositions},indent=2),flush=True)
    except BaseException as error:
        write('error.json',{'error':repr(error),'traceback':traceback.format_exc(),'retry_authorized':False});raise


if __name__=='__main__':main()
