"""Independent sort normalization and per-center-window score oracle for M43G."""
import numpy as np


def sorted_reference(raw):
    out = np.empty_like(raw)
    def median(x):
        s = np.sort(x, axis=-1); n = s.shape[-1]
        return s[..., n//2] if n%2 else (s[..., n//2-1]+s[..., n//2])/np.float32(2)
    for start in range(0, raw.shape[-1], 4096):
        x = raw[:, start:start+4096]
        m = median(x)[:, None]
        mad = median(np.abs(x-m))[:, None]
        scale = np.maximum(np.float32(1.4826)*mad, np.float32(np.finfo(np.float32).tiny))
        out[:, start:start+4096] = (x-m)/scale
    return out


def direct_reference(normalized, geometry, factors, grid, width, start, stop):
    """Materialize per-center windows; do not use the new filter/gather code."""
    centers = np.rint((factors[:, :, None]*grid.support_hz[None, None, start:stop]
                       -geometry.raw_zero_hz)/geometry.channel_width_hz).astype(np.int64)
    if centers.min() < width//2 or centers.max() >= geometry.channel_count-width//2:
        raise ValueError('reference coverage failure')
    out = np.zeros((factors.shape[0], stop-start), dtype=np.float32)
    for row in range(factors.shape[1]):
        windows = normalized[row, centers[:, row, :, None]+np.arange(-(width//2), width//2+1)] if width>1 else normalized[row, centers[:, row, :, None]]
        values = (np.sum(windows, axis=-1, dtype=np.float32)/np.sqrt(width)).astype(np.float32)
        out += values
    out /= np.float32(np.sqrt(factors.shape[1]))
    return out


