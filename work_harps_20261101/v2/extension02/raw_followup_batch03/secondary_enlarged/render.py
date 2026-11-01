"""Display unchanged central raw pixels for a secondary descriptive review.

This is display-only: no mapping, sample, threshold or classification is altered.
Run only after root authorizes the completed batch's visual review.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
OUT=HERE.parent

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--ids',nargs='*',help='Exact review IDs; omit for all available orders')
    args=parser.parse_args()
    mapping=json.loads((OUT/'NATIVE_MAPPING.json').read_text())
    keep=set(args.ids)if args.ids else None
    records=[r for r in mapping['orders']if r['status']=='EXTRACTED'and(keep is None or r['review_id']in keep)]
    assert records
    metadata=[]
    for page,start in enumerate(range(0,len(records),6),1):
        group=records[start:start+6]
        fig,axes=plt.subplots(len(group),3,figsize=(15,3.25*len(group)),squeeze=False)
        fig.suptitle('Secondary review: central ±8 columns; fixed pixels/coordinates; independent order scales',fontsize=11,y=.996)
        for row,r in enumerate(group):
            path=OUT/r['cutout'];assert digest(path)==r['cutout_sha256']
            with np.load(path)as z:
                raw=z['raw_cutout'][:,8:25];excess=z['raw_excess'][:,8:25];bg=z['raw_background'][8:25]
            low=float(np.percentile(raw,5));high=float(np.max(raw));scale=float(np.max(np.maximum(excess,0)))
            if high<=low:high=low+1
            if scale<=0:scale=1
            for ax,data,vmin,vmax,title in[(axes[row,0],raw,low,high,f"{r['review_id']} o{r['order']:02d}: raw [{low:g},{high:g}]"),(axes[row,1],np.maximum(excess,0),0,scale,f'Positive excess: scale 0–{scale:g}')]:
                ax.imshow(data,origin='lower',interpolation='nearest',aspect='auto',extent=[-8.5,8.5,-15.5,15.5],cmap='inferno',vmin=vmin,vmax=vmax)
                ax.axhline(0,color='cyan',lw=.5);ax.axvline(r['raw_column']-round(r['raw_column']),color='cyan',lw=.5)
                ax.set(xlabel='Cross-dispersion column offset',ylabel='Dispersion-row offset',title=title)
            center=np.mean(raw[13:18],axis=0);x=np.arange(-8,9)
            axes[row,2].plot(x,center,label='mean rows −2…+2');axes[row,2].plot(x,bg,label='frozen side median');axes[row,2].plot(x,center-bg,label='difference')
            axes[row,2].axvline(r['raw_column']-round(r['raw_column']),color='black',lw=.5)
            axes[row,2].set(xlabel='Column offset',ylabel='Raw counts',title='Spatial context; descriptive only')
            if row==0:axes[row,2].legend(fontsize=7)
            metadata.append(dict(review_id=r['review_id'],order=r['order'],cutout=r['cutout'],cutout_sha256=r['cutout_sha256'],figure=f'secondary_enlarged/CENTRAL_{page:02d}.png',row=row+1,crop='all31rows, columns8:25 of33 (center±8)',raw_percentile5=low,raw_maximum=high,positive_excess_scale=scale,center_profile_rows='13:18',background='stored frozen raw_background',mapping_verified=r['mapping_verified']))
        fig.tight_layout(rect=[0,0,1,.98],h_pad=2.1)
        fig.savefig(HERE/f'CENTRAL_{page:02d}.png',dpi=120)
        plt.close(fig)
    (HERE/'INDEX.json').write_text(json.dumps(dict(method='Display-only unchanged central±8columns; positive excess is clipped at zero only for plotting. Raw/background/difference curves retain counts. Every scale saved; no morphology thresholds.',selection='all extracted orders'if keep is None else sorted(keep),mapping_sha256=digest(OUT/'NATIVE_MAPPING.json'),records=metadata),indent=2)+'\n')
    print('Rendered',len(records),'order panels in',page,'pages')
if __name__=='__main__':main()
