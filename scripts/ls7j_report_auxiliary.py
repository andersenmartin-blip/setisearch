#!/usr/bin/env python3
"""Report the fixed LS7J feasibility outcome after the independent raw audit."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def write(path, lines):
    text = '\n'.join(lines) if isinstance(lines, list) else lines
    path.write_text('\n'.join(line.rstrip() for line in text.splitlines())+'\n')


def number(value, digits=6):
    return 'unavailable' if value is None else f'{value:.{digits}g}'


def verdict(value):
    return 'PASS' if value else 'FAIL'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'results_ls7j_auxiliary')
    parser.add_argument('--update-status', action='store_true')
    args = parser.parse_args(); out = args.output
    s, audit, sources = [json.loads((out/name).read_text()) for name in ['summary.json', 'AUDIT.json', 'sources.json']]
    assert audit['passed'] and audit['raw_auxiliary_review']['passed']
    assert audit['feasibility_pass'] == s['feasibility_pass']
    responses = [json.loads(line) for line in gzip.decompress((out/'responses.jsonl.gz').read_bytes()).splitlines()]
    result = verdict(s['feasibility_pass']); date = datetime.now(timezone.utc).date().isoformat()
    short = (f'LS7J completed **420 fixed native windows and 9,480 digital response rows** on the same twenty closed-sector contexts. '
             f'The combined motion/outside-aperture correction has joint feasibility **{result}**; the independent audit passes. '
             'There are no new detector decisions or added observing days.')
    if s['feasibility_pass']:
        next_step = ('The fixed correction passes this bounded information test. Next specify one joint detector comparison on these same closed '
                     'contexts, with correction uncertainty and physically consistent pixel/motion controls. Require an explicit account of upstream '
                     'motion-field dependence on target variability. A full detector and control qualification remains necessary before unused data.')
    else:
        next_step = ('Close this fixed unit-gain motion plus protected-plane correction as a failed feasibility route. Use the saved component ratios '
                     'and full-stamp mismatch responses to identify whether native prediction, source-wing protection or missing motion information '
                     'limits it. Any next information study must address that measured limitation explicitly; no gain, profile, plane or threshold '
                     'retry follows within LS7J. No unused sector or detector qualification follows from this result.')

    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                         'svg.hashsalt': 'ls7j-auxiliary-feasibility-v1'})
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.6), constrained_layout=True)
    for column, sector in enumerate([29, 32]):
        ss = s['sectors'][str(sector)]; ax = axes[0, column]
        for method, color in [('motion', '#537aa6'), ('plane', '#ac7441'), ('combined', '#377d62')]:
            values = [b['ratio'] if b['ratio'] is not None else np.nan for b in ss['methods'][method]['per_background']]
            ax.plot(range(10), values, marker='o', ms=4, color=color, label=method, linewidth=1.7)
        ax.axhline(1, color='#555555', linewidth=1, label='static = 1')
        ax.axhline(2, color='#ad3e3e', linestyle='--', linewidth=1)
        ax.set(title=f'Sector {sector}: native residual energy', ylabel='Correction / static energy',
               xlabel='Background', xticks=range(10), xticklabels=[f'{a:02d}' for a in range(10)])
        ax.set_ylim(bottom=0); ax.grid(axis='y', alpha=.18); ax.legend(fontsize=8)
        ax = axes[1, column]
        for cohort, color, offset, limit in [('full_stamp', '#537aa6', -.19, 1.), ('broadened_full_stamp', '#a05a79', .19, 5.)]:
            maximum = []
            for a in range(10):
                rows = [r for r in responses if r['sector'] == sector and r['anchor'] == a and r['cohort'] == cohort
                        and r['response']['combined'] is not None]
                values = [r['response']['combined']['pulse_metrics']['relative_distortion'] for r in rows
                          if r['response']['combined']['pulse_metrics'] is not None]
                maximum.append(100*max(values) if values else np.nan)
            label = 'full stamp' if cohort == 'full_stamp' else 'broadened'
            ax.bar(np.arange(10)+offset, maximum, width=.36, color=color, label=label)
            ax.axhline(limit, color=color, linestyle='--', linewidth=1, label=f'{label} limit: {limit:g}%')
        ax.set(title=f'Sector {sector}: worst pulse distortion', ylabel='Relative L2 distortion (%)', xlabel='Background',
               xticks=range(10), xticklabels=[f'{a:02d}' for a in range(10)])
        ax.grid(axis='y', alpha=.18); ax.legend(fontsize=8)
    fig.suptitle('LS7J | Motion and outside-aperture feasibility', fontsize=16)
    fig.savefig(out/'comparison.png', dpi=170)
    fig.savefig(out/'comparison.svg', metadata={'Date': None}); plt.close(fig)
    write(out/'comparison.svg', (out/'comparison.svg').read_text())

    lines = ['# LS7J auxiliary-observable feasibility — '+result, '', short, '',
             'The primary method predicts reference-image motion from verified mission fields, then fits a protected background plane using '
             'simultaneous pixels outside the aperture. The native comparison holds the LS7I static covariance and mean fixed. '
             'Digital pulse responses measure downstream signal distortion; they do not measure detection efficiency or physical laser sensitivity.', '',
             '![Native prediction and full-stamp pulse protection](comparison.png)', '',
             'Top: lower energy ratios improve on static prediction; one is the aggregate ceiling and two the single-background ceiling. '
             'Bottom: each bar is the largest distortion among sixty response rows in that background/class. Dashed lines show the predeclared '
             '1% and 5% limits. Missing methods have no point/bar; their rows remain in the failing availability denominator.', '',
             '## Fixed primary requirements by sector', '',
             '| Sector | Combined native ratio | Backgrounds improved / 10 | Native gate | Operator gate | Historical pulses | Full-stamp pulses | Broadened pulses | Feasibility |',
             '|---|---:|---:|---|---|---|---|---|---|']
    for sector, ss in s['sectors'].items():
        m = ss['methods']['combined']; p = ss['protection']
        improved = sum(b['ratio'] is not None and b['ratio'] < 1 for b in m['per_background'])
        lines.append(f'| {sector} | {number(m["ratio"])} | {improved} | {verdict(m["pass"])} | {verdict(ss["operator_gate_pass"])} | '
                     f'{verdict(p["aperture_limited_historical"]["pass"])} | {verdict(p["full_stamp"]["pass"])} | '
                     f'{verdict(p["broadened_full_stamp"]["pass"])} | {verdict(ss["feasibility_pass"])} |')
    lines += ['', '## Native prediction and fixed component ablations', '',
              '| Sector | Method | Available / 210 | Total energy ratio | Improved / 10 | Worst background ratio | Native gate |',
              '|---|---|---:|---:|---:|---:|---|']
    for sector, ss in s['sectors'].items():
        for method, mm in ss['methods'].items():
            values = [b['ratio'] for b in mm['per_background'] if b['ratio'] is not None]
            lines.append(f'| {sector} | {method} | {mm["available_windows"]}/210 | {number(mm["ratio"])} | '
                         f'{sum(v < 1 for v in values)} | {number(max(values) if values else None)} | {verdict(mm["pass"])} |')
    lines += ['', 'Static is the reference and cannot meet the strict six-background improvement requirement. The primary method was fixed as '
              '`combined`; component results do not select a replacement. All methods use the same paired native metric. This is not a new '
              'calibration of covariance, discovery significance or false-alarm rate.', '',
              '| Sector | Background | Motion / static | Plane / static | Combined / static | Combined windows / 21 |',
              '|---|---:|---:|---:|---:|---:|']
    for sector, ss in s['sectors'].items():
        for a in range(10):
            values = [ss['methods'][m]['per_background'][a] for m in ['motion', 'plane', 'combined']]
            lines.append(f'| {sector} | {a:02d} | {number(values[0]["ratio"])} | {number(values[1]["ratio"])} | '
                         f'{number(values[2]["ratio"])} | {values[2]["available_windows"]}/21 |')

    lines += ['', '## Pulse protection including light outside the aperture', '',
              '| Sector | Cohort | Available / rows | Distortion limit | Maximum distortion | Gain min–max | Failed rows |',
              '|---|---|---:|---:|---:|---|---:|']
    for sector, ss in s['sectors'].items():
        for cohort, p in ss['protection'].items():
            lines.append(f'| {sector} | {cohort} | {p["available"]}/{p["trials"]} | {number(p["distortion_limit"])} | '
                         f'{number(p["maximum_distortion"])} | {number(p["minimum_gain"])}–{number(p["maximum_gain"])} | {len(p["failed_case_ids"])} |')
    lines += ['', 'Distortion is norm(corrected pulse − expected pulse)/norm(expected pulse), not a fraction of missed detections. '
              'Gain is the projection onto the expected pulse. Sparse residual stress is held identical in both members of each pulse-response pair. '
              'This separates the pulse itself from changes caused by an outside residual pixel.', '',
              'The 2,640 historical stellar rows have aperture-limited profiles. The 2,400 new rows retain full-stamp wings and use separately '
              'labeled standard and broadened profiles. They derive from 240 fixed parents without retuning their amplitude or event window. '
              'The injection proxy uses the whole native context; the inference proxy uses protected sidebands. A proxy can contain neighbors '
              'and background structure, and is not an independently calibrated target PRF. Even a passing wing test would have that limit.', '',
              'Every failed gated response is in [RESPONSE_FAILURES.md](RESPONSE_FAILURES.md); the complete ledger also retains all instrumental '
              'and null responses. The original 6,720-row and 360-row cohorts remain intact.', '',
              '| Sector | Valid operators / frames | Available motion frames | Maximum protected-basis distortion |',
              '|---|---:|---:|---:|']
    for sector, ss in s['sectors'].items():
        lines.append(f'| {sector} | {ss["valid_operators"]}/{ss["spatial_frames"]} | {ss["available_motion_frames"]} | {number(ss["protected_basis_max_distortion"])} |')
    lines += ['', 'Exact protection of the declared nine-dimensional source family is a mathematical check. The separately broadened and '
              'whole-context profiles test mismatch against that family. These are different requirements.', '',
              '## Verified auxiliary fields', '',
              '| Field | Sector 29 finite / 4,010 | Sector 32 finite / 4,010 | Use |', '|---|---:|---:|---|']
    by_sector = {r['sector']: r for r in sources}
    for field in by_sector[29]['columns']:
        n29, n32 = [by_sector[s]['columns'][field]['finite_context_values'] for s in [29, 32]]
        lines.append(f'| {field} | {n29}/4010 | {n32}/4010 | {"Motion, in YX order" if field.startswith("POS_CORR") else "Inventory only"} |')
    lines += ['', 'The [frozen protocol](../LS7J_AUXILIARY_PROTOCOL.md#fixed-inputs-and-field-verification) links the mission field definitions. '
              'Units, formats, missingness and processing metadata are recorded in [sources.json](sources.json). Every extracted value was checked '
              'against the two original hashed light-curve products by an independent cadence lookup. Missing data are retained without interpolation.', '',
              'Mission moment/PSF centroids are excluded from correction inputs. The ledger also records the change in a simple aperture-moment '
              'proxy after adding each pulse. That illustrates target-flux dependence without claiming to reproduce the mission algorithm. '
              'Holding POS_CORR fixed in a digital injection does not prove the upstream mission motion estimate is independent of a real stellar pulse.', '',
              'Historical pixel-only pointing injections leave motion metadata unchanged, so their responses are not physically consistent '
              'instrumental-control qualification. There is no new accept/reject ledger in LS7J.', '',
              '## Independent audit and provenance', '',
              f'Nine synthetic known-answer tests pass. The audit verifies **{audit["protected_operator_frames"]} spatial frames**, '
              f'**{audit["joint_unit_input_columns"]:,} outside unit-input columns**, all **420 native windows**, and all **9,480 response rows**. '
              'Scalar geometry and simultaneous source-plus-plane least squares provide independent checks of the projected operator. '
              'Actual injected cubes, coefficients, gains, distortions and gate counts are reconstructed. Earlier extraction and static-baseline '
              'audits are reused by hash, including exclusion of the assessed background from all sixty static baseline pairs.', '',
              f'Raw audit: **{audit["raw_auxiliary_review"]["context_rows"]:,} rows**, '
              f'**{audit["raw_auxiliary_review"]["auxiliary_values_checked"]:,} auxiliary field values**, two original products. '
              'Preserved manifests verify all earlier scientific records unchanged. [AUDIT.json](AUDIT.json) records numerical differences.', '',
              f'Source commit: `{s["freeze_commit"]}`. Source manifest SHA-256: `{s["freeze_sha256"]}`.', '',
              f'[Execution run](https://github.com/andersenmartin-blip/setisearch/actions/runs/{s["github_run_id"]}), '
              '[configuration](../config/ls7j_auxiliary.json), [summary](summary.json), [source extracts](sources.json), '
              '[operators](frames.jsonl.gz), [native windows](native_windows.jsonl.gz), [all responses](responses.jsonl.gz), '
              '[new recipes](full_stamp_recipes.jsonl.gz), [new patterns](full_stamp_patterns.jsonl.gz), '
              '[tests](TESTS.log), [run log](RUN.log), [audit log](AUDIT.log), [environment](environment.txt), [checksums](SHA256SUMS).', '',
              '## Decision and next work', '', next_step, '',
              'This result adds no observing coverage, promotes no native candidate and leaves unused TESS sectors and M43 held-out panels closed. '
              'The twenty repeated contexts limit generalization; row counts are not independent observations. Earlier LS7I failures remain unchanged.']
    write(out/'REPORT.md', lines)

    failures = ['# LS7J: every failed gated pulse response', '',
                'Rows fail a predeclared distortion or availability requirement. They are not counted as lost detections. '
                'All values refer to the primary combined correction. Historical source cohorts retain their original denominators.', '',
                '| Sector | Cohort | Background | Case ID | Gain | Distortion | Limit |', '|---|---|---:|---|---:|---:|---:|']
    lookup = {r['case_id']: r for r in responses}; count = 0
    for sector, ss in s['sectors'].items():
        for cohort, p in ss['protection'].items():
            for case_id in p['failed_case_ids']:
                r = lookup[case_id]; value = r['response']['combined']
                mm = None if value is None else value['pulse_metrics']
                failures.append(f'| {sector} | {cohort} | {r["anchor"]:02d} | `{case_id}` | '
                                f'{number(None if mm is None else mm["gain"])} | {number(None if mm is None else mm["relative_distortion"])} | '
                                f'{number(p["distortion_limit"])} |')
                count += 1
    if not count:
        failures.append('| — | None | — | — | — | — | — |')
    failures += ['', f'Total failed response rows: **{count}**. The full [responses](responses.jsonl.gz) retain passing rows and all controls.']
    write(out/'RESPONSE_FAILURES.md', failures)

    if args.update_status:
        continuation = ['# LS7J continuation — audited '+result, '', f'Completed {date}.', '', short, '', next_step, '',
                        '[Full result](results_ls7j_auxiliary/REPORT.md), [every failed response](results_ls7j_auxiliary/RESPONSE_FAILURES.md), '
                        '[protocol](LS7J_AUXILIARY_PROTOCOL.md).', '',
                        '## Reproduce the fixed result', '',
                        'Install `requirements_ls7g.txt`; set `PYTHONPATH=src`, `OPENBLAS_NUM_THREADS=1` and `OMP_NUM_THREADS=1`. '
                        'Run the evaluator into a new output path; it refuses to overwrite an existing result. The original two light-curve '
                        'files are fetched and verified when missing from the cache.', '', '```bash',
                        'python scripts/ls7j_auxiliary.py --cache data_ls7j_auxiliary --output /tmp/ls7j-reproduction',
                        'python scripts/ls7j_review_auxiliary.py --cache data_ls7j_auxiliary --output /tmp/ls7j-reproduction', '```', '',
                        'A derived-only audit can omit `--cache`, but cannot replace the original raw-extraction audit. '
                        'The committed result, source freeze, old baselines and historical ledgers stay unchanged. '
                        'There is no unattended continuation scheduled between active sessions.']
        write(ROOT/'LS7J_CONTINUATION.md', continuation)
        status = ROOT/'PROJECT_STATUS.md'; old = status.read_text()
        marker = '## LS7J auxiliary-observable study completed:'
        assert marker not in old
        insertion = marker+' '+result+'\n\n'+short+'\n\n'+next_step+'\n\n[Full result](results_ls7j_auxiliary/REPORT.md), [continuation](LS7J_CONTINUATION.md).\n\n'
        index = old.index('## LS7I joint background model completed:')
        old = old[:index]+insertion+old[index:]
        old = old.replace('Updated 13 September 2026.', 'Updated 14 September 2026.', 1)
        write(status, old)
    manifest = []
    for path in sorted(out.iterdir()):
        if path.is_file() and path.name not in ['SHA256SUMS', 'AUDIT_RECHECK.json']:
            manifest.append(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name)
    write(out/'SHA256SUMS', manifest)
    print(json.dumps({'feasibility': result, 'failed_response_rows': count, 'sealed_files': len(manifest)}), flush=True)


if __name__ == '__main__':
    main()
