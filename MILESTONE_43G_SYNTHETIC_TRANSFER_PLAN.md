# M43G: fixed-bank synthetic numerical transfer qualification

Publish this plan, adapter, independent reference, executable, tests and hash-pinned
configuration before evaluating full-size synthetic sources with the M43E factors.
M43F exposed inadequate extraction width and forbidden duplicate native mappings.
M43G qualifies the numerical adapter needed to address them. It does not attest
remote telescope products or complete the real-data transfer gate.

## Fixed inputs and numerical contract

Keep the M43E 1,701-template bank, its 96-integration factor basis/table, the five
M37 proxy grids (747,793 support carriers each), eight filter widths and all six
ON/OFF scans. Use exactly the wider common extraction intervals published by M43F.
Require the M43F result identity and original metadata ancestry, without making
any telescope request. No parameter selection may depend on synthetic outcomes.

The new `transfer_m43g` module accepts explicitly synthetic row readers. It is a
separate type from every old M37 source/cache product. A future production adapter
must verify remote identity, transport and extraction ancestry before creating a
separately named telescope product. This numerical helper cannot provide that
attestation, and an arbitrary callback is not a telescope trust boundary.

Read one float32 integration at a time. Reverse descending archive rows before
normalization. Use the frozen float32 median/MAD arithmetic in 4096-channel blocks
anchored at ascending channel zero of the **new** extraction, including the final
short block. Do not reuse the old normalization scope or its threshold receipts.
Bind scope, geometry, raw payload, normalized payload and normalization contract
into the source identity. Back retained arrays with immutable bytes.

Apply native boxcars first, using ascending windows, float32 sums divided by
float64 sqrt(width) and cast to float32, as in the existing spectral primitive.
Filter chunks have native halos; chunk edges must not restart or truncate a window.
Cache identity binds source, new contract, fixed bank, factors, grid, width and
filtered payload. All bank endpoint mappings must lie inside full filter coverage.

Gather via the unchanged binary64 affine nearest-even rule. Permit finite positive
factors below 2 and nondecreasing native steps in {0,1,2}, including across chunk
boundaries. Retain every proxy carrier when adjacent carriers share a native channel;
no deduplication, weighting change, interpolation or dropped support cell is allowed.
Accumulate integrations in ascending row order in float32, then divide by float32
sqrt(integration_count). Slices are diagnostic outputs, not exhaustive search claims.
Duplicates induce correlations; no independence or threshold-transfer claim follows.

## Bounded resources

A single normalized source and one width cache are retained at a time. The adapter
uses a conservative array bound of `3*rows*channels*4 + 96*channels + 4 MiB`, plus
explicit gather output and mapping scratch. Reject before the reader/allocation if
the predicted bound exceeds 512 MiB. This bounds adapter-owned arrays, not process
RSS: exclude caller-held arrays, previous caches, transport buffers and OS caches.
The full-size qualification reader synthesizes only one integration at a time.
No frequency-coordinate array is needed; use header-affine geometry directly.
The separate oracle has its own short q blocks; never materialize the full
1,701 x 16 x 747,793 map or its filter windows.

## Predeclared evaluation

Use NumPy 2.3.5 PCG64, seed 430720260906 + 10000*window_index + 100*scan_index +
integration_index. Synthetic raw powers are float32(10) plus float32 standard
normal draws. This is a deterministic arithmetic fixture, not a validated noise
model, injection population or recovery experiment.

1. For all 30 scan/window sources, compare every full normalized integration
   bit-for-bit with an independent full-sort median/MAD implementation. Its median
   algorithm uses sorting rather than the adapter's frozen partition primitive.
2. For all 240 scan/window/width combinations and all 1,701 templates, compare
   integrated scores on 17 carriers at each support end, 17 at the center, and the
   two carriers in the already published M43F minimum-factor collision witness.
   The oracle independently builds nearest-even centers and gathers each complete
   native window directly from normalized data, then sums it. It does not call the
   adapter's filter or gather. Check the entire oracle output exactly.
3. At 1412.5 MHz, all six scans and widths 1 and 129, choose the first flattened
   minimum- and maximum-factor templates, deduplicating only this template list if
   identical. Exhaust every one of the 747,793 support carriers for those templates.
   Compare two gather chunk sizes (4096 and 32768), the independent native-window
   oracle in 4096-carrier blocks, and the corresponding local slices exactly.
4. For the 51 common diagnostic carriers, stack all templates for ON and OFF,
   all windows/widths and all four activity subsets. Compare the existing sum/sqrt
   epoch stack and active-epoch >=3 cut to an explicit sequential reference.
   This is arithmetic validation, not an adopted threshold or ON/OFF veto search.

Development tests cover sort/partition equivalence, terminal blocks, orientation,
half-channel ties, chunk boundaries, repeat preservation, legacy injective-domain
agreement, identity changes/tampering, invalid factors, bounds and capacity refusal.
They may run before freeze. The larger test above runs only after public freeze.

## Gate, reporting and next work

Require exact equality in every comparison; fail closed at the first discrepancy.
No tolerances, carrier exclusions or selection changes after seeing results. Publish
any failure before revising the contract. On success, publish sealed result inventories,
payload identities, exact denominators, manifest and a structural result audit.
A byte-identical replay may be used to resolve a concrete discrepancy but is not a
mandatory second full run. Do not call the oracle independent implementation of
every pipeline stage: it shares fixed input data, normalization mathematics and
NumPy arithmetic, while using distinct normalization/filter/gather code paths.

Success qualifies this synthetic numerical adapter only. Next: build and qualify a
separately attested widened telescope extractor/source factory with restartable
payload ancestry and bounded transport, then deterministic exhaustive real-data
anchors and renewed null calibration. Keep prior results and original denominators.
Existing owner authorization covers continuing analysis and publication.
