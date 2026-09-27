"""Conditional flat-spacetime emitter timing; no observer or search integration.

Stationary distant receiver, fixed LOS, system barycentre at rest, isolated
Keplerian COM emitter. Scalar examples and analytic inequalities only. Neither
floating-point solver brackets nor evaluated bounds are interval certificates.
"""
from __future__ import annotations

import math

from .phase_domain_radio import (AU_M, C_M_S, DAY_S, audit_contract, finite,
                                 state_at_eccentric_anomaly)


def domain_norm_bounds(contract):
    audit_contract(contract)
    d = contract["domain"]
    p, a, e = d["period_days"][0]*DAY_S, d["relative_axis_au"][1]*AU_M, d["eccentricity"][1]
    n = 2*math.pi/p
    speed = n*a*math.sqrt((1+e)/(1-e))
    acceleration = n*n*a/(1-e)**2
    jerk = 2*n**3*a*math.sqrt((1+e)/(1-e))/(1-e)**3
    return {"n_max_rad_s":n, "axis_max_m":a, "eccentricity_max":e,
            "speed_m_s":speed, "acceleration_m_s2":acceleration, "jerk_m_s3":jerk,
            "beta_max":speed/C_M_S}


def conditional_error_bounds(contract, reception_extent_seconds, reference_hz):
    """Bounds on three omitted terms of one conditional emitter model only."""
    T = finite(reception_extent_seconds, "absolute reception extent", lower=0)
    f = finite(reference_hz, "reference carrier", lower=0)
    if f == 0: raise ValueError("positive carrier required")
    b = domain_norm_bounds(contract)
    B, a, acc, e, n = b["beta_max"], b["axis_max_m"], b["acceleration_m_s2"], b["eccentricity_max"], b["n_max_rad_s"]
    tau = T/(1-B)
    delay = min(B*tau, 2*a/C_M_S)
    delta_beta = min(2*B, acc*tau/C_M_S)
    delta_radial_square = min(B*B, 2*B*delta_beta)
    # For each orbit the speed² range from apo- to periastron is explicit.
    # In particular gamma is constant for e=0 even when radial speed varies.
    kepler_speed_square_range = 4*e*(n*a/C_M_S)**2/(1-e*e)
    delta_speed_square = min(B*B, 2*B*acc*tau/C_M_S, kepler_speed_square_range)
    wrong_clock = f*acc*delay/(C_M_S*(1-B))
    reciprocal = f*delta_radial_square/(1-B)**2
    transverse = f*delta_speed_square/(2*(1-B)**2)
    return {"schema":"radio-conditional-time-error-bounds-v1", "norm_bounds":b,
        "reception_extent_seconds":T, "source_extent_seconds":tau,
        "reference_hz":f, "arrival_derivative_min":1-B, "arrival_derivative_max":1+B,
        "variable_light_travel_delay_seconds":delay,
        "normalized_wrong_clock_bound_hz":wrong_clock,
        "normalized_reciprocal_vs_linear_bound_hz":reciprocal,
        "normalized_transverse_bound_hz":transverse,
        "conditional_emitter_comparison_sum_hz":math.fsum((wrong_clock, reciprocal, transverse)),
        "scope":"fixed-LOS stationary-receiver flat-spacetime emitter; observer ratio one",
        "is_total_physical_error_bound":False, "total_physical_error_bound_hz":None,
        "physical_model_qualified":False, "spectral_access_authorized":False,
        "numeric_interval_certificate":False}


def validate_parameters(contract, parameters):
    audit_contract(contract)
    required = {"period_seconds", "emitter_axis_m", "projected_axis_m", "eccentricity",
                "mean_anomaly_reference", "omega"}
    if set(parameters) != required: raise ValueError("exact scalar parameter fields required")
    p = {k:finite(v, k) for k,v in parameters.items()}
    d = contract["domain"]
    if not d["period_days"][0]*DAY_S <= p["period_seconds"] <= d["period_days"][1]*DAY_S:
        raise ValueError("period outside conditional support")
    if not 0 <= p["projected_axis_m"] <= p["emitter_axis_m"] <= d["relative_axis_au"][1]*AU_M:
        raise ValueError("axis outside declared relaxation")
    if not 0 <= p["eccentricity"] <= d["eccentricity"][1]:
        raise ValueError("eccentricity outside conditional support")
    return p


def eccentric_anomaly_scalar(M, e):
    """Newton scalar solve with an explicit residual; restricted e<.8."""
    M, e = finite(M, "mean anomaly"), finite(e, "e", lower=0, upper=.8)
    if abs(M) > 1e6 or e == .8:
        raise ValueError("outside bounded scalar-solver scope")
    m = math.remainder(M, 2*math.pi)
    E = m
    for _ in range(16): E -= (E-e*math.sin(E)-m)/(1-e*math.cos(E))
    if abs(E-e*math.sin(E)-m) > 2e-14: raise ArithmeticError("Kepler residual exceeds scope")
    return E


def source_state(tau, parameters):
    tau = finite(tau, "source offset")
    p = parameters
    E = eccentric_anomaly_scalar(p["mean_anomaly_reference"]+2*math.pi*tau/p["period_seconds"], p["eccentricity"])
    return state_at_eccentric_anomaly(anomaly=E, eccentricity=p["eccentricity"],
        period_seconds=p["period_seconds"], emitter_axis_m=p["emitter_axis_m"],
        projected_axis_m=p["projected_axis_m"], omega=p["omega"])


def solve_emission_time(contract, reception_seconds, parameters):
    """Invert s=tau+(z(tau)-z(0))/c, with monotonic-domain brackets."""
    p = validate_parameters(contract, parameters)
    s = finite(reception_seconds, "reception offset")
    B = domain_norm_bounds(contract)["beta_max"]
    origin = source_state(0, p)
    def residual(tau): return tau+(source_state(tau, p)["z_m"]-origin["z_m"])/C_M_S-s
    lo, hi = sorted((s/(1-B), s/(1+B)))
    # Small rounding slack is numerical engineering, not interval arithmetic.
    slack = 128*math.ulp(max(1., abs(s)))
    lo -= slack; hi += slack
    if residual(lo) > slack or residual(hi) < -slack:
        raise ArithmeticError("arrival map did not bracket source time")
    for _ in range(80):
        mid = (lo+hi)/2
        if hi-lo <= 2e-10 or mid in (lo, hi): break
        if residual(mid) > 0: hi = mid
        else: lo = mid
    tau = (lo+hi)/2
    err = residual(tau)
    if abs(err) > 2e-9: raise ArithmeticError("arrival residual exceeds diagnostic tolerance")
    return {"emission_seconds":tau, "arrival_residual_seconds":err,
            "numeric_bracket_width_seconds":hi-lo, "interval_certified":False}


def normalized_factors(reference_state, current_state):
    """Coordinate-frequency reciprocal, proper-frequency SR, and first order."""
    b0 = reference_state["velocity_away_m_s"]/C_M_S
    b1 = current_state["velocity_away_m_s"]/C_M_S
    x0 = reference_state["speed_squared_m2_s2"]/C_M_S**2
    x1 = current_state["speed_squared_m2_s2"]/C_M_S**2
    for x in (x0, x1):
        finite(x, "speed squared/c²", lower=0)
        if x >= 1: raise ValueError("subluminal total speed required")
    for b,x in ((b0,x0),(b1,x1)):
        finite(b, "radial beta")
        if abs(b) >= 1 or b*b > x+8*math.ulp(max(x, 1e-300)):
            raise ValueError("radial velocity inconsistent with total speed")
    reciprocal = (1+b0)/(1+b1)
    proper = reciprocal*math.sqrt((1-x1)/(1-x0))
    return {"coordinate_frequency_reciprocal":reciprocal,
            "proper_frequency_relativistic":proper,
            "first_order_coordinate":(1-b1)/(1-b0)}


def compare_scalar_models(contract, reception_seconds, parameters, reference_hz):
    """One endpoint comparison, never a detector/coverage witness."""
    p = validate_parameters(contract, parameters)
    f = finite(reference_hz, "carrier", lower=0)
    if f == 0: raise ValueError("positive carrier required")
    solved = solve_emission_time(contract, reception_seconds, p)
    ref = source_state(0, p)
    retarded = normalized_factors(ref, source_state(solved["emission_seconds"], p))
    unretarded = normalized_factors(ref, source_state(reception_seconds, p))
    return {"parameters":p, "reception_seconds":reception_seconds, **solved,
        "retarded_factors":retarded, "unretarded_first_order_factor":unretarded["first_order_coordinate"],
        "wrong_clock_difference_hz":f*(retarded["first_order_coordinate"]-unretarded["first_order_coordinate"]),
        "reciprocal_difference_hz":f*(retarded["coordinate_frequency_reciprocal"]-retarded["first_order_coordinate"]),
        "transverse_difference_hz":f*(retarded["proper_frequency_relativistic"]-retarded["coordinate_frequency_reciprocal"]),
        "combined_emitter_difference_hz":f*(retarded["proper_frequency_relativistic"]-unretarded["first_order_coordinate"]),
        "total_physical_error_hz":None, "detector_or_template_evaluated":False}
