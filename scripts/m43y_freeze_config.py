"""Freeze selected X failures and predeclared counterpart probes; no Y scoring."""
import gzip,json
from m43y_response_diagnostic import ROOT,CONFIG,sha
from m43v_component_diagnostic import coordinate

def main():
    x=json.loads((ROOT/'config/m43x_confirmation.json').read_text())
    selected=[13,45,47,79,109,111];probes={};historical={}
    with gzip.open(ROOT/'results_m43x_confirmation/case_audits.jsonl.gz','rt') as f:
        for line in f:
            if line.strip():
                r=json.loads(line)
                if r['case']['case_index'] in selected:historical[r['case']['case_index']]=r
    bycase={}
    for i in selected:
        r=historical[i];decisions={d['record_id']:d for d in r['policy_decisions']['remaining_aggregate']}
        members=[m for m in r['reference_audit']['members'] if decisions[m['record_id']]['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut']]
        bycase[str(i)]=[m['record_id'] for m in members]
        for m in members:probes[coordinate(m)]={k:m[k] for k in ('template_index','proxy_carrier_index','spectral_width_channels','active_epochs_zero_based')}
    for i in (47,79,111):
        c=x['cases'][i];p=dict(template_index=c['local_template'],proxy_carrier_index=c['score_index'],spectral_width_channels=1,active_epochs_zero_based=c['active_epochs'])
        probes[coordinate(p)]=p
    inputs=[dict(name='baseline',variant='baseline',case_index=None,components=[])]
    for i in selected:
        c=x['cases'][i]
        for variant in (('original','on-only','off-only') if c['case_type']=='ON-OFF' else ('original',)):
            parts=c['components'] if variant=='original' else [p for p in c['components'] if p['kind']==variant.split('-')[0]]
            inputs.append(dict(name=f'case{i:03d}.{variant}',variant=variant,case_index=i,components=parts))
    assert len(inputs)==13
    paths=set(x['pinned_sha256'])|{'config/m43x_confirmation.json','results_m43x_confirmation/case_audits.jsonl.gz',
        'results_m43x_confirmation/calibration.json','results_m43x_confirmation/baseline.json',
        'results_m43x_confirmation/artifact_validation.json','scripts/m43v_component_diagnostic.py',
        'scripts/m43y_response_diagnostic.py','scripts/m43y_audit_report.py','scripts/m43y_freeze_config.py',
        'tests/test_m43y_response_diagnostic.py','results_m43y_response_diagnostic/unit_tests.txt',
        'MILESTONE_43Y_RESPONSE_DIAGNOSTIC_PLAN.md'}
    cfg=dict(milestone='M43Y',m43x_scientific_freeze='0d4406c5a6a7106f49a71d809fc7c79731ccc238',
        retrospective=True,selected_cases=selected,historical_surviving_record_ids=bycase,
        inputs=inputs,probes=[probes[k] for k in sorted(probes)],
        pinned_sha256={p:sha(ROOT/p) for p in sorted(paths)})
    CONFIG.write_text(json.dumps(cfg,indent=2)+'\n')
    print(json.dumps(dict(inputs=len(inputs),probes=len(probes),historical_members=sum(map(len,bycase.values())),pins=len(paths))))
if __name__=='__main__':main()
