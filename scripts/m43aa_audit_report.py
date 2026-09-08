"""Audit the completed retrospective ledger and extract descriptive comparisons."""
import gzip
import json
from collections import Counter
import numpy as np
from m43aa_native_response import ROOT, OUT, CONFIG, sha
from m43e_economical_bank import read_sealed, write_sealed
from m43v_component_diagnostic import coordinate
from seti_repeater import detector_m43u as detector

def load(p):
    r=json.loads(gzip.decompress(p.read_bytes()))
    assert r['result_sha256']==detector.digest({k:v for k,v in r.items() if k!='result_sha256'})
    return r

def main():
    cfg=json.loads(CONFIG.read_text()); result=read_sealed(OUT/'result.json')
    for p,h in cfg['pinned_sha256'].items(): assert sha(ROOT/p)==h,p
    assert result['complete'] and len(result['summary'])==len(cfg['inputs'])==32
    identities={}; scalar=0; response_count=0; probes=0; history_count=0
    off_shapes=[]; signal_stages=[]; residual=[]; stage_comparisons=[]; patch_checks=[]; correlations=[]
    # Keep only small summaries in memory; full arrays stay in per-input files.
    stages={}; patch_payloads={}; final_members={}
    z=json.loads((ROOT/'config/m43z_joint_controls.json').read_text())
    for summary,spec in zip(result['summary'],cfg['inputs']):
        p=ROOT/summary['file']; assert sha(p)==summary['file_sha256']; r=load(p)
        assert r['spec']==spec and r['freeze_commit']==result['freeze_commit'] and r['config_sha256']==sha(CONFIG)
        assert r['result_sha256']==summary['record_sha256']
        history_count+=spec['variant']=='historical'
        inv=cfg['probes'][spec['group']]; assert len(r['stage_trace'])==len(inv)
        assert [tuple(t['coordinate'][:3])+ (tuple(t['coordinate'][3]),) for t in r['stage_trace']]==[coordinate(p) for p in inv]
        probes+=len(inv)
        members=r['reference_audit']['members']; byid={m['record_id']:m for m in members}
        assert len(byid)==len(members)
        for policy,decisions in r['policy_decisions'].items():
            assert {d['record_id'] for d in decisions}==set(byid)
            finals=[byid[d['record_id']] for d in decisions if d['passes_evaluated_physical_vetoes'] and byid[d['record_id']]['meets_diagnostic_rank_cut']]
            assert len(finals)==r['final_counts'][policy]
            if policy=='combined': final_members[spec['name']]=finals
        payload=r['reference_audit']['overlay']['patch_payloads']; patch_payloads[spec['name']]=payload
        identities.setdefault(detector.digest(payload),[]).append(spec['name'])
        stages[spec['name']]={coordinate(m):dict(disposition=m['physical_disposition'],physical=m['passes_evaluated_physical_vetoes'],
            rank=m['meets_diagnostic_rank_cut'],snr=m['snr'],scores=m['epoch_values_at_proxy_carrier']) for m in members}
        for a in r['responses']:
            assert a['last_proxy_index']-a['first_proxy_index']+1==321
            assert [w['width'] for w in a['widths']]==[1,3,5,9,17,33,65,129]
            for w in a['widths']:
                for kind in ('on','off'):
                    values=np.asarray(w[kind]['values'],dtype='<f4'); base=np.asarray(w[kind]['baseline_values'],dtype='<f4')
                    assert values.shape==base.shape==(3,321) and np.isfinite(values).all() and np.isfinite(base).all()
                    for e,d in enumerate(w[kind]['direct_native']):
                        assert np.float32(d['score']).view('<u4')==values[e,160].view('<u4')
                        raw_sum=np.float32(0)
                        for v in d['filtered_row_values']: raw_sum+=np.float32(v)
                        raw_sum/=np.float32(np.sqrt(len(d['filtered_row_values'])))
                        assert raw_sum.view('<u4')==np.float32(d['score']).view('<u4')
                        scalar+=1
            response_count+=1
        if spec['case_index'] is not None:
            case=z['cases'][spec['case_index']]
            selected_ids=(set(r['associations']['neighbor9']['associated_record_ids']) if case['signal_present']
                          else {m['record_id'] for m in final_members[spec['name']]})
            response_lookup={(a['template_index'],a['proxy_carrier_index']):a for a in r['responses']}
            for m in members:
                if (m['record_id'] not in selected_ids or not m['passes_evaluated_physical_vetoes']
                        or not m['meets_diagnostic_rank_cut']):continue
                t,q,w,active=coordinate(m)
                if (t,q) not in response_lookup:continue
                aw=next(x for x in response_lookup[t,q]['widths'] if x['width']==w)
                correlations.append(dict(name=spec['name'],signal_present=case['signal_present'],coordinate=list(coordinate(m)),
                    active_pair_correlations={f'{e}:{f}':aw['correlations']['on_epoch_pairs'][f'{e}:{f}'] for e in active for f in active if e<f}))
            if case['signal_present'] and spec['variant']=='historical':
                ids=set(r['associations']['neighbor9']['associated_record_ids'])
                counts=Counter((m['spectral_width_channels'],m['physical_disposition']) for m in members if m['record_id'] in ids)
                signal_stages.append(dict(name=spec['name'],associations={p:a['recovered'] for p,a in r['associations'].items()},
                    retained_associated_by_width_and_disposition=[dict(width=w,disposition=d,count=n) for (w,d),n in sorted(counts.items())]))
            if spec['group'].startswith('off'):
                a=next(a for a in r['responses'] if (a['template_index'],a['proxy_carrier_index'])==(case['local_template'],case['score_index']))
                for w in a['widths']:
                    if w['width'] not in (1,17,129):continue
                    for e in case['active_epochs']:
                        off_shapes.append(dict(name=spec['name'],epoch=e,width=w['width'],
                            on_shape=w['on']['shape'][e],off_shape=w['off']['shape'][e],
                            on_increment_shape=w['on']['increment_shape'][e],off_increment_shape=w['off']['increment_shape'][e],
                            paired_correlation=w['correlations']['paired_on_off'][e]))
            if spec['group']=='residual':
                injected={e for c in spec['components'] if c['kind']=='on' for e in c['epochs']}
                lookup={(a['template_index'],a['proxy_carrier_index']):a for a in r['responses']}
                ev={e['record_id']:e for e in r['confirmation_evidence']}
                for m in final_members[spec['name']]:
                    t,q,w,active=coordinate(m); a=lookup[t,q]; aw=next(x for x in a['widths'] if x['width']==w)
                    support=[e for e in active if e not in injected]
                    for e in support:assert aw['on']['values'][e]==aw['on']['baseline_values'][e]
                    residual.append(dict(name=spec['name'],coordinate=list(coordinate(m)),injected_epochs=sorted(injected),
                        actual_active_epochs=list(active),uninjected_supporting_epochs=support,
                        on_scores=m['epoch_values_at_proxy_carrier'],remaining=ev[m['record_id']]['remaining'],
                        supporting_response_exactly_baseline=True,on_shapes=aw['on']['shape'],
                        epoch_correlations=aw['correlations']['on_epoch_pairs']))
    assert scalar==result['direct_native_comparisons']
    # Native patch identity checks are stronger than merely matching central scores.
    for group,ids in cfg['groups'].items():
        if group.startswith('off'):
            a=patch_payloads[f'case{ids[0]:03d}']; signal=patch_payloads[f'case{ids[1]:03d}']
            on=lambda p:{k:v for k,v in p.items() if k.startswith('on:')}
            off=lambda p:{k:v for k,v in p.items() if k.startswith('off:')}
            assert on(a)==on(signal)
            assert off(a)==off(patch_payloads[f'case{ids[0]:03d}.off-only'])
            patch_checks.append(dict(group=group,matched_ON_exact=True,isolated_OFF_exact=True))
        if group.startswith('agg'):
            for i in ids:
                for j in ids:
                    if i>=j:continue
                    first=stages[f'case{i:03d}']; second=stages[f'case{j:03d}']
                    for key in sorted(first.keys()|second.keys()):
                        a=first.get(key); b=second.get(key)
                        if a!=b:
                            stage_comparisons.append(dict(group=group,first=i,second=j,coordinate=list(key),first_stage=a,second_stage=b))
    write_sealed(OUT/'shape_summary.json',dict(rows=off_shapes,scope='descriptive selected panel; no fitted threshold'))
    write_sealed(OUT/'stage_summary.json',dict(signal_cases=signal_stages,coordinate_transitions=stage_comparisons))
    write_sealed(OUT/'residual_summary.json',dict(members=residual,unique_native_configurations=3))
    write_sealed(OUT/'correlation_summary.json',dict(rows=correlations,
        statistic='Unshifted mean-subtracted correlation across 321 samples at the member filter width; retrospective, no fitted cut'))
    alias_examples=[]
    for pure,mixed in ((170,171),(280,281)):
        a=load(OUT/'inputs'/f'case{pure:03d}.json.gz'); b=load(OUT/'inputs'/f'case{mixed:03d}.json.gz')
        q=z['cases'][pure]['score_index']+1; t=z['cases'][pure]['local_template']; active=z['cases'][pure]['active_epochs']
        pa=next(p for p in a['stage_trace'] if p['coordinate']==[t,q,1,active])
        pb=next(p for p in b['stage_trace'] if p['coordinate']==[t,q,1,active])
        assert pa['on_scores']==pb['on_scores'] and pa['off_scores']==pb['off_scores']
        ma=pa['annotated_records'][0]; mb=pb['annotated_records'][0]
        assert ma['member_disposition']=='pending_receiver_alias_evaluation'
        assert mb['member_disposition']=='rfi_veto_receiver_frame_alias'
        assert not mb['off_track_evidence']['local_track']['matched'] and not mb['single_adjacent_off_evidence']['vetoed']
        alias_examples.append(dict(signal_only=pure,mixed=mixed,coordinate=[t,q,1,active],
            central_ON_OFF_scores_identical=True,on_scores=pa['on_scores'],signal_only_annotation=ma,mixed_annotation=mb,
            signal_only_receiver_signatures=pa['receiver_signatures'],mixed_receiver_signatures=pb['receiver_signatures']))
    write_sealed(OUT/'receiver_alias_examples.json',dict(examples=alias_examples))
    write_sealed(OUT/'artifact_validation.json',dict(passed=True,inputs=32,historical_replays=history_count,
        separate_baseline=1,component_only_inputs=3,policy_endpoints=128,sealed_records=32,
        direct_native_comparisons=scalar,template_carrier_responses=response_count,stage_probes=probes,
        distinct_native_patch_inventories=len(identities),identity_groups=identities,paired_patch_checks=patch_checks,
        local_freeze_commit=result['freeze_commit'],public_freeze_verified=False,
        publication_blocker='Automatic approval review rejected publication despite prior ongoing authorization; no alternative upload attempted.',
        result_sha256=result['result_sha256']))
    print(json.dumps(dict(passed=True,inputs=32,historical=history_count,direct_native_comparisons=scalar,
        response_coordinates=response_count,stage_probes=probes,native_inventories=len(identities),residual_members=len(residual)),indent=2))

if __name__=='__main__':main()
