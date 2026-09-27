"""Analytic conditional Lipschitz envelopes and a grid *count*, no templates.

All derivatives concern the retarded proper-frequency model in the published
stationary-receiver setting. The sufficient Cartesian construction is not a
necessary bank-size bound, a physical-source certificate, or a runtime test.
"""
from __future__ import annotations

import math

from .phase_domain_radio import AU_M, C_M_S, DAY_S, contract_identity, finite
from .time_transfer_radio import domain_norm_bounds

PARAMETERS=("period_days", "emitter_axis_au", "projection", "eccentricity",
            "mean_anomaly_rad", "omega_rad")


def sensitivity_envelope(contract, reception_extent_seconds, reference_hz):
    T=finite(reception_extent_seconds,"extent",lower=0)
    f=finite(reference_hz,"carrier",lower=0)
    if f==0:raise ValueError("positive carrier required")
    b=domain_norm_bounds(contract)
    n,a,e,V,A,B=(b[k] for k in ("n_max_rad_s","axis_max_m","eccentricity_max",
                               "speed_m_s","acceleration_m_s2","beta_max"))
    P=contract["domain"]["period_days"][0]*DAY_S
    U=T/(1-B);d=1-e;k=math.sqrt(1-e*e);w=(n*a/C_M_S)**2
    # Z, Vtheta, X at fixed source time, for P(seconds), a(m), projection,
    # e, M0 and omega. x=|v|²/c². All are global upper bounds, not derivatives
    # of the *bound* V itself, and apply to the same orbit throughout time.
    raw={
        "period_days":(a*n*U/(P*d), V/P+n*n*a*U/(P*d**3),
                       2*B*B/P+2*w*e*n*U/(P*d**3), DAY_S),
        "emitter_axis_au":(1+e,V/a,2*B*B/a,AU_M),
        "projection":(a*(1+e),V,0.,1.),
        "eccentricity":(a*(1/k+1/d),n*a*(e/(k*d)+1/d**2+1/d**3),2*w/d**3,1.),
        "mean_anomaly_rad":(a/d,n*a/d**3,2*w*e/d**3,1.),
        "omega_rad":(a*(1+e),V,0.,1.)}
    ranges={"period_days":contract["domain"]["period_days"],
        "emitter_axis_au":[0,contract["domain"]["relative_axis_au"][1]],
        "projection":[0,1],"eccentricity":contract["domain"]["eccentricity"],
        "mean_anomaly_rad":[0,2*math.pi],"omega_rad":[0,2*math.pi]}
    rows={}
    for name,(z,v,x,unit) in raw.items():
        z,v,x=z*unit,v*unit,x*unit
        time_derivative=2*z/(C_M_S*(1-B))
        retarded_v=v+A*time_derivative
        retarded_x=x+2*V*A/C_M_S**2*time_derivative
        reciprocal=v/(C_M_S-V)+(C_M_S+V)*retarded_v/(C_M_S-V)**2
        gamma=(retarded_x+x)/(2*(1-B*B)**1.5)
        proper=reciprocal/math.sqrt(1-B*B)+(1+B)/(1-B)*gamma
        rows[name]={"support":ranges[name],"periodic":name in ("mean_anomaly_rad","omega_rad"),
            "fixed_source_z_derivative_m_per_unit":z,
            "fixed_source_v_derivative_m_s_per_unit":v,
            "fixed_source_speed_square_over_c2_derivative_per_unit":x,
            "implicit_source_time_derivative_seconds_per_unit":time_derivative,
            "retarded_v_derivative_m_s_per_unit":retarded_v,
            "retarded_speed_square_over_c2_derivative_per_unit":retarded_x,
            "normalized_reciprocal_derivative_per_unit":reciprocal,
            "gamma_ratio_derivative_per_unit":gamma,
            "proper_frequency_lipschitz_hz_per_unit":f*proper}
    return {"schema":"radio-conditional-motion-sensitivity-v1",
        "domain_sha256":contract_identity(contract),"reception_extent_seconds":T,
        "source_extent_seconds":U,"reference_hz":f,"norm_bounds":b,"parameters":rows,
        "coordinate_chart":"a_p and projection lambda with A=a_p*lambda; two circle angles",
        "scope":"conditional retarded proper frequency; stationary receiver; observer ratio one",
        "analytic_envelope":True,"numeric_interval_certificate":False,
        "physical_model_qualified":False,"spectral_access_authorized":False}


def circular_distance(left,right):
    x,y=finite(left,"left angle"),finite(right,"right angle")
    return abs(math.remainder(x-y,2*math.pi))


def sufficient_cover_count(envelope,tolerance_hz,clock_rows,clock_samples_per_row=3):
    """Count an equal-error-allocation midpoint/circular cover; never allocate it."""
    eps=finite(tolerance_hz,"center reporting tolerance",lower=0)
    if eps==0:raise ValueError("positive tolerance required")
    if type(clock_rows) is not int or clock_rows<=0 or type(clock_samples_per_row) is not int or clock_samples_per_row<=0:
        raise ValueError("positive integer sampling shape required")
    if set(envelope.get("parameters",{}))!=set(PARAMETERS):
        raise ValueError("complete six-coordinate envelope required")
    allocation=eps/len(PARAMETERS);product=1;rows={}
    for name in PARAMETERS:
        p=envelope["parameters"][name]
        width=p["support"][1]-p["support"][0]
        L=finite(p["proper_frequency_lipschitz_hz_per_unit"],name+" derivative",lower=0)
        finite(width,name+" support width",lower=0)
        ratio=width*L/(2*allocation)
        if not math.isfinite(ratio):raise ValueError("cover count exceeds arithmetic scope")
        # Slightly outward rounding of the count is engineering conservatism;
        # the derivative constants themselves are not interval certified.
        count=max(1,math.ceil(math.nextafter(ratio,math.inf)))
        radius=width/(2*count)
        rows[name]={"nodes":count,"max_parameter_distance":radius,
            "allocated_error_hz":allocation,"bounded_contribution_hz":L*radius,
            "geometry":"circle equally spaced" if p["periodic"] else "interval cell midpoints"}
        product*=count
    bounded_sum=math.fsum(row["bounded_contribution_hz"] for row in rows.values())
    if bounded_sum>eps*(1+1e-14):raise ArithmeticError("computed cover violates allocated tolerance")
    return {"schema":"radio-sufficient-cartesian-cover-count-v1","tolerance_hz":eps,
        "tolerance_is_detector_gate":False,"dimensions":rows,"product_nodes":product,
        "bounded_center_difference_hz":bounded_sum,
        "hypothetical_float64_factor_bytes":product*clock_rows*clock_samples_per_row*8,
        "clock_rows":clock_rows,"clock_samples_per_row":clock_samples_per_row,
        "count_is_necessary_lower_bound":False,"runtime_measured":False,
        "templates_generated":0,"templates_adopted":False,"recovery_qualified":False,
        "scope":"sufficient loose construction for conditional emitter-center tracks only"}
