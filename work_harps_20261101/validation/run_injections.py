"""Execute the frozen, paired HARPS injection plan; never select or tune locations.

This module does not open FITS files on import. Execution requires the explicit
--execute-frozen-plan switch after the project lead authorizes the locked plan.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def matching_hits(result, center_index, tolerance_pixels):
    """An accepted run matches iff its nearest sample is at most 2 bins away."""
    matched = []
    for event in result['all_threshold_runs']:
        if event['status'] != 'PRELIMINARY_EMISSION_HIT':
            continue
        distance = max(event['start_index'] - center_index,
                       center_index - (event['end_index_exclusive'] - 1), 0)
        if distance <= tolerance_pixels:
            matched.append(dict(event, center_to_run_distance_pixels=distance))
    return matched


def nearest_index(wave, center):
    """Nearest center with lower-index tie within floating-point roundoff."""
    distances = np.abs(wave - center)
    tolerance = 32 * np.finfo(np.float64).eps * abs(center)
    return int(np.flatnonzero(distances <= distances.min() + tolerance)[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=Path(__file__).with_name('VALIDATION_PLAN.json'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execute-frozen-plan', action='store_true')
    args = parser.parse_args()
    if not args.execute_frozen_plan:
        parser.error('Execution requires project-lead authorization and --execute-frozen-plan')
    plan_path = args.plan.resolve()
    base = plan_path.parent.parent
    plan = json.loads(plan_path.read_text())
    expected_plan_hash = plan_path.with_suffix('.sha256').read_text().split()[0]
    if digest(plan_path) != expected_plan_hash:
        raise RuntimeError('Validation plan hash mismatch')
    for relative, expected in plan['source_sha256'].items():
        if digest(base / relative) != expected:
            raise RuntimeError('Frozen source hash mismatch: ' + relative)
    if Path(__file__).resolve() != (base / 'validation/run_injections.py').resolve():
        raise RuntimeError('Run the frozen script from its registered path')
    inputs = plan['backgrounds_chronological']
    if len(inputs) != 3 or len(plan['anchor_wavelengths_angstrom']) != 4 or len(plan['amplitude_factors']) != 4:
        raise RuntimeError('The frozen design must contain exactly 48 paired trials')
    # All provenance hashes are checked before any FITS arrays are opened.
    for item in inputs:
        path = base / item['relative_path']
        if path.stat().st_size != item['bytes'] or digest(path) != item['sha256']:
            raise RuntimeError('Validation FITS identity mismatch: ' + str(path))
    sys.path.insert(0, str(base / 'code'))
    from harps_detector import analyze_arrays, read_spectrum
    import astropy
    import scipy
    config = json.loads((base / 'code/DETECTOR_CONFIG.json').read_text())
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    start_wall = time.monotonic()
    receipt = dict(schema='HARPS_PAIRED_INJECTION_RUN_V1', status='STARTED',
        started_utc=started, plan_sha256=expected_plan_hash,
        source_sha256=plan['source_sha256'],
        software=dict(python=platform.python_version(), numpy=np.__version__,
                      scipy=scipy.__version__, astropy=astropy.__version__),
        backgrounds=inputs,
        interpretation=plan['interpretation'])
    write_json(out / 'RUN_RECEIPT.json', receipt)
    controls, trials, errors = [], [], []
    half_patch = plan['patch_pixels'] // 2
    half_noise = plan['unmodified_noise_window_pixels'] // 2
    tolerance = plan['recovery_tolerance_pixels']
    try:
        for background_index, item in enumerate(inputs):
            wave, flux, metadata = read_spectrum(base / item['relative_path'])
            if metadata['sha256'] != item['sha256']:
                raise RuntimeError('Input changed during read: ' + item['relative_path'])
            if metadata['SPECSYS'] != 'BARYCENT' or metadata['wavelength_ucd'] != 'em.wl;obs.atmos':
                raise RuntimeError('Unexpected frame or air-wavelength UCD')
            if not np.all(np.isfinite(wave)) or np.any(np.diff(wave) <= 0):
                raise RuntimeError('Wavelength vector is not finite and strictly increasing')
            for anchor in plan['anchor_wavelengths_angstrom']:
                geometry_id = f'b{background_index + 1}_a{anchor:.2f}'.replace('.', 'p')
                directory = out / geometry_id
                directory.mkdir()
                base_index = nearest_index(wave, anchor)
                start, end = base_index - half_patch, base_index + half_patch + 1
                common = dict(geometry_id=geometry_id, background_index=background_index,
                    background_file=Path(item['relative_path']).name, anchor_angstrom=anchor,
                    subpixel_phase=item['subpixel_phase'], base_index_full_spectrum=base_index,
                    patch_start_index_full_spectrum=start, patch_end_index_exclusive_full_spectrum=end,
                    patch_pixels=plan['patch_pixels'], wavelength_unit='Angstrom',
                    wavelength_medium='air', spectral_frame='BARYCENT', flux_unit=metadata['flux_unit'])
                geometry_recorded = False
                try:
                    if start < 0 or end > len(wave):
                        raise ValueError('Registered patch exceeds spectrum boundary')
                    w, f = wave[start:end].copy(), flux[start:end].copy()
                    step = float(np.median(np.diff(w)))
                    if not np.allclose(np.diff(w), step, rtol=0, atol=1e-8):
                        raise ValueError('Patch wavelength bins are not uniform within 1e-8 Angstrom')
                    center = float(w[half_patch] + item['subpixel_phase'] * step)
                    center_index = nearest_index(w, center)
                    noise_start = center_index - half_noise
                    noise_end = center_index + half_noise + 1
                    noise_window = f[noise_start:noise_end]
                    if len(noise_window) != 101 or not np.all(np.isfinite(noise_window)) or np.any(noise_window == 0):
                        raise ValueError('Unmodified 101-pixel noise window is invalid or zero-filled')
                    noise = float(np.std(noise_window, ddof=0))
                    if not np.isfinite(noise) or noise <= 0:
                        raise ValueError('Unmodified local population standard deviation is not positive')
                    fwhm = center / plan['resolving_power']
                    gaussian_sigma = fwhm / (2 * np.sqrt(2 * np.log(2)))
                    shape = np.exp(-0.5 * ((w - center) / gaussian_sigma) ** 2)
                    common.update(center_angstrom=center, nearest_center_index_patch=center_index,
                        nearest_center_index_full_spectrum=start + center_index,
                        nearest_center_wavelength_angstrom=float(w[center_index]),
                        nominal_step_angstrom=step, injected_fwhm_angstrom=fwhm,
                        injected_fwhm_pixels=fwhm / step, unmodified_local_population_std_adu=noise,
                        noise_window_start_index_patch=noise_start,
                        noise_window_end_index_exclusive_patch=noise_end,
                        noise_window_first_center_angstrom=float(w[noise_start]),
                        noise_window_last_center_angstrom=float(w[noise_end - 1]),
                        noise_window_pixels=101, noise_ddof=0)
                    control_result, control_arrays = analyze_arrays(w, f, config)
                    if not control_arrays['searched'][center_index]:
                        raise ValueError('Nearest center is not searchable in the unmodified control')
                    control_matches = matching_hits(control_result, center_index, tolerance)
                    control = dict(common, status='EVALUATED', control_hit=bool(control_matches),
                        matching_hits=control_matches, detector_result=control_result, input_metadata=metadata)
                    controls.append(control)
                    geometry_recorded = True
                    write_json(directory / 'control.json', control)
                    np.savez_compressed(directory / 'control_arrays.npz', **control_arrays)
                    for amplitude in plan['amplitude_factors']:
                        addition = amplitude * noise * shape
                        injected_result, injected_arrays = analyze_arrays(w, f + addition, config)
                        matches = matching_hits(injected_result, center_index, tolerance)
                        trial = dict(common, amplitude_factor=amplitude, status='EVALUATED',
                            continuous_peak_added_adu=amplitude * noise,
                            sampled_peak_added_adu=float(addition.max()),
                            control_hit=bool(control_matches), recovered=bool(matches),
                            recovered_without_control_hit=bool(matches) and not bool(control_matches),
                            matching_hits=matches, detector_result=injected_result)
                        trials.append(trial)
                        write_json(directory / f'injection_{amplitude:02d}.json', trial)
                        np.savez_compressed(directory / f'injection_{amplitude:02d}_arrays.npz',
                                            added_flux=addition, **injected_arrays)
                except (ValueError, IndexError) as error:
                    if geometry_recorded:
                        raise  # A processing error after starting trials is a failed run, not a new geometry.
                    # Preserve every registered trial: do not move a center or invent a noise value.
                    failed = dict(common, status='NOT_EVALUABLE', reason=str(error))
                    errors.append(failed)
                    controls.append(failed)
                    write_json(directory / 'not_evaluable.json', failed)
                    for amplitude in plan['amplitude_factors']:
                        trials.append(dict(failed, amplitude_factor=amplitude, recovered=None,
                                           control_hit=None, recovered_without_control_hit=None))
        evaluated = [trial for trial in trials if trial['status'] == 'EVALUATED']
        summary = dict(schema='HARPS_PAIRED_INJECTION_SUMMARY_V1',
            registered_geometries=12, registered_trials=48,
            evaluated_geometries=sum(c['status'] == 'EVALUATED' for c in controls),
            evaluated_trials=len(evaluated), not_evaluable_trials=48-len(evaluated),
            control_hits=sum(c.get('control_hit', False) for c in controls),
            recovered_trials=sum(t['recovered'] for t in evaluated),
            recovered_without_control_hit=sum(t['recovered_without_control_hit'] for t in evaluated),
            by_amplitude=[dict(amplitude_factor=a,
                evaluated=sum(t['amplitude_factor'] == a for t in evaluated),
                recovered=sum(t['amplitude_factor'] == a and t['recovered'] for t in evaluated),
                recovered_without_control_hit=sum(t['amplitude_factor'] == a and t['recovered_without_control_hit'] for t in evaluated))
                for a in plan['amplitude_factors']],
            by_anchor=[dict(anchor_angstrom=a,
                evaluated=sum(t['anchor_angstrom'] == a for t in evaluated),
                recovered=sum(t['anchor_angstrom'] == a and t['recovered'] for t in evaluated))
                for a in plan['anchor_wavelengths_angstrom']],
            interpretation=plan['interpretation'], errors=errors)
        if len(trials) != 48 or len(controls) != 12:
            raise RuntimeError('Registered trial/control count changed unexpectedly')
        write_json(out / 'controls.json', controls)
        write_json(out / 'trials.json', trials)
        write_json(out / 'summary.json', summary)
        flat_trials = [{k:v for k,v in trial.items() if k not in ('matching_hits','detector_result')}
                       for trial in trials]
        fieldnames = sorted({key for trial in flat_trials for key in trial})
        with (out / 'trials.csv').open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(flat_trials)
        receipt.update(status='COMPLETED', finished_utc=datetime.now(timezone.utc).isoformat(),
                       wall_seconds=time.monotonic()-start_wall, summary=summary)
        write_json(out / 'RUN_RECEIPT.json', receipt)
        print(json.dumps(summary, indent=2))
    except Exception as error:
        receipt.update(status='FAILED', error=repr(error),
                       finished_utc=datetime.now(timezone.utc).isoformat(),
                       wall_seconds=time.monotonic()-start_wall)
        write_json(out / 'RUN_RECEIPT.json', receipt)
        raise


if __name__ == '__main__':
    main()
