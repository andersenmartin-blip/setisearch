"""Closed-data LS8B numerical repair: same OLS rule with flux centering.

This is separate from the frozen original scorer and does not rewrite history.
"""
import numpy as np

SIDE = 12
GUARD = 2
DURATIONS = (1, 2, 3)
SCREEN = 8.5

def _scale(side_flux, side_err, residual):
    mad = np.median(np.abs(residual - np.median(residual)))
    robust = 1.4826 * mad
    formal = np.median(side_err)
    floor = 1e-12 * abs(np.median(side_flux))
    return float(max(robust, formal, floor, 1e-12))

def stable_score_window(time_day, flux, error, status, event, start, duration, cadence_seconds):
    time_day=np.asarray(time_day,float); flux=np.asarray(flux,float)
    error=np.asarray(error,float); status=np.asarray(status); event=np.asarray(event)
    lo=start-GUARD-SIDE
    hi=start+duration+GUARD+SIDE
    if lo < 0 or hi > len(flux):
        return None
    context=np.arange(lo,hi)
    usable=(np.isfinite(time_day[context]) & np.isfinite(flux[context]) &
            np.isfinite(error[context]) & (error[context] > 0) &
            (status[context] == 0))
    if not usable.all():
        return None
    dt=np.diff(time_day[context])*86400.0
    if not ((dt >= .5*cadence_seconds) & (dt <= 1.5*cadence_seconds)).all():
        return None
    left=np.arange(start-GUARD-SIDE,start-GUARD)
    right=np.arange(start+duration+GUARD,start+duration+GUARD+SIDE)
    side=np.concatenate([left,right])
    ev=np.arange(start,start+duration)
    t0=float(np.mean(time_day[ev]))
    xs=(time_day[side]-t0)*86400.0
    xe=(time_day[ev]-t0)*86400.0
    X=np.column_stack([np.ones(len(side)),xs])
    XE=np.column_stack([np.ones(duration),xe])
    offset=float(np.median(flux[side]))
    beta=np.linalg.lstsq(X,flux[side]-offset,rcond=None)[0]
    residual=(flux[side]-offset)-X@beta
    sigma=_scale(flux[side],error[side],residual)
    predicted=XE@beta
    excess=float(np.sum((flux[ev]-offset)-predicted))
    xsum=XE.sum(axis=0)
    leverage=float(xsum @ np.linalg.inv(X.T@X) @ xsum)
    denom=float(sigma*np.sqrt(duration+leverage))
    return {
        'start':int(start),'duration':int(duration),
        'event_indices':ev.tolist(),'context_start':int(lo),'context_stop':int(hi),
        'bjd_mid':float(np.mean(time_day[ev])),
        'sigma_electrons':sigma,'baseline_event_sum_electrons':float(duration*offset+predicted.sum()),
        'excess_electrons':excess,'denominator_electrons':denom,
        'leverage':leverage,'score':float(excess/denom),
        'event_or':int(np.bitwise_or.reduce(event[ev].astype(np.int64))),
        'context_event_or':int(np.bitwise_or.reduce(event[context].astype(np.int64)))
    }
