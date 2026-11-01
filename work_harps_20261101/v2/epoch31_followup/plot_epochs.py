"""All28groups, all selected epochs, fixed frame comparison and epoch amplitudes."""
from pathlib import Path
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent;FIG=OUT/'figures';FIG.mkdir(exist_ok=True)
groups=json.loads((OUT/'GROUP_RESULTS.json').read_text());rows=list(csv.DictReader((OUT/'ALL_EPOCH_MEASUREMENTS.csv').open()))
for gi,g in enumerate(groups):
    fig,axs=plt.subplots(2,2,figsize=(12,8));fig.subplots_adjust(left=.07,right=.98,bottom=.08,top=.88,wspace=.27,hspace=.35)
    selected=[r for r in rows if r['group_id']==g['group_id'] and r['frame']=='barycentric'];colors=plt.cm.viridis(np.linspace(.05,.95,len(selected)))
    for fi,frame in enumerate(['barycentric','topocentric']):
        ax=axs[0,fi]
        for r,color in zip(selected,colors):
            rr=next(z for z in rows if z['group_id']==g['group_id'] and z['dp_id']==r['dp_id'] and z['frame']==frame)
            d=np.load(OUT/rr['profile_path']);label=r['date_obs'][:10]+(' *' if json.loads(r['source_unresolved_event_ids']) else '')
            ax.plot(d['offset_air_angstrom'],d['normalized_flux'],lw=.8,c=color,alpha=.85,label=label)
        med=g['frames'][frame]['pairwise_correlation_summary']['median'];ax.set_title(frame+f' · median pairwise core r={med:.3f}',fontsize=10)
        ax.axvline(0,c='red',ls=':',lw=.7);ax.set_xlim(-.45,.45);ax.set_xlabel('Air wavelength offset (Å)');ax.set_ylabel('Flux / local ±2 Å median')
        if fi==0:ax.legend(ncol=2,fontsize=6.8,loc='upper right')
    ax=axs[1,0];days=np.array([float(r['mjd_obs']) for r in selected]);days-=days.min()
    for name,marker,lab in [('narrow_amplitude','o','FWHM λ/115000'),('broad3_amplitude','s','3 × FWHM')]:
        values=np.array([float(r[name]) for r in selected]);ax.plot(days,values,marker+'-',ms=4,lw=.7,label=lab)
    for i,r in enumerate(selected):
        if json.loads(r['source_unresolved_event_ids']):ax.axvline(days[i],color='grey',alpha=.25,lw=.6)
    ax.axhline(0,color='grey',lw=.5);ax.set_xlabel('Days from first selected epoch');ax.set_ylabel('Signed fitted relative amplitude');ax.legend(fontsize=8)
    ax.set_title('Fixed-center descriptive fits; no formal errors',fontsize=10)
    ax=axs[1,1]
    for fi,frame in enumerate(['barycentric','topocentric']):
        rr=[next(z for z in rows if z['group_id']==g['group_id'] and z['dp_id']==r['dp_id'] and z['frame']==frame) for r in selected]
        values=[float(r['leave_one_out_profile_correlation']) for r in rr]
        ax.plot(days,values,'o-' if fi==0 else 's--',ms=4,lw=.8,label=frame)
    ax.set_ylim(-1.05,1.05);ax.set_xlabel('Days from first selected epoch');ax.set_ylabel('Correlation with other-epoch median');ax.legend(fontsize=8)
    ax.set_title('Leave-one-out residual core profiles',fontsize=10)
    fig.suptitle(f"{g['group_id']} · {g['target']} · barycentric air {g['center_bary_air_angstrom']:.4f} Å\n{len(g['member_ids'])} original unresolved event(s), {g['epoch_count']} selected epochs · * marks an original unresolved-hit exposure",fontsize=12)
    fig.savefig(FIG/(g['group_id']+'.png'),dpi=120);plt.close(fig)
print(str(len(groups))+' all-epoch figures written')
