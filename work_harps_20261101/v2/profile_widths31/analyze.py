"""Descriptive variable-width fits; original detector and catalogs untouched."""
from pathlib import Path
import csv,json,hashlib,datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent;V2=OUT.parent
PLAN=json.loads((OUT/'PLAN.json').read_text())
source=V2/'triage_batch02/CUMULATIVE_DISPOSITIONS.csv'
assert hashlib.sha256(source.read_bytes()).hexdigest()==PLAN['input_table_sha256']
hits=[r for r in csv.DictReader(source.open()) if r['review_id'] in PLAN['review_ids']]
maps={n:json.loads((V2/n/'NATIVE_MAPPING.json').read_text()) for n in ['triage_batch01','triage_batch02']}
ratios=np.geomspace(.4,10,121);shifts=np.linspace(-1,1,41)
allrows=[];curves={};provenance=[]
for hit in hits:
    key=hit['source_batch'];ms=[m for m in maps[key]['orders'] if m['review_id']==hit['review_id']]
    curves[hit['review_id']]=[]
    for m in ms:
        if m['status']!='EXTRACTED':continue
        path=V2/key/m['cutout'];data=np.load(path);wave=data['native_wave'];flux=data['native_flux']
        assert wave.shape==flux.shape==(41,) and np.all(np.isfinite(flux))
        center=m['topocentric_air_angstrom'];ref=center/115000
        x=(wave-center)/ref;B=np.column_stack([np.ones(41),x]);pinv=np.linalg.pinv(B)
        side=np.r_[0:8,33:41];sidecoef=np.linalg.lstsq(B[side],flux[side],rcond=None)[0]
        jointres=flux-B@(pinv@flux);sideres=flux-B@sidecoef
        fits={}
        for method,res in [('joint_linear',jointres),('fixed_side_linear',sideres)]:
            best=None;fixed=None
            for ratio in np.r_[ratios,1.]:
                g=np.exp(-.5*((x[:,None]-shifts[None,:])/(ratio/2.354820045))**2)
                q=g-B@(pinv@g) if method=='joint_linear' else g
                norm=np.sum(q*q,axis=0);amp=np.maximum(0,np.sum(q*res[:,None],axis=0)/norm)
                sse=np.sum((res[:,None]-q*amp[None,:])**2,axis=0);j=int(np.argmin(sse))
                coef=pinv@(flux-amp[j]*g[:,j]) if method=='joint_linear' else sidecoef
                z=dict(width_ratio=float(ratio),fwhm_angstrom=float(ratio*ref),center_shift_reference_fwhm=float(shifts[j]),
                       amplitude_native_units=float(amp[j]),sse=float(sse[j]),background_intercept=float(coef[0]),
                       background_slope_per_reference_fwhm=float(coef[1]),width_grid_boundary=bool(ratio==ratios[0] or ratio==ratios[-1]),center_grid_boundary=bool(j in [0,len(shifts)-1]))
                if ratio==1.:fixed=z
                elif best is None or z['sse']<best['sse']:best=z
            # Fixed ratio1 is a legitimate member of the expanded free model.
            if fixed['sse']<best['sse']:best=fixed.copy()
            assert best['sse']<=fixed['sse']*(1+1e-12)
            fits[method]=dict(free=best,fixed_reference_width=fixed)
            allrows.append(dict(review_id=hit['review_id'],target=hit['canonical_target'],order=m['order'],
                method=method,reference_fwhm_angstrom=ref,**best,rmse_ratio_to_fixed=float(np.sqrt(best['sse']/fixed['sse'])) if fixed['sse'] else None,
                source_path=str(path.relative_to(V2))))
        curves[hit['review_id']].append(dict(order=m['order'],wave_offset=(wave-center).tolist(),flux=flux.tolist(),fits=fits,ref=ref))
        provenance.append(dict(path=str(path.relative_to(V2)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
with (OUT/'ORDER_WIDTHS.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(allrows[0]));w.writeheader();w.writerows(allrows)
events=[]
for h in hits:
    rs=[r for r in allrows if r['review_id']==h['review_id']];assert rs
    events.append(dict(review_id=h['review_id'],target=h['canonical_target'],complete_orders=len(rs)//2,
        minimum_width_ratio=min(r['width_ratio'] for r in rs),maximum_width_ratio=max(r['width_ratio'] for r in rs),
        all_complete_orders_both_methods_above_two=all(r['width_ratio']>2 for r in rs),
        any_width_boundary=any(r['width_grid_boundary'] for r in rs),any_center_boundary=any(r['center_grid_boundary'] for r in rs)))
summary=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),events=len(events),complete_orders=len(allrows)//2,
    events_all_orders_both_methods_width_ratio_above_two=sum(r['all_complete_orders_both_methods_above_two'] for r in events),
    events_with_any_width_boundary=sum(r['any_width_boundary'] for r in events),events_with_any_center_boundary=sum(r['any_center_boundary'] for r in events),
    interpretation=PLAN['limitations'],no_origin_or_original_status_changed=True,plan_sha256=hashlib.sha256((OUT/'PLAN.json').read_bytes()).hexdigest(),
    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),source_arrays=provenance)
(OUT/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');(OUT/'EVENT_WIDTHS.json').write_text(json.dumps(events,indent=2)+'\n')
(OUT/'FIT_CURVES.json').write_text(json.dumps(curves)+'\n')
(OUT/'figures').mkdir(exist_ok=True)
for start in range(0,len(hits),8):
    fig,axs=plt.subplots(4,2,figsize=(12,12));fig.subplots_adjust(left=.075,right=.98,bottom=.055,top=.88,hspace=.47,wspace=.23)
    for ax,h in zip(axs.flat,hits[start:start+8]):
        for item in curves[h['review_id']]:
            wave=np.asarray(item['wave_offset']);flux=np.asarray(item['flux']);x=wave/item['ref'];best=item['fits']['joint_linear']['free'];fixed=item['fits']['joint_linear']['fixed_reference_width']
            bg=best['background_intercept']+x*best['background_slope_per_reference_fwhm'];scale=max(np.max(abs(flux-bg)),1)
            ax.plot(wave,(flux-bg)/scale,'.-',lw=.7,ms=2,label='o'+str(item['order'])+' data')
            for fit,style in [(best,'-'),(fixed,':')]:
                model=fit['amplitude_native_units']*np.exp(-.5*((x-fit['center_shift_reference_fwhm'])/(fit['width_ratio']/2.354820045))**2)
                model+=fit['background_intercept']+x*fit['background_slope_per_reference_fwhm']-bg
                ax.plot(wave,model/scale,style,lw=.8,label=('free ' if style=='-' else 'fixed ')+f"{fit['width_ratio']:.1f}×")
        ax.set_title(h['review_id']+' '+h['canonical_target'],fontsize=10);ax.set_xlabel('Native topocentric air offset (Å)',fontsize=8);ax.legend(fontsize=6,ncol=2);ax.tick_params(labelsize=7)
    for ax in list(axs.flat)[len(hits[start:start+8]):]:ax.set_visible(False)
    fig.suptitle('Descriptive native widths · all available complete orders\nJoint linear background: variable Gaussian width versus frozen λ/115000 reference\nPer-order residual normalization; unweighted fits, no statistical significance or origin veto',fontsize=12)
    fig.savefig(OUT/'figures'/f'WIDTHS_{start//8+1:02d}.png',dpi=110);plt.close(fig)
print(json.dumps({k:v for k,v in summary.items() if k!='source_arrays'},indent=2))
