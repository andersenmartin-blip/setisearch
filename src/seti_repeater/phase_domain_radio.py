"""Conditional phase-agnostic declarations; never search-bank authorization.

The domain is a mathematical support set, with no asserted probability or
membership of the real source. Scalar geometry below is for analytic checks;
there is deliberately no bank builder, spectrum reader, or pipeline adapter.
"""
from __future__ import annotations

import hashlib
import json
import math

AU_M = 149_597_870_700.0
DAY_S = 86400.0
C_M_S = 299_792_458.0


def finite(value, name, *, lower=None, upper=None):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value)):
        raise ValueError(name + ": finite real scalar required")
    if lower is not None and value < lower:
        raise ValueError(name + ": below domain")
    if upper is not None and value > upper:
        raise ValueError(name + ": above domain")
    return float(value)


def interval(value, name, *, positive=False):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(name + ": two explicit endpoints required")
    lo, hi = [finite(x, name) for x in value]
    if lo > hi or (positive and lo <= 0):
        raise ValueError(name + ": invalid interval")
    return lo, hi


def contract_identity(contract):
    return hashlib.sha256(json.dumps(contract, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def audit_contract(contract):
    """Require the explicit restricted scenario; validity is not readiness."""
    if contract.get("schema") != "radio-phase-domain-v1":
        raise ValueError("unknown phase-domain schema")
    if contract.get("kind") != "conditional_support_not_source_membership":
        raise ValueError("conditional support declaration required")
    for field in ("physical_bank_adopted", "spectral_access_authorized",
                  "actual_source_membership_established", "templates_authorized"):
        if contract.get(field) is not False:
            raise ValueError("must remain false: " + field)
    uncertainty = contract.get("uncertainty", {})
    if (uncertainty.get("joint_probability") is not None
            or uncertainty.get("probability_claim") != "none"
            or uncertainty.get("marginal_errors_define_joint_support") is not False):
        raise ValueError("no probability or marginal-to-joint support inference")
    d = contract.get("domain", {})
    p = interval(d.get("period_days"), "period", positive=True)
    a = interval(d.get("relative_axis_au"), "relative axis", positive=True)
    e = interval(d.get("eccentricity"), "eccentricity")
    if e[0] != 0 or not 0 <= e[1] < .8:
        raise ValueError("declared analytic scope requires 0 <= e < .8")
    if d.get("eccentricity_kind") != "conditional_ceiling_not_point_or_guarantee":
        raise ValueError("eccentricity ceiling meaning missing")
    if d.get("mean_anomaly_at_reference") != "entire_circle":
        raise ValueError("all reference phases required")
    if d.get("planet_orientation_angle") != "entire_circle":
        raise ValueError("all mathematical planet orientations required")
    axis = contract.get("axis", {})
    if (axis.get("emitter") != "planet_center_of_mass"
            or axis.get("model") != "isolated_newtonian_two_body"
            or axis.get("mass_ratio_policy") != "all_nonnegative_q_no_probability"
            or axis.get("relaxation") != "0 <= projected_axis <= emitter_axis <= relative_axis_max"
            or axis.get("additional_emitter_motion_included") is not False):
        raise ValueError("explicit COM and axis-relaxation conventions required")
    c = contract.get("conventions", {})
    expected = {"line_of_sight": "z_positive_away_from_receiver",
                "phase": "M(tau)=M0+2*pi*tau/P",
                "legacy_phase_mapping": "M0=-2*pi*legacy_phase_cycles",
                "omega": "own_geometric_angle_full_circle_no_catalogue_conversion",
                "time_origin": "emission_event_corresponding_to_first_ON_reception_midpoint",
                "source_time": "conditional_inertial_coordinate_seconds",
                "input_clock": "retained_UTC_reception_offsets_not_emission_offsets",
                "carrier": "received_frequency_at_reference_after_all_declared_factors",
                "observer_factor": "abstract_positive_ratio_not_yet_physically_qualified"}
    if any(c.get(k) != v for k, v in expected.items()):
        raise ValueError("missing or changed time/frequency/angular convention")
    unresolved = contract.get("unresolved", {})
    required = ("real_domain_membership", "period_clock_scale_transfer",
                "reception_to_emission_time", "systemic_and_gravitational_terms",
                "additional_emitter_motion", "observer_pointing_and_factor",
                "exposure_channel_response", "continuous_bank_and_recovery",
                "cross_window_numeric_transfer")
    if set(unresolved) != set(required) or any(v is not None for v in unresolved.values()):
        raise ValueError("complete physical terms must remain explicitly unresolved")
    # A mathematical domain can still be unusable if the Doppler denominator
    # crosses zero. This does not test actual-source membership.
    vmax = 2*math.pi*a[1]*AU_M/(p[0]*DAY_S)*math.sqrt((1+e[1])/(1-e[1]))
    if vmax >= C_M_S:
        raise ValueError("domain permits nonpositive arrival-time derivative")
    return {"schema": "radio-phase-domain-audit-v1", "contract_sha256": contract_identity(contract),
            "mathematical_declaration_valid": True, "conditional_speed_ceiling_m_s": vmax,
            "joint_probability": None, "actual_source_membership_established": False,
            "physical_model_qualified": False, "spectral_access_authorized": False,
            "templates_authorized": False, "unresolved": unresolved.copy()}


def projected_axes(relative_axis_m, mass_ratio, sine_inclination):
    """COM identity a_p=a_rel/(1+q); no measured mass or inclination assumed."""
    a = finite(relative_axis_m, "relative axis", lower=0)
    q = finite(mass_ratio, "planet/star mass ratio", lower=0)
    s = finite(sine_inclination, "sin inclination", lower=0, upper=1)
    emitter = a/(1+q)
    return {"emitter_axis_m": emitter, "projected_axis_m": emitter*s}


def state_at_eccentric_anomaly(*, anomaly, eccentricity, period_seconds,
                              emitter_axis_m, projected_axis_m, omega):
    """Single conditional state, not a search template or actual ephemeris.

    z=-A[(cos E-e)sin omega + sqrt(1-e²)sin E cos omega].
    Its derivative matches the legacy negative-velocity convention only under
    the explicitly stated M0 mapping. No archived omega is reinterpreted.
    """
    E, w = finite(anomaly, "E"), finite(omega, "omega")
    e = finite(eccentricity, "e", lower=0, upper=.8)
    if e == .8:
        raise ValueError("e must be below .8")
    p = finite(period_seconds, "period", lower=0)
    if p == 0:
        raise ValueError("positive period required")
    a = finite(emitter_axis_m, "emitter axis", lower=0)
    A = finite(projected_axis_m, "projected axis", lower=0, upper=a)
    n, d, root = 2*math.pi/p, 1-e*math.cos(E), math.sqrt(1-e*e)
    z = -A*((math.cos(E)-e)*math.sin(w)+root*math.sin(E)*math.cos(w))
    v = n*A*(math.sin(E)*math.sin(w)-root*math.cos(E)*math.cos(w))/d
    speed2 = (n*a)**2*(1+e*math.cos(E))/d
    return {"z_m": z, "velocity_away_m_s": v, "speed_squared_m2_s2": speed2}
