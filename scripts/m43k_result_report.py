#!/usr/bin/env python3
"""Audit the frozen M43K source/width/row inventory and report its scope."""
import hashlib
import json
from pathlib import Path
from m43e_economical_bank import read_sealed

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43k_native_filters'


def audit():
    r=read_sealed(OUT/'qualification.json')
    path=ROOT/'config/m43k_native_filters.json';cfg=json.loads(path.read_text())
    assert hashlib.sha256(path.read_bytes()).hexdigest()==r['config_sha256']
    for name,h in cfg['pinned_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
    assert r['status']=='all-wider-native-filter-values-qualified'
    for key in ('bank_sha256','factor_table_sha256','grid_sha256','numpy_version','m43i_result_sha256','m43j_result_sha256'):
        assert r[key]==cfg[key],key
    prior=read_sealed(ROOT/'results_m43i_telescope_transfer/qualification.json')
    assert prior['result_sha256']==r['m43i_result_sha256']
    assert [s['scan'] for s in r['sources']]==[a['scan'] for a in cfg['anchors']]
    assert len(r['sources'])==2
    for s,a in zip(r['sources'],cfg['anchors']):
        old=next(x for x in prior['sources'] if x['scan']==s['scan'])
        assert s['source_identity']==old['source_identity']
        assert s['receipt_sha256']==a['source_receipt_sha256']==old['receipt_sha256']
        assert s['integration_rows']==16 and s['native_channels']==1132270
    expected=[(a['scan'],w) for a in cfg['anchors'] for w in cfg['widths']]
    assert [(c['scan'],c['width']) for c in r['checks']]==expected and len(expected)==14
    for c in r['checks']:
        cp=read_sealed(OUT/f"{c['scan']}.width{c['width']:03d}.json")
        assert cp['check']==c and cp['freeze_commit']==r['freeze_commit'] and cp['config_sha256']==r['config_sha256']
        s=next(s for s in r['sources'] if s['scan']==c['scan'])
        old=next(x for x in prior['checks'] if x['scan']==c['scan'] and x['width']==c['width'])
        for key in ('source_identity','cache_identity','cache_payload_sha256','local_score_sha256'):assert c[key]==old[key],key
        assert c['source_identity']==s['source_identity'] and c['m43i_cache_identity_exact'] is True and c['m43i_local_scores_exact'] is True
        h=c['width']//2;valid=1132270-2*h
        assert len(c['native_rows'])==16
        for i,row in enumerate(c['native_rows']):
            assert row['row']==i and row['native_center_start']==h and row['native_center_stop']==1132270-h
            assert row['values_compared']==valid and row['exact'] is True
            assert row['reference_sha256']==row['cache_row_sha256'] and len(row['reference_sha256'])==64
        assert c['native_values_compared']==16*valid and c['local_integrated_cells']==1701*53
        b=c['bank_coverage']
        assert b['template_integration_pairs']==1701*16 and b['all_bank_mappings_inside_audited_domain'] is True
        assert b['audited_native_start']==h and b['audited_native_stop']==1132270-h
        assert h<=b['minimum_mapped_center']<=b['maximum_mapped_center']<1132270-h
    expected_summary={'sources':2,'widths':[3,5,9,17,33,65,129],'source_width_checks':14,
        'native_row_width_checks':224,'native_values_compared':253620352,'local_integrated_cells_reproduced':1262142}
    assert r['summary']==expected_summary
    assert r['new_remote_requests']==0
    for flag in ('all_widths_full_bank_integrated_scores_evaluated','candidate_selection_performed',
                 'detection_threshold_calibrated','multi_epoch_real_stack_qualified','recovery_measured'):
        assert r[flag] is False,flag
    return r,cfg


def main():
    r,cfg=audit()
    width_rows='\n'.join(f"| {w} | {1132270-w+1:,} | {32*(1132270-w+1):,} | Exact |" for w in cfg['widths'])
    report=f'''# M43K — every wider native-filter value matches

All **253,620,352 native filter values** match the separately accessed window
reference exactly. The complete valid native-channel domain is now checked for
widths 3,5,9,17,33,65,129, in every integration of both first-epoch ON/OFF telescope
sources at 1412.5 MHz. All 14 source/width checks and 224 row/width checks pass.

| Width in native channels | Valid centers per row | Values across both sources and all 32 rows | Reference |
| --- | --- | --- | --- |
{width_rows}
| **Total** | — | **253,620,352** | **Exact** |

The separate oracle materializes integer-indexed channel windows in chunks of
2,048 centers. Production uses sliding-window views in chunks of 16,384 centers.
Both follow the frozen float32 sum, binary64 square-root divisor and float32
output rule. Every valid center, including first/last and processing boundaries,
is checked with zero tolerance. Each complete reference row digest equals the
corresponding native-cache row digest.

## Coverage and connection to previous results

All regenerated source/cache identities and payload digests equal M43I. The
full 1,701-template bank has positive finite factors, and the proxy carrier grid
is strictly increasing. Endpoint bounds under the fixed nearest-even binary64
mapping show that every interior native center lies in the audited domain at
every width, including repeated mappings. This is a monotonic coverage argument,
not an additional exhaustive integrated-score calculation.

Separately, **1,262,142 prescribed local integrated cells** reproduce M43I's
published digests exactly (1,701 templates × 53 carriers × 2 sources × 7 widths).
These checks also run the unchanged gather's source/cache integrity validation.
They reproduce earlier score evidence; they are not newly independent oracle
comparisons over the whole integrated-score domain.

| Evidence | What is exhaustive | Remaining scope limit |
| --- | --- | --- |
| M43J | All template/carrier integrated scores at width one on these two sources | One filter width, one epoch pair and one window |
| M43K | Every valid native filter value at all seven wider widths | Does not enumerate all wider integrated-score vectors |
| M43I | Full carrier grid for two selected templates at all eight widths; prescribed local carriers for the full bank | Wider integrated scores for other template/carrier combinations remain unenumerated |

These complementary checks reduce the untested numerical components. They do
not silently widen any earlier endpoint or assert that a complete calibrated
detector has passed. All three keep their original denominators and limitations.
The reference shares the formula and NumPy runtime with production, so exact
agreement is not independent scientific replication.

## Integrity, freeze and reproduction

All **72 M43-family tests pass**, including four new M43K tests. They exercise
all widths and two different oracle chunk sizes, production block halos, single
float32-ULP changes at edges and block boundaries, dtype/shape/row-order changes,
and the endpoint bound against every mapping in a small synthetic grid. The
unit inputs are explicitly synthetic; the real run uses actual M43H receipt
rehydration and independently retained source hashes.

- Public pre-evaluation freeze: `{r['freeze_commit']}`.
- Config SHA-256: `{r['config_sha256']}`.
- M43K sealed result: `{r['result_sha256']}`.
- M43I result: `{r['m43i_result_sha256']}`.
- M43J result: `{r['m43j_result_sha256']}`.
- Fixed M43E bank: `{r['bank_sha256']}`.
- Fixed factor table: `{r['factor_table_sha256']}`.
- NumPy: `{r['numpy_version']}`.

Protocol, source/reference code, exact configuration and tests were public
before the run. No endpoint amendment or failed comparison occurred. Fourteen
sealed per-source/width checkpoints accompany the complete result. This report
checks all seals, parent identities, exact row/width inventory, coverage bounds
and denominators before writing the result manifest.

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 .venv/bin/python -m unittest discover -s tests -p 'test_m43*.py'
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/m43k_native_filters.py --work-root /path/to/m43h/live --freeze-commit {r['freeze_commit']}
PYTHONPATH=src:scripts .venv/bin/python scripts/m43k_result_report.py
sha256sum -c RESULTS_MANIFEST_M43K_NATIVE_FILTERS.sha256
```

Reproduction requires the two M43H source directories, or reconstruction under
that protocol with identical retained receipt hashes. A rerun recomputes the
comparisons. Source/cache, reference-row and local-score digests must reproduce;
elapsed time and the final enclosing result seal may differ. The manifest checks
the published run's file bytes.

## Runtime and next gate

The observed job took **{r['elapsed_seconds']:.3f} seconds**, including native
cache recreation, all direct reference windows and the local score comparisons.
This is descriptive timing, not detector throughput or measured sensitivity.
No new remote requests were made. One source/cache and one reference row/chunk
are handled at a time; the inherited 512 MiB adapter-owned ndarray bound excludes
reference/caller arrays, process RSS and OS caches.

The next gate must resolve the remaining wider integrated-score qualification
and extend real source/epoch coverage before validating the full stack/detection
endpoint and running newly frozen null and injection/recovery calibration.
No candidates were ranked, no threshold was calibrated and no recovery rate was
measured. These are numerical qualification results, not an astrophysical finding
or scientific nondetection.
'''
    (ROOT/'MILESTONE_43K_NATIVE_FILTERS_RESULT.md').write_text(report)
    names=['MILESTONE_43K_NATIVE_FILTERS_PLAN.md','MILESTONE_43K_NATIVE_FILTERS_RESULT.md',
        'config/m43k_native_filters.json','scripts/m43k_native_filters.py','scripts/m43k_result_report.py','tests/test_m43k_native_filters.py']
    names+=sorted(str(p.relative_to(ROOT)) for p in OUT.iterdir() if p.is_file())
    (ROOT/'RESULTS_MANIFEST_M43K_NATIVE_FILTERS.sha256').write_text(''.join(
        hashlib.sha256((ROOT/name).read_bytes()).hexdigest()+'  '+name+'\n' for name in names))
    print(json.dumps({'verified_summary':r['summary'],'manifest_entries':len(names)},indent=2))


if __name__=='__main__':main()
