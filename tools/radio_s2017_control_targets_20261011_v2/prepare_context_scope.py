"""Create-only prospective fixed context scope; source text/metadata only."""
from __future__ import annotations
import argparse
import importlib.util
from pathlib import Path
import sys


def build_scope(root, primary_scope_path, primary_receipt_status, primary_selection_rule):
    driver_path = root / 'analysis/s2017_control_targets_20261011_v2/context_profiles.py'
    spec = importlib.util.spec_from_file_location('context_source_only_scope_driver', driver_path)
    c = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = c
    spec.loader.exec_module(c)
    source, acq = c.read_json(root / c.SOURCE), c.read_json(root / c.ACQ)
    primary = c.read_json(c.confined(root, primary_scope_path))
    c.require(primary_receipt_status == c.PRIMARY_STATUS
        and isinstance(primary_selection_rule, str) and primary_selection_rule, 'Exact prospective primary interface required')
    # The primary scope, its pinned code, and all context inputs are frozen now;
    # no future result/QA SHA or observed winning tuple belongs in this scope.
    pins = dict(c.PINS)
    for name in (c.BASE + '/context_profiles.py', c.BASE + '/prepare_context_scope.py',
                 c.BASE + '/qa_saved.py', primary_scope_path):
        pins[name] = c.digest(c.confined(root, name))
    for name, value in primary.get('text_code_pins', {}).items():
        c.require(Path(name).suffix in ('.json', '.py'), 'Only primary text/code pins in context preparation')
        sha = value if isinstance(value, str) else value['sha256']
        c.require(c.digest(c.confined(root, name)) == sha, 'Primary prospective text/code pin differs')
        pins[name] = sha
    return {'schema': 'SETI_S2017_CONTROL_TARGET_FIXED_CONTEXT_SCOPE_V1',
        'status': 'PROSPECTIVE_FROZEN_METHOD_BEFORE_PRIMARY_RESULT_VALUES',
        'primary_scope_path': primary_scope_path, 'primary_scope_sha256': c.digest(root / primary_scope_path),
        'primary_receipt_status': primary_receipt_status, 'primary_selection_rule': primary_selection_rule,
        'primary_QA_source_sha256': pins[c.BASE + '/qa_saved.py'],
        'primary_QA_schema': c.QA_SCHEMA, 'primary_QA_status': c.QA_STATUS,
        'independent_context_review_paths': list(c.REVIEW_PATHS),
        'primary_ids': list(c.TARGETS), 'scan_order': list(c.SCANS), 'eligible_core_q': list(c.CORES),
        'compact_records': acq['decoded_files'], 'text_code_pins': pins,
        'native_chunk_index': 171, 'core_channels': 4096, 'halo_channels': 4000,
        'search_widths': [1, 3], 'drift_grid_count': 785, 'running_median_channels': 501,
        'selected_tracks_per_primary': 3, 'selected_tracks_total': 9, 'context_scores': 54,
        'source_decoded_rows': 96, 'raw_capsule_channels': 503,
        'CPU_cap_s': 180, 'wall_cap_s': 300, 'memory_cap_bytes': 2 * 1024**3,
        'output_cap_bytes': 32 * 1024**2, 'workspace_cap_bytes': 8 * 1024**3,
        'score_match_absolute_tolerance': 1e-7, 'score_match_relative_tolerance': 1e-10,
        'prospective_all_tuple_geometry': c.geometry(source),
        'relative_time_formula': '(context_header_tstart-origin_header_tstart)*86400+j*TSAMP; equal integration midpoint halves cancel; origin row0 exactly0',
        'absolute_rounding_formula': 'rint((primary_reference_frequency-FCH1)/DF+frozen_drift*time/DF), then subtract native/crop origin',
        'normalization_rule': 'Same original primary q4096 static absolute core channels in every scan, unchanged detector.preprocess with halo4000 and running median501',
        'fixed_score_rule': 'sum all16 selected-width standardized raw-box terms / sqrt(16*selected_width), direct sum without detector grid',
        'selection_rule': 'Exact first3 of each independently completed/QA-passed primary TOP20; no re-fit, shift, drift/width optimization, threshold filtering or context-driven selection',
        'runtime_admission': 'Caller exact3 COMPLETE receipt hashes and independent primary-map QA hash; QA pins exactTOP3/TOP20. Scope freezes method and primary code/scope before any primary values, not unknown future output hashes.',
        'qualification_limits': ['Nine tracks are selected by primary search; same-cadence context is post-selection, not blind confirmation.',
            'Other five pointings are direction/time context; original roles remain ON/OFF and are not blanksky controls or independent repeated scans of each primary target.',
            'Primary785-drift spacing is fixed from own16-row span and does not guarantee whole-cadence subchannel matching.',
            'No carrier/drift optimization, ON/OFF veto, physical cause, calibrated SNR/FAP, independent visit or qualified SETI detection.'],
        'new_HTTP_requests': 0, 'qualified_SETI_detection': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--primary-scope', required=True)
    parser.add_argument('--primary-receipt-status', required=True)
    parser.add_argument('--primary-selection-rule', required=True)
    parser.add_argument('--output', default='analysis/s2017_control_targets_20261011_v2/context_scope.json')
    args = parser.parse_args()
    root = args.root.resolve()
    scope = build_scope(root, args.primary_scope, args.primary_receipt_status, args.primary_selection_rule)
    c = sys.modules['context_source_only_scope_driver']
    c.contract(root, scope)
    c.save(c.confined(root, args.output), scope)
    print(c.digest(root / args.output))


if __name__ == '__main__':
    main()
