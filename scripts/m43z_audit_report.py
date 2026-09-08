"""Independent artifact accounting for frozen Z member cuts, associations and gates."""
import gzip,hashlib,json,math
import numpy as np
from m43e_economical_bank import read_sealed,write_sealed
from m43f_source_cache_preflight import build_context
from m43r_joint_calibration import grid_context
from m43s_profile_sensitivity import endpoint
from m43z_joint_controls import ROOT,OUT,CONFIG,sha
from seti_repeater import detector_m43u as detector,search_v0p6 as core
from seti_repeater.confirmation_m43z import POLICIES

def main():
    cfg=json.loads(CONFIG.read_text());r=read_sealed(OUT/'result.json')
    for p,h in cfg['pinned_sha256'].items():assert sha(ROOT/p)==h,p
    prior=set()
    for p in ('config/m43r_joint_calibration.json','config/m43t_mask_comparison.json','config/m43u_prior_neighbor2_shifts.json','config/m43u_signal_interference.json'):
        c=json.loads((ROOT/p).read_text());prior.update(tuple(s) for s in c['calibration_shifts']+c['heldout_shifts'])
    for letter in ('w','x'):
        c=json.loads((ROOT/f'config/m43{letter}_confirmation.json').read_text());prior.update(tuple(s) for s in c['training_shifts']+c['heldout_shifts'])
    fresh=[tuple(s) for s in cfg['training_shifts']+cfg['heldout_shifts']]
    assert len(prior)==1536 and len(set(fresh))==256 and not set(fresh)&prior
    for zero,a,b in fresh:assert zero==0 and min(a,4097-a,b,4097-b,abs(a-b),4097-abs(a-b))>=128
    train=read_sealed(OUT/'calibration.json');held=read_sealed(OUT/'heldout.json');anchors=read_sealed(OUT/'anchors.json')
    assert len(train['null_maxima'])==len(held['null_maxima'])==128
    cut=max(10.,max(train['null_maxima']));assert cut==held['diagnostic']['threshold']
    assert sum(v>=cut for v in held['null_maxima'])==r['heldout']['at_or_above_threshold']
    assert r['heldout']==held['diagnostic'] and anchors['all_96_arrays_exact'] and anchors['all_48_native_gathers_exact']
    assert anchors['reused_unchanged_arithmetic_anchors']=={p:sha(ROOT/p) for p in cfg['unchanged_arithmetic_anchors']}
    packed=(OUT/'case_audits.jsonl.gz').read_bytes();raw=gzip.decompress(packed)
    assert hashlib.sha256(packed).hexdigest()==r['ledger_sha256'] and hashlib.sha256(raw).hexdigest()==r['ledger_uncompressed_sha256']
    ledger=[json.loads(line) for line in raw.splitlines() if line.strip()];assert len(ledger)==320
    _,_,_,metadata,basis,parent,_,_=build_context();bank,table,_=detector.catalogue_bridge(parent,cfg['parent_template_indices'],basis)
    _,grid,_=grid_context();factors=np.stack([core.factor_table_for_scan(table,basis,f'epoch{e+1}_on') for e in range(3)],axis=1)
    endpoints=[];members=0;decisions=0;losses=[];identity_groups={};bycase={}
    for rec,case in zip(ledger,cfg['cases']):
        assert rec['result_sha256']==detector.digest({k:v for k,v in rec.items() if k!='result_sha256'})
        assert rec['case']==case and rec['freeze_commit']==r['freeze_commit'] and rec['config_sha256']==sha(CONFIG)
        assert rec['binding']==train['binding'] and rec['reference_audit']['overlay']['components']==case['components']
        bycase[case['case_index']]=rec
        identity_groups.setdefault(detector.digest(rec['reference_audit']['overlay']['patch_payloads']),[]).append(case['case_index'])
        base=rec['reference_audit'];members+=len(base['members']);proofs=rec['confirmation_evidence']
        assert len(proofs)==len(base['members']) and set(rec['policy_decisions'])==set(POLICIES)
        association=endpoint(base,case['reference_truth'],grid,factors,basis,case['strength'],'audit')
        associated=set(association['associated_record_ids']);finalsets={}
        for policy,ep in zip(POLICIES,rec['endpoints']):
            assert (ep['policy'],ep['case_index'],ep['case_type'],ep['strength'],ep['signal_present'])==(policy,case['case_index'],case['case_type'],case['strength'],case['signal_present'])
            ds=rec['policy_decisions'][policy];assert len(ds)==len(base['members']);physical=set();final=set()
            for m,proof,d in zip(base['members'],proofs,ds):
                assert m['record_id']==proof['record_id']==d['record_id']
                active=m['active_epochs_zero_based'];values=m['epoch_values_at_proxy_carrier'];e=proof['remaining'];o=proof['off_window']
                excluded=max(active,key=lambda k:values[k]);remaining=[k for k in active if k!=excluded]
                total=math.fsum(values[k] for k in remaining);stat=total/math.sqrt(len(remaining))
                assert e['excluded_epoch']==excluded and e['remaining_epochs']==remaining and e['remaining_sum']==total and e['remaining_score']==stat
                assert e['remaining_passed']==(stat>=5.5)
                width=m['spectral_width_channels'];center=grid.score_slice.start+m['proxy_carrier_index']
                assert o['active_epochs']==active and o['radius_proxy_bins']==width//2
                assert o['first_support_index']==center-width//2 and o['stop_support_index']==center+width//2+1
                assert len(o['maxima'])==len(active) and all(math.isfinite(v) for v in o['maxima'])
                assert all(o['first_support_index']<=q<o['stop_support_index'] for q in o['argmax_support_indices'])
                veto=any(v>=5.5 for v in o['maxima']);assert o['vetoed']==veto
                reasons=[]
                if policy in ('off_window','combined') and veto:reasons.append('width_aware_OFF')
                if policy in ('remaining_aggregate','combined') and stat<5.5:reasons.append('remaining_aggregate_below_5p5')
                passes=m['passes_evaluated_physical_vetoes'] and not reasons
                assert d['m43z_rejections']==reasons and d['passes_evaluated_physical_vetoes']==passes
                expected='m43z_rejected_'+'_and_'.join(reasons) if reasons and m['passes_evaluated_physical_vetoes'] else m['physical_disposition']
                assert d['physical_disposition']==expected
                if passes:
                    physical.add(m['record_id'])
                    if m['meets_diagnostic_rank_cut']:final.add(m['record_id'])
                decisions+=1
            finalsets[policy]=final
            assert ep['final_members']==len(final) and set(ep['truth_association']['associated_record_ids'])==associated
            assert ep['truth_association']['associated_physical_survivors']==len(physical&associated)
            assert ep['truth_association']['associated_final_survivors']==len(final&associated) and ep['truth_association']['recovered']==bool(final&associated)
        assert finalsets['combined']==finalsets['off_window']&finalsets['remaining_aggregate']
        assert all(s<=finalsets['neighbor9'] for s in finalsets.values())
        if case['signal_present']:
            for ep in rec['endpoints'][1:]:
                if rec['endpoints'][0]['truth_association']['recovered'] and not ep['truth_association']['recovered']:
                    relevant=associated&finalsets['neighbor9'];index={d['record_id']:d for d in rec['policy_decisions'][ep['policy']]}
                    losses.append(dict(case=case,policy=ep['policy'],lost_members=[dict(member=m,evidence=p,decision=index[m['record_id']]) for m,p in zip(base['members'],proofs) if m['record_id'] in relevant]))
        endpoints.extend(rec['endpoints'])
    assert endpoints==r['endpoints'] and len(endpoints)==1280
    assert sum(c['signal_present'] for c in cfg['cases'])==192
    summary=[]
    for p in POLICIES:
        for strength in (24.,48.):
            for kind in dict.fromkeys(c['case_type'] for c in cfg['cases']):
                rows=[e for e in endpoints if (e['policy'],e['strength'],e['case_type'])==(p,strength,kind)];assert len(rows)==16
                summary.append(dict(policy=p,strength=strength,case_type=kind,inputs=16,
                    truth_associations=sum(e['truth_association']['recovered'] for e in rows),cases_with_final_members=sum(e['final_members']>0 for e in rows),final_members=sum(e['final_members'] for e in rows)))
    assert summary==r['summary']
    lookup={(e['case_index'],e['policy']):e for e in endpoints}
    for p,c in r['comparisons'].items():
        rows=[e for e in endpoints if e['policy']==p];gain=[];loss=[];added=[];removed=[]
        for e in rows:
            old=lookup[e['case_index'],'neighbor9']
            a,b=(old['truth_association']['recovered'],e['truth_association']['recovered']) if e['signal_present'] else (old['final_members']>0,e['final_members']>0)
            if b and not a:(gain if e['signal_present'] else added).append(e['case_index'])
            if a and not b:(loss if e['signal_present'] else removed).append(e['case_index'])
        assert [gain,loss,added,removed]==[c['signal_gains'],c['signal_losses'],c['added_leaking_controls'],c['removed_leaking_controls']]
        conditions=dict(no_signal_case_loss=not loss,no_increased_leaking_control_count=len(added)<=len(removed),
            zero_ON_OFF_final_members=all(e['final_members']==0 for e in rows if e['case_type']=='ON-OFF'),
            zero_interferer_only_false_associations=all(not e['truth_association']['recovered'] for e in rows if e['case_type']=='interferer-only'),
            strict_control_leak_reduction=len(removed)>len(added),zero_interferer_only_final_members=all(e['final_members']==0 for e in rows if e['case_type']=='interferer-only'),
            zero_OFF_only_final_members=all(e['final_members']==0 for e in rows if e['case_type']=='OFF-only'),
            zero_supported_spike_final_members=all(e['final_members']==0 for e in rows if e['case_type']=='supported-spike'),
            zero_shared_heldout_pre_veto_exceedances=r['heldout']['at_or_above_threshold']==0)
        assert conditions==c['conditions'] and all(conditions.values())==c['development_gate_passed']
    pairs=[];baseline={(c['pair_group'],c['case_type']):c['case_index'] for c in cfg['cases']};native_pairs=0
    for c in cfg['cases']:
        if not c['matched_signal_only_type']:continue
        origin=baseline[c['pair_group'],c['matched_signal_only_type']]
        if 'OFF' in c['case_type']:
            def onpatch(i):return {k:v for k,v in bycase[i]['reference_audit']['overlay']['patch_payloads'].items() if k.startswith('on:')}
            assert onpatch(origin)==onpatch(c['case_index']);native_pairs+=1
        for p in POLICIES:
            a=lookup[origin,p]['truth_association']['recovered'];b=lookup[c['case_index'],p]['truth_association']['recovered'];ref=lookup[c['case_index'],'neighbor9']['truth_association']['recovered']
            pairs.append(dict(case_index=c['case_index'],signal_only_case_index=origin,case_type=c['case_type'],policy=p,
                signal_only_recovered=a,with_interference_recovered=b,paired_loss=a and not b,paired_gain=b and not a,added_policy_loss_on_interference_input=ref and not b))
    assert pairs==r['matched_component_comparison'] and native_pairs==96
    write_sealed(OUT/'signal_loss_evidence.json',dict(source_result=r['result_sha256'],losses=losses))
    write_sealed(OUT/'input_identity_groups.json',dict(groups=identity_groups,distinct_native_patch_inventories=len(identity_groups)))
    record=dict(passed=True,pinned_files=len(cfg['pinned_sha256']),inputs=320,endpoints=1280,reference_members=members,
        policy_member_decisions=decisions,matched_ON_payload_invariants=native_pairs,distinct_native_patch_inventories=len(identity_groups),
        future_excluded_shift_rows=1792,ledger_sha256=r['ledger_sha256'])
    write_sealed(OUT/'artifact_validation.json',record);print(json.dumps(record,indent=2))
if __name__=='__main__':main()
