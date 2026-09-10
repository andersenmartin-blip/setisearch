"""Prospective native validation of the separately published fixed M43AI OR model.

This runner owns new outputs only. It reuses the unchanged original native
pipeline, pre-confirmation acquisition and audits, with no old result rerun.
"""
import argparse
import copy
import importlib.metadata
import json
import platform
from pathlib import Path
import time

import m43ai_combined_rule as rule
import m43ah_epoch_support as ah

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43ai_native_validation'
CONFIG=ROOT/'config/m43ai_combined_rule.json'


def verified_config():
    cfg=json.loads(CONFIG.read_text())
    if platform.python_version()!=cfg['python_version']:
        raise ValueError('Frozen Python runtime differs')
    if {n:importlib.metadata.version(n) for n in cfg['dependencies']}!=cfg['dependencies']:
        raise ValueError('Frozen numerical dependencies differ')
    for p,h in cfg['native_dependency_sha256'].items():
        if rule.ag.sha((ROOT/p).read_bytes())!=h:
            raise ValueError('Frozen native dependency differs: '+p)
    return cfg


def public_protocol(cfg):
    files={p:rule.ag.sha((ROOT/p).read_bytes()) for p in cfg['protocol_files']}
    files['config/m43ai_combined_rule.json']=rule.ag.sha(CONFIG.read_bytes())
    return rule.verify_public_receipt(ROOT/'results_m43ai_preparation/public_freeze.json','protocol',files)


def verify_model_publication(model, receipt, config_sha256, protocol_commit):
    rule.verify_seal(model)
    rule.verify_seal(receipt)
    rule.validate_model(model)
    if (receipt.get('kind')!='model' or receipt.get('remote_verified') is not True
            or receipt.get('model_sha256')!=model['result_sha256']
            or not isinstance(receipt.get('commit'),str) or len(receipt['commit'])!=40
            or model.get('config_sha256')!=config_sha256
            or model.get('protocol_commit')!=protocol_commit
            or model.get('training_eligible') is not True):
        raise ValueError('A matching eligible public model must precede native evaluation')


def preflight(runtime):
    cfg=verified_config()
    import m43ae_joint_response as ae
    import m43af_response_study as af
    from seti_repeater.native_null_m43af import NativeShiftOverlay
    import numpy as np
    c=ae.context(runtime,json.loads(ae.CONFIG.read_text()))
    zero=NativeShiftOverlay(c.receiver,[0,0,0],c.bank,c.table,c.basis,c.grid)
    for key in c.baseline.expected_ids:
        if not np.array_equal(zero.baseline.get(*key)[0].view('<u4'),c.baseline.get(*key)[0].view('<u4')):
            raise ValueError('Zero translation differs from original anchors')
    z=copy.copy(c)
    z.receiver,z.overlay=zero.receiver,zero
    samples=af.native_samples(z,zero.baseline)
    row=rule.sealed(dict(passed=True,config_sha256=rule.ag.sha(CONFIG.read_bytes()),
        original_arrays_exact=96,original_native_gathers_exact=48,
        zero_translation_all_score_bits_exact=True,direct_native_checks=samples,
        original_calibration_binding=c.binding,new_validation_inputs_evaluated=0))
    rule.save(ROOT/'results_m43ai_preparation/runtime_preflight.json',row)
    print('M43AI NATIVE PREFLIGHT PASSED: 96 arrays, 48 gathers, 432 direct checks',flush=True)


def collect(c, spec, phase, cfg, model, protocol_commit):
    import numpy as np
    import m43ae_joint_response as ae
    from m43af_scalar_audit import audit_acquisition
    from seti_repeater.acquisition_m43af import acquire
    from seti_repeater.boundary_m43af import coordinates
    import m43af_response_study as af
    # Input creation and identity check precede detector execution. The unchanged
    # upstream routine reconstructs the same deterministic overlay for scoring.
    c.overlay.trial(spec['components'])
    payload_id=ae.payload_identity(c)
    if payload_id in set(cfg['excluded_native_payload_identities']):
        raise ValueError('Prospective native payload overlaps an earlier input')
    store,upstream,audits=ae.upstream(c,spec)
    if payload_id!=ae.payload_identity(c) or payload_id!=upstream['native_payload_identity']:
        raise ValueError('Native overlay changed during acquisition')
    geo=ae.geometry_audit(upstream)
    direct,seen=[],{}
    parts=ae.prior.native_parts(c.overlay,spec['components'])
    def check(kind,e,t,w,pos,score):
        key=(kind,e,t,w,pos)
        if key in seen:
            if seen[key]!=score:
                raise ValueError('Changed direct native score')
            return
        src=c.receiver.cache(f'epoch{e+1}_{kind}',1).source
        raw=ae.prior.raw_window_score(src,c.overlay.joint_indices[kind,e][t,:,pos],parts.get((kind,e),[]),w)
        if np.float32(raw['score']).view('<u4')!=np.float32(score).view('<u4'):
            raise ValueError('Independent native score differs')
        seen[key]=score
        direct.append(dict(kind=kind,epoch=e,template=t,width=w,support_index=pos,score=score,exact=True))
    evidence=acquire(geo,store,c.grid,c.on,c.off,None,check)
    scalar=audit_acquisition(geo,evidence,c.grid,c.on,c.off)
    if evidence['counts']['incomplete_profiles'] or evidence['counts']['undefined_member_measurements']:
        raise ValueError('Incomplete native profile evidence')
    endpoints=[]
    if phase=='ai_validation':
        endpoints=[ae.endpoint_row(c,spec,p,a,spec['name']+'.json',
                   upstream['additional_evidence_complete'] if p==ae.prior.POLICIES[-1] else True)
                   for p,a in audits.items()]
    associated=endpoints[0]['truth_association']['associated_record_ids'] if endpoints else []
    summary=dict(name=spec['name'],panel=phase,signal_present=spec['signal_present'],complete=True,
        members=[dict(record_id=m['record_id'],coordinate=coordinates(m)) for m in evidence['measurements']],
        associated_record_ids=associated,
        reference_recovered={p:next((r['recovered'] for r in endpoints if r['policy']==p),False) for p in rule.ag.REFERENCES})
    original={m['record_id']:m for m in geo['members']}
    feature_rows=[]
    profile_checks=0
    for member,measurement in zip(summary['members'],evidence['measurements'],strict=True):
        rid=member['record_id']
        if measurement['record_id']!=rid:
            raise ValueError('Measurement/member order differs')
        f=ah.member_features(original[rid],measurement)
        profile_checks+=ah.raw_profile_audit(original[rid],evidence['profiles'],f)
        feature_rows.append(dict(record_id=rid,original_m43af_coordinate=member['coordinate'],**f))
    outcome=rule.case_endpoint(summary,feature_rows,model)
    feature_case=dict(name=spec['name'],members=feature_rows)
    case_audit=rule.scalar_endpoint_audit([summary],[feature_case],model,[outcome])
    return rule.sealed(dict(spec=spec,phase=phase,protocol_commit=protocol_commit,
        config_sha256=rule.ag.sha(CONFIG.read_bytes()),model_sha256=model['result_sha256'],
        native_payload_identity=payload_id,upstream_evidence=upstream,
        geometry_member_audit=geo,acquisition=evidence,acquisition_scalar_audit=scalar,
        direct_native_checks=direct,null_direct_native_checks=af.native_samples(c,store) if phase=='ai_null_validation' else [],
        original_endpoints=endpoints,summary=summary,features=feature_rows,endpoint=outcome,
        independent_case_audit=case_audit,independent_profile_center_checks=profile_checks))


def verify_saved(record,spec,phase,model,protocol_commit,config_sha256):
    rule.verify_seal(record)
    if (record['spec']!=spec or record['phase']!=phase
            or record['model_sha256']!=model['result_sha256']
            or record['protocol_commit']!=protocol_commit
            or record['config_sha256']!=config_sha256):
        raise ValueError('Saved native checkpoint belongs to a different study')


def run(runtime):
    cfg=verified_config()
    protocol=public_protocol(cfg)
    model=rule.verify_seal(json.loads((ROOT/'results_m43ai_combined_rule/model.json').read_text()))
    publication=json.loads((ROOT/'results_m43ai_combined_rule/model_publication.json').read_text())
    config_sha256=rule.ag.sha(CONFIG.read_bytes())
    verify_model_publication(model,publication,config_sha256,protocol['commit'])
    pre=rule.verify_seal(json.loads((ROOT/'results_m43ai_preparation/runtime_preflight.json').read_text()))
    if pre['passed'] is not True or pre['config_sha256']!=config_sha256:
        raise ValueError('Matching original-native preflight required')
    if (OUT/'summary.json').exists():
        raise ValueError('Preserve completed native evaluation; do not rerun')
    import m43ae_joint_response as ae
    from seti_repeater.native_null_m43af import NativeShiftOverlay
    c=ae.context(runtime,json.loads(ae.CONFIG.read_text()))
    specs=[dict(name=f'ai_null_validation{i:03d}',panel='ai_null_validation',signal_present=False,
                components=[],shifts=shifts) for i,shifts in enumerate(cfg['native_null_shifts'])]
    specs+=cfg['validation_cases']
    inventory,outcomes=[],[]
    for i,spec in enumerate(specs):
        phase=spec['panel']
        path=OUT/'records'/(spec['name']+'.json')
        started=time.monotonic()
        reused=path.exists()
        if reused:
            r=json.loads(path.read_text())
            verify_saved(r,spec,phase,model,protocol['commit'],config_sha256)
        else:
            context=c
            if phase=='ai_null_validation':
                overlay=NativeShiftOverlay(c.receiver,spec['shifts'],c.bank,c.table,c.basis,c.grid)
                context=copy.copy(c)
                context.receiver,context.overlay,context.baseline=overlay.receiver,overlay,overlay.baseline
            r=collect(context,spec,phase,cfg,model,protocol['commit'])
            rule.save(path,r)
            if phase=='ai_null_validation':
                del context,overlay
        if r['native_payload_identity'] in cfg['excluded_native_payload_identities']:
            raise ValueError('Saved native input overlaps original evidence')
        outcomes.append(r['endpoint'])
        inventory.append(dict(name=spec['name'],phase=phase,path=str(path.relative_to(ROOT)),
            sha256=rule.ag.sha(path.read_bytes()),record_sha256=r['result_sha256'],
            native_payload_identity=r['native_payload_identity']))
        # Progress is operational and may advance; completed records are immutable.
        progress=dict(completed=i+1,planned=len(specs),last=spec['name'],model_sha256=model['result_sha256'])
        OUT.mkdir(exist_ok=True)
        (OUT/'progress.json').write_bytes(rule.ag.canonical(progress))
        print(json.dumps(dict(**progress,eligible=r['endpoint']['eligible_members'],
            survivors=len(r['endpoint']['accepted_record_ids']),recovered=r['endpoint']['recovered'],
            reused=reused,wall_seconds=round(time.monotonic()-started,3))),flush=True)
    injections=rule.summarize([r for r in outcomes if r['panel']=='ai_validation'])
    nulls=rule.summarize([r for r in outcomes if r['panel']=='ai_null_validation'])
    if (injections['case_count']!=112 or injections['signal_case_count']!=64
            or injections['non_signal_case_count']!=48 or nulls['case_count']!=128):
        raise ValueError('Prospective endpoint denominator differs')
    ids=[r['native_payload_identity'] for r in inventory]
    gates=dict(no_reference_signal_loss=not injections['required_signal_losses'],
        zero_control_members=not injections['leaking_non_signal_cases'],
        zero_false_control_associations=not injections['false_control_associations'],
        zero_native_null_members=not nulls['leaking_non_signal_cases'],
        complete_native_evidence=True,zero_prior_native_payload_overlap=True,
        fixed_public_model_before_evaluation=True)
    summary=dict(milestone='M43AI',phase='prospective_same_sequence_native_validation',complete=True,
        protocol_commit=protocol['commit'],model_publication_commit=publication['commit'],
        model_sha256=model['result_sha256'],injections=injections,native_nulls=nulls,gates=gates,
        prospective_same_sequence_gate_passed=all(gates.values()),
        distinct_native_payloads=len(set(ids)),within_panel_duplicate_payloads=len(ids)-len(set(ids)),
        full_upstream_native_executions=len(specs),previous_native_inputs_rerun=0,
        old_heldout_panels_opened=False,new_observing_sequences=0,detector_adopted=False,
        physical_false_alarm_probability_measured=False,astronomical_candidate_claimed=False)
    rule.save(OUT/'inventory.json',inventory)
    rule.save(OUT/'endpoints.json',outcomes)
    rule.save(OUT/'summary.json',summary)
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime-root',type=Path,required=True)
    p.add_argument('--preflight',action='store_true')
    a=p.parse_args()
    preflight(a.runtime_root) if a.preflight else run(a.runtime_root)
