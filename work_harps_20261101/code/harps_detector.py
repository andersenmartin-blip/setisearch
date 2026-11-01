"""Bounded first-stage emission-line search, independently implemented.

Method reference: Fields & Goodman 2025, arXiv:2508.08628, section III.1.
This is not their code and is not a laser identification or calibrated FAP test.
HARPS Phase-3 WAVE is air wavelength in Angstrom, in the frame in SPECSYS.
The archived ERR may be entirely NaN; this method estimates local scatter.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from scipy.ndimage import median_filter, uniform_filter1d

DEFAULTS = dict(wave_min_angstrom=3800.0, wave_max_angstrom=6900.0,
                window_pixels=101, threshold_local_std=3.5,
                minimum_run_pixels=4, maximum_run_pixels=60,
                mask_exact_zero_flux=True, gap_step_multiple=1.5)


def runs(mask):
    """Inclusive-start, exclusive-end runs, including a terminal true run."""
    changes = np.diff(np.r_[False, np.asarray(mask, dtype=bool), False].astype(int))
    return list(zip(np.flatnonzero(changes == 1).tolist(),
                    np.flatnonzero(changes == -1).tolist()))


def classify_run(size, cfg):
    if size < cfg['minimum_run_pixels']:
        return 'SHORT_RUN'
    if size > cfg['maximum_run_pixels']:
        return 'WIDE_RUN'
    return 'PRELIMINARY_EMISSION_HIT'


def _fwhm(wave, residual, peak, segment_start, segment_end):
    """Observed half-height width; no deconvolution or Gaussian fit."""
    half = residual[peak] / 2
    if not np.isfinite(half) or half <= 0:
        return None
    left = peak
    right = peak
    while left > segment_start and residual[left] > half:
        left -= 1
    while right < segment_end - 1 and residual[right] > half:
        right += 1
    if residual[left] > half or residual[right] > half:
        return None
    def cross(a, b):
        y0, y1 = residual[a], residual[b]
        if y0 == y1:
            return float(wave[a])
        return float(wave[a] + (half-y0) * (wave[b]-wave[a]) / (y1-y0))
    return cross(right-1, right) - cross(left, left+1)


def analyze_arrays(wave, flux, config=None):
    cfg = DEFAULTS | (config or {})
    window = cfg['window_pixels']
    if window < 3 or window % 2 != 1:
        raise ValueError('window_pixels must be odd and at least 3')
    w, f = np.asarray(wave, dtype=np.float64), np.asarray(flux, dtype=np.float64)
    if w.ndim != 1 or f.shape != w.shape or len(w) < window:
        raise ValueError('matching one-dimensional arrays of sufficient length required')
    if not np.all(np.isfinite(w)) or np.any(np.diff(w) <= 0):
        raise ValueError('finite, strictly increasing wavelength array required')
    valid = np.isfinite(f) & (w >= cfg['wave_min_angstrom']) & (w <= cfg['wave_max_angstrom'])
    if cfg['mask_exact_zero_flux']:
        valid &= f != 0
    step = float(np.median(np.diff(w)))
    cuts = set((np.flatnonzero(np.diff(w) > cfg['gap_step_multiple']*step)+1).tolist())
    segments = []
    for start, end in runs(valid):
        edges = [start] + sorted(x for x in cuts if start < x < end) + [end]
        segments.extend(zip(edges[:-1], edges[1:]))
    continuum = np.full_like(f, np.nan)
    scatter = np.full_like(f, np.nan)
    searched = np.zeros(len(f), dtype=bool)
    half = window//2
    searched_segments = []
    for start, end in segments:
        if end-start < window:
            continue
        values = f[start:end]
        # Segment edge padding is irrelevant: all padded windows are excluded below.
        med = median_filter(values, size=window, mode='nearest')
        mean = uniform_filter1d(values, size=window, mode='nearest')
        mean_square = uniform_filter1d(values*values, size=window, mode='nearest')
        std = np.sqrt(np.maximum(mean_square-mean*mean, 0.0))
        continuum[start:end], scatter[start:end] = med, std
        a, b = start+half, end-half
        searched[a:b] = np.isfinite(std[half:len(std)-half]) & (std[half:len(std)-half] > 0)
        searched_segments.append((a,b))
    residual = f-continuum
    contrast = np.divide(residual, scatter, out=np.full_like(f,np.nan), where=scatter>0)
    crossing = searched & (contrast >= cfg['threshold_local_std'])
    events = []
    # Process each fully supported interval separately; never merge across a wavelength gap.
    for a,b in searched_segments:
        for local_start,local_end in runs(crossing[a:b]):
            start,end = a+local_start,a+local_end
            peak = start + int(np.argmax(contrast[start:end]))
            width = _fwhm(w,residual,peak,a,b)
            events.append(dict(start_index=start,end_index_exclusive=end,
                peak_index=peak,run_pixels=end-start,
                status=classify_run(end-start,cfg),
                wave_start_angstrom=float(w[start]),wave_end_angstrom=float(w[end-1]),
                wave_peak_angstrom=float(w[peak]),peak_flux_adu=float(f[peak]),
                continuum_adu=float(continuum[peak]),local_std_adu=float(scatter[peak]),
                peak_local_contrast=float(contrast[peak]),
                observed_fwhm_angstrom=width,
                observed_fwhm_pixels=width/step if width is not None else None))
    intervals = [dict(first_index=a,last_index_exclusive=b,
                      first_center_angstrom=float(w[a]),last_center_angstrom=float(w[b-1]),
                      centers=b-a) for a,b in runs(searched)]
    result = dict(schema='HARPS_FIRST_STAGE_EMISSION_V1',config=cfg,
                  total_samples=len(w),nominal_step_angstrom=step,
                  searched_samples=int(searched.sum()),
                  sum_searched_bin_widths_angstrom=float(searched.sum()*step),
                  searched_intervals=intervals,
                  nonfinite_flux_samples=int((~np.isfinite(f)).sum()),
                  zero_flux_samples=int((f==0).sum()),
                  all_threshold_runs=events,
                  preliminary_hit_count=sum(e['status']=='PRELIMINARY_EMISSION_HIT' for e in events),
                  short_run_count=sum(e['status']=='SHORT_RUN' for e in events),
                  wide_run_count=sum(e['status']=='WIDE_RUN' for e in events),
                  interpretation='Local contrast is not calibrated SNR/sigma/FAP; hits are not identified lasers.')
    return result, dict(wave=w,flux=f,continuum=continuum,local_std=scatter,
                        local_contrast=contrast,searched=searched)


def read_spectrum(path):
    from astropy.io import fits
    with fits.open(path,memmap=False) as h:
        columns = h[1].columns
        unit = str(columns['WAVE'].unit)
        if unit.lower() not in ('angstrom','angstroms','angstroem'):
            raise ValueError('Unsupported wavelength unit: '+unit)
        wave=np.asarray(h[1].data['WAVE'][0],dtype=np.float64).copy()
        flux=np.asarray(h[1].data['FLUX'][0],dtype=np.float64).copy()
        err=np.asarray(h[1].data['ERR'][0],dtype=np.float64)
        header=h[0].header
        meta={k:header.get(k) for k in ['OBJECT','DATE-OBS','MJD-OBS','EXPTIME','SPECSYS','PROCSOFT','ORIGFILE','ARCFILE','WAVELMIN','WAVELMAX']}
        meta.update(wavelength_unit=unit,wavelength_ucd=h[1].header.get('TUCD1'),
                    flux_unit=str(columns['FLUX'].unit),finite_error_samples=int(np.isfinite(err).sum()),
                    sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),input_filename=Path(path).name,
                    raw_progenitors={k:header[k] for k in header if k.startswith('PROV')},
                    berv_km_s=header.get('HIERARCH ESO DRS BERV'))
    return wave,flux,meta


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('fits_path',type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--config',type=Path)
    parser.add_argument('--save-arrays',action='store_true')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    cpu,wall=time.process_time(),time.monotonic()
    cfg=json.loads(args.config.read_text()) if args.config else None
    w,f,meta=read_spectrum(args.fits_path)
    result,arrays=analyze_arrays(w,f,cfg)
    result['input']=meta
    result['cpu_seconds']=time.process_time()-cpu
    result['wall_seconds']=time.monotonic()-wall
    (args.output/'result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    events=result['all_threshold_runs']
    if events:
        with (args.output/'all_threshold_runs.csv').open('w',newline='') as out:
            writer=csv.DictWriter(out,fieldnames=list(events[0]));writer.writeheader();writer.writerows(events)
    else:
        (args.output/'all_threshold_runs.csv').write_text('status,wave_peak_angstrom\n')
    if args.save_arrays:
        np.savez_compressed(args.output/'search_arrays.npz',**arrays)
    print(json.dumps({k:result[k] for k in ['total_samples','searched_samples','preliminary_hit_count','short_run_count','wide_run_count','cpu_seconds','wall_seconds']}))


if __name__=='__main__':
    main()
