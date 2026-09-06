# M43I — real telescope score transfer passes the prescribed anchors

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
| epoch1_on | 16 | `06e1febc171ed4cdee9d92a33e13efaed6298d733ce1615c6b3ec64ca857650f` |
| epoch1_off | 16 | `30945e7f056f033cc28364255ef0d41f929ce71e53ff50c6597e662f84cd056b` |

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

- Public pre-evaluation freeze: `6a23b394a0198b9a8569d2f819fd8ff486b7bc08`.
- Config file SHA-256: `ac98881a75205252e91570617bf6aa3bdb66522b01004621399b1519a3b3ebda`.
- Numerical contract: `31e3ea77fabbeb87287ce7df03d31cb789f37f83b5b27d612ee188338697ef05`.
- Fixed M43E bank: `84524f7e129c0b414bde5004fe64bfb3ff94877357a7bb4dce399562d945d873`.
- Fixed full factor table: `bc5c9e1f7a2db63074be30a946b2e1bd68963966f6c6b11cc5ad30f4e173edcd`.
- M43H source result: `be4a08ee35c1b1a9257538c31c580ceb5fada308932daa47592844ab8e81e56e`.
- M43I sealed result: `b2f9be7ed22848aaca3d0eab15a1535ee12a5643a06c47a593b15e31db72c41a`.
- NumPy: `2.3.5`. Observed local run: **76.901 seconds**;
  this is descriptive timing for the bounded qualification, not a detector benchmark.

Sixteen sealed per-source/width checkpoints accompany the final result. The
report generator audits their seals, exact configuration identity, inventory,
denominators and success flags. The result manifest binds the delivered artifacts.
No new remote requests were made; existing M43H native/normalized products were
read locally. Reproduction requires those products or reconstruction through the
published M43H source protocol, with the retained receipt hashes matching.

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 .venv/bin/python -m unittest discover -s tests -p 'test_m43*.py'
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/m43i_telescope_qualification.py --work-root /path/to/m43h/live --freeze-commit 6a23b394a0198b9a8569d2f819fd8ff486b7bc08
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
