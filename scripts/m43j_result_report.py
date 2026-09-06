#!/usr/bin/env python3
"""Audit the complete frozen M43J inventory and render its limited inference."""
import hashlib
import json
from pathlib import Path
from m43e_economical_bank import read_sealed
from m43j_exhaustive_anchors import validate_inventory

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43j_exhaustive_anchors'


def audit():
    r=read_sealed(OUT/'qualification.json')
    path=ROOT/'config/m43j_exhaustive_anchors.json';cfg=json.loads(path.read_text())
    assert hashlib.sha256(path.read_bytes()).hexdigest()==r['config_sha256']
    for name,h in cfg['pinned_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
    assert r['status']=='exhaustive-width-one-real-anchors-qualified'
    for key in ('bank_sha256','factor_table_sha256','grid_sha256','numpy_version','m43i_result_sha256'):
        assert r[key]==cfg[key],key
    prior=read_sealed(ROOT/'results_m43i_telescope_transfer/qualification.json')
    assert prior['result_sha256']==r['m43i_result_sha256']
    assert len(r['sources'])==len(cfg['anchors'])==2
    assert [s['scan'] for s in r['sources']]==[a['scan'] for a in cfg['anchors']]
    cells=0
    for s,a in zip(r['sources'],cfg['anchors']):
        old_source=next(x for x in prior['sources'] if x['scan']==s['scan'])
        old_cache=next(x for x in prior['checks'] if x['scan']==s['scan'] and x['width']==1)
        assert s['receipt_sha256']==a['source_receipt_sha256']==old_source['receipt_sha256']
        assert s['source_identity']==old_source['source_identity']
        assert s['cache_identity']==old_cache['cache_identity'] and s['cache_payload_sha256']==old_cache['cache_payload_sha256']
        assert s['m43i_full_vectors_exact'] is True and s['m43i_overlap_sha256']==old_cache['full_score_sha256']
        subtotal=validate_inventory(s['batches'],count=cfg['template_count'],size=cfg['template_batch'],support=cfg['support_cells'])
        assert s['cells_compared']==subtotal;cells+=subtotal
        for b in s['batches']:
            cp=read_sealed(OUT/f"{s['scan']}.batch{b['template_start']:04d}.json")
            assert cp['check']==b and cp['scan']==s['scan']
            assert cp['freeze_commit']==r['freeze_commit'] and cp['config_sha256']==r['config_sha256']
            assert cp['source_identity']==s['source_identity'] and cp['cache_identity']==s['cache_identity']
    expected={'telescope_sources':2,'native_width':1,'templates_per_source':1701,
        'support_cells_per_template':747793,'complete_template_vectors':3402,
        'batches_completed':108,'score_cells_compared':2543991786}
    assert r['summary']==expected and cells==expected['score_cells_compared']
    assert r['new_remote_requests']==0
    for flag in ('candidate_selection_performed','detection_threshold_calibrated','multi_epoch_real_stack_qualified','all_widths_exhaustive','recovery_measured'):
        assert r[flag] is False,flag
    return r,cfg


def main():
    r,cfg=audit()
    source_rows='\n'.join(f"| {s['scan']} | 1,701 | 54 | {s['cells_compared']:,} | Exact |" for s in r['sources'])
    report=f'''# M43J — exhaustive width-one real anchors pass

All **2,543,991,786 prescribed score cells** match the direct native-window
reference exactly. At native filter width one, the complete 1,701-template bank
has now been checked across all 747,793 support carriers for both existing
first-epoch ON and OFF telescope sources at 1412.5 MHz.

| Source | Full-support templates | Batches | Compared cells | Direct reference |
| --- | --- | --- | --- | --- |
{source_rows}
| **Total** | **3,402** | **108** | **2,543,991,786** | **Exact** |

Each source's ordered inventory includes 53 full batches of 32 templates and a
final batch of five (indices 1696–1700). No template or carrier is omitted.
The support domain contains 747,665 score carriers plus 64 guard carriers on each
side. Same-native-channel mappings retain every proxy carrier. Counts include
correlated/repeated mappings and M43I overlap; they are numerical comparisons,
not independent trials, candidate counts or sensitivity measurements.

## What this establishes

M43I covered all templates only at 53 prescribed local carriers, while two
selected templates exhausted the support grid at all eight widths. M43J closes
the remaining bank/carrier combinations **at width one** for these two sources.
This isolates exhaustive channel mapping and ordered integration arithmetic.
The source, normalization, cache identity and numerical formula remain unchanged.

Both source/cache identities and payload hashes equal their M43I counterparts.
The complete vectors for indices 911 and 1678, recovered from the exhaustive
batches, reproduce each source's published M43I digest exactly. All 108 batches
match the independently implemented direct-window access path with zero tolerance.
That oracle shares the formula, factors and NumPy runtime; this is computational
cross-validation, not independent scientific replication.

All **68 M43-family unit tests pass**, including four new scheduler/inventory
checks: final partial coverage, exact retained-vector assembly, rejection of
missing/duplicate/reordered or false-success records, and deliberate oracle error.
The tiny fixtures mock M43H's gate; this real run used actual native/normalized
file rehydration with independently retained telescope receipt hashes.

## Freeze, identity and reproduction

- Public pre-evaluation freeze: `{r['freeze_commit']}`.
- Config SHA-256: `{r['config_sha256']}`.
- M43J sealed result: `{r['result_sha256']}`.
- Parent M43I result: `{r['m43i_result_sha256']}`.
- Fixed M43E bank: `{r['bank_sha256']}`.
- Fixed full factor table: `{r['factor_table_sha256']}`.
- Proxy grid: `{r['grid_sha256']}`.
- NumPy: `{r['numpy_version']}`.

The freeze preceded all M43J evaluation. No failure, amendment, score-dependent
selection or new remote request was needed. Both stored M43H source products
were verified again. The 108 sealed checkpoints identify the exact template
interval, comparison count, score digest, config, source and cache. The report
audits their seals, full ordered inventory, parent identities and counts before
creating the artifact manifest. The complete ON batch inventory was published
while OFF evaluation continued, in commit
`500a53180957de5a0f11443fec9f1bcdf919a5ae`.

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 .venv/bin/python -m unittest discover -s tests -p 'test_m43*.py'
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/m43j_exhaustive_anchors.py --work-root /path/to/m43h/live --freeze-commit {r['freeze_commit']}
PYTHONPATH=src:scripts .venv/bin/python scripts/m43j_result_report.py
sha256sum -c RESULTS_MANIFEST_M43J_EXHAUSTIVE_ANCHORS.sha256
```

Numerical reproduction needs the two M43H native/normalized source directories,
or their reconstruction under the published M43H protocol and matching receipts.
The runner recomputes on restart; it does not skip checks from self-sealed files.
Published checksums validate the published artifact bytes. A fresh run changes
elapsed timing and the final enclosing seal; source/cache, per-batch scores and
ancestor-overlap digests must remain identical.

## Runtime and limitations

The observed exhaustive run took **{r['elapsed_seconds']:.3f} seconds**. This is
a descriptive measurement of this width-one comparison job, including reference
work, not a full detector throughput or cloud-cost estimate.
The gather model for a 32-template batch is **434,394,176 bytes** (about 414 MiB),
below the adapter's 512 MiB cap. It excludes oracle/caller arrays, OS caches and
process RSS. Only one source/cache and one 32-template full-support output are
held at a time; no whole bank-by-carrier score matrix is retained.

This result does not qualify exhaustive wider-filter calculations, other
frequency windows, later epochs, the real multi-epoch stack, a detection threshold
or injection/recovery. No candidates were ranked or selected. In particular,
passing numerical equality is not evidence of an extraterrestrial signal or a
scientific nondetection. The next gate extends exhaustive width coverage and
real source/epoch coverage before the full detection and new calibration stages.
'''
    (ROOT/'MILESTONE_43J_EXHAUSTIVE_ANCHORS_RESULT.md').write_text(report)
    names=['MILESTONE_43J_EXHAUSTIVE_ANCHORS_PLAN.md','MILESTONE_43J_EXHAUSTIVE_ANCHORS_RESULT.md',
        'config/m43j_exhaustive_anchors.json','scripts/m43j_exhaustive_anchors.py','scripts/m43j_result_report.py',
        'tests/test_m43j_exhaustive.py']
    names+=sorted(str(p.relative_to(ROOT)) for p in OUT.iterdir() if p.is_file())
    (ROOT/'RESULTS_MANIFEST_M43J_EXHAUSTIVE_ANCHORS.sha256').write_text(''.join(
        hashlib.sha256((ROOT/n).read_bytes()).hexdigest()+'  '+n+'\n' for n in names))
    print(json.dumps({'verified_summary':r['summary'],'manifest_entries':len(names)},indent=2))


if __name__=='__main__':main()
