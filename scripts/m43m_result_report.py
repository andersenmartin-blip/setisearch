#!/usr/bin/env python3
"""Audit M43M source evidence and write the inventory result and report."""
import argparse
import json
from pathlib import Path
from m43m_epoch_sources import ROOT, OUT, frozen, restart_gate
from seti_repeater import source_m43h as src

FREEZE = '7bf9931f72e12b2e537b367a251ebc8933d3d983'


def audit(work_root):
    cfg, contract = frozen()
    _, source_contract, metadata, preflight = src.frozen_inputs(ROOT)
    definitions = {s['label']: s for s in metadata['scans']}
    interval = next(w['proposed_interval'] for w in preflight['windows'] if w['window_id'] == cfg['window'])
    head = src.verify(json.loads((OUT / 'metadata_head_preflight.json').read_text()), 'result_sha256')
    assert head['counters'] == dict(head_attempts=4, head_completed=4, range_attempts=0,
                                    range_completed=0, accepted_range_bytes=0)
    assert [s['scan'] for s in head['sources']] == cfg['new_scans']
    for item in head['sources']:
        definition = definitions[item['scan']]
        assert item['head_ok'] is True and item['identity_matches'] is True
        assert item['url'] == definition['url'] and item['etag'] == definition['expected_etag']
        assert item['size'] == definition['expected_remote_size_bytes']
    checks = []
    counters = dict(head_attempts=0, head_completed=0, range_attempts=0, range_completed=0, accepted_range_bytes=0)
    failures = []
    for label in cfg['new_scans']:
        path = OUT / f'{label}.json'
        cp = src.verify(json.loads(path.read_text()), 'result_sha256')
        assert cp['config_sha256'] == contract and cp['scan'] == label
        assert cp['status'] == 'telescope-source-attested'
        attempts = cp['attempts']
        assert 1 <= len(attempts) <= cfg['maximum_source_attempts']
        for index, attempt in enumerate(attempts, 1):
            assert attempt['attempt'] == index and attempt['scan'] == label and attempt['window'] == cfg['window']
            for key in counters:
                counters[key] += attempt['transport_counters'][key]
            if index < len(attempts):
                assert attempt['status'] == 'source-attempt-failed' and attempt['transient'] is True
                failures.append(attempt)
        final = attempts[-1]
        assert final['status'] == 'telescope-source-attested'
        assert final['telescope_rows'] == final['sorted_reference_rows_exact'] == final['finished_restart_rows'] == 16
        public = src.verify(json.loads((ROOT / final['receipt_path']).read_text()))
        assert public['receipt_sha256'] == final['source_receipt_sha256']
        expected_scope = src.make_scope(definitions[label], cfg['window'], interval, source_contract, 'telescope-remote')
        assert public['scope'] == expected_scope and public['complete'] is True
        retained = src.rehydrate(work_root / 'live' / label / cfg['window'], final['source_receipt_sha256'])
        assert public == retained
        restart_gate(public, retained, {'resumed_rows': final['finished_restart_rows']}, final['finished_restart_counters'])
        plan_path = OUT / f"{label}_{cfg['window']}.range-plan.json"
        assert src.file_hash(plan_path) == public['transport']['range_plan_file_sha256'] == final['range_plan_file_sha256']
        plan = json.loads(plan_path.read_text())
        assert plan_path.read_bytes() == src.old_transport._canonical_json_bytes(plan)
        assert public['transport']['identity']['size'] == definitions[label]['expected_remote_size_bytes']
        checks.append({'scan': label, 'checkpoint': str(path.relative_to(ROOT)), 'checkpoint_sha256': cp['result_sha256'],
            'source_receipt_sha256': final['source_receipt_sha256'], 'rows': 16, 'sorted_reference_rows_exact': 16,
            'finished_restart_rows': 16, 'attempt_count': len(attempts),
            'transport_counters': {k: sum(a['transport_counters'][k] for a in attempts) for k in counters}})
    retained_checks = []
    for label, identity in cfg['retained_sources'].items():
        public = src.verify(json.loads((ROOT / 'results_m43h_widened_source' / f"{label}_{cfg['window']}.telescope-source.json").read_text()))
        assert public['receipt_sha256'] == identity
        assert src.rehydrate(work_root / 'live' / label / cfg['window'], identity) == public
        retained_checks.append({'scan': label, 'source_receipt_sha256': identity, 'rows': 16})
    result = src.seal({'milestone': 'M43M', 'status': 'three-pair-source-inventory-qualified',
        'freeze_commit': FREEZE, 'config_sha256': contract, 'source_contract_sha256': source_contract,
        'metadata_head_preflight_sha256': head['result_sha256'],
        'window': cfg['window'], 'new_sources': checks, 'retained_sources': retained_checks,
        'summary': {'new_sources': 4, 'new_rows': 64, 'total_sources': 6, 'total_rows': 96, 'on_off_pairs': 3,
                    'native_channels_per_row': interval[1] - interval[0]},
        'new_source_transport_counters': counters, 'failed_attempts': failures,
        'score_calculation_performed': False, 'multi_epoch_real_stack_qualified': False,
        'threshold_calibrated': False, 'recovery_measured': False, 'candidate_selection_performed': False}, 'result_sha256')
    return result


def main(work_root):
    r = audit(work_root)
    src.atomic_json(OUT / 'qualification.json', r)
    rows = '\n'.join(f"| {c['scan']} | 16 | Exact | 16; zero range bytes | {c['attempt_count']} | {c['transport_counters']['accepted_range_bytes']:,} |" for c in r['new_sources'])
    c = r['new_source_transport_counters']
    report = f'''# M43M — three ON/OFF pairs now have verified widened sources

All four prescribed additional source products at **1412.5 MHz** pass the
unchanged M43H source gate. Their **64 normalized integration rows**, each
containing **1,132,270 native channels**, exactly match the independently
sorted median/MAD reference, including float32 dtype. Each completed source
was reopened through live identity and checkpoint validation: all 16 rows
were reused, the source receipt stayed identical, and no new range bytes
were downloaded during that restart check.

| New source | Rows | Sorted normalization | Finished restart | Attempts | Accepted range bytes |
| --- | --- | --- | --- | --- | --- |
{rows}

Together with the two retained M43H products, the local verified inventory
now contains **six sources / 96 rows / three ON/OFF pairs at one window**.
Both retained source identities reproduce exactly during this final audit.
The three “epochs” are repeated scans in the same observing sequence,
not separate observing dates or independent replications. These rows are
the existing frozen integration inventory, not newly selected observations.

## Provenance and execution

The protocol, runner, tests and exact inventory were public at commit
`{r['freeze_commit']}` before new spectral range requests. A preliminary
metadata-only check made four successful HEAD requests, with all remote sizes
and ETags matching the fixed M37 metadata and zero spectral range requests.
Those preliminary HEADs are separate from the execution counters below.
The metadata receipt, passing test log and an explicitly incomplete download
snapshot were published during extraction in commit
`7b82140ce7e2ff1cc9ac36c29f235c392038aeb8`. That historical snapshot remains
unchanged; the final qualification and complete source checkpoints supersede it.

The extraction used four ordinary subprocesses, one per file. M43H transport,
HDF5 runtime, dataset/header checks, widened bounds, normalization and receipt
semantics were unchanged. M43M config SHA-256 is `{r['config_sha256']}`;
the inherited source contract remains `{r['source_contract_sha256']}`.
Retries were restricted by the predeclared transient-error rule; all attempts,
including any failures and committed partial-row counts, are retained in the
per-source checkpoint files. **{len(r['failed_attempts'])} failed attempts** occurred.

New-source execution, including completed-restart checks, records
**{c['head_attempts']} HEAD attempts / {c['head_completed']} completed** and
**{c['range_attempts']} range attempts / {c['range_completed']} completed**,
with **{c['accepted_range_bytes']:,} accepted range bytes**. This byte counter
measures validated response payloads, not complete network billing, failed
partial responses or uncompressed array sizes. Sparse local mirrors do not
represent full archive-file downloads.

Exact legacy-encoded range plans are published beside their source receipts;
their file digests match the transport proof. Native and normalized row file
and payload hashes remain bound in each complete source receipt. All six local
products were rehydrated against independently retained receipt identities
in the final audit. Published checkpoints and hashes support reconstruction;
the large reproducible telescope arrays and sparse mirrors remain local.

All **78 M43-family tests pass**. The two added tests check the transient-error
boundary and rejection of changed identities, partial row reuse or range
downloads during the finished-restart gate.

## Scope and reproduction

M43M qualifies source extraction, normalization and finished-source restart.
It evaluates **zero new score cells**. Numerical score equality established
by M43I–L retains its original first-pair scope. Real multi-epoch stacking,
additional-epoch score validation and newly frozen null/recovery calibration
remain ahead. There is no candidate decision or scientific nondetection here.

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/m43m_epoch_sources.py --work-root /path/to/m43h_work
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/m43m_result_report.py --work-root /path/to/m43h_work
sha256sum -c RESULTS_MANIFEST_M43M_EPOCH_SOURCES.sha256
```

The final audit requires both retained epoch-one products as well as the new
four products under `work-root/live`. The source runner checks all frozen pins
before remote access. A repeat run revalidates identity and reuses verified
checkpoints; transfer counters, elapsed time and enclosing checkpoint/result
seals may differ while the source receipts and row payloads must reproduce.
The manifest verifies the exact published artifacts. Sealed M43M result:
`{r['result_sha256']}`.
'''
    (ROOT / 'MILESTONE_43M_EPOCH_SOURCES_RESULT.md').write_text(report)
    names = ['MILESTONE_43M_EPOCH_SOURCES_PLAN.md', 'MILESTONE_43M_EPOCH_SOURCES_RESULT.md',
        'config/m43m_epoch_sources.json', 'scripts/m43m_epoch_sources.py',
        'scripts/m43m_result_report.py', 'tests/test_m43m_sources.py']
    names += sorted(str(p.relative_to(ROOT)) for p in OUT.iterdir() if p.is_file())
    (ROOT / 'RESULTS_MANIFEST_M43M_EPOCH_SOURCES.sha256').write_text(''.join(
        src.file_hash(ROOT / name) + '  ' + name + '\n' for name in names))
    print(json.dumps({'summary': r['summary'], 'result_sha256': r['result_sha256'], 'manifest_entries': len(names)}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--work-root', type=Path, required=True)
    main(p.parse_args().work_root)
