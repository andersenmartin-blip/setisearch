#!/usr/bin/env python3
"""One-shot, release-guarded spatial diagnostic; never acquires data or classifies."""
import argparse,csv,datetime,hashlib,json,math,re
from pathlib import Path
import numpy as np
from astropy.io import fits
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
J=np.arange(-12,13)
GRID=np.arange(-8,9,dtype=float)
CENTERS=[-255,-205,-155,-105,106,156,206,256]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def dump(p,x):
    with p.open('x')as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n')
def path(relative):
    p=(REPO/relative).resolve()
    if not p.is_relative_to(REPO.resolve()):raise ValueError('Outside repository')
    return p

def coordinates():
    flank=set(range(-280,-80))|set(range(81,281))
    controls={f'C{i+1:02d}':list(range(c-5,c+6))for i,c in enumerate(CENTERS)}
    withheld={r for c in CENTERS for r in range(c-10,c+11)}
    training=sorted(flank-withheld)
    windows={'TARGET':list(range(-5,6)),**controls}
    assert len(training)==232 and len(set(training)&set(sum(windows.values(),[])))==0
    return training,windows

def validate(release_path):
    p=read(HERE/'PLAN.json');r=read(release_path)
    if r.get('schema')!='HARPS_SPATIAL_0235_RELEASE_V1':raise ValueError('Wrong release schema')
    if r.get('publication_readback_verified')is not True or not re.fullmatch('[0-9a-f]{40}',r.get('publication_commit','')):raise ValueError('Verified public freeze required')
    if r.get('plan_sha256')!=sha(HERE/'PLAN.json')or r.get('analysis_script_sha256')!=sha(Path(__file__)):raise ValueError('Method changed')
    if r.get('input_inventory_path')!=p['input_inventory_path']or r.get('input_inventory_sha256')!=p['source_hashes'][p['input_inventory_path']]:raise ValueError('Input inventory release mismatch')
    for f,h in p['source_hashes'].items():
        if sha(path(f))!=h:raise ValueError('Frozen source changed: '+f)
    if sha(path(p['raw_path']))!=p['raw_sha256']:raise ValueError('Raw bytes changed')
    return p,r

def row_geometry(raw,center):
    d=np.rint(center)+J-center
    finite=np.isfinite(raw)
    bgmask=(np.abs(d)>=9)&(np.abs(d)<=12)
    fitmask=np.abs(d)<=8
    if not finite.all()or bgmask.sum()<6:raise ValueError('Nonfinite native row or insufficient background pixels')
    bg=float(np.median(raw[bgmask]));noise=float(1.4826*np.median(np.abs(raw[bgmask]-bg)))
    return d,fitmask,bgmask,bg,noise

def train(raw,centers,training,indices):
    prepared={};dispositions=[]
    for rr in training:
        k=indices[rr]
        try:
            d,fit,bgm,bg,noise=row_geometry(raw[k],centers[k])
            prof=np.interp(GRID,d,raw[k]-bg)
            net=float(prof.sum())
            if not math.isfinite(net)or net<=0:raise ValueError('Nonpositive signed training profile sum')
            prepared[rr]=prof/net
            dispositions.append({'relative_raw_row':rr,'status':'USABLE','signed_normalization_adu':net,'background_adu':bg,'background_pixels':int(bgm.sum()),'negative_outer_median_adu':float(np.median(raw[k][bgm&(d<0)])),'positive_outer_median_adu':float(np.median(raw[k][bgm&(d>0)]))})
        except ValueError as e:dispositions.append({'relative_raw_row':rr,'status':'UNUSABLE','reason':str(e)})
    templates={};details={}
    for name,subset,minimum in [('pooled',training,200),('negative_raw_flank',[x for x in training if x<0],100),('positive_raw_flank',[x for x in training if x>0],100)]:
        valid=[x for x in subset if x in prepared]
        details[name]={'declared_rows':len(subset),'valid_rows':len(valid),'minimum_rows':minimum}
        if len(valid)<minimum:
            details[name]['status']='BLOCKED_INSUFFICIENT_TRAINING';continue
        t=np.median(np.stack([prepared[x]for x in valid]),axis=0)
        normalization=float(t.sum())
        if not np.isfinite(t).all()or normalization<=0:
            details[name]['status']='BLOCKED_NONPOSITIVE_MEDIAN_TEMPLATE';continue
        templates[name]=t/normalization
        details[name]['status']='USABLE'
        details[name]['pre_normalization_signed_sum']=normalization
        details[name]['negative_grid_samples']=int((templates[name]<0).sum())
    return templates,dispositions,details

def fit_row(raw,center,template):
    d,fit,bgm,bg,noise=row_geometry(raw,center)
    t=np.interp(d[fit],GRID,template)
    net=float(t.sum())
    if not math.isfinite(net)or net<=0:raise ValueError('Nonpositive evaluated template sum')
    t=t/net
    denominator=float(t@t)
    if denominator<=0:raise ValueError('Degenerate evaluated template')
    amplitude=float(t@(raw[fit]-bg)/denominator)
    model=np.full(25,np.nan);model[fit]=bg+amplitude*t
    residual=raw-model
    return d,fit,bgm,model,residual,{'amplitude_adu':amplitude,'background_adu':bg,'outer_mad_proxy_adu':noise,'fit_pixels':int(fit.sum()),'background_pixels':int(bgm.sum()),'negative_outer_median_adu':float(np.median(raw[bgm&(d<0)])),'positive_outer_median_adu':float(np.median(raw[bgm&(d>0)])),'fractional_trace_column':float(center-np.rint(center)),'signed_residual_sum_adu':float(np.sum(residual[fit])),'residual_rms_adu':float(np.sqrt(np.mean(residual[fit]**2)))}

def window_metrics(name,rr,raw,centers,template,indices):
    models=[];residuals=[];ds=[];fitsmask=[];row_records=[]
    for r in rr:
        k=indices[r];d,mask,bgm,model,residual,record=fit_row(raw[k],centers[k],template)
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
    with file.open('x',newline='')as stream:
        w=csv.DictWriter(stream,fields);w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--release',type=Path,default=HERE/'ROOT_RELEASE.json');args=ap.parse_args()
    plan,release=validate(args.release);release_hash=sha(args.release)
    training,windows=coordinates();allrows=sorted(set(training)|set(sum(windows.values(),[])))
    assert len(allrows)==331
    absolute_rows=np.array(allrows)+3139
    centers=np.polynomial.polynomial.polyval(absolute_rows,plan['trace_coefficients_ascending'])
    if abs(np.polynomial.polynomial.polyval(3139,plan['trace_coefficients_ascending'])-2323.7701943175816)>1e-8:raise ValueError('Trace location changed')
    cols=np.rint(centers).astype(int)[:,None]+J
    if not((cols>=2048)&(cols<4096)).all():raise ValueError('Frozen window no longer entirely on chip2')
    output=HERE/'results'
    if output.exists():raise RuntimeError('Existing result attempt is immutable')
    output.mkdir();dump(output/'STARTED.json',{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'release_sha256':release_hash,'new_array_values_read':False,'phase':'POST_HOC_SPATIAL_SUPPORT_DIAGNOSTIC'})
    # Only the 331 predeclared row strips are interpreted; all values stay native.
    with fits.open(path(plan['raw_path']),memmap=False,lazy_load_hdus=False)as hd:
        if hd[0].header.get('ARCFILE','').removesuffix('.fits')!='HARPS.2023-02-22T07:40:53.531':raise ValueError('Wrong raw exposure')
        if hd[2].header.get('NAXIS2')!=4096:raise ValueError('Wrong raw row dimension')
        raw=np.stack([np.asarray(hd[2].section[int(y):int(y)+1,int(x[0]-2048+50):int(x[-1]-2048+51)],dtype=float)[0]for y,x in zip(absolute_rows,cols)])
    if raw.shape!=(331,25):raise ValueError('Wrong declared pixel footprint')
    with(output/'SELECTED_NATIVE_PIXELS.npz').open('xb')as f:
        np.savez_compressed(f,raw_adu=raw,relative_raw_rows=np.array(allrows),absolute_raw_rows=absolute_rows,stitched_columns=cols,chip2_columns=cols-2048+50,trace_columns=centers,training_relative_rows=np.array(training),control_centers=np.array(CENTERS))
    indices={r:i for i,r in enumerate(allrows)}
    templates,dispositions,template_details=train(raw,centers,training,indices)
    dump(output/'TRAINING_DISPOSITIONS.json',dispositions)
    dump(output/'TEMPLATES.json',{'grid_true_crossdisp_pixels':GRID.tolist(),'templates':{k:v.tolist()for k,v in templates.items()},'details':template_details,'signs_preserved':True})
    metrics=[];row_metrics=[];arrays={'all_relative_raw_rows':np.array(allrows),'all_trace_columns':centers,'all_native_raw_pixels':raw,'all_native_stitched_columns':cols}
    for template_name in ['pooled','negative_raw_flank','positive_raw_flank']:
        for name,rr in windows.items():
            try:
                if template_name not in templates:raise ValueError(template_details[template_name]['status'])
                result,records,window_arrays=window_metrics(name,rr,raw,centers,templates[template_name],indices)
            except ValueError as exc:
                metrics.append({'template':template_name,'window':name,'status':'BLOCKED','reason':str(exc),'center_relative_raw_row':rr[len(rr)//2],'rows':len(rr)})
                continue
            metrics.append({'template':template_name,'status':'MEASURED_DESCRIPTIVE',**result})
            row_metrics.extend({'template':template_name,**x}for x in records)
            for key,val in window_arrays.items():arrays[template_name+'__'+name+'__'+key]=val
    dump(output/'WINDOW_METRICS.json',metrics);csvwrite(output/'WINDOW_METRICS.csv',metrics);csvwrite(output/'ROW_METRICS.csv',row_metrics)
    empirical=[]
    for name in ['pooled','negative_raw_flank','positive_raw_flank']:
        target=next(r for r in metrics if r['template']==name and r['window']=='TARGET');controls=[r for r in metrics if r['template']==name and r['window']!='TARGET'and r['status']=='MEASURED_DESCRIPTIVE']
        for key in ['off_trace_l1_fraction','maximum_pixel_l1_fraction','residual_l1_adu','positive_residual_sum_adu']:
            values=[r[key]for r in controls if r.get(key)is not None];value=target.get(key)
            empirical.append({'template':name,'metric':key,'target':value,'control_values':values,'controls_available':len(values),'controls_at_least_target':sum(v>=value for v in values)if value is not None else None,'meaning':'Coordinate-selected local empirical context only; not a probability, significance, photon fraction or classifier.'})
    dump(output/'EMPIRICAL_CONTEXT.json',empirical)
    with(output/'SPATIAL_ARRAYS.npz').open('xb')as f:np.savez_compressed(f,**arrays)
    validate(args.release)
    if sha(args.release)!=release_hash:raise ValueError('Release changed during analysis')
    dump(output/'SUMMARY.json',{'status':'COMPLETE_DESCRIPTIVE_SPATIAL_SUPPORT'if all(r['status']=='MEASURED_DESCRIPTIVE'for r in metrics)else'PARTIAL_OR_BLOCKED_DESCRIPTIVE_SPATIAL_SUPPORT','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'event':'V2E2-0235','original_classification':'U','classification_changed':False,'origin_assignments':0,'training_rows_declared':232,'training_dispositions':{s:sum(r['status']==s for r in dispositions)for s in ['USABLE','UNUSABLE']},'held_out_controls':8,'target_rows':11,'observed_native_pixels':int(raw.size),'templates_reported':list(templates),'all_template_window_records':len(metrics),'blocked_window_records':sum(r['status']=='BLOCKED'for r in metrics),'old_results_recomputed':False,'plan_sha256':sha(HERE/'PLAN.json'),'script_sha256':sha(Path(__file__)),'release_sha256':release_hash,'limitations':plan['limitations']})
    dump(output/'OUTPUT_HASHES.json',{str(p.relative_to(output)):sha(p)for p in sorted(output.iterdir())if p.is_file()})
    print(json.dumps(read(output/'SUMMARY.json'),indent=2))

if __name__=='__main__':main()
