#!/usr/bin/env python3
"""Post-run layout amendment only: shorter native-coordinate labels; identical data/scales.
Original frozen script and figures are retained. No measurement is recomputed.
"""
from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parents[1]
OUT=HERE/'results'
NAMES=['pooled','negative_raw_flank','positive_raw_flank']
WINDOWS=['TARGET']+[f'C{i:02d}'for i in range(1,9)]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    plan=json.loads((HERE/'PLAN.json').read_text())
    if sha(HERE/'plot_spatial.py')!=plan['plot_script_sha256']:raise ValueError('Plot code changed')
    hashes=json.loads((OUT/'OUTPUT_HASHES.json').read_text())
    for f,h in hashes.items():
        if sha(OUT/f)!=h:raise ValueError('Numeric output changed')
    data=np.load(OUT/'SPATIAL_ARRAYS.npz',allow_pickle=False)
    metrics=json.loads((OUT/'WINDOW_METRICS.json').read_text())
    figs=OUT/'figures_readable';figs.mkdir(exist_ok=False)
    finite_res=[data[n+'__'+w+'__residual'][np.isfinite(data[n+'__'+w+'__residual'])]for n in NAMES for w in WINDOWS if n+'__'+w+'__residual'in data]
    vmax=max([float(np.max(np.abs(x)))for x in finite_res if len(x)]+[1.])
    def maps(pairs,filename,title):
        fig,axes=plt.subplots(len(pairs),3,figsize=(13,2.2*len(pairs)),squeeze=False,layout='constrained')
        for i,(n,w)in enumerate(pairs):
            prefix=n+'__'+w+'__'
            if prefix+'raw'not in data:
                for ax in axes[i]:ax.text(.5,.5,'BLOCKED — retained slot',ha='center',va='center');ax.set_axis_off()
                continue
            raw=data[prefix+'raw'];model=data[prefix+'model'];res=data[prefix+'residual'];centers=data[prefix+'trace_columns']
            lo=float(np.nanmin(np.r_[raw.ravel(),model.ravel()]));hi=float(np.nanmax(np.r_[raw.ravel(),model.ravel()]))
            for j,(name,a)in enumerate([('raw ADU',raw),('fixed-template model',model),('residual ADU',res)]):
                ax=axes[i,j];im=ax.imshow(a,origin='lower',aspect='auto',extent=[-12.5,12.5,-5.5,5.5],interpolation='nearest',cmap='RdBu_r'if j==2 else'viridis',vmin=-vmax if j==2 else lo,vmax=vmax if j==2 else hi)
                ax.plot(centers-np.rint(centers),np.arange(-5,6),color='white',lw=.8)
                ax.set_title(w+' · '+n+' · '+name,fontsize=9);ax.set_xlabel('Column − rounded trace [pixel]');ax.set_ylabel('Raw row offset [pixel]')
                fig.colorbar(im,ax=ax,shrink=.8)
        fig.suptitle(title,fontsize=12);fig.savefig(figs/filename,dpi=140);plt.close(fig)
    maps([(n,'TARGET')for n in NAMES],'TARGET_ALL_TEMPLATES.png','0235 spatial diagnostic · all three declared templates; no model selection')
    maps([('pooled',w)for w in WINDOWS],'ALL_WINDOWS_POOLED.png','Target + all eight held-out controls · pooled template · common residual scale')
    t=json.loads((OUT/'TEMPLATES.json').read_text());fig,axes=plt.subplots(1,3,figsize=(15,4.2),layout='constrained')
    for n in NAMES:
        if n in t['templates']:axes[0].plot(t['grid_true_crossdisp_pixels'],t['templates'][n],label=n)
        rs=[r for r in metrics if r['template']==n];axes[1].plot(np.arange(9),[r.get('off_trace_l1_fraction',np.nan)for r in rs],marker='o',label=n);axes[2].plot(np.arange(9),[r.get('maximum_pixel_l1_fraction',np.nan)for r in rs],marker='o',label=n)
    axes[0].set_xlabel('True cross-dispersion offset [pixel]');axes[0].set_ylabel('Signed normalized empirical template');axes[0].axhline(0,color='grey',lw=.6)
    for ax in axes[1:]:ax.set_xticks(range(9),WINDOWS,rotation=45);ax.set_ylim(0,1);ax.grid(alpha=.2)
    axes[1].set_ylabel('Off-trace residual L1 / all residual L1');axes[2].set_ylabel('Maximum pixel |residual| / residual L1');axes[0].legend(fontsize=8)
    fig.suptitle('All declared sensitivity templates and coordinate-selected controls · descriptive only');fig.savefig(figs/'TEMPLATES_AND_CONTROL_CONTEXT.png',dpi=140);plt.close(fig)
    for f,h in hashes.items():
        if sha(OUT/f)!=h:raise ValueError('Numeric output changed during plotting')
    index={'layout_amendment':'Shorter repeated axis labels only; fixed data, scales, windows, templates and all numeric outputs unchanged. White line is the inherited trace; true cross-dispersion offset is native column minus that trace, not minus its rounded value. Raw row offsets are relative to each window center.', 'original_frozen_plot_script_sha256':sha(HERE/'plot_spatial.py'),'layout_script_sha256':sha(Path(__file__)),'all_windows_retained':True,'all_templates_retained':True,'pixel_interpolation':'none in displays; nearest native image pixels','residual_scale':'symmetric maximum absolute residual across all measured windows and all templates','raw_model_scale':'shared native min/max per displayed window; differs between windows','files':[{'path':str(p.relative_to(OUT)),'sha256':sha(p),'bytes':p.stat().st_size}for p in sorted(figs.glob('*.png'))],'original_outputs_unchanged':True,'origin_assignments':0}
    (OUT/'READABLE_PLOT_INDEX.json').write_text(json.dumps(index,indent=2)+'\n')
    print(json.dumps(index,indent=2))
if __name__=='__main__':main()
