"""Fixed central-column enlargements for explicitly requested visual inspection.

Display only: no new extraction, coordinate change, selection threshold or origin
classifier. Read native NPZ cutouts already produced by frozen extraction.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--ids',nargs='+',required=True);a=ap.parse_args()
    wanted=set(a.ids);mapping=json.loads((ROOT/'NATIVE_MAPPING.json').read_text())
    rows=[r for r in mapping['orders']if r['review_id']in wanted and r['status']=='EXTRACTED']
    assert set(a.ids).issubset({r['review_id']for r in mapping['events']})
    index=[]
    for page,start in enumerate(range(0,len(rows),6),1):
        subset=rows[start:start+6];fig,axes=plt.subplots(len(subset),3,figsize=(15.6,2.8*len(subset)),squeeze=False)
        for rr,r in enumerate(subset):
            p=ROOT/r['cutout'];assert hashlib.sha256(p.read_bytes()).hexdigest()==r['cutout_sha256']
            with np.load(p)as z:
                raw=z['raw_cutout'][:,8:25];excess=z['raw_excess'][:,8:25];bg=z['raw_background'][8:25]
            lo=float(np.min(raw));hi=float(np.max(raw));scale=float(np.max(np.maximum(excess,0)));scale=scale if scale>0 else 1.
            ax=axes[rr,0];ax.imshow(raw,origin='lower',aspect='auto',extent=(-8.5,8.5,-15.5,15.5),cmap='inferno',vmin=lo,vmax=hi);ax.set_title(f"{r['review_id']} o{r['order']} raw [{lo:g}, {hi:g}]");ax.axhline(0,color='cyan',lw=.5);ax.axvline(r['raw_column']-round(r['raw_column']),color='cyan',lw=.5);ax.set_ylabel('Dispersion-row offset');ax.set_xlabel('Column offset')
            ax=axes[rr,1];ax.imshow(np.maximum(excess,0),origin='lower',aspect='auto',extent=(-8.5,8.5,-15.5,15.5),cmap='inferno',vmin=0,vmax=scale);ax.set_title(f'Positive excess, scale 0–{scale:g}');ax.axhline(0,color='cyan',lw=.5);ax.axvline(r['raw_column']-round(r['raw_column']),color='cyan',lw=.5);ax.set_xlabel('Column offset')
            ax=axes[rr,2];x=np.arange(-8,9);central=np.mean(raw[13:18],axis=0);ax.plot(x,central,label='mean rows −2…+2');ax.plot(x,bg,label='side median');ax.plot(x,central-bg,label='difference');ax.axvline(r['raw_column']-round(r['raw_column']),color='gray',lw=.5);ax.set_title('Spatial context; descriptive');ax.set_ylabel('Raw counts');ax.set_xlabel('Column offset');ax.legend(fontsize=7)
            index.append(dict(review_id=r['review_id'],order=r['order'],source=r['cutout'],source_sha256=r['cutout_sha256'],figure=f'primary_enlarged/CENTRAL_{page:02d}.png',row=rr+1,column_offsets=[-8,8],raw_min=lo,raw_max=hi,positive_excess_max=scale))
        fig.suptitle('Primary central ±8 columns; fixed arrays/coordinates; per-order scales',fontsize=13,y=.995)
        fig.tight_layout(rect=(0,0,1,.975),h_pad=1.4,w_pad=1.4);fig.savefig(OUT/f'CENTRAL_{page:02d}.png',dpi=115);plt.close(fig)
    (OUT/'DISPLAY_SCALES.json').write_text(json.dumps(dict(scope='Post-hoc display enlargement only; no classifier thresholds or numerical changes.',requested_ids=a.ids,order_panels=len(rows),pages=(len(rows)+5)//6,index=index),indent=2)+'\n')
    print('pages',(len(rows)+5)//6,'order_panels',len(rows))
if __name__=='__main__':main()
