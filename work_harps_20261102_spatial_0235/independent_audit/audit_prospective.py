"""Metadata/source and synthetic-only preflight. No observational arrays read."""
import contextlib
import datetime
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
import numpy as np
import independent_math as reference

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
ANALYSIS = OUT.parent/'analysis'
CHECKS = []
SCALARS = 0

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def ck(test, label):
    if not test: raise AssertionError(label)
    CHECKS.append(label)
def compare(a, b, label):
    global SCALARS
    if isinstance(a, dict):
        ck(set(a)==set(b), label+' keys')
        for key in a: compare(a[key], b[key], label+'/'+key)
    elif isinstance(a, (str, bool)) or a is None:
        ck(a==b, label)
    elif isinstance(a, (list, tuple)) and a and isinstance(a[0], dict):
        ck(len(a)==len(b), label+' length')
        for i,(x,y) in enumerate(zip(a,b)): compare(x,y,label+'/'+str(i))
    else:
        aa=np.asarray(a,dtype=float);bb=np.asarray(b,dtype=float)
        ck(aa.shape==bb.shape and np.allclose(aa,bb,rtol=2e-10,atol=2e-10,equal_nan=True),label)
        SCALARS+=aa.size

def main():
    plan=read(ANALYSIS/'PLAN.json')
    for rel,digest in plan['source_hashes'].items(): ck(sha(ROOT/rel)==digest,'Frozen source '+rel)
    spec=importlib.util.spec_from_file_location('spatial_production_for_synthetic_only',ANALYSIS/'measure_spatial.py')
    production=importlib.util.module_from_spec(spec);spec.loader.exec_module(production)
    training,windows=reference.partition()
    ck(production.coordinates()==(training,windows),'Independently reconstructed exact partition')
    held=set(sum(list(windows.values())[1:],[]));flanks=set(range(-280,-80))|set(range(81,281))
    ck(len(training)==232 and len(held)==88 and len(flanks-set(training)-held)==80,'232 training /88 controls /80 unread buffers')
    ck(not(set(training)&held) and all(abs(r-c)>10 for r in training for c in reference.CONTROL_CENTERS),'No template/control/background-row leakage')
    allrows=sorted(set(training)|set(sum(windows.values(),[])));indices={r:i for i,r in enumerate(allrows)}
    ck(len(allrows)==331,'Exactly8275 selected native pixels')
    native_union={4095-(956+x)-3139 for x in flanks}
    ck(native_union==flanks,'Native/raw flank union exactly preserved')
    ck(plan['event']=='V2E2-0235' and plan['native_order']==50 and plan['native_pixel']==956 and plan['raw_center_row']==3139,'Exact inherited identity and row')
    ck(plan['orientation']==dict(row_flip=True,column_flip=False,argument_flip=True),'Inherited orientation unchanged')
    trace=read(OUT.parent/'inputs/TRACE_METADATA.json')
    ck(plan['trace_coefficients_ascending']==trace['trace_polynomial_coefficients_ascending'],'Header-only polynomial coefficients unchanged')
    # These arrays are invented, analytic synthetic fixtures, not observations.
    centers={r:2300.23+0.0007*r for r in allrows}
    strips={r:[40+0.01*r+250*math.exp(-0.5*((round(centers[r])+j-centers[r])/1.45)**2)
                   -2*math.exp(-0.5*((abs(round(centers[r])+j-centers[r])-6)/0.65)**2)
                   +0.3*math.sin(r+j) for j in range(-12,13)] for r in allrows}
    # Add both positive and negative localized model discrepancies to target.
    strips[0][17]+=35;strips[1][8]-=11
    raw=np.array([strips[r]for r in allrows]);cc=np.array([centers[r]for r in allrows])
    actual_t,actual_disp,actual_details=production.train(raw,cc,training,indices)
    want_t,want_disp,want_details=reference.templates(strips,centers,training)
    compare(actual_t,want_t,'Synthetic signed templates');compare(actual_disp,want_disp,'All synthetic training dispositions');compare(actual_details,want_details,'Template support details')
    ck(any(v['negative_grid_samples']>0 for v in actual_details.values()),'Negative template wings remain signed')
    for template_name in want_t:
        for name,rr in windows.items():
            metric,rows,arrays=production.window_metrics(name,rr,raw,cc,actual_t[template_name],indices)
            expected,row_expected,array_expected=reference.window(name,rr,strips,centers,want_t[template_name])
            compare(metric,expected,'Synthetic window '+template_name+'/'+name)
            compare(rows,row_expected,'Synthetic row fits '+template_name+'/'+name)
            compare(arrays['model'],[a[2]for a in array_expected],'Synthetic model '+template_name+'/'+name)
            compare(arrays['residual'],[a[3]for a in array_expected],'Synthetic residual '+template_name+'/'+name)
    # Exact-zero and signed-amplitude boundaries at an integer trace location.
    delta=np.zeros(17);delta[8]=1
    for amplitude in [0.,-5.,7.]:
        row=np.full(25,20.);row[12]+=amplitude
        _,_,_,_,_,got=production.fit_row(row,2300.,delta)
        compare(got['amplitude_adu'],amplitude,'Unconstrained signed amplitude '+str(amplitude))
    zero_raw=np.full((11,25),20.);zero_centers=np.full(11,2300.)
    metric,_,_=production.window_metrics('TARGET',list(range(-5,6)),zero_raw,zero_centers,delta,{r:r+5 for r in range(-5,6)})
    ck(metric['zero_residual_l1'] and metric['off_trace_l1_fraction']is None and metric['zero_positive_residual_sum'],'Exact-zero fractions explicitly null')
    ck(production.row_geometry(np.ones(25),2300.)[2].sum()==8 and production.row_geometry(np.ones(25),2300.23)[2].sum()==6,'Fractional background support counts')
    # Isolated execution uses fake FITS section values only; never real raw data.
    class Hdu:
        def __init__(self,header,section=None): self.header=header;self.section=section
    class FakeFits:
        def __init__(self,mode): self.mode=mode
        def __enter__(self): return [Hdu({'ARCFILE':'HARPS.2023-02-22T07:40:53.531.fits'}),Hdu({}),Hdu({'NAXIS2':4096},self)]
        def __exit__(self,*args): return False
        def __getitem__(self,key):
            row=key[0].start-3139
            if self.mode=='all_blocked': return np.full((1,25),20.)
            if self.mode=='target_blocked' and row==0: return np.full((1,25),np.nan)
            d=np.arange(-12,13,dtype=float)
            return (20+50*np.exp(-0.5*(d/1.4)**2)+0.1*np.sin(d+row))[None,:]
    with tempfile.TemporaryDirectory(prefix='spatial_synthetic_',dir=OUT)as temporary:
        tmp=Path(temporary);(tmp/'raw.bin').write_bytes(b'SYNTHETIC, NOT FITS');(tmp/'inventory.json').write_text('{}')
        fake_plan=dict(plan,source_hashes={'inventory.json':sha(tmp/'inventory.json')},raw_path='raw.bin',raw_sha256=sha(tmp/'raw.bin'),input_inventory_path='inventory.json')
        (tmp/'PLAN.json').write_text(json.dumps(fake_plan));release={'schema':'HARPS_SPATIAL_0235_RELEASE_V1','publication_readback_verified':True,'publication_commit':'a'*40,'plan_sha256':sha(tmp/'PLAN.json'),'analysis_script_sha256':sha(ANALYSIS/'measure_spatial.py'),'input_inventory_path':'inventory.json','input_inventory_sha256':sha(tmp/'inventory.json')}
        rp=tmp/'release.json';rp.write_text(json.dumps(release))
        with patch.object(production,'HERE',tmp),patch.object(production,'REPO',tmp):
            production.validate(rp);ck(True,'Valid synthetic release accepted')
            for field,bad in [('schema','BAD'),('publication_readback_verified',False),('publication_commit','x'),('plan_sha256','0'*64),('analysis_script_sha256','0'*64),('input_inventory_path','wrong'),('input_inventory_sha256','0'*64)]:
                rp.write_text(json.dumps(dict(release,**{field:bad})))
                try: production.validate(rp)
                except ValueError: ck(True,'Rejected release '+field)
                else: raise AssertionError('Accepted invalid '+field)
            rp.write_text(json.dumps(release))
            for mode,blocked in [('valid',0),('target_blocked',3),('all_blocked',27)]:
                with patch.object(production.fits,'open',return_value=FakeFits(mode)),patch.object(sys,'argv',['measure','--release',str(rp)]),contextlib.redirect_stdout(io.StringIO()): production.main()
                result=read(tmp/'results/SUMMARY.json');metrics=read(tmp/'results/WINDOW_METRICS.json');dispositions=read(tmp/'results/TRAINING_DISPOSITIONS.json')
                ck(len(metrics)==27 and result['blocked_window_records']==blocked,'All27 explicit slots '+mode)
                ck(len(dispositions)==232,'Every training disposition persisted '+mode)
                ck((tmp/'results/SELECTED_NATIVE_PIXELS.npz').is_file(),'Bounded input strips retained '+mode)
                ck(result['original_classification']=='U' and result['classification_changed']is False and result['origin_assignments']==0,'No classifier '+mode)
                with patch.object(production.fits,'open',side_effect=AssertionError('Array access before one-shot guard')),patch.object(sys,'argv',['measure','--release',str(rp)]):
                    try: production.main()
                    except RuntimeError: ck(True,'Existing results refused before data '+mode)
                    else: raise AssertionError('Existing results overwritten')
                (tmp/'results').rename(tmp/('finished_'+mode))
    for rel,digest in plan['source_hashes'].items(): ck(sha(ROOT/rel)==digest,'Sources unchanged after synthetic audit '+rel)
    report={'status':'PASS_PROSPECTIVE_METHOD_AND_SYNTHETIC_AUDIT','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks_passed':len(CHECKS),'synthetic_scalar_values_compared':SCALARS,'check_labels':CHECKS,'plan_sha256':sha(ANALYSIS/'PLAN.json'),'analysis_script_sha256':sha(ANALYSIS/'measure_spatial.py'),'independent_math_sha256':sha(OUT/'independent_math.py'),'audit_script_sha256':sha(Path(__file__)),'source_hashes_verified':len(plan['source_hashes']),'observational_array_values_read':0,'network_requests':0,'method_findings':['Inherited zero-based orientation, polynomial and exact8275-pixel footprint preserved.','232 template rows,88 held-out control rows and80 unread buffers are disjoint, including background columns.','Signed training profiles and fitted amplitudes are retained; all27 template/window outcomes remain explicit, including blocked cases.','L1/positive residual metrics and local empirical control counts are descriptive, not significance or physical-origin classifiers.'],'limitations':['Actual raw-array reconstruction awaits parent release and completed production run.','No gain/noise calibration, neighboring-fiber wing exclusion, physical-origin identification or validation of a cosmic-ray classifier is implied.']}
    with (OUT/'PROSPECTIVE_AUDIT.json').open('x')as f: json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in report.items()if k!='check_labels'},indent=2))

if __name__=='__main__': main()
