"""Exact-rational upper bounds on conditional track Taylor remainders.

No orbit, polynomial template, grid, spectrum or control is generated. Formal
power series here are derivative *majorants*, uniform over the declared orbit
domain. They do not qualify real-source support, clocks or the physical model.
"""
from __future__ import annotations

from fractions import Fraction as F
from math import isqrt

from .phase_domain_radio import audit_contract, contract_identity


def rational(value):
    if isinstance(value,bool):raise ValueError("boolean is not a rational parameter")
    return F(str(value))


def sqrt_enclosure(x,digits=40):
    x=F(x)
    if x<0 or type(digits) is not int or not 1<=digits<=80:
        raise ValueError("nonnegative radicand and bounded precision required")
    scale=10**digits
    lower=isqrt(x.numerator*scale*scale//x.denominator)
    exact=lower*lower*x.denominator==x.numerator*scale*scale
    return F(lower,scale),F(lower if exact else lower+1,scale)


def atan_reciprocal_enclosure(q,terms):
    if type(q) is not int or q<=1 or type(terms) is not int or not 1<=terms<=100:
        raise ValueError("bounded positive alternating-series inputs required")
    total=sum((F((-1)**k,(2*k+1)*q**(2*k+1)) for k in range(terms)),F(0))
    next_term=F(1,(2*terms+1)*q**(2*terms+1))
    return (total,total+next_term) if terms%2==0 else (total-next_term,total)


def ceil_fraction(x,digits):
    scale=10**digits
    return F(-(-x.numerator*scale//x.denominator),scale)


def pi_upper(fifth_terms=48,other_terms=16,digits=40):
    a0,a1=atan_reciprocal_enclosure(5,fifth_terms)
    b0,b1=atan_reciprocal_enclosure(239,other_terms)
    lower,upper=16*a0-4*b1,16*a1-4*b0
    return lower,upper,ceil_fraction(upper,digits)


def multiply(a,b,order):
    return [sum((a[j]*b[k-j] for j in range(k+1)
                 if j<len(a) and k-j<len(b)),F(0)) for k in range(order+1)]


def compose(a,b,order):
    if b[0]!=0:raise ValueError("composition requires zero inner constant")
    result=[F(0)]*(order+1);power=[F(1)]+[F(0)]*order
    for k,coefficient in enumerate(a[:order+1]):
        if k:power=multiply(power,b,order)
        for j in range(order+1):result[j]+=coefficient*power[j]
    return result


def binomial_absolute_series(delta,exponent,order):
    """Sum |binom(exponent,k)| delta^k; nonnegative majorant coefficients."""
    if delta[0]!=0 or any(x<0 for x in delta):raise ValueError("nonnegative zero-constant series required")
    coefficients=[F(1)];value=F(1)
    for k in range(1,order+1):
        value=value*(exponent-(k-1))/k;coefficients.append(abs(value))
    return compose(coefficients,delta,order)


def inverse_positive_majorant(linear_lower,nonlinear,order):
    """Coefficientwise solution H=s/linear_lower+nonlinear(H)/linear_lower."""
    linear_lower=F(linear_lower)
    if linear_lower<=0 or nonlinear[0]!=0 or nonlinear[1]!=0 or any(x<0 for x in nonlinear):
        raise ValueError("positive linear lower bound and nonnegative quadratic tail required")
    h=[F(0)]*(order+1);h[1]=1/linear_lower
    for k in range(2,order+1):h[k]=compose(nonlinear,h,k)[k]/linear_lower
    return h


def normalized_position_majorant(n,e,order):
    """Bounds R_j >= ||r^(j)||/(a*j!), from u''=-n²u/||u||³.

    Exact low-order norm bounds seed the recursion. Later coefficients follow
    positive majorants for ||u||^-3 with ||u||>=1-e. No a_p division is needed.
    """
    n,e=F(n),F(e)
    if n<=0 or not 0<=e<1 or type(order) is not int or not 3<=order<=10:
        raise ValueError("bounded elliptic derivative order required")
    d=1-e;v=sqrt_enclosure((1+e)/d)[1]
    r=[F(0)]*(order+1)
    r[0]=1+e;r[1]=n*v;r[2]=n*n/(2*d*d);r[3]=n**3*v/(3*d**3)
    for j in range(4,order+1):
        k=j-2;q=multiply(r,r,k);q[0]=0
        delta=[x/(d*d) for x in q]
        g=[x/d**3 for x in binomial_absolute_series(delta,F(-3,2),k)]
        r[j]=n*n*multiply(r,g,k)[k]/(j*(j-1))
    return r


def frequency_majorant(position,norm_speed_beta,axis_max_m,reference_hz,order,digits=40):
    """Compose source Doppler majorant with inverse arrival-time majorant."""
    B,a,f=F(norm_speed_beta),F(axis_max_m),F(reference_hz)
    c=F(299792458)
    if not 0<=B<1 or a<0 or f<=0 or len(position)<order+2:
        raise ValueError("subluminal bound and sufficient derivative orders required")
    velocity=[(j+1)*position[j+1]*a/c for j in range(order+1)]
    if velocity[0]>B:raise ValueError("speed majorant exceeds declared beta bound")
    velocity[0]=B
    delta_beta=velocity.copy();delta_beta[0]=0
    reciprocal=[x/(1-B) for x in binomial_absolute_series([x/(1-B) for x in delta_beta],F(-1),order)]
    delta_x=multiply(velocity,velocity,order);delta_x[0]=0
    proper_clock=binomial_absolute_series([x/(1-B*B) for x in delta_x],F(1,2),order)
    source=multiply(proper_clock,reciprocal,order)
    nonlinear=[F(0),F(0)]+[position[j]*a/c for j in range(2,order+1)]
    inverse=inverse_positive_majorant(1-B,nonlinear,order)
    gamma_lower=sqrt_enclosure(1-B*B,digits)[0]
    if gamma_lower==0:raise ValueError("insufficient lower-root precision")
    normalization=(1+B)/gamma_lower
    received=[f*normalization*x for x in compose(source,inverse,order)]
    return {"frequency_coefficients_hz_per_second_power":received,
        "inverse_time_coefficients":inverse,"source_doppler_coefficients":source,
        "normalization_upper":normalization}


def encode_fraction(x):
    return {"numerator":str(x.numerator),"denominator":str(x.denominator)}


def decimal_upper_text(x,places=15):
    q=ceil_fraction(x,places);scaled=q.numerator*10**places//q.denominator
    whole,fraction=divmod(scaled,10**places)
    return str(whole)+"."+str(fraction).zfill(places)


def temporal_remainder_certificate(contract,study):
    audit_contract(contract)
    if contract_identity(contract)!=study["domain_sha256"]:raise ValueError("domain identity differs")
    if study["orders"]!=[1,2,3,4,5,6]:raise ValueError("only frozen six-degree study supported")
    precision=study["outward_decimal_digits"]
    if precision!=40:raise ValueError("frozen outward precision required")
    T,f,eps=map(rational,(study["reception_extent_seconds"],study["reference_hz"],study["reporting_tolerance_hz"]))
    if T<0 or f<=0 or eps<=0:raise ValueError("invalid reporting scope")
    pt=study["pi_atan_terms"]
    pl,pu,pout=pi_upper(pt["fifth"],pt["two_hundred_thirty_ninth"],precision)
    d=contract["domain"];P=rational(d["period_days"][0])*86400
    a=rational(d["relative_axis_au"][1])*149597870700;e=rational(d["eccentricity"][1])
    n=2*pout/P;position=normalized_position_majorant(n,e,8)
    B=position[1]*a/299792458
    freq=frequency_majorant(position,B,a,f,7,precision)
    rows=[]
    for degree in study["orders"]:
        coefficient=freq["frequency_coefficients_hz_per_second_power"][degree+1]
        remainder=coefficient*T**(degree+1)
        rows.append({"degree":degree,"derivative_coefficient_upper":encode_fraction(coefficient),
            "remainder_hz_exact_upper":encode_fraction(remainder),
            "remainder_hz_outward_decimal":decimal_upper_text(remainder),
            "within_reporting_tolerance":remainder<=eps})
    return {"schema":"radio-conditional-temporal-remainder-certificate-v1",
        "domain_sha256":study["domain_sha256"],"reception_extent_seconds":str(T),"reference_hz":str(f),
        "arithmetic":"exact rational nonnegative majorants; outward pi and square-root enclosures",
        "conditional_mathematical_arithmetic_certified":True,"pi_series_lower":encode_fraction(pl),
        "pi_series_upper":encode_fraction(pu),"pi_outward_upper":encode_fraction(pout),
        "position_derivative_coefficients":[encode_fraction(v) for v in position],
        "beta_upper":encode_fraction(B),
        "frequency_derivative_coefficients":[encode_fraction(v) for v in freq["frequency_coefficients_hz_per_second_power"]],
        "inverse_time_coefficients":[encode_fraction(v) for v in freq["inverse_time_coefficients"]],
        "normalization_upper":encode_fraction(freq["normalization_upper"]),"degrees":rows,
        "uniform_at_every_source_phase":True,"scope":study["scope"],
        "templates_generated":0,"polynomial_tracks_generated":0,"bank_adopted":False,
        "coefficient_grid_qualified":False,"runtime_for_search_measured":False,"recovery_qualified":False,
        "total_physical_error_hz":None,"physical_model_qualified":False,"spectral_access_authorized":False}
