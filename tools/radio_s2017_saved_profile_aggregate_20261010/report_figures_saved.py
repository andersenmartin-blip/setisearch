"""Saved-JSON Danish interpretation and two display figures, after closed QA.

Source-only preparation is inert. This module never opens NPY, NPZ or HDF5,
imports detector/profile code, recomputes statistics or acquires source data.
The source aggregate's complete rank list and preset display case are retained.
"""
import time
START = time.monotonic()
import argparse
import fcntl
import hashlib
import importlib.util
from io import BytesIO
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import sys

sys.dont_write_bytecode = True
FAMILY = 'radio_s2017_saved_profile_aggregate_20261010'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
ONS = SCANS[::2]
LABELS = ('ON1', 'OFF1', 'ON2', 'OFF2', 'ON3', 'OFF3')
AGGREGATE_SCHEMA = 'SETI_S2017_SAVED_PROFILE_AGGREGATE_V1'
# Final source review binds the author's exact terminal schemas before GO.
EXEC_SCHEMA = 'SETI_S2017_SAVED_PROFILE_AGGREGATE_EXECUTION_V1'
EXEC_STATUS = 'COMPLETE_1905_SAVED_PROFILE_AGGREGATES_EXPLORATORY_ONLY'
QA_SCHEMA = 'SETI_S2017_SAVED_PROFILE_AGGREGATE_INDEPENDENT_QA_V1'
QA_STATUS = 'PASS_SAVED_2017_AGGREGATE_COMPLETE_INDEPENDENT_ARITHMETIC_QA'
LIMITS = {'CPU_seconds': 30, 'wall_seconds': 120, 'memory_bytes': 1073741824,
          'output_bytes': 16777216}
PNG_SHA = '98330391a76d1fa9b0138f1ecd62be1ef0c5a4c3ac3bdc2a5963538c5aa9434a'
FIGURE_NAMES = ('SIGNED_WORST_ON_OFF_GAP_VS_DRIFT.png', 'PRESELECTED_MAX_MEAN_GAP_LOCAL_PROFILES.png')
REPORT_NAME = 'README_DANSK.txt'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def confined(root, relative):
    p = Path(relative)
    require(type(relative) is str and not p.is_absolute() and p.parts and '..' not in p.parts
            and str(p) == relative and '\\' not in relative, 'Canonical root-relative metadata path required')
    target = root / p
    require(target.resolve() == target and root in target.parents, 'Escaped or symlinked metadata path')
    return target


def no_constant(value):
    raise ValueError('Nonfinite JSON constant: ' + value)


def read_json(root, pin, opened):
    require(set(pin) == {'path', 'bytes', 'sha256'} and type(pin['bytes']) is int
            and 0 < pin['bytes'] <= 67108864 and re.fullmatch('[0-9a-f]{64}', pin['sha256']), 'Exact bounded JSON pin required')
    target = confined(root, pin['path'])
    require(target.suffix == '.json', 'Scientific metadata intake is JSON only')
    raw = target.read_bytes()
    require(len(raw) == pin['bytes'] and sha(raw) == pin['sha256'], 'Saved JSON bytes differ: ' + pin['path'])
    require(pin['path'] not in opened or opened[pin['path']] == pin, 'Conflicting saved-JSON pin')
    opened[pin['path']] = pin
    return json.loads(raw, parse_constant=no_constant)


def file_pin(root, target):
    require(target.is_absolute() and target.resolve() == target and root in target.parents, 'Canonical own artifact path required')
    raw = target.read_bytes()
    return {'path': target.relative_to(root).as_posix(), 'bytes': len(raw), 'sha256': sha(raw)}


def prepare(target, value):
    pending = target.with_name(target.name + '.pending')
    raw = (json.dumps(value, allow_nan=False, indent=2) + '\n').encode()
    with pending.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    fd = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return pending


def publish(pending, target):
    os.link(pending, target)
    pending.unlink()
    fd = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_new(target, value):
    publish(prepare(target, value), target)


def check_resources(out, report_path=None):
    used = {'process_CPU_seconds_including_imports': time.process_time(),
            'wall_seconds_since_module_clock': time.monotonic() - START,
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            'derived_output_bytes': sum(p.stat().st_size for p in out.iterdir() if p.is_file()) if out.is_dir() else 0}
    if report_path is not None and report_path.is_file():
        used['derived_output_bytes'] += report_path.stat().st_size
    require(used['process_CPU_seconds_including_imports'] <= 30
            and used['wall_seconds_since_module_clock'] <= 120
            and used['peak_RSS_bytes'] <= LIMITS['memory_bytes']
            and used['derived_output_bytes'] <= LIMITS['output_bytes'], 'Finite saved-JSON display budget exceeded')
    return used


def admit(root, manifest, freeze, opened):
    require(manifest['schema'] == 'SETI_S2017_SAVED_PROFILE_AGGREGATE_POSTPROCESSING_INPUTS_V1'
            and manifest['postprocessing_public_freeze_commit'] == freeze
            and manifest['one_postprocessing_GO_after_closed_QA'] is True
            and manifest['root_verified_original_and_QA_closed_resources'] is True
            and manifest['retry_rerender_resume_authorized'] is False, 'Exact late frozen one-shot root admission required')
    require(manifest['script_pin'] == file_pin(root, Path(__file__))
            and manifest['publisher_pin'] == file_pin(root, Path(__file__).parent / 'saved_png_publish.py')
            and manifest['publisher_pin']['sha256'] == PNG_SHA, 'Frozen report/figure sources differ')
    pins = manifest['input_json_pins']
    require(type(pins) is list and 5 <= len(pins) <= 16
            and len({p['path'] for p in pins}) == len(pins), 'Finite unique metadata inventory required')
    inventory = {p['path']: p for p in pins}
    def explicit(name):
        pin = manifest[name]
        require(inventory.get(pin['path']) == pin, 'Explicit input not in exact inventory: ' + name)
        return read_json(root, pin, opened)
    scope = explicit('aggregate_scope_pin')
    execution = explicit('aggregate_execution_pin')
    aggregate = explicit('aggregate_pin')
    qa = explicit('qa_receipt_pin')
    whole = explicit('aggregate_whole_closed_pin')
    closed_evidence = explicit('closed_resource_evidence_pin')
    require(set(opened) == set(inventory), 'No unrelated or unexamined JSON inventory entries')
    require(execution['schema'] == EXEC_SCHEMA and execution['status'] == EXEC_STATUS
            and execution['scope_sha256'] == manifest['aggregate_scope_pin']['sha256']
            and execution['script_sha256'] == scope['script_sha256']
            and execution['public_freeze_commit'] == manifest['aggregate_public_freeze_commit']
            and execution['aggregate_pin'] == manifest['aggregate_pin']
            and execution['all_input_end_readbacks_exact'] is True and execution['resource_caps_satisfied'] is True,
            'Actual exact original aggregate COMPLETE required')
    require(whole['schema'] == 'SETI_S2017_SAVED_PROFILE_AGGREGATE_WHOLE_COMMAND_CLOSED_V1'
            and whole['status'] == 'PASS_CLOSED_EXIT0_COMPLETE_AGGREGATE_RESOURCES'
            and whole['actual_return_code'] == 0 and whole['child_closed_reaped'] is True
            and whole['resource_caps_satisfied'] is True and whole['timed_out'] is False
            and whole['public_freeze_commit'] == manifest['aggregate_public_freeze_commit']
            and whole['scope_pin'] == manifest['aggregate_scope_pin']
            and whole['execution_pin'] == manifest['aggregate_execution_pin']
            and whole['result_pin'] == manifest['aggregate_pin'], 'Exact actual closed producer resources required')
    require(qa['schema'] == QA_SCHEMA and qa['status'] == QA_STATUS
            and qa['aggregate_pin'] == manifest['aggregate_pin']
            and qa['aggregate_execution_pin'] == manifest['aggregate_execution_pin']
            and qa['aggregate_scope_pin'] == manifest['aggregate_scope_pin']
            and qa['aggregate_whole_closed_pin'] == manifest['aggregate_whole_closed_pin']
            and qa['public_aggregate_freeze_commit'] == manifest['aggregate_public_freeze_commit']
            and qa['all_input_end_readbacks_exact'] is True, 'Actual exact independent aggregate QA PASS required')
    closed = manifest['root_verified_closed_resource_summary']
    require(closed_evidence['schema'] == 'SETI_S2017_AGGREGATE_DISPLAY_CLOSED_RESOURCE_ADMISSION_V1'
            and closed_evidence['aggregate_whole_closed_pin'] == manifest['aggregate_whole_closed_pin']
            and closed_evidence['qa_receipt_pin'] == manifest['qa_receipt_pin']
            and closed_evidence['root_verified_closed_resource_summary'] == closed,
            'Pinned actual root closure evidence differs from admitted summaries')
    phase_limits = {'aggregate': {'CPU_seconds': scope['CPU_cap_s'], 'wall_seconds': scope['wall_cap_s'],
                                 'memory_bytes': scope['memory_cap_bytes']}, 'QA': qa['limits']}
    for phase in ('aggregate', 'QA'):
        proof = closed[phase]
        require(proof['closed_reaped'] is True and proof['actual_return_code'] == 0
                and proof['resource_caps_satisfied'] is True
                and all(finite(proof[k]) and proof[k] >= 0 for k in ('CPU_seconds', 'wall_seconds'))
                and type(proof['peak_RSS_bytes']) is int and proof['peak_RSS_bytes'] > 0,
                'Actual closed resource proof must be root verified for ' + phase)
        require(proof['CPU_seconds'] <= phase_limits[phase]['CPU_seconds']
                and proof['wall_seconds'] <= phase_limits[phase]['wall_seconds']
                and proof['peak_RSS_bytes'] <= phase_limits[phase]['memory_bytes'], 'Actual full-command cap exceeded for ' + phase)
    require(all(closed['aggregate'][k] == whole[k] for k in ('CPU_seconds', 'wall_seconds', 'peak_RSS_bytes')),
            'Original producer measured resources differ from root copied evidence')
    require(aggregate['schema'] == AGGREGATE_SCHEMA, 'Exact saved-profile aggregate schema required')
    require(aggregate['scope_sha256'] == execution['scope_sha256']
            and aggregate['script_sha256'] == execution['script_sha256']
            and aggregate['public_freeze_commit'] == execution['public_freeze_commit']
            and aggregate['member_count'] == 1905 and aggregate['triple_count'] == 635
            and aggregate['logical_scan_profiles'] == 11430 and aggregate['unique_geometries'] == 11369
            and aggregate['geometry_aliases'] == 61 and aggregate['old_geometry_overlap'] == 0
            and aggregate['new_original_detector_hypothesis_combinations'] == 0,
            'Original saved-family provenance/counts differ')
    records = aggregate['records']
    require(type(records) is list and len(records) == 1905
            and [r['logical_member_index'] for r in records] == list(range(1905))
            and len({r['match_id'] for r in records}) == 635, 'Complete original635-triplet/1905-path family required')
    for r in records:
        require(r['originating_ON'] in ONS and type(r['original_display_rank']) is int
                and 2 <= r['original_display_rank'] <= 636
                and r['width_channels'] in (1, 3)
                and all(finite(r[k]) for k in ('drift_hz_s', 'signed_worst_mean_gap', 'signed_worst_half_gap', 'signed_neighborhood_gap'))
                and -4 <= r['drift_hz_s'] <= 4, 'Saved finite original path/gap metadata required')
        require([s['scan_id'] for s in r['scan_metrics']] == list(SCANS), 'Six original scan metrics required')
    for rank_name in ('rank_by_signed_worst_mean_gap', 'rank_by_signed_neighborhood_gap'):
        ranking = aggregate[rank_name]
        require(type(ranking) is list and len(ranking) == 1905
                and all(type(index) is int for index in ranking) and set(ranking) == set(range(1905)),
                'Complete source-computed index permutation required')
    counts = aggregate['descriptive_counts']
    for name in ('signed_worst_mean_gap_positive', 'signed_worst_half_gap_positive',
                 'signed_neighborhood_gap_positive', 'all_ON_rows_positive'):
        require(type(counts[name]) is int and 0 <= counts[name] <= 1905,
                'Source-computed bounded headline count required: ' + name)
    chosen = aggregate['selected_display_case']
    index = aggregate['rank_by_signed_worst_mean_gap'][0]
    require(all(chosen[k] == v for k, v in records[index].items()), 'Preserve source-selected mean-gap rank1 case exactly')
    require(chosen['source_channel_offsets'] == list(range(-64, 65))
            and finite(chosen['df_hz']) and chosen['df_hz'] != 0 and finite(chosen['fch1_hz']),
            'All129 original offsets and native frequency coordinate required')
    profiles = chosen['scan_profiles']
    require([s['scan_id'] for s in profiles] == list(SCANS)
            and all(len(s['mean_normalized_minus_flank_frequency_profile']) == 129
                    and all(finite(v) for v in s['mean_normalized_minus_flank_frequency_profile']) for s in profiles),
            'Six complete saved129-channel mean profiles required')
    return aggregate, execution, qa


def figures(aggregate, out, publisher):
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[name] = '1'
    os.environ['MPLBACKEND'] = 'Agg'
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    def save(fig, name):
        buffer = BytesIO(); fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight', pad_inches=.2)
        raw = buffer.getvalue()
        require(sum(p.stat().st_size for p in out.iterdir() if p.is_file()) + len(raw) + 1048576 <= LIMITS['output_bytes'],
                'Finite figure/report reservation exceeded before publication')
        result = publisher.publish_png_atomic(out / name, raw)
        plt.close(fig)
        return {'path': 'presentation/' + name, **result}
    records, chosen = aggregate['records'], aggregate['selected_display_case']
    palette = ('#0072B2', '#D55E00', '#009E73')
    fig, ax = plt.subplots(figsize=(12, 7))
    for i, origin in enumerate(ONS):
        for width, marker in ((1, 'o'), (3, '^')):
            subset = [r for r in records if r['originating_ON'] == origin and r['width_channels'] == width]
            ax.scatter([r['drift_hz_s'] for r in subset], [r['signed_worst_mean_gap'] for r in subset],
                       s=17, alpha=.5, marker=marker, color=palette[i], linewidths=0,
                       label=f'ON{i+1} · bredde {width}')
    all_gaps = [r['signed_worst_mean_gap'] for r in records]
    low, high = min(min(all_gaps), 0), max(max(all_gaps), 0)
    pad = .08 * (high - low) if high > low else 1.0
    ax.set_ylim(low - pad, high + pad); ax.set_xlim(-4.1, 4.1)
    ax.axhline(0, color='#444444', linewidth=.8)
    ax.scatter([chosen['drift_hz_s']], [chosen['signed_worst_mean_gap']], s=140,
               facecolors='none', edgecolors='black', linewidths=1.7, label='Kildens valgte største middel-forskel')
    ax.set_xlabel('Oprindelig fast drift (Hz/s)')
    ax.set_ylabel('Gemt min(ON-midler) − max(OFF-midler)\n(normaliseret residual; ikke SNR)')
    ax.set_title('2017: alle 1.905 gemte stier fra 635 samme-observations-tripler', pad=16)
    ax.legend(loc='upper center', bbox_to_anchor=(.5, -.13), ncol=3, frameon=False, fontsize=9)
    ax.grid(alpha=.2)
    fig.text(.5, .025, 'Efterfølgende rangering af allerede udvalgte profiler · korrelerede stier · ingen falskalarmkalibrering eller detektionspåstand', ha='center', fontsize=9)
    fig.subplots_adjust(left=.12, right=.97, top=.9, bottom=.25)
    first = save(fig, FIGURE_NAMES[0])
    offsets = chosen['source_channel_offsets']
    ordering = sorted(range(129), key=lambda i: offsets[i] * chosen['df_hz'])
    hz = [offsets[i] * chosen['df_hz'] for i in ordering]
    profiles = chosen['scan_profiles']
    fig, ax = plt.subplots(figsize=(12, 7))
    values = []
    for i, s in enumerate(profiles):
        y = [s['mean_normalized_minus_flank_frequency_profile'][j] for j in ordering]
        values.extend(y)
        ax.plot(hz, y, color=palette[i // 2], linestyle='-' if i % 2 == 0 else '--',
                linewidth=1.4, label=LABELS[i])
    low, high = min(min(values), 0), max(max(values), 0)
    pad = .08 * (high - low) if high > low else 1.0
    ax.set_ylim(low - pad, high + pad); ax.set_xlim(hz[0], hz[-1])
    half_box_hz = .5 * chosen['width_channels'] * abs(chosen['df_hz'])
    ax.axvspan(-half_box_hz, half_box_hz, color='#777777', alpha=.12, label='Oprindelig valgt kanalbredde')
    ax.axvline(0, color='#555555', linewidth=.7); ax.axhline(0, color='#555555', linewidth=.7)
    member = chosen['original_member']
    origin = LABELS[SCANS.index(chosen['originating_ON'])]
    ax.set_title(f"Eftervalgt største middel-forskel: original tripelrang {chosen['original_display_rank']} · sti fra {origin}\n"
                 f"{member['original_reference_frequency_hz']/1e6:.9f} MHz ved egen ON-reference · {chosen['drift_hz_s']:+.6f} Hz/s · bredde {chosen['width_channels']}", pad=14)
    ax.set_xlabel('Fast kanaloffset × original df (Hz), omkring den fulgte centerkanal')
    ax.set_ylabel('Gemt mean(normaliseret power − række-flankemedian)\n(beskrivende lokal profil; ikke SNR)')
    ax.legend(loc='upper center', bbox_to_anchor=(.5, -.13), ncol=4, frameon=False, fontsize=9)
    ax.grid(alpha=.2)
    fig.text(.5, .025, 'Alle 129 offsets og seks kurver er bevaret. Native negativ df omordnet til stigende Hz.\nLokalt, track-alignet ±64-kanalsvindue; ingen ny peakfit, recentering, OFF-veto eller påstand om fravær langs hele sporet.',
             ha='center', fontsize=9)
    fig.subplots_adjust(left=.12, right=.97, top=.86, bottom=.25)
    second = save(fig, FIGURE_NAMES[1])
    return [first, second], matplotlib.__version__


def count(value):
    return f'{value:,}'.replace(',', '.')


def make_report(aggregate, execution, qa):
    chosen, records = aggregate['selected_display_case'], aggregate['records']
    counts = aggregate['descriptive_counts']
    local_first = records[aggregate['rank_by_signed_neighborhood_gap'][0]]
    selected_rank = chosen['original_display_rank']
    origin = LABELS[SCANS.index(chosen['originating_ON'])]
    text = ['2017: beskrivende ON/OFF-struktur i gemte profiler', '',
        'Denne opfølgning bruger allerede målte og autentificerede profiler fra samme 2017-observation. '
        'De nye beskrivende mål og gemte output har bestået QA. Der er ingen ny teleskopanskaffelse, detektorsøgning eller profiludmåling i denne fase.', '',
        'Alle 1.905 oprindelige ON-medlemsstier fra 635 cross-ON-tripler indgår med deres seks gemte scans. '
        'Kun det præcise oprindelige rang1-tripel var udeladt i profilfasen; beslægtede profiler kan stadig berøre samme lokale struktur. '
        'Stier og tripler er korrelerede og tælles ikke som uafhængige signaler.', '',
        'Middel-forskellen er det allerede gemte min(ON1, ON2, ON3)-max(OFF1, OFF2, OFF3) for de normaliserede, bredde-valgte residualmidler. '
        'Halv-forskellen anvender de gemte første/sidste halvdele. Det særskilte nabomål sammenholder ON-midlet med den største gemte lokale OFF-boksrespons i det afgrænsede profilvindue. '
        'Disse efterfølgende mål er beskrivende; de har ingen kalibreret falskalarmrate eller detektionstærskel.', '',
        f"Af alle 1.905 stier har {count(counts['signed_worst_mean_gap_positive'])} positiv gemt middel-forskel, "
        f"{count(counts['signed_worst_half_gap_positive'])} positiv gemt halv-forskel og "
        f"{count(counts['signed_neighborhood_gap_positive'])} positiv gemt lokal naboforskel. "
        f"{count(counts['all_ON_rows_positive'])} stier har positivt residual i alle 16 rækker i samtlige tre ON-scans. "
        'Tallene er overtaget direkte fra kildens deskriptive optælling; de er ikke uafhængige forsøgs- eller detektionstal.', '',
        f"Den største gemte lokale naboforskel er {local_first['signed_neighborhood_gap']:+.17g} "
        f"(oprindeligt medlemsindeks {local_first['logical_member_index']}, direkte fra kildens fulde nabomålsrangliste). "
        'Det lokale mål er særskilt fra middel-forskellen og fastslår ingen fysisk oprindelse.', '',
        f"Den viste sti er kildens forudeksporterede største middel-forskel: original tripelrang {selected_rank}, sti fra {origin}. "
        f"Gemt middel-forskel: {chosen['signed_worst_mean_gap']:+.9g}; halv-forskel: {chosen['signed_worst_half_gap']:+.9g}; "
        f"lokal naboforskel: {chosen['signed_neighborhood_gap']:+.9g}. "
        'Valget følger de observerede værdier. En stor middel-forskel er ikke i sig selv et bestået lokalt OFF-kriterium eller en uafhængig bekræftelse.', '',
        'Figur 1, hele den bevarede familie: presentation/' + FIGURE_NAMES[0], '',
        'Figur 2, den eftervalgte stis fulde lokale vindue: presentation/' + FIGURE_NAMES[1], '',
        'Alle 129 gemte kanaloffsets vises; der er ingen dynamisk peakfit, frekvensflytning, driftændring eller maskering. '
        'Vinduet følger den oprindelige faste sti med dens egen ON-reference. Det er lokal struktur og underbygger ingen påstand om fravær på hele OFF-sporet.', '',
        'Kildens første ti middel-rangposter (beskrivende, efterfølgende rangering):', '']
    for rank, index in enumerate(aggregate['rank_by_signed_worst_mean_gap'][:10], 1):
        r = records[index]; label = LABELS[SCANS.index(r['originating_ON'])]
        text.append(f"{rank}. Original tripelrang {r['original_display_rank']} / {label}; drift {r['drift_hz_s']:+.9g} Hz/s; bredde {r['width_channels']}; "
                    f"middel-forskel {r['signed_worst_mean_gap']:+.9g}; halv-forskel {r['signed_worst_half_gap']:+.9g}; naboforskel {r['signed_neighborhood_gap']:+.9g}.")
    text += ['', 'Resultatet ændrer ikke projektets oprindelige A/B-status FAIL_CLOSED eller independent_validation BLOCKED. '
        'Der er ingen sky-falskalarmkalibrering, blind gentagelse, fysisk oprindelsesklassifikation eller detektionspåstand. '
        'Figurerne læser alene nye, gemte JSON-scalarer og den allerede gemte lokale middelprofil; de gentager ingen måling eller rangering.', '',
        'Alle gemte mål og prædefinerede ranglister: measurement/SAVED_PROFILE_AGGREGATE.json',
        'Original execution: measurement/EXECUTION_RECEIPT.json', '']
    return '\n'.join(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'input-manifest', 'expected-input-manifest-sha256', 'postprocessing-freeze-commit'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--root-go-after-closed-qa', action='store_true')
    args = parser.parse_args()
    root = Path(args.root)
    require(root.is_absolute() and root.resolve() == root and root.is_dir() and args.root_go_after_closed_qa
            and re.fullmatch('[0-9a-f]{40}', args.postprocessing_freeze_commit), 'Canonical root and frozen late rootGO required')
    def stop(signum, frame):
        raise TimeoutError('Finite saved-JSON display deadline or termination')
    for s in (signal.SIGALRM, signal.SIGXCPU, signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(s, stop)
    resource.setrlimit(resource.RLIMIT_CPU, (30, 32))
    resource.setrlimit(resource.RLIMIT_AS, (LIMITS['memory_bytes'], LIMITS['memory_bytes']))
    signal.alarm(max(1, math.ceil(120 - (time.monotonic() - START))))
    stage = root / 'results' / FAMILY
    require(stage.is_dir(), 'Original completed aggregate stage required')
    out = stage / 'presentation'
    report_path = stage / REPORT_NAME
    marker, terminal = stage / 'DISPLAY_STARTED_ONCE.json', stage / 'DISPLAY_RECEIPT.json'
    guards, opened, owned, committed = [], {}, False, False
    try:
        # The root late admission establishes actual closure. Readonly locks
        # also fail closed if an original stage or QA is still an active owner.
        manifest_path = Path(args.input_manifest)
        require(manifest_path == stage / 'DISPLAY_INPUT_PINS.json' and manifest_path.resolve() == manifest_path
                and manifest_path.stat().st_size <= 1048576, 'Exact finite late display manifest path required')
        raw = manifest_path.read_bytes()
        require(sha(raw) == args.expected_input_manifest_sha256, 'Exact late manifest SHA required')
        manifest = json.loads(raw, parse_constant=no_constant)
        guard_paths = manifest['readonly_guard_paths']
        require(type(guard_paths) is list and set(guard_paths) == {
                'results/' + FAMILY + '/AGGREGATE_SERIAL.flock',
                'results/radio_s2017_saved_profile_aggregate_qa_20261010/QA_SERIAL.flock'} and len(guard_paths) == 2,
                'Two exact stable original/QA guard paths required')
        for relative in guard_paths:
            target = confined(root, relative)
            fd = os.open(target, os.O_RDONLY | (os.O_DIRECTORY if target.is_dir() else os.O_NOFOLLOW))
            guards.append(fd); fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not any(p.exists() for p in (out, report_path, marker, terminal, stage / 'DISPLAY_FAILURE_RECEIPT.json')),
                'Preserve previous display attempt; no rerender or replacement')
        owned = True
        write_new(marker, {'status': 'STARTED_ONE_SAVED_JSON_REPORT_TWO_FIGURES', 'script_pin': file_pin(root, Path(__file__)),
            'postprocessing_public_freeze_commit': args.postprocessing_freeze_commit, 'no_scientific_reexecution': True})
        manifest_pin = {'path': manifest_path.relative_to(root).as_posix(), 'bytes': len(raw), 'sha256': sha(raw)}
        aggregate, execution, qa = admit(root, manifest, args.postprocessing_freeze_commit, opened)
        out.mkdir(exist_ok=False)
        spec = importlib.util.spec_from_file_location('saved_profile_png_publisher', Path(__file__).parent / 'saved_png_publish.py')
        publisher = importlib.util.module_from_spec(spec); spec.loader.exec_module(publisher)
        images, version = figures(aggregate, out, publisher)
        check_resources(out)
        report_raw = make_report(aggregate, execution, qa).encode()
        with report_path.open('xb') as stream:
            stream.write(report_raw); stream.flush(); os.fsync(stream.fileno())
        for pin in list(opened.values()) + [manifest_pin]:
            read_json(root, pin, {})
        require(file_pin(root, Path(__file__)) == manifest['script_pin']
                and file_pin(root, Path(__file__).parent / 'saved_png_publish.py') == manifest['publisher_pin'], 'Display sources changed')
        measured = check_resources(out, report_path)
        receipt = {'schema': 'SETI_S2017_SAVED_PROFILE_AGGREGATE_DISPLAY_RECEIPT_V1',
            'status': 'COMPLETE_SAVED_JSON_REPORT_TWO_FIGURES_VISUAL_QA_PENDING', 'limits': LIMITS,
            'script_pin': manifest['script_pin'], 'publisher_pin': manifest['publisher_pin'],
            'postprocessing_public_freeze_commit': args.postprocessing_freeze_commit, 'input_manifest_pin': manifest_pin,
            'opened_JSON_pins': list(opened.values()), 'all_input_end_readbacks_exact': True,
            'images': images, 'report_pin': file_pin(root, report_path), 'matplotlib_version': version,
            'displayed_member_paths': 1905, 'displayed_mean_profile_values': 6 * 129,
            'source_selected_maximum_retained': True, 'ranking_or_gap_metrics_recomputed': False,
            'NPY_NPZ_HDF5_read': False, 'detector_or_profile_kernel_called': False,
            'median_or_normalization_computed': False, 'source_HTTP_requests': 0,
            'posthoc_same_visit_selection_explicit': True, 'original_statuses_preserved': True,
            'actual_visual_QA': 'PENDING_READONLY_IMAGE_INSPECTION', 'retry_authorized': False, **measured}
        pending = prepare(terminal, receipt)
        final = check_resources(out, report_path)
        require(final['process_CPU_seconds_including_imports'] + .1 < 30
                and final['wall_seconds_since_module_clock'] + 2 < 120, 'Insufficient finite display terminal headroom')
        signal.alarm(0)
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM, signal.SIGXCPU, signal.SIGTERM, signal.SIGHUP, signal.SIGINT})
        try:
            os.link(pending, terminal); committed = True
            pending.unlink()
            fd = os.open(stage, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)
        try:
            print(json.dumps({'status': receipt['status'], 'report': receipt['report_pin'], 'images': images}), flush=True)
        except BrokenPipeError:
            pass
    except BaseException as error:
        if owned and not committed:
            signal.alarm(0)
            signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM, signal.SIGXCPU, signal.SIGTERM, signal.SIGHUP, signal.SIGINT})
            write_new(stage / 'DISPLAY_FAILURE_RECEIPT.json', {'status': 'FAILED_DISPLAY_ATTEMPT_PRESERVED_NO_RETRY',
                'error_type': type(error).__name__, 'error': str(error), 'script_pin': file_pin(root, Path(__file__)),
                'source_HTTP_requests': 0, 'scientific_reexecution': False,
                'process_CPU_seconds': time.process_time(), 'wall_seconds': time.monotonic() - START})
        raise
    finally:
        signal.alarm(0)
        for fd in reversed(guards):
            os.close(fd)


if __name__ == '__main__':
    main()
