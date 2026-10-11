"""Prepare the new1536-map scope from original source text metadata only."""
from __future__ import annotations
import argparse
import importlib.util
from pathlib import Path
import sys

BASE = 'analysis/off_adjacent_20261011'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--restoration-receipt', action='append', default=[])
    args = parser.parse_args()
    root = args.root.resolve()
    path = root / BASE / 'driver.py'
    spec = importlib.util.spec_from_file_location('off_adjacent_scope_driver', path)
    driver = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = driver
    spec.loader.exec_module(driver)
    names = [*driver.PINS, driver.ACQ_ADJACENT, driver.FEASIBILITY,
             BASE + '/driver.py', BASE + '/prepare_scope.py', *args.restoration_receipt]
    prior = []
    for job in driver.JOBS:
        name = 'analysis/s2017_control_targets_20261011_v2/results/' + job + '/EXECUTION_RECEIPT.json'
        names.append(name)
        value = driver.read_json(root / name)
        driver.require(value['status'] == 'COMPLETE_251_NEW_ORIGINAL_OFF_PRIMARY_TARGET_MAPS_EXPLORATORY_ONLY',
                       'Previous native171 target incomplete')
        prior.append({'path': name, 'maps': value['counts']['maps'],
                      'process_CPU_seconds': value['process_CPU_seconds'], 'wall_seconds': value['wall_seconds'],
                      'peak_RSS_bytes': value['peak_RSS_bytes']})
    pins = [driver.byte_pin(root, driver.confined(root, name)) for name in dict.fromkeys(names)]
    driver.require(all(Path(p['path']).suffix in ('.py', '.json', '.md', '.txt') for p in pins), 'Text-only preparation')
    by_path = {p['path']: p['sha256'] for p in pins}
    driver.require(all(by_path[path] == sha for path, sha in driver.PINS.items()), 'Original input pins differ')
    scale = max(r['process_CPU_seconds'] for r in prior) * 512 / 251
    scope = {**driver.method_contract(), 'text_code_pins': pins,
             'source_compacts': driver.source_records(root),
             'resource_basis': {'prior_completed251_map_receipts': prior,
                                '512_map_CPU_linear_projection_s': scale,
                                'reason_for_fresh1800s_CPU_cap': 'roughly985s projected maps plus triplet source verification and conservative overhead',
                                'estimated_job_memory_bytes': 700 * 1024**2,
                                'conservative_job_output_bytes': 512 * (181000 + 4000) + 2051 * 34000 + 10 * 1024**2,
                                'parallel_jobs': 2, 'aggregate_memory_cap_bytes': 4 * 1024**3},
             'raw503_reconstruction': {'width1_center': 251, 'width1_median_half_open': [1, 502],
                                      'width3_centers': [250, 251, 252],
                                      'width3_medians_half_open': [[0, 501], [1, 502], [2, 503]],
                                      'equation': '((raw/row_power_median)-median501(raw/row_power_median)-row_winsorized_residual_location)/row_residual_MAD_scale'},
             'scope_preparation_source_values_opened': False,
             'interpretation_limitations': ['One historical observation scan per primary target.',
                                           'Correlated maxima over widths/drifts, no calibrated SNR or FAP.',
                                           'OriginalOFF labels preserved; no veto or independent blind confirmation.']}
    driver.contract(root, scope)
    output = root / BASE / 'scope.json'
    driver.save(output, scope)
    driver.save(root / BASE / 'PREPARATION_RECEIPT.json', {
        'schema': 'SETI_ORIGINAL_OFF_ADJACENT_PREPARATION_V1',
        'status': 'PASS_TEXT_ONLY_1536_NEW_MAP_SCOPE_NO_SCIENCE',
        'scope': driver.byte_pin(root, output), 'source_compacts': 9, 'source_rows': 144,
        'total_new_maps': 1536, 'source_values_opened': False, 'numerical_modules_imported': False,
        'new_telescope_HTTP_requests': 0})
    print(driver.byte_pin(root, output))


if __name__ == '__main__':
    main()
