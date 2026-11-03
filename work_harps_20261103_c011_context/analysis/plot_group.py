#!/usr/bin/env python3
"""Plot every fixed C011 merged/native/preserved-raw context without refitting."""
from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent;OUT=HERE/'results'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_bytes())
def limits(series):
    a=np.concatenate([x[np.isfinite(x)]for x in series]);lo,hi=(float(a.min()),float(a.max()))if len(a)else(-1,1)
    margin=.05*(hi-lo)if hi>lo else max(.05,abs(lo)*.05)
    return lo-margin,hi+margin

def main():
    plan=load(HERE/'PLAN.json')
    if sha(Path(__file__))!=plan['plot_script_sha256']:raise ValueError('Plot method changed')
    hashes=load(OUT/'OUTPUT_HASHES.json')
    for f,h in hashes.items():
        if sha(OUT/f)!=h:raise ValueError('Numeric output changed')
    rows=load(OUT/'PROFILE_METRICS.json');profiles={}
    for r in rows:
        with np.load(OUT/r['profile_path'],allow_pickle=False)as z:profiles[r['source_id'],r['frame']]={k:np.array(z[k])for k in z.files}
    figs=OUT/'figures';figs.mkdir(exist_ok=False)
    epochs=plan['merged_dp_ids'];colors=plt.cm.viridis(np.linspace(.05,.9,7))
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
        fig.suptitle('C011 · all seven original-cohort HD112410 epochs · '+label.lower()+' context\nCenter 3865.6775 Å / R012; marker: 0089 (red), discovery 2025-05-28.\nOne fixed May-2025 topocentric anchor; other features can leave its core. No origin assignment.',fontsize=11)
        fig.savefig(figs/('MERGED_'+label+'_CONTEXT.png'),dpi=140);plt.close(fig)
    native=[r for r in rows if r['kind']=='native'and r['frame']=='barycentric']
    assert len(native)==2
    for page in range(1):
        subset=native[4*page:4*page+4];fig,axes=plt.subplots(len(subset),4,figsize=(17,3*len(subset)),layout='constrained',squeeze=False)
        for i,initial in enumerate(subset):
            for j,frame in enumerate(['barycentric','topocentric']):
                r=next(r for r in rows if r['source_id']==initial['source_id']and r['frame']==frame);a=profiles[r['source_id'],frame]
                merged=next(q for q in rows if q['kind']=='merged'and q['dp_id']==initial['dp_id']and q['frame']==frame);b=profiles[merged['source_id'],frame]
                ax=axes[i,j];ax.plot(a['offset'],a['signed_raw_flux'],color='#28774b',lw=1);ax.axhline(0,color='grey',lw=.6);ax.set_title(f"{initial['date_obs'][:10]} · order {initial['order']} · {frame}",fontsize=8);ax.set_ylabel('Native extracted flux\n(unit unspecified)',fontsize=8)
                ax=axes[i,j+2];ax.plot(b['offset'],b['normalized_flux'],color='#333333',lw=.9,label='same-epoch merged');ax.plot(a['offset'],a['normalized_flux'],color='#28774b',lw=1,label='native order');ax.set_title('Flank-scaled · '+frame,fontsize=8);ax.set_ylabel('Flux / own flank reference',fontsize=8)
                if r['normalization_status']!='USABLE_POSITIVE_FLANK_REFERENCE':ax.text(.03,.95,'Native RAW-ONLY\n'+'\n'.join(r['normalization_reasons']),transform=ax.transAxes,va='top',fontsize=6.5)
                elif r.get('low_flank_reference')is True:ax.text(.03,.95,'LOW FLANK REFERENCE',transform=ax.transAxes,va='top',fontsize=6.5)
            rawseries=[profiles[initial['source_id'],f]['signed_raw_flux']for f in ['barycentric','topocentric']]
            for ax in axes[i,:2]:ax.set_ylim(*limits(rawseries))
            for ax in axes[i]:ax.set_xlim(-3,3);ax.set_xlabel('Fixed-frame offset [Å]',fontsize=8);ax.grid(alpha=.15)
        axes[0,2].legend(fontsize=7)
        fig.suptitle(f'C011 · discovery covering orders 2 and 3 · page {page+1}/1\n0089: 2025-05-28. Signed values and fixed-flank outcomes retained; shared extraction.',fontsize=12)
        fig.savefig(figs/f'NATIVE_ORDERS_{page+1}.png',dpi=140);plt.close(fig)
    evidence=load(OUT/'PRESERVED_RAW_CONTEXT.json');assert len(evidence)==2
    for page in range(1):
        subset=evidence[4*page:4*page+4];fig,axes=plt.subplots(len(subset),2,figsize=(11,3*len(subset)),layout='constrained',squeeze=False)
        for i,item in enumerate(subset):
            with np.load(OUT/item['copied_path'],allow_pickle=False)as z:
                for j,key in enumerate(['raw_cutout','raw_excess']):
                    a=np.array(z[key]);ax=axes[i,j];m=max(float(np.max(np.abs(a))),1.)
                    im=ax.imshow(a,origin='lower',interpolation='nearest',aspect='auto',cmap='RdBu_r'if j else'viridis',vmin=-m if j else float(np.min(a)),vmax=m if j else float(np.max(a)))
                    ax.set_title(f"{item['event']} · order {item['order']} · stored {key}",fontsize=9);ax.set_xlabel('Saved cutout column index');ax.set_ylabel('Saved cutout row index');fig.colorbar(im,ax=ax,shrink=.8)
        fig.suptitle(f'C011 · preserved 0089 raw-order context · page {page+1}/1\nBoth orders retain true at all four historical mapping stages. Separate full scales; no new mapping or subtraction.',fontsize=11)
        fig.savefig(figs/f'PRESERVED_RAW_ORDER_CONTEXT_{page+1}.png',dpi=140);plt.close(fig)
    for f,h in hashes.items():
        if sha(OUT/f)!=h:raise ValueError('Numeric output changed during plotting')
    index={'all18_profile_slots_retained':True,'both_event_raw_order_contexts_retained':True,'distinct_discovery_products':1,'metadata_excluded_native_orders':0,'plot_script_sha256':sha(Path(__file__)),'figure_scale_rules':'Merged: same y limits across both frames per quantity/window, all finite values plus 5 percent. Native raw: shared limits across frames per order; normalized panels use own positive flank divisors, or preserve raw-only reasons. Preserved raw panels have separate scales and all saved pixels. Native/raw pages follow fixed input order.','files':[{'path':str(p.relative_to(OUT)),'sha256':sha(p),'bytes':p.stat().st_size}for p in sorted(figs.glob('*.png'))],'numeric_outputs_unchanged':True,'origin_assignments':0}
    (OUT/'PLOT_INDEX.json').write_text(json.dumps(index,indent=2)+'\n');print(json.dumps(index,indent=2))
if __name__=='__main__':main()
