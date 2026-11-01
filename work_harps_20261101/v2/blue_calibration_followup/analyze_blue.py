"""Post-hoc native/reference-fiber comparison for fixed blue groups; no classification."""
from pathlib import Path
import numpy as np,json,hashlib,tarfile,io,subprocess,gc,datetime
from astropy.io import fits
from scipy.ndimage import median_filter
from scipy.signal import find_peaks
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
O=Path(__file__).resolve().parent; B=O.parents[1];P=json.loads((O/'PLAN.json').read_text())
A=O/'arrays';A.mkdir(exist_ok=True);F=O/'figures';F.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def dump(name,obj):(O/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def finite(x):return float(x)if np.isfinite(x)else None
def poly(h,p,d,o,x):return np.polynomial.polynomial.polyval(x,[h[p+str(o*(d+1)+j)]for j in range(d+1)])
def wave(h,o):return poly(h,'ESO DRS CAL TH COEFF LL',int(h['ESO DRS CAL TH DEG LL']),o,np.arange(4096))
def ctx(h):return {k:v for k,v in h.items()if any(t in k for t in ['DPR','INS OPTI','LAMP','CAL TH FILE','CAL LOC FILE','CAL FLAT FILE'])and isinstance(v,(str,int,float,bool))}
products=sum([json.loads((B/f'v2/triage_batch{i:02d}/products/MANIFEST.json').read_text())['products']for i in [1,2]],[])
meta={r['dp_id']:r for r in json.loads((B/'v2/acquisition/DOWNLOAD_MANIFEST.json').read_text())}
mappings=sum([json.loads((B/f'v2/triage_batch{i:02d}/NATIVE_MAPPING.json').read_text())['spectra']for i in [1,2]],[])
records=[];inventory=[];comparisons=[];patches=[]
for dp in P['available_native_exposure_ids']:
 print(dp,flush=True);tr=next(r for r in products if r['dp_id']==dp and r['kind']=='ANCILLARY');rr=next(r for r in products if r['dp_id']==dp and r['kind']=='RAW')
 for r in [tr,rr]:assert sha(B/r['relative_path'])==r['sha256']
 with fits.open(io.BytesIO(subprocess.run(['gzip','-cd',str(B/rr['relative_path'])],capture_output=True,check=True).stdout))as h:
  rh=h[0].header.copy();raw=np.hstack([h[1].data[:,50:2098],h[2].data[:,50:2098]]).astype(float)
 assert rh['DATE-OBS']==meta[dp]['primary_header']['DATE-OBS'];inv=dict(dp_id=dp,target=meta[dp]['canonical_target'],date_obs=rh['DATE-OBS'],raw_context=ctx(rh),raw_sha256=rr['sha256'],ancillary_sha256=tr['sha256'],fibers={})
 data={}
 with tarfile.open(B/tr['relative_path'])as t:
  inv['members']=t.getnames()
  for fiber in ['A','B']:
   ms=[m for m in t if m.name.endswith('_e2ds_'+fiber+'.fits')]
   if not ms:inv['fibers'][fiber]={'status':'MISSING'};continue
   with fits.open(io.BytesIO(t.extractfile(ms[0]).read()))as h: flux=h[0].data.astype(float);hd=h[0].header.copy()
   assert hd['DATE-OBS']==rh['DATE-OBS'];inv['fibers'][fiber]=dict(status='PRESENT',shape=list(flux.shape),member=ms[0].name,context=ctx(hd));data[fiber]=(flux,hd,np.array([wave(hd,o)for o in range(flux.shape[0])]))
  for group in [g for g in P['groups']if g['target']==meta[dp]['canonical_target']]:
   center=group['center_topocentric_air_angstrom'];subset={}
   for fiber,(flux,hd,waves)in data.items():
    subset[fiber]=[]
    for order in np.flatnonzero((waves[:,0]<center)&(waves[:,-1]>center)):
     order=int(order);sel=abs(waves[order]-center)<=2.;w=waves[order,sel];f=flux[order,sel];base=median_filter(f,size=31,mode='nearest');res=f-base;mad=1.4826*np.median(abs(res-np.median(res)));pk,props=find_peaks(res,distance=5,prominence=2*mad);name=dp.replace(':','_')+'_'+group['group_id']+'_'+fiber+'_o'+str(order)+'.npz';np.savez_compressed(A/name,wave_angstrom=w,flux_adu=f,highpass_adu=res,native_pixel=np.flatnonzero(sel))
     rec=dict(dp_id=dp,target=meta[dp]['canonical_target'],date_obs=rh['DATE-OBS'],group_id=group['group_id'],fiber=fiber,order=order,center_air_angstrom=center,reference_exposure=dp==group['reference_dp_id'],array='arrays/'+name,samples=len(w),window_edges_angstrom=[float(w[0]),float(w[-1])],full_4ang_window=bool(waves[order,0]<center-2 and waves[order,-1]>center+2),highpass_mad_adu=finite(mad),descriptive_peaks_air_angstrom=w[pk].tolist(),peak_spacing_angstrom=np.diff(w[pk]).tolist(),not_detection_catalog=True);records.append(rec);subset[fiber].append((rec,w,f,res))
   for a,wa,fa,ra in subset.get('A',[]):
    for b,wb,fb,rb in subset.get('B',[]):
     good=(abs(wa-center)<=1.5)&(wa>=wb[0])&(wa<=wb[-1]);br=np.interp(wa[good],wb,rb);corr=finite(np.corrcoef(ra[good],br)[0,1])if good.sum()>10 else None
     comparisons.append(dict(dp_id=dp,group_id=group['group_id'],A_order=a['order'],B_order=b['order'],samples=int(good.sum()),same_wavelength_highpass_Pearson_r=corr,shift_optimized=False,not_ghost_path_model=True))
   if dp==group['reference_dp_id']:
    fig,axs=plt.subplots(len(subset['A'])+len(subset.get('B',[])),1,figsize=(13,2.2*(len(subset['A'])+len(subset.get('B',[])))));axs=np.atleast_1d(axs)
    for ax,(r,w,f,res)in zip(axs,sum([subset[k]for k in subset],[])):
     ax.plot(w,res,lw=.8);ax.axvline(center,color='r',ls=':');ax.set_ylabel(r['fiber']+' o'+str(r['order'])+' residual ADU');ax.set_xlim(center-2,center+2);ax.grid(alpha=.15)
    axs[-1].set_xlabel('Native topocentric air wavelength (Å)');fig.suptitle(group['group_id']+' '+meta[dp]['canonical_target']+' · A science and B calibration, independent vertical scales');fig.tight_layout(rect=(0,0,1,.95));fig.savefig(F/(group['group_id']+'_NATIVE_AB.png'),dpi=120);plt.close(fig)
    mapping=next(m for m in mappings if m['dp_id']==dp);ori=mapping.get('grid_best',mapping['orientations'][0]);ha=data['A'][1];wa=data['A'][2]
    for r,_,_,_ in subset['A']:
     order=r['order'];k=int(np.argmin(abs(wa[order]-center)));cy=4095-k if ori['row_flip']else k;arg=4095-k if ori['argument_flip']else k;cx=poly(ha,'ESO DRS CAL LOC CTR',int(ha['ESO DRS CAL LOC DEG CTR']),order,arg);cx=4095-cx if ori['column_flip']else cx
     rows=np.arange(max(0,cy-250),min(4096,cy+251));cols=np.arange(max(0,round(cx)-80),min(4096,round(cx)+81));cut=raw[np.ix_(rows,cols)];high=cut-median_filter(cut,size=(31,1),mode='nearest');name=group['group_id']+'_raw_o'+str(order)+'.npz';np.savez_compressed(A/name,raw_adu=cut,highpass_adu=high,raw_rows=rows,raw_columns=cols)
     paths=[]
     for fiber,(_,h,ww)in data.items():
      for oo in range(ww.shape[0]):
       native_arg=4095-rows if ori['row_flip']else rows;arg=4095-native_arg if ori['argument_flip']else native_arg;trace=poly(h,'ESO DRS CAL LOC CTR',int(h['ESO DRS CAL LOC DEG CTR']),oo,arg);trace=4095-trace if ori['column_flip']else trace
       if np.any((trace>=cols[0])&(trace<=cols[-1])):paths.append(dict(fiber=fiber,order=oo,raw_columns=trace.tolist()))
     patch=dict(dp_id=dp,group_id=group['group_id'],A_order=order,native_pixel=k,raw_center_row=cy,raw_center_column=float(cx),raw_row_range=[int(rows[0]),int(rows[-1])],raw_column_range=[int(cols[0]),int(cols[-1])],edge_clipped=len(rows)<501 or len(cols)<161,array='arrays/'+name,orientation=ori,trace_paths=paths);patches.append(patch)
     fig,axs=plt.subplots(1,2,figsize=(10,9));ext=[cols[0]-.5,cols[-1]+.5,rows[0]-.5,rows[-1]+.5]
     for ax,im,label,lims in [(axs[0],cut,'raw ADU',np.percentile(cut,[10,99.5])),(axs[1],high,'31-row high-pass ADU',np.percentile(high,[1,99]))]:
      pic=ax.imshow(im,origin='lower',aspect='auto',extent=ext,vmin=lims[0],vmax=lims[1],cmap='gray');fig.colorbar(pic,ax=ax,shrink=.7);ax.set_xlabel('Raw CCD cross-dispersion column');ax.set_ylabel('Raw CCD dispersion row');ax.set_title(label);ax.axhline(cy,color='cyan',ls=':',lw=.7)
      for path in paths:ax.plot(path['raw_columns'],rows,lw=.6,alpha=.65,color='lime'if path['fiber']=='A'else 'orange');ax.text(path['raw_columns'][len(rows)//2],rows[-1]-10,path['fiber']+str(path['order']),color='lime'if path['fiber']=='A'else 'orange',fontsize=6,clip_on=True)
      ax.set_xlim(ext[:2]);ax.set_ylim(ext[2:])
     fig.suptitle(group['group_id']+f' · native A order {order} · predicted A (green), B (orange) traces\nFixed patch; clipped at detector boundary where necessary. No fitted ghost curve.');fig.tight_layout(rect=(0,0,1,.94));fig.savefig(F/(group['group_id']+'_RAW_o'+str(order)+'.png'),dpi=130);plt.close(fig)
 inventory.append(inv);del raw;gc.collect()
for rel,h in P['original_hashes'].items():assert sha(B/rel)==h
dump('NATIVE_MEASUREMENTS.json',records);dump('NATIVE_AB_COMPARISONS.json',comparisons);dump('FIBER_INVENTORY.json',inventory);dump('RAW_PATCH_METADATA.json',patches)
dump('SUMMARY.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),native_exposures=len(inventory),native_measurements=len(records),A_B_same_wave_comparisons=len(comparisons),raw_patches=len(patches),original_hashes_verified=True,plan_sha256=sha(O/'PLAN.json'),script_sha256=sha(Path(__file__)),automatic_classification=False));print('COMPLETE',len(records),len(patches),flush=True)
