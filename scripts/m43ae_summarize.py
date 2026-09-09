"""Read-only derivations for the M43AE report, after the independent audit."""
import json
from collections import Counter
from m43e_economical_bank import read_sealed, write_sealed
from m43ae_joint_response import ROOT, OUT, CONFIG
from seti_repeater.attribution_m43ae import POLICIES


def main():
    cfg=json.loads(CONFIG.read_text());result=read_sealed(OUT/'result.json');audit=read_sealed(OUT/'audit.json')
    assert result['complete'] and audit['passed']
    pairs=read_sealed(OUT/'paired_signal_costs.json')['comparisons']
    endpoints=result['endpoints'];changes=[];native=Counter();reasons=Counter();profile_counts=Counter()
    known={'ad_ab_z138','ad_ab_z158','ad_ab_z171','ad_ab_z260','ad_ab_z261','ad_ab_z265','ad_ab_z281','ad_ab_fresh032','ad_new038',
        'fresh048','fresh017'}
    diagnostics=[]
    for item in result['inventory']:
        rec=read_sealed(ROOT/item['file']);case=rec['case'];name=case['name']
        native[case['panel']]+=len(rec['direct_checks'])
        for p in rec['profiles'].values():
            profile_counts[(case['panel'],p['hypothesis'],'complete' if p['complete'] else 'incomplete')]+=1
        if name=='baseline':continue
        up=read_sealed(ROOT/rec['upstream_source']['file']) if rec['upstream_reused'] else rec['upstream_evidence']
        members={m['record_id']:m for m in rec['geometry_member_audit']['members']}
        by_policy={r['policy']:r for r in rec['endpoints']}
        for policy,decisions in rec['policy_decisions'].items():
            for d in decisions:
                m=members[d['record_id']]
                if m['meets_diagnostic_rank_cut'] and m['passes_evaluated_physical_vetoes']:
                    for reason in d['rejections']:reasons[(case['panel'],policy,reason)]+=1
        for policy in POLICIES:
            for ref in ('neighbor9','centered_receiver_off_match_aggregate','geometry_receiver_off_aggregate','geometry_receiver_aligned_off_aggregate'):
                a=by_policy[ref];b=by_policy[policy]
                if (case['signal_present'] and a['recovered']!=b['recovered']) or (not case['signal_present'] and bool(a['final_members'])!=bool(b['final_members'])):
                    changes.append(dict(name=name,panel=case['panel'],signal_present=case['signal_present'],policy=policy,reference=ref,
                        reference_recovered=a['recovered'],new_recovered=b['recovered'],reference_final_members=a['final_members'],new_final_members=b['final_members']))
        if name in known:
            traces=[]
            evidence={e['record_id']:e for e in rec['evidence']}
            rank=[m for m in members.values() if m['meets_diagnostic_rank_cut']]
            excluded=[dict(record_id=m['record_id'],disposition=m['physical_disposition'],remaining=evidence[m['record_id']]['remaining'])
                for m in rank if not m['passes_evaluated_physical_vetoes'] and evidence[m['record_id']]['remaining']['remaining_passed']]
            profile_summary=[]
            for h in ('receiver_mean','candidate_track'):
                ps=[p for p in rec['profiles'].values() if p['hypothesis']==h and p['complete']]
                above=[p for p in ps if p['both_centers_above_floor']]
                profile_summary.append(dict(hypothesis=h,complete_profiles=len(ps),both_centers_above_floor=len(above),
                    veto_profiles=sum(p['vetoed'] for p in ps),
                    on_center_range=[min(p['on_center_score'] for p in ps),max(p['on_center_score'] for p in ps)] if ps else None,
                    off_center_range=[min(p['off_center_score'] for p in ps),max(p['off_center_score'] for p in ps)] if ps else None,
                    correlation_range=[min(p['correlation'] for p in ps if p['correlation'] is not None),max(p['correlation'] for p in ps if p['correlation'] is not None)] if any(p['correlation'] is not None for p in ps) else None,
                    above_floor_correlation_max=max((p['correlation'] for p in above if p['correlation'] is not None),default=None)))
            for rid,m in members.items():
                if not m['meets_diagnostic_rank_cut'] or not m['passes_evaluated_physical_vetoes']:continue
                ev=evidence[rid]
                if not any(row['queried'] for row in ev['epochs']):continue
                queries=[]
                for row in ev['epochs']:
                    for h,query in row['hypotheses'].items():
                        if query['profile_id'] is None:continue
                        p=rec['profiles'][query['profile_id']]
                        keys=('complete','correlation','on_center_score','off_center_score','both_centers_above_floor','vetoed','center_shift_bins')
                        queries.append(dict(epoch=row['epoch'],hypothesis=h,profile_id=query['profile_id'],**{k:p[k] for k in keys if k in p}))
                traces.append(dict(record_id=rid,template=m['template_index'],score_index=m['proxy_carrier_index'],width=m['spectral_width_channels'],
                    remaining=ev['remaining'],original_off_window=ev['diagnostic_original_off_window'],profiles=queries,
                    new_decisions={p:next(d for d in rec['policy_decisions'][p] if d['record_id']==rid) for p in POLICIES}))
            diagnostics.append(dict(name=name,case_type=case['case_type'],signal_present=case['signal_present'],
                policy_endpoints=[dict(policy=p,recovered=r['recovered'],final_members=r['final_members']) for p,r in by_policy.items()],
                rank_eligible_members=len(rank),geometry_pass_before_remaining=sum(m['passes_evaluated_physical_vetoes'] for m in rank),
                remaining_pass_members=sum(evidence[m['record_id']]['remaining']['remaining_passed'] for m in rank),
                upstream_vetoes_among_remaining_pass_members_count=len(excluded),
                upstream_veto_dispositions=dict(Counter(e['disposition'] for e in excluded)),
                upstream_veto_examples_first_three=excluded[:3],profile_summary=profile_summary,
                unqueried_geometry_rank_members=sum(m['passes_evaluated_physical_vetoes'] and not evidence[m['record_id']]['remaining']['remaining_passed'] for m in rank),
                maximum_unqueried_remaining_score=max((evidence[m['record_id']]['remaining']['remaining_score'] for m in rank
                    if m['passes_evaluated_physical_vetoes'] and not evidence[m['record_id']]['remaining']['remaining_passed']),default=None),
                queried_geometry_members=traces))
    assert {d['name'] for d in diagnostics}==known
    paired=[]
    for p in cfg['policies']:
        rows=[r for r in pairs if r['policy']==p]
        paired.append(dict(policy=p,pairs=len(rows),signal_only_recovered=sum(r['signal_only_recovered'] for r in rows),
            mixed_recovered=sum(r['mixed_recovered'] for r in rows),paired_losses=sum(r['paired_loss'] for r in rows),
            lost_pairs=[dict(signal_only=r['signal_only'],mixed=r['mixed']) for r in rows if r['paired_loss']]))
    payload_counts=Counter(r['native_payload_identity'] for r in result['inventory'])
    repeated=[dict(native_payload_identity=h,names=[r['name'] for r in result['inventory'] if r['native_payload_identity']==h]) for h,n in sorted(payload_counts.items()) if n>1]
    write_sealed(OUT/'report_summary.json',dict(source_result_sha256=result['result_sha256'],audit_sha256=audit['result_sha256'],
        paired_signal_costs=paired,endpoint_changes=changes,repeated_native_payloads=repeated,
        direct_checks_by_panel=dict(native),profile_counts=[dict(panel=a,hypothesis=b,status=c,count=n) for (a,b,c),n in sorted(profile_counts.items())],
        rank_eligible_geometry_rejection_reasons=[dict(panel=a,policy=b,reason=c,count=n) for (a,b,c),n in sorted(reasons.items())],
        diagnostic_selection='Nine named M43AD mechanism/weak-support anchors plus the two outcome-selected fresh differences fresh048 and fresh017; retrospective explanation only.'))
    write_sealed(OUT/'mechanism_diagnostics.json',dict(cases=diagnostics,retrospective_only=True,new_endpoint_evaluations=0,
        scope='All queried geometry/rank-eligible members of the eleven named cases, aggregate counts of unqueried failures, and the first three upstream-veto examples. Complete original member inventories remain in the lossless input archive.'))
    print(json.dumps(dict(summary=result['summary'],comparisons=result['comparisons'],paired_signal_costs=paired,
        audit_totals=audit['totals'],distinct_native_payloads=result['distinct_native_payloads'],
        fresh_distinct_native_payloads=result['fresh_distinct_native_payloads'],fresh_payload_overlap=result['fresh_payload_overlap_with_prior']),indent=2))


if __name__=='__main__':main()
