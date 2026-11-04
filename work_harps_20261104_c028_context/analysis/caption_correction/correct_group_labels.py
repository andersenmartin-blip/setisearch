#!/usr/bin/env python3
"""Correct only R021 to R029 in the two merged display titles; preserve originals."""
from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parents[1];OUT=HERE/'results'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_bytes())
def limits(series):
    a=np.concatenate([x[np.isfinite(x)]for x in series]);lo,hi=(float(a.min()),float(a.max()))if len(a)else(-1,1)
    margin=.05*(hi-lo)if hi>lo else max(.05,abs(lo)*.05)
    return lo-margin,hi+margin

def main():
    plan=load(HERE/'PLAN.json')
    if sha(HERE/'plot_group.py')!=plan['plot_script_sha256']:raise ValueError('Original plot method changed')
    hashes=load(OUT/'OUTPUT_HASHES.json')
    for f,h in hashes.items():
        if sha(OUT/f)!=h:raise ValueError('Numeric output changed')
    rows=load(OUT/'PROFILE_METRICS.json');profiles={}
    for r in rows:
        with np.load(OUT/r['profile_path'],allow_pickle=False)as z:profiles[r['source_id'],r['frame']]={k:np.array(z[k])for k in z.files}
    figs=Path(__file__).resolve().parent/'figures';figs.mkdir(exist_ok=False)
    epochs=plan['merged_dp_ids'];colors=plt.cm.viridis(np.linspace(.05,.9,6))
    markers=plan['event_markers']
    for width,label in [(3.,'BROAD'),(.25,'CORE')]:
        fig,axes=plt.subplots(2,2,figsize=(13,8),layout='constrained')
        for j,frame in enumerate(['barycentric','topocentric']):
            for i,(field,title)in enumerate([('signed_raw_flux','Signed merged flux [ADU]'),('normalized_flux','Flux / flank reference')]):
                for k,dp in enumerate(epochs):
                    r=next(r for r in rows if r['kind']=='merged'and r['dp_id']==dp and r['frame']==frame);a=profiles[r['source_id'],frame]
                    axes[i,j].plot(a['offset'],a[field],color=colors[k],lw=1,label=r['date_obs'][:10]+(' · discovery'if dp in plan['discovery_dp_ids']else'')+(' · low ref'if r.get('low_flank_reference')is True else''))

                for mark in markers:
                    offset=mark['barycentric_offset_angstrom']if frame=='barycentric'else mark['discovery_topocentric_offset_angstrom']
                    axes[i,j].axvline(offset,color=mark['color'],lw=.65,ls=':',alpha=.8)
                axes[i,j].set_xlim(-width,width);axes[i,j].set_title(frame+' · '+title,fontsize=10);axes[i,j].set_xlabel('Fixed-frame air-wavelength offset [Å]');axes[i,j].axhline(0,color='grey',lw=.5);axes[i,j].grid(alpha=.15)
        for i,field in enumerate(['signed_raw_flux','normalized_flux']):
            vals=[]
            for r in rows:
                if r['kind']=='merged':
                    a=profiles[r['source_id'],r['frame']];vals.append(a[field][np.abs(a['offset'])<=width])
            for ax in axes[i]:ax.set_ylim(*limits(vals))
        handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=4,fontsize=7.5)
        fig.suptitle('C028 · all six original-cohort HD126093 epochs · '+label.lower()+' context\nCenter 3864.5550000000003 Å / R029; marker: 0260 (red), discovery 2025-04-27.\nOne fixed April-2025 topocentric anchor; other features can leave its core. No origin assignment.',fontsize=11)
        fig.savefig(figs/('MERGED_'+label+'_CONTEXT.png'),dpi=140);plt.close(fig)
    from PIL import Image
    comparisons=[]
    for name in ['MERGED_CORE_CONTEXT.png','MERGED_BROAD_CONTEXT.png']:
        original=OUT/'figures'/name;corrected=figs/name
        with Image.open(original) as im:before=np.array(im)
        with Image.open(corrected) as im:after=np.array(im)
        if before.shape!=after.shape:raise ValueError('Caption correction changed image dimensions')
        changed=np.any(before!=after,axis=2);ys,xs=np.where(changed)
        if not len(ys) or int(ys.max())>=90:raise ValueError('Change is not confined to title band')
        comparisons.append({'original_path':str(original.relative_to(HERE)),'original_sha256':sha(original),'corrected_path':str(corrected.relative_to(HERE)),'corrected_sha256':sha(corrected),'dimensions':[before.shape[1],before.shape[0]],'changed_pixel_bbox':[int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1],'all_pixels_below_title_band_identical':bool(np.array_equal(before[90:],after[90:]))})
    for f,h in hashes.items():
        if sha(OUT/f)!=h:raise ValueError('Numerical output changed')
    report={'schema':'HARPS_C028_CAPTION_CORRECTION_V1','status':'PASS_LABEL_ONLY_CORRECTION','reason':'The published frozen plot code inherited R021 in the merged titles. The plan, event identity, numerical center and all calculated values correctly use C028/R029. Correct only displayed R021 to R029 in separate copies.','original_plot_script_sha256':sha(HERE/'plot_group.py'),'correction_script_sha256':sha(Path(__file__)),'numeric_outputs_unchanged':True,'original_figures_preserved':True,'new_scientific_masks_or_fits':False,'comparisons':comparisons}
    (Path(__file__).resolve().parent/'CORRECTION.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
