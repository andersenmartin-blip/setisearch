"""Calibrated local PRF translation and explicit finite-exposure integration.

This is a forward operator, not a detector or a quaternion-to-pixel estimator.
Unsupported pixels are NaN with an explicit coverage mask; no tail is invented.
"""
from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Response:
    flux: np.ndarray
    uncertainty_envelope: np.ndarray
    covered: np.ndarray


@dataclass(frozen=True)
class LocalPRF:
    row_axis: np.ndarray
    column_axis: np.ndarray
    values: np.ndarray
    uncertainties: np.ndarray

    def __post_init__(self):
        y, x = np.asarray(self.row_axis, dtype=float), np.asarray(self.column_axis, dtype=float)
        a, u = np.asarray(self.values, dtype=float), np.asarray(self.uncertainties, dtype=float)
        if (y.ndim != 1 or x.ndim != 1 or min(len(y), len(x)) < 2
                or not np.all(np.diff(y) > 0) or not np.all(np.diff(x) > 0)
                or a.shape != (len(y), len(x)) or u.shape != a.shape
                or not all(np.isfinite(v).all() for v in (x, y, a, u))
                or np.any(a < 0) or np.any(u < 0)):
            raise ValueError('invalid calibration axes or nonnegative image arrays')
        for name, value in [('row_axis', y), ('column_axis', x), ('values', a), ('uncertainties', u)]:
            object.__setattr__(self, name, value)

    def sample(self, pixel_xy, source_xy):
        pixels = np.asarray(pixel_xy, dtype=float)
        source = np.asarray(source_xy, dtype=float)
        if pixels.ndim == 0 or pixels.shape[-1] != 2 or not pixels.size or source.shape != (2,) or not np.isfinite(pixels).all() or not np.isfinite(source).all():
            raise ValueError('finite x/y pixel centers and one finite x/y source required')
        dx, dy = (pixels-source).T if pixels.ndim == 2 else np.moveaxis(pixels-source, -1, 0)
        x, y = self.column_axis, self.row_axis
        eps = 1e-11
        valid = (dx >= x[0]-eps) & (dx <= x[-1]+eps) & (dy >= y[0]-eps) & (dy <= y[-1]+eps)
        dx, dy = np.clip(dx, x[0], x[-1]), np.clip(dy, y[0], y[-1])
        ix = np.clip(np.searchsorted(x, dx, side='right')-1, 0, len(x)-2)
        iy = np.clip(np.searchsorted(y, dy, side='right')-1, 0, len(y)-2)
        fx, fy = (dx-x[ix])/(x[ix+1]-x[ix]), (dy-y[iy])/(y[iy+1]-y[iy])
        weights = [(1-fx)*(1-fy), fx*(1-fy), (1-fx)*fy, fx*fy]
        indices = [(iy, ix), (iy, ix+1), (iy+1, ix), (iy+1, ix+1)]
        def interpolate(array):
            value = sum(w*array[index] for w, index in zip(weights, indices, strict=True))
            return np.where(valid, value, np.nan)
        return Response(interpolate(self.values), interpolate(self.uncertainties), valid)


class PRFCatalog:
    """Read sealed images and original MATLAB coordinate/shift metadata."""
    def __init__(self, root):
        from astropy.io import fits
        root = Path(root)
        inv = json.loads((root/'results_ls7k_inputs/inventory.json').read_text())
        original = json.loads((root/'results_ls7m_prf_inputs/inventory.json').read_text())
        self.entries = {}
        for model in original['models']:
            desc = model['field_descriptions']
            file = next(m for m in inv['prf_models'] if m['name'] == model['fits_file'])
            with fits.open(root/'results_ls7k_inputs'/file['path']) as hdus:
                local = LocalPRF(np.asarray(desc['prfRow']['values']), np.asarray(desc['prfColumn']['values']),
                                 hdus[0].data.copy(), hdus[1].data.copy())
            self.entries[(model['ccd'], model['grid_row'], model['grid_col'])] = {
                'model': local, 'file': model['fits_file'],
                'row_shift': desc['rowShift']['values'], 'column_shift': desc['columnShift']['values']}

    def local(self, ccd, field_xy, *, calibration_column_offset):
        """Offset is explicit: compare 0 and -44 without an implicit default.

        It changes the field interpolation coordinate, not the relative source
        position within a science stamp. Field shape is fixed during translation.
        """
        x, y = np.asarray(field_xy, dtype=float)
        x += float(calibration_column_offset)
        rows = np.array(sorted({r for c, r, col in self.entries if c == ccd}))
        cols = np.array(sorted({col for c, r, col in self.entries if c == ccd}))
        if not np.isfinite([x,y]).all() or not rows.size or not (cols[0] <= x <= cols[-1] and rows[0] <= y <= rows[-1]):
            raise ValueError('field position outside the calibration grid')
        i = min(max(np.searchsorted(cols,x,side='right')-1,0),len(cols)-2)
        j = min(max(np.searchsorted(rows,y,side='right')-1,0),len(rows)-2)
        fx, fy = (x-cols[i])/(cols[i+1]-cols[i]), (y-rows[j])/(rows[j+1]-rows[j])
        nodes = [(j,i,(1-fx)*(1-fy)),(j,i+1,fx*(1-fy)),(j+1,i,(1-fx)*fy),(j+1,i+1,fx*fy)]
        records, flux, uncertainty, reference = [], 0., 0., None
        for row, col, weight in nodes:
            if weight == 0: continue
            entry = self.entries[(ccd, int(rows[row]), int(cols[col]))]
            if entry['row_shift'] != 0 or entry['column_shift'] != 0:
                raise ValueError('original nonzero shift annotation requires interpretation')
            model = entry['model']
            if reference is not None:
                np.testing.assert_array_equal(reference.row_axis,model.row_axis)
                np.testing.assert_array_equal(reference.column_axis,model.column_axis)
            reference = model
            flux = flux+weight*model.values
            uncertainty = uncertainty+weight*model.uncertainties
            records.append({'file':entry['file'],'weight':float(weight)})
        return LocalPRF(reference.row_axis,reference.column_axis,flux,uncertainty), records


def live_intervals(*, readout_phase_seconds):
    """Ten 1.98-second integrations in 2-second frames, centered on cadence 0.

    readout_phase_seconds is the integration start offset within each frame;
    [0, .02] is allowed. Its actual mission value is not established here.
    """
    phase = float(readout_phase_seconds)
    if not np.isfinite(phase) or not 0 <= phase <= .02:
        raise ValueError('integration start phase must be in [0, 0.02] seconds')
    starts = -10.+phase+2.*np.arange(10)
    return np.column_stack([starts,starts+1.98])


def _intervals(value, label):
    a = np.asarray(value,dtype=float).reshape(-1,2)
    if not np.isfinite(a).all() or np.any(a[:,1] <= a[:,0]) or np.any(a[1:,0] < a[:-1,1]):
        raise ValueError(label+' must be finite, sorted, positive and disjoint')
    return a


def integrate(model, pixel_xy, trajectory_time, trajectory_xy, intervals, *, pulse_intervals=None):
    """Exact integration of the piecewise-bilinear model along a linear path.

    Split on trajectory knots and every spatial interpolation boundary. Two
    Gauss points then exactly integrate each quadratic segment, within floating
    arithmetic. Divide by total live time, including intervals without a pulse.
    An envelope is a positive weighted sum of supplied uncertainty entries;
    it is not a calibrated confidence interval or a sector-specific error model.
    """
    pixels = np.asarray(pixel_xy,dtype=float)
    if pixels.ndim == 0 or pixels.shape[-1] != 2 or not pixels.size or not np.isfinite(pixels).all():
        raise ValueError('finite nonempty x/y pixel centers required')
    t, xy = np.asarray(trajectory_time,dtype=float), np.asarray(trajectory_xy,dtype=float)
    live = _intervals(intervals,'live intervals')
    if (t.ndim != 1 or len(t) < 2 or xy.shape != (len(t),2) or not np.isfinite(t).all()
            or not np.isfinite(xy).all() or not np.all(np.diff(t)>0) or not len(live)
            or t[0] > live[0,0] or t[-1] < live[-1,1]):
        raise ValueError('strictly increasing trajectory must cover all live intervals')
    pulses = live if pulse_intervals is None else _intervals(pulse_intervals,'pulse intervals')
    gates = [(max(a,c),min(b,d)) for a,b in live for c,d in pulses if max(a,c)<min(b,d)]
    total_live = np.sum(live[:,1]-live[:,0])
    shape = pixels.shape[:-1]
    flux, envelope, covered = np.zeros(shape), np.zeros(shape), np.ones(shape,dtype=bool)
    flat = pixels.reshape(-1,2)
    thresholds = [np.unique(flat[:,0,None]-model.column_axis),np.unique(flat[:,1,None]-model.row_axis)]
    quadrature_pieces = 0
    for lo,hi in gates:
        coarse = sorted({lo,hi,*t[(t>lo)&(t<hi)].tolist()})
        for a,b in zip(coarse[:-1],coarse[1:],strict=True):
            start = np.array([np.interp(a,t,xy[:,k]) for k in range(2)])
            stop = np.array([np.interp(b,t,xy[:,k]) for k in range(2)])
            fractions = [0.,1.]
            for k in range(2):
                delta = stop[k]-start[k]
                if delta != 0:
                    f = (thresholds[k]-start[k])/delta
                    fractions.extend(f[(f>0)&(f<1)].tolist())
            cuts = np.unique(fractions)
            for left,right in zip(cuts[:-1],cuts[1:],strict=True):
                mid,half = (left+right)/2,(right-left)/2
                if half <= 0: continue
                for g in [-1/np.sqrt(3),1/np.sqrt(3)]:
                    position = start+(mid+g*half)*(stop-start)
                    sample = model.sample(pixels,position)
                    weight = (b-a)*half
                    covered &= sample.covered
                    flux += weight*np.nan_to_num(sample.flux,nan=0.)
                    envelope += weight*np.nan_to_num(sample.uncertainty_envelope,nan=0.)
                quadrature_pieces += 1
    return Response(np.where(covered,flux/total_live,np.nan),
                    np.where(covered,envelope/total_live,np.nan),covered), quadrature_pieces
