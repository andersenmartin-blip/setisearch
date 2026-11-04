#!/usr/bin/env python3
"""Plot every fixed C029 merged/native/preserved-raw context without refitting."""
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
    epochs=plan['merged_dp_ids'];colors=plt.cm.viridis(np.linspace(.05,.9,6))
    markers=plan['event_markers'];discovery_events={dp:[e for e,d in plan['events'].items() if d==dp] for dp in plan['discovery_dp_ids']}
    for width,label in [(3.,'BROAD'),(.25,'CORE')]:
        fig,axes=plt.subplots(2,2,figsize=(13,9.5),layout='constrained')
        for j,frame in enumerate(['barycentric','topocentric']):
            for i,(field,title)in enumerate([('signed_raw_flux','Signed merged flux [ADU]'),('normalized_flux','Flux / flank reference')]):
                for k,dp in enumerate(epochs):
                    r=next(r for r in rows if r['kind']=='merged'and r['dp_id']==dp and r['frame']==frame);a=profiles[r['source_id'],frame]
                    axes[i,j].plot(a['offset'],a[field],color=colors[k],lw=1,label=r['date_obs'][:10]+(' · '+','.join(e.replace('V2E2-','') for e in discovery_events[dp])+' discovery'if dp in discovery_events else'')+(' · low ref'if r.get('low_flank_reference')is True else''))

                for mark in markers:
                    offset=mark['barycentric_offset_angstrom']if frame=='barycentric'else mark['discovery_topocentric_offset_angstrom']
                    axes[i,j].axvline(offset,color=mark['color'],lw=.65,ls=':',alpha=.8,label=mark['event'].replace('V2E2-','')+' catalog/discovery marker')
                axes[i,j].set_xlim(-width,width);axes[i,j].set_title(frame+' · '+title,fontsize=10);axes[i,j].set_xlabel('Fixed-frame air-wavelength offset [Å]');axes[i,j].axhline(0,color='grey',lw=.5);axes[i,j].grid(alpha=.15)
        for i,field in enumerate(['signed_raw_flux','normalized_flux']):
            vals=[]
            for r in rows:
                if r['kind']=='merged':
                    a=profiles[r['source_id'],r['frame']];vals.append(a[field][np.abs(a['offset'])<=width])
            for ax in axes[i]:ax.set_ylim(*limits(vals))
        handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=4,fontsize=7.5)
        fig.suptitle('C029 · all six original-cohort HD126093 epochs · '+label.lower()+' context\nExact shared catalog center 3866.125 Å / R030; all three original cores are identical.\nAll three exact member/discovery markers retained; coincident barycentric markers keep separate identities. No origin assignment.',fontsize=10)
        fig.savefig(figs/('MERGED_'+label+'_CONTEXT.png'),dpi=140);plt.close(fig)
    native=[r for r in rows if r['kind']=='native'and r['frame']=='barycentric']
    assert len(native)==6;native_pages=(len(native)+3)//4
    assert native_pages==plan['plot_pagination']['native_pages']
    for page in range(native_pages):
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
        fig.suptitle(f'C029 · all three discovery/products × orders 2 and 3 · page {page+1}/{native_pages}\nFixed input order; signed values and every missing, low or invalid flank outcome retained. Shared same-exposure extraction.',fontsize=11)
        fig.savefig(figs/f'NATIVE_ORDERS_{page+1}.png',dpi=140);plt.close(fig)
    evidence=load(OUT/'PRESERVED_RAW_CONTEXT.json');assert len(evidence)==6;raw_pages=(len(evidence)+3)//4
    assert raw_pages==plan['plot_pagination']['raw_pages']
    for page in range(raw_pages):
        subset=evidence[4*page:4*page+4];fig,axes=plt.subplots(len(subset),2,figsize=(11,3*len(subset)),layout='constrained',squeeze=False)
        for i,item in enumerate(subset):
            with np.load(OUT/item['copied_path'],allow_pickle=False)as z:
                for j,key in enumerate(['raw_cutout','raw_excess']):
                    a=np.array(z[key]);ax=axes[i,j];m=max(float(np.max(np.abs(a))),1.)
                    im=ax.imshow(a,origin='lower',interpolation='nearest',aspect='auto',cmap='RdBu_r'if j else'viridis',vmin=-m if j else float(np.min(a)),vmax=m if j else float(np.max(a)))
                    ax.set_title(f"{item['event']} · order {item['order']} · stored {key}",fontsize=9);ax.set_xlabel('Saved cutout column index');ax.set_ylabel('Saved cutout row index');fig.colorbar(im,ax=ax,shrink=.8)
        fig.suptitle(f'C029 · all six preserved original event/order raw contexts · page {page+1}/{raw_pages}\n0261/0266 original local/baseline false;0272 true; global/later support true for all.0261 blend caution retained.\nSeparate full scales; remote deposits do not classify the central feature. No new mapping or subtraction.',fontsize=10)
        fig.savefig(figs/f'PRESERVED_RAW_ORDER_CONTEXT_{page+1}.png',dpi=140);plt.close(fig)
    for f,h in hashes.items():
        if sha(OUT/f)!=h:raise ValueError('Numeric output changed during plotting')
    index={'all24_profile_slots_retained':True,'all_three_original_event_raw_contexts_retained':True,'distinct_discovery_products':3,'native_pages':native_pages,'raw_pages':raw_pages,'total_figures':2+native_pages+raw_pages,'all_three_reference_and_marker_ids':list(plan['events']),'metadata_excluded_native_orders':0,'plot_script_sha256':sha(Path(__file__)),'figure_scale_rules':'Merged: same y limits across both frames per quantity/window, all finite values plus 5 percent. Native raw: shared limits across frames per order; normalized panels use own positive flank divisors, or preserve raw-only reasons. Preserved raw panels have separate scales and all saved pixels. Native/raw pages follow fixed input order.','files':[{'path':str(p.relative_to(OUT)),'sha256':sha(p),'bytes':p.stat().st_size}for p in sorted(figs.glob('*.png'))],'numeric_outputs_unchanged':True,'origin_assignments':0}
    (OUT/'PLOT_INDEX.json').write_text(json.dumps(index,indent=2)+'\n');print(json.dumps(index,indent=2))
if __name__=='__main__':main()
