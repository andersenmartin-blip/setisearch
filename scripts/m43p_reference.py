"""Independent M43P mask, sparse native-window and scramble references."""
import numpy as np
from seti_repeater import search_v0p6 as core
from m43o_stack_reference import reference_stack


def isolated_reference(vectors):
    safe = np.where(np.isfinite(vectors), vectors, np.float32(-np.inf))
    flags = np.empty(safe.shape, dtype=bool)
    for epoch in range(3):
        others = [i for i in range(3) if i != epoch]
        flags[epoch] = ((safe[epoch] >= core.M37_RFI_STRONG_SNR)
                        & (safe[others[0]] < core.M37_RFI_OTHER_EPOCHS_BELOW_SNR)
                        & (safe[others[1]] < core.M37_RFI_OTHER_EPOCHS_BELOW_SNR))
    return flags


def dilate_reference(flags, guard):
    # Prefix interval counts, independent of the production offset-OR loop.
    n = flags.shape[-1]
    prefix = np.pad(np.cumsum(flags, axis=-1, dtype=np.int64), ((0,0),(1,0)))
    q = np.arange(n)
    return prefix[:, np.minimum(n, q+guard+1)] != prefix[:, np.maximum(0, q-guard)]


def mask_reference(arrays):
    flags = np.zeros_like(next(iter(arrays.values())), dtype=bool)
    for width in core.M37_SPECTRAL_WIDTHS:
        flags |= isolated_reference(arrays[width])
    return dilate_reference(flags, core.M37_RFI_GUARD_Q_BINS)


def masked_stack_reference(vectors, subset, mask):
    result = reference_stack(vectors, subset, 'active3')
    for epoch in subset:
        result[mask[epoch]] = -np.inf
    return result


def sparse_reference(source, factors, grid, width, indices):
    # Absolute native windows; never use the production filter cache.
    out = np.zeros((len(factors), len(indices)), dtype='<f4')
    offsets = np.arange(-(width//2), width//2+1)
    for row in range(source.integration_count):
        centers = np.rint((factors[:,row,None]*grid.score_hz[indices][None,:]
                          - source.geometry.raw_zero_hz)/source.geometry.channel_width_hz).astype(np.int64)
        if centers.min() < width//2 or centers.max() >= source.geometry.channel_count-width//2:
            raise ValueError('reference native window outside coverage')
        windows = source.values[row, centers[:,:,None]+offsets]
        out += (np.sum(windows, axis=-1, dtype=np.float32)/np.sqrt(width)).astype('<f4')
    out /= np.float32(np.sqrt(source.integration_count))
    return out


def scramble_reference(arrays, mask, shifts):
    """All width/subset maxima with explicit modular indexing, no np.roll."""
    n = mask.shape[-1]
    maxima = np.full(len(shifts), -np.inf, dtype='<f8')
    for si, shift in enumerate(shifts):
        index = (np.arange(n)[None,:]-np.asarray(shift)[:,None]) % n
        moved_mask = mask[np.arange(3)[:,None], index]
        for vectors in arrays.values():
            moved = vectors[np.arange(3)[:,None], index]
            for subset in core.M37_ACTIVITY_SUBSETS:
                score = masked_stack_reference(moved, subset, moved_mask)
                maxima[si] = max(maxima[si], float(score.max()))
    return maxima
