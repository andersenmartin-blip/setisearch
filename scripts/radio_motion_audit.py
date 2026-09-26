"""Reproduce the HD1461 metadata-only motion audit, with no HTTP or spectra."""
from __future__ import annotations
import hashlib
import gzip
import importlib.metadata as metadata
import json
import math
from pathlib import Path
import platform
import numpy as np
from astropy import units as u
from astropy.coordinates import EarthLocation, SkyCoord, solar_system_ephemeris
from astropy.time import Time
from astropy.utils import iers
from seti_repeater import motion_radio as m

ROOT = Path(__file__).resolve().parents[1]
CONFIG = 'config/radio_hd1461_motion_audit_20260926.json'
OUT = ROOT/'results_radio_motion_2026-09-26'


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(name, value):
    data=(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()
    (OUT/name).write_bytes(gzip.compress(data,mtime=0) if name.endswith('.gz') else data)


def run():
    cfg = json.loads((ROOT/CONFIG).read_text())
    for key in ('preparation_contract', 'astrometry_snapshot'):
        if sha(ROOT/cfg[key]) != cfg[key+'_sha256']:
            raise ValueError(f'{key} pin changed')
    runtime = {key: metadata.version(key) for key in cfg['runtime'] if key != 'python'}
    runtime['python'] = platform.python_version()
    if runtime != cfg['runtime']:
        raise ValueError('motion-audit runtime differs from recorded environment')
    contract = json.loads((ROOT/cfg['preparation_contract']).read_text())
    star = json.loads((ROOT/cfg['astrometry_snapshot']).read_text())[0]
    if contract['stage'] != 'preparation-only-no-spectral-access' or contract['windows']:
        raise ValueError('the original closed preparation contract must remain unchanged')
    scans = contract['scans']
    labels, starts, mids, ends = m.integration_clock(scans)
    offsets = (mids-mids[0]).sec
    on = np.array([row['scan_label'].endswith('_on') for row in labels])
    old_mid = np.array([scan['expected_header']['tstart_mjd'] + (r+.5)*scan['expected_header']['tsamp_s']/m.DAY_S
                        for scan in scans for r in range(16)])
    clock_error_s = (Time(old_mid, format='mjd', scale='utc')-mids).sec
    mids.precision = starts.precision = ends.precision = 9
    clock = []
    for i, row in enumerate(labels):
        clock.append(row | {'start_utc': starts[i].isot, 'mid_utc': mids[i].isot,
            'end_utc': ends[i].isot, 'mid_mjd_utc': float(mids[i].mjd),
            'mid_offset_seconds': float(offsets[i]),
            'legacy_single_mjd_error_seconds': float(clock_error_s[i])})
    timing = []
    for si, scan in enumerate(scans):
        first, last = si*16, (si+1)*16-1
        timing.append({'scan': scan['label'], 'start_utc': starts[first].isot,
            'end_utc': ends[last].isot, 'exposure_s': float((ends[last]-starts[first]).sec),
            'gap_after_s': None if si == 5 else float((starts[last+1]-ends[last]).sec)})

    # All EOPs must be final IERS-B entries. Never fetch an online table.
    iers.conf.auto_download = False
    earth_orientation = iers.IERS_B.open(iers.IERS_B_FILE)
    all_times = Time(list(starts)+list(mids)+list(ends))
    _, status = earth_orientation.ut1_utc(all_times, return_status=True)
    _, _, polar_status = earth_orientation.pm_xy(all_times, return_status=True)
    if not np.all(status == iers.FROM_IERS_B) or not np.all(polar_status == iers.FROM_IERS_B):
        raise ValueError('the audit requires final IERS-B coverage at every timestamp')
    site = cfg['observatory']
    location = EarthLocation.from_geodetic(site['longitude_deg']*u.deg, site['latitude_deg']*u.deg,
                                          site['height_m']*u.m)
    directions = [{'id': 'catalogue_fixed', 'ra_deg': star['ra'], 'dec_deg': star['dec']}]
    for scan in scans:
        if scan['role'] == 'on':
            h = scan['expected_header']
            directions.append({'id': scan['label']+'_header_fixed',
                               'ra_deg': 15*h['src_raj_hours'], 'dec_deg': h['src_dej_deg']})
    corrections = {}
    coordinate_results = []
    f = cfg['comparison_frequency_hz']; df = abs(scans[0]['expected_header']['foff_mhz'])*1e6
    with iers.earth_orientation_table.set(earth_orientation), solar_system_ephemeris.set('builtin'):
        catalogue = SkyCoord(star['ra']*u.deg, star['dec']*u.deg, frame='icrs')
        for direction in directions:
            target = SkyCoord(direction['ra_deg']*u.deg, direction['dec_deg']*u.deg, frame='icrs')
            corr = target.radial_velocity_correction(obstime=all_times, location=location).to_value(u.m/u.s)
            start_v, mid_v, end_v = np.split(corr, 3)
            corrections[direction['id']] = mid_v
            factor = 1+mid_v/m.C_M_S
            anchored = factor/factor[0]
            base = 1+corrections['catalogue_fixed']/m.C_M_S
            anchored_difference = f*(anchored-base/base[0])
            coordinate_results.append(direction | {
                'separation_from_catalogue_arcmin': float(catalogue.separation(target).arcmin),
                'observer_correction_m_s_min': float(mid_v.min()),
                'observer_correction_m_s_max': float(mid_v.max()),
                'fixed_barycentric_carrier_sweep_hz': float(f*np.ptp(factor)),
                'max_exposure_endpoint_sweep_hz': float(f*np.max(np.abs(end_v-start_v))/m.C_M_S),
                'max_absolute_difference_from_catalogue_hz': float(f*np.max(np.abs(mid_v-corrections['catalogue_fixed']))/m.C_M_S),
                'max_difference_after_common_first_carrier_hz': float(np.max(np.abs(anchored_difference))),
                'midpoint_correction_m_s': mid_v.tolist(),
                'midpoint_factor': factor.tolist(),
                'first_carrier_anchored_difference_hz': anchored_difference.tolist()})

    orbit = dict(period_days=star['pl_orbper'], semi_major_axis_au=star['pl_orbsmax'],
                 eccentricity=star['pl_orbeccen'], omega_deg=star['pl_orblper'])
    phases = np.arange(cfg['phase_samples'])/cfg['phase_samples']
    exact = m.kepler_velocity(offsets, phases, **orbit)
    approximation = m.unchecked_quadrature_diagnostic(offsets, phases, **orbit)
    observer = corrections['catalogue_fixed']
    exact_factors = m.normalized_frequency_factor(observer, exact)
    approx_factors = m.normalized_frequency_factor(observer, approximation)
    residual = f*(exact_factors-approx_factors)
    maxima = np.max(np.abs(residual), axis=1)
    max_on = np.max(np.abs(residual[:, on]), axis=1)
    worst_phase, worst_row = np.unravel_index(np.argmax(np.abs(residual)), residual.shape)
    v_edges = m.kepler_velocity(np.concatenate([(starts-mids[0]).sec, (ends-mids[0]).sec]), phases, **orbit)
    sweep = f*np.abs(v_edges[:,96:]-v_edges[:,:96])/m.C_M_S
    per_phase = []
    for i, phase in enumerate(phases):
        per_phase.append({'phase_cycles': float(phase), 'max_quadrature_error_after_carrier_anchor_hz': float(maxima[i]),
            'max_on_quadrature_error_after_carrier_anchor_hz': float(max_on[i]),
            'max_orbital_exposure_endpoint_sweep_hz': float(sweep[i].max())})
    # This is a radial-only illustrative relativity comparison, not a full orbital redshift.
    radial_factor = (1+observer/m.C_M_S)*np.sqrt((1-exact/m.C_M_S)/(1+exact/m.C_M_S))
    radial_factor /= radial_factor[:, :1]
    radial_difference = f*np.abs(radial_factor-exact_factors)
    acceleration_bound = m.kepler_acceleration_bound(**orbit)
    max_tsamp = max(row['duration_s'] for row in labels)
    circular = orbit | {'eccentricity': 0.}
    cv = m.kepler_velocity(offsets, phases, **circular)
    cq = m.circular_quadrature(offsets, phases, **circular)

    result = {
        'schema': 'radio-metadata-motion-result-v1', 'status': 'AUDIT_COMPLETE_SPECTRA_HELD',
        'spectral_values_read': False, 'source_http_requests': 0,
        'pointing_status': cfg['source_status'], 'adopted_coordinate': None, 'adopted_motion_bank': None,
        'source_contract_sha256': sha(ROOT/cfg['preparation_contract']),
        'runtime': runtime, 'iers_b_sha256': sha(iers.IERS_B_FILE),
        'iers_b_first_last_mjd': [float(earth_orientation['MJD'][0].value), float(earth_orientation['MJD'][-1].value)],
        'all_ut1_and_polar_motion_status_final_iers_b': True, 'ephemeris': 'builtin',
        'comparison_frequency_hz': f, 'native_channel_width_hz': df,
        'scan_timing': timing, 'integration_count': 96, 'total_exposure_s': sum(row['duration_s'] for row in labels),
        'elapsed_first_start_to_last_end_s': float((ends[-1]-starts[0]).sec),
        'first_to_last_scan_start_s': float((starts[80]-starts[0]).sec),
        'first_to_last_midpoint_s': float(offsets[-1]),
        'max_legacy_single_mjd_clock_difference_s': float(np.max(np.abs(clock_error_s))),
        'catalogue_proper_motion_25_year_scale_arcsec': math.hypot(star['sy_pmra'],star['sy_pmdec'])*25/1000,
        'coordinate_scenarios': coordinate_results,
        'keplerian_comparison': {'parameters': orbit, 'phase_samples': cfg['phase_samples'],
            'phase_reference': 'first ON midpoint; no absolute periastron interpretation',
            'max_circular_quadrature_residual_m_s': float(np.max(np.abs(cv-cq))),
            'max_eccentric_quadrature_error_anchored_hz': float(maxima.max()),
            'max_eccentric_quadrature_error_anchored_native_channels': float(maxima.max()/df),
            'max_on_eccentric_quadrature_error_anchored_hz': float(max_on.max()),
            'worst_sample_phase_cycles': float(phases[worst_phase]), 'worst_row': int(worst_row),
            'sampled_phases_exceeding_one_native_channel': int(np.count_nonzero(maxima > df)),
            'max_sampled_orbital_exposure_endpoint_sweep_hz': float(sweep.max()),
            'max_sampled_orbital_midpoint_difference_from_endpoint_linear_interpolation_hz': float(
                f*np.max(np.abs(exact-(v_edges[:, :96]+v_edges[:, 96:])/2))/m.C_M_S),
            'all_phase_los_acceleration_upper_bound_m_s2': acceleration_bound,
            'all_phase_orbital_exposure_frequency_sweep_upper_bound_hz': f*acceleration_bound*max_tsamp/m.C_M_S,
            'all_phase_orbital_exposure_frequency_sweep_upper_bound_native_channels': f*acceleration_bound*max_tsamp/m.C_M_S/df,
            'max_anchored_radial_only_relativistic_vs_first_order_hz': float(radial_difference.max()),
            'continuous_phase_completeness_certified': False,
            'orbital_parameter_uncertainties_covered': False},
        'missing_for_physical_ephemeris': ['same-scan pointing provenance', 'astrometric reference epoch and parameter provenance',
            'one consistent orbital solution with uncertainty and time system', 'planet-versus-stellar omega convention',
            'finite-exposure signal response and Doppler accuracy budget'],
        'notes': ['Fixed-direction scenarios are comparisons, not corrected source coordinates.',
            'Endpoint sweeps are computed for sampled phases; the separate acceleration bound covers all phase angles for the stated idealized P/a/e.',
            'Orbital motion is an edge-on first-order central-parameter model. Absolute Tper and systemic RV are not used.',
            'The radial-only relativistic comparison omits transverse motion; it is a counterexample to silently assuming first-order precision, not a physical orbital correction.',
            'The old circular-source context remains unchanged. No old result is reinterpreted as an eccentric-source search.']}
    OUT.mkdir(exist_ok=True)
    write('clock.json', {'rows': clock})
    write('phase_comparison.json.gz', {'frequency_hz': f, 'phase_cases': per_phase,
          'worst_sample': {'phase_cycles': float(phases[worst_phase]),
             'exact_anchored_factor': exact_factors[worst_phase].tolist(),
             'false_quadrature_anchored_factor': approx_factors[worst_phase].tolist(),
             'difference_hz': residual[worst_phase].tolist()}})
    write('result.json', result)
    print(json.dumps({k: result[k] for k in ('status','elapsed_first_start_to_last_end_s','max_legacy_single_mjd_clock_difference_s','keplerian_comparison')}, indent=2))


if __name__ == '__main__': run()
