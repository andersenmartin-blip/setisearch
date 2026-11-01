"""Fresh-process independent scalar interpolation/fit cross-check; same-agent audit."""
from pathlib import Path
import json,csv,hashlib,bisect,itertools
import numpy as np
from astropy.io import fits
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1]
plan=json.loads((OUT/'PLAN.json').read_text());rows=list(csv.DictReader((OUT/'ALL_EPOCH_MEASUREMENTS.csv').open()));groups=plan['groups_definition']
assert len(groups)==28 and len(rows)==614 and len({x for g in groups for x in g['member_ids']})==64
assert len({(r['group_id'],r['dp_id'],r['frame']) for r in rows})==len(rows)
checks=[]
for g in [groups[0],groups[len(groups)//2],groups[-1]]:
    ep=[r for r in rows if r['group_id']==g['group_id'] and r['frame']=='barycentric']
    for item in [ep[0],ep[len(ep)//2],ep[-1]]:
        m=next(m for m in plan['input_manifest'] if m['dp_id']==item['dp_id'])
        with fits.open(BASE/m['relative_path']) as h:wave=np.array(h[1].data['WAVE'][0],float);flux=np.array(h[1].data['FLUX'][0],float)
        for frame in ['barycentric','topocentric']:
            r=next(r for r in rows if r['group_id']==g['group_id'] and r['dp_id']==m['dp_id'] and r['frame']==frame);d=np.load(OUT/r['profile_path']);x=d['offset_air_angstrom'];center=g['center_bary_air_angstrom'] if frame=='barycentric' else g['center_topocentric_air_angstrom'];factor=1 if frame=='barycentric' else (1+m['berv_km_s']/299792.458)
            wanted=(center+x)*factor;manual=[]
            for val in wanted:
                j=bisect.bisect_right(wave,val);lo=j-1;hi=j
                manual.append(flux[lo]+(flux[hi]-flux[lo])*(val-wave[lo])/(wave[hi]-wave[lo]))
            manual=np.array(manual);normal=np.median(flux[abs(wave-center*factor)<=2]);y=manual/normal;side=abs(x)>=.599999999
            n=side.sum();sx=x[side].sum();sy=y[side].sum();sxx=(x[side]**2).sum();sxy=(x[side]*y[side]).sum();slope=(n*sxy-sx*sy)/(n*sxx-sx*sx);intercept=(sy-slope*sx)/n;bg=intercept+slope*x
            rawdiff=float(np.nanmax(abs(manual-d['raw_flux'])));normdiff=float(np.nanmax(abs(y-d['normalized_flux'])));bgdiff=float(np.nanmax(abs(bg-d['linear_background'])));assert rawdiff<1e-8 and normdiff<1e-10 and bgdiff<1e-10
            amplitudes={};core=abs(x)<=.250000001
            for tag,fac in [('narrow',1),('broad3',3)]:
                z=np.exp(-.5*(x/(center/115000*fac/2.3548200450309493))**2);cols=[np.ones(core.sum()),x[core],z[core]];a=np.array([[sum(float(a)*float(b) for a,b in zip(c1,c2)) for c2 in cols] for c1 in cols]);b=np.array([sum(float(a)*float(b) for a,b in zip(col,y[core])) for col in cols]);coef=np.linalg.solve(a,b);diff=abs(float(coef[2])-float(r[tag+'_amplitude']));assert diff<1e-9;amplitudes[tag]=diff
            checks.append(dict(group_id=g['group_id'],dp_id=m['dp_id'],frame=frame,max_raw_interpolation_difference=rawdiff,max_normalization_difference=normdiff,max_background_difference=bgdiff,amplitude_differences=amplitudes))
source=BASE/'v2/triage_batch02/CUMULATIVE_DISPOSITIONS.csv';assert hashlib.sha256(source.read_bytes()).hexdigest()==plan['source_dispositions_sha256']
result=dict(status='PASSED',audit_kind='Same-agent fresh-process check using scalar bracketing interpolation, analytic line fit and normal-equation Gaussian amplitude; not independent human validation.',selected_groups=[g['group_id'] for g in [groups[0],groups[len(groups)//2],groups[-1]]],selection='First/middle/last group; first/middle/last epoch per group; both frames.',checked_profiles=len(checks),checks=checks,original_dispositions_unchanged=True,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(OUT/'NUMERICAL_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print('PASSED',len(checks),'profiles')
