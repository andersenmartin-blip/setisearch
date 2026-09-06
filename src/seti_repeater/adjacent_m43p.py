"""Sparse M43I scores for paired-OFF checks; preserve repeated native channels.

This is a separately named adapter, not an M37 cache or provenance product.
The caller must bind caches to the intended chronological scan inventory.
"""
import math
import numpy as np
from . import search_v0p6 as core
from . import transfer_m43i as transfer
from .transfer_m43g import integer, memory_bound


def gather_score_indices(cache, score_indices, *, template_indices=None, chunk_bins=4096):
    """Return [template, requested score index], preserving order/duplicates."""
    if type(cache) is not transfer.TelescopeCache:
        raise ValueError('M43I telescope cache required')
    selected = np.asarray(score_indices)
    if (selected.ndim != 1 or selected.dtype.kind not in 'iu'
            or any(isinstance(x, (bool, np.bool_)) for x in score_indices)
            or (selected.size and (selected.min() < 0 or selected.max() >= cache.grid.score_bin_count))):
        raise ValueError('integer score-grid indices required')
    integer(chunk_bins, 'sparse chunk')
    templates = np.arange(len(cache.factors)) if template_indices is None else np.asarray(template_indices)
    # Reuse the unchanged source/cache validation and template selection gates.
    # This one-column validation gather is not counted as a sparse query.
    guard = cache.grid.support_guard_bins
    transfer.gather_bank_slice(cache, guard, guard+1, template_indices=templates, chunk_bins=1)
    bound = (memory_bound(cache.source.integration_count, cache.source.geometry.channel_count)
             + len(templates)*selected.size*4 + len(templates)*min(chunk_bins, selected.size)*64)
    if bound > transfer.CONTRACT['memory_cap_bytes']:
        raise core.V0P6CapacityError('sparse gather memory cap exceeded')
    factors = cache.factors[templates]
    out = np.zeros((len(templates), selected.size), dtype='<f4')
    half = cache.width//2
    for row in range(cache.source.integration_count):
        for left in range(0, selected.size, chunk_bins):
            right = min(left+chunk_bins, selected.size)
            hz = cache.grid.support_hz[selected[left:right]+guard]
            index = core.nearest_native_indices(cache.source.geometry, factors[:, row, None]*hz)
            if index.min() < half or index.max() >= cache.source.geometry.channel_count-half:
                raise core.V0P6CoverageError('sparse native range exceeded')
            out[:, left:right] += cache.values[row, index-half]
    out /= np.float32(math.sqrt(cache.source.integration_count))
    if not np.isfinite(out).all():
        raise ValueError('nonfinite sparse score')
    return out


def paired_off_decision(epoch_scores, subset):
    """Apply inherited inclusive 5.5 rule on exact, unmasked paired OFF scores.

    No other width, neighboring carrier, or inactive epoch participates.
    This decision is a component result, not a complete candidate disposition.
    """
    scores = np.asarray(epoch_scores)
    if scores.dtype != np.dtype('<f4') or scores.ndim != 2 or scores.shape[0] != 3 or not np.isfinite(scores).all():
        raise ValueError('three finite float32 OFF epoch score vectors required')
    active = core.canonical_activity_subsets((subset,))[0]
    if active not in core.M37_ACTIVITY_SUBSETS:
        raise ValueError('unfrozen active subset')
    return np.any(scores[list(active)] >= np.float32(5.5), axis=0)
