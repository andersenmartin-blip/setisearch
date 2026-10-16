#!/usr/bin/env python3
"""Exercise the unchanged full-case consumer on one new ENGINEERING case.

This writes genuine legacy inputs/maps NPZ projections one array at a time from
the authenticated new payload. The detector result, recipe, truth, admission,
and every original descriptor survive unchanged. A separate, explicit bridge
adds only a completion envelope derived from the exact parent's wait4 receipt.
The unchanged summarizer's local VALID_CASE result is a compatibility outcome,
never a study admission. No old main, admission, case bank, calibration function,
rank function, RNG, telescope file, or historical result bank is invoked.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1]
LEGACY = SOURCE / 'analysis' / 'sixscan_burst_20261015'
PAYLOAD_ROOT = SOURCE / 'tools' / 'science_payload_20261016'
MODE = 'ENGINEERING_FIXTURES_ONLY'
SUMMARY_SHA256 = 'b742fc40bebc041c7917e5d6801b3d0e4b13aed41931b922009c01017b6d0c06'
GUARD_SHA256 = 'd02505861e9a5b3883708836e39b6a8712d56f983c740897857bb0f6e201e492'
QA_STATUS = 'PASS_COMPLETE_SEARCH_ENGINEERING_ONLY'
RANK_STATUS = 'NOT_APPLIED_NO_CALIBRATION'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def load(path, name, pin=None):
    if pin is not None:
        require(digest(path) == pin, 'Pinned consumer dependency differs: ' + str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def guarded_receipt(path, guard):
    receipt = read(path)
    limits = receipt['limits']
    require(guard.policy(limits['cpu_s'], limits['wall_s'], limits['address_space_bytes']) == limits,
            'Noncanonical whole-child guard policy')
    require(guard.assess(receipt, limits)['resource_acceptance'] is True and
            receipt.get('resource_acceptance') is True and receipt.get('interruption') is None,
            'Unaccepted or interrupted parent whole-child receipt')
    return receipt


def descriptor_inventory(value, found=None):
    found = {} if found is None else found
    if type(value) is dict and set(value) == {'array_descriptor'}:
        descriptor = value['array_descriptor']
        key = descriptor['npz_key']
        require(key not in found, 'Duplicate original legacy descriptor')
        found[key] = descriptor
    elif type(value) is dict:
        for child in value.values(): descriptor_inventory(child, found)
    elif type(value) is list:
        for child in value: descriptor_inventory(child, found)
    return found


def write_json(budget, path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    with budget.writer(path) as stream: stream.write(raw)


def array_specs(descriptors, np):
    specs = []
    for key, descriptor in descriptors.items():
        require(key == descriptor['npz_key'] and key and '/' not in key and '\\' not in key,
                'Invalid original NPZ key')
        dtype = np.dtype(descriptor['dtype'])
        require(not dtype.hasobject and descriptor['nbytes'] == math.prod(descriptor['shape']) * dtype.itemsize,
                'Original legacy descriptor geometry differs')
        specs.append({'key': key, 'shape': descriptor['shape'], 'dtype': dtype.str,
                      'nbytes': descriptor['nbytes']})
    return specs


def write_projection_arrays(archive, folder, descriptors, truth, metadata, transport, budget, np):
    map_specs = array_specs(descriptors, np)
    require(map_specs, 'A genuine complete maps array inventory is required')
    def map_value(spec):
        array = archive.load(('worker_arrays', spec['key']))
        require(transport.arrays.input_hash(array) == descriptors[spec['key']]['C_order_bytes_sha256'],
                'Original worker array hash changed in transport')
        return array
    map_copies = transport.arrays.write_arrays(folder / 'maps.npz', map_specs, map_value, budget)
    map_verified = transport.arrays.verify_arrays(folder / 'maps.npz', map_copies, map_specs)
    input_specs = []
    for scan in metadata:
        key = scan['scan_id']
        original = truth['authenticated_input_arrays'][key]
        shape = original['shape']
        dtype = np.dtype(original['dtype'])
        require(shape == [16, 12096] and dtype == np.dtype('<f4'), 'Full six-scan input shape/dtype required')
        input_specs.append({'key': key, 'shape': shape, 'dtype': dtype.str,
                            'nbytes': math.prod(shape) * dtype.itemsize})
    require(len(input_specs) == 6, 'All six genuine raw arrays required')
    def input_value(spec):
        array = archive.load(('inputs', spec['key']))
        require(transport.arrays.input_hash(array) ==
                truth['authenticated_input_arrays'][spec['key']]['C_order_bytes_sha256'],
                'Original complete input array hash differs')
        return array
    input_copies = transport.arrays.write_arrays(folder / 'inputs.npz', input_specs, input_value, budget)
    input_verified = transport.arrays.verify_arrays(folder / 'inputs.npz', input_copies, input_specs)
    return {'maps': map_verified, 'inputs': input_verified,
            'written_one_array_at_a_time': True, 'dummy_or_placeholder_NPZ_files': False}


def recovery_census(saved, independent, hit_by_id):
    require(saved['active_ON_scan_ids'] == list(saved['by_scan']), 'Saved recovery scan inventory differs')
    require(independent['applicable'] is bool(saved['active_ON_scan_ids']), 'Independent recovery applicability differs')
    if not saved['active_ON_scan_ids']:
        return {'applicable': False, 'by_scan': {}}
    require(set(independent['by_scan']) == set(saved['by_scan']), 'Independent active recovery scans differ')
    rows = {}
    for scan_id, value in saved['by_scan'].items():
        pre = value['pre_OFF_matches']; after = value['final_matches']
        for matches in (pre, after):
            ids = [m['hit_id'] for m in matches]
            require(len(ids) == len(set(ids)), 'Duplicate localized recovery identity')
            for match in matches:
                origin = hit_by_id[match['hit_id']]
                require(origin['scan_id'] == scan_id and origin['ON_score'] == match['ON_score'],
                        'Localized recovery source identity or score differs')
        require(all(hit_by_id[m['hit_id']]['disposition'] == 'SURVIVOR_EXPLORATORY' for m in after),
                'After-OFF recovery refers to a vetoed hit')
        own = independent['by_scan'][scan_id]
        require(own['pre_OFF'] is bool(pre) and own['after_OFF'] is bool(after),
                'Complete independent localized recovery decisions differ')
        require(own['after_OFF_hit_ids'] == [m['hit_id'] for m in after],
                'Complete independent localized after-OFF identity census differs')
        require(value['pre_OFF_localized_count'] == len(pre) and value['final_localized_count'] == len(after),
                'Saved localized recovery counts differ')
        rows[scan_id] = {'pre_OFF_count': len(pre), 'after_OFF_count': len(after),
                         'pre_OFF_hit_ids': [m['hit_id'] for m in pre],
                         'after_OFF_hit_ids': [m['hit_id'] for m in after]}
    require(saved['all_active_ON_pre_OFF_recovered'] is all(x['pre_OFF_count'] > 0 for x in rows.values()),
            'All-active pre-OFF recovery differs')
    require(saved['all_active_ON_final_recovered'] is all(x['after_OFF_count'] > 0 for x in rows.values()),
            'All-active after-OFF recovery differs')
    return {'applicable': True, 'by_scan': rows,
            'all_active_pre_OFF_recovered': all(x['pre_OFF_count'] > 0 for x in rows.values()),
            'any_active_pre_OFF_recovered': any(x['pre_OFF_count'] > 0 for x in rows.values()),
            'all_active_after_OFF_recovered': all(x['after_OFF_count'] > 0 for x in rows.values()),
            'any_active_after_OFF_recovered': any(x['after_OFF_count'] > 0 for x in rows.values())}


def run_check(payload_folder, producer_receipt_path, qa_report_path, qa_receipt_path,
              scope_path, projection_root, report_path, *, payload_cap, projection_cap):
    scope = read(scope_path)
    require(scope['mode'] == MODE and scope['scientific_bank_admission'] is False,
            'A frozen engineering-only scope is required')
    frozen = set()
    for pin in scope['source_pins']:
        relative = Path(pin['path'])
        require(not relative.is_absolute() and '..' not in relative.parts,
                'Unsafe frozen source pin')
        path = (SOURCE / relative).resolve()
        require(SOURCE in path.parents and pin['path'] not in frozen,
                'Frozen source escapes checkout or repeats a path')
        require(path.stat().st_size == pin['bytes'] and digest(path) == pin['sha256'],
                'Frozen source changed before complete case consumption')
        frozen.add(pin['path'])
    require({'tools/fullsearch_integration_20261016/summary_check.py',
             'tools/science_payload_20261016/payload.py',
             'analysis/sixscan_burst_20261015/summarize.py',
             'analysis/sixscan_burst_20261015/contract.json'} <= frozen,
            'Incomplete frozen summary prerequisites')
    # Imports occur only in this separately guarded summary child after freeze.
    import numpy as np
    transport = load(PAYLOAD_ROOT / 'payload.py', 'fullsearch_summary_transport')
    summary = load(LEGACY / 'summarize.py', 'fullsearch_unchanged_summary', SUMMARY_SHA256)
    guard = load(SOURCE / 'tools/whole_child_guard_20261015/guard.py', 'fullsearch_summary_guard', GUARD_SHA256)
    producer_guard = guarded_receipt(producer_receipt_path, guard)
    qa_guard = guarded_receipt(qa_receipt_path, guard)
    resources = scope['resources']
    for receipt, cpu in ((producer_guard, resources['primary_CPU_s']),
                         (qa_guard, resources['qa_CPU_s'])):
        require(receipt['limits'] == guard.policy(cpu, resources['primary_QA_wall_s'],
                resources['child_address_space_bytes']), 'Guard limits differ from the whole prospective scope')
    qa = read(qa_report_path)
    require(qa['status'] == QA_STATUS and qa['actual_complete_search_QA_performed'] is True,
            'A completed independent full-search engineering QA pass is required')
    require(qa.get('scientific_admission') is False, 'QA must not grant a scientific admission')
    require(qa['scope_sha256'] == digest(scope_path) and
            qa['producer_guard_receipt_sha256'] == digest(producer_receipt_path),
            'Complete independent QA scope or producer whole-child binding differs')
    require(qa['producer_receipt_sha256'] == digest(Path(payload_folder).parent / 'PRODUCER.json'),
            'Complete independent QA producer side receipt differs')
    archive = transport.verify_payload(payload_folder, cap=payload_cap,
        expected_semantic_sha256=qa['payload_semantic_sha256'], max_total_raw_bytes=projection_cap)
    require(qa['payload_manifest_sha256'] == digest(Path(payload_folder) / 'MANIFEST.json'),
            'Independent complete QA payload manifest pin differs')
    recipe = archive.load(('case',)); truth = archive.load(('truth',))
    admission = archive.load(('admission',)); encoded = archive.load(('worker_json',))
    descriptors = archive.load(('legacy_descriptors',))
    require(admission.get('scientific_admission') is False and admission.get('mode') == MODE,
            'New payload must retain its engineering-only admission structure')
    require(admission['scope_sha256'] == digest(scope_path), 'Original payload frozen scope pin differs')
    identity = recipe['case_id']
    require(identity == truth['case_id'] == encoded['case_id'] == qa['identity'] == scope['identity'],
            'Fresh engineering payload/QA/scope identities differ')
    require('ENGINEERING' in identity and encoded['case_index'] == 0 and encoded['exposed'] is False,
            'Only a newly named ordinary engineering case index0 is supported')
    require(truth['seed_sha256'] == recipe['seed_sha256'] == hashlib.sha256(identity.encode('ascii')).hexdigest(),
            'Deterministic engineering identity binding differs; no RNG is invoked')
    contract = read(LEGACY / 'contract.json'); metadata = contract['geometry']['scan_metadata']
    require(archive.load(('contract',)) == contract, 'Original transported complete contract differs')
    require(truth['active_ON_scan_ids'] == [metadata[i]['scan_id'] for i in recipe['active_scan_indices']
                                         if metadata[i]['role'] == 'ON'], 'Recipe truth ON activity differs')
    require(descriptor_inventory(encoded) == descriptors, 'Complete original legacy descriptor census differs')
    for forbidden in ('status', 'data_integrity_ok', 'resource_receipt', 'array_store'):
        require(forbidden not in encoded, 'Projection must not overwrite original result envelope: ' + forbidden)
    require(len(qa['full_search_checks']) == 6 and
            {x['scan_id'] for x in qa['full_search_checks']} == {x['scan_id'] for x in metadata},
            'All six complete independent scan-search receipts required')
    qa_scans = {x['scan_id']: x for x in qa['full_search_checks']}
    for meta, mapping in zip(metadata, encoded['scan_maps']):
        checked = qa_scans[meta['scan_id']]
        carrier_count = mapping['reference_source_channels']['array_descriptor']['shape'][0]
        require(checked['complete_search_recomputed'] is True and checked['complete_retained_maps_checked'] is True
                and checked['carrier_count'] == carrier_count and checked['role'] == meta['role'],
                'Complete independent scan search/map census differs')
        require(qa['independent_input_hashes'][meta['scan_id']] ==
                truth['authenticated_input_arrays'][meta['scan_id']]['C_order_bytes_sha256'],
                'Complete independent raw input hash differs')
        if meta['role'] == 'OFF':
            require(qa['OFF_inventory_checks'][meta['scan_id']] ==
                    encoded['OFF_inventory_certificates'][meta['scan_id']]['inventory_rows'],
                    'Complete independent OFF inventory record census differs')
    projection_root, report_path = Path(projection_root), Path(report_path)
    require(not projection_root.exists() and not projection_root.is_symlink(), 'Exclusive fresh engineering projection required')
    require(not report_path.exists() and report_path.parent.is_dir(), 'Exclusive summary report path required')
    projection_root.mkdir()
    folder = projection_root / 'results' / 'cases' / 'C0000'; folder.mkdir(parents=True)
    qa_folder = projection_root / 'results' / 'qa'; qa_folder.mkdir()
    budget = transport.store.Budget(projection_cap)
    with budget.writer(projection_root / 'SCOPE.json') as stream: stream.write(Path(scope_path).read_bytes())
    original = copy.deepcopy(encoded)
    encoded.update(status='COMPLETED_CASE_ONLY', data_integrity_ok=True,
        resource_receipt={'cpu_s': producer_guard['whole_child_CPU_s'], 'wall_s': producer_guard['wall_s'],
             'peak_rss_bytes': producer_guard['peak_RSS_bytes'],
             'caps': {'cpu_s': producer_guard['limits']['cpu_s'], 'wall_s': producer_guard['limits']['wall_s'],
                      'address_space_bytes': producer_guard['limits']['address_space_bytes']}},
        array_store={'file': 'maps.npz', 'descriptors': descriptors, 'all_array_fields_preserved': True})
    require({k: encoded[k] for k in original} == original, 'Projection changed an original result field')
    array_audit = write_projection_arrays(archive, folder, descriptors, truth, metadata, transport, budget, np)
    for name, value in (('output.json', encoded), ('truth.json', truth), ('case_definition.json', recipe),
                        ('admission.json', admission)):
        write_json(budget, folder / name, value)
    provenance = {'mode': MODE, 'scientific_admission': False, 'identity': identity,
        'meaning': 'Legacy file-format and unchanged case_record interoperability only',
        'producer_guard_receipt_sha256': digest(producer_receipt_path),
        'complete_QA_report_sha256': digest(qa_report_path), 'QA_guard_receipt_sha256': digest(qa_receipt_path),
        'payload_manifest_sha256': digest(Path(payload_folder) / 'MANIFEST.json'),
        'payload_semantic_sha256': archive.receipt['semantic_sha256'],
        'only_added_output_fields': ['status', 'data_integrity_ok', 'resource_receipt', 'array_store'],
        'resource_envelope_source': 'Exact complete parent wait4 measurements, not worker self-report',
        'array_projection_audit': array_audit, 'original_numeric_fields_modified': False,
        'old_scientific_admission_or_main_called': False, 'rank_status': RANK_STATUS}
    write_json(budget, folder / 'PROJECTION_PROVENANCE.json', provenance)
    manifest = {path.name: {'bytes': path.stat().st_size, 'sha256': digest(path)}
                for path in sorted(folder.iterdir()) if path.is_file()}
    write_json(budget, folder / 'artifact_manifest.json', manifest)
    write_json(budget, folder / 'COMMITTED.json', {'status': 'COMPLETED_CASE_ONLY',
        'case_id': identity, 'case_index': 0, 'exposed': False, 'data_integrity_ok': True,
        'artifact_manifest_sha256': digest(folder / 'artifact_manifest.json'),
        'engineering_format_projection_only': True, 'scientific_admission': False})
    bridge = {'status': 'PASS', 'status_meaning': 'Complete engineering QA format bridge only',
        'case_index': 0, 'case_id': identity, 'scientific_admission': False,
        'output_sha256': digest(folder / 'output.json'), 'truth_sha256': digest(folder / 'truth.json'),
        'artifact_manifest_sha256': digest(folder / 'artifact_manifest.json'),
        'scope_sha256': digest(projection_root / 'SCOPE.json'),
        'actual_complete_QA_report_sha256': digest(qa_report_path),
        'actual_complete_QA_guard_receipt_sha256': digest(qa_receipt_path),
        'actual_complete_QA_status': qa['status']}
    write_json(budget, qa_folder / 'C0000.json', bridge)
    row, consumed, consumed_truth = summary.case_record(projection_root, 0, recipe, require_qa=True, contract=contract)
    require(row['status'] == 'VALID_CASE' and row['data_integrity_ok'] and row['measurement_available'],
            'Unchanged case_record rejected engineering projection: ' + row['failure_reason'])
    require(consumed == encoded and consumed_truth == truth, 'Actual consumer omitted or changed result/truth fields')
    hits = consumed['all_ON_threshold_hypotheses']; by_id = {h['hit_id']: h for h in hits}
    require(len(by_id) == len(hits), 'Independent complete hit identity census differs')
    on = {s['scan_id'] for s in metadata if s['role'] == 'ON'}
    require(all(h['scan_id'] in on and math.isfinite(h['ON_score']) and h['ON_score'] >= 10 for h in hits),
            'Invalid actual complete ON hit')
    survivor_ids = [h['hit_id'] for h in hits if h['disposition'] == 'SURVIVOR_EXPLORATORY']
    require(len(survivor_ids) == row['after_OFF_survivor_count'] == consumed['surviving_ON_threshold_hypothesis_count'],
            'Independent actual after-OFF survivor census differs')
    maximum = consumed['maximum_pre_OFF_ON_score']
    require(maximum == qa['independent_global_pre_OFF_ON_maximum'] == row['maximum_pre_OFF_ON_score'],
            'Independent complete pre-OFF maximum differs')
    require(row['raw_ON_hit_count'] == len(hits), 'Independent actual raw ON hit census differs')
    recovery = recovery_census(consumed['recovery'], qa['independent_recovery'], by_id)
    diagnostic = {}
    for key, value in consumed.get('fixture_diagnostic_recovery', {}).items():
        independent = qa.get('independent_diagnostic_recovery', {}).get(key)
        require(independent is not None, 'Diagnostic recovery lacks complete independent QA: ' + key)
        diagnostic[key] = recovery_census(value, independent, by_id)
    report = {'schema': 'SETI_UNCHANGED_FULLCASE_CONSUMER_ENGINEERING_V1',
        'status': 'PASS_COMPLETE_CASE_SUMMARY_ENGINEERING_ONLY', 'mode': MODE, 'identity': identity,
        'unchanged_case_record_status': row['status'], 'case_record_row': row,
        'case_record_status_meaning': 'Engineering fixture interoperability; no scientific bank admission',
        'summarizer_sha256': SUMMARY_SHA256, 'provenance': provenance,
        'full_result_and_truth_preserved': True, 'complete_legacy_descriptors_preserved': True,
        'actual_ON_hit_count': len(hits), 'actual_after_OFF_survivor_count': len(survivor_ids),
        'actual_OFF_matched_count': len(hits) - len(survivor_ids),
        'actual_hit_census_by_ON_scan': {scan: sum(h['scan_id'] == scan for h in hits) for scan in sorted(on)},
        'independent_localized_primary_recovery': recovery, 'independent_diagnostic_recovery': diagnostic,
        'rank_status': RANK_STATUS, 'rank_hits_or_calibration_function_called': False,
        'after_rank_measurements_available': False, 'reference_bank_created_or_read': False,
        'statistical_final_candidate_claims': False, 'scientific_admission': False,
        'scientific_bank_admission': False,
        'qualified_SETI_detection': False, 'telescope_FAP_interpretation_allowed': False,
        'old_scientific_main_or_admission_called': False, 'old_bank_reopened': False,
        'projection_bytes_before_report': budget.used, 'projection_and_report_cap_bytes': projection_cap}
    write_json(budget, report_path, report)
    print(json.dumps({'status': report['status'], 'identity': identity,
          'actual_ON_hit_count': len(hits), 'rank_status': RANK_STATUS,
          'projection_and_report_bytes': budget.used, 'scientific_admission': False}), flush=True)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('payload', 'producer-receipt', 'qa-report', 'qa-receipt', 'scope', 'projection-root', 'report'):
        ap.add_argument('--' + name, type=Path, required=True)
    ap.add_argument('--payload-cap', type=int, required=True)
    ap.add_argument('--projection-cap', type=int, required=True)
    args = ap.parse_args()
    run_check(args.payload, args.producer_receipt, args.qa_report, args.qa_receipt,
              args.scope, args.projection_root, args.report,
              payload_cap=args.payload_cap, projection_cap=args.projection_cap)


if __name__ == '__main__': main()
