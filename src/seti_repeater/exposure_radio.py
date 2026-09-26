"""Idealized finite-exposure digital injections in native channel coordinates.

This models uniform time averaging, a linearly moving top-hat line and ideal
rectangular channel cells. It is not a measured GBT/polyphase filter response.
Power is conserved before native normalization; no detection truth is consulted.
"""
import math
import numpy as np


def linear_exposure_profile(channel_count, start_center, end_center, intrinsic_width_channels):
    """Unit total digital power averaged over one constant-rate exposure.

    Channel j is [j-0.5, j+0.5]. A zero-width stationary line exactly on an
    internal cell boundary splits equally. Swept support must be fully present.
    The finite-width integral uses exact trapezoids between every overlap kink.
    """
    if type(channel_count) is not int or channel_count < 2:
        raise ValueError('integer native channel count >= 2 required')
    a, b = sorted((float(start_center), float(end_center)))
    width = float(intrinsic_width_channels)
    if not all(map(math.isfinite, (a, b, width))) or width < 0:
        raise ValueError('finite centers and nonnegative intrinsic width required')
    if a-width/2 < -.5 or b+width/2 > channel_count-.5:
        raise ValueError('complete swept line support is outside native extraction')
    profile = np.zeros(channel_count, dtype=np.float64)
    lower = max(0, math.floor(a-width/2-.5))
    upper = min(channel_count, math.ceil(b+width/2+.5)+1)
    centers = np.arange(lower, upper, dtype=np.float64)
    left, right = centers-.5, centers+.5
    if width == 0:
        if a == b:
            values = ((left < a) & (a < right)).astype(np.float64)
            values += .5*((left == a) | (right == a))
        else:
            values = np.maximum(0, np.minimum(right, b)-np.maximum(left, a))/(b-a)
    elif a == b:
        values = np.maximum(0, np.minimum(right, a+width/2)-np.maximum(left, a-width/2))/width
    else:
        # Each channel's overlap is piecewise linear in the line center.
        knots = np.sort(np.clip(np.stack([left-width/2, left+width/2,
            right-width/2, right+width/2, np.full_like(left,a), np.full_like(left,b)]), a, b), axis=0)
        overlap = np.maximum(0, np.minimum(right[None,:],knots+width/2)
                              - np.maximum(left[None,:],knots-width/2))/width
        values = np.sum(np.diff(knots,axis=0)*(overlap[:-1]+overlap[1:])/2,axis=0)/(b-a)
    profile[lower:upper] = values
    if (not np.isfinite(profile).all() or np.any(profile < 0)
            or abs(float(profile.sum())-1.) > 2e-10):
        raise ValueError('ideal exposure integral failed power conservation')
    return profile


def add_linear_exposure(raw_rows, start_centers, end_centers, *, intrinsic_width_channels, total_power):
    """Add exposure-averaged power to a copy of ascending float32 raw powers."""
    raw = np.asarray(raw_rows)
    starts, ends = np.asarray(start_centers), np.asarray(end_centers)
    if (raw.dtype != np.dtype('<f4') or raw.ndim != 2 or not np.isfinite(raw).all()
            or starts.shape != (raw.shape[0],) or ends.shape != starts.shape):
        raise ValueError('finite float32 raw rows and one pair of centers per row required')
    power = float(total_power)
    if not math.isfinite(power) or power < 0:
        raise ValueError('nonnegative finite total digital power required')
    added = raw.copy()
    for row, (start, end) in enumerate(zip(starts, ends)):
        profile = linear_exposure_profile(raw.shape[1], start, end, intrinsic_width_channels)
        added[row] += np.asarray(power*profile, dtype='<f4')
    if not np.isfinite(added).all():
        raise ValueError('raw injection overflow')
    return added
