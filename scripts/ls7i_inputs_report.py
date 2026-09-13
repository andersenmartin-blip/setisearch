#!/usr/bin/env python3
"""Publish a readiness report for restored inputs, not a detector result."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'results_ls7i_inputs')
    parser.add_argument('--update-status', action='store_true')
    args = parser.parse_args()
    out = args.output
    summary = json.loads((out/'summary.json').read_text())
    audit = json.loads((out/'AUDIT.json').read_text())
    assert summary['status'] == 'INPUTS_RECONSTRUCTED' and audit['passed']
    assert audit['sector32_raw_fits_review']['passed']
    datasets = json.loads((out/'datasets.json').read_text())
    contexts = json.loads((out/'contexts.json').read_text())
    text = ['# LS7I input preparation: both closed TESS sectors are ready', '',
            '**Input restoration and independent checks pass. The new background model has not yet been evaluated.**', '',
            'The first work block of the [two-week plan](../TWO_WEEK_PLAN_2026-09-14.md) is complete: '
            'sector 32 has been restored from its original identity-pinned TESS products; sector 29 reuses its sealed LS7G cutouts. '
            'The common input index accounts for all **6,720 historical trial rows**, with full spatial/temporal injection recipes '
            'and original archive links. These reuse **20 background contexts**, with **8,020 individual cadences** in their cutouts. '
            'They are not independent trials or new observing coverage.', '',
            '| Closed TESS sector | Backgrounds × cadences | Aperture pixels | Historical trial rows | Models linked | Training vectors checked |',
            '|---|---:|---:|---:|---:|---:|']
    for ds in datasets:
        sector = str(ds['sector']); counts = audit['sectors'][sector]
        text.append(f'| {sector} | 10 × 401 | {ds["aperture_pixels"]} | {counts["trials"]:,} | {counts["model_links"]} | {counts["training_vectors"]} |')
    text += ['', '## Trial suites and the remaining design gap', '',
             '| Common suite | Sector 29 | Sector 32 |', '|---|---:|---:|']
    for suite in ['base', 'sparse_stress', 'known_extended', 'unmodeled_shapes', 'bounded_pointing']:
        text.append(f'| {suite} | {summary["suite_counts"]["29"].get(suite, 0)} | {summary["suite_counts"]["32"].get(suite, 0)} |')
    text += ['', 'Sector 32 has no historical cross/ring/triangle control suite corresponding to LS7G’s 360 omitted-shape rows. '
             'The upcoming model protocol must decide the corresponding fixed supplement before evaluating its outcomes. '
             'No supplement is generated here, and neither historical denominator changes.', '',
             '## What was verified', '',
             '- Both original sector-32 FITS product hashes and byte counts match. The original eligibility and all ten anchor indices reproduce.',
             '- An independent FITS reader restores cosmic-ray correction records using cadence and detector coordinates. It checks all 4,010 full-stamp context samples and the ten original run-flux arrays against the export, exactly.',
             '- Sector 29 remains byte-identical to its existing published cutout file. Its original FITS/eligibility audit is retained by hash; no second copy or download is required.',
             '- All 6,720 injection recipes reproduce the saved event vectors and both injected/native temporal selections. The audit uses independent pulse integration and scalar window enumeration.',
             '- All 300 archived training vectors reproduce from the individual cadences; every case has an original row, model and context link. Sector prefixes prevent historical trial-ID collisions.',
             '- Residual stress remains in its parent’s window even when the altered trial selects another window. Physical pointing remains at its original unamplified multiplier.',
             '- Three analytical tests cover parent-window stress, fixed-flux/null amplitudes and complete sector-qualified identity/order. Historical spatial fits and covariance audits are reused by hash; there is no new fitting or qualification pass.', '',
             '| Sector | Maximum event-vector error (e⁻/s per pixel) | Maximum temporal-score error | Maximum normalized training-vector error |',
             '|---|---:|---:|---:|']
    for sector in ['29', '32']:
        error = audit['maximum_errors'][sector]
        text.append(f'| {sector} | {error["event_vector"]:.6g} | {error["temporal_score"]:.6g} | {error["training_vector"]:.6g} |')
    text += ['', '## Input contract for the next model', '',
             '`datasets.json` identifies each context file and original ledger by SHA-256. Paths are relative to the repository root. '
             'Sector 29 points to `results_ls7g_transfer/backgrounds.npz`; sector 32 points to this package’s `sector32.npz`. '
             'Both use the same array names: `native`, `seconds`, `sigmas`, `aperture`, `anchors`, `anchor_btjd`, '
             '`context_cadence`, `context_quality`, and the per-anchor original run flux/bounds. ', '',
             '`contexts.json` provides the chronology and global context IDs. `trial_recipes.jsonl.gz` and `patterns.json` '
             'reconstruct each historical injected cube, including its residual pixel. The original fit outcomes and '
             'event vectors remain in the linked, unchanged historical ledgers.', '',
             '**The recipe files contain injection truth.** They belong in the evaluation harness. A new detector must '
             'receive only the observable input allowed by its frozen inference protocol, not the case kind, true '
             'native realization beneath a pulse, injection amplitude or clean target vector. This input-preparation '
             'freeze is not the upcoming model’s scientific freeze.', '',
             '## Restored contexts', '',
             '| Context | Native row index | Anchor BTJD | First cadence | Last cadence |', '|---|---:|---:|---:|---:|']
    for c in contexts:
        text.append(f'| {c["context_id"]} | {c["native_index"]} | {c["btjd"]:.9f} | {c["first_cadence"]} | {c["last_cadence"]} |')
    text += ['', '## Next action', '',
             'Implement the one primary time-dependent background/residual model with a protected event interval and '
             'training exclusions. Test whether surrounding cadences predict the problematic component while preserving '
             'pulses, including an unpredictable-noise known-answer case. Fix the joint two-sector evaluation and any '
             'missing control supplement before running it. No new sector, threshold sweep or model adoption follows '
             'from successful input restoration.', '',
             'All LS7G/LS7H detector failures remain unchanged. This stage produces no candidate, sensitivity limit or '
             'additional observing coverage. The dates in the two-week plan are work windows; input work started when '
             'the owner asked to start, without waiting for a calendar boundary.', '',
             f'Source freeze: `{summary["freeze_commit"]}`. GitHub run: '
             f'[restoration and independent audit](https://github.com/andersenmartin-blip/setisearch/actions/runs/{summary["github_run_id"]}).', '',
             '- [Input protocol](../LS7I_INPUT_PROTOCOL.md), [configuration](../config/ls7i_inputs.json), [source hashes](../LS7I_INPUT_FREEZE.sha256)',
             '- [Dataset identities](datasets.json), [context index](contexts.json), [sector-32 cutouts](sector32.npz), [original source identities](sector32_source.json)',
             '- [Trial recipes](trial_recipes.jsonl.gz), [patterns](patterns.json), [summary](summary.json), [independent audit](AUDIT.json), [output hashes](SHA256SUMS)',
             '- [Current status](../PROJECT_STATUS.md), [continuation](../LS7I_CONTINUATION.md)', '']
    (out/'REPORT.md').write_text('\n'.join(text))
    if args.update_status:
        short = ('The two-week plan has started. Both closed TESS sectors now have verified individual-cadence inputs. '
                 'All **6,720 historical trial recipes** and **300 training vectors** reproduce from **20 background contexts**. '
                 'The independent sector-32 FITS restoration check passes exactly; sector 29 reuses its sealed LS7G cutouts. '
                 'This completes input preparation, not evaluation of the new model.')
        continuation = '# LS7I continuation\n\nInput preparation completed, 13 September 2026.\n\n'+short+'\n\n'
        continuation += ('Next implement and freeze the integrated time-dependent background/residual study from '
                         '[the two-week plan](TWO_WEEK_PLAN_2026-09-14.md). Keep both closed sectors in the joint evaluation. '
                         'Sector 32 lacks the 360 historical cross/ring/triangle cases present in sector 29; declare any '
                         'supplement separately before its evaluation. The input freeze does not specify or approve a new '
                         'detector rule. Preserve LS7G/LS7H outcomes and the original denominators.\n\n'
                         'Use `results_ls7i_inputs/datasets.json` as the entry point. Each dataset records its context path '
                         'and source-ledger hash. The common recipes are truth-labelled evaluation data; do not pass their '
                         'labels, amplitudes or known native realization into inference. Both sectors retain their original '
                         '18/21-pixel apertures and ten contexts. No further FITS download is needed for model development.\n\n'
                         '[Input report and exact interface](results_ls7i_inputs/REPORT.md), '
                         '[independent audit](results_ls7i_inputs/AUDIT.json), '
                         '[restoration protocol](LS7I_INPUT_PROTOCOL.md).\n\n'
                         '```sh\nsha256sum -c LS7I_INPUT_FREEZE.sha256\n'
                         '(cd results_ls7i_inputs && sha256sum -c SHA256SUMS)\n'
                         'OPENBLAS_NUM_THREADS=1 python scripts/ls7i_review_inputs.py\n```\n\n'
                         'The derived-only audit command above does not overwrite the sealed raw-FITS audit. '
                         'To repeat the complete raw-source audit, use the protocol with its original input files in a cache. '
                         'Original spatial-fit audits are reused by hash; no detector challenge is rerun here.\n\n'
                         f'Published input freeze: `{summary["freeze_commit"]}`. '
                         f'[Complete GitHub job](https://github.com/andersenmartin-blip/setisearch/actions/runs/{summary["github_run_id"]}). '
                         'The model stage remains pending. PROJECT_STATUS.md is the maintained operational entry point.\n')
        (ROOT/'LS7I_CONTINUATION.md').write_text(continuation)
        p = ROOT/'PROJECT_STATUS.md'; status = p.read_text()
        lo, hi = status.index('## LS7I input preparation queued'), status.index('## LS7H completed:')
        section = '## LS7I input preparation completed: two-sector model work can begin\n\n'+short+'\n\n'
        section += ('Next implement the one background/residual model and its protected event/training rules. Freeze the '
                    'joint two-sector comparison, including any explicitly separate missing-control supplement, before '
                    'evaluation. LS7G/LS7H remain unqualified; no new model result, observing coverage or candidate is claimed.\n\n'
                    '[Input report](results_ls7i_inputs/REPORT.md), [continuation](LS7I_CONTINUATION.md), '
                    '[two-week plan](TWO_WEEK_PLAN_2026-09-14.md).\n\n')
        p.write_text(status[:lo]+section+status[hi:])
    files = sorted(p for p in out.iterdir() if p.is_file() and p.name != 'SHA256SUMS')
    (out/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in files))
    print(f'Sealed {len(files)} input-package files after the full audit passed.')


if __name__ == '__main__':
    main()
