#!/usr/bin/env python3
"""Audit complete M43N inventory, receipts and unchanged numerical lineage."""
import argparse
import hashlib
import json
from pathlib import Path
from m43n_epoch_scores import ROOT, OUT, CONFIG, frozen, collect, inventory
from m43e_economical_bank import read_sealed
from m43f_source_cache_preflight import build_context
from m43k_native_filters import bank_coverage
from seti_repeater import search_v0p6 as core
from seti_repeater import transfer_m43i as transfer


def audit(work_root):
    result=read_sealed(OUT/'qualification.json')
    cfg,contract=frozen(result['freeze_commit'])
    assert result['status']=='additional-epoch-scores-qualified' and result['config_sha256']==contract
    for key in ('m43m_result_sha256','bank_sha256','factor_table_sha256','grid_sha256','numpy_version','workers'):
        assert result[key]==cfg[key],key
    checks=[collect(a['scan'],w,cfg,contract,result['freeze_commit']) for a in cfg['anchors'] for w in cfg['widths']]
    assert checks==result['checks']
    assert inventory(checks,cfg)==result['summary']==cfg['expected_summary']
    _,_,_,_,basis,bank,table,_=build_context()
    grid=core.make_m37_proxy_carrier_grid(cfg['window'])
    for anchor in cfg['anchors']:
        label=anchor['scan']
        source=transfer.load_telescope_source(work_root/label/cfg['window'],trusted_receipt_sha256=anchor['source_receipt_sha256'])
        assert source.integration_count==16 and source.geometry.channel_count==1132270
        factors=core.factor_table_for_scan(table,basis,label)
        assert core.factor_table_sha256(factors)==anchor['scan_factor_sha256']
        for width in cfg['widths']:
            cp=read_sealed(OUT/f'{label}.width{width:03d}.json')
            assert cp['source_identity']==source.identity
            assert cp['native_reference_sha256']==cp['cache_payload_sha256']
            expected_identity=transfer.digest({'contract':transfer.CONTRACT_SHA256,'source':source.identity,
                'bank':cfg['bank_sha256'],'factors':anchor['scan_factor_sha256'],
                'grid':cfg['grid_sha256'],'width':width,'payload':cp['cache_payload_sha256']})
            assert cp['cache_identity']==expected_identity
            assert len(cp['native_rows'])==16
            for row,item in enumerate(cp['native_rows']):
                assert item['row']==row and item['exact'] is True
                assert item['values_compared']==source.geometry.channel_count-width+1
                core._frozen_sha256(item['sha256'],'native row')
            assert sum(x['values_compared'] for x in cp['native_rows'])==cp['native_values_compared']
            assert cp['bank_coverage']==bank_coverage(source.geometry,factors,grid,width)
        del source
    for flag in ('candidate_selection_performed','multi_epoch_real_stack_qualified','detection_threshold_calibrated','recovery_measured'):
        assert result[flag] is False
    assert result['new_remote_requests']==0
    assert not (OUT/'run_failure.json').exists(), 'failure disclosure needs review before reporting'
    probe=json.loads((OUT/'runtime_probe.json').read_text())
    assert probe['ordinary_subprocesses']==7 and probe['socket_service_used'] is False
    assert probe['initial_markers_exact'] is True and probe['file_stop_seen_by_all_children'] is True
    assert probe['telescope_score_cells']==probe['telescope_source_loads']==0
    j=read_sealed(ROOT/'results_m43j_exhaustive_anchors/qualification.json')
    l=read_sealed(ROOT/'results_m43l_wider_integrated/qualification.json')
    combined=j['summary']['score_cells_compared']+l['summary']['integrated_score_cells_compared']+result['summary']['integrated_score_cells_compared']
    assert combined==61055802864
    return result,cfg,combined


def main(work_root):
    r,cfg,combined=audit(work_root)
    rows='\n'.join(f"| {w} | {64*(1132270-w+1):,} | 216 | 5,087,983,572 | Exact |" for w in cfg['widths'])
    report=f'''# M43N — all additional-epoch native and integrated scores pass

All **40,703,868,576 prescribed integrated score cells** exactly match the
separately constructed factorized reference on the four M43M telescope
sources: epoch2_on, epoch2_off, epoch3_on and epoch3_off at **1412.5 MHz**.
Every source covers all **1,701 templates × 747,793 support carriers × eight
native filter widths**. All **1,728 batches / 54,432 full vectors** pass.
The complete valid native-filter domain also passes direct comparison:
**579,705,984 native values in 512 row/width checks**.

| Native width | Compared native values, four sources | Batches | Compared integrated cells | Reference |
| --- | --- | --- | --- | --- |
{rows}
| **Total** | **579,705,984** | **1,728** | **40,703,868,576** | **Exact** |

Together with M43J/L's unchanged first-pair results, exhaustive numerical
integrated coverage now includes **all six sources at all eight widths**:
**{combined:,} compared cells across the three milestones**. All grids include
747,665 score carriers and 64 support guards per side. The three ON/OFF pairs
are repeated scans in one observing sequence, not independent dates. These
are correlated numerical comparison counts, not independent trials, sky
candidates or measured sensitivity. No multi-epoch stack has yet been qualified.

## Numerical checks and provenance

The production path is the unchanged M43I telescope adapter: receipt-bound
source loading, native filtering, nearest-even binary64 affine mapping and
ascending-row float32 integration. The reference is unchanged M43L code,
which builds native filters from explicitly indexed channel windows and gathers
using absolute native positions. It shares the intended formula, NumPy runtime
and factors with production, while using separate indexing and array storage.
This is numerical cross-validation rather than independent scientific replication.

Before scoring, every valid native reference value is compared directly to the
production cache, including dtype; row and full payload hashes must also agree.
The M43K monotonic endpoint bound verifies that all bank mappings fit within the
audited native domain. Each 32-template batch compares every support carrier,
in 4,096-carrier chunks. The final batch has five templates. Cache identity binds
the telescope receipt, normalized payload, bank, scan factors, grid and width.
Every completed checkpoint includes 16 native row hashes and all 54 batch digests.

The public freeze `{r['freeze_commit']}` preceded numerical evaluation on these
new inputs. Source receipts come from the retained M43M result
`{r['m43m_result_sha256']}`. There are no old M43I/K score digests for these four
sources; M43N establishes their first exhaustive numerical anchors and makes
no invented overlap claim. The final audit rehydrates all four sources against
those retained receipt hashes, checks every cache identity and row count,
recomputes geometric bounds, validates all ordered batch inventories and
verifies the exact 32 completed source/width products.

All **81 M43-family tests pass**. Three new tests check all eight widths against
the original direct-window oracle on small mocked-provenance fixtures, reject
native scope/interior/digest corruption, and reject missing, duplicate or
reordered source/width inventories. These fixtures are not telescope evidence.
The additional real seven-child runtime probe verifies file-based cooperative
stops without loading telescope sources or evaluating scores.

## Execution and retained evidence

At most seven ordinary numerical subprocesses ran concurrently under the
available eight-CPU/20-GiB environment. Source/width jobs were scheduled in
descending width order and frozen source order. Each job retained one source,
one native cache, one independent reference and one 32-template output batch.
The inherited 512-MiB adapter limit excludes caller/reference/process/OS memory;
it is not a combined-job RSS measurement. No AI agents or delegation were used.
Successful wall time was **{r['elapsed_seconds']:.3f} seconds**, including source
rehydration and reference work; this is not calibrated detector throughput.

No new remote requests or telescope downloads were needed. No run failure
occurred. Native and batch checkpoints were sealed atomically, and completion
required every prescribed batch. The runner would stop peers at their next
batch boundary on an error and reject a partial inventory. It recomputes on a
rerun rather than accepting arbitrary self-sealed files as authority to skip
checks. Runtime and final enclosing seals can differ on reproduction; numerical
payload/batch/source/cache identities must reproduce. Large score matrices are
not retained; the complete batch digests, source/width checkpoints and audit are
published with a SHA-256 manifest. The first seven completed products were
publicly checkpointed during the run in commit
`c0707c545fe7d380efa057044ee5ccffcf2fa4b8`. All 28 wider-width products were
public by `461bd9e94da0967e9b5268fcad10be53d7ba8d1b`, while the final
width-one comparisons continued.

## Reproduction and next gate

- Configuration SHA-256: `{r['config_sha256']}`.
- Sealed M43N result: `{r['result_sha256']}`.
- Bank SHA-256: `{r['bank_sha256']}`.
- Factor table SHA-256: `{r['factor_table_sha256']}`.
- Support grid SHA-256: `{r['grid_sha256']}`.
- NumPy: `{r['numpy_version']}`.

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/m43n_epoch_scores.py --work-root /path/to/m43h_work/live --freeze-commit {r['freeze_commit']}
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/m43n_result_report.py --work-root /path/to/m43h_work/live
sha256sum -c RESULTS_MANIFEST_M43N_EPOCH_SCORES.sha256
```

The next gate is the real multi-epoch stack and detection logic, followed by
separately frozen null and injection/recovery calibration. M43N does not select
candidates, estimate recovery, calibrate thresholds or establish a scientific
nondetection. It supplies the fully checked per-epoch score foundation needed
for that next stage.
'''
    (ROOT/'MILESTONE_43N_EPOCH_SCORES_RESULT.md').write_text(report)
    names=['MILESTONE_43N_EPOCH_SCORES_PLAN.md','MILESTONE_43N_EPOCH_SCORES_RESULT.md',
        'config/m43n_epoch_scores.json','scripts/m43n_epoch_scores.py','scripts/m43n_result_report.py','tests/test_m43n_scores.py']
    names+=sorted(str(p.relative_to(ROOT)) for p in OUT.iterdir() if p.is_file())
    (ROOT/'RESULTS_MANIFEST_M43N_EPOCH_SCORES.sha256').write_text(''.join(
        hashlib.sha256((ROOT/name).read_bytes()).hexdigest()+'  '+name+'\n' for name in names))
    print(json.dumps({'summary':r['summary'],'combined_integrated_cells':combined,'manifest_entries':len(names),'result_sha256':r['result_sha256']},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work-root',required=True,type=Path);main(p.parse_args().work_root)
