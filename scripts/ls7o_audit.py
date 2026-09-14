#!/usr/bin/env python3
"""Independent LS7O rebuild: raw FITS, SciPy interpolation, QR/normal equations.

No imports from the LS7O producer, LS7O operator or LS7M PRF operator.
"""
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.interpolate import RegularGridInterpolator
from scipy.linalg import svd,lstsq
from scipy.stats import median_abs_deviation

from ls7l_review_inputs import image_hdus,verify_manifest
from ls7o_audit_inputs import audit_inputs,rebuild_motion

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results_ls7o_response'
DIFFERENCES={};CHECKS=0


def read(path):return json.loads(path.read_text())
def rows(path):return [json.loads(x) for x in gzip.decompress(path.read_bytes()).splitlines()]
def close(a,b,label,atol=1e-7,rtol=1e-8):
    global CHECKS
    if a is None or b is None:assert a is None and b is None,(label,a,b);return
    a,b=np.asarray(a),np.asarray(b)
    np.testing.assert_allclose(a,b,rtol=rtol,atol=atol,err_msg=label)
    DIFFERENCES[label]=max(DIFFERENCES.get(label,0),float(np.max(np.abs(a-b))))
    CHECKS+=a.size


def main():
    assert not (OUT/'audit.json').exists(),'refuse to overwrite a completed audit'
    cfg=read(ROOT/'config/ls7o_reference.json')
    for p,sha in cfg['input_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha,p
    inherited={p:verify_manifest(ROOT/p) for p in ['results_ls7k_inputs','results_ls7l_engineering','results_ls7l_inputs','results_ls7m_prf_inputs','results_ls7m_response','results_ls7j_auxiliary','results_ls7n_response','results_ls7o_metadata','results_ls7o_inputs']}
    native=rows(OUT/'native.jsonl.gz');pulses=rows(OUT/'pulses.jsonl.gz');summary=read(OUT/'summary.json')
    assert len(native)==len({r['case_id'] for r in native})==840
    assert len(pulses)==len({r['case_id'] for r in pulses})==12600
    by_id={r['case_id']:r for r in native};pulse_id={r['case_id']:r for r in pulses}
    windows=rows(ROOT/'results_ls7i_background/native_windows.jsonl.gz')
    baseline={r['fold_id']:r for r in read(ROOT/'results_ls7j_auxiliary/baselines.json')}
    raw={}
    for d in read(ROOT/'results_ls7i_inputs/datasets.json'):
        with np.load(ROOT/d['contexts'],allow_pickle=False) as z:raw[d['sector']]={k:z[k] for k in ['native','aperture']}
    references,designs,input_audit=audit_inputs()
    motion_rows=rows(OUT/'reference_motion.jsonl.gz');assert len(motion_rows)==420
    motion_by_id={r['window_id']:r for r in motion_rows};assert len(motion_by_id)==420
    old=read(ROOT/'results_ls7k_inputs/inventory.json');original=read(ROOT/'results_ls7m_prf_inputs/inventory.json')
    fits={(m['ccd'],m['grid_row'],m['grid_col']):image_hdus(ROOT/'results_ls7k_inputs'/m['path']) for m in old['prf_models']}
    yy,xx=np.indices((11,11));pixels=np.stack([xx,yy],axis=-1);support=xx>=1
    plane=np.array([np.ones((11,11)),(yy-5)/5,(xx-5)/5]).transpose(1,2,0)
    renderers={};nominal={}
    for s in [29,32]:
        geo=next(d for d in old['light_curves'] if d['sector']==s);ccd=geo['ccd'];nominal[s]=np.array(geo['geometry']['nominal_target_cutout_xy'])
        ys=sorted({y for c,y,x in fits if c==ccd});xs=sorted({x for c,y,x in fits if c==ccd})
        meta=next(m for m in original['models'] if m['ccd']==ccd)['field_descriptions']
        axes=(meta['prfRow']['values'],meta['prfColumn']['values'])
        for offset in [0,-44]:
            xy=np.array(geo['geometry']['nominal_target_detector_xy'])+[offset,0]
            interpolators=[]
            for k in [0,1]:
                bank=np.array([[fits[(ccd,y,x)][k] for x in xs] for y in ys])
                local=RegularGridInterpolator((ys,xs),bank)([xy[::-1]])[0]
                interpolators.append(RegularGridInterpolator(axes,local,bounds_error=False,fill_value=np.nan))
            renderers[(s,offset)]=interpolators

    def render(s,offset,displacement):
        d=pixels[None,:,:,:]-nominal[s]-np.asarray(displacement)[:,None,None,:]
        return [f(d[...,::-1]) for f in renderers[(s,offset)]]

    energies={};pulse_metrics={};max_side_leak=0.
    for wi,w in enumerate(windows):
        s,a,lo,hi=w['sector'],w['anchor'],w['start'],w['stop'];cube=raw[s]['native'][a];ap=raw[s]['aperture'];outside=support&~ap
        side=list(range(lo-60,lo-5))+list(range(hi+5,hi+60));event=list(range(lo,hi));selected=side+event
        ref=np.median(cube[side],axis=0)
        estimate=rebuild_motion(references[s],designs[s],a,side,selected)
        record=motion_by_id[w['window_id']]
        assert record['valid']==(estimate is not None)
        if estimate is None:
            bb=baseline[w['fold_id']]
            # Rebuild the unchanged static energy even if new inputs fail.
            dif=np.array([cube[t+1][ap].sum()-cube[t][ap].sum() for t in list(range(lo-60,lo-6))+list(range(hi+5,hi+59))])
            sig=float(median_abs_deviation(dif,scale='normal')/np.sqrt(2))
            residual=(cube[event].mean(0)-ref)[ap]/sig-bb['mean']
            inv=np.linalg.inv(bb['covariance']);one=np.ones(ap.sum());v=inv@one
            q=inv-np.outer(v,v)/(one@v);energy=float(residual@q@residual)
            for offset in [0,-44]:
                case=f"{w['window_id']}/offset{offset}";r=by_id[case]
                assert not r['reference_valid']
                close(energy,r['energies']['static'],'historical_static')
                energies[case]={'static':energy,'motion':None,'plane':None,'combined':None}
                assert all(r['energies'][k] is None for k in ['motion','plane','combined'])
                for si in range(5):
                    for variant in ['nominal','minus_entries','plus_entries']:
                        key=case+f'/pulse{si}/{variant}';assert pulse_id[key]['metrics'] is None;pulse_metrics[key]=None
            continue
        displacement=estimate['positions_xy'];zero=estimate['centers_xy']
        assert record['selected']==selected
        close(displacement[selected],record['positions_xy'],'reference_position',atol=1e-10,rtol=1e-9)
        close(estimate['formal_sigma_xy'][selected],record['formal_sigma_xy'],'reference_formal_sigma',atol=1e-10,rtol=1e-9)
        for key in ['centers_xy','sideband_median_error_xy','operators_xy','conditions_xy','reference_residual_mean_chi2_per_3_dof_xy']:
            close(estimate[key],record[key],'reference_'+key)

        adjacent=np.array([cube[i+1]-cube[i] for i in list(range(lo-60,lo-6))+list(range(hi+5,hi+59))])
        variance=(median_abs_deviation(adjacent,axis=0,scale='normal')/np.sqrt(2))**2
        floor=1e-6*np.median(variance[support&(variance>0)]);noise=np.sqrt(np.maximum(variance,floor))
        total_diff=np.array([cube[i+1][ap].sum()-cube[i][ap].sum() for i in list(range(lo-60,lo-6))+list(range(hi+5,hi+59))])
        sigma=float(median_abs_deviation(total_diff,scale='normal')/np.sqrt(2))
        # Each column is independently rendered at the fixed event shifts.
        protected=[]
        for offset in [0,-44]:
            for shift in cfg['protected_shifts_xy']:protected.append(render(s,offset,displacement[event]+shift)[0].mean(0))
        source=np.array([p[outside]/noise[outside] for p in protected]).T
        u,singular,_=svd(source,full_matrices=False,lapack_driver='gesvd');rank=int(np.sum(singular>1e-10*singular[0]))
        projector=np.eye(source.shape[0])-u[:,:rank]@u[:,:rank].T
        z=projector@(plane[outside]/noise[outside,None])
        zs=svd(z,compute_uv=False,lapack_driver='gesvd');prank=int(np.sum(zs>1e-10*zs[0]));condition=float(zs[0]/zs[-1])
        valid=prank==3 and condition<=1e8
        op=lstsq(z,np.eye(len(z)),cond=1e-10,lapack_driver='gelsy')[0]/noise[outside][None,:] if valid else None
        delta=cube[event].mean(0)-ref;bb=baseline[w['fold_id']];residual=delta[ap]/sigma-bb['mean']
        weight=np.linalg.solve(np.array(bb['covariance']),np.eye(ap.sum()));one=np.ones(ap.sum());wo=weight@one
        q=weight-np.outer(wo,wo)/(one@wo)
        for offset in [0,-44]:
            case=f"{w['window_id']}/offset{offset}";r=by_id[case]
            assert all(r[k]==w[k] for k in ['window_id','sector','anchor','start','stop','fold_id'])
            close(zero,r['position_reference_xy'],'position_reference');close(sigma,r['sigma'],'sigma');close(floor,r['variance_floor'],'variance_floor')
            p,e=render(s,offset,displacement[selected]);pmed=np.median(p[:len(side)],axis=0);pmean=p[len(side):].mean(0)
            x=np.column_stack([pmed[support],plane[support]])/noise[support,None];target=ref[support]/noise[support]
            singular=svd(x,compute_uv=False,lapack_driver='gesvd');frank=int(np.sum(singular>1e-10*singular[0]));fcondition=float(singular[0]/singular[-1])
            beta=np.linalg.solve(x.T@x,x.T@target) if frank==4 else lstsq(x,target,cond=1e-10)[0]
            fvalid=bool(frank==4 and fcondition<=1e8 and beta[0]>0)
            assert fvalid==r['source_fit']['valid'] and frank==r['source_fit']['rank']
            assert valid==r['plane_valid'] and rank==r['protected_rank'] and prank==r['plane_rank']
            close(beta,r['source_fit']['beta'],'source_beta');close(fcondition,r['source_fit']['condition'],'source_condition')
            close(condition,r['plane_condition'],'plane_condition')
            motion=beta[0]*(pmean-pmed) if fvalid else None
            envelope=beta[0]*(e[len(side):].mean(0)+e[:len(side)].max(0)) if fvalid else None
            close(None if envelope is None else envelope[ap],r['uncertainty_entry_envelope_aperture'],'uncertainty_entries')
            pred={'static':np.zeros((11,11)),'motion':motion,'plane':None if not valid else plane@(op@delta[outside]),
                  'combined':None if not valid or not fvalid else motion+plane@(op@(delta-motion)[outside])}
            energies[case]={}
            for method,correction in pred.items():
                energy=None if correction is None else float((residual-correction[ap]/sigma)@q@(residual-correction[ap]/sigma))
                energies[case][method]=energy;close(energy,r['energies'][method],'energy')
                if method=='static':close(energy,w['energies']['static'],'historical_static');continue
                close(None if correction is None else correction[ap],r['correction_aperture'][method],'correction')
                if correction is not None:
                    v=correction[ap]/sigma;close(float(v@q@v),r['accounting'][method]['correction_energy'],'correction_energy')
                    close(float(residual@q@v),r['accounting'][method]['alignment'],'alignment')
            for si,shift in enumerate(cfg['injected_shifts_xy']):
                p,e=render(s,offset,displacement[event]+shift);p,e=p.mean(0),e.mean(0)
                for name,profile in [('nominal',p),('minus_entries',np.maximum(p-e,0)),('plus_entries',p+e)]:
                    key=case+f'/pulse{si}/{name}';record=pulse_id[key]
                    assert (record['window_id'],record['sector'],record['column_offset'],record['shift_index'],record['variant'])==(w['window_id'],s,offset,si,name)
                    metric=None
                    if fvalid and valid:
                        signal=profile[ap];transfer=signal-plane[ap]@(op@profile[outside])
                        metric={'gain':float(signal@transfer/(signal@signal)),
                                'relative_distortion':float(np.sqrt(np.sum((transfer-signal)**2)/np.sum(signal**2)))}
                    assert (metric is None)==(record['metrics'] is None)
                    if metric is not None:
                        for k in metric:close(metric[k],record['metrics'][k],'pulse_'+k,atol=1e-8,rtol=0)
                    pulse_metrics[key]=metric
        if (wi+1)%70==0:print(f'Independent windows: {wi+1}/420',flush=True)
    joint=True
    for cell in summary['cells']:
        subset=[r for r in native if (r['sector'],r['column_offset'])==(cell['sector'],cell['column_offset'])]
        for method,saved in cell['methods'].items():
            available=[r for r in subset if energies[r['case_id']][method] is not None]
            total=sum(energies[r['case_id']][method] for r in available);static=sum(energies[r['case_id']]['static'] for r in available)
            ratio=total/static if static>0 else None
            close(total,saved['energy'],'aggregate');close(static,saved['static_energy'],'aggregate');close(ratio,saved['ratio'],'ratio')
            ratios=[]
            for a,bg in enumerate(saved['backgrounds']):
                rr=[r for r in available if r['anchor']==a];base=sum(energies[r['case_id']]['static'] for r in rr)
                rat=sum(energies[r['case_id']][method] for r in rr)/base if base>0 else None
                ratios.append(rat);close(rat,bg['ratio'],'background_ratio');assert len(rr)==bg['windows']
            gates={'all_210_available':len(available)==210,'aggregate_not_increased':ratio is not None and ratio<=1,
                   'six_backgrounds_improve':sum(r is not None and r<1 for r in ratios)>=6,
                   'no_background_doubled':all(r is not None and r<=2 for r in ratios)}
            assert gates==saved['gates'] and all(gates.values())==saved['pass'] and saved['windows']==len(available)
        passed=cell['methods']['combined']['pass']
        for variant,saved in cell['protection'].items():
            pp=[r for r in pulses if r['sector']==cell['sector'] and r['column_offset']==cell['column_offset'] and r['variant']==variant]
            mm=[pulse_metrics[r['case_id']] for r in pp];valid=[m for m in mm if m is not None];limit=.01 if variant=='nominal' else .05
            failed=sum(m is None or m['relative_distortion']>limit for m in mm)
            assert len(pp)==saved['cases']==1050 and len(valid)==saved['available'] and failed==saved['failed_cases']
            close(max((m['relative_distortion'] for m in valid),default=None),saved['maximum_distortion'],'maximum_distortion',atol=1e-8,rtol=0)
            close([min(m['gain'] for m in valid),max(m['gain'] for m in valid)] if valid else None,saved['gain_range'] if valid else None,'gain_range',atol=1e-8,rtol=0)
            passed=passed and failed==0
        assert passed==cell['pass'];joint=joint and passed
    assert summary['reference_windows_available']==sum(r['valid'] for r in motion_rows)
    assert joint==summary['joint_feasibility_pass'] and summary['native_windows']==420 and summary['model_window_rows']==840 and summary['pulse_response_rows']==12600
    audit={'status':'PASS','native_windows':420,'model_window_rows':840,'pulse_response_rows':12600,
           'input_audit':input_audit,'reference_windows_available':sum(r['valid'] for r in motion_rows),
           'numeric_comparisons':CHECKS,'maximum_absolute_differences':DIFFERENCES,'preserved_manifest_entries':inherited,
           'independent_joint_feasibility_pass':joint,'method':'independent raw struct reference rows + normal affine equations + raw FITS/SciPy PRF + normal source equations + independent SVD/QR plane + scalar quadratic energies'}
    (OUT/'audit.json').write_text(json.dumps(audit,indent=2,allow_nan=False)+'\n');print(json.dumps(audit,indent=2),flush=True)


if __name__=='__main__':main()
