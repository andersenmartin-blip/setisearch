"""Audit the complete M43P inventory and produce a readable bounded claim."""
import json
from m43p_combined_controls import ROOT, OUT, CONFIG, sha, frozen
from m43e_economical_bank import read_sealed
from m43o_real_stacks import ancestor


def main():
    result=read_sealed(OUT/'qualification.json');cfg=frozen(result['freeze_commit'])
    parent=json.loads((ROOT/'config/m43o_real_stacks.json').read_text())
    products=[];logic=[]
    for kind in ('on','off'):
        for width in cfg['widths']:
            cp=read_sealed(OUT/f'{kind}.width{width:03d}.json');products.append(cp)
            assert cp['complete'] is True and cp['kind']==kind and cp['width']==width
            assert cp['freeze_commit']==result['freeze_commit'] and cp['config_sha256']==sha(CONFIG)
            assert [s['scan'] for s in cp['sources']]==[f'epoch{e}_{kind}' for e in (1,2,3)]
            for source in cp['sources']:
                old,spec=ancestor(parent,source['scan'],width)
                anchor=next(x for x in parent['sources'] if x['scan']==source['scan'])
                assert source['receipt_sha256']==anchor['receipt_sha256']
                assert source['ancestor_result_sha256']==spec['result_sha256']
                assert source['source_identity']==old['source_identity'] and source['cache_identity']==old['cache_identity']
                assert source['queries']==cfg['query_score_indices'][source['scan']]
                assert source['sparse_cells']==1701*9 and source['native_window_exact'] and source['full_anchor_exact']
                assert len(source['arrays'])==2
                for arr,bi in zip(source['arrays'],cfg['ancestor_batch_indices']):
                    b=old['batches'][bi]
                    assert [arr['template_start'],arr['template_stop']]==[b['template_start'],b['template_stop']]
                    assert arr['score_sha256']==b['score_sha256']
            if kind=='off':
                assert [v['subset'] for v in cp['paired_off_checks']]==parent['subsets']
                for v in cp['paired_off_checks']:
                    assert v['cells_compared']==1701*7 and 0<=v['vetoed_cells']<=v['cells_compared']
                    assert v['mask_applied'] is False
            else:assert not cp['paired_off_checks']
        item=read_sealed(OUT/f'{kind}.logic.json');logic.append(item)
        assert item['complete'] is True and item['kind']==kind and item['freeze_commit']==result['freeze_commit']
        assert item['config_sha256']==sha(CONFIG)
        assert [x['template_index'] for x in item['checks']]==[i for a,b in cfg['template_intervals'] for i in range(a,b)]
        expected_inputs={a['path']:a['score_sha256'] for cp in products if cp['kind']==kind for s in cp['sources'] for a in s['arrays']}
        assert item['input_array_hashes']==expected_inputs
        for x in item['checks']:
            assert x['reference_exact'] is True and x['mask_bits_compared']==3*cfg['support_carriers']
            assert x['masked_score_cells']==32*cfg['score_carriers']
            assert x['scrambled_score_cells']==128*cfg['score_carriers'] and len(x['null_maxima'])==4
            assert 0<=x['finite_masked_scores']<=x['masked_score_cells']
    assert result['source_product_sha256s']==[p['result_sha256'] for p in products]
    assert result['logic_product_sha256s']==[p['result_sha256'] for p in logic]
    checks=[x for p in logic for x in p['checks']]
    expected={'source_width_products':48,'anchor_templates_per_kind':37,
        'full_support_epoch_cells_replayed':37*6*8*cfg['support_carriers'],
        'all_bank_sparse_cells':1701*9*48,'mask_bits_compared':sum(x['mask_bits_compared'] for x in checks),
        'masked_stack_cells_compared':sum(x['masked_score_cells'] for x in checks),
        'scrambled_stack_cells_compared_through_maxima':sum(x['scrambled_score_cells'] for x in checks),
        'paired_off_decisions_compared':1701*7*4*8}
    assert result['summary']==expected
    tests=(OUT/'unit_tests.txt').read_text()
    assert 'Ran 158 tests' in tests and tests.rstrip().endswith('OK')
    def num(k):return f'{expected[k]:,}'
    report=f'''# M43P — combined component controls pass

The missing sparse M43I score adapter now handles repeated native-channel
mappings, arbitrary score-index order and duplicate requests. Its direct
paired-OFF rule retains the inclusive 5.5 floor, active epochs only, exact
q/template/width, and no mask or frequency neighborhood. The unchanged M37
adapter still rejects noninjective mappings; no old attestation is bypassed.

This run combines source/score transfer, full-support mask construction,
masked sums, scramble wiring and paired-OFF decisions. All declared numerical
comparisons pass. **158 tests pass**, including six new boundary/adversarial
tests and inherited retention, OFF-track association, adjacent-OFF, alias,
rank-significance and sparse physical-disposition fixtures.

| Check | Evaluated scope | Result |
| --- | --- | --- |
| Independent sparse native-window reference | {num('all_bank_sparse_cells')} cells; all 1,701 templates, six sources, eight widths, nine queries/source | Exact |
| Full-support ancestor replay | {num('full_support_epoch_cells_replayed')} per-epoch cells; templates 0–31 and 1696–1700 | Prior M43J/L/N batch hashes reproduce |
| Width-OR masks and clipped dilation | {num('mask_bits_compared')} Boolean cells | Exact |
| Masked sum and active>=3 outputs | {num('masked_stack_cells_compared')} cells; both ON and OFF | Exact |
| Four scramble maxima per template/kind | {num('scrambled_stack_cells_compared_through_maxima')} underlying stack cells; 296 maxima | Exact maxima and inventory counts |
| Paired-OFF active-subset decision | {num('paired_off_decisions_compared')} Boolean decisions | Exact scalar-rule agreement |

The sparse queries are fixed from geometry, including six literal repeated-
channel witnesses, before reading scores. Duplicated requests count as
repeated numerical checks, not independent trials. The seven common queries
provide paired-OFF comparisons; the two source-specific collision queries
are not mixed across epochs. All 48 source/width inputs reproduce independently
retained source and cache identities.

## What is now checked

For each of 37 fixed template anchors and both scan kinds, every support
carrier is included at all eight widths. The first pass combines isolated-
epoch flags across widths. A separate reference uses explicit other-epoch
comparisons and prefix interval counts, independent of production sorting and
offset-OR dilation. Masks are built over all 747,793 support carriers, then
cropped to 747,665 score carriers. This preserves edge neighborhoods.

Every masked score is compared directly for the four inherited subsets.
Scramble validation checks the correct rotation direction, wrap domain and
the movement of each mask with its own epoch scores. Independent modular
indexing/reference sums produce the same maxima as `update_calibration`.
The scramble endpoint compares **maxima**, not every individual scrambled
score; the table states the underlying evaluated cell count accordingly.
The four rows are deterministic wiring controls, not a null ensemble used
for statistical inference. Each accumulator has an explicitly separate
one-template diagnostic identity; no full-bank calibration is certified.

## Execution and reproducibility

Public protocol/code freeze: `{result['freeze_commit']}`.
Configuration: `{result['config_sha256']}`.
Sealed result: `{result['result_sha256']}`.
The configuration pins {len(cfg['pinned_sha256'])} files. NumPy {cfg['numpy_version']}.
Runtime: **{result['wall_seconds']:.3f} seconds** wall time for the combined
real-data run. Seven ordinary source workers and two logic workers, with
cooperative stop boundaries. **Zero new telescope requests/downloads.**
All 16 kind/width source checkpoints and both 37-template logic checkpoints
are complete. Checkpoints and the full run log are retained in the result
directory. Large disposable anchor arrays stay outside git; their full
payload hashes are retained and reproduce earlier public batch identities.
Reproduction recomputes them from the six verified source directories.

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/m43p_combined_controls.py --freeze-commit {result['freeze_commit']} --work-root /path/to/new-empty-work-directory --source-root /path/to/m43h_work/live
PYTHONPATH=src:scripts .venv/bin/python scripts/m43p_result_report.py
sha256sum -c RESULTS_MANIFEST_M43P_COMBINED_CONTROLS.sha256
```

## Scientific boundary and next work

These are numerical/component results in one window, using repeated scans
in one observing sequence. The 37 full-support anchors are a fixed sample
of the 1,701-template bank; they do not qualify all template-specific masks.
Passing the inherited synthetic event/physical-veto tests does not establish
the final M43 pipeline. The new paired-OFF adapter has not yet been connected
to a bank-bound final retention/evidence entry point. No new threshold,
false-alarm rate, native injection/recovery curve, candidate or scientific
nondetection is claimed. Synthetic injected scores in unit tests are logic
fixtures, not a measured sensitivity experiment.

Next: integrate the already qualified source, mask, stack and sparse-OFF
components into one explicit M43 detector contract, preserving track
association and provenance. Then freeze a combined null and native-injection
calibration. Reuse M43J/L/N/O/P evidence where it applies; avoid another
unmotivated census of unchanged arithmetic. All older results and denominators
remain intact.
'''
    path=ROOT/'MILESTONE_43P_COMBINED_CONTROLS_RESULT.md';path.write_text(report)
    files=[ROOT/'MILESTONE_43P_COMBINED_CONTROLS_PLAN.md',path,CONFIG,
           ROOT/'src/seti_repeater/adjacent_m43p.py',ROOT/'tests/test_m43p_controls.py']
    files+=sorted((ROOT/'scripts').glob('m43p_*.py'))
    files+=sorted(p for p in OUT.iterdir() if p.is_file())
    (ROOT/'RESULTS_MANIFEST_M43P_COMBINED_CONTROLS.sha256').write_text(''.join(
        f'{sha(p)}  {p.relative_to(ROOT).as_posix()}\n' for p in sorted(set(files))))
    print(json.dumps({'audit':'pass','summary':expected,'manifest_files':len(set(files)),'report':str(path)},indent=2))


if __name__=='__main__':main()
