"""Independent closed-form fit checks and boundary tests, development only."""
import numpy as np
from profile_detector import analyze_arrays,fit_profile,DEFAULTS

cfg=DEFAULTS.copy();w=5000+np.arange(1001)*.01;k=500
rng=np.random.default_rng(2701);background=1000+.02*(np.arange(1001)-k)+rng.normal(0,1,1001)
for phase in (0.,.25,.5):
 center=w[k]+phase*.01;sigma=(w[k]/115000)/(2*np.sqrt(2*np.log(2)))
 f=background+32*np.exp(-.5*((w-center)/sigma)**2)
 result,_=analyze_arrays(w,f,cfg)
 hits=[e for e in result['events'] if e['status']=='PRELIMINARY_PROFILE_HIT' and abs(e['fitted_center_angstrom']-center)<.021]
 assert hits,(phase,result['events'])
 e=fit_profile(w,f,k,cfg)
 offsets=list(range(-50,-12))+list(range(13,51))
 slope=(float(np.median(f[k+np.arange(13,51)]))-float(np.median(f[k+np.arange(-50,-12)])))/63
 intercept=float(np.median([f[k+x]-slope*x for x in offsets]))
 residual=[f[k+x]-intercept-slope*x for x in offsets]
 noise=1.4826*float(np.median(np.abs(residual-np.median(residual))))
 assert abs(e['sideband_intercept_adu']-intercept)<1e-10
 assert abs(e['sideband_mad_adu']-noise)<1e-10
 g=np.exp(-.5*((w[k-12:k+13]-e['fitted_center_angstrom'])/sigma)**2)
 y=f[k-12:k+13]-intercept-slope*np.arange(-12,13)
 amp=sum(float(a)*float(b) for a,b in zip(g,y))/sum(float(a)**2 for a in g)
 assert abs(e['amplitude_adu']-amp)<1e-9
f=background.copy();f[k]=0
r,a=analyze_arrays(w,f,cfg)
assert not a['searched'][k-49:k+50].any()
print('PASS: 3 phases, independent sideband and amplitude arithmetic, zero-gap margins')
