#!/usr/bin/env python3
"""Illustrate every numerically evaluable main object; never change decisions."""
import json,datetime,hashlib
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from astropy.time import Time
P=Path(__file__).resolve().parent
colors={'u':'#8b5cf6','g':'#168a55','r':'#d17a24','i':'#b6424a','z':'#6f4b8c','y':'#555555'}

def main():
    streams={s:json.loads((P/f'{s.upper()}_NORMALIZED.json').read_text()) for s in ['sources','forced']}
    scored={s:json.loads((P/f'{s.upper()}_SCORED.json').read_text()) for s in streams}
    ids=sorted({r['object_id'] for rows in scored.values() for r in rows if r['status']=='NUMERICALLY_EVALUABLE'},key=int)
    fig,axes=plt.subplots(len(ids),2,figsize=(12,8.8),squeeze=False,layout='constrained')
    start=datetime.datetime(2026,10,1);stop=datetime.datetime(2026,11,1)
    for i,oid in enumerate(ids):
        for j,stream in enumerate(['sources','forced']):
            ax=axes[i,j];rows=[r for r in streams[stream] if r['object_id']==oid]
            for band in sorted({r['band'] for r in rows}):
                for bad in (False,True):
                    subset=[r for r in rows if r['band']==band and bool(r['exclusion_reasons'])==bad and r['flux_njy'] is not None and r['flux_error_njy'] is not None and r['time_mjd_tai'] is not None]
                    if not subset:continue
                    x=[Time(r['time_mjd_tai'],format='mjd',scale='tai').utc.datetime for r in subset]
                    ax.errorbar(x,[r['flux_njy'] for r in subset],yerr=[r['flux_error_njy'] for r in subset],
                                fmt='x' if bad else 'o',markersize=3.5,color='#969696' if bad else colors[band],
                                alpha=0.7 if bad else 0.9,elinewidth=.7,capsize=1.2,
                                label=('quality-excluded' if bad else band) if not bad or not any(l.get_label()=='quality-excluded' for l in ax.containers) else '_nolegend_')
            ax.axvspan(start,stop,color='#e9edf4',zorder=-1)
            n=sum(r['status']=='NUMERICALLY_EVALUABLE' and r['object_id']==oid for r in scored[stream])
            ax.set_title(f'{oid} · {stream}\n{n} numerically evaluable October rows',fontsize=9)
            ax.xaxis.set_major_locator(mdates.MonthLocator());ax.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
            ax.tick_params(labelsize=7);ax.grid(alpha=.18);ax.set_ylabel('Direct science flux [nJy]',fontsize=8)
            ax.legend(fontsize=7,ncol=4,frameon=False,loc='best')
            ax.set_xlabel('UTC date · gray area = October 2026 event window',fontsize=8)
    fig.suptitle('Rubin feasibility study: all 3 numerically evaluable objects\nSeparate source and forced photometry; long gaps, unknown withdrawal status; no threshold-passing rows',fontsize=12)
    destination=P/'EVALUABLE_HISTORIES.png';fig.savefig(destination,dpi=160);plt.close(fig)
    record={'selection':'Every object with at least one NUMERICALLY_EVALUABLE row in either fixed stream, exactnumericIDorder','ids':ids,
            'separate_streams_and_filters':True,'history_display':'All saved history shown; only preceding 180 days can enter the frozen detector baseline','error_bars':'Quoted scienceFluxErr, not extra intrinsic scatter','gray_markers':'Rows excluded by frozen quality/numeric rules where finite flux/time/error permits display',
            'source_sha256':{f'{s.upper()}_{suffix}.json':hashlib.sha256((P/f'{s.upper()}_{suffix}.json').read_bytes()).hexdigest() for s in streams for suffix in ['NORMALIZED','SCORED']},
            'image_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'science_decisions_changed':False}
    (P/'FIGURE_PROVENANCE.json').write_text(json.dumps(record,indent=2)+'\n')
    print(destination)

if __name__=='__main__':main()
