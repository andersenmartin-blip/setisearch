"""Follow fixed LOCAL_PLAN; retain old failed checks and add new evidence only."""
from pathlib import Path
import json,itertools,gc
import numpy as np
from scipy.ndimage import median_filter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from check_mapping import OUT,BASE,OLD,PLAN,MAPPING,load,trace,sha,highpass,number

LOCAL=json.loads((OUT/'LOCAL_PLAN.json').read_text())
(OUT/'native').mkdir(exist_ok=True)
(OUT/'figures').mkdir(exist_ok=True)

def correlation(a,b,mask):return number(np.corrcoef(a[mask],b[mask])[0,1])
def mad(x):return float(1.4826*np.median(abs(x-np.median(x))))
def profile_position(raw,h,o,x,mask):
    tc=trace(h,o,x,True); cx=np.rint(tc).astype(int);yy=4095-x
    profile=np.median(np.stack([raw[yy,cx+j][mask] for j in range(-5,6)]),axis=1)
    j=int(np.argmax(profile));off=float(j-5)
    if 0<j<len(profile)-1:
        den=profile[j-1]-2*profile[j]+profile[j+1]
        if den!=0:off+=float(.5*(profile[j-1]-profile[j+1])/den)
    return dict(profile=profile.tolist(),peak_offset_from_rounded_polynomial=off,
        median_rounding_correction=float(np.median(cx[mask]-tc[mask])),
        peak_offset_from_polynomial=off+float(np.median(cx[mask]-tc[mask])))

records=[];plots=[]
for dp in PLAN['dp_ids']:
    raw,native,h,provenance=load(dp)
    allhits=[r for r in MAPPING['orders'] if r['dp_id']==dp]
    original_ref=[]
    x=np.arange(1000,1400);ref=highpass(native[50,x])
    for argflip in [False,True]:
        cx=np.rint(trace(h,50,x,argflip)).astype(int);yy=4095-x
        val=np.stack([raw[yy,cx+j] for j in range(-3,4)]).sum(axis=0)
        hp=highpass(val)
        mask=(abs(ref-np.median(ref))<=8*mad(ref))&(abs(hp-np.median(hp))<=8*mad(hp))
        original_ref.append(dict(argument_flip=argflip,original_pearson=correlation(ref,hp,np.ones(len(x),bool)),
            diagnostic_8mad_pearson=correlation(ref,hp,mask),remaining_samples=int(mask.sum()),
            native_highpass_mad=mad(ref),raw_highpass_mad=mad(hp),
            excluded_pixels=[dict(native_pixel=int(k),native_highpass=float(a),raw_highpass=float(b)) for k,a,b,keep in zip(x,ref,hp,mask) if not keep]))
    infos=[]
    for hit in allhits:
        if hit['review_id'] not in PLAN['review_ids']:continue
        o=hit['order'];k=hit['native_pixel'];local=[]
        for a,b in LOCAL['local_reference_intervals_relative_to_native_candidate']:
            xx=np.arange(max(0,k+a),min(4096,k+b));mask=np.ones(len(xx),bool)
            excluded=[]
            for r in allhits:
                if r['order']==o:
                    near=abs(xx-r['native_pixel'])<=80
                    if near.any():excluded.append(r['review_id'])
                    mask&=~near
            cs=[]
            for argflip in [False,True]:
                cx=np.rint(trace(h,o,xx,argflip)).astype(int);yy=4095-xx
                vals=np.stack([raw[yy,cx+j] for j in range(-3,4)]).sum(axis=0)
                cs.append(dict(argument_flip=argflip,correlation=correlation(highpass(native[o,xx]),highpass(vals),mask)))
            local.append(dict(pixel_interval_half_open=[int(xx[0]),int(xx[-1])+1],samples=int(mask.sum()),excluded_candidate_ids=excluded,
                correlations=cs,continuum_profile=profile_position(raw,h,o,xx,mask)))
        tc=float(trace(h,o,k,True));ic=round(tc);cy=4095-k
        cut=raw[cy-15:cy+16,ic-20:ic+21]
        background=np.median(cut[np.r_[0:8,23:31]],axis=0);excess=cut-background[None,:]
        filename=f'{hit["review_id"]}_o{o:02d}_corrected.npz'
        with np.load(OLD/hit['cutout']) as oldnp:
            wave=oldnp['native_wave'];flux=oldnp['native_flux']
        np.savez_compressed(OUT/'native'/filename,raw_cutout=cut,raw_background=background,raw_excess=excess,native_wave=wave,native_flux=flux)
        info=dict(review_id=hit['review_id'],dp_id=dp,order=o,native_pixel=k,raw_row=cy,
            original_raw_column=hit['raw_column'],revised_raw_column=tc,column_difference_from_original=tc-hit['raw_column'],
            local_reference_regions=local,corrected_cutout='native/'+filename,
            status='MAPPING_SUPPORTED_BY_REFERENCE_GRID_AND_LOCAL_CONTINUUM',origin_status='UNASSIGNED')
        infos.append(info);plots.append((info,cut,background,excess,wave,flux))
    records.append(dict(dp_id=dp,provenance=provenance,original_reference_diagnostic=original_ref,hits=infos))
    del raw,native;gc.collect()

fig,axes=plt.subplots(len(plots),4,figsize=(17,3.1*len(plots)),constrained_layout=True)
for row,(r,cut,bg,excess,wave,flux) in enumerate(plots):
    ax=axes[row];ic=round(r['revised_raw_column']);new=r['revised_raw_column']-ic;old=r['original_raw_column']-ic
    ax[0].plot(wave,flux,'o-',ms=2,lw=.8);ax[0].set_title(f"{r['review_id']} order {r['order']}: unchanged native")
    ax[0].set_xlabel('Native air wavelength [Angstrom]');ax[0].set_ylabel('Native flux')
    for j,data in [(1,cut),(2,np.maximum(excess,0))]:
        if j==1:vmin,vmax=np.percentile(data,[2,99.5]);title='Raw: stellar trace at cyan'
        else:vmin=0;vmax=max(1,float(np.percentile(data[:,15:26],99.5)));title='Positive excess (central 11 cols scale)'
        ax[j].imshow(data,origin='lower',aspect='auto',extent=[-20.5,20.5,-15.5,15.5],vmin=vmin,vmax=vmax,cmap='magma')
        ax[j].axvline(new,color='cyan',lw=.8,label='grid-supported');ax[j].axvline(old,color='lime',ls='--',lw=.8,label='original')
        ax[j].set_xlabel('Raw column - new rounded trace');ax[j].set_ylabel('Raw row - candidate row');ax[j].set_title(title)
    ax[1].legend(fontsize=7)
    ax[3].plot(np.arange(-20,21),bg,'o-',ms=2)
    ax[3].axvline(new,color='c',label='new trace');ax[3].axvline(old,color='g',ls='--',label='old trace')
    ax[3].set_xlabel('Raw column - new rounded trace');ax[3].set_ylabel('Median background/continuum');ax[3].set_title('Candidate core excluded: outer raw rows')
fig.suptitle('Six mapping follow-ups — geometry evidence only; no origin assignments',fontsize=15)
fig.savefig(OUT/'figures/CORRECTED_MAPPING.png',dpi=150);plt.close(fig)
result=dict(script_sha256=sha(Path(__file__)),plan_sha256=sha(OUT/'LOCAL_PLAN.json'),records=records,
    status_note='New mapping evidence only. Original failed correlations and tables remain unchanged. Candidate morphology is not used to choose mapping or assign origin.')
(OUT/'LOCAL_CHECK.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
for r in records:
    print(json.dumps(dict(dp_id=r['dp_id'],original_reference_diagnostic=r['original_reference_diagnostic'],hits=[dict(review_id=z['review_id'],column_difference=z['column_difference_from_original'],local=[dict(correlations=y['correlations'],continuum_peak_offset=y['continuum_profile']['peak_offset_from_polynomial']) for y in z['local_reference_regions']]) for z in r['hits']])),flush=True)
