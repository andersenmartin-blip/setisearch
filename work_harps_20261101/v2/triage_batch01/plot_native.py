"""Complete six-event pages: native orders and raw positive excess, no ranking."""
from pathlib import Path
import json,csv,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent;FIG=OUT/'figures';FIG.mkdir(exist_ok=True)
data=json.loads((OUT/'NATIVE_MAPPING.json').read_text())
hits=list(csv.DictReader((OUT/'SELECTED_HITS.csv').open()))
dates={r['dp_id']:r.get('date_obs','')[:10] for r in data['spectra']}
local_audit=OUT/'LOCAL_TRACE_AUDIT.json'
local_warnings={r['review_id'] for r in json.loads(local_audit.read_text())['orders'] if r['visual_local_mapping_warning']} if local_audit.exists() else set()
for start in range(0,len(hits),6):
    if len(sys.argv)>1 and start//6+1!=int(sys.argv[1]):continue
    fig,axs=plt.subplots(3,4,figsize=(14,10),layout='constrained')
    for j,h in enumerate(hits[start:start+6]):
        ax=axs[j//2,2*(j%2)];rx=axs[j//2,2*(j%2)+1]
        orders=[r for r in data['orders'] if r['review_id']==h['review_id'] and r['status']=='EXTRACTED']
        imgs=[];xcenters=[];width=0
        for m in orders:
            d=np.load(OUT/m['cutout']);center=m['topocentric_air_angstrom']
            ax.plot(d['native_wave']-center,d['native_flux']/m['native_side_median'],'.-',ms=3,lw=.8,label='order '+str(m['order']))
            img=d['raw_excess'];mx=max(img.max(),1);imgs.append(np.maximum(img,0)/mx)
            xcenters.append(width+12+m['raw_column']-round(m['raw_column']));width+=28
            imgs.append(np.full((21,3),np.nan))
        ax.axvline(0,c='red',ls=':',lw=.7);ax.axhline(1,c='grey',lw=.5);ax.set_xlim(-.38,.38)
        ax.set_title(h['review_id']+' '+h['target']+'\n'+dates[h['dp_id']]+(' · O I flag' if h['OI_0p03_angstrom_flag']=='True' else ''),fontsize=9)
        ax.set_xlabel('Topocentric air offset (Å)',fontsize=8);ax.set_ylabel('Native flux / side median',fontsize=8);ax.legend(fontsize=7);ax.tick_params(labelsize=7)
        if imgs:
            rx.imshow(np.hstack(imgs[:-1]),origin='lower',aspect='auto',cmap='magma',vmin=0,vmax=1)
            for x in xcenters:rx.axvline(x,c='cyan',lw=.55)
            rx.axhline(10,c='cyan',lw=.55)
        warning='LOCAL TRACE MISALIGNED · ' if h['review_id'] in local_warnings else ('UNVERIFIED MAPPING · ' if any(not m['mapping_verified'] for m in orders) else 'Raw excess · orders ')
        rx.set_title(warning+', '.join(str(m['order']) for m in orders),fontsize=9)
        rx.set_xlabel('Each order scaled to its own maximum',fontsize=7);rx.set_ylabel('Dispersion row',fontsize=8);rx.set_xticks([]);rx.set_yticks([0,10,20],[-10,0,10])
    page=start//6+1
    fig.suptitle(f'V2 native/raw review · page {page}/16 · six consecutive hits\nRaw background: column medians outside ±5 rows; positive excess only. All arrays retained.',fontsize=12)
    fig.savefig(FIG/f'REVIEW_{page:02}.png',dpi=100);plt.close(fig)
print('16 complete six-event pages written')
