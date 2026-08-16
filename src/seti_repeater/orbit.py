"""Celestial and Keplerian Doppler models used by the search."""

from __future__ import annotations

import numpy as np
from astropy import units as u
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.time import Time
from astropy.utils import iers


iers.conf.auto_download = False
C_M_S = 299_792_458.0
AU_M = 149_597_870_700.0
DAY_S = 86_400.0


def make_location(config: dict) -> EarthLocation:
    return EarthLocation.from_geodetic(
        lon=config["longitude_deg"] * u.deg,
        lat=config["latitude_deg"] * u.deg,
        height=config["height_m"] * u.m,
    )


def make_target(config: dict) -> SkyCoord:
    return SkyCoord(
        ra=config["ra"], dec=config["dec"],
        pm_ra_cosdec=config["pm_ra_cosdec_mas_yr"] * u.mas / u.yr,
        pm_dec=config["pm_dec_mas_yr"] * u.mas / u.yr,
        distance=(config["parallax_mas"] * u.mas).to(u.pc, equivalencies=u.parallax()),
        radial_velocity=config["radial_velocity_km_s"] * u.km / u.s,
        obstime=Time(config["reference_epoch_jyear"], format="jyear"),
    )


def planet_radial_velocity(
    times: Time,
    projected_scale: float,
    phase_offset_cycles: float,
    orbit: dict,
) -> np.ndarray:
    """Line-of-sight orbital velocity for a projected Keplerian template."""
    period = orbit["period_days"]
    eccentricity = orbit["eccentricity"]
    t_periastron = orbit["t_periastron_bjd_tdb"] + phase_offset_cycles * period
    mean_anomaly = np.mod(2 * np.pi * (times.tdb.jd - t_periastron) / period, 2 * np.pi)
    eccentric_anomaly = mean_anomaly.copy()
    for _ in range(12):
        eccentric_anomaly -= (
            eccentric_anomaly - eccentricity * np.sin(eccentric_anomaly) - mean_anomaly
        ) / (1 - eccentricity * np.cos(eccentric_anomaly))
    true_anomaly = 2 * np.arctan2(
        np.sqrt(1 + eccentricity) * np.sin(eccentric_anomaly / 2),
        np.sqrt(1 - eccentricity) * np.cos(eccentric_anomaly / 2),
    )
    speed = (
        2 * np.pi * orbit["semi_major_axis_au"] * AU_M
        / (period * DAY_S * np.sqrt(1 - eccentricity**2))
    )
    omega = orbit["omega_rad"]
    return -projected_scale * speed * (
        np.cos(true_anomaly + omega) + eccentricity * np.cos(omega)
    )


def celestial_frequency_factor(
    times: Time,
    projected_scale: float,
    phase_offset_cycles: float,
    target: SkyCoord,
    location: EarthLocation,
    orbit: dict,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Observed/rest frequency ratio plus its two velocity components."""
    moving_source = target.apply_space_motion(new_obstime=times)
    observer_correction = moving_source.radial_velocity_correction(
        obstime=times, location=location
    ).to_value(u.m / u.s)
    planet_velocity = planet_radial_velocity(
        times, projected_scale, phase_offset_cycles, orbit
    )
    factor = (1 + observer_correction / C_M_S) * (1 - planet_velocity / C_M_S)
    return factor, observer_correction, planet_velocity

