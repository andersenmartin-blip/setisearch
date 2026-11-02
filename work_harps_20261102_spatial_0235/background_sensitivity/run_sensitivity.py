#!/usr/bin/env python3
"""Released, fixed two-estimator sensitivity using only already selected pixels."""
import argparse,csv,datetime,hashlib,json,math,re
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
J=np.arange(-12,13);GRID=np.arange(-8,9,dtype=float)
CENTERS=[-255,-205,-155,-105,106,156,206,256]
ESTIMATORS=('negative_side','positive_side')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def dump(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n')
def path(name):
 if Path(name).is_absolute():raise ValueError('Repository-relative path required')
 p=(REPO/name).resolve();p.relative_to(REPO);return p
def coordinates():
 flank=set(range(-280,-80))|set(range(81,281));controls={f'C{i+1:02d}':list(range(c-5,c+6)) for i,c in enumerate(CENTERS)}
 withheld={r for c in CENTERS for r in range(c-10,c+11)};training=sorted(flank-withheld);windows={'TARGET':list(range(-5,6)),**controls}
 assert len(training)==232 and not set(training)&set(sum(windows.values(),[]))
 return training,windows

def validate(release_path):
 p=read(HERE/'PLAN.json');r=read(release_path)
 if r.get('schema')!='HARPS_SPATIAL0235_BACKGROUND_SENSITIVITY_RELEASE_V1' or r.get('approved') is not True:raise ValueError('Exact root release required')
 if r.get('publication_readback_verified') is not True or not re.fullmatch('[0-9a-f]{40}',r.get('publication_commit','')):raise ValueError('Verified public freeze required')
 if r.get('plan_sha256')!=sha(HERE/'PLAN.json') or r.get('script_sha256')!=sha(Path(__file__)):raise ValueError('Method release changed')
 if p.get('runner_sha256')!=sha(Path(__file__)) or p.get('estimators')!=list(ESTIMATORS):raise ValueError('Fixed method differs')
 for name,h in p['source_hashes'].items():
  if sha(path(name))!=h:raise ValueError('Frozen source changed: '+name)
 frozen=path(r['freeze_path'])
 if sha(frozen)!=r['freeze_sha256']:raise ValueError('Freeze bytes changed')
 freeze=read(frozen)
 required=[HERE/'PLAN.json',Path(__file__),HERE/'README.md']
 for f in required:
  rec=freeze['files'].get(str(f.relative_to(REPO)))
  if rec is None or rec['sha256']!=sha(f) or rec['bytes']!=f.stat().st_size:raise ValueError('Freeze omits exact method '+str(f))
 pubpath=path(r['publication_receipt_path'])
 if sha(pubpath)!=r['publication_receipt_sha256']:raise ValueError('Publication receipt changed')
 pub=read(pubpath)
 if pub['status']!='PASS_EXACT_REMOTE_READBACK' or pub['commit']!=r['publication_commit']:raise ValueError('Exact publication absent')
 pubfiles={x['path']:x for x in pub['files']}
 for f in [frozen,*required]:
  rec=pubfiles.get(str(f.relative_to(REPO)))
  if rec is None or rec['sha256']!=sha(f) or rec['bytes']!=f.stat().st_size:raise ValueError('Publication omits exact method '+str(f))
 return p,r

def row_geometry(raw,center,estimator):
 if estimator not in ESTIMATORS:raise ValueError('Unknown fixed estimator')
 d=np.rint(center)+J-center;outer=(np.abs(d)>=9)&(np.abs(d)<=12)
 neg=outer&(d<0);pos=outer&(d>0);fit=np.abs(d)<=8
 if raw.shape!=(25,) or not np.isfinite(raw).all() or not np.isfinite(d).all() or neg.sum()!=3 or pos.sum()!=3:raise ValueError('Nonfinite row or fixed three-pixel side geometry differs')
 bgmask=neg if estimator=='negative_side' else pos
 bg=float(np.median(raw[bgmask]));noise=float(1.4826*np.median(np.abs(raw[bgmask]-bg)))
 return d,fit,bgmask,bg,noise,{'negative_outer_median_adu':float(np.median(raw[neg])),'positive_outer_median_adu':float(np.median(raw[pos]))}

def train(raw,centers,training,indices,estimator):
 prepared={};dispositions=[]
 for rr in training:
  k=indices[rr]
  try:
   d,fit,bgm,bg,noise,side=row_geometry(raw[k],centers[k],estimator)
   prof=np.interp(GRID,d,raw[k]-bg);net=float(prof.sum())
   if not math.isfinite(net) or net<=0:raise ValueError('Nonpositive signed training profile sum')
   prepared[rr]=prof/net
   dispositions.append({'relative_raw_row':rr,'status':'USABLE','signed_normalization_adu':net,'background_adu':bg,'background_pixels':int(bgm.sum()),'outer_mad_proxy_adu':noise,**side})
  except ValueError as exc:dispositions.append({'relative_raw_row':rr,'status':'UNUSABLE','reason':str(exc)})
 valid=[r for r in training if r in prepared];details={'declared_rows':232,'valid_rows':len(valid),'minimum_rows':200}
 if len(valid)<200:return None,dispositions,{**details,'status':'BLOCKED_INSUFFICIENT_TRAINING'}
 template=np.median(np.stack([prepared[r] for r in valid]),axis=0);normalization=float(template.sum())
 if not np.isfinite(template).all() or normalization<=0:return None,dispositions,{**details,'status':'BLOCKED_NONPOSITIVE_MEDIAN_TEMPLATE'}
 template=template/normalization
 return template,dispositions,{**details,'status':'USABLE','pre_normalization_signed_sum':normalization,'negative_grid_samples':int((template<0).sum())}

def fit_row(raw,center,template,estimator):
 d,fit,bgm,bg,noise,side=row_geometry(raw,center,estimator);t=np.interp(d[fit],GRID,template);net=float(t.sum())
 if not math.isfinite(net) or net<=0:raise ValueError('Nonpositive evaluated template sum')
 t=t/net;denominator=float(t@t)
 if denominator<=0:raise ValueError('Degenerate evaluated template')
 amplitude=float(t@(raw[fit]-bg)/denominator);model=np.full(25,np.nan);model[fit]=bg+amplitude*t;residual=raw-model
 return d,fit,bgm,model,residual,{'amplitude_adu':amplitude,'background_adu':bg,'outer_mad_proxy_adu':noise,'fit_pixels':int(fit.sum()),'background_pixels':int(bgm.sum()),**side,'fractional_trace_column':float(center-np.rint(center)),'signed_residual_sum_adu':float(np.sum(residual[fit])),'residual_rms_adu':float(np.sqrt(np.mean(residual[fit]**2)))}

# Original window aggregation retained, with only explicit estimator forwarding.
def window_metrics(name,rr,raw,centers,template,indices,estimator):
    models=[];residuals=[];ds=[];fitsmask=[];row_records=[]
    for r in rr:
        k=indices[r];d,mask,bgm,model,residual,record=fit_row(raw[k],centers[k],template,estimator)
        models.append(model);residuals.append(residual);ds.append(d);fitsmask.append(mask)
        row_records.append({'window':name,'relative_raw_row':r,**record})
    residual=np.array(residuals);d=np.array(ds);mask=np.array(fitsmask)
    on=mask&(np.abs(d)<=3);off=mask&(np.abs(d)>3)
    absolute=np.where(mask,np.abs(residual),0);positive=np.where(mask,np.maximum(residual,0),0)
    l1=float(absolute.sum());pos=float(positive.sum());row_offset=np.array(rr)[:,None]-rr[len(rr)//2]
    result={'window':name,'center_relative_raw_row':rr[len(rr)//2],'rows':len(rr),'fit_pixels':int(mask.sum()),'on_trace_pixels':int(on.sum()),'off_trace_pixels':int(off.sum()),'amplitude_sum_adu':sum(x['amplitude_adu']for x in row_records),'median_background_adu':float(np.median([x['background_adu']for x in row_records])),'median_outer_mad_proxy_adu':float(np.median([x['outer_mad_proxy_adu']for x in row_records])),'signed_residual_sum_adu':float(np.nansum(residual)),'residual_l1_adu':l1,'on_trace_residual_l1_adu':float(absolute[on].sum()),'off_trace_residual_l1_adu':float(absolute[off].sum()),'off_trace_l1_fraction':float(absolute[off].sum()/l1)if l1>0 else None,'maximum_pixel_l1_fraction':float(absolute.max()/l1)if l1>0 else None,'l1_centroid_crossdisp_pixels':float((absolute*d).sum()/l1)if l1>0 else None,'l1_centroid_dispersion_pixels':float((absolute*row_offset).sum()/l1)if l1>0 else None,'negative_residual_sum_adu':float(np.where(mask,np.minimum(residual,0),0).sum()),'on_trace_mean_absolute_residual_adu':float(absolute[on].sum()/on.sum()),'off_trace_mean_absolute_residual_adu':float(absolute[off].sum()/off.sum()),'positive_residual_sum_adu':pos,'positive_residual_centroid_crossdisp_pixels':float((positive*d).sum()/pos)if pos>0 else None,'positive_residual_centroid_dispersion_pixels':float((positive*row_offset).sum()/pos)if pos>0 else None,'zero_residual_l1':l1==0,'zero_positive_residual_sum':pos==0}
    return result,row_records,{'raw':raw[[indices[r]for r in rr]],'model':np.array(models),'residual':residual,'true_crossdisp_offsets':d,'fit_mask':mask,'relative_raw_rows':np.array(rr),'trace_columns':centers[[indices[r]for r in rr]]}

def csvwrite(file,rows):
 fields=list(dict.fromkeys(k for r in rows for k in r))
 with file.open('x',newline='') as stream:
  w=csv.DictWriter(stream,fields);w.writeheader();w.writerows(rows)

def maps(rr,raw,centers,cols,indices,estimator):
 ix=[indices[r] for r in rr];d=np.rint(centers[ix])[:,None]+J-centers[ix,None];outer=(np.abs(d)>=9)&(np.abs(d)<=12)
 return {'raw':raw[ix],'true_crossdisp_offsets':d,'fit_mask':np.abs(d)<=8,'background_mask':outer&(d<0 if estimator=='negative_side' else d>0),'negative_background_mask':outer&(d<0),'positive_background_mask':outer&(d>0),'relative_raw_rows':np.array(rr),'absolute_raw_rows':np.array(rr)+3139,'trace_columns':centers[ix],'stitched_columns':cols[ix],'chip2_columns':cols[ix]-2048+50}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');ap.add_argument('--release',type=Path,default=HERE/'ROOT_RELEASE.json');args=ap.parse_args()
 if not args.execute:raise SystemExit('No observational calculation by default; published root release and --execute required.')
 plan,release=validate(args.release);release_hash=sha(args.release);output=HERE/'results'
 if output.exists():raise RuntimeError('Existing attempt is immutable')
 output.mkdir();dump(output/'STARTED.json',{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'release_sha256':release_hash,'plan_sha256':sha(HERE/'PLAN.json'),'new_pixels_requested':0,'input_artifact_sha256':sha(path(plan['selected_pixels_path']))})
 training,windows=coordinates();allrows=sorted(set(training)|set(sum(windows.values(),[])))
 with np.load(path(plan['selected_pixels_path']),allow_pickle=False) as z:
  raw=z['raw_adu'].copy();centers=z['trace_columns'].copy();cols=z['stitched_columns'].copy()
  if not(np.array_equal(z['relative_raw_rows'],allrows) and np.array_equal(z['absolute_raw_rows'],np.array(allrows)+3139) and np.array_equal(z['training_relative_rows'],training) and np.array_equal(z['control_centers'],CENTERS) and np.array_equal(z['chip2_columns'],cols-2048+50)):raise ValueError('Frozen maps/coordinate sets differ')
 if raw.shape!=(331,25) or centers.shape!=(331,) or cols.shape!=(331,25) or not np.array_equal(cols,np.rint(centers).astype(int)[:,None]+J):raise ValueError('Frozen selected footprint differs')
 indices={r:i for i,r in enumerate(allrows)};metrics=[];row_metrics=[];templates={};dispositions={};arrays={};details={}
 for estimator in ESTIMATORS:
  template,disp,detail=train(raw,centers,training,indices,estimator);templates[estimator]=None if template is None else template.tolist();dispositions[estimator]=disp;details[estimator]=detail
  for name,rr in windows.items():
   wa=maps(rr,raw,centers,cols,indices,estimator)
   try:
    if template is None:raise ValueError(detail['status'])
    result,records,measured=window_metrics(name,rr,raw,centers,template,indices,estimator);wa.update(measured)
    metrics.append({'estimator':estimator,'template':'pooled','status':'MEASURED_DESCRIPTIVE',**result})
    row_metrics.extend({'estimator':estimator,'template':'pooled','status':'MEASURED_DESCRIPTIVE',**r} for r in records)
   except ValueError as exc:
    reason=str(exc);metrics.append({'estimator':estimator,'template':'pooled','window':name,'status':'BLOCKED','reason':reason,'center_relative_raw_row':rr[len(rr)//2],'rows':len(rr)})
    row_metrics.extend({'estimator':estimator,'template':'pooled','window':name,'relative_raw_row':r,'status':'BLOCKED','reason':reason} for r in rr)
    wa.update(model=np.full((11,25),np.nan),residual=np.full((11,25),np.nan))
   for key,val in wa.items():arrays[estimator+'__'+name+'__'+key]=val
 assert len(metrics)==18 and len(row_metrics)==198 and all(len(dispositions[e])==232 for e in ESTIMATORS)
 dump(output/'TRAINING_DISPOSITIONS.json',dispositions);dump(output/'TEMPLATES.json',{'grid_true_crossdisp_pixels':GRID.tolist(),'templates':templates,'details':details,'signs_preserved':True})
 dump(output/'WINDOW_METRICS.json',metrics);csvwrite(output/'WINDOW_METRICS.csv',metrics);csvwrite(output/'ROW_METRICS.csv',row_metrics)
 original={r['window']:r for r in read(path(plan['original_window_metrics_path'])) if r['template']=='pooled'}
 comparison=[]
 for r in metrics:
  old=original[r['window']];numeric={k:{'original_pooled_two_sided':v,'one_sided':r.get(k),'difference':r[k]-v if isinstance(r.get(k),(int,float)) and not isinstance(r.get(k),bool) else None} for k,v in old.items() if isinstance(v,(int,float)) and not isinstance(v,bool)}
  comparison.append({'estimator':r['estimator'],'window':r['window'],'status':r['status'],'metrics':numeric})
 dump(output/'ORIGINAL_POOLED_COMPARISON.json',comparison)
 empirical=[]
 for estimator in ESTIMATORS:
  target=next(r for r in metrics if r['estimator']==estimator and r['window']=='TARGET');controls=[next(r for r in metrics if r['estimator']==estimator and r['window']==name) for name in list(windows)[1:]]
  keys=[k for k,v in original['TARGET'].items() if (v is None or isinstance(v,(int,float)) and not isinstance(v,bool)) and k not in {'center_relative_raw_row','rows','fit_pixels','on_trace_pixels','off_trace_pixels'}]
  for key in keys:
   value=target.get(key);context=[{'window':r['window'],'status':r['status'],'value':r.get(key)} for r in controls];valid=[x['value'] for x in context if isinstance(x['value'],(int,float))]
   empirical.append({'estimator':estimator,'metric':key,'target':value,'controls':context,'controls_available':len(valid),'controls_at_least_target':sum(v>=value for v in valid) if isinstance(value,(int,float)) else None,'meaning':'Eight coordinate-selected local controls; descriptive context, no significance or classification.'})
 dump(output/'EMPIRICAL_CONTEXT.json',empirical)
 with (output/'SPATIAL_ARRAYS.npz').open('xb') as f:np.savez_compressed(f,**arrays)
 validate(args.release)
 if sha(args.release)!=release_hash:raise ValueError('Release changed during execution')
 dump(output/'SUMMARY.json',{'status':'COMPLETE_DESCRIPTIVE_BACKGROUND_SENSITIVITY' if all(r['status']=='MEASURED_DESCRIPTIVE' for r in metrics) else 'PARTIAL_OR_BLOCKED_BACKGROUND_SENSITIVITY','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'estimators':list(ESTIMATORS),'background_pixels_per_estimator_per_row':3,'training_rows_per_estimator':232,'templates':details,'window_records':len(metrics),'row_records':len(row_metrics),'held_out_controls_per_estimator':8,'reused_unique_native_pixels':int(raw.size),'new_native_pixels_read':0,'original_results_changed':False,'classification':'U','classification_changed':False,'origin_assignments':0,'plan_sha256':sha(HERE/'PLAN.json'),'script_sha256':sha(Path(__file__)),'release_sha256':release_hash,'limitations':plan['limitations']})
 dump(output/'OUTPUT_HASHES.json',{str(p.relative_to(output)):sha(p) for p in sorted(output.iterdir()) if p.is_file()})
 print(json.dumps(read(output/'SUMMARY.json'),indent=2))
if __name__=='__main__':main()
