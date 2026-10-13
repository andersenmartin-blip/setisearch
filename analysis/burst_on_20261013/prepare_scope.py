"""Freeze the ON burst application from source-only text metadata.

This command neither imports numerical libraries nor opens HDF5 source payloads.
Existing output files are never replaced.
"""
from __future__ import annotations
import argparse
import importlib.util
from pathlib import Path
import sys

BASE = 'seti_burst_on'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('.'))
    p.add_argument('--extra-text-pin', action='append', default=[],
                   help='Final QA/context/review source path; no source arrays')
    args = p.parse_args()
    root = args.root.resolve()
    spec = importlib.util.spec_from_file_location('on_burst4_scope_driver', root / BASE / 'driver.py')
    driver = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = driver
    spec.loader.exec_module(driver)
    names = [*driver.PINS, driver.RESTORED,
             BASE + '/driver.py', BASE + '/prepare_scope.py', *args.extra_text_pin]
    pins = [driver.byte_pin(root, driver.confined(root, name)) for name in dict.fromkeys(names)]
    driver.require(all(Path(pin['path']).suffix in ('.py', '.json', '.md', '.txt') for pin in pins),
                   'Preparation is text-only')
    source_records = driver.source_records(root)
    driver.require(len(source_records) == 9 and sum(len(r['decoded_rows']) for r in source_records) == 144,
                   'Exact nine declared ON compacts/144 rows required')
    driver.require(all(driver.confined(root, r['path']).is_file()
                       and driver.confined(root, r['path']).stat().st_size == r['bytes'] for r in source_records),
                   'Explicit relocated source compacts missing or declared size differs')
    scope = {**driver.method_contract(), 'text_code_pins': pins,
             'source_compacts': source_records,
             'source_metadata_directory': 'burst_previous', 'raw_compact_directory': 'seti_raw',
             'prior_OFF_burst_scope_sha256': driver.PINS[driver.PREVIOUS + '/scope.json'],
             'prior_OFF_burst_driver_sha256': driver.PINS[driver.PREVIOUS + '/driver.py'],
             'output_directory_template': BASE + '/results/<primary_id>',
             'expected_output_files_per_job_including_receipt': 589,
             'conservative_job_output_bytes': 96 * (190 * 1024 + 4000) + 390 * 11000 + 4 * 1024**2,
             'resource_basis': 'Same96core seven-window frozen burst method as preceding completed OFF application;159drifts and preprocessing once/core;600CPU/900wall2GiB cap perONscan.',
             'source_values_opened_in_preparation': False,
             'raw_bytes_hashed_in_preparation': False,
             'root_GO_status_required': 'GO_288_NEW_ON_BURST4_COMBINED_MAPS',
             'public_freeze_status_required': 'PASS_PUBLIC_FREEZE_ON_BURST4_SCOPE_READBACK',
             'public_freeze_file_required': BASE + '/freeze.json',
             'interpretation_limitations': [
                 'Same exposed historical visit; three HIP98505 ON scan positions are not independent visits or blind validation.',
                 'Four-row maxima over correlated hypotheses are not calibrated SNR/FAP.',
                 'Unchanged core sampling q4+8k already keeps all allowed fourrow boxes far from DC. DC-aware shortlist is a geometry diagnostic, expected identical to raw shortlist.',
                 'DC-aware filtering checks only already winning chosen4row width boxes. No nonwinning hypotheses are recomputed or recovered.',
                 'DC-free geometry does not establish freedom from instrumental structure, RFI or chance maxima.',
                 'No protected2016 data, injection arrays, source acquisition, or prior numerical scope rerun.']}
    driver.contract(root, scope)
    output = root / BASE / 'SCOPE.json'
    driver.save(output, scope)
    driver.save(root / BASE / 'PREPARATION_RECEIPT.json', {
        'schema': 'SETI_ON_BURST4_SCOPE_PREPARATION_V1', 'status': 'PASS_TEXT_ONLY_288_NEW_ON_BURST4_MAP_SCOPE',
        'scope': driver.byte_pin(root, output), 'source_compacts': 9, 'decoded_rows': 144,
        'maps': 288, 'carrier_maximum_records': 1179648, 'valid_hypothesis_records': 2625896448,
        'score_audit_queries': 1170, 'raw_power_cells': 2354040,
        'numerical_modules_imported': False, 'source_values_opened': False, 'raw_bytes_hashed': False,
        'new_telescope_HTTP_requests': 0})
    print(driver.byte_pin(root, output))


if __name__ == '__main__':
    main()
