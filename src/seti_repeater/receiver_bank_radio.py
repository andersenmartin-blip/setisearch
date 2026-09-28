"""Pinned, receiver-coordinate linear factors; no orbital or telescope admission API."""
from dataclasses import dataclass
from fractions import Fraction as Q
import hashlib
import json
import math

import numpy as np

from .window_identity_radio_v2 import build as bind_windows

SCHEMA = "radio-hd189733-received-linear-bank-v1"
WIDTHS = (1, 3, 5, 9, 17, 33, 65, 129)
RATE_TENTHS = tuple(range(-40, 41))
SCORE_HALF = 40
SUPPORT_GUARD = 9
LABELS = tuple(f"epoch{e}_{k}" for e in (1, 2, 3) for k in ("on", "off"))


def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def rational(x):
    if type(x) not in (int, float) or not math.isfinite(x):
        raise ValueError("Finite numeric metadata required")
    return Q(x)


def ratio_record(q):
    return {"numerator": q.numerator, "denominator": q.denominator,
            "approximate": float(q)}


def clock(source):
    scans = source["scans"]
    if len(scans) != 6 or tuple(s["label"] for s in scans) != LABELS:
        raise ValueError("Exact six-scan order required")
    first = scans[0]["expected_header"]
    origin = rational(first["tstart_mjd"])
    anchor = rational(first["tsamp_s"]) / 2
    rows = []
    for scan in scans:
        h = scan["expected_header"]
        if h["dataset_shape"] != [16, 1, 264503296]:
            raise ValueError("Frozen source row geometry changed")
        dt = rational(h["tsamp_s"])
        if dt <= 0:
            raise ValueError("Positive integration duration required")
        start = (rational(h["tstart_mjd"]) - origin) * 86400 - anchor
        rows.extend(tuple(start + (Q(i) + f) * dt for f in (Q(0), Q(1,2), Q(1)))
                    for i in range(16))
    if (rows[0][1] != 0 or any(a[2] > b[0] for a,b in zip(rows, rows[1:]))
            or any(r[1]*2 != r[0]+r[2] for r in rows)):
        raise ValueError("Overlapping or invalid exact header clock")
    return tuple(rows)


def inputs(source_raw, source_sha, design_raw, design_sha):
    bound = bind_windows(source_raw, source_sha, design_raw, design_sha)
    source = json.loads(source_raw)
    design = json.loads(design_raw)
    rows = clock(source)
    return source, design, bound, rows


@dataclass(frozen=True)
class ReceiverBank:
    provenance_json: bytes
    factors: np.ndarray
    identity: str

    def record(self):
        return {"schema": SCHEMA, "provenance": json.loads(self.provenance_json),
                "factor_sha256": sha(self.factors.tobytes()), "shape": list(self.factors.shape),
                "encoding": "C-order little-endian float64",
                "axes": ["rate-tenths-index", "scan-major integration", "start-midpoint-end"],
                "spectral_access_authorized": False, "scientific_recovery_qualified": False,
                "planetary_or_observer_ephemeris_coverage_claimed": False}

    def validate(self):
        p = json.loads(self.provenance_json)
        if (self.provenance_json != canonical(p) or p["rate_tenths"] != list(RATE_TENTHS)
                or p["widths"] != list(WIDTHS) or p["frame"] != "recorded-topocentric"
                or p["primary"] != "neighbor9" or self.factors.shape != (81,96,3)
                or self.factors.dtype != np.dtype("<f8") or self.factors.flags.writeable
                or not self.factors.flags.c_contiguous
                or not np.isfinite(self.factors).all() or np.any(self.factors <= 0)
                or np.any(self.factors >= 2) or not np.all(self.factors[:,0,1] == 1)
                or self.identity != sha(canonical(self.record()))):
            raise ValueError("Receiver factor binding or immutable payload changed")


def build(source_raw, source_sha, design_raw, design_sha, role):
    source, design, bound, rows = inputs(source_raw, source_sha, design_raw, design_sha)
    matches = [w for w in design["windows"] if w["role"] == role]
    if len(matches) != 1:
        raise ValueError("Exactly one frozen role required")
    w = matches[0]
    center = w["proposed_first_on_midpoint_carrier_center_hz"]
    t = np.array([[float(q) for q in row] for row in rows], dtype="<f8")
    r = np.array(RATE_TENTHS, dtype="<f8") / 10
    values = np.ascontiguousarray(1 + r[:,None,None] * t[None,:,:] / center, dtype="<f8")
    values = np.frombuffer(values.tobytes(), dtype="<f8").reshape(81,96,3)
    clock_pairs = [[[q.numerator, q.denominator] for q in row] for row in rows]
    p = {"source_contract_sha256": source_sha, "window_design_sha256": design_sha,
         "window_binding_sha256": bound["contract_sha256"], "window_identity": w["identity"],
         "role": role, "center_hz": center, "clock_rationals_sha256": sha(canonical(clock_pairs)),
         "rate_tenths": list(RATE_TENTHS), "widths": list(WIDTHS),
         "primary": "neighbor9", "frame": "recorded-topocentric",
         "formula": "F=1+(rate_tenths/10)*t/center; f=q*F; actual slope=q*(rate_tenths/10)/center",
         "observer_ephemeris_used": False, "orbital_factor_type": False,
         "score_half_bins": SCORE_HALF, "support_guard_bins": SUPPORT_GUARD}
    initial = ReceiverBank(canonical(p), values, "")
    bank = ReceiverBank(initial.provenance_json, values, sha(canonical(initial.record())))
    bank.validate()
    return bank


def coverage(source_raw, source_sha, design_raw, design_sha, role):
    """Exact conditional support geometry, not power recovery or physical completeness."""
    source, design, _, rows = inputs(source_raw, source_sha, design_raw, design_sha)
    w = next((w for w in design["windows"] if w["role"] == role), None)
    if w is None:
        raise ValueError("Unknown role")
    center = rational(w["proposed_first_on_midpoint_carrier_center_hz"])
    df = abs(rational(source["scans"][0]["expected_header"]["foff_mhz"])) * 10**6
    extent = max(abs(t) for row in rows for t in row)
    dt = max(row[2]-row[0] for row in rows)
    max_q = center + SCORE_HALF*df
    max_factor = 1 + 4*extent/center
    terms = {
        "rate_quantization": max_q/center * Q(1,20)*extent,
        "carrier_quantization": df/2*max_factor,
        "half_integration_sweep": max_q/center * 4*dt/2,
        "intrinsic_half_width": df/2,
        "predicted_bin_rounding": df/2,
        "occupied_bin_rounding": df/2,
        "reserved_float_arithmetic": Q(1,10000)}
    required = sum(terms.values())
    available = (max(WIDTHS)//2)*df
    # Stronger than a centre-window check: whole support grid + widest filter,
    # native rounding and receiver-veto ±100 Hz neighborhood remain in extraction.
    support_edge = (SCORE_HALF+SUPPORT_GUARD)*df
    max_shift = (center+support_edge)/center*4*extent
    extraction_needed = support_edge+max_shift+available+df+100
    extraction_available = min(center-rational(w["native_frequency_low_hz"]),
                               rational(w["native_frequency_high_hz"])-center)
    return {"role": role, "schema": "radio-received-linear-conditional-containment-v1",
            "extent_seconds": ratio_record(extent), "integration_seconds": ratio_record(dt),
            "terms_hz": {k: ratio_record(v) for k,v in terms.items()},
            "required_half_support_hz": ratio_record(required),
            "available_half_support_hz": ratio_record(available),
            "continuous_linear_family_contained_at_width_129": required <= available,
            "extraction_needed_half_hz": ratio_record(extraction_needed),
            "extraction_available_half_hz": ratio_record(extraction_available),
            "full_support_and_receiver_neighborhood_inside_extraction": extraction_needed <= extraction_available,
            "smaller_width_continuous_coverage_claimed": False,
            "time_coordinate": "exact rational interpretation of retained header numbers",
            "absolute_clock_calibration_qualified": False,
            "spectral_power_recovery_qualified": False, "spectral_access_authorized": False}
