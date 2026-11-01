"""Independent reconstruction; does not import the production measurement module."""
from pathlib import Path
import bisect, csv, datetime, hashlib, json, math, platform, statistics, sys
from collections import Counter
import numpy as np
import astropy
from astropy.io import fits

AUDIT=Path(__file__).resolve().parent
OUT=AUDIT.parent
BASE=OUT.parents[2]
C=299792.458
GRID=[-1.0+i/100.0 for i in range(201)]
CORE=[i for i,x in enumerate(GRID) if abs(x)<=.250000001]
SIDE=[i for i,x in enumerate(GRID) if abs(x)>=.599999999]
errors=[]; maxima={}; scalar_cases=[]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def csvrows(p):return list(csv.DictReader(p.open()))
def require(ok,msg):
    if not ok: errors.append(msg)
def f(x):return None if x in ('',None) else float(x)
def close(a,b,label,atol=2e-7,rtol=2e-8):
    if a is None or b is None:
        require(a is None and b is None,label+' missing mismatch');return
    if not math.isfinite(a) or not math.isfinite(b):
        require(math.isnan(a) and math.isnan(b),label+' finite mismatch');return
    d=abs(a-b);maxima[label.split(':')[0]]=max(maxima.get(label.split(':')[0],0),d)
    require(d<=atol+rtol*max(abs(a),abs(b)),f'{label}: {a} != {b} (diff {d})')
def arrayclose(a,b,label):
    require(len(a)==len(b),label+' length')
    for i,(x,y) in enumerate(zip(a,b)):close(float(x),float(y),label+':'+str(i))
def quantile(a,q):
    a=sorted(a);v=(len(a)-1)*q;i=int(v);j=min(i+1,len(a)-1)
    return a[i]+(v-i)*(a[j]-a[i])
def statistics_check(vals,saved,label):
    a=[x for x in vals if x is not None and math.isfinite(x)]
    require(saved['n']==len(a),label+' count')
    expected={'median':statistics.median(a),'q25':quantile(a,.25),'q75':quantile(a,.75),'min':min(a),'max':max(a)} if a else dict.fromkeys(['median','q25','q75','min','max'])
    for k,v in expected.items():close(v,saved[k],label+':'+k,atol=1e-12,rtol=1e-12)
def solve(matrix,rhs):
    a=[list(row)+[r] for row,r in zip(matrix,rhs)]
    for k in range(len(a)):
        pivot=max(range(k,len(a)),key=lambda i:abs(a[i][k]));a[k],a[pivot]=a[pivot],a[k]
        v=a[k][k];assert abs(v)>1e-14
        a[k]=[x/v for x in a[k]]
        for i in range(len(a)):
            if i!=k:
                v=a[i][k];a[i]=[x-v*y for x,y in zip(a[i],a[k])]
    return [row[-1] for row in a]
def linfit(xs,ys):
    n=len(xs);sx=math.fsum(xs);sy=math.fsum(ys);sxx=math.fsum(x*x for x in xs);sxy=math.fsum(x*y for x,y in zip(xs,ys))
    slope=(n*sxy-sx*sy)/(n*sxx-sx*sx)
    return (sy-slope*sx)/n,slope
def fitgaussian(y,center,factor):
    indices=[i for i in CORE if math.isfinite(y[i])]
    if len(indices)<20:return None,None
    sigma=center/115000*factor/2.3548200450309493
    design=[[1.0,GRID[i],math.exp(-.5*(GRID[i]/sigma)**2)] for i in indices]
    ata=[[math.fsum(r[i]*r[j] for r in design) for j in range(3)] for i in range(3)]
    aty=[math.fsum(r[j]*y[i] for i,r in zip(indices,design)) for j in range(3)]
    coef=solve(ata,aty)
    residual=[y[i]-math.fsum(a*b for a,b in zip(row,coef)) for i,row in zip(indices,design)]
    return coef[2],math.sqrt(math.fsum(x*x for x in residual)/len(residual))
def correlation(a,b):
    pairs=[(a[i],b[i]) for i in CORE if math.isfinite(a[i]) and math.isfinite(b[i])]
    if len(pairs)<20:return None
    am=math.fsum(x for x,y in pairs)/len(pairs);bm=math.fsum(y for x,y in pairs)/len(pairs)
    aa=math.fsum((x-am)**2 for x,y in pairs);bb=math.fsum((y-bm)**2 for x,y in pairs)
    return math.fsum((x-am)*(y-bm) for x,y in pairs)/math.sqrt(aa*bb) if aa>0 and bb>0 else None
def interpolate(w,flux,q,spacing):
    if q<w[0] or q>w[-1]:return float('nan')
    j=bisect.bisect_left(w,q)
    right=max(1,min(j,len(w)-1))
    if w[right]-w[right-1]>1.51*spacing:return float('nan')
    if j<len(w) and w[j]==q:return flux[j]
    if j==0:return flux[0]
    fraction=(q-w[j-1])/(w[j]-w[j-1])
    return flux[j-1]+fraction*(flux[j]-flux[j-1])
def reconstruct(w,flux,center,scale):
    spacing=statistics.median([w[i+1]-w[i] for i in range(len(w)-1)])
    q=[(center+x)*scale for x in GRID];cb=center*scale
    raw=[interpolate(w,flux,a,spacing) for a in q]
    lo=bisect.bisect_left(w,cb-2.000000000001);hi=bisect.bisect_right(w,cb+2.000000000001)
    vals=[flux[i] for i in range(lo,hi) if abs(w[i]-cb)<=2 and math.isfinite(flux[i])]
    normalization=statistics.median(vals) if vals else float('nan')
    diffs=[flux[i+1]-flux[i] for i in range(lo,min(hi,len(w)-1)) if abs(w[i]-cb)<=2 and math.isfinite(flux[i]) and math.isfinite(flux[i+1]) and w[i+1]-w[i]<1.51*spacing]
    median_diff=statistics.median(diffs)
    noise=1.4826*statistics.median([abs(x-median_diff) for x in diffs])/math.sqrt(2)
    y=[x/normalization for x in raw] if normalization>0 and math.isfinite(normalization) else [float('nan')]*201
    si=[i for i in SIDE if math.isfinite(y[i])]
    if len(si)>=20:
        a,b=linfit([GRID[i] for i in si],[y[i] for i in si]);bg=[a+b*x for x in GRID]
    else:bg=[float('nan')]*201
    residual=[v-b for v,b in zip(y,bg)]
    narrow,nrms=fitgaussian(y,center,1)
    broad,brms=fitgaussian(y,center,3)
    integral=math.fsum(.5*(residual[i]+residual[j])*(GRID[j]-GRID[i]) for i,j in zip(CORE[:-1],CORE[1:]))
    return {'offset_air_angstrom':GRID,'requested_bary_air_angstrom':q,'raw_flux':raw,'normalized_flux':y,'linear_background':bg,'residual':residual}, {
        'normalization_adu':normalization,'normalization_samples':len(vals),'first_difference_noise_proxy_adu':noise,
        'narrow_amplitude':narrow,'narrow_residual_rms':nrms,'broad3_amplitude':broad,'broad3_residual_rms':brms,
        'core_flux_integral_over_linear_background':integral,'local_continuum_low':not math.isfinite(normalization) or normalization<=0 or normalization<=3*noise}

def main():
    require((OUT/'SUMMARY.json').exists(),'Production SUMMARY missing')
    plan=read(OUT/'PLAN.json');summary=read(OUT/'SUMMARY.json');events=read(OUT/'EVENT_RESULTS.json')
    rows=csvrows(OUT/'ALL_EPOCH_MEASUREMENTS.csv');hits=csvrows(BASE/'v2/extension02/production/V2_HITS.csv')
    mainrows=csvrows(BASE/'v2/extension02/MAIN100.csv');manifest=read(BASE/'v2/extension02/acquisition/DOWNLOAD_MANIFEST.json')
    byd={m['dp_id']:m for m in plan['inputs']};hitby={h['candidate_id']:h for h in hits}
    catids=[h['candidate_id'] for h in hits]
    require(len(catids)==336 and len(set(catids))==336,'336 unique catalog IDs')
    require([r['candidate_id'] for r in events]==catids==plan['event_ids'],'Catalog/event/plan ID order')
    require([r['dp_id'] for r in mainrows]==[r['dp_id'] for r in plan['inputs']],'All100 MAIN100 exposures retained in order')
    require(len(byd)==100,'100 unique input exposures')
    start_hashes={p:sha(OUT/p) for p in ['PLAN.json','measure_epochs.py','SUMMARY.json','EVENT_RESULTS.json','ALL_EPOCH_MEASUREMENTS.csv','INPUT_CHECKS.json','EVENT_SUMMARY.csv']}
    for p,digest in plan['source_hashes'].items():require(sha(BASE/p)==digest,'Source integrity '+p)
    require(summary['plan_sha256']==start_hashes['PLAN.json'],'Plan summary hash')
    require(summary['script_sha256']==start_hashes['measure_epochs.py'],'Script summary hash')
    input_checks=[];wave_limits={};source_arrays={}
    selected_ids=[catids[0],catids[len(catids)//2],catids[-1]]
    low=next(r for r in rows if r['local_continuum_low']=='True')
    if low['candidate_id'] not in selected_ids:selected_ids.append(low['candidate_id'])
    selected_targets={hitby[cid]['canonical_target'] for cid in selected_ids}
    manifest_by={m['dp_id']:m for m in manifest}
    for m,original in zip(plan['inputs'],mainrows):
        p=BASE/m['relative_path'];digest=sha(p)
        require(digest==m['sha256']==manifest_by[m['dp_id']]['sha256'],'Input SHA256 '+m['dp_id'])
        require(m['target']==original['canonical_target']==manifest_by[m['dp_id']]['canonical_target'],'Target metadata '+m['dp_id'])
        with fits.open(p) as h:
            ph,eh=h[0].header,h[1].header
            require(ph['SPECSYS']=='BARYCENT' and eh['TUNIT1']=='angstrom' and 'obs.atmos' in eh['TUCD1'],'Barycentric air Angstrom units '+m['dp_id'])
            require(eh['TUNIT2']=='adu' and ph['NCOMBINE']==1,'Single ADU spectrum '+m['dp_id'])
            require(ph['DATE-OBS']==m['date_obs'],'Date identity '+m['dp_id'])
            close(float(ph['ESO DRS BERV']),m['berv_km_s'],'BERV header',atol=1e-10,rtol=0)
            w=np.array(h[1].data['WAVE'][0],float);fl=np.array(h[1].data['FLUX'][0],float);er=np.array(h[1].data['ERR'][0],float)
        require(bool(np.isfinite(w).all() and (np.diff(w)>0).all()),'Finite increasing wavelengths '+m['dp_id'])
        wave_limits[m['dp_id']]=(float(w[0]),float(w[-1]))
        if m['target'] in selected_targets:source_arrays[m['dp_id']]=(w.tolist(),fl.tolist())
        input_checks.append({'dp_id':m['dp_id'],'sha256':digest,'matches_plan_and_acquisition':digest==m['sha256']==manifest_by[m['dp_id']]['sha256'],
                             'finite_positive_ERR_samples':int((np.isfinite(er)&(er>0)).sum()),'wave_min':float(w[0]),'wave_max':float(w[-1])})
    expected={(h['candidate_id'],m['dp_id'],frame) for h in hits for m in plan['inputs'] if m['target']==h['canonical_target'] for frame in ('barycentric','topocentric')}
    keys=[(r['candidate_id'],r['dp_id'],r['frame']) for r in rows]
    require(len(keys)==len(set(keys)) and set(keys)==expected,'Complete exact same-target event/epoch/frame coverage')
    rowby={k:r for k,r in zip(keys,rows)}
    stored_arrays={};outside=0;array_count=0
    for r in rows:
        h=hitby[r['candidate_id']];source=byd[h['dp_id']];m=byd[r['dp_id']]
        cb=float(h['fitted_center_angstrom']);center=cb if r['frame']=='barycentric' else cb/(1+source['berv_km_s']/C)
        scale=1 if r['frame']=='barycentric' else 1+m['berv_km_s']/C
        require((r['is_discovery_exposure']=='True')==(r['dp_id']==h['dp_id']),'Discovery flag '+str((r['candidate_id'],r['dp_id'],r['frame'])))
        close(f(r['center_in_frame_air_angstrom']),center,'Frame center',atol=1e-10,rtol=0)
        close(f(r['center_sampled_bary_air_angstrom']),center*scale,'Requested center',atol=1e-10,rtol=0)
        close(f(r['source_epoch_displacement_resolution_elements']),abs(m['berv_km_s']-source['berv_km_s'])/C*115000,'BERV displacement',atol=1e-12,rtol=1e-12)
        p=OUT/r['profile_path'];require(sha(p)==r['profile_sha256'],'Profile hash '+r['profile_path'])
        with np.load(p) as z:arr={k:np.array(z[k]) for k in z.files}
        array_count+=1
        arrayclose(arr['offset_air_angstrom'],GRID,'All profile offset grid')
        arrayclose(arr['requested_bary_air_angstrom'],[(center+x)*scale for x in GRID],'All profile frame transform')
        loww,highw=wave_limits[r['dp_id']]
        for q,y in zip(arr['requested_bary_air_angstrom'],arr['raw_flux']):
            if q<loww or q>highw:
                outside+=1;require(math.isnan(float(y)),'No extrapolation '+r['profile_path'])
        require(int(r['valid_samples'])==int(np.isfinite(arr['normalized_flux']).sum()),'Valid count '+r['profile_path'])
        if r['candidate_id'] in selected_ids:stored_arrays[(r['candidate_id'],r['dp_id'],r['frame'])]=arr
    # Check every aggregate against the full row table, omitting discovery explicitly.
    for s in events:
        cid=s['candidate_id'];target=hitby[cid]['canonical_target'];same=[m for m in plan['inputs'] if m['target']==target]
        require(s['other_epochs']==len(same)-1 and s['comparison_epochs_including_discovery']==len(same),'Epoch totals '+cid)
        span=max(m['berv_km_s'] for m in same)-min(m['berv_km_s'] for m in same)
        close(span,s['berv_span_km_s'],'Span',atol=1e-12,rtol=1e-12)
        require(s['frame_separation_below_one_resolution_element']==(span<C/115000),'Span flag '+cid)
        for frame in ('barycentric','topocentric'):
            other=[rowby[(cid,m['dp_id'],frame)] for m in same if m['dp_id']!=hitby[cid]['dp_id']]
            saved=s['frames'][frame]
            require(saved['other_epoch_count']==len(other),'Discovery excluded '+cid+frame)
            require(saved['other_valid_profile_count']==sum(int(r['valid_samples'])>=181 for r in other),'Other valid '+cid+frame)
            require(saved['other_low_continuum_count']==sum(r['local_continuum_low']=='True' for r in other),'Other low '+cid+frame)
            for column,key in [('correlation_to_discovery','other_correlation_to_discovery'),('narrow_amplitude','other_narrow_amplitude'),('broad3_amplitude','other_broad3_amplitude'),('core_flux_integral_over_linear_background','other_integrated_excess')]:
                statistics_check([f(r[column]) for r in other],saved[key],'Summary '+key)
            close(saved['discovery_narrow_amplitude'],f(rowby[(cid,hitby[cid]['dp_id'],frame)]['narrow_amplitude']),'Discovery amplitude',atol=1e-12,rtol=1e-12)
        a=s['frames']['barycentric']['other_correlation_to_discovery']['median'];b=s['frames']['topocentric']['other_correlation_to_discovery']['median']
        close(a-b if a is not None and b is not None else None,s['median_correlation_bary_minus_topo'],'Difference summary',atol=1e-12,rtol=1e-12)
    # Independent scalar interpolation, background and Gaussian normal-equation fits.
    reconstructed={}
    for cid in selected_ids:
        h=hitby[cid];source=byd[h['dp_id']];cb=float(h['fitted_center_angstrom'])
        for m in plan['inputs']:
            if m['target']!=h['canonical_target']:continue
            w,flux=source_arrays[m['dp_id']]
            for frame in ('barycentric','topocentric'):
                center=cb if frame=='barycentric' else cb/(1+source['berv_km_s']/C)
                scale=1 if frame=='barycentric' else 1+m['berv_km_s']/C
                arr,metrics=reconstruct(w,flux,center,scale)
                key=(cid,m['dp_id'],frame);r=rowby[key];stored=stored_arrays[key]
                for k,v in arr.items():arrayclose(v,stored[k],'Scalar '+k)
                for k,v in metrics.items():
                    if isinstance(v,bool):require(v==(r[k]=='True'),'Scalar '+k+str(key))
                    else:close(v,f(r[k]),'Scalar '+k)
                reconstructed[key]=arr['residual']
                scalar_cases.append({'candidate_id':cid,'dp_id':m['dp_id'],'frame':frame,**metrics})
    for key,residual in reconstructed.items():
        cid,dp,frame=key;ref=reconstructed[(cid,hitby[cid]['dp_id'],frame)]
        close(correlation(ref,residual),f(rowby[key]['correlation_to_discovery']),'Scalar correlation')
    require(summary['events']==336 and summary['frame_measurements']==len(rows) and summary['profiles']==len(rows),'Topline event/profile totals')
    require(summary['event_epoch_pairs']==len(rows)//2,'Event epoch pairs')
    require(summary['discovery_frame_measurements']==sum(r['is_discovery_exposure']=='True' for r in rows)==672,'Discovery672')
    require(summary['other_epoch_frame_measurements']==sum(r['is_discovery_exposure']!='True' for r in rows),'Other frame totals')
    require(summary['low_continuum_measurements']==sum(r['local_continuum_low']=='True' for r in rows),'Low continuum total')
    require(all(sha(OUT/p)==digest for p,digest in start_hashes.items()),'Production outputs unchanged throughout audit')
    result={'status':'PASS_INDEPENDENT_SCALAR_AND_COVERAGE_AUDIT' if not errors else 'FAIL',
            'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'errors':errors,
            'source_snapshot_hashes':start_hashes,'audit_script_sha256':sha(Path(__file__)),
            'catalog_events':len(catids),'verified_input_exposures':len(input_checks),'profile_hashes_checked':array_count,
            'complete_expected_event_epoch_frame_records':len(expected),'all_event_summaries_checked':len(events),
            'outside_coverage_requested_samples':outside,
            'scalar_selection_rule':'First, index len//2, and last immutable catalog IDs; additionally first row flagged low continuum in completed table. Audits are post-hoc validation, not blinded new data.',
            'scalar_event_ids':selected_ids,'scalar_frame_profiles':len(scalar_cases),
            'scalar_low_continuum_profiles':sum(r['local_continuum_low'] for r in scalar_cases),
            'maximum_absolute_differences_by_field':maxima,
            'input_checks':input_checks,'scalar_cases':scalar_cases,
            'dependencies':{'python':sys.version,'numpy':np.__version__,'astropy':astropy.__version__},
            'independence':'Separate agent, code and process; production module never imported. Scalar bisect interpolation, statistics.median/MAD, closed-form sideband linear regression, pivoted scalar normal equations for Gaussian fits, fsum Pearson correlations and scalar quantiles. Shared Astropy FITS decoding, NumPy array/NPZ handling, source bytes, mathematical specification and floating-point runtime.',
            'limitations':['Source byte/header and coverage checks cover all100 inputs and all4370 profile hashes/transforms; independent scalar flux-to-metric reconstruction covers only four event IDs and their same-target epochs.',
                           'Earlier200 main exposures are excluded by the fixed scope; results are not all available project epochs.',
                           'No requested sample lies outside coverage in this dataset: no-extrapolation code is inspected but boundary failure behavior is not empirically exercised.',
                           'Classical BERV transform, no stellar radial-velocity or full relativistic/drift correction.',
                           'Low continuum metrics remain in aggregate statistics and must be interpreted cautiously; unavailable ERR prevents formal uncertainty.',
                           'No origin/repeat classifier, independent telescope observation, false-alarm calibration or human verification is provided.']}
    (AUDIT/'SUMMARY.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['input_checks','scalar_cases','source_snapshot_hashes']},indent=2))
    raise SystemExit(0 if not errors else 1)

if __name__=='__main__':main()
