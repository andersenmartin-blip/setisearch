"""Independent arithmetic for May quality audit; no production imports or I/O.
Derived from the already validated independent BERV audit, not production code.
"""
import math, statistics
import numpy as np
C=299792.458
X=np.arange(201,dtype=float)/100-1
CORE=np.abs(X)<=.250000001
SIDE=np.abs(X)>=.599999999

def value(x):return float(x)if np.isfinite(x)else None

def quantile(values,p):
 a=sorted(values);pos=p*(len(a)-1);lo=int(math.floor(pos));hi=int(math.ceil(pos));return a[lo]+(a[hi]-a[lo])*(pos-lo)

def stats(values):
 a=[float(v)for v in values if v is not None and math.isfinite(v)]
 return {'n':len(a),'median':quantile(a,.5)if a else None,'q25':quantile(a,.25)if a else None,'q75':quantile(a,.75)if a else None,'min':min(a)if a else None,'max':max(a)if a else None}

def correlation(a,b):
 valid=CORE&np.isfinite(a)&np.isfinite(b)
 if valid.sum()<20:return None
 aa=a[valid]-np.mean(a[valid]);bb=b[valid]-np.mean(b[valid]);va=np.dot(aa,aa);vb=np.dot(bb,bb)
 if va==0 or vb==0:return None
 return float(np.dot(aa,bb)/math.sqrt(va*vb))

def reconstruct(w,f,e,center,scale):
 step=statistics.median(np.diff(w).tolist());requested=(center+X)*scale;cb=center*scale
 right=np.searchsorted(w,requested,side='left');right=np.minimum(np.maximum(right,1),len(w)-1);left=right-1
 weight=(requested-w[left])/(w[right]-w[left])
 raw=f[left]+weight*(f[right]-f[left])
 raw[requested==w[left]]=f[left[requested==w[left]]];raw[requested==w[right]]=f[right[requested==w[right]]]
 raw[(requested<w[0])|(requested>w[-1])]=np.nan
 gaps=(w[right]-w[left])>1.51*step;raw[gaps]=np.nan
 nearby=(np.abs(w-cb)<=2)&np.isfinite(f);normal=statistics.median(f[nearby].tolist())if nearby.any()else math.nan
 pair=(np.abs(w[:-1]-cb)<=2)&np.isfinite(f[:-1])&np.isfinite(f[1:])&(np.diff(w)<1.51*step);dif=np.diff(f)[pair];dif=dif[np.isfinite(dif)]
 noise=1.4826*statistics.median(np.abs(dif-statistics.median(dif.tolist())).tolist())/math.sqrt(2)if len(dif)else math.nan
 usable=math.isfinite(normal)and normal>0;y=raw/normal if usable else np.full(201,np.nan)
 valid=SIDE&np.isfinite(y)
 if valid.sum()>=20:
  design=np.column_stack([np.ones(valid.sum()),X[valid]]);coef=np.linalg.solve(design.T@design,design.T@y[valid]);background=coef[0]+coef[1]*X
 else:background=np.full(201,np.nan)
 residual=y-background;metrics={'center_in_frame_air_angstrom':center,'center_sampled_bary_air_angstrom':cb,'normalization_adu':value(normal),'normalization_samples':int(nearby.sum()),'first_difference_noise_proxy_adu':value(noise),'local_continuum_low':bool(not usable or(math.isfinite(noise)and normal<=3*noise)),'valid_samples':int(np.isfinite(y).sum()),'gap_masked_samples':int(gaps.sum()),'finite_positive_ERR_samples':int((np.isfinite(e[right])&(e[right]>0)).sum()),'normalization_status':'USABLE_POSITIVE_MEDIAN'if usable else'NONPOSITIVE_OR_MISSING_MEDIAN'}
 for name,factor in [('narrow',1),('broad3',3)]:
  valid=CORE&np.isfinite(y)
  if valid.sum()<20:amp=rms=None
  else:
   sigma=center/115000*factor/2.3548200450309493;gaussian=np.exp(-.5*(X/sigma)**2);design=np.column_stack([np.ones(valid.sum()),X[valid],gaussian[valid]]);coef=np.linalg.solve(design.T@design,design.T@y[valid]);amp=float(coef[2]);rms=float(np.sqrt(np.mean((y[valid]-design@coef)**2)))
  metrics[name+'_amplitude']=amp;metrics[name+'_residual_rms']=rms
 # Explicit trapezoid sum, independent of production np.trapezoid call.
 xr=X[CORE];rr=residual[CORE];metrics['core_flux_integral_over_linear_background']=value(np.sum((rr[:-1]+rr[1:])*.5*np.diff(xr)))
 return {'offset_air_angstrom':X,'requested_bary_air_angstrom':requested,'raw_flux':raw,'normalized_flux':y,'linear_background':background,'residual':residual},metrics
