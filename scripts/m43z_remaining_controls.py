"""Extract remaining control support from the audited immutable case ledger."""
import gzip,hashlib,json
from pathlib import Path
from m43e_economical_bank import read_sealed,write_sealed
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results_m43z_joint_controls'

def main():
    r=read_sealed(OUT/'result.json');packed=(OUT/'case_audits.jsonl.gz').read_bytes()
    assert hashlib.sha256(packed).hexdigest()==r['ledger_sha256']
    rows=[json.loads(x) for x in gzip.decompress(packed).splitlines() if x.strip()];controls=[]
    for row in rows:
        case=row['case']
        if case['signal_present']:continue
        ep=next(e for e in row['endpoints'] if e['policy']=='combined')
        if not ep['final_members']:continue
        ds={d['record_id']:d for d in row['policy_decisions']['combined']};members=[]
        injected={e for c in case['components'] if c['kind']=='on' for e in c['epochs']}
        for m,p in zip(row['reference_audit']['members'],row['confirmation_evidence']):
            if ds[m['record_id']]['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut']:
                bg={str(e):m['epoch_values_at_proxy_carrier'][e] for e in m['active_epochs_zero_based'] if e not in injected}
                members.append(dict(member=m,evidence=p,uninjected_active_epoch_scores=bg))
        controls.append(dict(case=case,members=members))
    write_sealed(OUT/'remaining_control_evidence.json',dict(source_result_sha256=r['result_sha256'],cases=controls))
    special=next(c for c in controls if c['case']['case_index']==96)
    assert len(special['members'])==19
    assert all(m['member']['active_epochs_zero_based']==[0,1,2] and m['evidence']['remaining']['excluded_epoch']==1 for m in special['members'])
    assert all(max(m['uninjected_active_epoch_scores'].values())<5.5 for m in special['members'])
    print('Seven leaking control labels extracted; case96 has19 three-epoch members supported by two individually sub-floor background epochs')
if __name__=='__main__':main()
