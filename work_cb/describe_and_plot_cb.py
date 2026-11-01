"""Posthoc interpretation of the closed catalogue and measured-data plots."""
from pathlib import Path
import csv,json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator,FormatStrFormatter

R=Path(__file__).resolve().parent
rows=list(csv.DictReader(open(R/'results/SPECTRAL_FEATURES_CB.csv')))
temporal=list(csv.DictReader(open(R/'results/TEMPORAL_FEATURES_CB.csv')))
st=np.load(R/'results/STATISTICS_CB.npz',allow_pickle=False)
result=json.loads((R/'results/RESULT_CB.json').read_text())
header=json.loads((R/'new_data_discovery/HIP35136_HEADER.json').read_text())
freq=st['frequency_MHz'];df=abs(header['foff']);dt=header['tsamp']
comb=[r for r in rows if int(r['peak_channel'])%1024==512]
hi=[r for r in rows if 1419.5<=float(r['peak_frequency_MHz'])<=1421.5]
other=[r for r in rows if r not in comb and r not in hi]
event=max(temporal,key=lambda r:float(r['peak_score']))
first,last=int(event['first_row']),int(event['last_row']);flo,fhi=int(event['first_channel']),int(event['last_channel'])
triage={'schema':'SETI_CB_POSTHOC_CATALOGUE_DESCRIPTION_V1','posthoc':True,
 'all_original_masks_and_catalogues_unchanged':True,'spectral_groups':len(rows),
 'grid_aligned_peak_groups':len(comb),'grid_rule':'peak_channel modulo1024 equals512',
 'grid_spacing_MHz':1024*df,'grid_interpretation':'Alignment with repeated instrument-channel pattern documented in source tutorial; not independent emitter identification.',
 'HI_window_groups':len(hi),'HI_component_numbers':[int(r['component']) for r in hi],
 'HI_window_and_grid_overlap_groups':len([r for r in hi if r in comb]),
 'HI_window_non_grid_groups':len([r for r in hi if r not in comb]),
 'category_note':'HI window and grid alignment overlap;only grid64,HI-window-non-grid1,other9 form a partition.',
 'other_spectral_groups':len(other),'other_spectral_frequencies_MHz':[float(r['peak_frequency_MHz']) for r in other],
 'largest_temporal_score_component':{'component':int(event['component']),'pixels':int(event['pixels']),
   'peak_frequency_MHz':float(event['peak_frequency_MHz']),'first_row':first,'last_row':last,
   'observed_integrations':last-first+1,'observed_integration_duration_seconds':(last-first+1)*dt,
   'frequency_bounding_box_width_MHz':(fhi-flo+1)*df,'time_bounding_box_start_seconds':first*dt,
   'touches_end_of_file':last==header['complete_time_rows']-1,
   'interpretation':'Broad time-local excess; origin unresolved without OFF comparison. True end time and full event duration not measured.'},
 'limitations':['Labels were added after seeing output and do not alter fixed search decisions.',
 'No physical source assigned to other9 spectral groups or310 temporal groups.',
 'These are coarse-resolution features,not qualifiedSETI candidates.'],
 'bound_catalogues':{n:hashlib.sha256((R/'results'/n).read_bytes()).hexdigest() for n in ['SPECTRAL_FEATURES_CB.csv','TEMPORAL_FEATURES_CB.csv']}}
(R/'POSTHOC_DESCRIPTION_CB.json').write_text(json.dumps(triage,indent=2)+'\n')
nt,nc=result['shape'];a=np.memmap(R/'new_data_discovery/HIP35136_57563_0011_mid.fil',mode='r',dtype='<f4',offset=header['header_bytes'],shape=(nt,nc))
norm=a.astype(float)/st['row_medians'][:,None]
relative=norm/st['temporal_median'][None,:]
plt.rcParams.update({'font.size':11,'svg.fonttype':'none'})
fig,axes=plt.subplots(2,2,figsize=(13,8))
ax=axes[0,0];ax.plot(freq,st['median_normalized_spectrum'],color='#193f68',lw=.65)
ax.set(xlim=(freq.min(),freq.max()),xlabel='Frekvens (MHz)',ylabel='Medianeffekt / rækkemedian',title='Hele stjerneobservationens spektrum')
ax.text(.03,.92,'64 af 74 grupper følger et fast kanalgrid',transform=ax.transAxes,fontsize=10)
ax=axes[0,1];q=(freq>1419.8)&(freq<1420.8)
ax.plot(freq[q],100*st['spectral_residual'][q],color='#1e836d',lw=1.5)
ax.set(xlabel='Frekvens (MHz)',ylabel='Lokalt overskud (%)',title='Hydrogenområdet omkring 1420 MHz')
ax.xaxis.set_major_locator(MaxNLocator(5));ax.xaxis.set_major_formatter(FormatStrFormatter('%.1f'))
ax.text(.03,.9,'Kendt struktur i kildens vejledning',transform=ax.transAxes,fontsize=10)
ax=axes[1,0];rebinned=np.mean(relative.reshape(nt,1024,64),axis=2)
im=ax.imshow(np.log10(rebinned[:,::-1]),origin='lower',aspect='auto',extent=[freq.min(),freq.max(),-.5*dt,(nt-.5)*dt],cmap='magma',vmin=-.05,vmax=.25)
ax.set(xlabel='Frekvens (MHz)',ylabel='Tid fra første sample (s)',title='Tidsvariation over hele båndet')
fig.colorbar(im,ax=ax,label='log10 relativ effekt',pad=.02)
ax=axes[1,1];region=(freq>1379.9)&(freq<1382.1);times=np.arange(nt)*dt;tmask=times>275
small=relative[tmask][:,region]
im=ax.imshow(small[:,::-1],origin='lower',aspect='auto',extent=[freq[region].min(),freq[region].max(),times[tmask][0]-.5*dt,times[-1]+.5*dt],cmap='magma',vmin=.8,vmax=3)
ax.set(xlabel='Frekvens (MHz)',ylabel='Tid fra første sample (s)',title='Bred opblussen mod slutningen')
ax.xaxis.set_major_locator(MaxNLocator(4));ax.xaxis.set_major_formatter(FormatStrFormatter('%.1f'))
fig.colorbar(im,ax=ax,label='Effekt / tidsmedian',pad=.02)
fig.suptitle('HIP35136: 17,9 millioner målte radioværdier analyseret',fontsize=17,x=.07,ha='left')
fig.text(.07,.025,'Én historisk observation · 187,5 MHz inputbånd · 2.861 Hz kanaler · ingen OFF-sammenligning eller kvalificeret SETI-kandidat',fontsize=10)
fig.subplots_adjust(left=.07,right=.96,top=.9,bottom=.12,hspace=.35,wspace=.3)
out=R/'figures';out.mkdir(exist_ok=True)
fig.savefig(out/'CB_HIP35136_2026-11-01.png',dpi=160)
fig.savefig(out/'CB_HIP35136_2026-11-01.svg')
plt.close(fig)
print(json.dumps(triage))
