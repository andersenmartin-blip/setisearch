"""Metadata-only radio motion diagnostics; no source access or readiness change.

The eccentric Keplerian calculation is a comparison model, not an adopted bank.
Phase means mean-anomaly phase at the supplied reference time, not an inferred
absolute ephemeris. No catalogue epoch or corrected telescope pointing is chosen.
"""
from __future__ import annotations

import math
import numpy as np

C_M_S = 299_792_458.0
AU_M = 149_597_870_700.0
DAY_S = 86400.0


def integration_clock(scans):
    """Return UTC integration edges/midpoints using split-JD Time arithmetic."""
    from astropy.time import Time, TimeDelta

    expected = [f"epoch{e}_{kind}" for e in range(1, 4) for kind in ("on", "off")]
    if [s["label"] for s in scans] != expected:
        raise ValueError("the explicit six alternating scan labels are required")
    rows, starts, mids, ends = [], [], [], []
    last_end = None
    for si, scan in enumerate(scans):
        h = scan["expected_header"]
        if h["dataset_shape"][0] != 16 or not math.isfinite(h["tstart_mjd"]):
            raise ValueError("finite start and exactly 16 integrations required")
        dt = float(h["tsamp_s"])
        if not math.isfinite(dt) or dt <= 0:
            raise ValueError("positive finite integration duration required")
        origin = Time(h["tstart_mjd"], format="mjd", scale="utc")
        if last_end is not None and origin < last_end:
            raise ValueError("overlapping scan intervals")
        for row in range(16):
            times = [origin + TimeDelta((row + x)*dt, format="sec") for x in (0, .5, 1)]
            starts.append(times[0]); mids.append(times[1]); ends.append(times[2])
            rows.append({"scan_index": si, "scan_label": scan["label"],
                         "integration_index": row, "duration_s": dt})
        last_end = ends[-1]
    return rows, Time(starts), Time(mids), Time(ends)


def eccentric_anomaly(mean_anomaly, eccentricity):
    """Solve E - e sin E = M on [-pi, pi), with an explicit residual check."""
    e = float(eccentricity)
    if not math.isfinite(e) or not 0 <= e < .8:
        raise ValueError("this diagnostic solver supports 0 <= e < 0.8")
    original = np.asarray(mean_anomaly, dtype=np.float64)
    if not np.isfinite(original).all():
        raise ValueError("finite mean anomaly required")
    m = (original + np.pi) % (2*np.pi) - np.pi
    result = m.copy()
    for _ in range(16):
        result -= (result - e*np.sin(result) - m)/(1 - e*np.cos(result))
    if np.max(np.abs(result - e*np.sin(result) - m), initial=0.) > 3e-14:
        raise ValueError("Kepler equation residual exceeds tolerance")
    return result


def kepler_velocity(offset_seconds, phase_cycles, *, period_days, semi_major_axis_au,
                    eccentricity, omega_deg):
    """First-order, edge-on planet LOS velocity, positive for recession.

    Preserve the legacy planet-velocity sign. This is a declared model convention,
    not proof that the archive's omega refers to the planet rather than the star.
    """
    p, a, omega = float(period_days)*DAY_S, float(semi_major_axis_au)*AU_M, math.radians(omega_deg)
    if not all(map(math.isfinite, (p, a, omega))) or min(p, a) <= 0:
        raise ValueError("positive finite period/axis and finite omega required")
    phases = np.asarray(phase_cycles, dtype=np.float64).reshape(-1, 1)
    offsets = np.asarray(offset_seconds, dtype=np.float64).reshape(1, -1)
    e = float(eccentricity)
    anomaly = eccentric_anomaly(2*np.pi*(offsets/p-phases), e)
    cos_true = (np.cos(anomaly)-e)/(1-e*np.cos(anomaly))
    sin_true = math.sqrt(1-e*e)*np.sin(anomaly)/(1-e*np.cos(anomaly))
    speed = 2*np.pi*a/(p*math.sqrt(1-e*e))
    return -speed*(cos_true*math.cos(omega)-sin_true*math.sin(omega)+e*math.cos(omega))


def circular_quadrature(offset_seconds, phase_cycles, **orbit):
    """The old two-phase construction is admitted only for a circular orbit."""
    if float(orbit["eccentricity"]) != 0.:
        raise ValueError("circular quadrature requires exact zero eccentricity")
    return unchecked_quadrature_diagnostic(offset_seconds, phase_cycles, **orbit)


def unchecked_quadrature_diagnostic(offset_seconds, phase_cycles, **orbit):
    """Intentionally apply the old form to quantify its failure, never to search."""
    phases = np.asarray(phase_cycles, dtype=np.float64).reshape(-1, 1)
    v0, vq = kepler_velocity(offset_seconds, [0., .25], **orbit)
    return np.cos(2*np.pi*phases)*v0 + np.sin(2*np.pi*phases)*vq


def kepler_acceleration_bound(*, period_days, semi_major_axis_au, eccentricity, **unused):
    """Norm of orbital acceleration at periastron; an all-phase LOS upper bound."""
    if not 0 <= eccentricity < 1 or period_days <= 0 or semi_major_axis_au <= 0:
        raise ValueError("invalid Keplerian bound parameters")
    return (2*np.pi/(period_days*DAY_S))**2 * semi_major_axis_au*AU_M/(1-eccentricity)**2


def normalized_frequency_factor(observer_correction, planet_velocity):
    """First-order emitter model, optical barycentric multiplier, carrier at t0."""
    factors = (1+np.asarray(observer_correction)/C_M_S)*(1-np.asarray(planet_velocity)/C_M_S)
    if not np.isfinite(factors).all() or np.any(factors <= 0):
        raise ValueError("invalid diagnostic frequency factors")
    return factors/factors[..., :1]
