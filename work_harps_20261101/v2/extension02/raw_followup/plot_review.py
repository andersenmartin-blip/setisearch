"""Neutral complete native/raw pages; all selected records and every covering order."""
from pathlib import Path
import json,csv,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
O=Path(__file__).resolve().parent;F=O/'figures';F.mkdir(exist_ok=True)
D=json.loads((O/'NATIVE_MAPPING.json').read_text());events=list(csv.DictReader((O/'SELECTED_EVENTS.csv').open()));spectra={r['dp_id']:r for r in D['spectra']};index=[]
for start in range(0,len(events),4):
 fig,axs=plt.subplots(4,3,figsize=(14,11.6));fig.subplots_adjust(left=.055,right=.985,bottom=.06,top=.91,wspace=.23,hspace=.55)
 for j,event in enumerate(events[start:start+4]):
  orders=[r for r in D['orders']if r['review_id']==event['review_id']and r['status']=='EXTRACTED'];title=event['review_id']+' '+event['target'];ax=axs[j,0];rawax=axs[j,1];exax=axs[j,2];images={k:[]for k in ['raw_cutout','raw_excess']};centers=[];offset=0
  for m in orders:
   a=np.load(O/m['cutout']);side=float(np.median(a['native_flux'][np.r_[0:8,33:41]]));normal=side if side>0 else 1.;ax.plot(a['native_wave']-m['topocentric_air_angstrom'],a['native_flux']/normal,'.-',lw=.8,ms=2.7,label='o'+str(m['order'])+(' / side'if side>0 else' ADU'));centers.append(offset+12+m['raw_column']-round(m['raw_column']));offset+=28
   raw=a['raw_cutout'];low=np.percentile(raw,5);scale=max(float(raw.max()-low),1.)
   images['raw_cutout'].extend([(raw-low)/scale,np.full((21,3),np.nan)]);images['raw_excess'].extend([np.maximum(a['raw_excess'],0)/max(float(a['raw_excess'].max()),1.),np.full((21,3),np.nan)])
  ax.axvline(0,color='red',ls=':',lw=.7);ax.axhline(1,color='gray',lw=.5);ax.set_title(title+' · '+spectra[event['dp_id']].get('date_obs','')[:10]+'\n'+event['fitted_center_bary_air_angstrom'][:10]+' Å barycentric',fontsize=9);ax.set_xlabel('Native topocentric offset (Å)',fontsize=8);ax.set_ylabel('Native flux / local side median',fontsize=8);ax.tick_params(labelsize=8)
  if orders:ax.legend(fontsize=7)
  for plot,key,label in [(rawax,'raw_cutout','Original raw counts'),(exax,'raw_excess','Positive raw excess')]:
   if images[key]:
    plot.imshow(np.hstack(images[key][:-1]),origin='lower',aspect='auto',cmap='magma',vmin=0,vmax=1)
    for c in centers:plot.axvline(c,color='cyan',lw=.7)
    plot.axhline(10,color='cyan',lw=.7)
   plot.set_title(label+' · order '+','.join(str(r['order'])for r in orders),fontsize=9);plot.set_yticks([0,10,20],[-10,0,10]);plot.set_xticks([]);plot.set_xlabel('Each order independently scaled; cyan = predicted trace/row',fontsize=7);plot.set_ylabel('Dispersion-row offset',fontsize=8)
  usable=bool(orders)and all(m['mapping_verified']for m in orders);note='mapping verified'if usable else'LOCAL/GLOBAL MAPPING INCOMPLETE'
  exax.text(.5,1.14,note,transform=exax.transAxes,ha='center',fontsize=8,color='black'if usable else'crimson')
  index.append(dict(review_id=event['review_id'],detector=event['detector'],dp_id=event['dp_id'],page=start//4+1,row=j+1,figure='figures/REVIEW_'+str(start//4+1).zfill(2)+'.png',orders=[r['order']for r in orders],all_extracted_orders_mapping_verified=usable))
 for j in range(len(events[start:start+4]),4):
  for ax in axs[j]:ax.set_visible(False)
 fig.suptitle('Extension02 raw/native review · page '+str(start//4+1)+'/'+str(math.ceil(len(events)/4))+' · original selected-event order\nAll covering extracted orders displayed; independent scales; no origin labels. Source arrays retained.',fontsize=12)
 fig.savefig(F/('REVIEW_'+str(start//4+1).zfill(2)+'.png'),dpi=110);plt.close(fig)
(O/'FIGURE_INDEX.json').write_text(json.dumps(index,indent=2)+'\n');print('pages',math.ceil(len(events)/4),'events',len(index))
