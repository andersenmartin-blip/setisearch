#!/usr/bin/env python3
"""Audit complete M43L checkpoints, parent oracles and the retained startup failure."""
import hashlib
import json
from pathlib import Path
from m43e_economical_bank import read_sealed
from m43l_wider_integrated import validate_batches

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43l_wider_integrated'


def audit():
    r=read_sealed(OUT/'qualification.json')
    p=ROOT/'config/m43l_wider_integrated.json';cfg=json.loads(p.read_text())
    assert hashlib.sha256(p.read_bytes()).hexdigest()==r['config_sha256']
    for name,h in cfg['pinned_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
    assert r['status']=='all-wider-integrated-real-anchors-qualified'
    for key in ('bank_sha256','factor_table_sha256','grid_sha256','numpy_version','m43i_result_sha256',
                'm43j_result_sha256','m43k_result_sha256','initial_freeze','runtime_amendment','workers'):
        assert r[key]==cfg[key],key
    prior=read_sealed(ROOT/'results_m43i_telescope_transfer/qualification.json')
    native=read_sealed(ROOT/'results_m43k_native_filters/qualification.json')
    narrow=read_sealed(ROOT/'results_m43j_exhaustive_anchors/qualification.json')
    assert prior['result_sha256']==r['m43i_result_sha256'] and native['result_sha256']==r['m43k_result_sha256']
    assert narrow['result_sha256']==r['m43j_result_sha256']
    failure=read_sealed(OUT/'initial_failure.json')
    assert failure['result_sha256']==cfg['initial_failure_sha256']
    assert failure['score_cells_evaluated']==0 and failure['telescope_source_loads']==0
    assert failure['freeze_commit']==r['initial_freeze']
    probe=json.loads((OUT/'runtime_probe.json').read_text())
    assert probe['ordinary_subprocesses']==7 and probe['initial_markers_exact'] is True and probe['file_stop_seen_by_all_children'] is True
    assert probe['socket_service_used'] is False and probe['telescope_score_cells']==0
    expected=[(a['scan'],w) for a in cfg['anchors'] for w in cfg['widths']]
    assert [(x['scan'],x['width']) for x in r['checks']]==expected and len(expected)==14
    for item in r['checks']:
        cp=read_sealed(ROOT/item['checkpoint'])
        assert cp['result_sha256']==item['checkpoint_sha256'] and cp['complete'] is True
        assert cp['freeze_commit']==r['freeze_commit'] and cp['config_sha256']==r['config_sha256']
        assert cp['scan']==item['scan'] and cp['width']==item['width']
        old=next(x for x in prior['checks'] if x['scan']==cp['scan'] and x['width']==cp['width'])
        k=next(x for x in native['checks'] if x['scan']==cp['scan'] and x['width']==cp['width'])
        a=next(a for a in cfg['anchors'] if a['scan']==cp['scan'])
        assert cp['receipt_sha256']==a['source_receipt_sha256']
        for key in ('source_identity','cache_identity','cache_payload_sha256'):assert cp[key]==old[key]==k[key],key
        assert cp['source_identity']==item['source_identity'] and cp['cache_identity']==item['cache_identity']
        assert cp['native_reference_sha256']==k['cache_payload_sha256']
        assert cp['m43k_native_reference_exact'] is True and item['m43k_native_reference_exact'] is True
        assert cp['m43i_full_vectors_exact'] is True and item['m43i_full_vectors_exact'] is True
        assert cp['m43i_overlap_sha256']==old['full_score_sha256']
        cells=validate_batches(cp['batches'],1701,32,747793)
        assert cells==cp['cells_compared']==item['cells_compared'] and item['batch_count']==54
    summary={'sources':2,'widths':[3,5,9,17,33,65,129],'source_width_checks':14,
        'complete_template_vectors':23814,'batches_completed':756,'integrated_score_cells_compared':17807942502}
    assert r['summary']==summary
    assert narrow['summary']['score_cells_compared']+summary['integrated_score_cells_compared']==20351934288
    assert r['new_remote_requests']==0
    for flag in ('candidate_selection_performed','detection_threshold_calibrated','multi_epoch_real_stack_qualified','recovery_measured'):
        assert r[flag] is False,flag
    return r,cfg


def main():
    r,cfg=audit()
    rows='\n'.join(f"| {w} | 3,402 | 108 | 2,543,991,786 | Exact |" for w in cfg['widths'])
    report=f'''# M43L — exhaustive wider integrated real scores pass

All **17,807,942,502 prescribed integrated score cells** match the independently
constructed factorized reference exactly. The complete 1,701-template bank now
spans every one of the 747,793 support carriers at widths 3,5,9,17,33,65,129 for
both first-epoch ON/OFF telescope sources at 1412.5 MHz. All 756 batches pass.

| Native width | Full-support vectors, both sources | Batches | Compared integrated cells | Reference |
| --- | --- | --- | --- | --- |
{rows}
| **Seven-width total** | **23,814** | **756** | **17,807,942,502** | **Exact** |

Together with M43J's width-one result, the complete bank/carrier integrated
score domain is covered at **all eight widths** on these two sources:
**20,351,934,288 evaluated cells** across the two milestones. This is a numerical
qualification denominator, including correlated/repeated mappings and earlier
M43I overlap. It is not an independent-trial, candidate or sensitivity count.
Every vector includes 747,665 score carriers and 64 support guards on each side.

## Independent reference path and exact lineage

Each width worker rebuilds its own native reference from explicit indexed
normalized channel windows. Production's filter and sliding-window view are not
called by that reference. Its complete valid payload digest and every native
row digest must match M43K before integrated comparisons begin. The reference
stores absolute native channel positions, including NaN invalid guards, and
shares no array storage with the production cache, which uses a half-width offset.

The reference then calculates native coordinates directly and accumulates the
selected values in ascending integration order with the frozen float32 rule.
Every integrated cell is compared to the unchanged receipt-bound M43I gather.
This factorization reuses independently calculated native values rather than
materializing the same native windows anew for each score. Unit tests establish
agreement with the original direct-window oracle at every wider width and
multiple chunk sizes. Both paths share the formula, factors and NumPy runtime;
this is numerical cross-validation, not independent scientific replication.

Every source/cache identity reproduces M43I/K. Full vectors for templates 911 and
1678, recovered from the exhaustive batches, match M43I at each source/width.
All 14 complete source/width checkpoints include the exact ordered 54-batch
inventory, including the final five-template batch. The final audit checks their
seals, ranges, counts, parent identities and reference/overlap digests.

## Disclosed startup failure and public amendment

The initial freeze `{r['initial_freeze']}` failed before submitting any numerical
jobs: Python SyncManager could not create a local listening socket
(`PermissionError: Operation not permitted`). **Zero telescope sources were
loaded and zero M43L score cells were evaluated in that attempt.** Its original
configuration, traceback and sealed failure record remain published.

The public amendment replaced the manager with seven ordinary Python child
processes, lightweight parent coordinator threads, and a cooperative stop file.
It required no socket service, permission change or sandbox escalation. A real
seven-child preflight verified initial markers and stop-file visibility. The
arithmetic, bank, source inputs and 17,807,942,502-cell endpoint stayed unchanged.
The amended freeze `{r['freeze_commit']}` preceded the successful evaluation.
No subsequent numerical mismatch occurred. Workers would stop at the next batch
boundary after a peer error; partial checkpoints are never aggregate success.

All **76 M43-family tests pass**. Four M43L tests cover direct/factorized oracle
agreement, absolute native guards, full batch/retained-vector assembly, and
rejection of malformed inventories or deliberately incorrect reference outputs.
The ordinary-process preflight is additional runtime evidence, with no spectra.

## Reproduction and saved evidence

- Amended config SHA-256: `{r['config_sha256']}`.
- M43L sealed result: `{r['result_sha256']}`.
- M43I result: `{r['m43i_result_sha256']}`.
- M43J result: `{r['m43j_result_sha256']}`.
- M43K result: `{r['m43k_result_sha256']}`.
- Fixed bank: `{r['bank_sha256']}`.
- Fixed factor table: `{r['factor_table_sha256']}`.
- NumPy: `{r['numpy_version']}`.

Source/width files were atomically checkpointed after every successful batch and
marked complete only after full coverage and ancestor-vector agreement. The final
result references all 14 completed checkpoint seals. It retains every batch digest
without publishing enormous score matrices. The manifest binds the delivered code,
protocols, failure/probe evidence, checkpoints, final report and logs. All seven
ON checkpoints were publicly saved while OFF evaluation continued, in commit
`c8526ac271118ac77f568cb5d0bffe062bf88ee4`.

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 .venv/bin/python -m unittest discover -s tests -p 'test_m43*.py'
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/m43l_runtime_probe.py
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/m43l_wider_integrated.py --work-root /path/to/m43h/live --freeze-commit {r['freeze_commit']}
PYTHONPATH=src:scripts .venv/bin/python scripts/m43l_result_report.py
sha256sum -c RESULTS_MANIFEST_M43L_WIDER_INTEGRATED.sha256
```

Reproduction needs the two M43H native/normalized source directories or their
reconstruction with the retained receipt hashes. This runner recomputes on restart;
it does not accept arbitrary self-sealed files as authority to skip checks.
Checkpoint/source/reference/output digests must reproduce. Elapsed time and the
final enclosing result seal can differ; the manifest checks published artifact bytes.

## Runtime and next scientific gate

The successful seven-process job took **{r['elapsed_seconds']:.3f} seconds** wall
time. This describes this qualification run, including independent reference work;
it is not calibrated detector throughput or a cloud-cost measurement. Seven
numerical subprocesses used the available eight-CPU quota and 20 GiB environment.
Each held one source/cache, one independent native reference and one 32-template
output. The existing 512 MiB adapter bound is per adapter and excludes reference,
caller, process and OS-cache memory; it is not a combined-job or measured RSS cap.
No new remote requests were needed. No AI agents or research delegation were used.

This closes the remaining wider integrated-score combinations for **one window
and the first ON/OFF epoch pair only**. It does not qualify other real epochs,
real multi-epoch stacking, detection thresholds or injection/recovery behavior.
The next gate is additional real epoch coverage and full stack/detection validation,
followed by newly frozen null and injection/recovery calibration. No candidates
were selected; numerical equality is neither an extraterrestrial finding nor a
scientific nondetection.
'''
    (ROOT/'MILESTONE_43L_WIDER_INTEGRATED_RESULT.md').write_text(report)
    names=['MILESTONE_43L_WIDER_INTEGRATED_PLAN.md','MILESTONE_43L_RUNTIME_AMENDMENT.md','MILESTONE_43L_WIDER_INTEGRATED_RESULT.md',
        'config/m43l_wider_integrated.json','config/m43l_wider_integrated_initial.json','scripts/m43l_reference.py',
        'scripts/m43l_wider_integrated.py','scripts/m43l_runtime_probe.py','scripts/m43l_result_report.py','tests/test_m43l_integrated.py']
    names+=sorted(str(p.relative_to(ROOT)) for p in OUT.iterdir() if p.is_file())
    (ROOT/'RESULTS_MANIFEST_M43L_WIDER_INTEGRATED.sha256').write_text(''.join(
        hashlib.sha256((ROOT/n).read_bytes()).hexdigest()+'  '+n+'\n' for n in names))
    print(json.dumps({'verified_summary':r['summary'],'manifest_entries':len(names)},indent=2))


if __name__=='__main__':main()
