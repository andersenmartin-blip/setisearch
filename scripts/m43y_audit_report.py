"""Validate sealed Y evidence and paired component invariants without detector reruns."""
import gzip,json
import numpy as np
from m43y_response_diagnostic import ROOT,OUT,CONFIG,sha
from m43e_economical_bank import read_sealed,write_sealed
from seti_repeater.detector_m43u import digest

def audit():
    cfg=json.loads(CONFIG.read_text());result=read_sealed(OUT/'result.json')
    for p,h in cfg['pinned_sha256'].items():assert sha(ROOT/p)==h,p
    anchors=read_sealed(OUT/'anchors.json')
    assert all(anchors[k] for k in ('all_96_arrays_exact','all_48_native_gathers_exact','m43x_calibration_replay_exact'))
    packed=(OUT/'case_audits.jsonl.gz').read_bytes();raw=gzip.decompress(packed)
    import hashlib
    assert hashlib.sha256(packed).hexdigest()==result['ledger_sha256']
    assert hashlib.sha256(raw).hexdigest()==result['ledger_uncompressed_sha256']
    rows=[json.loads(line) for line in raw.splitlines() if line];assert len(rows)==13
    checks=0;lookup={}
    for row,spec in zip(rows,cfg['inputs']):
        assert row['result_sha256']==digest({k:v for k,v in row.items() if k!='result_sha256'})
        assert row['config_sha256']==sha(CONFIG) and row['freeze_commit']==result['freeze_commit'] and row['spec']==spec
        lookup[spec['name']]=row
        assert len(row['trace'])==len(cfg['probes'])
        for p,trace in zip(cfg['probes'],row['trace']):
            assert trace['coordinate']==[p['template_index'],p['proxy_carrier_index'],p['spectral_width_channels'],p['active_epochs_zero_based']]
            for r in trace['responses']:
                a=np.asarray(r['values'],dtype='<f4');w=r['width'];q=p['proxy_carrier_index']
                assert a.shape==(3,w) and r['first_proxy_index']==q-w//2 and r['last_proxy_index']==q+w//2
                assert a[:,w//2].tolist()==r['center'] and a.max(axis=1).tolist()==r['maximum']
                assert (q-w//2+a.argmax(axis=1)).tolist()==r['first_maximum_proxy_index']
                assert np.asarray(r['mask']).shape==(3,w)
                for e,d in enumerate(r['direct_native']):
                    assert d['score']==r['center'][e]
                    total=np.float32(0)
                    for value in d['filtered_row_values']:total+=np.float32(value)
                    total/=np.float32(np.sqrt(len(d['filtered_row_values'])))
                    assert float(total)==d['score'];checks+=1
        for policy,decisions in row['policy_decisions'].items():
            rank={m['record_id']:m['meets_diagnostic_rank_cut'] for m in row['reference_audit']['members']}
            assert row['final_counts'][policy]==sum(d['passes_evaluated_physical_vetoes'] and rank[d['record_id']] for d in decisions)
    assert checks==result['direct_native_scalar_comparisons']
    def values(row,kind):return [[r for r in t['responses'] if r['kind']==kind] for t in row['trace']]
    for i in (47,79,111):
        both,on,off=(lookup[f'case{i:03d}.{v}'] for v in ('original','on-only','off-only'))
        assert values(both,'on')==values(on,'on') and values(both,'off')==values(off,'off')
        assert values(on,'off')==values(lookup['baseline'],'off')
        assert values(off,'on')==values(lookup['baseline'],'on')
    groups={}
    for r in rows:groups.setdefault(digest(r['reference_audit']['overlay']['patch_payloads']),[]).append(r['spec']['name'])
    assert groups==result['patch_identity_groups'] and len(groups)==result['distinct_native_patch_inventories']
    record=dict(passed=True,sealed_inputs=13,pinned_files=len(cfg['pinned_sha256']),direct_native_comparisons=checks,
        component_response_invariants=12,ledger_sha256=result['ledger_sha256'],independent_physical_validation=False)
    write_sealed(OUT/'artifact_validation.json',record);print(json.dumps(record,indent=2))
if __name__=='__main__':audit()
