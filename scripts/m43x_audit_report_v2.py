"""Audit complete M43X decisions, associations and declared development gates."""
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np
from m43b_active_support import seal
from m43e_economical_bank import read_sealed,write_sealed
from m43f_source_cache_preflight import build_context
from m43r_joint_calibration import grid_context
from m43s_profile_sensitivity import endpoint
from seti_repeater import detector_m43u as detector,search_v0p6 as core

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results_m43x_confirmation'
POLICIES=('neighbor9','epoch_confirmation','remaining_aggregate')

def verify_member_activity_identity(rec):
    members=rec['reference_audit']['members']
    hard=rec['policy_decisions']['epoch_confirmation']
    aggregate=rec['policy_decisions']['remaining_aggregate']
    assert len(members)==len(hard)==len(aggregate)
    for m,h,a in zip(members,hard,aggregate):
        assert m['record_id']==h['record_id']==a['record_id']
        if len(m['active_epochs_zero_based'])==2:
            assert h['passes_evaluated_physical_vetoes']==a['passes_evaluated_physical_vetoes']

def main():
    r=read_sealed(OUT/'result.json');cfg=json.loads((ROOT/'config/m43x_confirmation.json').read_text())
    config_sha=hashlib.sha256((ROOT/'config/m43x_confirmation.json').read_bytes()).hexdigest()
    for p,h in cfg['pinned_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
    prior=set()
    for path in ('config/m43r_joint_calibration.json','config/m43t_mask_comparison.json','config/m43u_prior_neighbor2_shifts.json','config/m43u_signal_interference.json'):
        c=json.loads((ROOT/path).read_text());prior.update(tuple(x) for x in c['calibration_shifts']+c['heldout_shifts'])
    w=json.loads((ROOT/'config/m43w_confirmation.json').read_text());prior.update(tuple(x) for x in w['training_shifts']+w['heldout_shifts'])
    fresh=[tuple(x) for x in cfg['training_shifts']+cfg['heldout_shifts']]
    assert len(prior)==1280 and len(set(fresh))==256 and not set(fresh)&prior
    for zero,a,b in fresh:assert zero==0 and min(a,4097-a,b,4097-b,abs(a-b),4097-abs(a-b))>=128
    train=read_sealed(OUT/'calibration.json');held=read_sealed(OUT/'heldout.json');anchors=read_sealed(OUT/'anchors.json')
    assert len(train['null_maxima'])==len(held['null_maxima'])==128
    cut=max(10.,max(train['null_maxima']))
    assert cut==r['heldout']['threshold'] and r['heldout']==held['diagnostic']
    assert sum(v>=cut for v in held['null_maxima'])==r['heldout']['at_or_above_threshold']
    assert anchors['all_96_arrays_exact'] and anchors['all_48_native_gathers_exact']
    assert len(anchors['queries'])==anchors['remaining_scalar_comparisons']==5920
    packed=(OUT/'case_audits.jsonl.gz').read_bytes();raw=gzip.decompress(packed)
    assert hashlib.sha256(packed).hexdigest()==r['ledger_sha256'] and hashlib.sha256(raw).hexdigest()==r['ledger_uncompressed_sha256']
    ledger=[json.loads(x) for x in raw.splitlines() if x.strip()];assert len(ledger)==256
    _,_,_,metadata,basis,parent,_,_=build_context();bank,table,_=detector.catalogue_bridge(parent,cfg['parent_template_indices'],basis)
    _,grid,_=grid_context();factors=np.stack([core.factor_table_for_scan(table,basis,f'epoch{e+1}_on') for e in range(3)],axis=1)
    endpoints=[];members=0;policy_member_decisions=0;loss_evidence=[]
    for rec,case in zip(ledger,cfg['cases']):
        assert rec['result_sha256']==seal({k:v for k,v in rec.items() if k!='result_sha256'})
        assert rec['case']==case and rec['freeze_commit']==r['freeze_commit'] and rec['config_sha256']==config_sha
        assert rec['binding']==train['binding'] and rec['reference_audit']['overlay']['components']==case['components']
        base=rec['reference_audit'];evidence=rec['confirmation_evidence'];members+=len(base['members'])
        assert len(evidence)==len(base['members']) and set(rec['policy_decisions'])==set(POLICIES)
        matched=endpoint(base,case['reference_truth'],grid,factors,basis,case['strength'],'audit')
        associated=set(matched['associated_record_ids'])
        reference_final={m['record_id'] for m in base['members'] if m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut']}
        for p,e in zip(POLICIES,rec['endpoints']):
            assert (e['policy'],e['case_index'],e['case_type'],e['strength'],e['signal_present'])==(p,case['case_index'],case['case_type'],case['strength'],case['signal_present'])
            final=set();physical=set()
            assert len(rec['policy_decisions'][p])==len(base['members'])
            for m,proof,d in zip(base['members'],evidence,rec['policy_decisions'][p]):
                assert d['record_id']==m['record_id']==proof['record_id']
                values=[m['epoch_values_at_proxy_carrier'][i] for i in m['active_epochs_zero_based']]
                assert proof['minimum_active_ON_score']==min(values)
                assert proof['active_confirmation_passed']==all(v>=5.5 for v in values)
                import math
                active=m['active_epochs_zero_based']
                excluded=max(active,key=lambda e:m['epoch_values_at_proxy_carrier'][e])
                remaining=[e for e in active if e!=excluded]
                total=math.fsum(m['epoch_values_at_proxy_carrier'][e] for e in remaining)
                statistic=total/math.sqrt(len(remaining))
                assert proof['active_epochs']==active and proof['excluded_epoch']==excluded
                assert proof['remaining_epochs']==remaining and proof['remaining_sum']==total
                assert proof['remaining_score']==statistic and proof['remaining_passed']==(statistic>=5.5)
                reasons=[]
                if p=='epoch_confirmation' and not all(v>=5.5 for v in values):reasons.append('active_epoch_below_5p5')
                if p=='remaining_aggregate' and statistic<5.5:reasons.append('remaining_aggregate_below_5p5')
                passing=m['passes_evaluated_physical_vetoes'] and not reasons
                assert d['m43x_rejections']==reasons and d['passes_evaluated_physical_vetoes']==passing
                if passing:
                    physical.add(m['record_id'])
                    if m['meets_diagnostic_rank_cut']:final.add(m['record_id'])
                policy_member_decisions+=1
            assert final<=reference_final and e['final_members']==len(final)
            a=e['truth_association'];assert set(a['associated_record_ids'])==associated
            assert a['associated_final_survivors']==len(final&associated) and a['recovered']==bool(final&associated)
            assert a['associated_physical_survivors']==len(physical&associated)
        if case['signal_present'] and rec['endpoints'][0]['truth_association']['recovered']:
            relevant=associated&reference_final
            for e in rec['endpoints'][1:]:
                if e['truth_association']['recovered']:continue
                by_id={d['record_id']:d for d in rec['policy_decisions'][e['policy']]}
                proof_by_id={d['record_id']:d for d in evidence}
                loss_evidence.append({'case_index':case['case_index'],'case_type':case['case_type'],
                    'strength':case['strength'],'score_index':case['score_index'],'local_template':case['local_template'],
                    'active_epochs':case['active_epochs'],'policy':e['policy'],
                    'lost_associated_members':[{'member':m,'new_decision':by_id[m['record_id']],
                        'confirmation_evidence':proof_by_id[m['record_id']]} for m in base['members'] if m['record_id'] in relevant]})
        endpoints.extend(rec['endpoints'])
    assert endpoints==r['endpoints'] and len(endpoints)==768
    assert sum(c['signal_present'] for c in cfg['cases'])==160
    assert len({(c['score_index'],tuple(c['active_epochs']),c['local_template']) for c in cfg['cases']})==16
    summary=[]
    for p in POLICIES:
        for strength in (16.,40.):
            for kind in dict.fromkeys(c['case_type'] for c in cfg['cases']):
                rows=[e for e in endpoints if (e['policy'],e['strength'],e['case_type'])==(p,strength,kind)]
                assert len(rows)==16
                summary.append({'policy':p,'strength':strength,'case_type':kind,'inputs':16,
                    'truth_associations':sum(e['truth_association']['recovered'] for e in rows),
                    'cases_with_final_members':sum(e['final_members']>0 for e in rows),'final_members':sum(e['final_members'] for e in rows)})
    assert summary==r['summary']
    write_sealed(OUT/'signal_loss_evidence.json',{'source_result':r['result_sha256'],'losses':loss_evidence})
    lookup={(e['case_index'],e['policy']):e for e in endpoints}
    for p,c in r['comparisons'].items():
        rows=[e for e in endpoints if e['policy']==p];loss=[];gain=[];added=[];removed=[]
        for e in rows:
            old=lookup[e['case_index'],'neighbor9']
            a,b=(old['truth_association']['recovered'],e['truth_association']['recovered']) if e['signal_present'] else (old['final_members']>0,e['final_members']>0)
            if b and not a:(gain if e['signal_present'] else added).append(e['case_index'])
            if a and not b:(loss if e['signal_present'] else removed).append(e['case_index'])
        assert [gain,loss,added,removed]==[c['signal_gains'],c['signal_losses'],c['added_leaking_controls'],c['removed_leaking_controls']]
        cond={'no_signal_case_loss':not loss,'no_increased_leaking_control_count':len(added)<=len(removed),
            'zero_ON_OFF_final_members':all(e['final_members']==0 for e in rows if e['case_type']=='ON-OFF'),
            'zero_interferer_only_false_associations':all(not e['truth_association']['recovered'] for e in rows if e['case_type']=='interferer-only'),
            'strict_control_leak_reduction':len(removed)>len(added),
            'zero_supported_spike_final_members':all(e['final_members']==0 for e in rows if e['case_type']=='supported-spike'),
            'zero_shared_heldout_pre_veto_exceedances':r['heldout']['at_or_above_threshold']==0}
        assert cond==c['conditions'] and c['development_gate_passed']==all(cond.values())
        assert not gain and not added
    # Check policy topology and exact component pairing separately from detector.
    for rec in ledger:
        finals={p:{m['record_id'] for m,d in zip(rec['reference_audit']['members'],rec['policy_decisions'][p])
            if d['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut']} for p in POLICIES}
        assert finals['epoch_confirmation']<=finals['remaining_aggregate']<=finals['neighbor9']
        verify_member_activity_identity(rec)
    payload_groups={}
    for rec in ledger:
        key=detector.digest(rec['reference_audit']['overlay']['patch_payloads'])
        payload_groups.setdefault(key,[]).append(rec['case']['case_index'])
    duplicate_groups=[v for v in payload_groups.values() if len(v)>1]
    write_sealed(OUT/'input_identity_groups.json',{'cases':256,'distinct_patch_payload_inventories':len(payload_groups),
        'duplicate_case_groups':duplicate_groups,'independent_realizations_claimed':False})
    pairing=[]
    for stratum in range(16):
        for strength in (16.,40.):
            cs={c['case_type']:c for c in cfg['cases'] if c['stratum']==stratum and c['strength']==strength}
            for kind in ('equal','unequal'):
                assert cs['mixed-'+kind]['components']==cs['combined-'+kind]['components']+cs['interferer-only']['components']
                for p in POLICIES:
                    pairing.append(dict(stratum=stratum,strength=strength,amplitude_profile=kind,policy=p,
                        signal_only_associated=lookup[cs['combined-'+kind]['case_index'],p]['truth_association']['recovered'],
                        mixed_associated=lookup[cs['mixed-'+kind]['case_index'],p]['truth_association']['recovered'],
                        interferer_only_false_association=lookup[cs['interferer-only']['case_index'],p]['truth_association']['recovered']))
    write_sealed(OUT/'matched_components.json',{'pairs':pairing,'component_pairing_exact':True})
    audit=write_sealed(OUT/'artifact_validation.json',{'complete':True,'pinned_files':len(cfg['pinned_sha256']),
        'sealed_inputs':256,'policy_endpoints':768,'reference_member_records':members,'policy_member_decisions':policy_member_decisions,
        'fresh_shift_rows':256,'excluded_prior_rows':1280,'new_scalar_remaining_anchors':5920,
        'all_policy_subsets_exact':True,'two_epoch_identity_checked_on_member_activity':True,
        'validator_revision':'v2-member-activity-only','truth_associations_recomputed':True,'gates_recomputed':True,'result_seal':r['result_sha256']})
    aggregate=[]
    for p in POLICIES:
        rows=[e for e in endpoints if e['policy']==p]
        aggregate.append(dict(policy=p,signal_associations=sum(e['truth_association']['recovered'] for e in rows if e['signal_present']),
            leaking_controls=sum(e['final_members']>0 for e in rows if not e['signal_present']),
            ON_OFF_leaks=sum(e['final_members']>0 for e in rows if e['case_type']=='ON-OFF'),
            spike_leaks=sum(e['final_members']>0 for e in rows if e['case_type']=='supported-spike'),
            false_associations=sum(e['truth_association']['recovered'] for e in rows if e['case_type']=='interferer-only'),
            final_members=sum(e['final_members'] for e in rows)))
    groups=[]
    for p in POLICIES:
        for active in core.M37_ACTIVITY_SUBSETS:
            for strength in (16.,40.):
                for kind in dict.fromkeys(c['case_type'] for c in cfg['cases']):
                    rows=[e for e in endpoints if e['policy']==p and e['strength']==strength and e['case_type']==kind
                        and cfg['cases'][e['case_index']]['active_epochs']==list(active)]
                    assert len(rows)==4
                    groups.append(dict(policy=p,active_epochs=list(active),strength=strength,case_type=kind,inputs=len(rows),
                        truth_associations=sum(e['truth_association']['recovered'] for e in rows),
                        cases_with_final_members=sum(e['final_members']>0 for e in rows)))
    write_sealed(OUT/'activity_breakdown.json',{'groups':groups})
    lines=['# M43X: strongest-epoch-excluded aggregate confirmation','',
        'Completed **256 native inputs, 256 shared base detector executions and 768 paired policy endpoints**. '+
        'One uninjected execution/three endpoints is separate. No candidate or general adoption is claimed.','',
        'The new rule excludes the strongest declared active epoch and requires the normalized sum of the remaining '+
        'epochs to be >=5.5. Both alternatives retain all original neighbor9 vetoes and the shared score threshold.','',
        '| Endpoint | Signal associations /160 | Leaking controls /96 | ON-OFF leaks /32 | Supported spikes /32 | False associations /32 | Development gate |',
        '|---|---:|---:|---:|---:|---:|---|']
    for a in aggregate:
        p=a['policy'];gate='reference' if p=='neighbor9' else str(r['comparisons'][p]['development_gate_passed'])
        lines.append(f"| {p} | {a['signal_associations']} | {a['leaking_controls']} | {a['ON_OFF_leaks']} | {a['spike_leaks']} | {a['false_associations']} | {gate} |")
    lines+=['','## Strength and morphology','',
        'Each cell has 16 paired inputs. Signal rows count associations; interferer-only rows count absent-truth false '+
        'associations; supported-spike and ON-OFF rows count cases with any final member.','',
        '| Strength / input | Neighbor9 | Epoch confirmation | Remaining aggregate |','|---|---:|---:|---:|']
    for strength in (16.,40.):
        for kind in dict.fromkeys(c['case_type'] for c in cfg['cases']):
            rows=[next(s for s in summary if (s['policy'],s['strength'],s['case_type'])==(p,strength,kind)) for p in POLICIES]
            field='cases_with_final_members' if kind in ('supported-spike','ON-OFF') else 'truth_associations'
            lines.append(f'| {strength:g} / {kind} | '+' | '.join(f'{s[field]}/16' for s in rows)+' |')
    lines+=['','## Predeclared gates and losses','']
    for p,c in r['comparisons'].items():
        lines.extend([f'### {p}','',f"Signal losses: {c['signal_losses']}. Signal gains: {c['signal_gains']}.",''])
        lines.extend(f'- {k}: **{v}**.' for k,v in c['conditions'].items())
        lines.append('')
    lines+=['Every lost associated member and its exact epoch evidence is retained in '+
        '[signal_loss_evidence.json](results_m43x_confirmation/signal_loss_evidence.json). '+
        'The complete [activity breakdown](results_m43x_confirmation/activity_breakdown.json) and '+
        '[matched component outcomes](results_m43x_confirmation/matched_components.json) preserve uneven-strength and causal-confusion diagnostics.','',
        '## Interpretation and scope','',
        'The two-epoch aggregate rule is mathematically identical to the hard minimum rule; all member-level two-epoch decisions verify that identity. '+
        'With three epochs it pools the two weaker scores and may retain cases the hard floor rejects. Every hard-floor final set '+
        'is a subset of the aggregate final set, itself a subset of neighbor9. This is not a new independent detection channel.','',
        f'The 256 declared cases have {len(payload_groups)} distinct native patch-payload inventories; '+
        'duplicate control cases are listed in [input_identity_groups.json](results_m43x_confirmation/input_identity_groups.json). '+
        'There are 16 strata at new carriers 1280/2816, four activity subsets and two anchor templates. '+
        'Strengths 16/40 are nominal injection amplitudes, not output SNR. Unequal ratios are rotated [1,1/2] or [1,3/4,1/2]. '+
        'The panel includes exact paired signal-only, interference-only and mixed inputs. Associations use exact activity and '+
        '<=20 Hz center-track residual; an association does not demonstrate causal recovery. Cases are correlated digital '+
        'interventions on one existing observing sequence, not independent observations.','',
        'No OFF rule changed; prior V OFF failures remain unresolved regardless of outcomes at new carriers. '+
        'The exposed W73/74 examples are not counted in this prospective panel. No threshold is fitted after evaluation, '+
        'no failed condition is weakened, and no general detector adoption follows.','',
        '## Calibration and verification','',
        f"Training: 128 fresh shifts, maximum {max(train['null_maxima']):.6f}; shared threshold {cut:.6f}. "+
        f"Held-out: 128 distinct shifts, maximum {max(held['null_maxima']):.6f}, {r['heldout']['at_or_above_threshold']}/128 at or above threshold. "+
        'All 256 new shift rows exclude 1,280 earlier rows. Shared conservative pre-veto evidence is not independent physical FAP or OFF false-veto calibration.','',
        f"All 96 original arrays, 48 native gathers and 5,920 scalar aggregate anchors verify. Four focused tests pass. "+
        f"The audit verifies {len(cfg['pinned_sha256'])} pinned files, 256 sealed inputs, 768 endpoints, {members:,} retained reference records and "+
        f"{policy_member_decisions:,} policy decisions, including all associations, gates, subset relations and exact component pairings. "+
        f"Runtime: {r['wall_seconds']:.1f} seconds. New telescope requests: 0.",'',
        f"Public freeze: `{r['freeze_commit']}`. Result seal: `{r['result_sha256']}`.",'',
        '[Plan](MILESTONE_43X_CONFIRMATION_PLAN.md), [complete result](results_m43x_confirmation/result.json), '+
        '[ledger](results_m43x_confirmation/case_audits.jsonl.gz), [validation](results_m43x_confirmation/artifact_validation.json), '+
        '[run log](results_m43x_confirmation/live_run.log), [manifest](RESULTS_MANIFEST_M43X_CONFIRMATION.sha256).','']
    (ROOT/'MILESTONE_43X_CONFIRMATION_RESULT.md').write_text('\n'.join(lines))
    print(json.dumps({'audit':audit,'aggregate':aggregate,'comparisons':r['comparisons']},indent=2))

if __name__=='__main__':main()
