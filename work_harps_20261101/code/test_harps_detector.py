"""Small meaningful boundary and scalar-reference checks; no sky tuning."""
import numpy as np
from harps_detector import analyze_arrays,runs,DEFAULTS,classify_run

assert runs([True,True,False,True]) == [(0,2),(3,4)]
assert classify_run(3,DEFAULTS)=='SHORT_RUN'
assert classify_run(4,DEFAULTS)=='PRELIMINARY_EMISSION_HIT'
assert classify_run(60,DEFAULTS)=='PRELIMINARY_EMISSION_HIT'
assert classify_run(61,DEFAULTS)=='WIDE_RUN'
n=1800
w=5000+np.arange(n)*0.01
f=100+np.where(np.arange(n)%2,1.,-1.)
f[100:104]+=40
f[300:303]+=40
f[600:610]=np.nan
f[800:810]=0
# A run that ends at the final searched pixel must be flushed and retained.
f[1746:1750]+=40
r,a=analyze_arrays(w,f)
hits=[e for e in r['all_threshold_runs'] if e['status']=='PRELIMINARY_EMISSION_HIT']
assert [(e['start_index'],e['end_index_exclusive']) for e in hits]==[(100,104),(1746,1750)],hits
assert any(e['start_index']==300 and e['status']=='SHORT_RUN' for e in r['all_threshold_runs'])
assert not a['searched'][550:660].any()
assert not a['searched'][750:860].any()
assert not a['searched'][:50].any()
assert not a['searched'][-50:].any()
for i in [50,99,100,103,130,299,300,303,400,660,1000,1749]:
    v=f[i-50:i+51]
    assert np.isclose(a['continuum'][i],np.median(v),atol=0,rtol=0)
    assert np.isclose(a['local_std'][i],np.std(v,ddof=0),atol=2e-10,rtol=2e-10),(i,a['local_std'][i],np.std(v))
print('PASS: segment edges, terminal run, 4-pixel inclusion, short/wide classification, NaN/zero gaps, and scalar window statistics')
