#!/usr/bin/env python3
"""Independent scalar Rubin audit; no production imports and no network.

Uses Python statistics rather than NumPy for photometry and ERFA taiutc for
UTC date conversion. Raw IDs are exact decimal strings. Invoke only after
the main acquisition and frozen production analysis are complete.
"""
import argparse
import collections
import csv
import datetime
import hashlib
import json
import math
import statistics
from pathlib import Path
import erfa

HERE = Path(__file__).resolve().parent
RUBIN = HERE.parent


def load(path, raw=False):
    return json.loads(Path(path).read_bytes(), **({'parse_int': str} if raw else {}))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def date_index(mjd):
    a, b = erfa.taiutc(2400000.5, mjd)
    return math.floor((a - 2400000.5) + b)


def calculate(raw, stream, cfg):
    idkey = 'r:diaSourceId' if stream == 'sources' else 'r:diaForcedSourceId'
    grouped = {}
    for index, record in enumerate(raw):
        grouped.setdefault(record[idkey], []).append((index, record))
    measurements = []
    repeated = []
    for identity, versions in grouped.items():
        row = versions[0][1]
        conflict = any(other != row for _, other in versions[1:])
        for index, _ in versions[1:]:
            repeated.append({'row_index': index, 'measurement_id': identity,
                             'reason': 'CONFLICTING_ID' if conflict else 'EXACT_DUPLICATE'})
        reasons = []
        notes = []
        for field in ('midpointMjdTai', 'scienceFlux', 'scienceFluxErr'):
            if number(row.get('r:' + field)) is None:
                reasons.append('MISSING_OR_NONFINITE_' + field)
        err = number(row.get('r:scienceFluxErr'))
        if err is not None and err <= 0:
            reasons.append('NONPOSITIVE_ERROR')
        if row.get('r:band') not in ('u', 'g', 'r', 'i', 'z', 'y'):
            reasons.append('INVALID_BAND')
        if conflict:
            reasons.append('CONFLICTING_MEASUREMENT_ID')
        if 'r:timeWithdrawnMjdTai' not in row:
            notes.append('WITHDRAWAL_STATUS_UNKNOWN')
        elif row['r:timeWithdrawnMjdTai'] is not None:
            if number(row['r:timeWithdrawnMjdTai']) is None:
                notes.append('WITHDRAWAL_STATUS_UNKNOWN')
            else:
                reasons.append('WITHDRAWN_RECORD')
        if stream == 'sources':
            for flag in cfg['critical_source_flags']:
                if row.get('r:' + flag) is True:
                    reasons.append('FLAG_' + flag)
                elif row.get('r:' + flag) is not False:
                    reasons.append('UNKNOWN_FLAG_' + flag)
        else:
            notes.append('FORCED_MEASUREMENT_FLAGS_UNAVAILABLE')
        tai = number(row.get('r:midpointMjdTai'))
        exposure = number(row.get('r:exposureTime'))
        measurements.append({
            'measurement_id': identity, 'object_id': row['r:diaObjectId'],
            'stream': stream, 'band': row.get('r:band'),
            'visit': str(row.get('r:visit')), 'detector': str(row.get('r:detector')),
            'time_mjd_tai': tai, 'utc_day': date_index(tai) if tai is not None else None,
            'flux_njy': number(row.get('r:scienceFlux')), 'flux_error_njy': err,
            'exposure_seconds': exposure if exposure is not None and exposure > 0 else None,
            'quality_notes': notes, 'exclusion_reasons': reasons,
            'source_row_index': versions[0][0], 'duplicate_rows': len(versions) - 1,
        })
    visits = collections.defaultdict(list)
    for row in measurements:
        visits[(row['object_id'], row['visit'], row['band'])].append(row)
    for group in visits.values():
        if len(group) != 1:
            for row in group:
                row['exclusion_reasons'].append('AMBIGUOUS_MULTIPLE_MEASUREMENTS_ONE_VISIT')
    measurements.sort(key=lambda r: (int(r['object_id']), str(r['band']),
                                    r['time_mjd_tai'] if r['time_mjd_tai'] is not None else -1,
                                    int(r['measurement_id'])))
    clean_by_band = collections.defaultdict(list)
    for row in measurements:
        if not row['exclusion_reasons']:
            clean_by_band[(row['object_id'], row['band'])].append(row)
    scored = []
    for row in measurements:
        time = row['time_mjd_tai']
        if time is None or time < cfg['window_start_mjd_tai'] or time >= cfg['window_end_mjd_tai_exclusive']:
            continue
        out = dict(row)
        out.update(status='EXCLUDED_QUALITY_OR_NUMERIC' if row['exclusion_reasons'] else 'NO_USABLE_BASELINE',
                   baseline_ids=[], baseline_visits=0, baseline_dates=0, hit=False,
                   score_is_gaussian_significance=False)
        scored.append(out)
        if row['exclusion_reasons']:
            continue
        history = [r for r in clean_by_band[(row['object_id'], row['band'])]
                   if time - cfg['baseline_lookback_days'] <= r['time_mjd_tai'] < time
                   and r['utc_day'] < row['utc_day']]
        # A visit remains one visit if it has more than one detector record.
        nvisit = len({r['visit'] for r in history})
        ndate = len({r['utc_day'] for r in history})
        out.update(baseline_ids=[r['measurement_id'] for r in history],
                   baseline_visits=nvisit, baseline_dates=ndate,
                   baseline_quality_notes=sorted({n for r in history for n in r['quality_notes']}))
        if history:
            first = min(r['time_mjd_tai'] for r in history)
            last = max(r['time_mjd_tai'] for r in history)
            out.update(baseline_first_mjd_tai=first, baseline_last_mjd_tai=last,
                       baseline_gap_days=time-last, baseline_span_days=last-first,
                       long_baseline_gap=time-last > cfg['long_gap_days'])
        if nvisit < cfg['baseline_min_unique_visits'] or ndate < cfg['baseline_min_earlier_utc_dates']:
            out['baseline_failure'] = 'INSUFFICIENT_PRIOR_VISITS_OR_DATES'
            continue
        baseline = statistics.median(r['flux_njy'] for r in history)
        mad = statistics.median(abs(r['flux_njy']-baseline) for r in history)
        scale = max(cfg['mad_scale']*mad, statistics.median(r['flux_error_njy'] for r in history))
        out.update(baseline_flux_njy=baseline, baseline_scale_njy=scale, baseline_mad_njy=mad)
        if baseline <= 0 or scale <= 0 or baseline / scale < cfg['baseline_min_B_over_scale']:
            out['baseline_failure'] = 'NONPOSITIVE_OR_VARIABLE_LOW_PRECISION_BASELINE'
            continue
        ratio = row['flux_njy'] / baseline
        denominator = math.hypot(row['flux_error_njy'], scale)
        deficit = (baseline-row['flux_njy']) / denominator
        out.update(status='NUMERICALLY_EVALUABLE', flux_ratio=ratio,
                   conservative_deficit_score=deficit, conservative_denominator_njy=denominator,
                   depth_mag=-2.5*math.log10(ratio) if ratio > 0 else None,
                   nonpositive_science_estimate=ratio <= 0,
                   hit=ratio <= cfg['flux_ratio_threshold'] and deficit >= cfg['conservative_deficit_score_min'],
                   requires_quality_and_image_review=bool(row['quality_notes'] or out['baseline_quality_notes']))
    return measurements, scored, repeated


class Checks:
    def __init__(self):
        self.count = 0
        self.failures = []
        self.numeric = 0
        self.max_abs = 0.0

    def equal(self, actual, expected, label):
        self.count += 1
        if isinstance(actual, dict) and isinstance(expected, dict):
            if set(actual) != set(expected):
                self.failures.append({'check': label, 'keys_actual_only': sorted(set(actual)-set(expected)),
                                      'keys_expected_only': sorted(set(expected)-set(actual))})
            for key in actual.keys() & expected.keys():
                self.equal(actual[key], expected[key], label + '/' + key)
        elif isinstance(actual, list) and isinstance(expected, list):
            if len(actual) != len(expected):
                self.failures.append({'check': label, 'length_actual': len(actual), 'length_expected': len(expected)})
            for i, (a, e) in enumerate(zip(actual, expected)):
                self.equal(a, e, label + '/' + str(i))
        elif type(actual) is float or type(expected) is float:
            self.numeric += 1
            if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
                delta = abs(actual - expected)
                self.max_abs = max(self.max_abs, delta)
                if not math.isclose(actual, expected, rel_tol=2e-12, abs_tol=2e-10):
                    self.failures.append({'check': label, 'actual': actual, 'expected': expected})
            else:
                self.failures.append({'check': label, 'actual': actual, 'expected': expected})
        elif actual != expected:
            self.failures.append({'check': label, 'actual': actual, 'expected': expected})


