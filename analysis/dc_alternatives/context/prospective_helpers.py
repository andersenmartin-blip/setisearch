#!/usr/bin/env python3
"""Metadata-only baseline union and typed selected-score admission helpers.

No NPZ/HDF5 or numerical module is imported. The optional inspection reads
only already saved JSON profiles and normalization terms; it never replays
scores or decodes source power. Actual new contexts need a later frozen driver.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
MATRICES = ('next_dc/crossscan/results/CONTEXT_PROFILES.json',
            'on_cached/context/results/CONTEXT_PROFILES.json')
TERMS = ('row_power_median', 'row_residual_median',
         'row_winsorized_residual_location', 'row_residual_MAD_scale')
SOURCE_KINDS = ('original_clean_cached_carrier_maximum',
                'recovered_original_DC_free_hypothesis')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def object_sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest}


def checked(declaration):
    path = ROOT / declaration['path']
    require(path.resolve().is_relative_to(ROOT), 'Input outside workspace')
    require(pin(path) == declaration, 'Immutable input pin differs: '+declaration['path'])
    return path


def physical_identity(native, q, width, vectors):
    require(width in (1, 3) and native in (170, 171, 172), 'Original scientific family differs')
    require(len(vectors) == 6 and all(len(v) == 16 for v in vectors), 'Six full16 vectors required')
    raw = {'width_channels': width, 'six_scan_rounded_absolute_centers': vectors}
    geometry = {'native_chunk_index': native, 'core_q': q, **raw, 'raw_geometry_id': object_sha(raw)}
    return object_sha(geometry), geometry


def normalization_identity(declaration, native, q):
    norm = read(checked(declaration))
    first = native*1048576 + q*4096
    require(norm['normalization_source_channel_interval_half_open'] == [first, first+4096],
            'Baseline normalization physical core differs')
    require(norm['normalization_unmasked_counts'] == [4096]*16, 'Baseline full16 counts differ')
    identity = {'physical_core': [first, first+4096], 'unmasked_counts': [4096]*16}
    for field in TERMS:
        values = norm[field]
        require(len(values) == 16 and all(math.isfinite(v) for v in values), 'Invalid saved row terms')
        identity[field] = [float(value).hex() for value in values]
    return object_sha(identity)


def baseline_union():
    """Return exact saved physical families, keeping every logical reference."""
    families, logical_count = {}, 0
    for name in MATRICES:
        path = ROOT/name
        matrix, matrix_pin = read(path), pin(path)
        groups = {}
        for outer in matrix.get('profiles', matrix.get('selected_profiles', [])):
            logical_count += 1
            template = outer['template_id']
            track = outer['selected_original_record']
            source = outer.get('source_fixed_profile', outer)
            group = groups.setdefault(template, {'track': track, 'profiles': {}})
            require(group['track'] == track, 'Logical template changes selected tuple')
            require(outer['context_scan_id'] not in group['profiles'], 'Duplicate logical context')
            group['profiles'][outer['context_scan_id']] = (outer, source)
        for template, group in sorted(groups.items()):
            require(set(group['profiles']) == set(SCANS), 'Incomplete baseline six-scan family')
            track = group['track']
            native, q, width = track['native_chunk_index'], track['core_q'], track['width_channels']
            vectors = [group['profiles'][scan][1]['rounded_absolute_centers'] for scan in SCANS]
            pid, geometry = physical_identity(native, q, width, vectors)
            family = families.setdefault(pid, {'physical_geometry': geometry, 'logical_references': [], 'profiles': {}})
            require(family['physical_geometry'] == geometry, 'Physical hash collision')
            family['logical_references'].append({'matrix_pin': matrix_pin, 'template_id': template})
            for scan in SCANS:
                outer, source = group['profiles'][scan]
                require(source['width_channels'] == width, 'Saved width differs')
                for field in ('raw_capsule', 'normalization'):
                    checked(source[field])
                norm_id = normalization_identity(source['normalization'], native, q)
                evidence = {'matrix_pin': matrix_pin, 'template_id': template, 'context_scan_id': scan,
                            'source_profile_object_sha256': object_sha(source),
                            'normalization_term_identity_sha256': norm_id,
                            'raw_capsule': source['raw_capsule'], 'normalization': source['normalization']}
                if scan in family['profiles']:
                    previous = family['profiles'][scan]
                    require(previous['normalization_term_identity_sha256'] == norm_id,
                            'Same normalized geometry has differing frozen row terms')
                    # Exact values already saved; this comparison does not replay scores.
                    prior = previous['_source_profile']
                    for field in ('rounded_absolute_centers', 'width_channels', 'row_standardized_box_sum',
                                  'row_score_contribution', 'fixed_robust_box_track_score'):
                        require(prior[field] == source[field], 'Duplicate physical saved measurement differs: '+field)
                    previous['alias_references'].append(evidence)
                else:
                    family['profiles'][scan] = {**evidence, 'alias_references': [], '_source_profile': source}
    require(logical_count == 108 and len(families) == 16, 'Exposed baseline union count differs')
    for family in families.values():
        for profile in family['profiles'].values():
            del profile['_source_profile']
    return {'schema': 'SETI_DC_ALTERNATIVES_BASELINE_UNION_METADATA_V1',
            'counts': {'logical_profiles': logical_count, 'normalized_physical_template_families': len(families),
                       'normalized_physical_context_profiles': sum(len(f['profiles']) for f in families.values()),
                       'source_power_float_cells_decoded': 0, 'prior_scores_recomputed': 0},
            'families': families}


def typed_own_score_source(track):
    """Prospective adapter; final selector field names must be frozen first."""
    declaration = track['authoritative_score_source']
    require(declaration['kind'] in SOURCE_KINDS, 'Unknown selected-score authority')
    require(all(field in declaration for field in ('pin', 'record_index', 'score_field',
                                                   'drift_field', 'width_field', 'channel_field')),
            'Incomplete typed selected-score locator')
    checked(declaration['pin'])
    if declaration['kind'] == 'recovered_original_DC_free_hypothesis':
        require(declaration['pin'] != track['map_pin'], 'Recovered tuple incorrectly binds original maximum')
    return declaration


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inspect-baselines', action='store_true')
    args = parser.parse_args()
    require(args.inspect_baselines, 'Only metadata baseline inspection is currently implemented')
    result = baseline_union()
    print(json.dumps({'status': 'PASS_METADATA_ONLY_BASELINE_UNION', 'counts': result['counts'],
                      'baseline_union_object_sha256': object_sha(result)}, sort_keys=True))
