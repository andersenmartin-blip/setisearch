#!/usr/bin/env python3
"""Audit complete real-stack coverage, source ordering and parent score lineage."""
import argparse
import hashlib
import json
from pathlib import Path
from m43e_economical_bank import read_sealed
from m43o_real_stacks import ROOT,OUT,CONFIG,frozen,validate_checkpoint
from seti_repeater import transfer_m43i as transfer


def audit(work_root):
    r=read_sealed(OUT/'qualification.json');cfg,contract=frozen(r['freeze_commit'])
    assert r['status']=='real-stack-arithmetic-and-active-cut-qualified' and r['config_sha256']==contract
    for key in ('bank_sha256','factor_table_sha256','grid_sha256','numpy_version','workers'):
        assert r[key]==cfg[key]
    checks=[]
    for kind in cfg['kinds']:
        for width in cfg['widths']:
            cp=read_sealed(OUT/f'{kind}.width{width:03d}.json')
            checks.append(validate_checkpoint(cp,cfg,kind,width,r['freeze_commit'],contract))
    assert checks==r['checks']
    assert len(list(OUT.glob('*.width*.json')))==16 and not (OUT/'run_failure.json').exists()
    summary={'source_width_inputs':len(cfg['sources'])*len(cfg['widths']),
        'kind_width_checks':len(checks),'batches':sum(x['batches'] for x in checks),
        'epoch_cells_replayed':sum(x['epoch_cells_replayed'] for x in checks),
        'stack_cells_compared':sum(x['stack_cells_compared'] for x in checks),
        'raw_stack_cells':sum(x['finite_cells_by_mode']['raw'] for x in checks),
        'active3_finite_cells':sum(x['finite_cells_by_mode']['active3'] for x in checks)}
    assert summary==r['summary']
    for key,value in cfg['expected_counts'].items():assert summary[key]==value
    identities={}
    for anchor in cfg['sources']:
        source=transfer.load_telescope_source(work_root/anchor['scan']/cfg['window'],trusted_receipt_sha256=anchor['receipt_sha256'])
        assert source.integration_count==16 and source.geometry.channel_count==1132270
        identities[anchor['scan']]=source.identity
        del source
    for kind in cfg['kinds']:
        for width in cfg['widths']:
            cp=read_sealed(OUT/f'{kind}.width{width:03d}.json')
            for item in cp['sources']:assert item['source_identity']==identities[item['scan']]
    for flag in ('exclusion_masks_qualified','candidate_selection_performed','detection_threshold_calibrated','recovery_measured'):
        assert r[flag] is False
    assert r['new_remote_requests']==0
    probe=json.loads((OUT/'runtime_probe.json').read_text())
    assert probe['ordinary_subprocesses']==7 and probe['file_stop_seen_by_all_children'] is True
    assert probe['socket_service_used'] is False and probe['telescope_score_cells']==0
    return r,cfg


def main(work_root):
    r,cfg=audit(work_root)
    rows=[]
    for width in cfg['widths']:
        on=next(x for x in r['checks'] if x['kind']=='on' and x['width']==width)
        off=next(x for x in r['checks'] if x['kind']=='off' and x['width']==width)
        rows.append(f"| {width} | 10,175,967,144 | 10,175,967,144 | {on['finite_cells_by_mode']['active3']:,} | {off['finite_cells_by_mode']['active3']:,} | Exact |")
    table='\n'.join(rows)
    report=f'''# M43O — real three-epoch sum and active-cut checks pass

The unchanged sum stack now passes exhaustive comparison on the six verified
telescope sources at **1412.5 MHz**, ordered as three ON and three OFF scans.
For every one of **1,701 templates × 747,793 support carriers × eight widths**,
all four activity subsets pass both declared endpoints:

- **81,407,737,152 raw sum-stack cells**, with no minimum-active cut.
- **81,407,737,152 active-cut cells**, requiring every selected epoch to be >=3.

Together, **162,815,474,304 stack comparisons** pass across **16 kind/width
products, 864 template batches and 6,912 batch/rule records**. All raw outputs
are finite and match, so agreement cannot be explained merely by both paths
rejecting the same cells. Before stacking, every replayed per-epoch batch
reproduces its retained M43J/L/N score digest: **61,055,802,864 replayed cells**.
Those replays repeat earlier numerical work and are not independent trials.

| Native width | Raw cells, ON + OFF | Active-cut cells, ON + OFF | Finite active-cut ON cells | Finite active-cut OFF cells | Comparison |
| --- | --- | --- | --- | --- | --- |
{table}

Finite active-cut counts are numerical diagnostics. They include correlated
carriers/templates and four overlapping activity subsets, and have no candidate,
event-rate, false-alarm or discovery interpretation. No candidate selection,
exclusion masks, OFF veto or calibrated detection threshold is applied here.
The >=3 requirement is the existing M43G active rule, not a newly calibrated
search threshold. Raw uncut sums are an additional arithmetic diagnostic.

## Scope and implementation

The four subsets are **(0,1), (0,2), (1,2), (0,1,2)** in chronological order.
ON and OFF are never mixed. The three epochs are repeated scans in one
observing sequence, not independent observing dates. Every support grid includes
747,665 score carriers plus 64 guards on each side.

Production source loading, native filtering and gather use unchanged M43I code;
stacking calls unchanged `stack_hypothesis` with `stack_statistic='sum'` and
`exclusion_mask=None`. The reference independently accumulates each selected
epoch in float32, divides by float32 sqrt(active count), and accumulates the
per-epoch >=3 conditions. Both finite results and rejected -infinity values must
agree exactly in dtype and value. The implementations share the intended formula,
input scores and NumPy runtime; this is numerical cross-validation.

Each job loads three receipt-bound sources/caches. The ordered scan labels,
source/cache identities and exact prior batch hashes are checked before the
score arrays may enter the stack. All six source identities reproduce again in
the final audit. The fixed factor table, bank, support grid, ancestor artifacts,
code and source trust anchors are bound by **{len(cfg['pinned_sha256'])} pinned files**.
The final audit checks all 16 complete product seals, the exact chronological
source inventory, all 54 batches per product, all eight rules per batch,
parent score hashes, cell counts and finite-output bounds.

## Execution and checkpoint format

The public freeze `{r['freeze_commit']}` preceded telescope score evaluation.
No new telescope data requests or downloads were made. At most seven ordinary numerical
subprocesses ran concurrently, scheduled in descending width and ON/OFF order.
They used the tested cooperative file stop mechanism; no AI agents or delegation.
The successful run took **{r['elapsed_seconds']:.3f} seconds** wall time, including
source verification, cache building, score replay and stack comparisons. This
is not calibrated detector throughput or a measured combined memory cap.

Each batch holds three 32-template full-support score arrays, then compares
stacks in 4,096-carrier chunks. Chunk temporaries preserve the epoch, template
and carrier axes before flattening only the final two for the production call.
The last template batch contains five templates. Source and cache arrays remain
bound to their independently retained receipt/ancestor identities.

Every completed batch is sealed atomically, with its three parent score hashes
and eight result records. Stack digests hash a **chunk-major stream**: carrier
chunks in increasing order, and template-major float32 bytes within each chunk.
They are not full template-major vector hashes; the frozen chunk size is part
of their reproducibility contract. Finite counts are retained without storing
large stack matrices. Completed products were checkpointed locally. Automatic approval review
blocked publication of the first three complete M43O products, stating that
the standing continuation request did not specifically authorize this new
public disclosure. No completed M43O product was public during the run;
the protocol/code freeze was public before evaluation. This deviates from
the planned during-run public checkpoint schedule, not from numerical scope
or acceptance rules. Public upload was deferred for separate approval; the block and
local checkpoint history are retained in MILESTONE_43O_PUBLICATION_BLOCK.md.
No numerical run failure occurred. A failure would stop peers at the next batch boundary,
retain incomplete checkpoints and prevent an aggregate success result.

All **85 M43-family tests pass**. Four new tests cover scalar agreement at and
immediately below/above the active boundary, all subsets and both modes, multiple
chunk sizes, deliberate output corruption, swapped epochs, mixed ON/OFF,
changed payloads/dtypes and invalid rules/chunks. The seven-child runtime probe
is additional no-spectra evidence. The artifact manifest binds the delivered
protocol, code, test/probe evidence, complete checkpoints, run log and report.

## Reproduction and next gate

- Configuration SHA-256: `{r['config_sha256']}`.
- Sealed result: `{r['result_sha256']}`.
- Bank SHA-256: `{r['bank_sha256']}`.
- Factor table SHA-256: `{r['factor_table_sha256']}`.
- Support grid SHA-256: `{r['grid_sha256']}`.
- NumPy: `{r['numpy_version']}`.

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/m43o_real_stacks.py --work-root /path/to/m43h_work/live --freeze-commit {r['freeze_commit']}
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/m43o_result_report.py --work-root /path/to/m43h_work/live
sha256sum -c RESULTS_MANIFEST_M43O_REAL_STACKS.sha256
```

Reproduction needs all six M43H/M source directories and the pinned parent
checkpoints. Reruns recompute rather than trusting self-sealed files as authority
to skip evaluation. Numerical digests must reproduce; elapsed time and enclosing
result seals can differ. The manifest checks the exact published artifact bytes.

This closes the real-data **sum arithmetic and active-cut** endpoint only.
Exclusion-mask construction, event association, OFF vetoes and scramble/detection
logic remain to be qualified, followed by separately frozen null and injection/
recovery calibration. M43O establishes neither a candidate nor a scientific
nondetection and does not qualify the detector as a whole.
'''
    (ROOT/'MILESTONE_43O_REAL_STACKS_RESULT.md').write_text(report)
    names=['MILESTONE_43O_REAL_STACKS_PLAN.md','MILESTONE_43O_REAL_STACKS_RESULT.md','config/m43o_real_stacks.json',
        'scripts/m43o_real_stacks.py','scripts/m43o_stack_reference.py','scripts/m43o_result_report.py','tests/test_m43o_stacks.py',
        'MILESTONE_43O_PUBLICATION_BLOCK.md']
    names+=sorted(str(p.relative_to(ROOT)) for p in OUT.iterdir() if p.is_file())
    (ROOT/'RESULTS_MANIFEST_M43O_REAL_STACKS.sha256').write_text(''.join(
        hashlib.sha256((ROOT/p).read_bytes()).hexdigest()+'  '+p+'\n' for p in names))
    print(json.dumps({'summary':r['summary'],'manifest_entries':len(names),'result_sha256':r['result_sha256']},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work-root',required=True,type=Path);main(p.parse_args().work_root)
