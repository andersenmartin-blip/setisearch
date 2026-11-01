"""Plot retained reference failures and fixed-grid evidence, not candidate origin."""
import json,gc
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from check_mapping import OUT,PLAN,load,trace,highpass

grid=json.loads((OUT/'REFERENCE_GRID.json').read_text())
local=json.loads((OUT/'LOCAL_CHECK.json').read_text())
fig,ax=plt.subplots(2,2,figsize=(14,8),constrained_layout=True)
for row,rec in enumerate(grid['records']):
    dp=rec['dp_id'];vals=[];labels=[]
    for reg in rec['reference_regions']:
        labels.append(str(reg['order'])+':'+str(reg['pixel_interval_half_open'][0]))
        vals.append([next(z['correlation'] for z in reg['options'] if z['row_flip'] and not z['column_flip'] and z['argument_flip']==af) for af in [False,True]])
    vals=np.array(vals)
    xx=np.arange(len(vals))
    ax[row,0].plot(xx,vals[:,0],'o-',ms=4,label='P(native pixel), incorrect global trace')
    ax[row,0].plot(xx,vals[:,1],'o-',ms=4,label='P(raw row = 4095-native pixel)')
    ax[row,0].axhline(.8,color='gray',ls='--',label='original 0.8 threshold')
    ax[row,0].set_xticks(xx,labels,rotation=90,fontsize=7)
    ax[row,0].set_ylim(-.15,1.05);ax[row,0].set_ylabel('Pearson r');ax[row,0].set_xlabel('Order: starting native pixel')
    ax[row,0].set_title(dp+'\nFixed grid with candidate exclusions');ax[row,0].legend(fontsize=7)
    raw,native,h,_=load(dp)
    x=np.arange(1000,1400);ref=highpass(native[50,x]);cx=np.rint(trace(h,50,x,True)).astype(int);yy=4095-x
    hp=highpass(np.stack([raw[yy,cx+j] for j in range(-3,4)]).sum(axis=0))
    diag=next(z for z in local['records'][row]['original_reference_diagnostic'] if z['argument_flip'])
    removed={z['native_pixel'] for z in diag['excluded_pixels']}
    keep=np.array([int(k) not in removed for k in x])
    slope=np.linalg.lstsq(np.c_[ref[keep],np.ones(sum(keep))],hp[keep],rcond=None)[0]
    ax[row,1].plot(x,hp,lw=.8,label='raw seven-column sum, high-passed')
    ax[row,1].plot(x,slope[0]*ref+slope[1],lw=.8,label='native, linearly scaled using retained samples')
    ax[row,1].scatter(x[~keep],hp[~keep],s=25,facecolor='none',edgecolor='red',label='fixed 8-MAD diagnostic exclusions')
    ax[row,1].set_xlabel('Native pixel (original order-50 reference)');ax[row,1].set_ylabel('High-pass raw counts')
    ax[row,1].set_title(f"Original failed r={diag['original_pearson']:.3f}; diagnostic masked r={diag['diagnostic_8mad_pearson']:.3f}\nAll old checks retained; diagnostic mask is not a replacement gate")
    ax[row,1].legend(fontsize=7)
    del raw,native;gc.collect()
fig.savefig(OUT/'figures/REFERENCE_DIAGNOSTICS.png',dpi=160);plt.close(fig)
