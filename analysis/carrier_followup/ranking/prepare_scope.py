#!/usr/bin/env python3
"""Prepare streaming-selector scope by reading metadata/NPY headers only."""
import gzip
import hashlib
import json
from pathlib import Path
import zipfile
from numpy.lib import format

BASE = Path(__file__).resolve().parent
WORKSPACE = BASE.parent.parent
EXPECTED = {
    'frequency_hz_at_tref.npy': ((4096,), '<f8'),
    'maximum_robust_box_track_score.npy': ((4096,), '<f8'),
    'winning_drift_hz_s.npy': ((4096,), '<f8'),
    'winning_width_channels.npy': ((4096,), '<i2'),
    'valid_hypothesis_count.npy': ((4096,), '<i8'),
    'source_reference_channels.npy': ((4096,), '<i8'),
    'drift_grid_hz_s.npy': ((785,), '<f8'),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path.relative_to(WORKSPACE)), 'bytes': len(raw), 'sha256': sha(raw)}


source_path = WORKSPACE / 'next_dc/ranking/scope.json'
source = json.loads(source_path.read_text())
groups, seen_domains = [], set()
for group in source['groups']:
    maps = []
    for original in group['core_sources']:
        native, q = original['native_chunk_index'], original['core_q']
        identity = (group['primary_target'], native, q)
        assert identity not in seen_domains, 'Duplicate domain would invalidate streaming-prefix bound'
        seen_domains.add(identity)
        old_pin = original['original_map']
        path = WORKSPACE / 'seti_previous' / old_pin['path']
        assert path.is_file() and path.stat().st_size == old_pin['bytes']
        with zipfile.ZipFile(path) as archive:
            assert set(archive.namelist()) == set(EXPECTED)
            for name, (expected_shape, expected_dtype) in EXPECTED.items():
                with archive.open(name) as stream:
                    version = format.read_magic(stream)
                    reader = {(1, 0): format.read_array_header_1_0,
                              (2, 0): format.read_array_header_2_0}[version]
                    shape, fortran, dtype = reader(stream)
                assert shape == expected_shape and dtype.str == expected_dtype and not fortran
        maps.append({'map_id': original['map_id'], 'native_chunk_index': native, 'core_q': q,
                     'reference_channel_interval_half_open': [native * 1048576 + q * 4096,
                                                               native * 1048576 + (q + 1) * 4096],
                     'pin': {'path': str(path.relative_to(WORKSPACE)), 'bytes': old_pin['bytes'],
                             'sha256': old_pin['sha256']},
                     'original_coremax_query_id': original['query_id']})
    groups.append({'phase': group['phase'], 'primary_target': group['primary_target'],
                   'primary_id': group['primary_id'], 'scan_id': group['scan_id'],
                   'map_count': len(maps), 'maps': maps})
assert len(seen_domains) == 2289
scope = {
    'schema': 'SETI_CACHED_CARRIER_DC_UNTOUCHED_STREAMING_SELECTION_SCOPE_V1',
    'date_utc': '2026-10-12',
    'goal': 'Evaluate frozen DC contact geometry for all 9,375,744 cached per-carrier winning paths, then expose exact descriptive global rankings without another detector search.',
    'groups': groups,
    'source_metadata_scope_pin': pin(source_path),
    'previous_coremax_annotation_pin': pin(WORKSPACE / 'next_dc/ranking/ALL2289_GEOMETRY.json'),
    'previous_selected9_pin': pin(WORKSPACE / 'next_dc/ranking/SELECTED_TOP9.json'),
    'producer_pin': pin(BASE / 'select_streaming.py'),
    'constants': {'fch1_hz': 2802832031.25, 'df_hz': -2.7939677238464355,
                  'tsamp_s': 18.253611008, 'rows': 16, 'core_channels': 4096,
                  'fine_channels_per_native': 1048576, 'DC_channels': [178782208, 179830784, 180879360]},
    'NPZ_member_headers': {name: {'shape': list(shape), 'dtype': dtype, 'fortran_order': False}
                           for name, (shape, dtype) in EXPECTED.items()},
    'metadata_preparation': {'NPZ_headers_checked': 2289, 'numerical_NPZ_payloads_decoded': 0,
                             'score_arrays_read': 0, 'new_selection_metrics': 0,
                             'source_map_whole_byte_hashes_deferred_to_execution': True},
    'targets': ['HIP97319', 'HIP97461', 'HIP97663'],
    'expected_counts': {'maps': 2289, 'maps_per_target': 763, 'cached_carriers_per_map': 4096,
                        'cached_carriers': 9375744, 'cached_carriers_per_target': 3125248,
                        'winner_row_occurrences': 150011904,
                        'DC_row_box_membership_checks': 450035712,
                        'maximum_raw_TOP700_records': 2100,
                        'maximum_final_selected_records': 9},
    'center_rule': 'np.rint((frequency_hz_at_tref-fch1_hz)/df_hz + winning_drift_hz_s*(np.arange(16)*tsamp_s)/df_hz).astype(int64); own first integration midpoint has dt=0.',
    'DC_rule': 'Eligible iff none of sixteen inclusive center +/- winning_width_channels//2 boxes includes any frozen DC channel. Widths1 and3 retain their cached winner values.',
    'rank_rule': 'Per target: original score descending, frequency ascending, drift ascending, width ascending, native ascending, q ascending, carrier index ascending. Exact numerical ties, no epsilon.',
    'streaming_rule': 'Process one map at a time; evaluate all4096 cached winner geometries and counts; retain a minheap containing exact best700 eligible carriers per target. No scientific score threshold or adaptive rule.',
    'separation_rule': 'Traverse raw TOP700 once in exact rank order; retain up to100 entries with reference-source-channel distance>3 from every earlier retained entry. Final TOP3 is first3 of this separated list.',
    'prefix_completeness_proof': 'Domains are disjoint and each source channel occurs once per target. Every prior chosen reference channel blocks at most7 distinct carriers including itself. Before the100th separated choice, at most99*7=693 carriers can be blocked; if at least694 eligible carriers exist, the100th choice occurs by raw rank694. Retaining TOP700 therefore suffices. With fewer carriers, retain all available and preserve EMPTY/partial outputs.',
    'preserved_lists': ['raw ranked TOP700', 'raw ranked TOP100 (first100 of TOP700)',
                        'frequency-separated TOP100', 'final TOP3 (first3 of separated list)',
                        'per-core counts and eligible maximum', 'overlap with previous nine coremax selections'],
    'coremax_verification': 'For every original map reproduce its historical maximum using score descending then source channel ascending; match original stored coremax channel/frequency/drift/width/score exactly. This checks cached values, not raw detector scoring.',
    'overlap_identity': 'Compare phase,target,native,q,carrier,reference channel,frequency,reference MJD,drift,width and original score; preserve shared-frequency selections across different primary scans separately.',
    'execution': {'one_job_per_target': True, 'max_parallel_jobs': 2,
                  'CPU_seconds_per_job': 600, 'wall_seconds_per_job': 900,
                  'RAM_bytes_per_job': 2147483648, 'output_bytes_per_job': 4194304,
                  'new_detector_grid_scores': 0, 'new_telescope_HTTP': 0, 'DKK': 0,
                  'rerun_or_overwrite': False},
    'interpretation_limits': [
        'This is a prospective exploratory DC-aware selection of exposed cached per-carrier winners. The previous DC and coremax result scopes remain unchanged.',
        'Excluded carriers retain only their contaminated winning hypothesis; nonwinning drift/width hypotheses are not recovered. This is not a newly masked detector search.',
        'Original scores are empirical robust box-track values, not calibrated SNR, sigma or false-alarm probability.',
        'Removing frozen DC contact does not rule out other receiver structure, interference or chance maxima. No detection threshold or source-classification rule is established.',
        'Raw and frequency-separated TOP100 are different descriptive lists. Reference-channel separation is a geometry rule, not independent physical-source identity.',
        'No new telescope observation, frequency coverage, raw power scoring, flux sensitivity, EIRP limit or independent visit is produced.',
        'Original A/B FAIL_CLOSED and protected2016/closed2019 boundaries remain unchanged; only existing2017 products are opened.',
    ],
}
path = BASE / 'scope.json'
assert not path.exists(), 'Preserve the frozen original scope'
raw = (json.dumps(scope, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
path.write_bytes(raw)
compressed = gzip.compress(raw, compresslevel=9, mtime=0)
(BASE / 'scope.json.gz').write_bytes(compressed)
assert gzip.decompress(compressed) == raw
print(json.dumps({'status': 'PREPARED_HEADERS_ONLY_NO_SCORE_PAYLOADS', 'scope_sha256': sha(raw),
                  'compressed_scope_sha256': sha(compressed), 'producer_sha256': scope['producer_pin']['sha256'],
                  'scope_bytes': len(raw), 'compressed_bytes': len(compressed), 'maps_headers_checked': 2289}))
