#!/usr/bin/env python3
"""Prepare portable metadata only after completed source QA; never scores."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent


def pin(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def read(path):
    return json.loads(path.read_bytes())


def copy_exact(source, target):
    if target.exists():
        assert target.read_bytes() == source.read_bytes(), str(target)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-qa-root', type=Path, required=True,
                        help='Analysis root containing actual PASS QA and its detailed audit')
    args = parser.parse_args()
    qa_rel = Path('dc_alternatives/qa/selection/QA_RECEIPT.json')
    qa = read(args.source_qa_root/qa_rel)
    assert qa['status'] == 'PASS_INDEPENDENT_EXHAUSTIVE_DC_ALTERNATIVES' and qa['mismatch_count'] == 0
    assert qa['counts']['inventory_carriers'] == 7083
    for rel in [qa_rel, Path(qa['compact_detailed_audit_pin']['path']),
                Path('dc_alternatives/qa/selection/RELOCATION_RECEIPT.json'),
                Path('dc_alternatives/qa/selection/REALPATH_REPAIR_PREFLIGHT.json')]:
        copy_exact(args.source_qa_root/rel, ROOT/rel)
    assert pin(ROOT/qa['compact_detailed_audit_pin']['path']) == qa['compact_detailed_audit_pin']
    search = ROOT/'dc_alternatives/search'
    original_scope_path = search/'scope.json'
    search_scope = read(original_scope_path)
    result_pins, raw_frames, winners, pins = [], [], [], {}
    def add(declaration):
        actual = pin(ROOT/declaration['path'])
        assert actual == declaration, declaration['path']
        assert not declaration['path'].endswith('.h5'), 'Never archive whole HDF5 sources'
        pins[declaration['path']] = declaration
        return declaration
    add(pin(original_scope_path))
    add(search_scope['excluded_inventory_pin'])
    for scan in search_scope['primary_scan_ids']:
        result_path = search/scan/'RESULT.json'
        result_pins.append(add(pin(result_path)))
        result = read(result_path)
        for summary in result['group_summaries']:
            raw_frames.append(add(summary['raw_frame_pin']))
            winners.append(add(summary['recovered_winner_arrays_pin']))
    for group in search_scope['groups']:
        add(group['source_map_metadata']['map_pin'])
        add(group['source_map_metadata']['normalization_pin'])
    for old in search_scope['cached_clean_prefixes']:
        add(old['result_pin'])
    kernel_pin = add(pin(ROOT/'dc_alternatives/qa/exhaustive_core.py'))
    selected_pin = add(pin(search/'SELECTED_TOP9.json'))
    source_qa_pin = add(pin(ROOT/qa_rel))
    expected = {'groups': 18, 'excluded_carriers': 7083, 'recovered_carriers': 7074,
                'EMPTY_carriers': 9, 'hypothesis_occurrences': 11120310,
                'admissible_hypothesis_occurrences': 10688400}
    scope = {'schema': 'PORTABLE_NUMPY_ORIGINAL_FRAME_DC_REPLAY_SCOPE_V1',
             'source_QA_actual_PASS_required': True, 'original_source_QA_pin': source_qa_pin,
             'original_search_scope_pin': pin(original_scope_path),
             'independent_kernel_pin': kernel_pin, 'producer_result_pins': result_pins,
             'selected_TOP9_pin': selected_pin, 'raw_frame_pins': raw_frames,
             'recovered_winner_array_pins': winners, 'input_pins': list(pins.values()),
             'expected_counts': expected,
             'replay_code_pin': pin(BASE/'replay_from_saved_frames.py'),
             'runtime': {'numpy': '2.3.5'},
             'limits': {'CPU_seconds': 600, 'wall_seconds': 900, 'RAM_bytes': 2147483648},
             'source_power_policy': 'Use exactly eighteen preserved float32 16x12096 original scoring crops. The separate completed source QA authenticates original H5 files, decoded rows and crop identities. This replay cannot independently reauthenticate missing whole H5 sources.',
             'numerical_policy': 'Immutable original normalization; fullframe nearest501 medians; original prefix origin/sequential16 additions; exhaustive785xwidth1,3 scores; exact unrestricted and admissible winner reconciliation; exact700/separated100/TOP3/global9 merge.',
             'new_source_float_queries_during_preparation': 0,
             'new_hypothesis_scores_during_preparation': 0,
             'new_observing_data': False, 'new_telescope_HTTP': 0,
             'interpretation': 'Portable numerical reproduction of exposed scores, not blind validation, calibrated SNR/FAP, physical independence or a SETI detection.'}
    scope_path = BASE/'portable_scope.json'
    assert not scope_path.exists()
    scope_path.write_text(json.dumps(scope, indent=2, sort_keys=True, allow_nan=False)+'\n')
    draft = {'authorized': False, 'scope_sha256': pin(scope_path)['sha256'],
             'code_sha256': scope['replay_code_pin']['sha256'],
             'source_QA_sha256': source_qa_pin['sha256'],
             'reason_pending': 'Root must publicly freeze and review this portable code/scope before numerical replay.'}
    (BASE/'PORTABLE_GO_DRAFT.json').write_text(json.dumps(draft, indent=2)+'\n')
    archive = dict(pins)
    additional = [scope_path, BASE/'replay_from_saved_frames.py', BASE/'prepare_portable_scope.py',
                  BASE/'original_frame_numpy.py', BASE/'CONTEXT_REUSE_AUDIT.json',
                  ROOT/qa['compact_detailed_audit_pin']['path'],
                  ROOT/'dc_alternatives/qa/selection/scope.json',
                  ROOT/'dc_alternatives/qa/selection/restored_admission_scope.json',
                  ROOT/'dc_alternatives/qa/selection/independent_alternative_qa.py',
                  ROOT/'dc_alternatives/qa/selection/ROOT_GO_RESTORED.json',
                  ROOT/'dc_alternatives/qa/selection/REALPATH_REPAIR_PREFLIGHT.json',
                  ROOT/'dc_alternatives/qa/selection/RELOCATION_RECEIPT.json',
                  ROOT/'dc_alternatives/review/CODE_STATIC_REVIEW.json',
                  ROOT/'dc_alternatives/review/SCIENCE_SCOPE_REVIEW.json',
                  ROOT/'dc_alternatives/ROOT_SCOPE.json',
                  search/'EXCLUDED_CARRIERS.json.gz', search/'INVENTORY_RECEIPT.json',
                  search/'recover_alternatives.py', search/'scope.json.gz',
                  search/'SELECTED_TOP9.json', search/'AGGREGATION_RECEIPT.json']
    for scan in search_scope['primary_scan_ids']:
        additional.extend([search/scan/'EXECUTION_RECEIPT.json', search/scan/'RECOVERED_CARRIERS.csv'])
    for path in additional:
        if path.is_file():
            declaration = pin(path)
            archive[declaration['path']] = declaration
    manifest = {'schema': 'DC_PORTABLE_MINIMAL_ARCHIVE_MANIFEST_V1',
                'archive_root_layout': 'Place these relative paths under a folder named analysis; code computes analysis as ROOT.',
                'files': list(archive.values()), 'uncompressed_bytes': sum(d['bytes'] for d in archive.values()),
                'whole_H5_files_included': 0, 'raw_frames_included': len(raw_frames),
                'additional_delivery_files_expected_later': ['dc_alternatives/reproduction/DC_RESULTS.md', 'dc_alternatives/reproduction/SUMMARY.json', 'dc_alternatives/reproduction/README.md', 'dc_alternatives/reproduction/PORTABLE_STATIC_REVIEW.json', 'dc_alternatives/reproduction/PORTABLE_ROOT_GO.json', 'dc_alternatives/reproduction/portable_check/REPLAY_RECEIPT.json']}
    (BASE/'MINIMAL_ARCHIVE_MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'status': 'PORTABLE_SCOPE_PREPARED_AFTER_ACTUAL_SOURCE_QA',
                     'scope_pin': pin(scope_path), 'code_pin': scope['replay_code_pin'],
                     'minimal_archive_files': len(archive), 'uncompressed_bytes': manifest['uncompressed_bytes'],
                     'new_source_float_queries': 0, 'new_hypothesis_scores': 0}))


if __name__ == '__main__':
    main()
