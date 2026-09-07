"""Render the completed, verified M43T neighbor9 evidence without tuning it."""
import json
from pathlib import Path
from m43e_economical_bank import read_sealed

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_m43t_mask_comparison'


def main():
    r = read_sealed(OUT / 'result.json')
    v = read_sealed(OUT / 'artifact_validation.json')
    assert v['complete'] and v['result_sha256_verified'] == r['result_sha256']
    table = ['| Profile | Added strength | Legacy retained / physical / recovered | Neighbor9 retained / physical / recovered |',
             '|---|---:|---:|---:|']
    for row in r['summary']:
        if row['mask_policy'] != 'legacy':
            continue
        other = next(x for x in r['summary'] if x['mask_policy'] == 'neighbor9' and x['profile'] == row['profile'] and x['strength'] == row['strength'])
        fmt = lambda x: ' / '.join(str(x[k]) for k in ('retained', 'passes_physical_vetoes', 'recovered'))
        table.append(f"| {row['profile']} | {row['strength']} | {fmt(row)} | {fmt(other)} |")
    null_table = ['| Policy | Training maximum (128) | Threshold | Held-out maximum (128) | Held-out >= threshold |', '|---|---:|---:|---:|---:|']
    for policy, h in r['heldout'].items():
        null_table.append(f"| {policy} | {v['null_checks'][policy]['training_maximum']:.6f} | {h['threshold']:.6f} | {h['maximum']:.6f} | {h['at_or_above_threshold']}/128 |")
    changes = ['| Truth index | Profile | Strength | Change |', '|---:|---|---:|---|']
    for kind in ('gains', 'losses'):
        for x in v['paired_' + kind]:
            changes.append(f"| {x['truth_index']} | {x['profile']} | {x['strength']} | {kind[:-1]} |")
    if len(changes) == 2:
        changes.append('| — | — | — | No paired recovery changes |')
    strong = ['| Previously missed truth | Legacy at 32 | Neighbor9 at 32 |', '|---:|---|---|']
    for i in (1, 5, 9, 13):
        vals = [next(e['recovered'] for e in r['endpoints'] if e['mask_policy'] == p and e['truth']['truth_index'] == i and e['nominal_total_epoch_strength'] == 32) for p in ('legacy', 'neighbor9')]
        strong.append(f'| {i} | {vals[0]} | {vals[1]} |')
    reversal_text = '; '.join(f"{x['policy']} truth {x['truth_index']}: {x['lower_strength']} -> {x['higher_strength']}" for x in v['adjacent_strength_reversals']) or 'None'
    gate_text = '\n'.join(f"- {k.replace('_', ' ')}: **{value}**." for k, value in v['development_gate_conditions'].items())
    mirrors = [read_sealed(OUT / f'mirror_restore.epoch{e}_{k}.json') for e in (1, 2, 3) for k in ('on', 'off')]
    segment_count = sum(len(x['segments']) for x in mirrors)
    segment_bytes = sum(s['stop'] - s['start'] for x in mirrors for s in x['segments'])
    report = f'''# M43T neighbor9: paired isolation-mask comparison

The saved nine-bin support alternative produces **{len(v['paired_gains'])} paired recovery gains and {len(v['paired_losses'])} losses** across 64 distinct nonzero injected inputs. Both policies were executed on every input under their own prospectively frozen calibration. The predeclared development gate is **{'passed' if v['development_gate_passed'] else 'not passed'}**. General adoption remains unqualified; no astronomical candidate is claimed.

This is the `neighbor9` experiment on `m43-support-qualification`. The separate [M43T neighbor2 result](https://github.com/andersenmartin-blip/setisearch/blob/m43t-neighbor-mask/MILESTONE_43T_NEIGHBOR_MASK_RESULT.md) uses a different support radius and narrower signal-strength panel. Its original history is preserved. See [branch and continuation scope](MILESTONE_43T_BRANCH_SCOPE.md). The neighbor2 results were read after this saved plan was publicly frozen and before this numerical evaluation; no parameter was changed. Neither study is blind validation or a radius optimization study.

## Recovery and failure stages

Every row below has **eight truth endpoints per policy**. The three counts separate retention, passage through physical vetoes, and final rank-qualified recovery. Strength denotes added profile power, not measured recovered SNR.

{chr(10).join(table)}

There are 160 endpoints: 128 nonzero endpoints from 64 input pairs and 32 explicitly reused zero-level endpoints from two unmodified-background executions. The baseline reuses are not independent noise trials. The ledger contains {v['nonzero_member_decisions']:,} compact nonzero-trial member decisions.

{chr(10).join(changes)}

All four previously missed strongest combined-profile cases are shown explicitly:

{chr(10).join(strong)}

Adjacent tested-strength recovery reversals: **{reversal_text}**. The original M43S results are unchanged. New legacy recovery differs from M43S at **{len(r['legacy_differences_from_m43s'])} shared endpoints**; the full difference list is in `result.json`.

## Calibration and development decision

{chr(10).join(null_table)}

Both thresholds were sealed before either held-out or injected evaluation. There are 256 unique new shift rows relative to M43R, with the same 128 training and 128 held-out rows used for both arms: 512 arm-specific maxima, not 512 independent realizations. The shift inventory also has zero overlap with the separate neighbor2 experiment. All shifts still use one observing sequence. Masks are formed on the unmodified full-support baseline, cropped, then co-rolled with scores; masks are not regenerated after scrambling. These conditional, correlated pre-veto maxima do not measure physical false-alarm probability.

All 74 cropped baseline masks are exactly zero in each policy: **{all(x['baseline_all_74_cropped_masks_zero'] for x in v['null_checks'].values())}**. Consequently this background does not directly measure the change in rejection of strong interference. Equal or small held-out exceedance counts do not establish general interference safety.

The prospectively specified development conditions are:

{gate_text}

These conditions permit broader validation only. The next useful programme is a jointly frozen signal-and-interference panel at additional carrier locations, separately varying fractional placement, template offset and smearing, followed by additional observing sequences. Keep both masks' physical dispositions and threshold exceedances visible. Do not tune this completed panel or interpret known-truth recovery as general completeness.

## Scope, restoration and reproducibility

The comparison uses 37 templates, 4,097 central score carriers (about 11.6 kHz), eight widths and four activity subsets in three ON/OFF pairs from one observing sequence. It is not a full 1,701-template search. Carrier position and anchor identity remain confounded, and the combined profile does not isolate its three effects. Association requires the exact activity subset and <=20 Hz maximum center-track error at every active ON integration, followed by unchanged physical vetoes and inclusive rank p <=0.01. No detector record cap was exhausted in the completed run.

The original scratch inputs were lost before continuation. Recovery verified all {segment_count} published HTTP segments ({segment_bytes:,} accepted segment bytes in the historical indexes), then reproduced all six complete source receipt identities and all 96 full-support score-array hashes. That byte total describes the indexed historical segments; interrupted attempts and retries mean it is not total network traffic. Fresh recovery proofs and logs describe the completed download stages, while earlier interrupted attempts are retained separately. These were downloads of old observations, with no added observing coverage. The numerical experiment itself issued zero telescope requests after restoration.

The six focused tests passed in the restored runtime. Artifact validation checks all {v['frozen_dependencies_verified']} pinned dependencies, result seals, 64 full sealed trial records, 160 endpoints, paired score/overlay identities, original input hashes, summary counts and threshold diagnostics. All 64 injected score inventories also exactly match their historical M43S counterparts. The grouped numerical run took **{r['wall_seconds']:.1f} seconds**, excluding restoration. Python and NumPy remain 3.12.13 and 2.3.5, respectively; the qualified HDF5 source runtime is retained.

- Public freeze: `{r['freeze_commit']}`.
- Configuration SHA-256: `{r['config_sha256']}`.
- Result seal: `{r['result_sha256']}`.
- Compressed trial-ledger SHA-256: `{r['trial_ledger_sha256']}`.
- Uncompressed trial-ledger SHA-256: `{r['trial_ledger_uncompressed_sha256']}`.
- [Frozen plan](MILESTONE_43T_MASK_COMPARISON_PLAN.md), [complete result](results_m43t_mask_comparison/result.json), [artifact validation](results_m43t_mask_comparison/artifact_validation.json), [numerical log](results_m43t_mask_comparison/live_run.log), and [complete lossless paired ledger](results_m43t_mask_comparison/paired_trial_audits.jsonl.gz).
- [Checksum manifest](RESULTS_MANIFEST_M43T_MASK_COMPARISON.sha256) covers the complete published package. Original M43R/S artifacts are retained intact.

With verified source and anchor roots available, use a clean output location at the public freeze, then run:

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/m43t_mask_comparison.py \\
  --freeze-commit {r['freeze_commit']} \\
  --anchor-root /path/to/anchors --source-root /path/to/sources \\
  --checkpoint-root /path/to/paired-trial-checkpoints
```

Completed results are protected from overwrite. Restart checkpoints must match the public freeze, exact configuration, truths and both calibration bindings. Operational restoration helpers are published alongside their logs; they do not modify any frozen scientific dependency.
'''
    (ROOT / 'MILESTONE_43T_MASK_COMPARISON_RESULT.md').write_text(report)
    print('Wrote M43T neighbor9 result report')


if __name__ == '__main__':
    main()
