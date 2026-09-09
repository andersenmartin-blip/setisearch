import copy
from types import SimpleNamespace
import numpy as np
import pytest
from m43ae_joint_response import geometry_audit, comparisons
from m43ae_audit import profile_oracle
from seti_repeater.attribution_m43ae import response_profile
from seti_repeater.attribution_m43ae import POLICIES


def test_rehydration_preserves_scores_and_rank_but_uses_geometry_decisions():
    members=[dict(record_id='a',passes_evaluated_physical_vetoes=False,physical_disposition='old',
        meets_diagnostic_rank_cut=True,epoch_values_at_proxy_carrier=[6.,7.,8.]),
        dict(record_id='b',passes_evaluated_physical_vetoes=True,physical_disposition='pending_receiver_alias_evaluation',
        meets_diagnostic_rank_cut=False,epoch_values_at_proxy_carrier=[7.,8.,9.])]
    decisions=[dict(record_id='a',passes_evaluated_physical_vetoes=True,physical_disposition='pending_receiver_alias_evaluation',rejections=[]),
        dict(record_id='b',passes_evaluated_physical_vetoes=False,physical_disposition='prior_veto',rejections=[])]
    rec=dict(reference_audit={'members':members,'receiver_alias_certificate':'old'},
        policy_decisions={'geometry_receiver':decisions},final_counts={'geometry_receiver':1})
    untouched=copy.deepcopy(rec);out=geometry_audit(rec)
    assert out['final_diagnostic_survivors']==1 and out['all_member_physical_survivors']==1
    assert out['members'][0]['epoch_values_at_proxy_carrier']==[6.,7.,8.]
    assert 'receiver_alias_certificate' not in out and rec==untouched


def test_signal_loss_fails_even_when_the_control_is_removed():
    refs=('neighbor9','centered_receiver_off_match_aggregate','geometry_receiver_off_aggregate','geometry_receiver_aligned_off_aggregate')
    rows=[]
    for panel in ('historical','fresh'):
        for policy in refs+POLICIES:
            rows.extend([dict(name='signal',panel=panel,policy=policy,signal_present=True,
                recovered=policy in refs,final_members=int(policy in refs),additional_evidence_complete=True),
                dict(name='control',panel=panel,policy=policy,signal_present=False,recovered=False,
                    final_members=int(policy in refs),additional_evidence_complete=True)])
    out=comparisons(rows,{p:0 for p in POLICIES},{p:True for p in POLICIES})
    for row in out.values():
        assert row['conditions']['zero_control_members']
        assert row['conditions']['strict_control_leak_reduction']
        assert not row['conditions']['no_signal_loss'] and not row['development_gate_passed']


@pytest.mark.parametrize('hypothesis', ['receiver_mean','candidate_track'])
def test_coordinate_oracle_detects_a_detached_center_amplitude(hypothesis):
    hz=1000.+np.arange(301)
    g=SimpleNamespace(score_bin_count=201,support_bin_count=301,score_slice=slice(50,251),
        support_hz=hz,score_hz=hz[50:251],channel_width_hz=1.)
    shape=np.exp(-((np.arange(301)-150)/8)**2).astype('<f4')
    on=[np.ones((1,2))]*3;off=[np.full((1,2),1150./1190.5)]*3
    p=response_profile(10*shape,np.roll(10*shape,40),g,100,9,on[0][0],off[0][0],hypothesis)
    p.update(template=0,score_index=100,width=9,epoch=0)
    assert profile_oracle(p,g,on,off)==(hypothesis=='receiver_mean')
    p['off_center_score']+=1.
    with pytest.raises(AssertionError):profile_oracle(p,g,on,off)
