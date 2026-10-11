"""Create-only scientific plot from the complete QA-admitted saved-JSON summary.

No detector imports, HDF5/NPZ reads, scientific recomputation or source HTTP.
Run only after root GO, both completed jobs, numeric QA and saved summary.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import resource
import signal
import time

BASE = 'analysis/s2017_injection_20261011'
SCOPE_SHA = '64e34e40377751a261381a589dc5603c851ca562a162b9255239aff785d93631'
QA_STATUS = 'PASS450_MAPS540_DIAGNOSTICS_RAW_ARITHMETIC_AND_ROUNDED_SUPPORT_NO_DETECTOR_RERUN'
SUMMARY_STATUS = 'COMPLETE_ALL450_MAPS540_DIAGNOSTICS30_PREDECLARED_GROUPS_WITH_ACTUAL_QA_PASS'
QS, WIDTHS, AMPLITUDES = (64, 128, 192), (1, 9), (0, 1, 3, 6, 12)
DOMAIN_NAMES = ('local_window_winner', 'full_core_winner')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--qa-sha256', required=True)
    parser.add_argument('--summary-sha256', required=True)
    parser.add_argument('--summary-receipt-sha256', required=True)
    parser.add_argument('--root-go', action='store_true', required=True)
    args = parser.parse_args()
    require(args.root_go, 'Root GO after actual numeric QA and summary required')
    for sha in (args.qa_sha256, args.summary_sha256, args.summary_receipt_sha256):
        require(len(sha) == 64 and all(c in '0123456789abcdef' for c in sha), 'Exact SHA256 required')
    root = args.root.resolve()
    started, cpu0 = time.monotonic(), time.process_time()
    resource.setrlimit(resource.RLIMIT_CPU, (60, 61))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))

    def deadline(signum, frame):
        raise TimeoutError('Figure wall cap300')

    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(300)
    pins = {}

    def read_bytes(name, expected=None):
        path = root / name
        require(not Path(name).is_absolute() and path.resolve().is_relative_to(root)
                and path.suffix in ('.json', '.py') and path.is_file(), 'Confined code/JSON input required')
        require(path.stat().st_size <= 64 * 1024**2, 'Bounded input required')
        data = path.read_bytes()
        observed = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        require(expected is None or observed == expected, 'Input byte pin differs: ' + name)
        require(name not in pins or pins[name] == observed, 'Input changed: ' + name)
        pins[name] = observed
        return data

    def read_json(name, sha=None):
        require(Path(name).suffix == '.json', 'JSON input required')
        data = read_bytes(name)
        require(sha is None or pins[name]['sha256'] == sha, 'Exact input SHA differs: ' + name)
        return json.loads(data, object_pairs_hook=pairs)

    scope_name = BASE + '/scope.json'
    renderer_name = BASE + '/delivery/render_comparison_v2.py'
    read_bytes(renderer_name)
    scope = read_json(scope_name, SCOPE_SHA)
    require(scope['schema'] == 'SETI_S2017_RAW_POWER_INJECTION_SCOPE_V1', 'Exact science scope required')
    qa_name = BASE + '/results/review/QA_RECEIPT.json'
    qa = read_json(qa_name, args.qa_sha256)
    require(qa['schema'] == 'SETI_S2017_SAVED_INJECTION_INDEPENDENT_QA_V1'
            and qa['status'] == QA_STATUS and qa['scope_sha256'] == SCOPE_SHA
            and qa['counts']['maps'] == 450 and qa['counts']['diagnostics'] == 540
            and qa['detector_import_or_search_rerun'] is False, 'Actual complete numeric QA required')
    summary_name = BASE + '/results/summary/SUMMARY.json'
    summary = read_json(summary_name, args.summary_sha256)
    receipt_name = BASE + '/results/summary/SUMMARY_RECEIPT.json'
    receipt = read_json(receipt_name, args.summary_receipt_sha256)
    require(summary['schema'] == 'SETI_S2017_RAW_POWER_INJECTION_ALL_GROUP_SAVED_JSON_SUMMARY_V1'
            and summary['status'] == SUMMARY_STATUS
            and summary['actual_QA_receipt_sha256'] == args.qa_sha256
            and receipt['schema'] == 'SETI_S2017_INJECTION_SAVED_JSON_SUMMARY_RECEIPT_V1'
            and receipt['status'] == 'COMPLETE_CREATE_ONLY_ALL_GROUP_SUMMARY'
            and receipt['output_pin'] == pins[summary_name]
            and receipt['input_byte_pins'] == summary['input_byte_pins'], 'Actual saved summary admission differs')
    require(summary['counts'] == {'distinct_baseline_maps': 18, 'modified_maps': 432,
            'distinct_total_maps': 450, 'matched_zero_geometry_queries': 108,
            'all_logical_diagnostics': 540, 'groups': 30, 'logical_records_per_group': 18,
            'role_records_per_group': 9, 'scan_records_per_group': 3}, 'Complete declared grid required')
    require(summary['detector_or_score_rerun'] is False
            and summary['source_HDF5_NPZ_BIN_opened'] is False
            and summary['new_fit_veto_or_track_selection'] is False, 'Saved-only summary required')
    for name, pin in summary['input_byte_pins'].items():
        require(Path(name).suffix == '.json', 'Summary may pin only JSON for this renderer')
        read_bytes(name, pin)
        if name != qa_name:
            require(qa['input_byte_pins'].get(name) == pin, 'Summary input is not numerically QA-authenticated')
    code_name = BASE + '/summarize.py'
    read_bytes(code_name)
    require(pins[code_name]['sha256'] == receipt['summary_script_sha256'], 'Summary producer code pin differs')
    rows, groups = [], {}
    for group in summary['all_predeclared_groups']:
        key = (group['core_q'], group['injected_width_channels'], group['amplitude_per_cell_baseline_MAD_units'])
        require(key not in groups and key in {(q, w, a) for q in QS for w in WIDTHS for a in AMPLITUDES},
                'Group duplicate or unexpected identity')
        require(group['logical_records'] == group['flag_denominator'] == 18, 'Every q/width/A group requires18 cases')
        require(group['record_kind'] == ('shared_zero_geometry_queries' if key[2] == 0 else 'modified_power_maps'),
                'Shared-zero label differs')
        groups[key] = group
        row = {'core_q': key[0], 'injected_width_channels': key[1], 'amplitude': key[2],
               'denominator': 18, 'record_kind': group['record_kind']}
        for domain in DOMAIN_NAMES:
            count = group['flag_counts'][domain]['support_overlap_and_operational10']
            require(type(count) is int and 0 <= count <= 18, 'Invalid support count')
            row[domain + '_support_and10_count'] = count
        rows.append(row)
    require(len(groups) == 30, 'All30 groups required; no selected-only display')
    out = root / BASE / 'delivery'
    out.mkdir(parents=True, exist_ok=True)
    output_names = ('comparison_v2.png', 'COMPARISON_DATA_V2.json', 'COMPARISON_RENDER_RECEIPT_V2.json')
    require(all(not (out / name).exists() for name in output_names), 'Create-only figure outputs already exist')

    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    os.environ['OMP_NUM_THREADS'] = '1'
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                         'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(2, 2, figsize=(11.3, 8.7), sharex=True, sharey=True)
    styles = {64: ('#177e89', 'o', '-'), 192: ('#4053a4', 's', '--'), 128: ('#c46b18', '^', '-.')}
    for col, width in enumerate(WIDTHS):
        for row_index, domain in enumerate(DOMAIN_NAMES):
            ax = axes[row_index, col]
            for q in (64, 192, 128):
                counts = [groups[q, width, amp]['flag_counts'][domain]['support_overlap_and_operational10']
                          for amp in AMPLITUDES]
                color, marker, line = styles[q]
                ax.plot(range(1, 5), counts[1:], color=color, marker=marker, linestyle=line,
                        linewidth=2, markersize=6, label='q%d%s' % (q, ' · kendt konkurrent' if q == 128 else ''))
                ax.plot([0], [counts[0]], color=color, marker=marker, markerfacecolor='white',
                        markeredgewidth=1.6, markersize=7, linestyle='None')
            ax.set_ylim(-0.6, 18.9)
            ax.set_xlim(-0.3, 4.3)
            ax.set_yticks((0, 3, 6, 9, 12, 15, 18))
            ax.set_xticks(range(5), [str(a) for a in AMPLITUDES])
            ax.grid(axis='y', color='#dce1e7', linewidth=0.8)
            ax.set_axisbelow(True)
            if row_index == 0:
                ax.set_title('Indsat bredde %d kanal%s%s' % (width, '' if width == 1 else 'er',
                    '' if width == 1 else ' · mismatch'), fontsize=13, pad=12)
            if col == 0:
                ax.set_ylabel(('Lokal ±5' if row_index == 0 else 'Hel kerne · rang 1') + '\nAntal cases af 18')
            if row_index == 1:
                ax.set_xlabel('A · faste baselineenheder pr. celle')
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 0.938), ncol=3, frameon=False)
    fig.suptitle('Geometrisk støtte ved den operationelle scoregrænse 10', y=0.982, fontsize=16, fontweight='bold')
    fig.text(0.5, 0.073, 'Positivt box-overlap i alle 16 rækker og gemt score ≥10. Åbne markører: delte A=0-geometrispørgsmål.',
             ha='center', fontsize=10)
    fig.text(0.5, 0.043, 'Faste, afhængige cases · ingen sandsynlighedsintervaller. Bredde 9 tilfører 9× råeffekt ved samme A.',
             ha='center', fontsize=10)
    fig.subplots_adjust(left=0.10, right=0.98, top=0.84, bottom=0.145, wspace=0.12, hspace=0.21)
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', dpi=180, facecolor='white',
                metadata={'Title': 'SETI conditional injection support comparison',
                          'Description': 'Complete30 frozen groups; local known-truth support and full-core rank1 competition only.'})
    plt.close(fig)
    png = buffer.getvalue()
    data = {'schema': 'SETI_INJECTION_COMPARISON_ALL30_GROUPS_V1', 'actual_QA_sha256': args.qa_sha256,
            'summary_sha256': args.summary_sha256, 'metric': 'positive_interval_overlap_all16 AND score_at_least_operational10',
            'width9_is_support_stress_not_exact_width_recovery': True,
            'full_core_metric_is_rank1_competition_not_search_completeness': True,
            'zero_geometry_queries_not_injection_credit_or_fresh_trials_per_amplitude': True,
            'all30_rows': rows}
    outputs = {'comparison_v2.png': png,
               'COMPARISON_DATA_V2.json': (json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf8')}
    for name, payload in outputs.items():
        with (out / name).open('xb') as stream:
            stream.write(payload)
    for name, pin in list(pins.items()):
        read_bytes(name, pin)
    require(time.monotonic() - started <= 300 and time.process_time() - cpu0 <= 60, 'Figure resource cap exceeded')
    output_pins = {name: {'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}
                   for name, payload in outputs.items()}
    receipt_data = {'schema': 'SETI_INJECTION_SAVED_SUMMARY_STATIC_FIGURE_RECEIPT_V1',
                    'status': 'COMPLETE_ALL30_PREDECLARED_GROUPS_STATIC_PNG',
                    'renderer_sha256': pins[renderer_name]['sha256'],
                    'presentation_revision': 'V2_header_legend_clearance_only_same_summary_and_metric',
                    'preserved_V1_renderer_sha256': '80483b804e58f5880bb7e1f797ee1381990e64bdfb18fd330e72949578aac360',
                    'input_byte_pins': pins, 'output_pins': output_pins,
                    'process_CPU_seconds': time.process_time() - cpu0,
                    'wall_seconds': time.monotonic() - started,
                    'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                    'matplotlib_version': matplotlib.__version__, 'H5_NPZ_BIN_opened': False,
                    'detector_or_score_rerun': False, 'new_HTTP_requests': 0, 'Bernoulli_error_bars': False,
                    'all30_groups_present': True, 'numeric_source_is_previously_QA_admitted_saved_summary': True}
    with (out / 'COMPARISON_RENDER_RECEIPT_V2.json').open('x', encoding='utf8') as stream:
        json.dump(receipt_data, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
    signal.alarm(0)
    print(json.dumps({'status': receipt_data['status'], 'output_pins': output_pins}))


if __name__ == '__main__':
    main()
