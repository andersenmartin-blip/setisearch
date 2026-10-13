"""Trace original ON adapters and producing receipts without science payloads."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import math
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
COUNT, CORE, HALO = 1048576, 4096, 4000
RESTORE = ROOT / 'on_cached/feasibility/ON_RESULTS_RESTORATION_RECEIPT.json'
CENTRAL = ROOT / 'on_cached/on_results/central'
ADJACENT = ROOT / 'on_cached/on_results/adjacent'
ROWFIELDS = ('row_power_median', 'row_residual_median',
             'row_winsorized_residual_location', 'row_residual_MAD_scale')


def pin(path):
    data = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def snippet(path, first, last, purpose):
    lines = path.read_text().splitlines()
    return {'file_pin': pin(path), 'line_range_inclusive': [first, last],
            'purpose': purpose,
            'numbered_lines': [{'line': i, 'text': lines[i - 1]} for i in range(first, last + 1)]}


def main():
    started = time.monotonic()
    restoration = json.loads(RESTORE.read_text())
    originals = {p['path']: p for p in restoration['restored_file_pins']}

    def original_pin(path):
        observed = pin(path)
        assert originals.get(observed['path']) == observed, path
        return observed

    detector = CENTRAL / 'analysis/new_visit_search/dependencies/detector.py'
    detector_pin = original_pin(detector)
    specs = {
        'central_recovery_q128': {
            'driver': CENTRAL / 'analysis/new_visit_recovery/driver.py',
            'scope': CENTRAL / 'analysis/new_visit_recovery/scope.json',
            'receipt': CENTRAL / 'analysis/new_visit_recovery/results/search/EXECUTION_RECEIPT.json',
            'adapter_lines': [234, 242]},
        'central_fullband_q127': {
            'driver': CENTRAL / 'analysis/s2017_full_band/driver.py',
            'scope': CENTRAL / 'analysis/s2017_full_band/scopes/batch02.json',
            'receipt': CENTRAL / 'analysis/s2017_full_band/results/batch02/EXECUTION_RECEIPT.json',
            'adapter_lines': [272, 277]},
        'adjacent_native170_q127_q128': {
            'driver': ADJACENT / 'analysis/s2017_next_native/search/driver.py',
            'scope': ADJACENT / 'analysis/s2017_next_native/search/scopes/native170_batch02.json',
            'receipt': ADJACENT / 'analysis/s2017_next_native/results/search/native170_batch02/EXECUTION_RECEIPT.json',
            'adapter_lines': [348, 353]},
        'adjacent_native172_q127_q128': {
            'driver': ADJACENT / 'analysis/s2017_next_native/search/driver.py',
            'scope': ADJACENT / 'analysis/s2017_next_native/search/scopes/native172_batch02.json',
            'receipt': ADJACENT / 'analysis/s2017_next_native/results/search/native172_batch02/EXECUTION_RECEIPT.json',
            'adapter_lines': [348, 353]},
    }
    producing, evidence = {}, []
    for name, spec in specs.items():
        scope = json.loads(spec['scope'].read_text())
        receipt = json.loads(spec['receipt'].read_text())
        dp, sp, rp = (original_pin(spec[k]) for k in ('driver', 'scope', 'receipt'))
        assert receipt['driver_sha256'] == scope['driver_sha256'] == dp['sha256'], name
        assert receipt['scope_sha256'] == sp['sha256'], name
        deps = scope.get('unchanged_original_dependency_SHA256s', scope.get('unchanged_dependency_SHA256s'))
        assert deps['detector'] == detector_pin['sha256'], name
        assert scope['rows_per_scan'] == 16 and scope['core_channel_count'] == CORE
        assert scope['crop_halo_channels'] == HALO and scope['widths_channels'] == [1, 3]
        assert scope['drift_grid'] == {'first_hz_s': -4, 'last_hz_s': 4, 'count': 785}
        assert receipt['status'].startswith('COMPLETE_')
        expected = scope['runtime_package_versions']
        for k, value in expected.items():
            assert receipt['runtime_versions'][k] == value, (name, k)
        assert receipt['runtime_versions']['numpy'] == '2.3.5'
        assert receipt['runtime_versions']['scipy'] == '1.17.0'
        producing[name] = {
            'driver_pin': dp, 'scope_pin': sp, 'producing_completed_execution_receipt_pin': rp,
            'producing_completed_status': receipt['status'],
            'driver_SHA_matches_original_completed_receipt_and_scope': True,
            'scope_SHA_matches_original_completed_receipt': True,
            'detector_SHA_matches_original_scope_dependency_declaration': True,
            'original_detector_pin': detector_pin, 'original_detector_code_path_in_scope': scope['code_paths']['detector'],
            'producing_runtime_versions_from_completed_receipt': receipt['runtime_versions'],
            'public_freeze_commit_from_completed_receipt': receipt['public_freeze_commit'],
            'scope_rows': 16, 'core_channel_count': CORE, 'crop_halo_channels_each_side': HALO,
            'original_widths_channels': [1, 3], 'original_drift_grid': scope['drift_grid'],
        }
        evidence.append(snippet(spec['driver'], *spec['adapter_lines'],
                                'Actual original Scan power slice, source origin, normalization channels, and search call'))
    evidence.extend([
        snippet(detector, 17, 28, 'Original Scan positional-field mapping and full16 expected rows'),
        snippet(detector, 111, 150, 'Whole-frame float64 preprocessing, core4096 metadata domain,501 median filter, location/MAD and z equation'),
        snippet(detector, 152, 160, 'Original float64 cumulative-sum origin is first z/s.power frame cell'),
        snippet(CENTRAL / 'analysis/new_visit_recovery/driver.py', 224, 232,
                'Full-native row medians are separate historical fixed-profile normalization; then detector uses original Config widths1/3'),
    ])
    selected = [r for r in restoration['map_inventory']
                if r['scan_id'] in ('epoch1_on', 'epoch2_on', 'epoch3_on')
                and r['native_chunk_index'] in (170, 171, 172) and r['core_q'] in (127, 128)]
    expected_ids = {(s, n, q) for s in ('epoch1_on', 'epoch2_on', 'epoch3_on')
                    for n in (170, 171, 172) for q in (127, 128)}
    assert len(selected) == 18 and {(r['scan_id'], r['native_chunk_index'], r['core_q']) for r in selected} == expected_ids
    checkpoints, groups = {}, []
    for item in selected:
        n, q, scan = item['native_chunk_index'], item['core_q'], item['scan_id']
        family = ('central_recovery_q128' if q == 128 else 'central_fullband_q127') if n == 171 else f'adjacent_native{n}_q127_q128'
        contract = producing[family]
        cp_path = ROOT / item['checkpoint_pin']['path']
        cp_pin = original_pin(cp_path)
        assert cp_pin == item['checkpoint_pin']
        if cp_pin['path'] not in checkpoints:
            checkpoints[cp_pin['path']] = json.loads(cp_path.read_text())
        cp = checkpoints[cp_pin['path']]
        assert cp['complete'] is True
        first, stop = n * COUNT + q * CORE, n * COUNT + (q + 1) * CORE
        ref = [first, stop]
        assert item['reference_channel_interval_half_open'] == ref
        declarations = [x for x in cp['receipts'] if x['scan_id'] == scan and x['reference_channel_interval_half_open'] == ref]
        assert len(declarations) == 1
        declared = declarations[0]
        assert declared['searched_carriers'] == CORE and declared['valid_hypotheses_per_carrier'] == 1570
        np = ROOT / item['normalization_pin']['path']
        norm_pin = pin(np)
        assert norm_pin == item['normalization_pin']
        norm = json.loads(np.read_text())
        assert norm['normalization_source_channels'] == list(range(first, stop))
        assert norm['normalization_unmasked_counts'] == [CORE] * 16
        assert all(len(norm[k]) == 16 and all(math.isfinite(v) for v in norm[k]) for k in ROWFIELDS)
        assert all(v > 0 for v in norm['row_power_median']) and all(v > 0 for v in norm['row_residual_MAD_scale'])
        if item['normalization_is_inline_checkpoint_metadata']:
            assert n == 171 and q == 128 and norm == declared['normalization']
            provenance = 'Field-for-field original inline normalization object; derived metadata copy only.'
            normalization_declared_field_names = ['normalization']
        else:
            assert original_pin(np) == norm_pin
            d = declared['normalization']
            assert d['sha256'] == norm_pin['sha256'] and d['bytes'] == norm_pin['bytes']
            assert (cp_path.parent / d['path']).resolve() == np.resolve()
            provenance = 'Original archived normalization file; exact checkpoint path/bytes/SHA256 declaration.'
            normalization_declared_field_names = ['normalization.path', 'normalization.bytes', 'normalization.sha256']
        m = item['map_pin']
        assert m['sha256'] == declared['sha256'] and m['bytes'] == declared['bytes']
        assert (cp_path.parent / declared['path']).resolve() == (ROOT / m['path']).resolve()
        left, right = first - HALO, stop + HALO
        dc = n * COUNT + COUNT // 2
        groups.append({
            'scan_id': scan, 'native_chunk_index': n, 'core_q': q, 'producing_contract_id': family,
            'original_s_power_dtype_inferred_from_original_float32_adapter_slice': '<f4',
            'original_s_power_shape': [16, CORE + 2 * HALO],
            'original_s_power_source_channel0': left,
            'original_s_power_source_channel_interval_half_open': [left, right],
            'native_parent_source_channel0': n * COUNT,
            'native_parent_shape_read_by_adapter': [16, COUNT],
            'native_parent_slice_local_half_open': [q * CORE - HALO, (q + 1) * CORE + HALO],
            'parent_is_not_original_detector_frame': True,
            'preprocessing_frame': {'shape': [16, CORE + 2 * HALO], 'dtype': '<f8',
                                    'absolute_source_interval_half_open': [left, right],
                                    'running_median_channels': 501, 'median_filter_mode': 'nearest',
                                    'residual_domain': 'Every cell of original12096 detector crop frame.',
                                    'row_level_location_MAD_domain': 'Original4096 physical reference core only.'},
            'normalization_source_channel_interval_half_open': ref,
            'normalization_local_indices_half_open': [HALO, HALO + CORE],
            'full16_normalization_terms': list(ROWFIELDS),
            'normalization_unmasked_counts': [CORE] * 16,
            'original_normalization_pin': norm_pin,
            'normalization_is_inline_checkpoint_metadata': item['normalization_is_inline_checkpoint_metadata'],
            'normalization_origin_proof': provenance,
            'normalization_checkpoint_field_names': normalization_declared_field_names,
            'original_checkpoint_pin': cp_pin, 'original_checkpoint_member': item['original_checkpoint_member'],
            'original_map_pin_declared_by_checkpoint_only_not_map_payload_read': m,
            'original_map_checkpoint_field_names': ['path', 'bytes', 'sha256', 'scan_id', 'reference_channel_interval_half_open'],
            'original_DC_source_channel': dc, 'original_DC_local_frame_index': dc - left,
            'prefix_arithmetic': {'dtype': '<f8', 'zero_initial_column': True,
                                  'cumsum_axis': 1, 'cumsum_absolute_origin_channel': left,
                                  'cumsum_source_frame_columns': CORE + 2 * HALO,
                                  'row_box_expression': 'prefix[:,width:] - prefix[:,:-width]',
                                  'local_original_box_sum_is_not_identical_floating_point_expression': True},
        })
    evidence_path = OUT / 'ORIGINAL_ON_FRAME_EVIDENCE.json'
    save(evidence_path, {'schema': 'SETI_ORIGINAL_ON_FRAME_TEXT_EVIDENCE_V1', 'evidence': evidence})
    result = {
        'schema': 'SETI_ORIGINAL_ON_DC_GROUP_FRAME_INVENTORY_V1',
        'status': 'PASS_EXACT18_ORIGINAL12096_CROP_FRAMES_PRODUCING_CODE_SCOPE_CHECKPOINT_AND_RUNTIME_BOUND',
        'restoration_receipt_pin': pin(RESTORE),
        'counts': {'requested_group_frames': 18, 'crop12096_original_detector_frames': 18,
                   'fullnative1048576_original_detector_frames': 0, 'unique_producing_contracts': 4,
                   'unique_driver_codes': 3, 'original_q128_inline_metadata_normalizations': 3},
        'producing_contracts': producing, 'groups': groups,
        'evidence_pin': pin(evidence_path),
        'original_detector_pin': detector_pin,
        'producing_runtime_versions_are_from_completed_receipts_not_current_runtime': True,
        'original_saved_prefix_or_preprocessed_z_artifact': {
            'declared_by_original_adapters': False,
            'reason': 'All original adapters bind result,_=detector.search_scan and discard second returned cached box arrays. Their map writers store result numerical arrays plus channel/drift-grid metadata, not prefix or entire preprocessed z frame.',
            'scope': 'Static original adapter output contract; no NPZ payload inspection asserted.'},
        'metadata_only_limits': {'NPZ_score_or_payload_values_read': False, 'HDF5_or_source_power_values_read': False,
                                 'detector_or_alternative_numerical_queries_executed': False},
        'important_distinction': 'Full-native parent loading and separate historical visual-profile fullnative row medians do not define detector s.power frame. All18 actual completed searches used16x12096 crops and4096-core normalization.',
        'prefix_replay_requirement': 'For original floating-point row-box arithmetic, replay full original12096 z frame and np.cumsum from its actual leftedge under original NumPy2.3.5/SciPy1.17.0 producing runtime contract; local box-cell sums or another frame prefix origin are different arithmetic.',
        'mismatches': [], 'wall_seconds': time.monotonic() - started,
    }
    save(OUT / 'ORIGINAL_ON_FRAME_INVENTORY.json', result)
    print(json.dumps({'status': result['status'], 'counts': result['counts'], 'wall_seconds': result['wall_seconds']}))


if __name__ == '__main__':
    main()
