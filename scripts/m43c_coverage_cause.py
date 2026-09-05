#!/usr/bin/env python3
"""Separate template-track mismatch from carrier-grid coverage failures."""
import json
import hashlib
from pathlib import Path
import numpy as np
from m43b_active_support import ROOT, ACTIVITY, active_plans, seal
from seti_repeater import search_v0p6 as core

GUARD_HZ=.001


def template_diagnostic(a, y, grid_hz, exact_count):
    a=np.asarray(a,dtype=np.longdouble);y=np.asarray(y,dtype=np.longdouble)
    if a.ndim!=1 or y.shape!=a.shape or not a.size or not np.isfinite(a).all() or not np.isfinite(y).all() or np.any(a<=0):
        raise ValueError('invalid positive-factor track')
    # Independent pairwise lower bound on uniform absolute residual.
    pair=(y[:,None]*a[None,:]-a[:,None]*y[None,:])/(a[:,None]+a[None,:])
    i,j=np.unravel_index(np.argmax(pair),pair.shape)
    minimum=max(np.longdouble(0),pair[i,j]);q=(y[i]+y[j])/(a[i]+a[j])
    actual=np.max(np.abs(a*q-y))
    if abs(actual-minimum)>GUARD_HZ:raise RuntimeError('minimax residual check failed')
    lower=np.max((y-20)/a);upper=np.min((y+20)/a)
    left=np.longdouble(grid_hz[0]);right=np.longdouble(grid_hz[-1])
    if exact_count:
        cause='supported'
    elif minimum>20+GUARD_HZ:
        cause='track-shape-incompatible'
    elif minimum>=20-GUARD_HZ:
        cause='numerical-boundary-unresolved'
    elif upper<left-GUARD_HZ or lower>right+GUARD_HZ:
        cause='outside-carrier-range'
    elif upper<left+GUARD_HZ or lower>right-GUARD_HZ:
        cause='numerical-boundary-unresolved'
    else:
        start=int(np.searchsorted(grid_hz,lower,side='left'))
        if start<len(grid_hz) and np.longdouble(grid_hz[start])<=upper:
            cause='numerical-boundary-unresolved'
        else:
            # A gap must be separated from both neighboring samples by the guard.
            before=lower-np.longdouble(grid_hz[start-1]) if start else np.inf
            after=np.longdouble(grid_hz[start])-upper if start<len(grid_hz) else np.inf
            cause='carrier-grid-gap' if min(before,after)>GUARD_HZ else 'numerical-boundary-unresolved'
    return {'cause':cause,'minimum_continuous_residual_hz':float(actual),
        'minimax_carrier_hz':float(q),'feasible_carrier_lower_hz':float(lower),
        'feasible_carrier_upper_hz':float(upper),'exact_candidate_cells':int(exact_count)}


def truth_cause(diagnostics):
    counts={c:sum(x['cause']==c for x in diagnostics) for c in ('supported','track-shape-incompatible','outside-carrier-range','carrier-grid-gap','numerical-boundary-unresolved')}
    for c in ('supported','numerical-boundary-unresolved','carrier-grid-gap','outside-carrier-range','track-shape-incompatible'):
        if counts[c]:return c,counts
    raise ValueError('empty template inventory')


def run():
    cfgpath=ROOT/'config/m43c_coverage_cause.json';cfg=json.loads(cfgpath.read_text());cfg_hash=hashlib.sha256(cfgpath.read_bytes()).hexdigest()
    for p,h in cfg['pinned_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise RuntimeError('changed frozen file: '+p)
    prior=json.loads((ROOT/'results_m43b_active_support/geometry.json').read_text())
    if prior['result_sha256']!=seal({k:v for k,v in prior.items() if k!='result_sha256'}):raise RuntimeError('M43B identity changed')
    metadata=json.loads((ROOT/'config/hd156668b_m37_preflight.json').read_text())
    basis=core.make_factor_basis_from_metadata(metadata)
    bank=json.loads((ROOT/'results_m37_v0p6_bank_preflight/bank_preflight.json').read_text())['template_bank']['records']
    table=core.make_template_factor_table(basis,bank,expected_template_bank_sha256=core.M37_BANK_SHA256)
    if table.factor_table_sha256!=prior['factor_table_sha256'] or basis.basis_sha256!=prior['factor_basis_sha256']:raise RuntimeError('factor ancestry differs')
    labels=('epoch1_on','epoch2_on','epoch3_on');matrices=tuple(core.factor_table_for_scan(table,basis,l) for l in labels)
    grid=core.make_m37_proxy_carrier_grid('m37_1412p5')
    out=ROOT/'results_m43c_coverage_cause';out.mkdir(exist_ok=True)
    local=out/'truths';local.mkdir(exist_ok=True);rows=[]
    for old in prior['rows']:
        t=old['truth'];ordinal=t['truth_ordinal'];path=local/f'{ordinal:03d}.json'
        if path.exists():
            row=json.loads(path.read_text())
            if row['config_sha256']!=cfg_hash or row['truth']!=t or row['checkpoint_sha256']!=seal({k:v for k,v in row.items() if k!='checkpoint_sha256'}):raise RuntimeError('checkpoint changed')
        else:
            factors=tuple(np.ascontiguousarray(core.template_factors_from_basis(basis,t,scan_label=l),dtype='<f8') for l in labels)
            active=tuple(t['active_epochs_zero_based']);plans=active_plans(grid,matrices,factors,t['proxy_carrier_hz'],active)
            count=sum(p.candidate_indices.indices.size for p in plans)
            if seal([p.as_record() for p in plans])!=old['active_plan_inventory_sha256'] or count!=old['active_candidate_cells']:raise RuntimeError('M43B replay differs')
            matrix=np.concatenate([matrices[i] for i in active],axis=1)
            y=t['proxy_carrier_hz']*np.concatenate([factors[i] for i in active])
            details=[template_diagnostic(a,y,grid.score_hz,p.candidate_indices.indices.size) for a,p in zip(matrix,plans,strict=True)]
            cause,counts=truth_cause(details)
            best=min(range(len(details)),key=lambda i:details[i]['minimum_continuous_residual_hz'])
            row={'config_sha256':cfg_hash,'truth':t,'cause':cause,'template_cause_counts':counts,
                'best_template_index':best,'best_continuous_fit':details[best],
                'template_diagnostics_sha256':seal(details),'m43b_plan_exact':True,
                'active_candidate_cells':int(count),'m43b_plan_sha256':old['active_plan_inventory_sha256']}
            row['checkpoint_sha256']=seal(row)
            temp=path.with_suffix('.tmp');temp.write_bytes(core.canonical_json_bytes(row));temp.replace(path)
        rows.append(row)
        if (ordinal+1)%64==0:print('classified',ordinal+1,'/512',flush=True)
    causes={c:sum(r['cause']==c for r in rows) for c in ('supported','track-shape-incompatible','outside-carrier-range','carrier-grid-gap','numerical-boundary-unresolved')}
    if len(rows)!=512 or causes['supported']!=167:raise RuntimeError('prior support changed')
    groups=[]
    for active in ACTIVITY:
        selected=[r for r in rows if tuple(r['truth']['active_epochs_zero_based'])==active]
        groups.append({'active_epochs':list(active),'truth_count':len(selected),'causes':{c:sum(r['cause']==c for r in selected) for c in causes}})
    quantiles={}
    for name,selected in [('all',rows),('unsupported',[r for r in rows if r['cause']!='supported'])]:
        quantiles[name]=dict(zip(('min','p25','median','p75','max'),map(float,np.percentile([r['best_continuous_fit']['minimum_continuous_residual_hz'] for r in selected],[0,25,50,75,100]))))
    r={'artifact_type':'m43c-coverage-cause-v1','status':'complete-geometric-diagnosis','config_sha256':cfg_hash,
        'parent_result_sha256':prior['result_sha256'],'counts':causes,'activity_groups':groups,
        'best_continuous_residual_quantiles_hz':quantiles,'longdouble_mantissa_bits':int(np.finfo(np.longdouble).nmant),
        'rows':rows,'new_spectral_reads':0,'new_injections':0,'bank_or_tolerance_changed':False,'sensitivity_claimed':False}
    r['result_sha256']=seal(r);(out/'diagnostic.json').write_bytes(core.canonical_json_bytes(r))
    print(json.dumps({k:v for k,v in r.items() if k not in ('rows','activity_groups')},indent=2),flush=True)


if __name__=='__main__':run()
