"""Build the explicitly retrospective panel from sealed M43Z records."""
import gzip
import json
from pathlib import Path
from m43aa_native_response import ROOT, CONFIG, sha
from m43v_component_diagnostic import coordinate

def main():
    z=json.loads((ROOT/'config/m43z_joint_controls.json').read_text())
    groups={'off324':[324,42,43,44,48], 'off336':[336,162,163,164,168],
            'off346':[346,262,263,264,268], 'agg171':[171,170,176],
            'agg260':[260,261,265,266], 'agg281':[281,280,286], 'residual':[6,16,96]}
    selected=sorted({i for ids in groups.values() for i in ids}); history={}
    with gzip.open(ROOT/'results_m43z_joint_controls/case_audits.jsonl.gz','rt') as f:
        for line in f:
            if line.strip():
                r=json.loads(line)
                if r['case']['case_index'] in selected: history[r['case']['case_index']]=r
    probes={}; inputs=[]
    keys=('template_index','proxy_carrier_index','spectral_width_channels','active_epochs_zero_based')
    for group,ids in groups.items():
        inventory={}
        for i in ids:
            case=z['cases'][i]; rec=history[i]
            associated=set(rec['endpoints'][0]['truth_association']['associated_record_ids']) if case['signal_present'] else set()
            combined={d['record_id'] for d in rec['policy_decisions']['combined'] if d['passes_evaluated_physical_vetoes']}
            for m in rec['reference_audit']['members']:
                if m['record_id'] in associated or (group=='residual' and m['record_id'] in combined and m['meets_diagnostic_rank_cut']):
                    p={k:m[k] for k in keys}; inventory[coordinate(p)]=p
            for w in (1,3,5,9,17,33,65,129):
                p=dict(template_index=case['local_template'],proxy_carrier_index=case['score_index'],
                       spectral_width_channels=w,active_epochs_zero_based=case['active_epochs'])
                inventory[coordinate(p)]=p
            inputs.append(dict(name=f'case{i:03d}',case_index=i,group=group,variant='historical',components=case['components']))
        probes[group]=[inventory[k] for k in sorted(inventory)]
        if group.startswith('off'):
            i=ids[0]
            inputs.append(dict(name=f'case{i:03d}.off-only',case_index=i,group=group,variant='component',
                               components=[c for c in z['cases'][i]['components'] if c['kind']=='off']))
    union={coordinate(p):p for ps in probes.values() for p in ps}
    probes['baseline']=[union[k] for k in sorted(union)]
    inputs.append(dict(name='baseline',case_index=None,group='baseline',variant='baseline',components=[]))
    pinpaths=['scripts/m43aa_native_response.py','scripts/m43aa_freeze_config.py','tests/test_m43aa_native_response.py',
              'MILESTONE_43AA_NATIVE_RESPONSE_PLAN.md','config/m43z_joint_controls.json',
              'scripts/m43z_joint_controls.py','scripts/m43v_component_diagnostic.py','scripts/m43s_profile_sensitivity.py',
              'results_m43z_joint_controls/result.json','results_m43z_joint_controls/calibration.json',
              'results_m43z_joint_controls/baseline.json','results_m43z_joint_controls/case_audits.jsonl.gz']
    cfg=dict(milestone='M43AA',retrospective=True,m43z_execution_freeze='ac2337057670b40438bcbc3ff4c59ec2ed47626b',
             historical_cases=selected,groups=groups,inputs=inputs,probes=probes,response_radius_bins=160,
             pinned_sha256={p:sha(ROOT/p) for p in pinpaths})
    CONFIG.write_text(json.dumps(cfg,indent=2)+'\n')
    print('Inputs:',len(inputs),'historical:',len(selected),'probes:',{g:len(p) for g,p in probes.items()})

if __name__=='__main__':main()
