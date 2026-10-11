"""Create prospective fixed-tuple temporal-order scope from authenticated metadata.

Hashes prior capsules as opaque bytes; no numerical modules or source arrays.
"""
from __future__ import annotations
import argparse
import importlib.util
from pathlib import Path
import sys

BASE = 'analysis/burst_order_20261011'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('.'))
    p.add_argument('--extra-text-pin', action='append', default=[])
    args = p.parse_args()
    root = args.root.resolve()
    spec = importlib.util.spec_from_file_location('temporal_order_scope_driver', root / BASE / 'driver.py')
    driver = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = driver
    spec.loader.exec_module(driver)
    prior_scope = driver.read(root / driver.PRIOR / 'scope.json')
    prior_qa = driver.read(root / driver.PRIOR_QA)
    driver.require(prior_qa['status'] == 'PASS288_BURST4_MAPS1161_RAW4X503_QUERIES144_SOURCE_ROWS_NO_GRID_RERUN'
                   and prior_qa['primary_scope_sha256'] == driver.digest(root / driver.PRIOR / 'scope.json')
                   and prior_qa['qa_sha256'] == driver.digest(root / 'analysis/burst4_20261011_qa/qa_saved.py'),
                   'Authenticated prior saved-output QA provenance differs')
    text_names = [BASE + '/' + name for name in ('driver.py', 'prepare_scope.py', 'qa_saved.py', 'restore_inputs.py', 'INPUT_RESTORATION_RECEIPT.json')]
    text_names += [driver.PRIOR + '/scope.json', driver.PRIOR + '/driver.py', driver.PRIOR + '/ROOT_GO.json',
                   driver.PRIOR + '/PUBLIC_FREEZE.json', driver.PRIOR_QA, 'analysis/burst4_20261011_qa/qa_saved.py',
                   'analysis/new_visit_search/dependencies/detector.py', 'analysis/new_visit_search/dependencies/standard_reader.py',
                   'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json', 'analysis/s2017_next_native/source_manifest_v2.json',
                   'analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json',
                   'analysis/s2017_next_native/results/acquire/ACQUISITION_RESULT.json',
                   'analysis/RESTORATION_RECEIPT_20261011.json', *args.extra_text_pin]
    jobs, prior_pins = {}, {}
    for job, (scan, target) in driver.JOBS.items():
        folder = driver.PRIOR + '/results/' + job
        receipt_name = folder + '/EXECUTION_RECEIPT.json'
        receipt = driver.read(root / receipt_name)
        driver.require(prior_qa['primary_receipt_sha256s'].get(job) == driver.digest(root / receipt_name),
                       'Prior independent QA did not bind this exact primary receipt')
        driver.require(receipt['status'] == 'COMPLETE_96_NEW_BURST4_COMBINED_MAPS_EXPLORATORY_ONLY'
                       and receipt['scope_sha256'] == driver.digest(root / driver.PRIOR / 'scope.json')
                       and receipt['driver_sha256'] == driver.digest(root / driver.PRIOR / 'driver.py'), 'Prior primary provenance differs')
        receipt_outputs = {r['path']: r for r in receipt['output_byte_pins']}
        for name in ('SCORE_AUDITS.json', 'TOP3.json'):
            path = root / folder / name
            actual = driver.pin(root, path)
            driver.require(receipt_outputs.get(actual['path']) == actual, 'Prior selected-query metadata not receipt-bound')
            prior_pins[actual['path']] = actual
        audits = driver.read(root / folder / 'SCORE_AUDITS.json')
        tops = driver.read(root / folder / 'TOP3.json')
        driver.require(audits['scan_id'] == scan and audits['primary_id'] == job and len(audits['records']) == 387,
                       'Exact saved387query list required')
        for query in audits['records']:
            for declaration in (query['normalization'], query['capsule']):
                actual = driver.pin(root, driver.confined(root, declaration['path']))
                driver.require(receipt_outputs.get(actual['path']) == actual == declaration, 'Prior norm/capsule anchor differs')
                prior_pins[actual['path']] = actual
        text_names.append(receipt_name)
        groups = {}
        for query in audits['records']:
            key = tuple(query['selected_tuple'][field] for field in driver.method()['scientific_tuple_key_fields'])
            groups.setdefault(key, []).append(query['query_id'])
        jobs[job] = {'primary_id': job, 'scan_id': scan, 'primary_target': target,
                     'primary_receipt': driver.pin(root, root / receipt_name),
                     'prior_runtime_versions': receipt['runtime_versions'], 'queries': audits['records'], 'TOP3': tops['records'],
                     'scientific_tuple_groups': [{'scientific_tuple_key': list(key), 'query_ids': values} for key, values in groups.items()]}
    text_pins = [driver.pin(root, driver.confined(root, name)) for name in dict.fromkeys(text_names)]
    driver.require(all(Path(r['path']).suffix in ('.py', '.json', '.md', '.txt') for r in text_pins), 'Only text/code extra pins allowed')
    scope = {**driver.method(), 'text_code_pins': text_pins, 'prior_data_pins': list(prior_pins.values()),
             'source_compacts': prior_scope['source_compacts'], 'jobs': jobs,
             'output_directory_template': BASE + '/results/<primary_id>',
             'expected_output_files_per_job_including_receipt': 389,
             'source_values_opened_in_preparation': False, 'numerical_modules_imported_in_preparation': False,
             'selection_limitations': ['All1161 tuples are stored winners from an already exposed search:384 fixed audit carriers plus3 global TOP3 pertarget.',
                                       'Order scores reuse physical source data, saved normalization and selection; they are not independent evidence or calibrated permutation p-values.',
                                       'Repeated integer centers reduce distinct assignments and stationary centers provide no temporal-order information.',
                                       'Width3 boxes may overlap and assignments remain correlated even when integer center vectors differ.',
                                       'No new masks, grid search, drift fit, MAD/location estimate, protected2016 data, telescope requests or paid services.'],
             'resource_basis': 'Only1161 fixed4x4 matrices and24 assignments perquery; previous full-grid search is not repeated.'}
    driver.contract(root, scope)
    path = root / BASE / 'scope.json'
    driver.save(path, scope)
    driver.save(root / BASE / 'PREPARATION_RECEIPT.json', {'schema': 'SETI_BURST4_TEMPORAL_ORDER_PREPARATION_V1',
        'status': 'PASS_METADATA_ONLY_1161_FIXED_TEMPORAL_ORDER_SCOPE', 'scope': driver.pin(root, path),
        'queries': 1161, 'source_compacts': 9, 'source_rows': 144, 'normalization_files': 288,
        'numerical_modules_imported': False, 'source_arrays_opened': False, 'new_telescope_HTTP_requests': 0})
    print(driver.pin(root, path))


if __name__ == '__main__':
    main()
