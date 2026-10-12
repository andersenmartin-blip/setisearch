"""Create a prospective eight-family Gamma scope from code/reference metadata.

No NumPy/SciPy import, draws, observations or stored numerical arrays.
"""
from __future__ import annotations
import argparse
import importlib.util
from pathlib import Path
import sys

BASE = 'analysis/burst_null_20261012'
OLD_ORDER = 'analysis/burst_order_20261011'
OLD_BURST = 'analysis/burst4_20261011'
OLD_JOBS = ('primary20170428_HIP97319', 'primary20170428_HIP97461', 'primary20170428_HIP97663')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--extra-text-pin', action='append', default=[])
    args = parser.parse_args()
    root = args.root.resolve()
    spec = importlib.util.spec_from_file_location('gamma_null_scope_driver', root / BASE / 'driver.py')
    driver = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = driver
    spec.loader.exec_module(driver)
    runtime = driver.versions()
    driver.require(runtime['numpy'] == '2.3.5' and runtime['scipy'] == '1.17.0', 'Exact declared model runtime required')
    references = [OLD_ORDER + '/' + name for name in
                  ('scope.json', 'ROOT_GO.json', 'PUBLIC_FREEZE.json', 'QA_RECEIPT.json')]
    references += [OLD_ORDER + '/delivery/' + name for name in
                   ('SUMMARY.json', 'TOP9.csv', 'SETI_BURST_ORDER_FINAL_2026-10-11.md', 'REPORT_RECEIPT.json')]
    references += [OLD_BURST + '/scope.json', OLD_BURST + '/ROOT_GO.json', OLD_BURST + '/PUBLIC_FREEZE.json',
                   'analysis/burst4_20261011_qa/results/QA_RECEIPT.json']
    previous_resources = []
    order_qa = driver.read_json(root / OLD_ORDER / 'QA_RECEIPT.json')
    driver.require(order_qa['status'] == 'PASS_1161_FIXED_TEMPORAL_ORDER_QUERIES18576_ROW_CENTER_BOXES27864_PERMUTATION_SCORES9_TOP3',
                   'Completed independent real-order reference QA required')
    for job in OLD_JOBS:
        order_receipt = OLD_ORDER + '/results/' + job + '/EXECUTION_RECEIPT.json'
        references += [order_receipt, OLD_ORDER + '/results/' + job + '/QUERY_DIAGNOSTICS.json']
        driver.require(order_qa['job_receipt_sha256s'][job] == driver.digest(root / order_receipt),
                       'Previous real-order receipt differs from exact QA reference')
        burst_receipt = OLD_BURST + '/results/' + job + '/EXECUTION_RECEIPT.json'
        references += [burst_receipt, OLD_BURST + '/results/' + job + '/TOP3.json']
        receipt = driver.read_json(root / burst_receipt)
        driver.require(receipt['status'] == 'COMPLETE_96_NEW_BURST4_COMBINED_MAPS_EXPLORATORY_ONLY'
                       and receipt['counts']['maps'] == 96, 'Completed96map legacy family required')
        previous_resources.append({'path': burst_receipt, 'CPU_seconds': receipt['process_CPU_seconds'],
                                   'wall_seconds': receipt['wall_seconds'], 'peak_RSS_bytes': receipt['peak_RSS_bytes']})
    text_names = [BASE + '/' + name for name in
                  ('driver.py', 'prepare_scope.py', 'qa_saved.py', 'PROTOCOL.md', 'INPUT_RESTORATION_RECEIPT.json')]
    text_names += [driver.DETECTOR, driver.LEGACY, OLD_ORDER + '/driver.py', OLD_ORDER + '/qa_saved.py',
                   OLD_ORDER + '/PRIOR_CONTINUATION_RESOURCE_LEDGER.json', *args.extra_text_pin]
    text_pins = [driver.byte_pin(root, driver.confined(root, name)) for name in dict.fromkeys(text_names)]
    reference_pins = [driver.byte_pin(root, driver.confined(root, name)) for name in dict.fromkeys(references)]
    driver.require(all(Path(record['path']).suffix in ('.py', '.json', '.md', '.txt', '.csv')
                       for record in text_pins + reference_pins), 'Preparation may pin only text/code/reference files')
    scope = {**driver.method_contract(), 'text_code_pins': text_pins, 'prior_reference_pins': reference_pins,
             'runtime_versions': runtime, 'output_directory_template': BASE + '/results/<primary_id>',
             'expected_output_files_per_family_including_receipt': '589+winning_raw_crops; winning_raw_crops1..3',
             'previous_full_family_resource_receipts': previous_resources,
             'resource_basis': 'Previous96-core burst families took138.955..142.982CPU s and about321MB RSS; fresh600CPU/900wall/2GiB permits Gamma draw and order QA overhead. Streaming no observations; keep96 model crops in RAM.',
             'model_values_generated_in_preparation': False, 'numerical_modules_imported_in_preparation': False,
             'observational_arrays_opened_in_preparation': False,
             'interpretation_limitations': ['A fixed illustrative IID Gamma engineering law, not an inferred instrument degrees-of-freedom model.',
                                          'Eight complete independent realizations; the24 pooledTOP3 winners remain correlated within families.',
                                          'RealreferenceTOP3 were already selected from exposed observations and remain a separate descriptive panel.',
                                          'Winner order controls occur after the same full drift/window/width search; they are not exchangeable permutation trials.',
                                          'Repeated centers and width3 overlap create additional correlations; U=1 gives no order information.',
                                          'No tail calibration, telescope skyFAP, discovery claim, new mask, veto or A/B repair.',
                                          'QA regenerates fixed bytes and winningcore terms, but does not independently recompute all7billion grid scores.',
                                          'Stored nonwinning audit MAD/location remain conditional on saved fullcore parameters.']}
    driver.contract(root, scope)
    path = root / BASE / 'scope.json'
    driver.save(path, scope)
    driver.save(root / BASE / 'PREPARATION_RECEIPT.json', {
        'schema': 'SETI_GAMMA_NULL_SCOPE_PREPARATION_V1', 'status': 'PASS_METADATA_ONLY_EIGHT_FULL_GAMMA_NULL_FAMILIES',
        'scope': driver.byte_pin(root, path), 'runtime_versions': runtime,
        'families': 8, 'maps': 768, 'carrier_maximum_records': 3145728, 'valid_hypothesis_records': 7002390528,
        'score_audit_queries': 3096, 'order_queries': 24, 'row_center_boxes': 384, 'permutation_scores': 576,
        'numerical_modules_imported': False, 'model_values_generated': False, 'observational_arrays_opened': False,
        'new_telescope_HTTP_requests': 0})
    print(driver.byte_pin(root, path))


if __name__ == '__main__':
    main()
