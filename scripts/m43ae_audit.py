"""Independent coordinate/amplitude oracle over sealed M43AE evidence."""
import copy
import json
from collections import Counter
import numpy as np
from m43ac_dual_evidence import context
from m43e_economical_bank import read_sealed, write_sealed
from m43ae_joint_response import ROOT, OUT, CONFIG, sha, comparisons, summaries
from m43s_profile_sensitivity import endpoint
from seti_repeater import detector_m43u as detector, search_v0p6 as core
from seti_repeater.attribution_m43ae import POLICIES, POLICY_HYPOTHESES, HYPOTHESES
from seti_repeater.receiver_v0p6 import _predicted_midpoint_hz


def profile_oracle(p,grid,on,off):
    t,q,w,e,h=(p[k] for k in ('template','score_index','width','epoch','hypothesis'))
    center=grid.score_slice.start+q;first=center-w;stop=center+w+1
    complete=first>=0 and stop<=grid.support_bin_count
    positions=None
    if complete:
        if h=='receiver_mean':
            receiver=np.asarray([_predicted_midpoint_hz(float(f),on[e][t]) for f in grid.support_hz[first:stop]])
            positions=(receiver/_predicted_midpoint_hz(1.,off[e][t])-grid.support_hz[0])/grid.channel_width_hz
            complete=bool(np.all(positions>=0) and np.all(positions<=grid.support_bin_count-1))
        else:
            assert h=='candidate_track';positions=np.arange(first,stop,dtype=float)
    assert p['complete']==complete
    assert p['amplitude_and_shape_share_center'] and p['score_floor']==5.5
    if not complete:
        assert not p['vetoed'];return False
    assert p['first_support_index']==first and p['stop_support_index']==stop and p['radius_proxy_bins']==w
    assert positions.tolist()==p['off_positions']
    left=np.floor(positions).astype(int)
    right=np.minimum(left+1,grid.support_bin_count-1) if h=='receiver_mean' else left.copy()
    weights=positions-left
    assert left.tolist()==p['off_left_indices'] and right.tolist()==p['off_right_indices']
    assert weights.tolist()==p['interpolation_weights']
    a=np.asarray(p['on_values'],dtype=float)
    b=(1-weights)*np.asarray(p['off_left_values'])+weights*np.asarray(p['off_right_values'])
    assert len(a)==2*w+1 and np.isfinite(a).all() and np.isfinite(b).all()
    assert b.tolist()==p['aligned_off_values']
    assert p['on_center_score']==a[w] and p['off_center_score']==b[w]
    ca=a-a.mean();cb=b-b.mean();den=float(np.linalg.norm(ca)*np.linalg.norm(cb))
    correlation=None if den==0 else float(np.dot(ca,cb)/den)
    assert p['correlation']==correlation and p['correlation_floor']==.8
    qualifies=bool(a[w]>=5.5 and b[w]>=5.5)
    veto=bool(qualifies and correlation is not None and correlation>=.8)
    assert p['both_centers_above_floor']==qualifies and p['vetoed']==veto
    assert p['center_shift_bins']==float(positions[w]-center)
    if h=='receiver_mean':
        hz=float(grid.score_hz[q])
        assert p['on_track_span_hz']==float(np.ptp(hz*np.asarray(on[e][t])))
        assert p['off_track_span_hz']==float(np.ptp(hz*np.asarray(off[e][t])))
    return veto


def run():
    cfg=json.loads(CONFIG.read_text());result=read_sealed(OUT/'result.json');freeze=read_sealed(OUT/'public_freeze.json')
    assert freeze['remote_verified'] and freeze['commit']==result['freeze_commit']
    for p,h in cfg['pinned_sha256'].items():assert sha(ROOT/p)==h,p
    _,metadata,basis,parent,pt,bank,table,original,grid,start=context()
    on=[core.factor_table_for_scan(table,basis,f'epoch{e+1}_on') for e in range(3)]
    off=[core.factor_table_for_scan(table,basis,f'epoch{e+1}_off') for e in range(3)]
    factors=np.stack(on,axis=1);expected={c['name']:c for c in cfg['cases']}
    assert len(result['inventory'])==262 and {i['name'] for i in result['inventory']}==set(expected)|{'baseline'}
    anchor=read_sealed(OUT/'anchors.json');assert anchor['all_96_arrays_exact'] and anchor['all_48_native_gathers_exact'] and anchor['new_null_rows']==0
    replay=read_sealed(OUT/'upstream_replay.json');assert replay['passed'] and replay['names']==cfg['upstream_replay_anchors']
    assert replay['freeze_commit']==result['freeze_commit'] and replay['config_sha256']==sha(CONFIG)
    totals=Counter();all_rows=[];payloads=set();fresh_payloads=set();by_case={};baseline_counts=None;baseline_complete=None
    for item in result['inventory']:
        path=ROOT/item['file'];assert sha(path)==item['file_sha256'];rec=read_sealed(path)
        assert rec['result_sha256']==item['record_sha256'] and rec['freeze_commit']==result['freeze_commit']
        assert rec['config_sha256']==sha(CONFIG);case=rec['case'];name=case['name'];by_case[name]=rec
        if name!='baseline':assert case==expected[name]
        reused=case['panel'] in ('baseline','historical');assert rec['upstream_reused']==reused==item['upstream_reused']
        if reused:
            source=cfg['historical_sources'][case['source_name']];assert rec['upstream_source']==source
            assert sha(ROOT/source['file'])==source['file_sha256'];up=read_sealed(ROOT/source['file'])
            assert up['result_sha256']==source['record_sha256'];assert rec['upstream_evidence'] is None
            totals['upstream_audits_reused']+=1
        else:
            assert rec['upstream_source'] is None;up=rec['upstream_evidence'];totals['new_input_detector_executions']+=1
        identity=detector.digest({k:v for k,v in up['reference_audit']['overlay'].items() if k in ('patch_payloads','background_provenance')})
        assert identity==up['native_payload_identity']==rec['native_payload_identity']==item['native_payload_identity']
        payloads.add(identity)
        if not reused:fresh_payloads.add(identity)
        original_members=up['reference_audit']['members'];ids=[m['record_id'] for m in original_members]
        assert len(ids)==len(set(ids));geo=rec['geometry_member_audit'];members=geo['members']
        ds=up['policy_decisions']['geometry_receiver'];assert [d['record_id'] for d in ds]==ids
        assert geo['reused_geometry_decisions_sha256']==detector.digest(ds)
        for old,m,d in zip(original_members,members,ds):
            expected_member=dict(old);expected_member.update({k:d[k] for k in ('passes_evaluated_physical_vetoes','physical_disposition')})
            assert m==expected_member and d['rejections']==[]
        assert geo['final_diagnostic_survivors']==up['final_counts']['geometry_receiver']
        assert geo['final_diagnostic_survivors']==sum(m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut'] for m in members)
        assert geo['all_member_physical_survivors']==sum(m['passes_evaluated_physical_vetoes'] for m in members)
        profiles=rec['profiles']
        for pid,p in profiles.items():
            assert pid==f"{p['template']}:{p['score_index']}:{p['width']}:{p['epoch']}:{p['hypothesis']}"
            profile_oracle(p,grid,on,off);totals['complete_profiles' if p['complete'] else 'incomplete_profiles']+=1
        assert [ev['record_id'] for ev in rec['evidence']]==ids
        old_evidence={e['record_id']:e for e in up['old_confirmation_evidence']}
        seen_profiles=set();checked=set();native_coords={};expected_native=[]
        for m,ev in zip(members,rec['evidence']):
            prior=old_evidence[m['record_id']]
            assert ev['remaining']==prior['remaining'] and ev['diagnostic_original_off_window']==prior['off_window']
            eligible=bool(m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut'] and ev['remaining']['remaining_passed'])
            assert [r['epoch'] for r in ev['epochs']]==m['active_epochs_zero_based']
            t,q,w=(m[k] for k in ('template_index','proxy_carrier_index','spectral_width_channels'))
            for row in ev['epochs']:
                e=row['epoch'];assert row['queried']==eligible and set(row['hypotheses'])==set(HYPOTHESES)
                for h in HYPOTHESES:
                    info=row['hypotheses'][h]
                    if not eligible:
                        assert info==dict(complete=True,vetoed=False,profile_id=None);continue
                    pid=f'{t}:{q}:{w}:{e}:{h}';p=profiles[pid]
                    assert info==dict(complete=p['complete'],vetoed=p['vetoed'],profile_id=pid)
                    if p['complete']:
                        assert p['on_center_score']==m['epoch_values_at_proxy_carrier'][e]
                        if pid not in seen_profiles and (e,w,h) not in checked:
                            for j in (0,w,2*w):
                                coords=[('on',p['first_support_index']+j,p['on_values'][j])]
                                coords += [('off',p[f'off_{side}_indices'][j],p[f'off_{side}_values'][j]) for side in ('left','right')]
                                for kind,pos,score in coords:
                                    key=(kind,e,t,w,pos)
                                    if key in native_coords:assert native_coords[key]==score;continue
                                    native_coords[key]=score;expected_native.append(dict(kind=kind,epoch=e,template=t,width=w,support_index=pos,score=score,exact=True))
                            checked.add((e,w,h))
                    seen_profiles.add(pid);totals['member_profile_links']+=1
        assert seen_profiles==set(profiles) and rec['direct_checks']==expected_native
        totals['direct_native_checks']+=len(expected_native)
        assert set(rec['policy_decisions'])==set(POLICIES)
        for policy,hypotheses in POLICY_HYPOTHESES.items():
            decisions=rec['policy_decisions'][policy];assert [d['record_id'] for d in decisions]==ids
            audited=copy.deepcopy(geo);complete=True
            for m,ev,d in zip(audited['members'],rec['evidence'],decisions):
                reasons=[]
                if not ev['remaining']['remaining_passed']:reasons.append('remaining_aggregate_below_5p5')
                for h in hypotheses:
                    if any(r['hypotheses'][h]['vetoed'] for r in ev['epochs']):reasons.append('co_located_'+h+'_ON_OFF')
                    if not all(r['hypotheses'][h]['complete'] for r in ev['epochs']):
                        reasons.append('incomplete_'+h+'_evidence');complete=False
                if reasons and m['passes_evaluated_physical_vetoes']:
                    m['passes_evaluated_physical_vetoes']=False;m['physical_disposition']='m43ae_rejected_'+'_and_'.join(reasons)
                assert d==dict(record_id=m['record_id'],rejections=reasons,
                    passes_evaluated_physical_vetoes=m['passes_evaluated_physical_vetoes'],physical_disposition=m['physical_disposition'])
                totals['new_policy_member_decisions']+=1
            count=sum(m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut'] for m in audited['members'])
            assert count==rec['final_counts'][policy] and complete==rec['complete_by_policy'][policy]
            if name!='baseline':
                row=next(r for r in rec['endpoints'] if r['policy']==policy)
                association=endpoint(audited,case['reference_truth'],grid,factors,basis,case['strength'],path.name)
                assert row['truth_association']==association and row['recovered']==association['recovered']
                assert row['final_members']==count and row['additional_evidence_complete']==complete
        old_rows=[r for r in rec['endpoints'] if r['policy'] not in POLICIES]
        if reused:
            assert old_rows==[dict(r,name=name,panel=case['panel'],case_index=case['case_index']) for r in up['endpoints']]
        elif name!='baseline':
            for row in old_rows:
                policy=row['policy'];audited=copy.deepcopy(up['reference_audit'])
                for m,d in zip(audited['members'],up['policy_decisions'][policy]):
                    assert m['record_id']==d['record_id'];m.update({k:d[k] for k in ('passes_evaluated_physical_vetoes','physical_disposition')})
                association=endpoint(audited,case['reference_truth'],grid,factors,basis,case['strength'],path.name)
                assert row['truth_association']==association and row['recovered']==association['recovered']
                assert row['final_members']==up['final_counts'][policy]
                assert row['final_members']==sum(m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut'] for m in audited['members'])
                assert row['additional_evidence_complete']==(up['additional_evidence_complete'] if policy=='geometry_receiver_aligned_off_aggregate' else True)
        for p,n in up['final_counts'].items():assert rec['final_counts'][p]==n
        if name=='baseline':baseline_counts=rec['final_counts'];baseline_complete=rec['complete_by_policy']
        else:
            assert len(rec['endpoints'])==13 and {r['policy'] for r in rec['endpoints']}==set(cfg['policies'])
            assert all((r['name'],r['panel'],r['case_index'],r['signal_present'],r['case_type'])==
                       (name,case['panel'],case['case_index'],case['signal_present'],case['case_type']) for r in rec['endpoints'])
        all_rows.extend(rec['endpoints']);totals['inputs']+=1;totals['members']+=len(ids)
    assert all_rows==result['endpoints'] and len(all_rows)==3393
    assert summaries(all_rows,cfg['policies'])==result['summary']
    overlap=fresh_payloads & set(cfg['previous_native_payload_identities'])
    assert comparisons(all_rows,baseline_counts,baseline_complete,not bool(overlap))==result['comparisons']
    assert baseline_counts==result['baseline_counts'] and baseline_complete==result['baseline_complete_by_policy']
    assert len(payloads)==result['distinct_native_payloads'] and len(fresh_payloads)==result['fresh_distinct_native_payloads']
    assert len(overlap)==result['fresh_payload_overlap_with_prior']
    assert totals['upstream_audits_reused']==150 and totals['new_input_detector_executions']==112
    assert result['paired_policy_endpoints_including_baseline']==3406 and result['reused_policy_endpoints']==1500 and result['new_policy_endpoints']==1906
    pairs=[]
    for case in cfg['cases']:
        if case['panel']!='fresh' or case['case_type'] not in ('mixed-unequal','distributed17-moderate-OFF'):continue
        kind='combined-unequal' if case['case_type']=='mixed-unequal' else 'distributed17'
        other=next(c for c in cfg['cases'] if c['panel']=='fresh' and c['case_type']==kind and
                   (c['score_index'],c['local_template'],c['active_epochs'])==(case['score_index'],case['local_template'],case['active_epochs']))
        for policy in cfg['policies']:
            a=next(r for r in by_case[other['name']]['endpoints'] if r['policy']==policy)
            b=next(r for r in by_case[case['name']]['endpoints'] if r['policy']==policy)
            pairs.append(dict(signal_only=other['name'],mixed=case['name'],policy=policy,
                signal_only_recovered=a['recovered'],mixed_recovered=b['recovered'],paired_loss=a['recovered'] and not b['recovered']))
    assert len(pairs)==416
    write_sealed(OUT/'paired_signal_costs.json',dict(comparisons=pairs))
    write_sealed(OUT/'audit.json',dict(passed=True,freeze_commit=result['freeze_commit'],pinned_files=len(cfg['pinned_sha256']),
        totals=dict(totals),upstream_replay_anchors=3,distinct_native_payloads=len(payloads),fresh_payload_overlap=len(overlap),
        new_rule_adopted=False,new_null_rows=0))
    print(json.dumps(dict(passed=True,totals=dict(totals),fresh_payload_overlap=len(overlap))),flush=True)


if __name__=='__main__':run()
