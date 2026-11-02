#!/usr/bin/env python3
"""Compact synthetic-only checks; never open observational arrays."""
from pathlib import Path
import ast,hashlib,importlib.util,json,math
import numpy as np
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
def module(p):
    spec=importlib.util.spec_from_file_location('c002_synthetic_target',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=module(HERE/'compare_group.py');checks=[]
def check(test,label):
    if not test:raise AssertionError(label)
    checks.append(label)
def funcs(p):return{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef)}
a=funcs(HERE/'compare_group.py');b=funcs(REPO/'work_harps_20261102_c004_context/analysis/compare_group.py')
for name in ['sampling_parameters','profile','comparison']:check(a[name]==b[name],name+' function unchanged from C004')
check(int(m.CORE.sum())==51 and int(m.BROAD.sum())==550,'51 core / 550 surrounding centers')
check(len(m.EVENTS)==1 and len(m.REFERENCES)==1,'One record / one fixed reference product')
check(m.COVERING_ORDERS=={'ADP.2022-05-08T01:01:37.876':[2,3]},'Both native covering orders retained')
check(m.ANCHOR_BERV==-18.8907517532076 and m.REFERENCES[0]=='ADP.2022-05-08T01:01:37.876','C002 discovery is May 2022; no March or January anchor inheritance')
w=m.CB+np.arange(-700,701)/100;f=200+15*np.sin(np.arange(len(w))*.1);e=np.full(len(w),np.nan)
for berv in [30.3750612537025,-29.2347518620376]:
    for frame in m.FRAMES:
        p,q=m.profile(w,f,e,berv,frame,.01)
        check(q['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE' and q['raw_grid_finite_samples']==601,'Full positive synthetic '+str(berv)+' '+frame)
        p2,q2=m.profile(w,7*f,e,berv,frame,.01)
        check(np.allclose(p['normalized_flux'],p2['normalized_flux'],rtol=1e-13,atol=1e-13),'Positive scaling invariance '+str(berv)+' '+frame)
        for mask,minimum in [(m.CORE,41),(m.BROAD,440)]:
            c=m.comparison(p,p,mask);check(c['minimum_common_samples']==minimum and abs(c['raw_pearson']-1)<1e-14 and c['normalized_rms']==0,'Self support Pearson RMS '+str(berv)+' '+frame+' '+str(minimum))
    center,scale=m.sampling_parameters(berv,'topocentric');check(center==m.CT and np.allclose((center+m.X)*scale/(1+berv/m.C),m.CT+m.X,rtol=0,atol=1e-12),'One native topocentric anchor '+str(berv))
wshort=m.CB+np.arange(-300,101)/100;p,q=m.profile(wshort,np.ones(len(wshort))*10,np.full(len(wshort),np.nan),m.ANCHOR_BERV,'barycentric',.01)
check(q['normalization_status']=='RAW_ONLY' and 'MISSING_RIGHT_FLANK_COVERAGE'in q['normalization_reasons'] and np.isfinite(p['signed_raw_flux'][m.CORE]).all(),'Missing right flank remains raw-only with core support')
wpartial=m.CB+np.arange(-300,117)/100
fpartial=10+np.sin(np.arange(len(wpartial))*.1)
p,q=m.profile(wpartial,fpartial,np.full(len(wpartial),np.nan),m.ANCHOR_BERV,'barycentric',.01)
check(q['raw_grid_finite_samples']==417 and q['normalized_grid_finite_samples']==0 and q['right_flank_native_samples']==0,'Synthetic order 2 endpoint preserves 417 raw samples and missing right flank')
cc=m.comparison(p,p,m.CORE);bc=m.comparison(p,p,m.BROAD)
check(cc['common_finite_raw_samples']==51 and cc['raw_pearson']is not None and cc['normalized_rms']is None,'Synthetic partial order retains raw core Pearson but not normalized RMS')
check(bc['common_finite_raw_samples']==366 and bc['raw_pearson_block_reason']=='INSUFFICIENT_COMMON_RAW_COVERAGE' and bc['normalized_rms']is None,'Synthetic partial order retains 366 surrounding samples below fixed 440 gate')
p,q=m.profile(w,-f,e,m.ANCHOR_BERV,'barycentric',.01);check(q['normalization_status']=='RAW_ONLY' and 'NONPOSITIVE_FLANK_REFERENCE'in q['normalization_reasons'],'Negative reference never sign-flipped')
p={'signed_raw_flux':np.ones(601)*.1,'normalized_flux':np.ones(601)};check(m.comparison(p,p,m.CORE)['raw_pearson_block_reason']=='ZERO_RAW_VARIANCE','Exact constant zero-range guard')
for mask,minimum in [(m.CORE,41),(m.BROAD,440)]:
    for count in [minimum-1,minimum]:
        f=np.full(601,np.nan);f[np.flatnonzero(mask)[:count]]=np.arange(count,dtype=float);p={'signed_raw_flux':f,'normalized_flux':f}
        r=m.comparison(p,p,mask);check((r['raw_pearson']is not None)==(count>=minimum),'Common support boundary '+str(count)+'/'+str(minimum))
plan=json.loads((HERE/'PLAN.json').read_text())
for item in plan['native_fixed_frame_header_geometry']:
    for frame,geometry in item['fixed_frame_header_geometry'].items():
        lo,hi=geometry['offset_endpoints_from_frame_center_angstrom'];covered=(m.X>=lo)&(m.X<=hi)
        if item['order']==2:
            check(int(covered.sum())==417 and int((covered&m.CORE).sum())==51 and int((covered&m.BROAD).sum())==366,'Header-only order 2 grid support '+frame)
            check(not np.any(covered&(m.X>=1.5)),'Header-only order 2 entire positive flank missing '+frame)
        else:check(int(covered.sum())==601,'Header-only order 3 complete grid coverage '+frame)
for path,h in plan['source_hashes'].items():check(hashlib.sha256((REPO/path).read_bytes()).hexdigest()==h,'Frozen source exact: '+path)
r={'status':'PASS_COMPACT_SYNTHETIC_PREFLIGHT','checks':checks,'observational_arrays_read':False,'network_requests':0,'script_sha256':hashlib.sha256((HERE/'compare_group.py').read_bytes()).hexdigest(),'plan_sha256':hashlib.sha256((HERE/'PLAN.json').read_bytes()).hexdigest()}
(HERE/'SYNTHETIC_PREFLIGHT.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='checks'}));print('checks',len(checks))
