#!/usr/bin/env python3
"""Checkpointed, metadata-only comparison of fixed all/active-epoch support."""
import hashlib
import json
from pathlib import Path
import numpy as np
from seti_repeater import search_v0p6 as core
from seti_repeater.truth_local_v0p6 import plan_truth_local_template_scores_interval
import m42_m41_support_mask_diagnostic as m42
import m41_m37_high_snr_truth_local_calibration as m41

ROOT=Path(__file__).resolve().parents[1]
ACTIVITY=((0,1),(0,2),(1,2),(0,1,2))


def seal(x):return hashlib.sha256(core.canonical_json_bytes(x)).hexdigest()


def active_plans(grid, matrices, truths, carrier, active):
    if not isinstance(active,tuple) or active not in ACTIVITY or any(type(x) is not int for x in active):
        raise ValueError('activity must be an ordered canonical epoch tuple')
    if len(matrices)!=3 or len(truths)!=3:
        raise ValueError('exactly three labelled epoch arrays required')
    count=None
    for m,t in zip(matrices,truths,strict=True):
        if (not isinstance(m,np.ndarray) or not isinstance(t,np.ndarray)
            or m.ndim!=2 or t.ndim!=1 or m.shape[1]!=t.size or t.size<1
            or m.dtype!=np.dtype('<f8') or t.dtype!=np.dtype('<f8')
            or not m.flags.c_contiguous or not t.flags.c_contiguous
            or not np.isfinite(m).all() or not np.isfinite(t).all()
            or np.any(m<=0) or np.any(t<=0)):
            raise ValueError('invalid epoch factor geometry')
        if count is not None and m.shape[0]!=count:raise ValueError('template inventory differs')
        count=m.shape[0]
    matrix=np.ascontiguousarray(np.concatenate([matrices[i] for i in active],axis=1),dtype='<f8')
    truth=np.ascontiguousarray(np.concatenate([truths[i] for i in active]),dtype='<f8')
    return plan_truth_local_template_scores_interval(grid,matrix,carrier,truth,tolerance_hz=20.)


def run():
    cfg_path=ROOT/'config/m43b_active_support.json';cfg=json.loads(cfg_path.read_text());cfg_hash=hashlib.sha256(cfg_path.read_bytes()).hexdigest()
    for p,h in cfg['pinned_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise RuntimeError('changed input: '+p)
    metadata=json.loads((ROOT/'config/hd156668b_m37_preflight.json').read_text())
    basis=core.make_factor_basis_from_metadata(metadata)
    bank=json.loads((ROOT/'results_m37_v0p6_bank_preflight/bank_preflight.json').read_text())['template_bank']['records']
    table=core.make_template_factor_table(basis,bank,expected_template_bank_sha256=core.M37_BANK_SHA256)
    if table.factor_table_sha256!=cfg['expected_factor_table_sha256']:raise RuntimeError('historical factor table differs')
    labels=('epoch1_on','epoch2_on','epoch3_on')
    matrices=tuple(core.factor_table_for_scan(table,basis,label) for label in labels)
    grid=core.make_m37_proxy_carrier_grid('m37_1412p5')
    _,ledger,_=m42.load_validated_records(ROOT,m42.load_json(ROOT/'config/m42_m41_support_mask_diagnostic.json'))
    old={r['truth']['truth_ordinal']:r for r in ledger if r['trial']['level_index']==0}
    truths=m41.make_plan().truths
    out=ROOT/'results_m43b_active_support';out.mkdir(exist_ok=True)
    checkpoints=out/'truths';checkpoints.mkdir(exist_ok=True)
    rows=[]
    for truth in truths:
        record=truth.as_record();ordinal=truth.truth_ordinal
        if record!=old[ordinal]['truth']:raise RuntimeError('M41 truth mismatch')
        path=checkpoints/f'{ordinal:03d}.json'
        if path.exists():
            row=json.loads(path.read_text())
            if row['config_sha256']!=cfg_hash or row['truth']!=record or row['checkpoint_sha256']!=seal({k:v for k,v in row.items() if k!='checkpoint_sha256'}):raise RuntimeError('checkpoint changed')
        else:
            factors=tuple(np.ascontiguousarray(core.template_factors_from_basis(basis,{'coefficient_x':truth.coefficient_x,'coefficient_y':truth.coefficient_y},scan_label=label),dtype='<f8') for label in labels)
            legacy=active_plans(grid,matrices,factors,truth.proxy_carrier_hz,(0,1,2))
            legacy_hash=seal([p.as_record() for p in legacy]);legacy_count=sum(p.candidate_indices.indices.size for p in legacy)
            if legacy_hash!=old[ordinal]['adapter']['plan_inventory_sha256'] or legacy_count*32!=old[ordinal]['adapter']['candidate_score_cell_count']:raise RuntimeError('legacy M41 plan mismatch')
            active=active_plans(grid,matrices,factors,truth.proxy_carrier_hz,truth.active_epochs_zero_based)
            for a,b in zip(legacy,active,strict=True):
                if not np.isin(a.candidate_indices.indices,b.candidate_indices.indices).all():raise RuntimeError('support lost')
            active_hash=seal([p.as_record() for p in active]);active_count=sum(p.candidate_indices.indices.size for p in active)
            if truth.active_epochs_zero_based==(0,1,2) and active_hash!=legacy_hash:raise RuntimeError('all-active identity differs')
            category='legacy-supported' if legacy_count else ('newly-supported' if active_count else 'unsupported')
            row={'config_sha256':cfg_hash,'truth':record,'legacy_candidate_cells':int(legacy_count),'active_candidate_cells':int(active_count),'legacy_plan_inventory_sha256':legacy_hash,'active_plan_inventory_sha256':active_hash,'legacy_m41_plan_exact':True,'legacy_cells_subset_of_active':True,'category':category}
            row['checkpoint_sha256']=seal(row)
            temp=path.with_suffix('.tmp');temp.write_bytes(core.canonical_json_bytes(row));temp.replace(path)
        rows.append(row)
        if (ordinal+1)%64==0:print('checkpoint',ordinal+1,'/512',flush=True)
    counts={c:sum(r['category']==c for r in rows) for c in ('legacy-supported','newly-supported','unsupported')}
    if counts['legacy-supported']!=98 or len(rows)!=512:raise RuntimeError('legacy inventory count changed')
    groups=[];anchors=[]
    for act in ACTIVITY:
        for width in (1,3,5,9,17,33,65,129):
            group=[r for r in rows if tuple(r['truth']['active_epochs_zero_based'])==act and r['truth']['spectral_width_channels']==width]
            groups.append({'active_epochs':list(act),'width':width,'truth_count':len(group),'legacy_supported':sum(r['legacy_candidate_cells']>0 for r in group),'active_supported':sum(r['active_candidate_cells']>0 for r in group)})
            if width in (1,129):
                for category in counts:
                    candidates=[r for r in group if r['category']==category]
                    anchors.append({'active_epochs':list(act),'width':width,'category':category,'truth_ordinal':min(r['truth']['truth_ordinal'] for r in candidates) if candidates else None})
    result={'artifact_type':'m43b-active-epoch-geometric-association-v1','status':'geometry-complete-score-and-real-anchor-qualification-pending','config_sha256':cfg_hash,'factor_basis_sha256':basis.basis_sha256,'factor_table_sha256':table.factor_table_sha256,'truth_count':512,'counts':counts,'legacy_supported':98,'active_supported':512-counts['unsupported'],'groups':groups,'future_anchor_inventory':anchors,'rows':rows,'new_spectral_reads':0,'new_injections':0,'recovery_measured':False,'sensitivity_claimed':False,'production_detector_changed':False}
    result['result_sha256']=seal(result);(out/'geometry.json').write_bytes(core.canonical_json_bytes(result))
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','groups','future_anchor_inventory')},indent=2),flush=True)


if __name__=='__main__':run()
