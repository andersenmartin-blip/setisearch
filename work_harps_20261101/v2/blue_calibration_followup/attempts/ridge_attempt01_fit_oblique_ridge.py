"""Fit off-order oblique structure while withholding the candidate vicinity."""
from pathlib import Path
import numpy as np,json,hashlib,datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
O=Path(__file__).resolve().parent;meta=json.loads((O/'RAW_PATCH_METADATA.json').read_text());results=[]
for group,order in [('E01',2),('E10',1)]:
 m=next(r for r in meta if r['group_id']==group and r['A_order']==order);d=np.load(O/m['array']);y=d['raw_rows'];x=d['raw_columns'];im=d['highpass_adu'];cy=m['raw_center_row'];cx=m['raw_center_column'];valid=np.ones(im.shape,dtype=bool)
 for path in m['trace_paths']:valid&=abs(x[None,:]-np.array(path['raw_columns'])[:,None])>6
 valid&=abs(y[:,None]-cy)>80
 trials=[]
 for slope in np.arange(-120,-29)*.001:
  for intercept_offset in np.arange(-40,41)*.25:
   ridge=cx+intercept_offset+slope*(y-cy);mask=(abs(x[None,:]-ridge[:,None])<=2)&valid
   score=float(im[mask].mean())if mask.sum()else -1e30
   trials.append(dict(slope=float(slope),intercept_offset=float(intercept_offset),training_pixels=int(mask.sum()),score_adu=score))
 best=max(trials,key=lambda r:r['score_adu']);ridge=cx+best['intercept_offset']+best['slope']*(y-cy)
 rec=dict(group_id=group,A_order=order,dp_id=m['dp_id'],candidate_row=cy,predicted_science_column=cx,best=best,heldout_ridge_column=cx+best['intercept_offset'],heldout_ridge_minus_science_columns=best['intercept_offset'],slope_angle_degrees=float(np.degrees(np.arctan(abs(best['slope'])))),full_grid=trials,heldout_rows=[cy-80,cy+80],physical_parent_order_identified=False,original_disposition_preserved=True)
 if group=='E10':
  n=next(r for r in meta if r['group_id']=='E11'and r['A_order']==1);cc=cx+best['intercept_offset']+best['slope']*(n['raw_center_row']-cy);rec['E11_independent_evaluation']=dict(candidate_row=n['raw_center_row'],ridge_column=float(cc),science_column=n['raw_center_column'],ridge_minus_science_columns=float(cc-n['raw_center_column']))
 results.append(rec)
 fig,axs=plt.subplots(1,2,figsize=(11,8));ext=[x[0]-.5,x[-1]+.5,y[0]-.5,y[-1]+.5];lo,hi=np.percentile(im,[1,99])
 for ax in axs:
  ax.imshow(im,origin='lower',extent=ext,aspect='auto',cmap='gray',vmin=lo,vmax=hi)
  for path in m['trace_paths']:ax.plot(path['raw_columns'],y,color='lime'if path['fiber']=='A'else'orange',lw=.7)
  ax.plot(ridge,y,color='magenta',lw=1.2,label='ridge fitted off main traces');ax.axhline(cy,color='cyan',lw=.8,ls=':');ax.axhspan(cy-80,cy+80,facecolor='cyan',alpha=.12,label='rows excluded from fit');ax.set_xlabel('Raw cross-dispersion column');ax.set_ylabel('Raw dispersion row')
 axs[0].set_xlim(ext[:2]);axs[0].set_ylim(ext[2:]);axs[0].set_title('Full fixed patch');axs[0].legend(fontsize=8,loc='upper right')
 axs[1].set_xlim(cx-15,cx+15);axs[1].set_ylim(cy-100,cy+100);axs[1].set_title('Held-out crossing, no fit to candidate rows')
 fig.suptitle(group+f' oblique train: slope {best["slope"]:.3f} columns/row; predicted crossing offset {best["intercept_offset"]:+.2f} columns\nPost-hoc descriptive ridge fit; no calibrated significance or physical parent-order ID.');fig.tight_layout(rect=(0,0,1,.94));fig.savefig(O/'figures'/(group+'_OBLIQUE_RIDGE.png'),dpi=130);plt.close(fig)
 print(group,{k:v for k,v in rec.items()if k!='full_grid'},flush=True)
(O/'RIDGE_RESULTS.json').write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha256=hashlib.sha256((O/'RIDGE_PLAN.json').read_bytes()).hexdigest(),results=results),indent=2)+'\n')
