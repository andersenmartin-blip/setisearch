"""LS7F retrospective nuisance-bank and exact margin tradeoffs.

All fits use the unchanged LS7E arithmetic. A threshold sweep describes the
closed records only; it cannot calibrate probabilities or qualify a detector.
"""
import numpy as np


def rectangle_bank(aperture_yx, stamp_shape, shapes):
    """All in-stamp placements intersecting the aperture, in declared order.

    Keep duplicates: a label denotes an actual placement, including those
    indistinguishable after restricting the fit to the optimal aperture.
    """
    coords = np.asarray(aperture_yx, dtype=int)
    height, width = stamp_shape
    if (coords.ndim != 2 or coords.shape[1] != 2 or len(coords) < 4
            or len({tuple(p) for p in coords}) != len(coords)
            or np.any(coords < 0) or np.any(coords >= np.array(stamp_shape))):
        raise ValueError('invalid aperture')
    templates, labels = [], []
    for h, w in shapes:
        if not (1 <= h <= height and 1 <= w <= width):
            raise ValueError('invalid rectangle')
        for y in range(height-h+1):
            for x in range(width-w+1):
                p = ((coords[:, 0] >= y) & (coords[:, 0] < y+h)
                     & (coords[:, 1] >= x) & (coords[:, 1] < x+w)).astype(float)
                if p.sum():
                    templates.append(p)
                    labels.append(f'rect{h}x{w}_{y}_{x}')
    return np.asarray(templates), labels


def exact_thresholds(margins, eligible, reference=9.):
    """Every distinct eligible acceptance set for margin >= threshold.

    Each observed margin includes its ties. The next greater observed margin
    excludes that entire tie. A finite nextafter sentinel rejects everything;
    the unchanged reference threshold is also explicitly evaluated.
    """
    m = np.asarray(margins, dtype=float)[np.asarray(eligible, dtype=bool)]
    if not np.all(np.isfinite(m)):
        raise ValueError('nonfinite margin')
    if not len(m):
        return np.array([float(reference)])
    return np.unique(np.r_[m, reference, np.nextafter(m.max(), np.inf)])


def threshold_counts(margins, eligible, thresholds, masks):
    m = np.asarray(margins, dtype=float)
    e = np.asarray(eligible, dtype=bool)
    cols = []
    for mask in masks:
        selected = np.sort(m[e & np.asarray(mask, dtype=bool)])
        cols.append(len(selected)-np.searchsorted(selected, thresholds, side='left'))
    return np.column_stack(cols)


def core_cells(rows):
    """Original matched signals/controls plus LS7E extended controls.

    Stress, fixed-flux, null and bounded-pointing cases retain full ledgers and
    descriptive cells but do not silently acquire new qualification targets.
    """
    cells = []
    for kind, fraction in [('stellar', .9), ('off_profile', .8),
                           ('single_pixel', .05), ('block_2x2', .05),
                           ('uniform', .05), ('pointing', .05),
                           ('block3x3', .05), ('row1x5', .05), ('column5x1', .05)]:
        suite = 'extended' if kind in ('block3x3', 'row1x5', 'column5x1') else 'ls7c_replay'
        for score in (8.5, 12., 20.):
            ids = [i for i, r in enumerate(rows) if r['suite'] == suite
                   and r['kind'] == kind and r.get('target_score') == score]
            if not ids:
                raise ValueError('missing core cell')
            signal = kind in ('stellar', 'off_profile')
            limit = int(np.ceil(fraction*len(ids))) if signal else int(np.floor(fraction*len(ids)))
            cells.append({'cell_id': f'{suite}/{kind}/{score:g}', 'suite': suite,
                          'kind': kind, 'target_score': score, 'signal': signal,
                          'trials': len(ids), 'limit': limit, 'indices': ids})
    return cells


def group_key(row):
    key = [row['suite'], row['kind'], row.get('target_score')]
    if row['suite'] == 'sparse_stress':
        key += [row['residual_location'], int(np.sign(row['residual_e_per_s']))]
    elif row['suite'] == 'ls7c_replay' and row.get('target_score') is None:
        key += [row.get('amplitude_fraction'), row.get('shape')]
    return tuple(key)
