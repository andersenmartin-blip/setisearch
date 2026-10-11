"""Prepare the four-row burst pilot from source-only frozen text metadata."""
from __future__ import annotations
import argparse
import importlib.util
from pathlib import Path
import sys

BASE = 'analysis/burst4_20261011'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('.'))
    p.add_argument('--extra-text-pin', action='append', default=[],
                   help='Optional final QA/context/packager/document path; no source arrays')
    args = p.parse_args()
    root = args.root.resolve()
    path = root / BASE / 'driver.py'
    spec = importlib.util.spec_from_file_location('burst4_scope_driver', path)
    driver = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = driver
    spec.loader.exec_module(driver)
    names = [*driver.PINS, driver.ACQ_ADJACENT, driver.RESTORED,
             BASE + '/driver.py', BASE + '/prepare_scope.py', driver.PREVIOUS + '/scope.json', *args.extra_text_pin]
    previous_receipts = []
    for job in driver.JOBS:
        name = driver.PREVIOUS + '/results/' + job + '/EXECUTION_RECEIPT.json'
        names.append(name)
        rec = driver.read_json(root / name)
        driver.require(rec['status'] == 'COMPLETE_512_NEW_ORIGINAL_OFF_MAPS_EXPLORATORY_ONLY', 'Previous search incomplete')
        previous_receipts.append({'path': name, 'maps': rec['counts']['maps'],
                                  'process_CPU_seconds': rec['process_CPU_seconds'], 'wall_seconds': rec['wall_seconds']})
    pins = [driver.byte_pin(root, driver.confined(root, name)) for name in dict.fromkeys(names)]
    driver.require(all(Path(pin['path']).suffix in ('.py', '.json', '.md', '.txt') for pin in pins), 'Preparation is text-only')
    scope = {**driver.method_contract(), 'text_code_pins': pins,
             'source_compacts': driver.source_records(root),
             'previous_completed_receipts': previous_receipts,
             'output_directory_template': BASE + '/results/<primary_id>',
             'expected_output_files_per_job_including_receipt': 584,
             'conservative_job_output_bytes': 96 * (190 * 1024 + 4000) + 387 * 11000 + 4 * 1024**2,
             'resource_basis': '96 cores versus previous512; seven windows total28 scored rows per hypothesis versus16 previously, with fewer159drifts versus785 and preprocessing once/core;600CPU/900wall2GiB conservative fresh cap',
             'source_values_opened_in_preparation': False,
             'root_GO_status_required': 'GO_288_NEW_BURST4_COMBINED_MAPS',
             'interpretation_limitations': ['Exposed historical observations; no blind validation or new observing exposure.',
                                          'Four-row window maxima over correlated hypotheses are not calibrated SNR/FAP.',
                                          'Uniform q selection excludes known q128 lines by geometry; no numerical mask or veto.',
                                          'Three OFF primaries are distinct stars with one scan each; other pointings are descriptive context.']}
    driver.contract(root, scope)
    output = root / BASE / 'scope.json'
    driver.save(output, scope)
    driver.save(root / BASE / 'PREPARATION_RECEIPT.json', {
        'schema': 'SETI_BURST4_SCOPE_PREPARATION_V1', 'status': 'PASS_TEXT_ONLY_288_NEW_BURST4_MAP_SCOPE',
        'scope': driver.byte_pin(root, output), 'source_compacts': 9, 'decoded_rows': 144,
        'maps': 288, 'carrier_maximum_records': 1179648, 'valid_hypothesis_records': 2625896448,
        'numerical_modules_imported': False, 'source_values_opened': False, 'new_telescope_HTTP_requests': 0})
    print(driver.byte_pin(root, output))


if __name__ == '__main__':
    main()
