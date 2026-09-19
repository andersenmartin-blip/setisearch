"""Frozen LS8D temporal maps, paired corrections and descriptive shape fits."""
import numpy as np


def temporal_map(times, cube, side, event, valid=None):
    a = np.asarray(cube, float)
    valid = np.isfinite(a[np.r_[side, event]]).all(axis=0) if valid is None else valid
    out = np.full(a.shape[1:], np.nan)
    if not valid.any():
        return out
    y = a[:, valid]
    offset = np.median(y[side], axis=0)
    x = np.asarray(times, float)
    xm = np.mean(x[side]); xs = x[side]-xm
    ys = y[side]-offset
    intercept = np.mean(ys, axis=0)
    slope = xs @ (ys-intercept) / (xs @ xs)
    out[valid] = np.sum((y[event]-offset)-intercept-(x[event]-xm)[:, None]*slope, axis=0)
    return out


def fit(y, columns):
    y = np.asarray(y, float)
    if len(y) < len(columns) or not len(y):
        return {'available': False, 'reason': 'TOO_FEW_PIXELS'}
    x = np.column_stack(columns)
    norms = np.linalg.norm(x, axis=0)
    xn = x / np.where(norms > 0, norms, 1.)
    b, _, rank, singular = np.linalg.lstsq(xn, y, rcond=1e-12)
    if rank != len(columns):
        return {'available': False, 'reason': 'RANK_DEFICIENT', 'rank': int(rank)}
    residual = y-xn@b
    energy = float(y@y)
    return {'available': True, 'pixels': len(y), 'rank': int(rank),
            'condition': float(singular[0]/singular[-1]),
            'coefficients': (b/norms).tolist(),
            'rms': float(np.sqrt(np.mean(residual**2))),
            'explained': 1.-float(residual@residual)/energy if energy > 0 else None}


def project_columns(a, valid):
    counts = valid.sum(axis=0)
    means = np.divide(np.where(valid, a, 0.).sum(axis=0), counts,
                      out=np.zeros(a.shape[1]), where=counts>0)
    result = np.broadcast_to(means, a.shape).copy()
    result[~valid] = np.nan
    energy = float(np.sum(a[valid]**2))
    fraction = float(np.sum(result[valid]**2))/energy if energy>0 else None
    return result, fraction


def classify(conventions, sign):
    for c in conventions.values():
        if not c['aperture_complete'] or c['delta_over_cor'] is None or not c['sign_matches_l2']:
            return 'UNRESOLVED_WITHIN_FIXED_SCOPE'
    if all(abs(c['delta_over_cor'])>=.5 or abs(c['column_delta_over_cor'])>=.5
           for c in conventions.values()):
        return 'CORRECTION_LINKED'
    for c in conventions.values():
        b, d = c['fits']['COR']['brightness'], c['fits']['COR']['displacement']
        if not (b['available'] and d['available'] and b['explained'] is not None and
                d['explained'] is not None and d['explained']>=.8 and d['explained']-b['explained']>=.2):
            return 'UNRESOLVED_WITHIN_FIXED_SCOPE'
    return 'SPATIALLY_STRUCTURED'


def analyze(times, cal, cor, smear, side, event, center, sign):
    used = np.r_[side,event]
    common = np.isfinite(cal[used]).all(axis=0)&np.isfinite(cor[used]).all(axis=0)
    maps = {'CAL': temporal_map(times,cal,side,event,common),
            'COR': temporal_map(times,cor,side,event,common),
            'SMEAR': temporal_map(times,smear,side,event)}
    maps['DELTA'] = maps['COR']-maps['CAL']
    dcol, dfrac = project_columns(maps['DELTA'], common)
    _, cfrac = project_columns(maps['COR'], common)
    yy,xx = np.indices(common.shape)
    means = {}
    for kind,cube in [('CAL',cal),('COR',cor)]:
        mean = np.full(common.shape,np.nan)
        mean[common] = np.mean(cube[side][:,common],axis=0)
        means[kind] = mean
    results = {}
    for convention in (0,1):
        cx,cy = center[0]-convention,center[1]-convention
        radius2 = (xx-cx)**2+(yy-cy)**2
        geom = radius2<=25**2; aperture=geom&common
        annulus = (radius2>30**2)&(radius2<=40**2)&common
        sums = {k:float(np.sum(maps[k][aperture])) for k in ('CAL','COR','DELTA')}
        floor = 512*np.finfo(float).eps*max(1.,float(np.mean(np.sum(np.abs(cor[side][:,aperture]),axis=1))))
        valid_den = abs(sums['COR'])>floor
        fits = {}
        for kind in ('CAL','COR'):
            if not annulus.any():
                fits[kind] = {m:{'available':False,'reason':'NO_BACKGROUND_ANNULUS'} for m in ('brightness','displacement','combined')}
                continue
            p = means[kind]-np.median(means[kind][annulus])
            dx,dy = np.full_like(p,np.nan),np.full_like(p,np.nan)
            dx[:,1:-1]=(p[:,2:]-p[:,:-2])/2
            dy[1:-1,:]=(p[2:,:]-p[:-2,:])/2
            mask = aperture&np.isfinite(dx)&np.isfinite(dy)
            values, px, gx, gy = maps[kind][mask],p[mask],dx[mask],dy[mask]
            one=np.ones(len(values))
            fits[kind]={'brightness':fit(values,[px,one]),
                        'displacement':fit(values,[gx,gy,one]),
                        'combined':fit(values,[px,gx,gy,one])}
        outside=(radius2>35**2)&common&np.isfinite(maps['SMEAR'])[None,:]
        sv=np.broadcast_to(maps['SMEAR'],common.shape)[outside]
        smear_fit=fit(maps['DELTA'][outside],[np.ones(len(sv)),sv])
        l1=float(np.sum(np.abs(maps['COR'][common])))
        complete = bool(common[geom].all() and 25<=cx<=common.shape[1]-26 and 25<=cy<=common.shape[0]-26)
        results[f'C{convention}']={'center':[float(cx),float(cy)],'aperture_pixels':int(geom.sum()),
            'valid_aperture_pixels':int(aperture.sum()),'aperture_complete':complete,
            'event_sums':sums,'cor_zero_floor':float(floor),
            'delta_over_cor':sums['DELTA']/sums['COR'] if valid_den else None,
            'column_delta_over_cor':float(np.sum(dcol[aperture]))/sums['COR'] if valid_den else None,
            'sign_matches_l2':bool((sums['COR']>0)==(sign=='positive')) if valid_den else False,
            'cor_l1_aperture_fraction':float(np.sum(np.abs(maps['COR'][aperture])))/l1 if l1>0 else None,
            'smearing_delta_fit':smear_fit,'fits':fits}
    summary={'common_pixels':int(common.sum()),'cor_column_energy_fraction':cfrac,
             'delta_column_energy_fraction':dfrac,'conventions':results,
             'classification':classify(results,sign)}
    maps['COMMON']=common
    return summary,maps
