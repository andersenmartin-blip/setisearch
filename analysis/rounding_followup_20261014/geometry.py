"""Exact affine rounding-path geometry; no spectrum or NumPy imports.

Binary64 metadata scalars are rationalized separately before arithmetic. Sweep
critical drift slices and intervening slabs, then each phase cut and gap. Integer
crossings of row bases and pair differences give all critical drift values.
"""
from fractions import Fraction
from itertools import combinations


HALF = Fraction(1, 2)


def exact(value):
    return Fraction.from_float(float(value))


def encode(value):
    return [str(value.numerator), str(value.denominator)]


def decode(value):
    return Fraction(int(value[0]), int(value[1]))


def floor(value):
    return value.numerator // value.denominator


def ceil(value):
    return -((-value.numerator) // value.denominator)


def round_even(value):
    lo = floor(value)
    remainder = value - lo
    if remainder < HALF:
        return lo
    if remainder > HALF:
        return lo + 1
    return lo if lo % 2 == 0 else lo + 1


def integer_events(intercept, slope, half_drift):
    if not slope:
        return []
    low, high = sorted((intercept - slope * half_drift, intercept + slope * half_drift))
    return [(Fraction(integer) - intercept) / slope for integer in range(ceil(low), floor(high) + 1)]


def phase_cuts(row_values):
    cuts = {-HALF, HALF}
    for value in row_values:
        # value + phase crosses k+.5. A closed phase interval of length1
        # contains at most two cuts from a row, both endpoints if value integral.
        for integer in range(ceil(value - 1), floor(value) + 1):
            phase = Fraction(integer) + HALF - value
            if -HALF <= phase <= HALF:
                cuts.add(phase)
    return sorted(cuts)


def stratum_dimension(delta, phase, slopes, values, half_drift):
    normals = []
    if delta in (-half_drift, half_drift):
        normals.append((Fraction(1), Fraction(0)))
    if phase in (-HALF, HALF):
        normals.append((Fraction(0), Fraction(1)))
    tied = []
    for row, (slope, value) in enumerate(zip(slopes, values)):
        coordinate = value + phase
        if coordinate - floor(coordinate) == HALF:
            normals.append((slope, Fraction(1)))
            tied.append(row)
    if not normals:
        return 2, tied
    first = normals[0]
    rank = 1 + int(any(first[0] * normal[1] != first[1] * normal[0] for normal in normals[1:]))
    return 2 - rank, tied


def enumerate_paths(base_channel, drift0, times, df, half_drift, evaluation_cap=None):
    """Return sorted unique four-row integer paths and exact attainable witnesses."""
    h, d0, spacing = exact(half_drift), exact(drift0), exact(df)
    slopes = [exact(t) / spacing for t in times]
    intercepts = [Fraction(base_channel) + d0 * slope for slope in slopes]
    events = {-h, h}
    event_count_bound = 2
    forms = list(zip(intercepts, slopes))
    forms.extend((intercepts[i] - intercepts[j], slopes[i] - slopes[j]) for i, j in combinations(range(4), 2))
    for intercept, slope in forms:
        crosses = integer_events(intercept, slope, h)
        event_count_bound += len(crosses)
        events.update(crosses)
    critical = sorted(events)
    slices = []
    for i, delta in enumerate(critical):
        slices.append((delta, 'critical'))
        if i + 1 < len(critical):
            slices.append(((delta + critical[i + 1]) / 2, 'open_slab'))
    # A phase interval has ≤4 interior cuts plus its two box endpoints.
    certified_evaluation_bound = 11 * (2 * event_count_bound - 1)
    if evaluation_cap is not None and 11 * len(slices) > evaluation_cap:
        raise ValueError('Geometry sampling upper bound exceeds remaining cap')
    paths = {}
    evaluated = 0
    for delta, slice_kind in slices:
        values = [intercept + delta * slope for intercept, slope in zip(intercepts, slopes)]
        cuts = phase_cuts(values)
        for i, phase in enumerate(cuts):
            points = [(phase, 'cut')]
            if i + 1 < len(cuts):
                points.append(((phase + cuts[i + 1]) / 2, 'open_gap'))
            for sample_phase, phase_kind in points:
                evaluated += 1
                if evaluation_cap is not None and evaluated > evaluation_cap:
                    raise ValueError('Actual geometry sampling exceeds remaining cap')
                channels = tuple(round_even(value + sample_phase) for value in values)
                if channels not in paths:
                    dimension, ties = stratum_dimension(delta, sample_phase, slopes, values, h)
                    paths[channels] = {'channels': list(channels), 'delta_drift_fraction': encode(delta),
                                       'phase_fraction': encode(sample_phase), 'sampling_slice': slice_kind,
                                       'sampling_phase': phase_kind, 'witness_stratum_dimension': dimension,
                                       'tie_row_indices_in_window': ties}
    ordered = [paths[path] for path in sorted(paths)]
    return {'paths': ordered, 'unique_paths': len(ordered), 'critical_drift_count': len(critical),
            'slices_sampled': len(slices), 'witness_pairs_evaluated': evaluated,
            'conservative_witness_pair_bound': certified_evaluation_bound,
            'actual_critical_slices_pair_bound': 11 * len(slices),
            'geometry': 'exact_separately_rationalized_binary64_affine_rounding_ties_to_even'}


def witness_centers(base_channel, drift0, times, df, delta_fraction, phase_fraction, offset=0):
    delta, phase = decode(delta_fraction), decode(phase_fraction)
    d0, spacing = exact(drift0), exact(df)
    return [round_even(Fraction(base_channel + offset) + (d0 + delta) * exact(t) / spacing + phase) for t in times]
