# M43M — three ON/OFF pairs now have verified widened sources

All four prescribed additional source products at **1412.5 MHz** pass the
unchanged M43H source gate. Their **64 normalized integration rows**, each
containing **1,132,270 native channels**, exactly match the independently
sorted median/MAD reference, including float32 dtype. Each completed source
was reopened through live identity and checkpoint validation: all 16 rows
were reused, the source receipt stayed identical, and no new range bytes
were downloaded during that restart check.

| New source | Rows | Sorted normalization | Finished restart | Attempts | Accepted range bytes |
| --- | --- | --- | --- | --- | --- |
| epoch2_on | 16 | Exact | 16; zero range bytes | 1 | 457,175,806 |
| epoch2_off | 16 | Exact | 16; zero range bytes | 1 | 457,108,614 |
| epoch3_on | 16 | Exact | 16; zero range bytes | 1 | 457,176,572 |
| epoch3_off | 16 | Exact | 16; zero range bytes | 1 | 457,171,246 |

Together with the two retained M43H products, the local verified inventory
now contains **six sources / 96 rows / three ON/OFF pairs at one window**.
Both retained source identities reproduce exactly during this final audit.
The three “epochs” are repeated scans in the same observing sequence,
not separate observing dates or independent replications. These rows are
the existing frozen integration inventory, not newly selected observations.

## Provenance and execution

The protocol, runner, tests and exact inventory were public at commit
`7bf9931f72e12b2e537b367a251ebc8933d3d983` before new spectral range requests. A preliminary
metadata-only check made four successful HEAD requests, with all remote sizes
and ETags matching the fixed M37 metadata and zero spectral range requests.
Those preliminary HEADs are separate from the execution counters below.
The metadata receipt, passing test log and an explicitly incomplete download
snapshot were published during extraction in commit
`7b82140ce7e2ff1cc9ac36c29f235c392038aeb8`. That historical snapshot remains
unchanged; the final qualification and complete source checkpoints supersede it.

The extraction used four ordinary subprocesses, one per file. M43H transport,
HDF5 runtime, dataset/header checks, widened bounds, normalization and receipt
semantics were unchanged. M43M config SHA-256 is `52fa731281b1fa348ad428aab59f5949a547ceb51d2def7b5e1bf50fed64b8eb`;
the inherited source contract remains `fd1e74f41cc39e20f434f6e241647bc41a97b7981d3bf5f92e7ee53d87707553`.
Retries were restricted by the predeclared transient-error rule; all attempts,
including any failures and committed partial-row counts, are retained in the
per-source checkpoint files. **0 failed attempts** occurred.

New-source execution, including completed-restart checks, records
**8 HEAD attempts / 8 completed** and
**384 range attempts / 384 completed**,
with **1,828,632,238 accepted range bytes**. This byte counter
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
`bce9b6c487c0af46c33669c30132135df83a9d048d45188d5aa24758757fb840`.
