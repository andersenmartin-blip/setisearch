"""Frozen same-band Rubin direct-science-flux screening; no network.

The conservative deficit score is not a calibrated Gaussian significance.
Source-centroid and object-centroid forced streams must be run separately.
"""
from pathlib import Path
import collections
import copy
import datetime
import hashlib
import json
import math
import numpy as np
from astropy.time import Time
from astropy.utils import iers
iers.conf.auto_download = False

CRITICAL_SOURCE_FLAGS = [
    'centroid_flag', 'forced_PsfFlux_flag', 'forced_PsfFlux_flag_edge',
    'forced_PsfFlux_flag_noGoodPixels', 'pixelFlags', 'pixelFlags_bad',
    'pixelFlags_crCenter', 'pixelFlags_edge', 'pixelFlags_nodata',
    'pixelFlags_nodataCenter', 'pixelFlags_offimage',
    'pixelFlags_interpolatedCenter', 'pixelFlags_saturatedCenter',
    'pixelFlags_streakCenter', 'pixelFlags_suspectCenter',
    'pixelFlags_injected', 'pixelFlags_injectedCenter',
    'pixelFlags_injected_template', 'pixelFlags_injected_templateCenter',
    'glint_trail', 'isDipole',
]


def finite(value):
    try:
        return not isinstance(value, bool) and math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    # Python arbitrary-precision integer parsing protects 64-bit identifiers.
    return json.loads(Path(path).read_text(), parse_int=str)


def utc_day(tai_mjd):
    return int(math.floor(float(Time(float(tai_mjd), format='mjd', scale='tai').utc.mjd)))


def merge_supplement(rows, supplements):
    """Join supplementary quality metadata only on exact source identifiers."""
    by_id = {}
    for row in supplements:
        id_ = str(row['r:diaSourceId'])
        if id_ in by_id:
            raise ValueError('Repeated supplemental source ID ' + id_)
        by_id[id_] = row
    out = []
    for row in rows:
        row = copy.deepcopy(row)
        extra = by_id.get(str(row['r:diaSourceId']), {})
        for key, value in extra.items():
            if key in row and row[key] != value:
                raise ValueError('Supplement disagrees: ' + str(row['r:diaSourceId']) + ' ' + key)
            row[key] = value
        out.append(row)
    return out


def normalize(rows, stream, config):
    if stream not in ('sources', 'forced'):
        raise ValueError('One separate stream required')
    idkey = 'r:diaSourceId' if stream == 'sources' else 'r:diaForcedSourceId'
    groups = collections.defaultdict(list)
    for index, row in enumerate(rows):
        groups[str(row[idkey])].append((index, row))
    normalized, duplicate_log = [], []
    for id_, group in groups.items():
        # Exact repetition only: never select a conflicting version by its flux.
        variants = {json.dumps(r, sort_keys=True, allow_nan=False) for _, r in group}
        conflict = len(variants) > 1
        row = group[0][1]
        for index, _ in group[1:]:
            duplicate_log.append({'row_index':index, 'measurement_id':id_,
                                  'reason':'CONFLICTING_ID' if conflict else 'EXACT_DUPLICATE'})
        reasons, quality_notes = [], []
        for key in ('r:midpointMjdTai', 'r:scienceFlux', 'r:scienceFluxErr'):
            if not finite(row.get(key)):
                reasons.append('MISSING_OR_NONFINITE_' + key[2:])
        if finite(row.get('r:scienceFluxErr')) and float(row['r:scienceFluxErr']) <= 0:
            reasons.append('NONPOSITIVE_ERROR')
        if row.get('r:band') not in list('ugrizy'):
            reasons.append('INVALID_BAND')
        if conflict:
            reasons.append('CONFLICTING_MEASUREMENT_ID')
        if 'r:timeWithdrawnMjdTai' not in row:
            quality_notes.append('WITHDRAWAL_STATUS_UNKNOWN')
        elif row['r:timeWithdrawnMjdTai'] is not None:
            if finite(row['r:timeWithdrawnMjdTai']):
                reasons.append('WITHDRAWN_RECORD')
            else:
                quality_notes.append('WITHDRAWAL_STATUS_UNKNOWN')
        if stream == 'sources':
            for flag in config['critical_source_flags']:
                value = row.get('r:' + flag)
                if value is True:
                    reasons.append('FLAG_' + flag)
                elif value is not False:
                    reasons.append('UNKNOWN_FLAG_' + flag)
        else:
            quality_notes.append('FORCED_MEASUREMENT_FLAGS_UNAVAILABLE')
        t = float(row['r:midpointMjdTai']) if finite(row.get('r:midpointMjdTai')) else None
        rec = {'measurement_id':id_, 'object_id':str(row['r:diaObjectId']),
               'stream':stream, 'band':row.get('r:band'),
               'visit':str(row.get('r:visit')), 'detector':str(row.get('r:detector')),
               'time_mjd_tai':t, 'utc_day':utc_day(t) if t is not None else None,
               'flux_njy':float(row['r:scienceFlux']) if finite(row.get('r:scienceFlux')) else None,
               'flux_error_njy':float(row['r:scienceFluxErr']) if finite(row.get('r:scienceFluxErr')) else None,
               'exposure_seconds':float(row['r:exposureTime']) if finite(row.get('r:exposureTime')) and float(row['r:exposureTime'])>0 else None,
               'quality_notes':quality_notes, 'exclusion_reasons':reasons,
               'source_row_index':group[0][0], 'duplicate_rows':len(group)-1}
        normalized.append(rec)
    physical = collections.defaultdict(list)
    for rec in normalized:
        physical[(rec['object_id'],rec['visit'],rec['detector'],rec['band'])].append(rec)
    for group in physical.values():
        if len(group)>1:
            for rec in group:
                rec['exclusion_reasons'].append('AMBIGUOUS_MULTIPLE_MEASUREMENTS_ONE_VISIT')
    normalized.sort(key=lambda r:(int(r['object_id']),str(r['band']),r['time_mjd_tai'] or -1,int(r['measurement_id'])))
    return normalized, duplicate_log


def score(normalized, config):
    out = []
    for row in normalized:
        t = row['time_mjd_tai']
        if t is None or not config['window_start_mjd_tai'] <= t < config['window_end_mjd_tai_exclusive']:
            continue
        rec = copy.deepcopy(row)
        rec.update(status='EXCLUDED_QUALITY_OR_NUMERIC' if row['exclusion_reasons'] else 'NO_USABLE_BASELINE',
                   baseline_ids=[], baseline_visits=0, baseline_dates=0, hit=False,
                   score_is_gaussian_significance=False)
        if row['exclusion_reasons']:
            out.append(rec)
            continue
        context = [r for r in normalized if not r['exclusion_reasons']
                   and r['object_id']==row['object_id'] and r['band']==row['band']
                   and t-config['baseline_lookback_days']<=r['time_mjd_tai']<t
                   and r['utc_day']<row['utc_day']]
        visits = {(r['visit'],r['detector'])for r in context}
        dates = {r['utc_day']for r in context}
        rec['baseline_ids']=[r['measurement_id']for r in context]
        rec['baseline_visits']=len(visits)
        rec['baseline_dates']=len(dates)
        rec['baseline_quality_notes']=sorted({note for r in context for note in r['quality_notes']})
        if context:
            rec['baseline_first_mjd_tai']=min(r['time_mjd_tai']for r in context)
            rec['baseline_last_mjd_tai']=max(r['time_mjd_tai']for r in context)
            rec['baseline_gap_days']=t-rec['baseline_last_mjd_tai']
            rec['baseline_span_days']=rec['baseline_last_mjd_tai']-rec['baseline_first_mjd_tai']
            rec['long_baseline_gap']=rec['baseline_gap_days']>config['long_gap_days']
        if len(visits)<config['baseline_min_unique_visits'] or len(dates)<config['baseline_min_earlier_utc_dates']:
            rec['baseline_failure']='INSUFFICIENT_PRIOR_VISITS_OR_DATES'
            out.append(rec)
            continue
        f=np.array([r['flux_njy']for r in context]);errors=np.array([r['flux_error_njy']for r in context])
        baseline=float(np.median(f));mad=float(np.median(np.abs(f-baseline)))
        scale=max(config['mad_scale']*mad,float(np.median(errors)))
        rec.update(baseline_flux_njy=baseline,baseline_scale_njy=scale,baseline_mad_njy=mad)
        if not math.isfinite(baseline) or baseline<=0 or not math.isfinite(scale) or scale<=0 or baseline/scale<config['baseline_min_B_over_scale']:
            rec['baseline_failure']='NONPOSITIVE_OR_VARIABLE_LOW_PRECISION_BASELINE'
            out.append(rec)
            continue
        ratio=row['flux_njy']/baseline
        error=math.sqrt(row['flux_error_njy']**2+scale**2)
        deficit=(baseline-row['flux_njy'])/error
        rec.update(status='NUMERICALLY_EVALUABLE',flux_ratio=ratio,
                   conservative_deficit_score=deficit,conservative_denominator_njy=error,
                   depth_mag=-2.5*math.log10(ratio)if ratio>0 else None,
                   nonpositive_science_estimate=ratio<=0,
                   hit=bool(ratio<=config['flux_ratio_threshold'] and deficit>=config['conservative_deficit_score_min']),
                   requires_quality_and_image_review=bool(row['quality_notes']or rec['baseline_quality_notes']))
        out.append(rec)
    return out


def summarize(normalized, scored, duplicates):
    evaluated=[r for r in scored if r['status']=='NUMERICALLY_EVALUABLE']
    return {'input_unique_measurements':len(normalized),'input_objects':len({r['object_id']for r in normalized}),
            'admitted_measurements':sum(not r['exclusion_reasons']for r in normalized),
            'explicit_or_unknown_quality_exclusions':dict(collections.Counter(reason for r in normalized for reason in r['exclusion_reasons'])),
            'quality_note_counts':dict(collections.Counter(note for r in normalized for note in r['quality_notes'])),
            'duplicate_rows':len(duplicates),'primary_window_measurements':len(scored),
            'primary_window_objects':len({r['object_id']for r in scored}),
            'status_counts':dict(collections.Counter(r['status']for r in scored)),
            'numerically_evaluable_objects':len({r['object_id']for r in evaluated}),
            'numerically_evaluable_visits':len(evaluated),'hits':sum(r['hit']for r in scored),
            'long_gap_evaluable_visits':sum(r.get('long_baseline_gap',False)for r in evaluated),
            'fully_quality_vetted_evaluable_objects':len({r['object_id']for r in evaluated if not r['requires_quality_and_image_review']}),
            'local_quiescence_established':False,'global_false_alarm_rate_calibrated':False}
