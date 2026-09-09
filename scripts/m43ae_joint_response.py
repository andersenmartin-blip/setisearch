"""Frozen joint response study; reuse sealed upstream M43AD evidence."""
import argparse
import copy
import gzip
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import m43ad_geometry as prior
from m43e_economical_bank import read_sealed, write_sealed
from seti_repeater import detector_m43u as detector, search_v0p6 as core
from seti_repeater.attribution_m43ae import apply_controls, evidence_complete, POLICIES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results_m43ae_joint_response'
CONFIG = ROOT/'config/m43ae_joint_response.json'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def context(runtime, cfg):
    _, _, _, metadata, basis, parent, parent_table, _ = prior.build_context()
    bank, table, bridge = detector.catalogue_bridge(parent, cfg['parent_template_indices'], basis)
    assert bridge == cfg['bridge']
    original, grid, start = prior.grid_context()
    assert core.proxy_carrier_grid_sha256(grid) == cfg['grid_sha256']
    anchors = prior.AnchorStore(runtime/'anchors', dict(parent_template_indices=cfg['parent_template_indices'], support_carriers=original.support_bin_count))
    arrays = {k:anchors.get(*k)[0][:,start:start+grid.support_bin_count] for k in anchors.expected_ids}
    provenance = dict(family='M43P-exact-central-slice', parent_inventory_sha256=detector.digest(anchors.inventory),
        parent_score_ids_sha256=detector.digest([[*k,v] for k,v in sorted(anchors.expected_ids.items())]),
        support_start=start,support_count=grid.support_bin_count,grid_sha256=cfg['grid_sha256'])
    assert provenance == read_sealed(ROOT/'results_m43r_joint_calibration/calibration.json')['baseline_provenance']
    baseline = prior.ScoreStore(arrays, provenance)
    receiver = prior.NativeReceiver(runtime/'sources',metadata,basis,parent,parent_table,original)
    overlay = prior.JointOverlay(baseline,receiver,bank,table,basis,grid,progress=lambda m:print(m,flush=True))
    assert overlay.cache_inventory == read_sealed(ROOT/'results_m43u_signal_interference/input_anchors.json')['cache_inventory']
    saved = read_sealed(ROOT/'results_m43z_joint_controls/calibration.json')
    cal,threshold = prior.restore_calibration(saved,saved['result_sha256'],saved['threshold']['certificate_sha256'])
    binding = prior.bind_calibration(cal,threshold,'neighbor9'); assert binding == saved['binding']
    on = [core.factor_table_for_scan(table,basis,f'epoch{e+1}_on') for e in range(3)]
    off = [core.factor_table_for_scan(table,basis,f'epoch{e+1}_off') for e in range(3)]
    return SimpleNamespace(grid=grid,bank=bank,table=table,basis=basis,metadata=metadata,baseline=baseline,
        receiver=receiver,overlay=overlay,cal=cal,threshold=threshold,binding=binding,on=on,off=off,
        factors=np.stack(on,axis=1),cfg=cfg,
        common=dict(window=prior.WINDOW,grid=grid,bank=bank,table=table,basis=basis,scans=metadata['scans']))


def payload_identity(c):
    return detector.digest({k:v for k,v in c.overlay.overlay_receipt.items()
                            if k in ('patch_payloads','background_provenance')})


def upstream(c, case):
    """Execute unchanged M43AD policies for a new input or a named replay anchor."""
    store = c.overlay.trial(case['components'])
    if case['name'] == 'baseline': store = c.baseline
    result = detector.execute(**c.common,store=store,mask_policy='neighbor9',calibration=c.cal,
        threshold=c.threshold,calibration_binding=c.binding,receiver_factory=c.overlay,
        maximum_records=c.cfg['maximum_records'])
    audit = prior.compact(result,c.overlay.overlay_receipt); audit['masked_cell_counts'] = result['masked_cell_counts']
    audits, old_evidence = prior.old_controls(audit,store,c.grid)
    parts = prior.native_parts(c.overlay,case['components']); checks=[]; profile_checks=[]
    def centered_check(e,w,raw,score):
        src=c.receiver.cache(f'epoch{e+1}_on',1).source
        direct=prior.raw_window_score(src,np.full(src.integration_count,raw),parts.get(('on',e),[]),w)
        assert np.float32(direct['score']).view('<u4') == np.float32(score).view('<u4')
        checks.append(dict(epoch=e,width=w,native_center=raw,score=score,exact=True))
    sigs,receipt=prior.centered_signatures(c.overlay,result['retained']['on'],centered_check)
    centered=prior.reclassify(result,sigs,receipt,c.grid,c.bank,c.table,c.basis,c.metadata['scans'],prior.WINDOW,c.cfg['maximum_records'])
    centered_audits,centered_evidence=prior.centered_controls(prior.compact(centered,c.overlay.overlay_receipt),store,c.grid)
    audits.update(centered_audits)
    selected,geo_receipt,geometry=prior.attributed_signatures(result['retained']['on'],result['receiver_signatures'],sigs,c.on,c.grid)
    geo=prior.reclassify(result,selected,geo_receipt,c.grid,c.bank,c.table,c.basis,c.metadata['scans'],prior.WINDOW,c.cfg['maximum_records'])
    geo['schema']='m43ad-geometry-attributed-receiver-v1';geo.pop('result_sha256');geo['result_sha256']=detector.digest(geo)
    def profile_check(kind,e,t,w,index,score):
        src=c.receiver.cache(f'epoch{e+1}_{kind}',1).source
        direct=prior.raw_window_score(src,c.overlay.joint_indices[kind,e][t,:,index],parts.get((kind,e),[]),w)
        assert np.float32(direct['score']).view('<u4') == np.float32(score).view('<u4')
        profile_checks.append(dict(kind=kind,epoch=e,template=t,width=w,support_index=index,score=score,exact=True))
    geometry_audits,geo_evidence=prior.apply_controls(prior.compact(geo,c.overlay.overlay_receipt),store,c.grid,c.on,c.off,profile_check)
    audits.update(geometry_audits)
    record=dict(reference_audit=audits['neighbor9'],policy_decisions=prior.policy_decisions(audits),
        old_confirmation_evidence=old_evidence,new_confirmation_evidence=centered_evidence,
        original_signatures=result['receiver_signatures'],centered_signatures=sigs,centered_receipt=receipt,
        centered_alias=centered['receiver_alias'],original_alias=result['receiver_alias'],direct_checks=checks,
        geometry_signatures=selected,geometry_receipt=geo_receipt,geometry_evidence=geometry,
        geometry_alias=geo['receiver_alias'],geometry_confirmation_evidence=geo_evidence,
        profile_direct_checks=profile_checks,additional_evidence_complete=all(e['aligned_complete'] for e in geo_evidence),
        native_payload_identity=payload_identity(c),final_counts={p:a['final_diagnostic_survivors'] for p,a in audits.items()})
    return store,record,audits


def geometry_audit(record):
    """Rehydrate decisions without attributing old certificates to new policies."""
    members=copy.deepcopy(record['reference_audit']['members'])
    decisions=record['policy_decisions']['geometry_receiver']
    assert [m['record_id'] for m in members] == [d['record_id'] for d in decisions]
    for m,d in zip(members,decisions):
        assert d['rejections'] == []
        m.update({k:d[k] for k in ('passes_evaluated_physical_vetoes','physical_disposition')})
    final=sum(m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut'] for m in members)
    assert final == record['final_counts']['geometry_receiver']
    return dict(members=members,final_diagnostic_survivors=final,
        all_member_physical_survivors=sum(m['passes_evaluated_physical_vetoes'] for m in members),
        reused_geometry_decisions_sha256=detector.digest(decisions))


def endpoint_row(c,case,policy,audit,artifact,complete):
    association=prior.endpoint(audit,case['reference_truth'],c.grid,c.factors,c.basis,case['strength'],artifact)
    return dict(name=case['name'],panel=case['panel'],case_index=case['case_index'],policy=policy,
        case_type=case['case_type'],signal_present=case['signal_present'],recovered=association['recovered'],
        final_members=audit['final_diagnostic_survivors'],truth_association=association,
        additional_evidence_complete=complete)


def comparisons(endpoints,baseline_counts,baseline_complete,fresh_novel=True):
    out={}
    references=('neighbor9','centered_receiver_off_match_aggregate','geometry_receiver_off_aggregate','geometry_receiver_aligned_off_aggregate')
    for panel in ('historical','fresh'):
        for policy in POLICIES:
            rows=[r for r in endpoints if r['panel']==panel and r['policy']==policy]
            changes={}
            for ref in references:
                before={r['name']:r for r in endpoints if r['panel']==panel and r['policy']==ref}
                changes[ref]=dict(
                    signal_gains=[r['name'] for r in rows if r['signal_present'] and r['recovered'] and not before[r['name']]['recovered']],
                    signal_losses=[r['name'] for r in rows if r['signal_present'] and not r['recovered'] and before[r['name']]['recovered']],
                    added_leaking_controls=[r['name'] for r in rows if not r['signal_present'] and r['final_members'] and not before[r['name']]['final_members']],
                    removed_leaking_controls=[r['name'] for r in rows if not r['signal_present'] and not r['final_members'] and before[r['name']]['final_members']])
            ref=changes['neighbor9']; controls=[r for r in rows if not r['signal_present']]
            gates=dict(no_signal_loss=not ref['signal_losses'],zero_control_members=all(r['final_members']==0 for r in controls),
                zero_false_control_associations=all(not r['recovered'] for r in controls),
                strict_control_leak_reduction=len(ref['removed_leaking_controls'])>len(ref['added_leaking_controls']),
                zero_baseline_members=baseline_counts[policy]==0,
                preserve_centered_combination_signals=not changes['centered_receiver_off_match_aggregate']['signal_losses'],
                preserve_geometry_original_off_signals=not changes['geometry_receiver_off_aggregate']['signal_losses'],
                complete_additional_evidence=baseline_complete[policy] and all(r['additional_evidence_complete'] for r in rows),
                novel_additional_payloads=panel!='fresh' or fresh_novel)
            out[f'{panel}:{policy}']=dict(reference_changes=changes,conditions=gates,development_gate_passed=all(gates.values()))
    return out


def summaries(endpoints,policies):
    out=[]
    for panel in ('historical','fresh'):
        for policy in policies:
            rows=[r for r in endpoints if (r['panel'],r['policy'])==(panel,policy)]
            signal=[r for r in rows if r['signal_present']];control=[r for r in rows if not r['signal_present']]
            out.append(dict(panel=panel,policy=policy,signal_inputs=len(signal),control_inputs=len(control),
                recovered_signals=sum(r['recovered'] for r in signal),leaking_controls=sum(r['final_members']>0 for r in control),
                false_control_associations=sum(r['recovered'] for r in control)))
    return out


def run(runtime,freeze,preflight=False):
    started=time.monotonic();cfg=json.loads(CONFIG.read_text())
    assert platform.python_version()==cfg['python_version'] and np.__version__==cfg['numpy_version']
    assert all(importlib.metadata.version(n)==v for n,v in cfg['dependencies'].items())
    for p,h in cfg['pinned_sha256'].items(): assert sha(ROOT/p)==h,p
    OUT.mkdir(exist_ok=True)
    if not preflight:
        assert subprocess.check_output(['git','show',freeze+':config/m43ae_joint_response.json'],cwd=ROOT)==CONFIG.read_bytes()
        publication=read_sealed(OUT/'public_freeze.json');assert publication['commit']==freeze and publication['remote_verified']
        assert not (OUT/'result.json').exists(),'preserve completed result'
    c=context(runtime,cfg)
    if preflight:
        write_sealed(OUT/'runtime_preflight.json',dict(passed=True,all_96_arrays_exact=True,all_48_native_gathers_exact=True,
            calibration_restored_without_new_nulls=True,new_cases_scored=0,new_rule_evaluated=False,
            wall_seconds=round(time.monotonic()-started,3)))
        print('M43AE OPERATIONAL PREFLIGHT PASSED',flush=True);return
    write_sealed(OUT/'anchors.json',dict(all_96_arrays_exact=True,all_48_native_gathers_exact=True,new_null_rows=0))
    historical={}
    for name,item in cfg['historical_sources'].items():
        path=ROOT/item['file'];assert sha(path)==item['file_sha256']
        record=read_sealed(path);assert record['result_sha256']==item['record_sha256'];historical[name]=record
    replay_file=OUT/'upstream_replay.json'
    if replay_file.exists():
        replay=read_sealed(replay_file);assert replay['freeze_commit']==freeze and replay['config_sha256']==sha(CONFIG)
        assert replay['names']==cfg['upstream_replay_anchors'] and replay['passed']
    else:
        replay_checks=[]
        for name in cfg['upstream_replay_anchors']:
            previous=historical[name];_,record,_=upstream(c,previous['case'])
            for key,value in record.items(): assert value==previous[key],(name,key)
            replay_checks.append(dict(name=name,fields=list(record),exact=True))
            print('UPSTREAM EXACT REPLAY',name,flush=True)
        write_sealed(replay_file,dict(passed=True,names=cfg['upstream_replay_anchors'],checks=replay_checks,
            freeze_commit=freeze,config_sha256=sha(CONFIG)))
    (OUT/'inputs').mkdir(exist_ok=True);inventory=[];endpoints=[];baseline_counts=None;baseline_complete=None
    specs=[dict(name='baseline',panel='baseline',components=[],source_name='baseline')]+cfg['cases']
    for index,case in enumerate(specs):
        path=OUT/'inputs'/(case['name']+'.json.gz')
        if path.exists():
            rec=read_sealed(path);assert rec['freeze_commit']==freeze and rec['config_sha256']==sha(CONFIG) and rec['case']==case
        else:
            reused=case['panel'] in ('historical','baseline')
            if reused:
                original=historical[case['source_name']]
                store=c.overlay.trial(case['components'])
                if case['panel']=='baseline':store=c.baseline
                assert payload_identity(c)==original['native_payload_identity'],case['name']
                old_rows=[dict(r,name=case['name'],panel=case['panel'],case_index=case['case_index']) for r in original['endpoints']]
                source=cfg['historical_sources'][case['source_name']]
            else:
                store,original,old_audits=upstream(c,case);source=None
                old_rows=[endpoint_row(c,case,p,a,path.name,original['additional_evidence_complete'] if p==prior.POLICIES[-1] else True)
                          for p,a in old_audits.items()]
            geo=geometry_audit(original);parts=prior.native_parts(c.overlay,case['components']);direct=[];seen={}
            def check(kind,e,t,w,pos,score):
                key=(kind,e,t,w,pos)
                if key in seen: assert seen[key]==score;return
                src=c.receiver.cache(f'epoch{e+1}_{kind}',1).source
                measured=prior.raw_window_score(src,c.overlay.joint_indices[kind,e][t,:,pos],parts.get((kind,e),[]),w)
                assert np.float32(measured['score']).view('<u4')==np.float32(score).view('<u4'),(case['name'],key)
                seen[key]=score;direct.append(dict(kind=kind,epoch=e,template=t,width=w,support_index=pos,score=score,exact=True))
            audits,evidence,profiles=apply_controls(geo,store,c.grid,c.on,c.off,check)
            complete={p:evidence_complete(evidence,p) for p in POLICIES}
            rows=old_rows
            if case['panel']!='baseline':rows += [endpoint_row(c,case,p,a,path.name,complete[p]) for p,a in audits.items()]
            decisions={p:[dict(record_id=m['record_id'],passes_evaluated_physical_vetoes=m['passes_evaluated_physical_vetoes'],
                physical_disposition=m['physical_disposition'],rejections=m['m43ae_rejections']) for m in a['members']] for p,a in audits.items()}
            rec=dict(case=case,freeze_commit=freeze,config_sha256=sha(CONFIG),upstream_reused=reused,
                upstream_source=source,upstream_evidence=None if reused else original,geometry_member_audit=geo,
                native_payload_identity=original['native_payload_identity'],evidence=evidence,profiles=profiles,
                direct_checks=direct,policy_decisions=decisions,complete_by_policy=complete,
                final_counts=original['final_counts']|{p:a['final_diagnostic_survivors'] for p,a in audits.items()},endpoints=rows)
            rec['result_sha256']=detector.digest(rec)
            temporary=path.with_suffix('.tmp');temporary.write_bytes(gzip.compress(core.canonical_json_bytes(rec),compresslevel=6,mtime=0));temporary.replace(path)
        endpoints.extend(rec['endpoints'])
        if case['panel']=='baseline':baseline_counts=rec['final_counts'];baseline_complete=rec['complete_by_policy']
        inventory.append(dict(name=case['name'],file=path.relative_to(ROOT).as_posix(),file_sha256=sha(path),
            record_sha256=rec['result_sha256'],native_payload_identity=rec['native_payload_identity'],upstream_reused=rec['upstream_reused']))
        print(json.dumps(dict(completed=index+1,total=len(specs),name=case['name'],new_counts={p:rec['final_counts'][p] for p in POLICIES})),flush=True)
        write_sealed(OUT/'progress.json',dict(complete=False,completed_inputs=index+1,planned_inputs=len(specs)))
    fresh={r['native_payload_identity'] for r in inventory if not r['upstream_reused']}
    previous=set(cfg['previous_native_payload_identities'])
    write_sealed(OUT/'result.json',dict(milestone='M43AE',complete=True,freeze_commit=freeze,
        case_evaluations_including_baseline=len(specs),historical_inputs=149,fresh_inputs=112,separate_baseline=1,
        upstream_audits_reused=150,new_input_detector_executions=112,upstream_replay_anchor_executions=3,
        paired_policy_endpoints_including_baseline=len(specs)*len(cfg['policies']),reused_policy_endpoints=1500,
        new_policy_endpoints=1906,inventory=inventory,endpoints=endpoints,baseline_counts=baseline_counts,
        baseline_complete_by_policy=baseline_complete,summary=summaries(endpoints,cfg['policies']),
        comparisons=comparisons(endpoints,baseline_counts,baseline_complete,not bool(fresh & previous)),
        distinct_native_payloads=len({r['native_payload_identity'] for r in inventory}),
        fresh_distinct_native_payloads=len(fresh),fresh_payload_overlap_with_prior=len(fresh & previous),
        new_null_rows=0,new_observing_sequences=0,general_adoption_qualified=False,astronomical_candidate_claimed=False,
        physical_false_alarm_probability_measured=False,wall_seconds=round(time.monotonic()-started,3)))
    write_sealed(OUT/'progress.json',dict(complete=True,completed_inputs=len(specs),planned_inputs=len(specs)))
    print('M43AE COMPLETE',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime-root',type=Path,required=True)
    p.add_argument('--freeze');p.add_argument('--preflight',action='store_true');a=p.parse_args()
    if not a.preflight and not a.freeze:p.error('--freeze is required for evaluation')
    run(a.runtime_root,a.freeze,a.preflight)
