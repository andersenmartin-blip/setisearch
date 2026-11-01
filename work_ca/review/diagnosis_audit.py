"""Independent CA score-decomposition audit; no production imports.

Reconstructs triangle exposure integrals through piecewise polynomial integrals,
uses scalar Python sums, and verifies fixed stored-seed selection and summaries.
This is a review of a posthoc diagnostic, not a new detector-bank run.
"""
from pathlib import Path
import hashlib, io, json, math, statistics, zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).with_name('DIAGNOSIS_REVIEW_CA.json')
ON=(0,2,4)

def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def integral(a,b):
    """Integrate max(0,1-|x|) on [a,b], clipping each linear half."""
    result=0.0
    lo,hi=max(a,-1.0),min(b,0.0)
    if lo<hi: result+=(hi-lo)*(1.0+(hi+lo)/2.0)
    lo,hi=max(a,0.0),min(b,1.0)
    if lo<hi: result+=(hi-lo)*(1.0-(hi+lo)/2.0)
    return result

def sparse(case,scope,source,record,reflect=False):
    c=case['true_center_native_at_scan0_midpoint']; d=case['true_drift_hz_s']
    if reflect: c=2*record['support_start']+12288-1-c;d=-d
    center=c+d*((scope['tref_midpoint_mjd']-source['tref_midpoint_mjd'])*86400)/scope['df_hz']-record['support_start']
    sweep=abs(d*scope['dt_seconds']/scope['df_hz'])/2
    answer=[]
    for t in range(16):
        mid=center+d*(t-7.5)*scope['dt_seconds']/scope['df_hz']
        lo,hi=mid-sweep,mid+sweep
        weights={}
        for k in range(math.floor(lo)-1,math.ceil(hi)+2):
            w=max(0.0,1-abs(k-mid)) if sweep==0 else integral(lo-k,hi-k)/(hi-lo)
            if w>0: weights[k]=w
        assert abs(math.fsum(weights.values())-1)<1e-10
        answer.append(weights)
    return answer

def sumtrack(a,offsets,center,width):
    half=width//2
    return math.fsum(float(a[t,center+o+j]) for t,o in enumerate(offsets) for j in range(-half,half+1))

def main():
    assert not OUT.exists(),'Exclusive review result required'
    prod_path=ROOT/'work_ca/diagnosis/SCORE_DECOMPOSITION_CA.json'
    prod=json.loads(prod_path.read_text())
    plan=json.loads((ROOT/'work_bz/PLAN_BZ.json').read_text())
    for p,h in prod['input_sha256'].items(): assert digest(ROOT/p)==h,p
    receipt=json.loads((ROOT/'work_bz/execution/production/RESULT.json').read_text())
    arch=ROOT/'work_bz/execution/production/EVIDENCE.zip'
    assert digest(arch)==receipt['archive']['sha256']
    with zipfile.ZipFile(arch) as z:
        assert z.testzip() is None
        manifest=json.loads(z.read('ARCHIVE_MANIFEST.json'))
        assert manifest['members']==receipt['archive']['members']
        for m in manifest['members']:
            b=z.read(m['path']);assert len(b)==m['bytes'];assert hashlib.sha256(b).hexdigest()==m['sha256']
        cases=json.loads(z.read('outputs/CASES_BZ.json'))['cases']
        data=z.read('outputs/RESULT_ARRAYS_BZ.npz')
        assert hashlib.sha256(data).hexdigest()==json.loads(z.read('outputs/SUMMARY_BZ.json'))['arrays_sha256']
        with np.load(io.BytesIO(data),allow_pickle=False) as f: arrays={k:f[k] for k in f.files}
    bg=[]
    for rec in plan['inputs']:
        p=ROOT/'work_by/inputs'/Path(rec['path']).name
        assert digest(p)==rec['sha256'];assert p.stat().st_size==rec['bytes']
        bg.append(np.load(p,allow_pickle=False))
    chosen=[c for c in cases if c['amplitude']==8.0 and c['presence']=='ON_ONLY']
    pcase={c['case_index']:c for c in prod['cases']}
    errs=[];newbytes=0;captured_err=[];mirrors=[];weight_error=[];sparse_mass_error=[]
    decoded=[];missing=[];projection_count=0;rowcount=0;groups={314:[],419:[],524:[]}
    for c in chosen:
        ci=c['case_index'];p=pcase[ci]
        idx=[i for i,v in enumerate(arrays['seed_case_index']) if int(v)==ci]
        assert len(idx)==p['matched_seed_count']
        units=[]
        for scan in range(5):
            a=sparse(c,plan['scans'][scan],plan['scans'][0],plan['inputs'][scan])
            b=sparse(c,plan['scans'][scan],plan['scans'][0],plan['inputs'][scan],True)
            for t in range(16):
                assert set(b[t])=={12287-k for k in a[t]}
                weight_error.extend(abs(w-b[t][12287-k]) for k,w in a[t].items())
                sparse_mass_error.append(abs(math.fsum(a[t].values())-1))
                rowcount+=1
            units.append(a)
        if not idx:
            assert p['best_common_seed'] is None;missing.append(ci);continue
        best=max(idx,key=lambda i:min(float(arrays['center_scores'][i,t]) for t in ON))
        ps=p['best_common_seed'];assert best==ps['union_row']
        width=int(arrays['seed_width'][best]);wi=(1,3,9,33).index(width)
        ri=int(arrays['seed_refined_index'][best]);rate=float(arrays['seed_drift_hz_s'][best])
        assert width==ps['width'] and ri==ps['refined_index'] and rate==ps['drift_hz_s']
        assert ps['minimum_ON_score']==min(float(arrays['center_scores'][best,t]) for t in ON)
        assert ps['three_ON_recovered']==all(float(arrays['center_scores'][best,t])>=10 for t in ON)
        for scan in ON:
            scope=plan['scans'][scan];rec=plan['inputs'][scan]
            offsets=[round(rate*(t-7.5)*scope['dt_seconds']/scope['df_hz']) for t in range(16)]
            native=int(arrays['predicted_native'][best,scan]);center=native-rec['support_start']
            startfreq=plan['scans'][0]['fch1_mhz']+int(arrays['seed_center_native'][best])*plan['scans'][0]['df_hz']/1e6
            gap=(scope['tref_midpoint_mjd']-plan['scans'][0]['tref_midpoint_mjd'])*86400
            projected=round(((startfreq+rate*gap/1e6)-scope['fch1_mhz'])*1e6/scope['df_hz'])
            assert projected==native;projection_count+=1
            matrix=bg[scan].copy()
            for t,row in enumerate(units[scan]):
                for channel,weight in row.items(): matrix[t,channel]=np.float32(float(bg[scan][t,channel])+8.0*weight)
            assert hashlib.sha256(matrix.tobytes()).hexdigest()==arrays['injected_sha256'][ci,scan]
            newbytes+=1
            med,scale=map(float,arrays['calibration'][ci,scan,ri,wi])
            raw=sumtrack(matrix,offsets,center,width);rawbg=sumtrack(bg[scan],offsets,center,width)
            terms=[float(matrix[t,center+o+j])-float(bg[scan][t,center+o+j]) for t,o in enumerate(offsets) for j in range(-width//2+1,width//2+1)]
            excess=math.fsum(terms)
            score=(raw-med)/scale;stored=float(arrays['center_scores'][best,scan])
            # Selected-seed arithmetic only: calibration vectors are never rerun.
            termbg=(rawbg-med)/scale;terminj=excess/scale
            err=abs(score-stored);assert err<1e-10;assert abs(score-termbg-terminj)<1e-10
            q=next(x for x in ps['scans'] if x['scan']==scan)
            values={'native_center':native,'median_stored':med,'MAD_scale_stored':scale,
                    'stored_score':stored,'scalar_score':score,'background_score_term':termbg,
                    'injected_excess_score_term':terminj,'raw_background_sum':rawbg,'raw_injected_excess_sum':excess}
            for k,v in values.items(): assert abs(v-q[k])<1e-10,(ci,scan,k,v,q[k])
            ideal=math.fsum(weight for t,row in enumerate(units[scan]) for channel,weight in row.items() if abs(channel-(center+offsets[t]))<=width//2)
            captured_err.append(abs(ideal/16-q['captured_fraction_of_ideal_excess']))
            assert captured_err[-1]<1e-12
            assert abs(excess-8*ideal-q['float32_injection_rounding_delta'])<1e-10
            assert bool(terminj>=10)==q['passes_with_background_term_omitted']
            assert bool(stored>=10)==q['passes_stored']
            mirror=sumtrack(bg[scan][:,::-1],[-o for o in offsets],12287-center,width)
            mirrors.append(abs(mirror-rawbg));assert mirrors[-1]<1e-10
            errs.append(err);decoded.append(values)
            groups[c['base_drift_index']].append(q)
    assert len(chosen)==24 and len(missing)==4 and len(errs)==60 and newbytes==60
    summaries=[]
    for g in prod['groups']:
        values=groups[g['base_drift_index']];assert len(values)==g['evaluated_selected_seed_ON_tracks']
        for key in ('background_score_term','injected_excess_score_term','captured_fraction_of_ideal_excess','MAD_scale_stored','float32_injection_rounding_delta'):
            vals=[s[key] for s in values]
            for k,v in [('minimum',min(vals)),('median',statistics.median(vals)),('maximum',max(vals))]:assert v==g[key][k]
        fail=sum(not s['passes_stored'] for s in values)
        exfail=sum(not s['passes_stored'] and s['passes_with_background_term_omitted'] for s in values)
        assert fail==g['failed_stored_tracks'];assert exfail==g['failed_stored_tracks_with_excess_alone_at_least_10']
        summaries.append({'base_drift_index':g['base_drift_index'],'tracks':len(values),'failed':fail,'failed_with_excess_alone_ge10':exfail})
    assert max(weight_error)<1e-9 and max(mirrors)<1e-10
    result={'schema':'SETI_CA_INDEPENDENT_DIAGNOSIS_REVIEW_V1','status':'PASS_INDEPENDENT_DIAGNOSIS_REVIEW',
      'diagnostic_sha256':digest(prod_path),'reviewer_sha256':digest(Path(__file__)),
      'selected_cases':len(chosen),'missing_seed_case_indices':missing,'selected_seeds_checked':20,
      'scalar_track_decompositions':len(errs),'injected_matrices_exact_sha256_matches':newbytes,
      'projection_checks':projection_count,'max_stored_score_absolute_error':max(errs),
      'max_captured_fraction_absolute_error':max(captured_err),'reflection_geometry_scan_pairs':120,
      'reflection_time_rows':rowcount,'max_independent_reflected_weight_error':max(weight_error),
      'max_independent_template_mass_error':max(sparse_mass_error),'integer_track_reflections':len(mirrors),
      'max_mirror_track_sum_error':max(mirrors),'group_counts_checked':summaries,
      'independence':'No production imports. Piecewise clipped linear integration replaces producer CDF. Scalar loops and math.fsum reconstruct selected sums; Python round verifies projections/offsets. NumPy shares float32 representation and stored array reader.',
      'limits':['Posthoc selected paths on exposed BZ backgrounds; this audit is not new scientific validation.',
       'Stored local medians/MAD are held fixed; no calibration vectors or detector bank rerun.',
       'Four cases without stored source seeds are intentionally not decomposed.',
       'Mirror test checks sparse model and integer-track algebra only, not every detector selection/projection branch.',
       'No new observation, blind ON/OFF search, false-alarm calibration, Jy sensitivity or missing-OFF5 qualification.']}
    OUT.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
