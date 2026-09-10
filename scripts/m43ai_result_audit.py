"""Post-execution integrity and independent reporting audit; no new scoring."""
import argparse
import collections
import json
from pathlib import Path

import m43ai_combined_rule as rule
import m43ai_native_validation as native

ROOT=Path(__file__).resolve().parents[1]


def audit(root):
    out=root/'results_m43ai_native_validation'
    cfg=json.loads((root/'config/m43ai_combined_rule.json').read_text())
    model=rule.verify_seal(json.loads((root/'results_m43ai_combined_rule/model.json').read_text()))
    result=json.loads((out/'summary.json').read_text())
    ledger=json.loads((out/'inventory.json').read_text())
    endpoints=json.loads((out/'endpoints.json').read_text())
    specs=[dict(name=f'ai_null_validation{i:03d}',panel='ai_null_validation',signal_present=False,
                components=[],shifts=shifts) for i,shifts in enumerate(cfg['native_null_shifts'])]+cfg['validation_cases']
    if len(ledger)!=240 or [r['name'] for r in ledger]!=[s['name'] for s in specs]:
        raise ValueError('Incomplete planned native inventory')
    if len(endpoints)!=240:
        raise ValueError('Incomplete published endpoint inventory')
    reconstructed=[]
    direct_checks=profile_checks=members=0
    payload_names=collections.defaultdict(list)
    class_rows=collections.defaultdict(list)
    for entry,spec,endpoint in zip(ledger,specs,endpoints,strict=True):
        path=(root/entry['path']).resolve()
        if not path.is_relative_to((out/'records').resolve()):
            raise ValueError('Record path outside current native study')
        if rule.ag.sha(path.read_bytes())!=entry['sha256']:
            raise ValueError('Native record bytes changed')
        r=json.loads(path.read_text())
        native.verify_saved(r,spec,spec['panel'],model,model['protocol_commit'],model['config_sha256'])
        if r['result_sha256']!=entry['record_sha256'] or r['native_payload_identity']!=entry['native_payload_identity']:
            raise ValueError('Native identity ledger differs')
        if r['native_payload_identity'] in cfg['excluded_native_payload_identities']:
            raise ValueError('Prior native input reused')
        if r['endpoint']!=endpoint or r['summary']['signal_present']!=spec['signal_present']:
            raise ValueError('Record/endpoint/label differs')
        # Reference recovery comes directly from the original upstream endpoint
        # records, rather than trusting the new combined endpoint's copy.
        for ref in rule.ag.REFERENCES:
            truth=next((x['recovered'] for x in r['original_endpoints'] if x['policy']==ref),False)
            if r['summary']['reference_recovered'][ref]!=truth or endpoint['reference_recovered'][ref]!=truth:
                raise ValueError('Reference recovery differs from upstream record')
        original={m['record_id']:m for m in r['geometry_member_audit']['members']}
        eligible={rid for rid,m in original.items() if m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut']}
        if eligible!={m['record_id'] for m in r['features']}:
            raise ValueError('Missing eligible native member')
        if (r['acquisition']['counts']['incomplete_profiles'] or r['acquisition']['counts']['undefined_member_measurements']):
            raise ValueError('Incomplete acquired evidence')
        for f in r['features']:
            profile_checks+=rule.ah.raw_profile_audit(original[f['record_id']],r['acquisition']['profiles'],f)
        fresh=rule.case_endpoint(r['summary'],r['features'],model)
        if fresh!=endpoint:
            raise ValueError('Reconstructed endpoint differs')
        rule.scalar_endpoint_audit([r['summary']],[dict(name=spec['name'],members=r['features'])],model,[fresh])
        members+=endpoint['eligible_members']
        direct_checks+=len(r['direct_native_checks'])+len(r['null_direct_native_checks'])
        if spec['panel']=='ai_null_validation' and len(r['null_direct_native_checks'])!=432:
            raise ValueError('Native null sample audit is incomplete')
        payload_names[r['native_payload_identity']].append(spec['name'])
        class_rows[spec.get('case_type','native_null')].append(fresh)
        reconstructed.append(fresh)
    for phase,key in [('ai_validation','injections'),('ai_null_validation','native_nulls')]:
        if rule.summarize([r for r in reconstructed if r['panel']==phase])!=result[key]:
            raise ValueError('Reported headline counts differ')
    if result['distinct_native_payloads']!=len(payload_names) or result['within_panel_duplicate_payloads']!=240-len(payload_names):
        raise ValueError('Native independence denominator differs')
    signal_result=result['injections']
    null_result=result['native_nulls']
    expected_gates=dict(no_reference_signal_loss=not signal_result['required_signal_losses'],
        zero_control_members=not signal_result['leaking_non_signal_cases'],
        zero_false_control_associations=not signal_result['false_control_associations'],
        zero_native_null_members=not null_result['leaking_non_signal_cases'],
        complete_native_evidence=True,zero_prior_native_payload_overlap=True,
        fixed_public_model_before_evaluation=True)
    if result['gates']!=expected_gates:
        raise ValueError('Reported gates differ from independently reduced evidence')
    if result['prospective_same_sequence_gate_passed']!=all(expected_gates.values()):
        raise ValueError('Reported gate result differs')
    return dict(passed=True,verified_records=240,verified_eligible_members=members,
        original_profile_center_rechecks=profile_checks,recorded_direct_native_checks=direct_checks,
        summary_recomputed_from_complete_records=True,original_reference_endpoints_checked=True,
        payload_duplicate_groups=[dict(native_payload_identity=k,cases=v) for k,v in sorted(payload_names.items()) if len(v)>1],
        by_case_type={k:rule.summarize(v) for k,v in sorted(class_rows.items())},
        full_native_detector_reruns=0,new_native_inputs_evaluated=0)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT)
    a=p.parse_args()
    result=audit(a.root.resolve())
    rule.save(a.root/'results_m43ai_native_validation/final_audit.json',result)
    print(json.dumps(result,indent=2))
