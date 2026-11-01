"""Two additional displays; read-only access to all previous analysis outputs."""
from pathlib import Path
import sys,json,csv,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path(__file__).resolve().parent
BASE=OUT.parents[1]
sys.path.insert(0,str(BASE/'v2/mapping_followup'))
from check_mapping import load,trace,highpass,MAPPING,OLD
PLAN=json.loads((OUT/'PLAN.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
guarded=[OLD/'NATIVE_MAPPING.json',OLD/'FOLLOWUP_DISPOSITIONS.csv',BASE/'v2/mapping_followup/MAPPING_FINDINGS.json',BASE/'v2/mapping_followup/MAPPING_FOLLOWUP_EVIDENCE.zip',BASE/'v2/mapping_followup/README.md']
before={str(p.relative_to(BASE)):sha(p) for p in guarded}
old_dispositions={r['review_id']:r for r in csv.DictReader((OLD/'FOLLOWUP_DISPOSITIONS.csv').open())}
raw,native,h,provenance=load(PLAN['dp_id'])
allhits=[r for r in MAPPING['orders'] if r['dp_id']==PLAN['dp_id']]
selected=[r for r in allhits if r['review_id'] in PLAN['review_ids']]
assert len(selected)==2
(OUT/'native').mkdir(exist_ok=True);(OUT/'figures').mkdir(exist_ok=True)
results=[]
fig,axes=plt.subplots(2,4,figsize=(17,7),constrained_layout=True)
for row,hit in enumerate(selected):
    o=hit['order'];k=hit['native_pixel'];regs=[]
    for a,b in PLAN['local_intervals_relative_to_native_pixel_half_open']:
        x=np.arange(max(0,k+a),min(4096,k+b));mask=np.ones(len(x),bool);excluded=[]
        for other in allhits:
            if other['order']==o:
                near=abs(x-other['native_pixel'])<=80
                if near.any():excluded.append(other['review_id'])
                mask&=~near
        assert sum(mask)>=100
        options=[]
        for argflip in [False,True]:
            tc=trace(h,o,x,argflip);cx=np.rint(tc).astype(int);yy=4095-x
            hp=highpass(np.stack([raw[yy,cx+j] for j in range(-3,4)]).sum(axis=0))
            ref=highpass(native[o,x])
            options.append({'argument_flip':argflip,'correlation':float(np.corrcoef(ref[mask],hp[mask])[0,1])})
        tc=trace(h,o,x,True);cx=np.rint(tc).astype(int);yy=4095-x
        profile=np.median(np.stack([raw[yy,cx+j][mask] for j in range(-5,6)]),axis=1)
        baseline=float(np.median(profile[[0,1,9,10]]));signal=profile-baseline
        peak=int(np.argmax(signal));offset=float(peak-5)
        if 0<peak<10:
            den=signal[peak-1]-2*signal[peak]+signal[peak+1]
            if den:offset+=float(.5*(signal[peak-1]-signal[peak+1])/den)
        offset+=float(np.median(cx[mask]-tc[mask]))
        regs.append({'pixel_interval_half_open':[int(x[0]),int(x[-1])+1],'samples':int(sum(mask)),
            'excluded_candidate_ids':excluded,'orientation_correlations':options,'continuum_profile':profile.tolist(),
            'continuum_offset_from_corrected_polynomial':offset})
    tc=float(trace(h,o,k,True));ic=round(tc);cy=4095-k
    cut=raw[cy-15:cy+16,ic-20:ic+21]
    bg=np.median(cut[np.r_[0:8,23:31]],axis=0);excess=cut-bg[None,:]
    with np.load(OLD/hit['cutout']) as original:
        wave=original['native_wave'];flux=original['native_flux']
    name=f'{hit["review_id"]}_o{o:02d}_corrected.npz'
    np.savez_compressed(OUT/'native'/name,raw_cutout=cut,raw_background=bg,raw_excess=excess,native_wave=wave,native_flux=flux)
    r={'review_id':hit['review_id'],'dp_id':hit['dp_id'],'order':o,'native_pixel':k,'raw_row':cy,
        'original_raw_column':hit['raw_column'],'corrected_raw_column':tc,'column_change':tc-hit['raw_column'],
        'original_followup_status_quoted_not_reassigned':old_dispositions[hit['review_id']]['followup_status'],
        'local_reference_regions':regs,'new_origin_status':'UNASSIGNED','cutout':'native/'+name}
    results.append(r)
    ax=axes[row];new=tc-ic;old=hit['raw_column']-ic
    ax[0].plot(wave,flux,'o-',ms=3,lw=1);ax[0].set_title(f"{hit['review_id']} order{o}: unchanged native")
    ax[0].set_xlabel('Native air wavelength [Angstrom]');ax[0].set_ylabel('Native flux')
    for j,data in [(1,cut),(2,np.maximum(excess,0))]:
        if j==1:vmin,vmax=np.percentile(data,[2,99.5]);title='Raw, corrected trace cyan'
        else:vmin=0;vmax=max(1,float(np.percentile(data[:,15:26],99.5)));title='Positive excess: central 11-column scale'
        ax[j].imshow(data,origin='lower',aspect='auto',extent=[-20.5,20.5,-15.5,15.5],vmin=vmin,vmax=vmax,cmap='magma')
        ax[j].axvline(new,color='cyan',lw=1,label='corrected');ax[j].axvline(old,color='lime',ls='--',lw=1,label='old')
        ax[j].set_xlabel('Raw column - corrected rounded trace');ax[j].set_ylabel('Raw row - candidate');ax[j].set_title(title)
    ax[1].legend(fontsize=8)
    ax[3].plot(np.arange(-20,21),bg,'o-',ms=3);ax[3].axvline(new,color='c');ax[3].axvline(old,color='g',ls='--')
    ax[3].set_xlabel('Raw column - corrected rounded trace');ax[3].set_ylabel('Outer-row median raw counts');ax[3].set_title('Continuum: candidate core excluded')
fig.suptitle('Additional December geometry check — previous dispositions unchanged; no new origin assignments',fontsize=14)
fig.savefig(OUT/'figures/ADDITIONAL_CORRECTED_MAPPING.png',dpi=170);plt.close(fig)
after={str(p.relative_to(BASE)):sha(p) for p in guarded}
assert before==after
record={'scope':PLAN['purpose'],'provenance':provenance,'fixed_orientation':PLAN['fixed_orientation'],
    'hits':results,'previous_outputs_unchanged':True,'guarded_sha256':after,
    'script_sha256':sha(Path(__file__)),'plan_sha256':sha(OUT/'PLAN.json')}
(OUT/'ADDITIONAL_CHECK.json').write_text(json.dumps(record,indent=2,allow_nan=False)+'\n')
for r in results:
    print(json.dumps({'review_id':r['review_id'],'column_change':r['column_change'],
        'local_continuum_offsets':[z['continuum_offset_from_corrected_polynomial'] for z in r['local_reference_regions']],
        'local_correlations':[[c['correlation'] for c in z['orientation_correlations']] for z in r['local_reference_regions']]}))
