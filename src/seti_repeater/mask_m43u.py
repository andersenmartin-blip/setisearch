"""Two fixed neighborhood-support alternatives to the M37 isolation mask."""
import hashlib
import numpy as np
from . import search_v0p6 as core

POLICIES = ('legacy', 'neighbor2', 'neighbor9')


def digest(value):
    return hashlib.sha256(core.canonical_json_bytes(value)).hexdigest()


def build_mask(vector_factory, policy):
    if policy not in POLICIES:
        raise ValueError('unknown M43T mask policy')
    if policy == 'legacy':
        return core.build_m37_two_pass_template_mask(vector_factory)
    combined = None
    for width in core.M37_SPECTRAL_WIDTHS:
        values = np.asarray(vector_factory(width))
        if values.dtype != np.dtype('<f4') or values.ndim != 2 or not np.isfinite(values).all():
            raise ValueError('finite float32 epoch vectors required')
        flags = core.isolated_single_epoch_mask(values, 10., 3.)
        # A seed is isolated only if every other epoch is below 3 throughout
        # the same-width clipped policy-radius carrier neighborhood. Never wrap edges.
        support = core.dilate_q_mask(values >= 3., 2 if policy == 'neighbor2' else 9)
        for epoch in range(len(values)):
            other = np.any(support[np.arange(len(values)) != epoch], axis=0)
            flags[epoch] &= ~other
        if combined is None:
            combined = flags
        elif flags.shape != combined.shape:
            raise ValueError('vector factory changed shape between widths')
        else:
            combined |= flags
    return core.dilate_q_mask(combined, 9)


def bind_calibration(calibration, threshold, policy):
    if policy not in POLICIES:
        raise ValueError('unknown M43T mask policy')
    null_sha = core.float64_vector_sha256(calibration.null_maxima)
    if null_sha != threshold.global_null_maxima_sha256:
        raise ValueError('threshold/null binding mismatch')
    record = {'schema': 'm43u-mask-calibration-binding-v1', 'mask_policy': policy,
              'null_maxima_sha256': null_sha,
              'threshold_certificate_sha256': threshold.certificate_sha256}
    return {**record, 'binding_sha256': digest(record)}


def validate_binding(binding, policy, calibration, threshold):
    if binding != bind_calibration(calibration, threshold, policy):
        raise ValueError('mask/calibration binding mismatch')
