"""Describe completed M43X comparisons without changing any frozen decisions."""
import json
import gzip
from collections import Counter
from pathlib import Path
from m43e_economical_bank import read_sealed,write_sealed
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43x_confirmation'

def main():
    r=read_sealed(OUT/'result.json');validated=read_sealed(OUT/'artifact_validation.json')
    assert r['complete'] and validated['result_seal']==r['result_sha256']
    cfg=json.loads((ROOT/'config/m43x_confirmation.json').read_text())
    rows=r['endpoints'];assert len(rows)==768
    lookup={(e['case_index'],e['policy']):e for e in rows}
    comparisons=[];epoch_groups=[]
    for p in ('epoch_confirmation','remaining_aggregate'):
        for n in (2,3):
            cases=[c for c in cfg['cases'] if len(c['active_epochs'])==n]
            signal=[c for c in cases if c['signal_present']];controls=[c for c in cases if not c['signal_present']]
            ref=[lookup[c['case_index'],'neighbor9'] for c in signal]
            alt=[lookup[c['case_index'],p] for c in signal]
            epoch_groups.append(dict(policy=p,active_epoch_count=n,signal_cases=len(signal),control_cases=len(controls),
                reference_signal_associations=sum(e['truth_association']['recovered'] for e in ref),
                policy_signal_associations=sum(e['truth_association']['recovered'] for e in alt),
                reference_leaking_controls=sum(lookup[c['case_index'],'neighbor9']['final_members']>0 for c in controls),
                policy_leaking_controls=sum(lookup[c['case_index'],p]['final_members']>0 for c in controls)))
    for c in cfg['cases']:
        hard=lookup[c['case_index'],'epoch_confirmation'];agg=lookup[c['case_index'],'remaining_aggregate']
        if hard['final_members']!=agg['final_members'] or hard['truth_association']['recovered']!=agg['truth_association']['recovered']:
            comparisons.append(dict(case_index=c['case_index'],case_type=c['case_type'],strength=c['strength'],
                score_index=c['score_index'],local_template=c['local_template'],active_epochs=c['active_epochs'],
                injection_active_epoch_count=len(c['active_epochs']),signal_present=c['signal_present'],hard_associated=hard['truth_association']['recovered'],
                aggregate_associated=agg['truth_association']['recovered'],
                hard_members=hard['final_members'],aggregate_members=agg['final_members']))
    ledger=[json.loads(line) for line in gzip.decompress((OUT/'case_audits.jsonl.gz').read_bytes()).splitlines() if line.strip()]
    surviving_controls=[]
    for rec in ledger:
        if rec['case']['signal_present']:continue
        evidence={e['record_id']:e for e in rec['confirmation_evidence']}
        for p in ('epoch_confirmation','remaining_aggregate'):
            decisions={d['record_id']:d for d in rec['policy_decisions'][p]}
            members=[m for m in rec['reference_audit']['members'] if decisions[m['record_id']]['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut']]
            if not members:continue
            case={k:v for k,v in rec['case'].items() if k not in ('components','reference_truth')}
            surviving_controls.append(dict(case=case,policy=p,members=[dict(member=m,confirmation=evidence[m['record_id']]) for m in members]))
    write_sealed(OUT/'control_survivor_evidence.json',dict(source_result=r['result_sha256'],surviving_controls=surviving_controls,
        interpretation='Retrospective extraction of frozen decisions; no OFF samples reconstructed, threshold changed, or candidate promoted.'))
    paired=read_sealed(OUT/'matched_components.json')['pairs'];pair_states=[]
    for p in cfg['policies']:
        subset=[x for x in paired if x['policy']==p];assert len(subset)==64
        counts=Counter((x['signal_only_associated'],x['mixed_associated'],x['interferer_only_false_association']) for x in subset)
        pair_states.extend(dict(policy=p,signal_only_associated=k[0],mixed_associated=k[1],
            interferer_only_false_association=k[2],paired_comparisons=v) for k,v in sorted(counts.items()))
    result=write_sealed(OUT/'interpretation.json',dict(source_result=r['result_sha256'],
        epoch_groups=epoch_groups,aggregate_vs_hard_changed_cases=comparisons,matched_component_states=pair_states,
        aggregate_restored_signal_cases_vs_hard=[c['case_index'] for c in comparisons if c['signal_present'] and c['aggregate_associated'] and not c['hard_associated']],
        aggregate_added_leaking_controls_vs_hard=[c['case_index'] for c in comparisons if not c['signal_present'] and c['aggregate_members']>0 and c['hard_members']==0]))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
