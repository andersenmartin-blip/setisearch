"""Offline motion-contract diagnostics, never a physical-bank approval path.

Archive limits are not central values. A complete metadata declaration is only
a prerequisite; these functions cannot authorize spectra or scientific use.
"""
from __future__ import annotations

import math
import numpy as np

from .motion_radio import AU_M, C_M_S, DAY_S

CORE_PARAMETERS = ("period", "axis", "eccentricity", "omega")


def central_solution_audit(parameters, conventions):
    """Fail closed on missing/limited/mixed inputs to a *central* orbit.

    A phase-agnostic domain need not supply a periastron epoch. It still needs
    its own uncertainty/coverage contract; this audit does not create one.
    Flag 0 is the supplied point-value declaration; every other flag is refused.
    """
    blockers = []
    phase_policy = conventions.get("phase_policy")
    if phase_policy not in ("all_phases", "epoch_anchored"):
        blockers.append("phase_policy_unresolved")
    required = CORE_PARAMETERS + (("periastron_epoch",) if phase_policy == "epoch_anchored" else ())
    references = set()
    for name in required:
        item = parameters.get(name, {})
        value = item.get("value")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            blockers.append(name + ":missing_or_nonfinite")
        elif ((name in ("period", "axis") and value <= 0)
              or (name == "eccentricity" and not 0 <= value < 1)):
            blockers.append(name + ":outside_domain")
        flag = item.get("limit_flag")
        if type(flag) is not int or flag != 0:
            blockers.append(name + ":not_declared_point_estimate")
        reference = item.get("reference")
        if not isinstance(reference, str) or not reference.strip():
            blockers.append(name + ":reference_missing")
        else:
            references.add(reference)
    if len(references) > 1:
        blockers.append("mixed_orbital_solutions")
    # BJD is not a time scale and is deliberately not accepted here.
    if conventions.get("time_scale") not in ("TDB", "TCB", "TT", "UTC"):
        blockers.append("time_scale_unresolved")
    if conventions.get("omega_body") not in ("stellar_reflex", "planet"):
        blockers.append("omega_body_unresolved")
    if conventions.get("axis_definition") not in ("relative", "planet_barycentric"):
        blockers.append("axis_definition_unresolved")
    if conventions.get("axis_definition") == "relative":
        if not conventions.get("mass_conversion_evidence"):
            blockers.append("relative_to_transmitter_axis_unresolved")
    return {"metadata_consistent": not blockers, "blockers": blockers,
            "references": sorted(references), "required_parameters": list(required),
            "physical_model_qualified": False, "spectral_access_authorized": False}


def carrier_minimax(target_hz, template_factor):
    """Exact finite-time minimax over a free positive carrier q, q*G(t).

    E = max_ik |y_i G_k - y_k G_i|/(G_i+G_k). Positive y,G ensure q>0.
    Long double limits cancellation; this is not an interval-arithmetic proof.
    The result relaxes a bounded/discrete carrier grid, so its error is a lower
    bound on that grid's best achievable maximum center-track discrepancy.
    """
    y = np.asarray(target_hz, dtype=np.longdouble)
    g = np.asarray(template_factor, dtype=np.longdouble)
    if (y.ndim != 1 or y.size == 0 or y.shape != g.shape
            or not np.isfinite(y).all() or not np.isfinite(g).all()
            or np.any(y <= 0) or np.any(g <= 0)):
        raise ValueError("equal nonempty positive finite vectors required")
    pair_error = np.abs(y[:, None]*g[None, :] - y[None, :]*g[:, None]) / (g[:, None]+g[None, :])
    active = np.unravel_index(np.argmax(pair_error), pair_error.shape)
    error = pair_error[active]
    lower, upper = np.max((y-error)/g), np.min((y+error)/g)
    tolerance = 32*np.finfo(np.longdouble).eps*max(np.max(y), error)
    if lower > upper + tolerance or upper <= 0:
        raise ArithmeticError("minimax carrier interval inconsistent")
    q = (lower+upper)/2
    residual = y-q*g
    observed = np.max(np.abs(residual))
    if abs(observed-error) > tolerance:
        raise ArithmeticError("minimax residual does not match pair bound")
    return {"error_hz": float(error), "carrier_hz": float(q),
            "active_pair_local_indices": [int(i) for i in active],
            "max_residual_hz": float(observed),
            "residual_hz": [float(x) for x in residual],
            "numeric_consistency_tolerance_hz": float(tolerance)}


def kepler_domain_bounds(*, period_days, semi_major_axis_au, eccentricity_max,
                         integration_seconds, frequency_hz):
    """Conditional idealized two-body bounds; no posterior/domain adoption.

    Central P,a, all phases, e in [0,e_max], |LOS projection| <= 1. Observer
    multiplier is held fixed: the interpolation bound covers the emitter only.
    """
    values = (period_days, semi_major_axis_au, integration_seconds, frequency_hz)
    if not all(math.isfinite(v) and v > 0 for v in values):
        raise ValueError("positive finite period, axis, duration and frequency required")
    if not math.isfinite(eccentricity_max) or not 0 <= eccentricity_max < 1:
        raise ValueError("elliptic eccentricity bound required")
    period, axis = period_days*DAY_S, semi_major_axis_au*AU_M
    n = 2*math.pi/period
    radius = axis*(1-eccentricity_max)
    mu = n*n*axis**3
    velocity = n*axis*math.sqrt((1+eccentricity_max)/(1-eccentricity_max))
    if velocity >= C_M_S:
        raise ValueError("positive first-order Doppler denominator required")
    acceleration = mu/radius**2
    jerk = 2*mu*velocity/radius**3
    error = frequency_hz*jerk*integration_seconds**2/(8*(C_M_S-velocity))
    return {"speed_m_s": velocity, "acceleration_m_s2": acceleration,
            "jerk_m_s3": jerk, "emitter_interpolation_bound_hz": error,
            "scope": "conditional emitter only; observer held fixed; central P/a",
            "joint_probability_coverage": None, "physical_model_qualified": False}


def accuracy_contract(terms, required_names, tolerance_hz, scope):
    """A partial sum is never a full accuracy certificate.

    Only qualified, finite nonnegative upper bounds with the exact common scope
    can be summed. An explicit None stays missing, not zero. This diagnostic
    also never grants a physical-bank or spectral permission.
    """
    if not math.isfinite(tolerance_hz) or tolerance_hz <= 0 or not scope:
        raise ValueError("finite positive tolerance and explicit scope required")
    if not required_names or len(set(required_names)) != len(required_names):
        raise ValueError("nonempty unique required term names required")
    known, missing = {}, {}
    for name in required_names:
        term = terms.get(name, {})
        value = term.get("bound_hz")
        if term.get("qualified") is not True:
            missing[name] = "unqualified_or_missing"
        elif term.get("scope") != scope:
            missing[name] = "scope_mismatch"
        elif (not isinstance(value, (int, float)) or isinstance(value, bool)
              or not math.isfinite(value) or value < 0):
            missing[name] = "invalid_or_missing_upper_bound"
        else:
            known[name] = value
    total = math.fsum(known.values()) if not missing else None
    return {"status": "BLOCKED" if missing else ("WITHIN_TOLERANCE" if total <= tolerance_hz else "EXCEEDS_TOLERANCE"),
            "known_terms_hz": known, "unresolved_terms": missing,
            "total_bound_hz": total, "tolerance_hz": tolerance_hz, "scope": scope,
            "physical_model_qualified": False, "spectral_access_authorized": False}
