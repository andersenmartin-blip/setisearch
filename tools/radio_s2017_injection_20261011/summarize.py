"""Create-only saved-JSON summary; run only after root GO and actual QA PASS.

No HDF5, NPZ, detector, spectrum, fit, candidate selection or rescoring.
All540 logical records and all30 predeclared groups remain represented.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import resource
import signal
import time

BASE = 'analysis/s2017_injection_20261011'
SCOPE_SHA = '64e34e40377751a261381a589dc5603c851ca562a162b9255239aff785d93631'
DRIVER_SHA = '4942208fef8bdc2eae702f8db44901cb54422f6a83168bd1b3a4ab05fcc191bc'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
QS, WIDTHS, AMPLITUDES, DRIFT_INDICES = (64, 128, 192), (1, 9), (0, 1, 3, 6, 12), (245, 392, 539)
JOBS = {'offcenter': (64, 192), 'known_center_competitor': (128,)}

def require(condition, message):
    if not condition:
        raise ValueError(message)

def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'Duplicate JSON field')
        result[key] = value
    return result

def byte_pin(path):
    data = path.read_bytes()
    return data, {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def save(path, value):
    data = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf8')
    with path.open('xb') as stream:
        stream.write(data)

def stats(values):
    require(values and all(isinstance(v, (float, int)) and math.isfinite(v) for v in values), 'Finite saved values required')
    return {'count': len(values), 'minimum': min(values), 'maximum': max(values),
            'mean': math.fsum(values) / len(values)}

def group(records):
    result = {'logical_records': len(records), 'flag_counts': {}, 'saved_score_statistics': {}}
    for domain in ('local_window_winner', 'nearest_reference_carrier_winner', 'full_core_winner'):
        tuples = [r[domain] for r in records]
        flags = ('center_geometry_within_one_channel_all16', 'positive_interval_overlap_all16',
                 'exact_injected_width_match', 'score_at_least_operational10')
        for name in flags:
            require(all(type(t[name]) is bool for t in tuples), 'Boolean saved flags required')
        result['flag_counts'][domain] = {name: sum(t[name] for t in tuples) for name in flags}
        result['flag_counts'][domain]['center_geometry_and_operational10'] = sum(
            t['center_geometry_within_one_channel_all16'] and t['score_at_least_operational10'] for t in tuples)
        result['flag_counts'][domain]['support_overlap_and_operational10'] = sum(
            t['positive_interval_overlap_all16'] and t['score_at_least_operational10'] for t in tuples)
        result['saved_score_statistics'][domain] = {
            'modified_maximum_score': stats([t['score'] for t in tuples]),
            'same_tuple_matched_zero_score': stats([t['matched_zero_score_same_winning_tuple'] for t in tuples]),
            'same_tuple_score_delta_from_zero': stats([t['score_delta_same_tuple_from_zero'] for t in tuples])}
    for name in ('local_known_truth_nominal_width1_matched_tuple_threshold_crossing_at10',
                 'full_core_rank1_nominal_width1_matched_tuple_threshold_crossing_at10',
                 'zero_already_center_compatible_at_operational10',
                 'zero_full_core_already_center_compatible_at_operational10'):
        require(all(type(r[name]) is bool for r in records), 'Boolean saved labels required')
        result['flag_counts'][name] = sum(r[name] for r in records)
    result['saved_truth_score_statistics'] = {name: stats([r[name] for r in records])
        for name in ('baseline_truth_score', 'modified_truth_score', 'truth_score_delta_from_zero')}
    result['flag_denominator'] = len(records)
    result['interpretation'] = 'Numerators/denominators are conditional deterministic case counts, not independent trials or calibrated detection probability.'
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--qa-receipt', required=True)
    parser.add_argument('--qa-sha256', required=True)
    parser.add_argument('--root-go', action='store_true', required=True)
    args = parser.parse_args()
    require(args.root_go, 'Root GO required before actual saved science JSON reads')
    root = args.root.resolve()
    started, cpu0 = time.monotonic(), time.process_time()
    resource.setrlimit(resource.RLIMIT_CPU, (60, 61))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
    def deadline(signum, frame):
        raise TimeoutError('Summary wall cap300')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(300)
    pins = {}
    def read(name):
        path = root / name
        require(not Path(name).is_absolute() and path.resolve().is_relative_to(root)
                and path.suffix == '.json', 'Confined JSON input required')
        data, observed = byte_pin(path)
        require(name not in pins or pins[name] == observed, 'Input changed')
        pins[name] = observed
        return json.loads(data, object_pairs_hook=pairs)
    scope_name = BASE + '/scope.json'
    scope = read(scope_name)
    require(pins[scope_name]['sha256'] == SCOPE_SHA, 'Exact frozen method scope required')
    qa = read(args.qa_receipt)
    require(pins[args.qa_receipt]['sha256'] == args.qa_sha256
        and qa['schema'] == 'SETI_S2017_SAVED_INJECTION_INDEPENDENT_QA_V1'
        and qa['status'] == 'PASS450_MAPS540_DIAGNOSTICS_RAW_ARITHMETIC_AND_ROUNDED_SUPPORT_NO_DETECTOR_RERUN',
        'Actual byte-pinned exact QA PASS required')
    require(qa['counts']['maps'] == 450 and qa['counts']['diagnostics'] == 540
        and qa['counts']['baseline_maps'] == 18 and qa['counts']['modified_maps'] == 432
        and qa['counts']['zero_geometry_queries'] == 108, 'Actual complete450/540 QA required')
    require(qa['scope_sha256'] == SCOPE_SHA and qa['input_byte_pins'][scope_name] == pins[scope_name]
        and qa['input_byte_pins'][BASE + '/driver.py']['sha256'] == DRIVER_SHA, 'QA frozen code/scope linkage differs')
    records, receipts, unique_maps, zero_maps = [], [], {}, {}
    for job, qs in JOBS.items():
        prefix = BASE + '/results/' + job
        execution_name, diagnostic_name = prefix + '/EXECUTION_RECEIPT.json', prefix + '/DIAGNOSTICS.json'
        execution, diagnostics = read(execution_name), read(diagnostic_name)
        require(qa['input_byte_pins'][diagnostic_name] == pins[diagnostic_name]
            and qa['input_byte_pins'][execution_name] == pins[execution_name]
            and qa['job_receipt_sha256s'][job] == pins[execution_name]['sha256'],
            'Actual QA does not authenticate exact current completed JSON bytes')
        require(execution['status'] == 'COMPLETE_PROSPECTIVE_RAW_POWER_INJECTION_BENCHMARK_EXPLORATORY_ONLY'
            and execution['driver_sha256'] == DRIVER_SHA and execution['scope_sha256'] == SCOPE_SHA
            and execution['job'] == job and execution['public_freeze_commit'] == qa['public_freeze_commit'],
            'Actual completed frozen job/public freeze required')
        require(execution['counts']['maps'] == len(qs) * 150
            and execution['counts']['diagnostic_records'] == len(qs) * 180, 'Actual job counts differ')
        require(diagnostics['schema'] == 'SETI_RAW_POWER_INJECTION_DIAGNOSTICS_V1', 'Diagnostic schema differs')
        records.extend(diagnostics['records'])
        receipts.append({'job': job, 'path': execution_name, **pins[execution_name],
            'process_CPU_seconds': execution['process_CPU_seconds'], 'wall_seconds': execution['wall_seconds'],
            'peak_RSS_bytes': execution['peak_RSS_bytes']})
    require(len(records) == 540, 'All540 logical diagnostics required')
    identities, expected = set(), {(q, width, amp, di, scan) for q in QS for width in WIDTHS
        for amp in AMPLITUDES for di in DRIFT_INDICES for scan in SCANS}
    for r in records:
        identity = (r['core_q'], r['injected_width_channels'], r['amplitude_per_cell_baseline_MAD_units'],
                    r['injected_drift_index'], r['scan_id'])
        require(identity in expected and identity not in identities, 'Diagnostic grid duplicate or omission')
        identities.add(identity)
        key, value = r['map_id'], r['map_sha256']
        require(key not in unique_maps or unique_maps[key] == value, 'Map identity alias mismatch')
        unique_maps[key] = value
        key, value = r['matched_zero_map_id'], r['matched_zero_map_sha256']
        require(key not in zero_maps or zero_maps[key] == value, 'Shared zero identity differs')
        zero_maps[key] = value
        require(r['baseline_all_compatible_templates_below10_proven'] is False, 'Unsupported baseline absence claim')
        if r['injected_width_channels'] == 9 or r['amplitude_per_cell_baseline_MAD_units'] == 0:
            require(not r['local_known_truth_nominal_width1_matched_tuple_threshold_crossing_at10']
                and not r['full_core_rank1_nominal_width1_matched_tuple_threshold_crossing_at10'], 'Width9/zero nominal credit forbidden')
    require(identities == expected and len(unique_maps) == 450 and len(zero_maps) == 18, 'Exact complete map/grid identities required')
    modified = [r for r in records if r['amplitude_per_cell_baseline_MAD_units'] > 0]
    zeros = [r for r in records if r['amplitude_per_cell_baseline_MAD_units'] == 0]
    require(len(modified) == 432 and len(zeros) == 108, 'Modified/zero query counts differ')
    groups = []
    for q in QS:
        for width in WIDTHS:
            for amp in AMPLITUDES:
                members = [r for r in records if (r['core_q'], r['injected_width_channels'],
                           r['amplitude_per_cell_baseline_MAD_units']) == (q, width, amp)]
                require(len(members) == 18, 'Every predeclared group requires6scans x3drifts')
                item = {'core_q': q, 'context': 'known_center_competitor' if q == 128 else 'fixed_offcenter',
                    'injected_width_channels': width, 'amplitude_per_cell_baseline_MAD_units': amp,
                    'record_kind': 'shared_zero_geometry_queries' if amp == 0 else 'modified_power_maps',
                    'width9_is_template_mismatch_stress': width == 9, **group(members)}
                item['role_subsets'] = {role: group([r for r in members if r['role'] == role]) for role in ('on', 'off')}
                item['scan_subsets'] = {scan: group([r for r in members if r['scan_id'] == scan]) for scan in SCANS}
                groups.append(item)
    require(len(groups) == 30, 'All30 groups required')
    summary = {'schema': 'SETI_S2017_RAW_POWER_INJECTION_ALL_GROUP_SAVED_JSON_SUMMARY_V1',
        'status': 'COMPLETE_ALL450_MAPS540_DIAGNOSTICS30_PREDECLARED_GROUPS_WITH_ACTUAL_QA_PASS',
        'input_byte_pins': pins, 'actual_QA_receipt_sha256': args.qa_sha256,
        'counts': {'distinct_baseline_maps': 18, 'modified_maps': 432, 'distinct_total_maps': 450,
            'matched_zero_geometry_queries': 108, 'all_logical_diagnostics': 540, 'groups': 30,
            'logical_records_per_group': 18, 'role_records_per_group': 9, 'scan_records_per_group': 3},
        'actual_job_resources': receipts, 'all_predeclared_groups': groups,
        'all540_original_diagnostics_preserved': records,
        'map_and_shared_zero_byte_identities': {'all450_maps': unique_maps, 'shared18_zero_maps': zero_maps},
        'qualification': {'new_sky_coverage': False, 'independent_visit': False, 'qualified_SETI_detection': False,
            'calibrated_SNR_FAP_global_null_or_population_completeness': False,
            'cadence_coherent_ON_only_source_or_OFF_veto_test': False},
        'limits': scope['limits'] + ['Full-core flag describes rank1 competition, not absence of retained non-rank1 carrier responses.',
            'Matched-tuple threshold crossing excludes that particular baseline tuple at10; it does not prove every compatible baseline hypothesis was below10.',
            'Groups include every amplitude/core/width and all signed roles without positive-only filtering.'],
        'detector_or_score_rerun': False, 'source_HDF5_NPZ_BIN_opened': False, 'new_fit_veto_or_track_selection': False,
        'new_HTTP_requests': 0, 'original_A_B_status': 'FAIL_CLOSED_UNCHANGED'}
    for name, observed in pins.items():
        require(byte_pin(root / name)[1] == observed, 'Actual JSON input changed')
    out = root / BASE / 'results/summary'
    out.mkdir(parents=True, exist_ok=False)
    save(out / 'SUMMARY.json', summary)
    _, output_pin = byte_pin(out / 'SUMMARY.json')
    _, code_pin = byte_pin(Path(__file__).resolve())
    save(out / 'SUMMARY_RECEIPT.json', {'schema': 'SETI_S2017_INJECTION_SAVED_JSON_SUMMARY_RECEIPT_V1',
        'status': 'COMPLETE_CREATE_ONLY_ALL_GROUP_SUMMARY', 'summary_script_sha256': code_pin['sha256'],
        'input_byte_pins': pins, 'output_pin': output_pin, 'counts': summary['counts'],
        'process_CPU_seconds': time.process_time() - cpu0, 'wall_seconds': time.monotonic() - started,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        'source_HDF5_NPZ_BIN_opened': False, 'detector_or_score_rerun': False, 'new_HTTP_requests': 0})
    signal.alarm(0)
    print(json.dumps({'status': 'COMPLETE_CREATE_ONLY_ALL_GROUP_SUMMARY', **output_pin}))

if __name__ == '__main__':
    main()
