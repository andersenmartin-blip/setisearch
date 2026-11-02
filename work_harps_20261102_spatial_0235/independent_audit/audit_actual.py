"""Independent bounded FITS decode and scalar reconstruction after root run.

Uses astropy only to inspect FITS headers/data offsets, then directly decodes
the selected signed16-bit pixels. No production functions are imported.
"""
import argparse
import csv
import datetime
import hashlib
import json
import math
from pathlib import Path
import struct
import numpy as np
from astropy.io import fits
import independent_math as reference

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
ANALYSIS=OUT.parent/'analysis'
RESULT=ANALYSIS/'results'
CHECKS=[]
DIFFERENCES=[]
SCALARS=0

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def ck(test,label):
    if not test:raise AssertionError(label)
    CHECKS.append(label)
def compare(a,b,label,kind='metric'):
    global SCALARS
    if isinstance(b,dict):
        ck(set(a)==set(b),label+' keys')
        for key in b:compare(a[key],b[key],label+'/'+key,kind)
    elif isinstance(b,(str,bool)) or b is None:ck(a==b,label)
    elif isinstance(b,list) and b and isinstance(b[0],dict):
        ck(len(a)==len(b),label+' count')
        for i,(x,y)in enumerate(zip(a,b)):compare(x,y,label+'/'+str(i),kind)
    else:
        aa=np.asarray(a,dtype=float);bb=np.asarray(b,dtype=float)
        ck(aa.shape==bb.shape,label+' shape');SCALARS+=aa.size
        ck(np.allclose(aa,bb,rtol=5e-9,atol=5e-8,equal_nan=True),label)
        valid=np.isfinite(aa)&np.isfinite(bb)
        error=float(np.max(np.abs(aa[valid]-bb[valid])))if valid.any()else 0.
        DIFFERENCES.append(dict(name=label,kind=kind,scalar_values=int(aa.size),maximum_absolute_difference=error))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--authorized-after-root-run',action='store_true');args=parser.parse_args()
    if not args.authorized_after_root_run:raise SystemExit('Root completed-run signal and explicit flag are required before observational pixel interpretation.')
    plan=read(ANALYSIS/'PLAN.json');release=read(ANALYSIS/'ROOT_RELEASE.json');summary=read(RESULT/'SUMMARY.json');hashes=read(RESULT/'OUTPUT_HASHES.json')
    ck(release['schema']=='HARPS_SPATIAL_0235_RELEASE_V1' and release['publication_readback_verified']is True,'Actual released phase')
    ck(release['plan_sha256']==sha(ANALYSIS/'PLAN.json') and release['analysis_script_sha256']==sha(ANALYSIS/'measure_spatial.py'),'Released plan/code exact')
    ck(release['input_inventory_path']==plan['input_inventory_path'] and release['input_inventory_sha256']==sha(ROOT/plan['input_inventory_path']),'Released exact input inventory')
    ck(summary['release_sha256']==sha(ANALYSIS/'ROOT_RELEASE.json'),'Result release binding')
    ck(summary['status']in ['COMPLETE_DESCRIPTIVE_SPATIAL_SUPPORT','PARTIAL_OR_BLOCKED_DESCRIPTIVE_SPATIAL_SUPPORT'],'Terminal descriptive result exists')
    for name,digest in plan['source_hashes'].items():ck(sha(ROOT/name)==digest,'Frozen source '+name)
    for name,digest in hashes.items():ck(sha(RESULT/name)==digest,'Production output '+name)
    rawpath=ROOT/plan['raw_path'];ck(sha(rawpath)==plan['raw_sha256'],'Exact original raw bytes')
    initial_bindings={str(p.relative_to(ROOT)):sha(p)for p in [ANALYSIS/'PLAN.json',ANALYSIS/'ROOT_RELEASE.json',RESULT/'OUTPUT_HASHES.json',OUT/'independent_math.py']}
    training,windows=reference.partition();allrows=sorted(set(training)|set(sum(windows.values(),[])))
    absolute_rows=[3139+r for r in allrows]
    coefs=plan['trace_coefficients_ascending']
    # Direct scalar polynomial sum independently evaluates the fixed header trace.
    centers={r:math.fsum(c*(3139+r)**i for i,c in enumerate(coefs))for r in allrows}
    columns={r:list(range(round(centers[r])-12,round(centers[r])+13))for r in allrows}
    ck(len(allrows)==331 and len(training)==232,'Exact declared rows before pixel reads')
    with fits.open(rawpath,memmap=False,lazy_load_hdus=False,do_not_scale_image_data=True)as hd:
        primary=hd[0].header;header=hd[2].header.copy();offset=hd[2].fileinfo()['datLoc']
        ck(primary['ARCFILE']=='HARPS.2023-02-22T07:40:53.531.fits' and primary['INSTRUME']=='HARPS','Independent raw identity headers')
        ck(header['BITPIX']==16 and header['NAXIS1']==2148 and header['NAXIS2']==4096,'Independent decoder exact raw representation')
    bscale=header.get('BSCALE',1);bzero=header.get('BZERO',0);blank=header.get('BLANK')
    strips={}
    with rawpath.open('rb')as stream:
        for row in allrows:
            chipcol=columns[row][0]-2048+50
            ck(50<=chipcol and chipcol+25<=2098,'Selected strip on chip2 '+str(row))
            stream.seek(offset+2*((3139+row)*2148+chipcol));encoded=stream.read(50)
            ck(len(encoded)==50,'Exact25-pixel decode '+str(row))
            stored=struct.unpack('>25h',encoded)
            strips[row]=[math.nan if blank is not None and x==blank else float(x)*bscale+bzero for x in stored]
    selected={'raw_adu':[strips[r]for r in allrows],'relative_raw_rows':allrows,'absolute_raw_rows':absolute_rows,'stitched_columns':[columns[r]for r in allrows],'chip2_columns':[[x-2048+50 for x in columns[r]]for r in allrows],'trace_columns':[centers[r]for r in allrows],'training_relative_rows':training,'control_centers':reference.CONTROL_CENTERS}
    with np.load(RESULT/'SELECTED_NATIVE_PIXELS.npz',allow_pickle=False)as saved:
        ck(set(saved.files)==set(selected),'Exact persisted selected-array keys')
        for name,want in selected.items():
            compare(saved[name],want,'Selected '+name,'selected_coordinates'if name!='raw_adu'else'raw_pixels')
        ck(np.array_equal(saved['raw_adu'],selected['raw_adu'],equal_nan=True),'All8275 decoded native pixels exactly match saved values')
    templates,dispositions,details=reference.templates(strips,centers,training)
    recorded_dispositions=read(RESULT/'TRAINING_DISPOSITIONS.json')
    ck(len(recorded_dispositions)==232,'Every training row retained')
    # Failure reasons are prose; independently require disposition and explanation.
    for actual,expected in zip(recorded_dispositions,dispositions):
        if expected['status']=='UNUSABLE':
            ck(actual['relative_raw_row']==expected['relative_raw_row'] and actual['status']=='UNUSABLE' and bool(actual.get('reason')),'Unusable training row '+str(expected['relative_raw_row']))
        else:compare(actual,expected,'Training '+str(expected['relative_raw_row']),'training')
    template_file=read(RESULT/'TEMPLATES.json')
    compare(template_file['templates'],templates,'Templates','template')
    compare(template_file['details'],details,'Template support','template')
    ck(template_file['signs_preserved']is True and template_file['grid_true_crossdisp_pixels']==reference.GRID,'Signed fixed template grid')
    expected_metrics=[];expected_rows=[]
    expected_arrays={'all_relative_raw_rows':allrows,'all_trace_columns':[centers[r]for r in allrows],'all_native_raw_pixels':[strips[r]for r in allrows],'all_native_stitched_columns':[columns[r]for r in allrows]}
    for template_name in ['pooled','negative_raw_flank','positive_raw_flank']:
        for name,rr in windows.items():
            try:
                if template_name not in templates:raise ValueError(details[template_name]['status'])
                metrics,rows,arrays=reference.window(name,rr,strips,centers,templates[template_name])
            except ValueError as error:
                expected_metrics.append(dict(template=template_name,window=name,status='BLOCKED',reason=str(error),center_relative_raw_row=rr[len(rr)//2],rows=len(rr)))
                continue
            expected_metrics.append(dict(template=template_name,status='MEASURED_DESCRIPTIVE',**metrics))
            expected_rows.extend(dict(template=template_name,**row)for row in rows)
            derived={'raw':[strips[r]for r in rr],'model':[a[2]for a in arrays],'residual':[a[3]for a in arrays],
                     'true_crossdisp_offsets':[a[0]for a in arrays],
                     'fit_mask':[[i in a[1]for i in range(25)]for a in arrays],
                     'relative_raw_rows':rr,'trace_columns':[centers[r]for r in rr]}
            for key,value in derived.items():expected_arrays[template_name+'__'+name+'__'+key]=value
    recorded_metrics=read(RESULT/'WINDOW_METRICS.json');ck(len(recorded_metrics)==27,'Every template/window slot retained')
    for actual,expected in zip(recorded_metrics,expected_metrics):
        if expected['status']=='BLOCKED':
            ck(all(actual[k]==expected[k]for k in expected if k!='reason')and bool(actual.get('reason')),'Explicit blocked window '+expected['template']+expected['window'])
        else:compare(actual,expected,'Window '+expected['template']+'/'+expected['window'],'window_metric')
    with (RESULT/'ROW_METRICS.csv').open(newline='')as stream:recorded_rows=list(csv.DictReader(stream))
    ck(len(recorded_rows)==len(expected_rows),'All successful row fits represented')
    for actual,expected in zip(recorded_rows,expected_rows):
        ck(set(actual)==set(expected),'Row metric schema')
        compare({k:actual[k]if isinstance(v,str)else float(actual[k])for k,v in expected.items()},expected,'Row '+expected['template']+'/'+expected['window']+'/'+str(expected['relative_raw_row']),'row_metric')
    with np.load(RESULT/'SPATIAL_ARRAYS.npz',allow_pickle=False)as saved:
        ck(set(saved.files)==set(expected_arrays),'Every saved spatial array accounted for')
        for name,want in expected_arrays.items():compare(saved[name],want,'Array '+name,'array_'+name.split('__')[-1])
    empirical=[]
    for template_name in ['pooled','negative_raw_flank','positive_raw_flank']:
        target=next(r for r in expected_metrics if r['template']==template_name and r['window']=='TARGET')
        controls=[r for r in expected_metrics if r['template']==template_name and r['window']!='TARGET'and r['status']=='MEASURED_DESCRIPTIVE']
        for key in ['off_trace_l1_fraction','maximum_pixel_l1_fraction','residual_l1_adu','positive_residual_sum_adu']:
            values=[r[key]for r in controls if r.get(key)is not None];value=target.get(key)
            empirical.append(dict(template=template_name,metric=key,target=value,control_values=values,controls_available=len(values),controls_at_least_target=sum(v>=value for v in values)if value is not None else None,meaning='Coordinate-selected local empirical context only; not a probability, significance, photon fraction or classifier.'))
    compare(read(RESULT/'EMPIRICAL_CONTEXT.json'),empirical,'Empirical context','empirical')
    ck(summary['event']=='V2E2-0235'and summary['original_classification']=='U'and summary['classification_changed']is False and summary['origin_assignments']==0,'U preserved without origin assignment')
    ck(summary['training_rows_declared']==232 and summary['held_out_controls']==8 and summary['target_rows']==11 and summary['observed_native_pixels']==8275 and summary['all_template_window_records']==27,'Exact summary coverage')
    ck(summary['templates_reported']==list(templates)and summary['blocked_window_records']==sum(r['status']=='BLOCKED'for r in expected_metrics),'Summary template/blocked accounting')
    compare(summary['training_dispositions'],{s:sum(r['status']==s for r in dispositions)for s in ['USABLE','UNUSABLE']},'Training summary')
    for name,digest in plan['source_hashes'].items():ck(sha(ROOT/name)==digest,'Frozen sources unchanged '+name)
    for name,digest in hashes.items():ck(sha(RESULT/name)==digest,'Production output unchanged '+name)
    for name,digest in initial_bindings.items():ck(sha(ROOT/name)==digest,'Audit binding unchanged '+name)
    maxima={kind:max(r['maximum_absolute_difference']for r in DIFFERENCES if r['kind']==kind)for kind in sorted({r['kind']for r in DIFFERENCES})}
    report={'status':'PASS_INDEPENDENT_BOUNDED_NUMERICAL_RECONSTRUCTION','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks_passed':len(CHECKS),'scalar_values_compared':SCALARS,'check_labels':CHECKS,'raw_pixels_independently_decoded':8275,'raw_rows_read':331,'training_rows_reconstructed':232,'template_window_slots_reconstructed':27,'successful_row_fits_reconstructed':len(expected_rows),'templates_reconstructed':list(templates),'blocked_windows':summary['blocked_window_records'],'original_classification':'U','classification_changed':False,'production_functions_imported':False,'network_requests':0,'prior_scientific_results_recomputed':False,'raw_decode':{'hdu':2,'bitpix':16,'naxis1':2148,'naxis2':4096,'bscale':bscale,'bzero':bzero,'blank':blank,'method':'Direct big-endian signed16-bit byte decode of only the same331×25 prescribed pixels; FITS headers used for offset and scaling.'},'maximum_absolute_differences_by_kind':maxima,'source_hashes':initial_bindings,'audit_script_sha256':sha(Path(__file__)),'limitations':['Independent arithmetic/provenance check only; residual fractions and control counts have no calibrated probability or physical-origin meaning.','All observations are the same existing discovery raw exposure; this audit does not create an independent detection, noise calibration or classifier.']}
    with (OUT/'NUMERICAL_AUDIT.json').open('x')as file:json.dump(report,file,indent=2);file.write('\n')
    with (OUT/'NUMERICAL_DIFFERENCES.csv').open('x',newline='')as file:
        writer=csv.DictWriter(file,fieldnames=['name','kind','scalar_values','maximum_absolute_difference']);writer.writeheader();writer.writerows(DIFFERENCES)
    print(json.dumps({k:v for k,v in report.items()if k not in ['check_labels','source_hashes']},indent=2))

if __name__=='__main__':main()
