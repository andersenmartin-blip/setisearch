# M43J — exhaustive width-one real anchors pass

All **2,543,991,786 prescribed score cells** match the direct native-window
reference exactly. At native filter width one, the complete 1,701-template bank
has now been checked across all 747,793 support carriers for both existing
first-epoch ON and OFF telescope sources at 1412.5 MHz.

| Source | Full-support templates | Batches | Compared cells | Direct reference |
| --- | --- | --- | --- | --- |
| epoch1_on | 1,701 | 54 | 1,271,995,893 | Exact |
| epoch1_off | 1,701 | 54 | 1,271,995,893 | Exact |
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

- Public pre-evaluation freeze: `c20d453183ddf0f52044abde9ca659a4f69668e0`.
- Config SHA-256: `370b93f15bb0fa38e08ddbc54f56a4179c026a1b9a9d58c696b28e3c7bfb5e17`.
- M43J sealed result: `3e9ef51c89d4b8d97a4223adb2bcdd3adc0cedbbac08fe3506a546949b098179`.
- Parent M43I result: `b2f9be7ed22848aaca3d0eab15a1535ee12a5643a06c47a593b15e31db72c41a`.
- Fixed M43E bank: `84524f7e129c0b414bde5004fe64bfb3ff94877357a7bb4dce399562d945d873`.
- Fixed full factor table: `bc5c9e1f7a2db63074be30a946b2e1bd68963966f6c6b11cc5ad30f4e173edcd`.
- Proxy grid: `18739188d199ffeaf1854911efc590c2cb2c5a0817704ed7f9f9bb86358c6429`.
- NumPy: `2.3.5`.

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
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/m43j_exhaustive_anchors.py --work-root /path/to/m43h/live --freeze-commit c20d453183ddf0f52044abde9ca659a4f69668e0
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

The observed exhaustive run took **525.174 seconds**. This is
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
