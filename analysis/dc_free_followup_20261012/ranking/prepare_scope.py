#!/usr/bin/env python3
"""Prepare metadata pins; never sort or print existing scientific scores."""
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
WORKSPACE = BASE.parent.parent
PHASES = [
    ('central171', 'seti_previous/analysis/s2017_control_targets_20261011_v2', [171], 251,
     'seti_previous/analysis/s2017_control_targets_20261011_v2/delivery/CORE_MAX753.csv'),
    ('adjacent512', 'seti_previous/analysis/off_adjacent_20261011', [170, 171, 172], 512,
     'seti_previous/analysis/off_adjacent_20261011_context/delivery/CORE_MAX1536.csv'),
]
TARGETS = [('HIP97319', 'epoch1_off'), ('HIP97461', 'epoch2_off'), ('HIP97663', 'epoch3_off')]


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path.relative_to(WORKSPACE)), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}


groups = []
for phase, directory, natives, expected, csv_path in PHASES:
    for target, scan in TARGETS:
        primary_id = 'primary20170428_' + target
        directory_path = WORKSPACE / directory / 'results' / primary_id
        audit_path, maps_path = directory_path / 'SCORE_AUDITS.json', directory_path / 'MAPS.json'
        audits, maps = json.loads(audit_path.read_text()), json.loads(maps_path.read_text())
        core_records = [r for r in audits['records'] if r['query_kind'] == 'core_max']
        assert len(core_records) == expected and len(maps['records']) == expected
        map_by_id = {r['map_id']: r for r in maps['records']}
        assert len(map_by_id) == expected
        metadata = []
        for entry in core_records:
            selected = entry['selected_tuple']
            # Deliberately omit all score/frequency/drift/carrier values here.
            native = selected.get('native_chunk_index', 171)
            q, map_id = selected['core_q'], selected['map_id']
            assert native in natives and selected['scan_id'] == scan
            assert selected['primary_target'] == target and selected['original_acquisition_role'] == 'OFF'
            matched_map = map_by_id[map_id]
            assert matched_map['core_q'] == q
            capsule = entry['capsule']
            local_capsule = WORKSPACE / 'seti_previous' / capsule['path']
            assert local_capsule.is_file() and local_capsule.stat().st_size == capsule['bytes']
            metadata.append({'query_id': entry['query_id'], 'map_id': map_id,
                             'native_chunk_index': native, 'core_q': q,
                             'capsule': capsule, 'normalization': entry['normalization'],
                             'original_map': {k: matched_map[k] for k in ('path', 'bytes', 'sha256')},
                             'local_capsule_path': str(local_capsule.relative_to(WORKSPACE))})
        groups.append({'phase': phase, 'primary_target': target, 'scan_id': scan,
                       'primary_id': primary_id, 'natives': natives,
                       'expected_coremax_records': expected,
                       'audit_index': pin(audit_path), 'map_index': pin(maps_path),
                       'source_scope': pin(WORKSPACE / directory / 'scope.json'),
                       'core_sources': metadata})
scope = {
    'schema': 'SETI_PROSPECTIVE_DC_FREE_EXISTING_COREMAX_SELECTION_SCOPE_V1',
    'created_utc_date': '2026-10-12',
    'goal': 'Expose strongest cached per-core winners whose full sixteen-row selected boxes do not contact any of three frozen DC channels, then preserve their original raw503 capsules for subsequent followup.',
    'groups': groups,
    'constants': {'fch1_hz': 2802832031.25, 'df_hz': -2.7939677238464355,
                  'tsamp_s': 18.253611008, 'rows': 16, 'fine_channels_per_native': 1048576,
                  'native_indices': [170, 171, 172], 'DC_channels': [178782208, 179830784, 180879360]},
    'original_reference': 'Each primary scan own first integration midpoint; dt[r]=r*tsamp for r=0..15.',
    'rounded_center_formula': 'np.rint((frequency_hz_at_own_first_midpoint-fch1_hz)/df_hz+drift_hz_s*(np.arange(16)*tsamp_s)/df_hz).astype(int64)',
    'DC_eligibility_rule': 'Eligible iff none of the sixteen inclusive center +/- width//2 boxes intersects any frozen DC channel.',
    'decision_scope': 'Prospective exploratory annotation/selection only on previously exposed per-core winners; the raw power and detector grid remain unchanged.',
    'ranking_rule': 'Within each target combine eligible central171 and adjacent512 per-core winners. Sort original score descending, then frequency_hz_at_own_first_midpoint ascending, drift_hz_s ascending, width_channels ascending, native_chunk_index ascending, core_q ascending, carrier_index_in_core ascending. Greedily retain up to3 entries with reference-channel distance>3 from previously retained entries.',
    'ties': 'Exact original floating-point score equality; explicit deterministic secondary keys; no epsilon or threshold.',
    'EMPTY_policy': 'If fewer than3 eligible separated entries exist preserve available entries, including an explicit EMPTY result if none; no fallback or tuning.',
    'output_order': 'All2289 annotated per-core records retain phase central then adjacent, target HIP97319/HIP97461/HIP97663, original audit order. Selected rows are target order then new exploratory rank1..3.',
    'expected_counts': {'groups': 6, 'central_core_winners': 753, 'adjacent_core_winners': 1536,
                        'combined_core_winners': 2289, 'per_target_core_winners': 763,
                        'geometry_row_occurrences': 36624, 'frozen_DC_row_box_checks': 109872,
                        'maximum_selected_records': 9},
    'original_domain_note': 'Each central phase has native171 q1..254 excluding64,128,192 (251). Each adjacent phase has native170 q1..255, native171 q0 and255, native172 q0..254 (512). The six central/adjacent group domains are preserved exactly; no earlier missing cores are added.',
    'CSV_consistency_sources': [pin(WORKSPACE / csv_path) for _, _, _, _, csv_path in PHASES],
    'producer_pin': pin(BASE / 'select_cached_coremax.py'),
    'metadata_preparation': {'power_arrays_opened': 0, 'maps_arrays_opened': 0,
                             'scientific_scores_printed_or_compared': 0,
                             'audit_JSON_parsed_including_uninspected_score_fields': True,
                             'capsule_presence_checked_with_stat_only': True},
    'execution_limits': {'CPU_seconds': 600, 'wall_seconds': 900, 'RAM_bytes': 1073741824,
                         'output_bytes': 8388608, 'new_telescope_HTTP': 0, 'DKK': 0,
                         'new_detector_scores': 0, 'rerun_or_overwrite': False},
    'selection_reads': 'Pinned SCORE_AUDITS/MAPS JSON and previous CORE_MAX CSV. For all2289 core winners verify raw503 NPZ whole-file byte hashes, then decode only rounded_absolute_centers.npy to verify geometry. Do not decode raw_power or standardized sums arrays. No detector map arrays are opened.',
    'interpretation_limits': [
        'The newly adopted DC eligibility rule and ranking are exploratory and apply only to this new scope; they do not alter historical results or retrospectively validate earlier A/B.',
        'Cached per-core winners are maxima over carrier, drift and width; the selection adds an eligibility condition and target ranking. It yields no calibrated false-alarm probability or SNR.',
        'A DC-contacting core winner can conceal a clean carrier or template runner-up. No runner-ups or new masked detector search are reconstructed; this shortlist is incomplete.',
        'No DC contact does not exclude other instrumental effects or radio interference and does not establish a sky source.',
        'All three primary OFF targets have one scan in one historical visit; their OFF labels are preserved and they are not independent repeat observations of the same star.',
        'No automatic detection threshold, OFF veto, A/B qualification, 2016 holdout opening, flux sensitivity or EIRP limit is established.',
        'Original A/B FAIL_CLOSED, protected2016 holdouts and closed2019 transport remain unchanged; existing2017 sources only.',
    ],
}
destination = BASE / 'scope.json'
assert not destination.exists(), 'Preserve original prospective scope'
destination.write_text(json.dumps(scope, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
print(json.dumps({'scope_path': str(destination), 'scope_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
                  'producer_sha256': scope['producer_pin']['sha256'],
                  'metadata_core_sources': sum(g['expected_coremax_records'] for g in groups),
                  'new_selection_metrics_computed': 0, 'power_arrays_opened': 0}))
