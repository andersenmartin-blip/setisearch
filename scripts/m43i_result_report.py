#!/usr/bin/env python3
"""Audit sealed M43I outcomes and render their exact bounded scope."""
import hashlib
import json
from pathlib import Path
from m43e_economical_bank import read_sealed

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43i_telescope_transfer'


def main():
    r=read_sealed(OUT/'qualification.json')
    cfgpath=ROOT/'config/m43i_telescope_transfer.json'
    cfg=json.loads(cfgpath.read_text())
    assert hashlib.sha256(cfgpath.read_bytes()).hexdigest()==r['config_sha256']
    for path,h in cfg['pinned_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==h,path
    assert r['status']=='bounded-telescope-score-anchors-qualified'
    assert r['bank_sha256']==cfg['bank_sha256'] and r['factor_table_sha256']==cfg['factor_table_sha256']
    assert r['contract_sha256']==cfg['contract_sha256'] and r['m43h_result_sha256']==cfg['m43h_result_sha256']
    expected={(a['scan'],w) for a in cfg['anchors'] for w in cfg['widths']}
    assert {(c['scan'],c['width']) for c in r['checks']}==expected and len(r['checks'])==len(expected)
    assert len(r['sources'])==len(cfg['anchors'])==2
    for a in cfg['anchors']:
        s=next(s for s in r['sources'] if s['scan']==a['scan'])
        assert s['receipt_sha256']==a['source_receipt_sha256'] and s['rows_sort_checked']==16 and s['native_channels']==1132270
    for c in r['checks']:
        cp=read_sealed(OUT/f"{c['scan']}.width{c['width']:03d}.json")
        assert cp['check']==c and cp['freeze_commit']==r['freeze_commit'] and cp['config_sha256']==r['config_sha256']
        a=next(a for a in cfg['anchors'] if a['scan']==c['scan'])
        s=next(s for s in r['sources'] if s['scan']==c['scan'])
        assert c['source_identity']==s['source_identity']
        assert c['full_grid_template_indices']==a['full_grid_template_indices']
        assert c['bank_templates']==1701 and c['local_cells_per_template']==53 and c['support_cells_per_template']==747793
        for flag in ('local_native_window_reference_exact','full_native_window_reference_exact','chunk_invariance_exact','local_full_agreement_exact','repeat_witness_retained'):
            assert c[flag] is True
    summary={'telescope_sources':2,'normalization_rows_sort_checked':32,'bank_scan_width_local_checks':16,
             'local_score_cells_compared':1701*53*16,'full_grid_template_vectors':32,
             'full_grid_score_cells_compared':32*747793}
    assert r['summary']==summary
    assert r['new_remote_requests']==0
    for flag in ('full_bank_full_grid_search','epoch_stack_qualified_on_real_data','candidate_selection_performed','detection_threshold_calibrated','recovery_measured'):
        assert r[flag] is False
    rows='\n'.join(f"| {s['scan']} | {s['rows_sort_checked']} | `{s['receipt_sha256']}` |" for s in r['sources'])
    report=f'''# M43I — real telescope score transfer passes the prescribed anchors

The two M43H first-epoch telescope sources at 1412.5 MHz pass every M43I
numerical comparison. All 16 source/width checks match the direct native-window
reference exactly, with no numerical tolerance or endpoint amendment.

| Check | Completed scope | Result |
| --- | --- | --- |
| Native-to-normalized rows | 32 rows, each 1,132,270 native channels | Exact sorted median/MAD reference |
| Whole-bank fixed local cells | 1,701 templates × 53 carriers × 2 sources × 8 widths = **1,442,448 cells** | Exact direct-window scores |
| Selected full-support vectors | 2 templates × 747,793 carriers × 2 sources × 8 widths = **23,929,376 cells** | Exact direct-window scores |
| Gather chunk invariance | All 32 full-support vectors, chunks 4,096 versus 32,768 | Exact |
| Local/full overlap | Every prescribed overlap for the selected templates | Exact |
| Repeated native channels | Frozen collision pair for each source at all eight widths | Both proxy cells retained |

The 53 local carriers comprise 17 at each support edge, 17 at the center and
one two-carrier collision witness. Full-support templates are indices 911 and
1678, chosen from the maximum/minimum factors before evaluation. All widths
1, 3, 5, 9, 17, 33, 65 and 129 are included. Support has 747,793 carriers;
its 747,665 score carriers are surrounded by 64 guards on each side. Counts
include local/full overlap and repeated native mappings; they are evaluation
cells, not independent trials or astrophysical detections.

## Source and cache integrity

| Source | Independently sort-checked rows | Retained M43H receipt SHA-256 |
| --- | --- | --- |
{rows}

A new `TelescopeSource`/`TelescopeCache` boundary calls M43H rehydration with the
pinned telescope receipt, then rechecks every loaded normalized row. Immutable
source and cache payloads remain bound to that receipt, geometry, row order,
normalization origin, fixed bank, scan factors, complete proxy grid, filter width
and numerical contract. Telescope values never pass through the synthetic type.
The new adapter preserves M43G v2 arithmetic and mapping steps 0, 1 and 2.

The full M43-family suite passes **64 tests**, including nine new M43I tests.
They cover boundary separation, wrong-kind or altered receipts, changed row
order, dtype/shape reinterpretation, writable arrays, substituted cache metadata,
post-gate row changes, factor/coverage errors and exact all-width chunked arithmetic.
Tiny unit fixtures mock the M43H gate; the real run uses its actual receipt and
native/normalized file verification. This trust model protects reproducible local
integrity, not against a malicious runtime or authenticated-server compromise.

## Freeze, reproduction and checkpoints

- Public pre-evaluation freeze: `{r['freeze_commit']}`.
- Config file SHA-256: `{r['config_sha256']}`.
- Numerical contract: `{r['contract_sha256']}`.
- Fixed M43E bank: `{r['bank_sha256']}`.
- Fixed full factor table: `{r['factor_table_sha256']}`.
- M43H source result: `{r['m43h_result_sha256']}`.
- M43I sealed result: `{r['result_sha256']}`.
- NumPy: `{r['numpy_version']}`. Observed local run: **{r['elapsed_seconds']:.3f} seconds**;
  this is descriptive timing for the bounded qualification, not a detector benchmark.

Sixteen sealed per-source/width checkpoints accompany the final result. The
report generator audits their seals, exact configuration identity, inventory,
denominators and success flags. The result manifest binds the delivered artifacts.
No new remote requests were made; existing M43H native/normalized products were
read locally. Reproduction requires those products or reconstruction through the
published M43H source protocol, with the retained receipt hashes matching.

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 .venv/bin/python -m unittest discover -s tests -p 'test_m43*.py'
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/m43i_telescope_qualification.py --work-root /path/to/m43h/live --freeze-commit {r['freeze_commit']}
PYTHONPATH=src:scripts .venv/bin/python scripts/m43i_result_report.py
sha256sum -c RESULTS_MANIFEST_M43I_TELESCOPE_TRANSFER.sha256
```

A fresh numerical rerun may have a different elapsed time and enclosing result
seal; compare the exact source/cache/output hashes and comparison inventory.
The final manifest checks the published run's artifact bytes. The adapter retains
its 512 MiB modelled ndarray cap, excluding caller/reference arrays, OS caches
and total RSS. One source/cache is processed at a time; this bound is not a
measured process-memory claim.

## Interpretation and next work

This qualifies the specified real score anchors. It is **not a full-bank,
full-grid search**, a multi-epoch real-stack qualification, a new detection
threshold, a recovery measurement or a candidate finding. Only first-epoch ON/OFF
at one window were used. The reference has an independently implemented direct
window/access path but shares the formula, frozen factors and NumPy runtime;
exact agreement is not independent scientific replication.

The next gate should establish computationally bounded exhaustive real anchors
for the complete bank and extend source/epoch coverage before qualifying the
stack/detection endpoint. New null and injection/recovery protocols must be
frozen before their evaluation. Earlier source identities and thresholds remain
inapplicable to the widened extraction.
'''
    (ROOT/'MILESTONE_43I_TELESCOPE_TRANSFER_RESULT.md').write_text(report)
    names=['MILESTONE_43I_TELESCOPE_TRANSFER_PLAN.md','MILESTONE_43I_TELESCOPE_TRANSFER_RESULT.md',
           'config/m43i_telescope_transfer.json','src/seti_repeater/transfer_m43i.py',
           'tests/test_m43i_transfer.py','scripts/m43i_telescope_qualification.py','scripts/m43i_result_report.py']
    names+=sorted(str(p.relative_to(ROOT)) for p in OUT.iterdir() if p.is_file())
    (ROOT/'RESULTS_MANIFEST_M43I_TELESCOPE_TRANSFER.sha256').write_text(''.join(
        hashlib.sha256((ROOT/n).read_bytes()).hexdigest()+'  '+n+'\n' for n in names))
    print(json.dumps({'verified_summary':summary,'manifest_entries':len(names)},indent=2))


if __name__=='__main__':main()
