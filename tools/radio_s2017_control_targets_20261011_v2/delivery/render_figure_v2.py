"""Additive figure-only repair from the closed original saved-JSON text report.

The copied render function has exactly one AST change: Colorbar.set_ticks
uses the keyword-only labels parameter. Existing scientific derivation,
text outputs, original producer source/log/failure receipt stay unchanged.
Only the absent intended PNG and a new completion receipt may be created.
"""
from __future__ import annotations
import argparse
import ast
import copy
import fcntl
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import re
import resource
import signal
import time

for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
BASE = 'analysis/s2017_control_targets_20261011_v2'
DELIVERY = BASE + '/delivery'
SOURCE = DELIVERY + '/render_figure_v2.py'
ORIGINAL_SOURCE = DELIVERY + '/make_report.py'
ORIGINAL_SOURCE_SHA = '48e216b2aa60d1c999fa7c5065c32e5449c1ad6b13fa0360f9b573319acbe2e1'
PROVENANCE = DELIVERY + '/REPORT_RENDER_FAILURE_PROVENANCE.json'
PROVENANCE_PIN = {'bytes': 2839, 'sha256': '31eba3ef24c983e1c96d8dababa6c8013ea4499b7f2d5bfc9732b47387bcb3d0'}
REVIEW = BASE + '/review/FIGURE_REPAIR_SOURCE_REVIEW.json'
PRIMARY_QA = BASE + '/results/review/QA_RECEIPT.json'
CONTEXT_QA = BASE + '/results/context_review/QA_RECEIPT.json'
PRIMARY_QA_SHA = '67c11a8d3d09a29e4d8dbdc2b22d1183e8a8bebcecf87f5100d7e46297f7cd45'
CONTEXT_QA_SHA = '37b8cb78bcfb93a5c2ae4c6bbc8553ca78c74ae1ef8c295eab29353c36fccec6'
SUMMARY = DELIVERY + '/SUMMARY.json'
TEXT_NAMES = ('SUMMARY.json', 'TOP60.csv', 'CORE_MAX753.csv', 'CONTEXT54.csv', 'SETI_CONTROL_TARGETS_2026-10-11.md')
PNG_NAME = 'SETI_CONTROL_TARGETS_2026-10-11.png'
COMPLETION_NAME = 'REPORT_COMPLETION_RECEIPT.json'
OUTPUT_PATHS = [DELIVERY + '/' + PNG_NAME, DELIVERY + '/' + COMPLETION_NAME]
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
TARGETS = {'primary20170428_HIP97319': ('HIP97319', 'epoch1_off'),
           'primary20170428_HIP97461': ('HIP97461', 'epoch2_off'),
           'primary20170428_HIP97663': ('HIP97663', 'epoch3_off')}
KNOWN_CHANNEL, KNOWN_MHZ = 179830784, 2300.390625
CPU_CAP, WALL_CAP, RAM_CAP, OUTPUT_CAP, WORKSPACE_CAP = 180, 300, 2 * 1024**3, 32 * 1024**2, 8 * 1024**3


def require(test, message):
    if not test:
        raise ValueError(message)


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result


def confined(root, name):
    p = Path(name)
    require(not p.is_absolute() and '..' not in p.parts, 'Root-relative confined path required')
    path = root / p
    require(path.resolve().is_relative_to(root) and not path.is_symlink(), 'Unconfined or symlink path')
    return path


def byte_pin(root, name):
    path = confined(root, name)
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for b in iter(lambda: stream.read(1048576), b''):
            h.update(b)
    return {'bytes': path.stat().st_size, 'sha256': h.hexdigest()}


def authenticate(root, name, pins, expected=None):
    require(Path(name).suffix in ('.py', '.json', '.md', '.csv', '.log'), 'Text/source pin only; no H5/NPZ/BIN opens')
    observed = byte_pin(root, name)
    require(expected is None or observed == expected, 'Exact input byte pin differs: ' + name)
    require(name not in pins or pins[name] == observed, 'Input changed during admission')
    pins[name] = observed
    return observed


def load_json(root, name, pins, expected):
    require(Path(name).suffix == '.json', 'Saved JSON only')
    raw = confined(root, name).read_bytes()
    observed = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    require(observed == expected and (name not in pins or pins[name] == observed), 'Parsed JSON differs from exact admitted bytes: ' + name)
    pins[name] = observed
    return json.loads(raw, object_pairs_hook=pairs)


def save_bytes(path, data):
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()


def render_copy_proof(root):
    require(byte_pin(root, ORIGINAL_SOURCE)['sha256'] == ORIGINAL_SOURCE_SHA, 'Original frozen producer source differs')
    original = ast.parse(confined(root, ORIGINAL_SOURCE).read_text())
    current = ast.parse(confined(root, SOURCE).read_text())
    before = next(n for n in original.body if isinstance(n, ast.FunctionDef) and n.name == 'render')
    after = next(n for n in current.body if isinstance(n, ast.FunctionDef) and n.name == 'render')
    expected = copy.deepcopy(before)
    changes = 0
    for node in ast.walk(expected):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'set_ticks' and len(node.args) == 2:
            require(not node.keywords, 'Unexpected original set_ticks keywords')
            labels = node.args.pop()
            node.keywords.append(ast.keyword(arg='labels', value=labels))
            changes += 1
    require(changes == 1 and ast.dump(expected, include_attributes=False) == ast.dump(after, include_attributes=False),
            'Render AST differs beyond the single labels= correction')
    for name in ('SCANS', 'TARGETS'):
        def literal(tree):
            node = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
            return ast.literal_eval(node.value)
        require(literal(original) == literal(current), 'Copied plot constant differs: ' + name)
    return {'render_function_AST_only_change': 'one Colorbar.set_ticks second positional argument moved to labels keyword',
            'changed_calls': changes, 'plot_scan_order_and_primary_ID_constants_unchanged': True}


def workspace_allocated(root):
    seen, total = set(), 0
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in files:
            try:
                st = (Path(parent) / name).stat(follow_symlinks=False)
            except FileNotFoundError:
                continue
            key = st.st_dev, st.st_ino
            if key not in seen:
                seen.add(key)
                total += st.st_blocks * 512
    return total


def output_guard(root, reserve=0):
    paths = [DELIVERY + '/' + name for name in TEXT_NAMES + (PNG_NAME, COMPLETION_NAME)]
    total = sum(confined(root, path).stat().st_size for path in paths if confined(root, path).exists())
    require(total + reserve <= OUTPUT_CAP and workspace_allocated(root) + reserve <= WORKSPACE_CAP,
            'Report output32MiB/workspace8GiB bound')
    return total


def admit(root, args):
    pins = {}
    for sha in (args.source_sha256, args.review_sha256, args.summary_sha256, args.primary_qa_sha256,
                args.context_qa_sha256, args.root_go_sha256):
        require(re.fullmatch('[0-9a-f]{64}', sha or ''), 'Exact source/review/summary/QA/GO SHA required')
    own = authenticate(root, SOURCE, pins)
    require(own['sha256'] == args.source_sha256, 'Renderer source differs from CLI pin')
    review_pin = authenticate(root, REVIEW, pins)
    require(review_pin['sha256'] == args.review_sha256, 'Independent repair-source review CLI pin differs')
    review = load_json(root, REVIEW, pins, review_pin)
    require(review['status'].startswith('PASS_') and review['repair_source_sha256'] == args.source_sha256,
            'Independent repair-source review not PASS for these exact bytes')
    provenance = load_json(root, PROVENANCE, pins, PROVENANCE_PIN)
    require(provenance['schema'] == 'SETI_S2017_CONTROL_REPORT_EXPORT_FAILURE_PROVENANCE_V1'
            and provenance['status'] == 'ROOT_AUTHORIZES_ADDITIVE_FIGURE_ONLY_REPAIR_PRESERVE_TEXT_AND_FAILURE'
            and provenance['actual_original_producer_exit_code'] == 1
            and provenance['complete_existing_text_output_count'] == 5
            and provenance['PNG_created_before_failure'] is False
            and provenance['science_QA_or_derive_rerun_authorized'] is False
            and provenance['new_renderer_allowed_outputs'] == [PNG_NAME, COMPLETION_NAME], 'Root closed failure provenance differs')
    known = provenance['existing_file_pins']
    require(known[ORIGINAL_SOURCE]['sha256'] == ORIGINAL_SOURCE_SHA, 'Preserved producer source binding')
    for name, expected in known.items():
        authenticate(root, name, pins, expected)
    proof = render_copy_proof(root)
    go_pin = authenticate(root, args.root_go_path, pins)
    require(go_pin['sha256'] == args.root_go_sha256, 'Exact root figure-only GO CLI pin differs')
    go = load_json(root, args.root_go_path, pins, go_pin)
    require(go['schema'] == 'SETI_S2017_CONTROL_REPORT_FIGURE_REPAIR_ROOT_GO_V1'
            and go['status'] == 'ROOT_GO_SAVED_SUMMARY_FIGURE_REPAIR_ONCE'
            and go['repair_source_sha256'] == args.source_sha256 and go['source_review_sha256'] == args.review_sha256
            and go['failure_provenance_sha256'] == PROVENANCE_PIN['sha256']
            and go['summary_sha256'] == args.summary_sha256
            and go['actual_primary_QA_receipt_sha256'] == args.primary_qa_sha256
            and go['actual_context_QA_receipt_sha256'] == args.context_qa_sha256
            and go['allowed_output_paths'] == OUTPUT_PATHS and go['numerical_science_rerun_authorized'] is False,
            'Explicit exact figure-only root GO contract differs')
    require(args.summary_sha256 == known[SUMMARY]['sha256'], 'Summary CLI SHA differs from exact original text pin')
    summary = load_json(root, SUMMARY, pins, known[SUMMARY])
    require(summary['schema'] == 'SETI_S2017_CONTROL_TARGET_ALL_SAVED_JSON_REPORT_V1'
            and summary['status'] == 'COMPLETE_ALL753_CORE_MAXIMA60_TOP20_NINE_FIXED54_CONTEXTS_BOTH_QA_PASS',
            'Closed original saved-text summary status/schema differs')
    for name, expected in summary['read_input_byte_pins'].items():
        authenticate(root, name, pins, expected)
    require(args.primary_qa_sha256 == PRIMARY_QA_SHA == summary['actual_primary_QA_receipt_sha256'] == provenance['primary_QA_sha256']
            and args.context_qa_sha256 == CONTEXT_QA_SHA == summary['actual_context_QA_receipt_sha256'] == provenance['context_QA_sha256'],
            'Both original closed QA SHA bindings differ')
    require(pins[PRIMARY_QA]['sha256'] == args.primary_qa_sha256
            and pins[CONTEXT_QA]['sha256'] == args.context_qa_sha256, 'Actual authenticated QA file SHA differs from CLI')
    primary = load_json(root, PRIMARY_QA, pins, summary['read_input_byte_pins'][PRIMARY_QA])
    context = load_json(root, CONTEXT_QA, pins, summary['read_input_byte_pins'][CONTEXT_QA])
    require(primary['schema'] == 'SETI_S2017_CONTROL_TARGET_SAVED_INDEPENDENT_QA_V1'
            and primary['status'] == 'PASS753_ORIGINAL_OFF_MAPS3021_RAW_SCORE_QUERIES_NO_DETECTOR_RERUN'
            and context['schema'] == 'SETI_S2017_CONTROL_TARGET_FIXED_CONTEXT_INDEPENDENT_QA_V1'
            and context['status'] == 'PASS54_FIXED_CONTEXT_RAW503_SCORES96_SOURCE_ROWS_NO_SEARCH'
            and context['primary_qa_receipt_sha256'] == PRIMARY_QA_SHA, 'Both closed independent QA PASS required')
    failure_name = DELIVERY + '/REPORT_RECEIPT.json'
    failure = load_json(root, failure_name, pins, known[failure_name])
    require(failure == provenance['failure'] and failure['status'] == 'INCOMPLETE_PRESERVED_NO_AUTOMATIC_RETRY'
            and failure['failure_type'] == 'TypeError'
            and failure['failure'] == 'Colorbar.set_ticks() takes 2 positional arguments but 3 were given', 'Original render failure differs')
    expected_counts = {'primary_jobs': 3, 'maps': 753, 'carrier_maxima': 3084288,
        'correlated_width_drift_combinations': 4842332160, 'top20_records': 60,
        'selected_logical_tracks': 9, 'fixed_context_records': 54, 'primary_fraction_rows': 144}
    require(summary['counts'] == expected_counts and len(summary['all753_audited_core_maxima']) == 753
            and len(summary['selected_primary_summaries']) == 9 and len(summary['all54_original_fixed_context_records']) == 54,
            'Exact saved summary count contract differs')
    require(summary['qualified_SETI_detection'] is False and summary['new_fit_selection_or_veto'] is False
            and summary['new_HTTP_requests'] == 0 and summary['cost_DKK'] == 0, 'Preserved saved report scope differs')
    return summary, provenance, pins, proof


def render(summary, output):
    import numpy as np
    import matplotlib
    require(importlib.metadata.version('matplotlib') == '3.10.8', 'Exact Matplotlib3.10.8 required')
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt, colors, patches, patheffects
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.titlesize': 11, 'axes.labelsize': 10})
    fig = plt.figure(figsize=(16, 11.5), dpi=160)
    grid = fig.add_gridspec(3, 2, width_ratios=(1.35, 2.05), height_ratios=(1, 1, 1.2),
                          left=.065, right=.94, bottom=.11, top=.88, hspace=.45, wspace=.36)
    fig.suptitle('Tre oprindelige kontrolretninger · 28. april 2017', fontsize=20, fontweight='bold', y=.98)
    fig.text(.5, .935, '753 kernemaksima · 9 faste udvalg × 6 scanninger · robuste scorer, ikke kalibreret S/N eller FAP', ha='center', fontsize=11)
    for index, (primary_id, (target, scan)) in enumerate(TARGETS.items()):
        ax = fig.add_subplot(grid[index, 0])
        rows = [r for r in summary['all753_audited_core_maxima'] if r['primary_id'] == primary_id]
        for start, stop in ((1, 64), (65, 128), (129, 192), (193, 255)):
            segment = [r for r in rows if start <= r['core_q'] < stop]
            ax.plot([r['frequency_hz_at_own_first_midpoint'] / 1e6 for r in segment],
                    [r['score'] for r in segment], color=('#137f88', '#4356a8', '#b75f12')[index], lw=.9, marker='.', ms=2.8)
        ax.axvline(KNOWN_MHZ, color='#383838', ls='--', lw=1, label='Tidligere kendt reference 2300.390625 MHz')
        ax.set_yscale('symlog', linthresh=1.)
        ax.grid(alpha=.2)
        ax.set_title(target + ' · ' + scan + ' (oprindelig OFF)', loc='left')
        ax.set_ylabel('Robust maksimumsscore')
        if index == 2:
            ax.set_xlabel('MHz ved primærscanningens første midpoint')
        if index == 0:
            ax.legend(fontsize=7.5, frameon=False, loc='upper right')
    rows = summary['selected_primary_summaries']
    values = np.asarray([[r['context_scores'][s] for s in SCANS] for r in rows], dtype=float)
    vmax = max(1., float(np.max(np.abs(values))))
    ax = fig.add_subplot(grid[:2, 1])
    image = ax.imshow(values, aspect='auto', cmap='coolwarm',
                      norm=colors.SymLogNorm(linthresh=1., vmin=-vmax, vmax=vmax))
    ax.set_yticks(range(9), [r['track_key'] for r in rows])
    ax.set_xticks(range(6), ['%d %s\n%s' % (i // 2 + 1, item['original_acquisition_role'], item['target'])
        for i, item in enumerate(summary['original_scan_metadata'])], fontsize=8)
    ax.set_title('Fast uændret spor i alle seks scanninger', loc='left', pad=12)
    for i, row in enumerate(rows):
        origin = SCANS.index(row['selected_tuple']['scan_id'])
        ax.add_patch(patches.Rectangle((origin - .5, i - .5), 1, 1, fill=False, ec='black', lw=2.1))
        for j, value in enumerate(values[i]):
            text = ax.text(j, i, format(value, '.3g'), ha='center', va='center', fontsize=8.2, color='black')
            text.set_path_effects([patheffects.withStroke(linewidth=2.0, foreground='white')])
    colorbar = fig.colorbar(image, ax=ax, fraction=.035, pad=.025)
    colorbar.set_label('Fast robust score · symmetrisk logfarve')
    ax.text(0., - .13, 'Sort ramme: primærscanning. Alle andre felter: tid/retningskontekst.', transform=ax.transAxes, fontsize=9)
    ax = fig.add_subplot(grid[2, 1])
    fractions = np.asarray([[np.nan if x is None else x for x in r['primary_positive_row_fractions']] for r in rows])
    cmap = plt.get_cmap('viridis').copy(); cmap.set_bad('#c9c9c9')
    image = ax.imshow(fractions, aspect='auto', cmap=cmap, vmin=0, vmax=1)
    labels = [r['track_key'] + ' · hit %d/16' % r['known_reference_box_hit_row_count'] for r in rows]
    ax.set_yticks(range(9), labels, fontsize=8.5)
    ax.set_xticks(range(16), range(1, 17), fontsize=8)
    ax.set_title('Primærscanning: andel af positive rækkebidrag', loc='left', pad=9)
    ax.set_xlabel('Integrationsrække · ×: box dækker den tidligere referencekanal')
    for i, row in enumerate(rows):
        for j, hit in enumerate(row['known_reference_box_hit_by_primary_row']):
            if hit:
                text = ax.text(j, i, '×', ha='center', va='center', color='white', fontsize=11)
                text.set_path_effects([patheffects.withStroke(linewidth=1.5, foreground='black')])
    colorbar = fig.colorbar(image, ax=ax, fraction=.035, pad=.025)
    colorbar.set_ticks([0, .25, .5, .75, 1], labels=['0%', '25%', '50%', '75%', '100%'])
    fig.text(.5, .045, 'Alle logiske udvalg bevares; samme 96 centre/bredde/kerne kan gentages. Rækkeandele er beskrivende og giver ingen ny detektionstest.', ha='center', fontsize=9)
    fig.text(.5, .018, 'Referenceoverlap fastslår ingen fysisk årsag. Kerne-MAD/lokation er hashbundne; ingen uafhængig fuld refiltrering eller global FAP.', ha='center', fontsize=9)
    buffer = io.BytesIO(); fig.savefig(buffer, format='png'); plt.close(fig)
    save_bytes(output, buffer.getvalue())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--source-sha256')
    parser.add_argument('--review-sha256')
    parser.add_argument('--summary-sha256')
    parser.add_argument('--primary-qa-sha256')
    parser.add_argument('--context-qa-sha256')
    parser.add_argument('--root-go-path')
    parser.add_argument('--root-go-sha256')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    if args.check_only:
        proof = render_copy_proof(root)
        print(json.dumps({'status': 'PASS_SOURCE_ONLY_EXACT_RENDER_AST_SINGLE_LABELS_KEYWORD_REPAIR',
                         'renderer_source_pin': byte_pin(root, SOURCE), 'original_source_sha256': ORIGINAL_SOURCE_SHA, **proof}))
        return
    started, cpu0 = time.monotonic(), time.process_time()
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
    def deadline(signum, frame):
        raise TimeoutError('Figure repair wall300s cap')
    signal.signal(signal.SIGALRM, deadline); signal.alarm(WALL_CAP)
    lock, output_started = None, False
    try:
        fd = os.open(root / BASE / 'ACTIVE_FAMILY_FLOCK.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        lock = os.fdopen(fd, 'a+b'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        summary, provenance, pins, proof = admit(root, args)
        require(not any(confined(root, path).exists() for path in OUTPUT_PATHS), 'Create-only figure/completion outputs already exist')
        output_guard(root, reserve=OUTPUT_CAP - output_guard(root))
        output_started = True
        render(summary, confined(root, OUTPUT_PATHS[0]))
        for name, expected in pins.items():
            require(byte_pin(root, name) == expected, 'Admitted input changed during drawing: ' + name)
        output_guard(root)
        usage = {'process_CPU_seconds': time.process_time() - cpu0, 'wall_seconds': time.monotonic() - started,
                 'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        require(0 < usage['process_CPU_seconds'] <= CPU_CAP and 0 < usage['wall_seconds'] <= WALL_CAP
                and 0 < usage['peak_RSS_bytes'] <= RAM_CAP, 'Measured final figure-repair resource bound')
        receipt = {'schema': 'SETI_S2017_CONTROL_REPORT_FIGURE_REPAIR_COMPLETION_V1',
            'status': 'COMPLETE_SAVED_TEXT_REPORT_AND_REPAIRED_FIGURE',
            'report_source_sha256': ORIGINAL_SOURCE_SHA,
            'report_receipt_sha256': pins[DELIVERY + '/REPORT_RECEIPT.json']['sha256'],
            'renderer_source_sha256': args.source_sha256, 'renderer_source_review_sha256': args.review_sha256,
            'root_figure_GO_sha256': args.root_go_sha256, 'failure_provenance_sha256': PROVENANCE_PIN['sha256'],
            'actual_original_producer_exit_code': 1, 'original_failure': provenance['failure'],
            'original_failure_and_five_text_outputs_preserved': True,
            'actual_primary_QA_receipt_sha256': args.primary_qa_sha256,
            'actual_context_QA_receipt_sha256': args.context_qa_sha256,
            'summary_sha256': args.summary_sha256, 'input_byte_pins': pins,
            'output_base_directory': DELIVERY, 'output_byte_pin_keys': 'basenames',
            'output_byte_pins': {name: byte_pin(root, DELIVERY + '/' + name) for name in TEXT_NAMES + (PNG_NAME,)},
            'counts': summary['counts'], 'render_source_AST_proof': proof,
            'matplotlib_version': '3.10.8', **usage, 'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP,
            'memory_cap_bytes': RAM_CAP, 'output_cap_bytes': OUTPUT_CAP, 'workspace_cap_bytes': WORKSPACE_CAP,
            'H5_NPZ_BIN_opened': False, 'science_QA_or_numerical_derivation_rerun': False,
            'detector_or_score_grid_rerun': False, 'new_fit_selection_or_veto': False,
            'new_HTTP_requests': 0, 'new_BODY_bytes': 0, 'cost_DKK': 0,
            'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False}
        data = json_bytes(receipt)
        output_guard(root, reserve=len(data))
        save_bytes(confined(root, OUTPUT_PATHS[1]), data)
        print(json.dumps({'status': receipt['status'], 'completion_receipt_pin': byte_pin(root, OUTPUT_PATHS[1]),
                         'PNG_pin': byte_pin(root, OUTPUT_PATHS[0])}))
    except BaseException as exc:
        if output_started and not confined(root, OUTPUT_PATHS[1]).exists():
            save_bytes(confined(root, OUTPUT_PATHS[1]), json_bytes({
                'schema': 'SETI_S2017_CONTROL_REPORT_FIGURE_REPAIR_COMPLETION_V1',
                'status': 'INCOMPLETE_FIGURE_ONLY_REPAIR_PRESERVED_NO_AUTOMATIC_RETRY',
                'failure_type': type(exc).__name__, 'failure': str(exc),
                'original_report_source_sha256': ORIGINAL_SOURCE_SHA,
                'original_failure_preserved': True, 'H5_NPZ_BIN_opened': False,
                'science_QA_or_numerical_derivation_rerun': False, 'new_HTTP_requests': 0}))
        raise
    finally:
        signal.alarm(0)
        if lock is not None:
            lock.close()


if __name__ == '__main__':
    main()
