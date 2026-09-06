#!/usr/bin/env python3
"""Structural audit and readable report of completed frozen M43G qualification."""
from pathlib import Path
import hashlib
import json
from m43e_economical_bank import read_sealed
from m43f_source_cache_preflight import build_context
from seti_repeater import search_v0p6 as core
from seti_repeater import transfer_m43g as transfer

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43g_synthetic_transfer'
FREEZE='3d3123b5ae1c1ed861b93c8f55a0b08c204bd29b'


def main():
    result=read_sealed(OUT/'qualification.json')
    cfgpath=ROOT/'config/m43g_synthetic_transfer.json'
    cfg=json.loads(cfgpath.read_text())
    assert result['config_sha256']==hashlib.sha256(cfgpath.read_bytes()).hexdigest()
    for path,h in cfg['pinned_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==h,path
    _,_,_,metadata,basis,bank,table,_=build_context()
    preflight=read_sealed(ROOT/'results_m43f_source_cache_preflight/preflight.json')
    assert result['m43f_result_sha256']==preflight['result_sha256']
    assert result['bank_sha256']==core.template_bank_sha256(bank)
    assert result['factor_table_sha256']==table.factor_table_sha256
    assert result['contract_sha256']==transfer.CONTRACT_SHA256
    scans=[s['label'] for s in metadata['scans']]
    expected={(w,s) for w in core.M37_WINDOW_IDS for s in scans}
    norms=result['normalization']; caches=result['cache_checks']; full=result['full_grid_checks']; stacks=result['stack_checks']
    assert len(norms)==30 and {(r['window'],r['scan']) for r in norms}==expected
    assert len(caches)==240 and {(r['window'],r['scan'],r['width']) for r in caches}=={(*p,w) for p in expected for w in core.M37_SPECTRAL_WIDTHS}
    assert len(stacks)==320 and {(r['window'],r['width'],r['kind'],tuple(r['subset'])) for r in stacks}=={(w,x,k,a) for w in core.M37_WINDOW_IDS for x in core.M37_SPECTRAL_WIDTHS for k in ('on','off') for a in core.M37_ACTIVITY_SUBSETS}
    assert len(full)==12 and {(r['window'],r['scan'],r['width']) for r in full}=={(cfg['full_grid_window'],s,w) for s in scans for w in cfg['full_grid_widths']}
    windows={w['window_id']:w for w in preflight['windows']}
    for row in norms:
        n=windows[row['window']]['proposed_interval'][1]-windows[row['window']]['proposed_interval'][0]
        assert row['row_count']==16 and row['native_channels']==n
        assert row['adapter_ndarray_bound_bytes']==transfer.memory_bound(16,n)
        assert row['adapter_ndarray_bound_bytes']<transfer.CONTRACT['memory_cap_bytes']
    for row in caches:
        assert row['templates']==1701 and row['local_carrier_cells_per_template']==53
        assert row['native_window_reference_exact'] is True
    import numpy as np
    for row in full:
        matrix=core.factor_table_for_scan(table,basis,row['scan'])
        wanted=sorted(set((int(np.unravel_index(matrix.argmin(),matrix.shape)[0]),int(np.unravel_index(matrix.argmax(),matrix.shape)[0]))))
        assert row['template_indices']==wanted and row['carrier_cells_per_template']==747793
        for flag in ('chunk_invariance_exact','native_window_reference_exact','local_full_agreement_exact'):assert row[flag] is True
    for row in stacks:
        assert row['cells']==1701*51 and 0<=row['finite_cells']<=row['cells'] and row['reference_exact'] is True
    expected_summary={'synthetic_scan_window_sources':30,'normalization_rows_sort_checked':480,
        'bank_scan_width_local_checks':240,'local_score_cells_compared':240*1701*53,
        'full_grid_template_vectors':24,'full_grid_score_cells_compared':24*747793,
        'stack_vectors_checked':320,'stack_cells_compared':320*1701*51}
    assert result['summary']==expected_summary
    assert result['status']=='synthetic-numerical-transfer-qualified'
    assert result['telescope_requests']==result['telescope_spectral_reads']==0
    for flag in ('detection_threshold_calibrated','production_source_attested','measured_recovery'):assert result[flag] is False
    audit={'result_sha256':result['result_sha256'],'frozen_files_verified':len(cfg['pinned_sha256']),
           'source_inventory_exact':True,'cache_inventory_exact':True,'full_grid_selection_exact':True,
           'stack_inventory_exact':True,'denominators_recomputed':expected_summary,
           'audit_scope':'sealed identities and complete structural inventory; numerical comparisons executed in frozen primary run'}
    (OUT/'verification.json').write_bytes(core.canonical_json_bytes(audit))
    low=min(r['adapter_ndarray_bound_bytes'] for r in norms)/1024**2
    high=max(r['adapter_ndarray_bound_bytes'] for r in norms)/1024**2
    finite=sum(r['finite_cells'] for r in stacks)
    lines=['# M43G: synthetic numerical transfer qualification','',
        '**The separately frozen numerical adapter passes every prescribed synthetic comparison.**','',
        'The separately named adapter normalizes and natively filters full-size synthetic sources, then gathers the fixed M43E tracks using the wider M43F geometries and repeat-permitting channel mapping. The legacy M37 source factory and detector remain unchanged. This closes the numerical prerequisite; it does not attest a widened telescope source or validate detection sensitivity.','',
        '## Integrity failure and public repair','',
        'The initial freeze `0165b67ec77992ac291d7d49914165dc24bec574` failed an additional adversarial fixture: an immutable float32 cache reinterpreted as uint32 retained the same byte hash but produced incorrect scores. The initial full-size run was interrupted. Its sealed counterexample and partial progress log remain published. Version 2 checks dtype, shape and layout and revalidates source metadata/payload before use. Its regression test covers same-byte reinterpretation/reshaping and altered source geometry. The amended contract was public before the completed rerun; all seeds and numerical selections stayed fixed. This is an implementation repair, not a passed initial gate or independent fresh confirmation.','',
        '## What was checked','',
        '| Comparison | Exact scope | Result |','|---|---|---|',
        '| Normalization vs independent sorted median/MAD | 30 full-size synthetic scan/window sources; 480 complete integration rows | Bit-for-bit equal |',
        '| Native filtering and integration vs direct per-center native windows | All 1,701 templates, 30 scan/window pairs, 8 widths, 53 prescribed carrier cells each | 21,636,720 score cells equal |',
        '| Complete support-grid comparison | 1412.5 MHz, all 6 scans, widths 1 and 129, minimum- and maximum-factor templates | 24 vectors / 17,947,032 score cells equal |',
        '| Gather chunk invariance and local/full agreement | Same complete vectors; chunks 4096 and 32768; common local slices | Bit-for-bit equal |',
        '| ON/OFF epoch-stack arithmetic and active >=3 cut | All windows/widths, 4 activity subsets, all templates, 51 common diagnostic carriers | 320 vectors / 27,760,320 cells equal |','',
        'All 44 M43-family development tests pass, including 11 new adapter tests. These cover nearest-even ties, repeat preservation, chunk boundaries/halos, terminal normalization blocks, archive orientation, legacy injective-domain agreement, altered identities/payloads and fail-closed input, coverage and capacity checks. No full repository test run is claimed.','',
        'The local carrier selection is fixed: 17 at each support end, 17 at its center, and the 2 carriers in each previously published M43F collision witness. The full-grid templates are selected by the first minimum and maximum in each fixed scan factor matrix. They are diagnostic extremes, not random or independent signal trials. The complete grid is exhausted only for those selected templates, one window and two widths. The 1,701-template bank is checked locally across all windows/widths; this is not a full-bank exhaustive search.','',
        '## Numerical and source changes','',
        'Descending input rows reverse before normalization. Every 4096-channel normalization block starts from the ascending zero of the new, wider extraction. Native filters retain their full windows across filter chunks. Nearest-even mapping permits steps 0, 1 and 2 while preserving every proxy carrier. Integration uses the original ascending row order and float32 arithmetic. No deduplication, interpolation, carrier exclusion or repeat reweighting is applied.','',
        'The new source and cache identities bind the numerical contract, extraction geometry/scope, raw and normalized synthetic payloads, bank, factors, grid and filtered payload. Payloads are immutable and changed metadata/payloads are rejected. The adapter accepts only explicitly synthetic source scope; a hash does not convert synthetic data or an arbitrary row callback into attested telescope data.','',
        f'The conservative adapter-owned ndarray bound for one source plus a width cache is {low:.2f}–{high:.2f} MiB before the separately checked gather output/mapping allowance, below the new 512 MiB cap. This is static allocation accounting, not a measured process-RSS ceiling. It excludes caller-held matrices/previous caches, transport and OS caches. Production transport needs separate accounting and validation.','',
        '## Interpretation and next step','',
        'The oracle uses full sorting for normalization and independently constructs each requested native filter window for scores. It shares the fixed mathematics, input factors and NumPy arithmetic with the adapter, so this is numerical cross-checking, not an independent scientific replication. Synthetic Gaussian arrays are arithmetic fixtures, not a validated null model. The active-epoch cut in the stack comparison is an arithmetic exercise; it is not a newly calibrated detection threshold.','',
        'Repeated native channels introduce correlations that must remain in later null calibration. No telescope spectra were read, no recovery rate was measured, no old threshold was transferred and no technosignature inference follows. M43E remains a geometric qualification; M43F remains the published incompatibility of the old adapter.','',
        'Next: implement and qualify the separately attested widened telescope extractor/source factory, including remote identity, exact extraction ancestry, new normalization scope, restartable payloads and bounded transport memory. Then run predetermined exhaustive real-data anchors and renewed null calibration before interpreting new-bank detections.','',
        '## Reproduction and audit','',
        f'Public freeze: `{FREEZE}`, verified before the full-size synthetic evaluation. Result identity: `{result["result_sha256"]}`. Numerical contract: `{result["contract_sha256"]}`. The manifest identifies the plan, configuration, implementation, oracle, tests and derived results.','',
        'The primary executable requires exact equality and aborts at the first discrepancy. Its sealed inventories record every source, width and full-grid/stack comparison. The separate result audit rechecks pinned inputs, bank/factor ancestry, complete inventory coverage, extremum-template selection, memory bounds and denominators. It does not rerun all numerical comparisons or claim a second full numerical replay.','',
        '```bash',
        "PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python -m unittest discover -s tests -p 'test_m43*.py' -q",
        'PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43g_synthetic_qualification.py',
        'PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43g_result_report.py','```','']
    (ROOT/'MILESTONE_43G_SYNTHETIC_TRANSFER_RESULT.md').write_text('\n'.join(lines))
    print(json.dumps({'result_sha256':result['result_sha256'],**expected_summary,'adapter_bound_mib':[low,high],'finite_diagnostic_stack_cells':finite},indent=2))


if __name__=='__main__':main()
