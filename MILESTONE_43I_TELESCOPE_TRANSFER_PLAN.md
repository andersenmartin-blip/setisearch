# M43I — bounded telescope score anchors

## Purpose and freeze

Bridge M43G's synthetic numerical contract to M43H's two verified, widened
first-epoch ON/OFF telescope products at 1412.5 MHz. Publish this protocol,
implementation, tests and exact configuration before computing M43I real scores.
The raw/normalized inputs already exist; their M43H receipts are retained trust
anchors. No fresh transport, score-dependent choice, candidate ranking, threshold
or injection/recovery measurement is in this endpoint.

## Prescribed evaluation

Keep the M43E 1,701-template bank and fixed 1,701-by-96 factor table unchanged.
For each of the two sources, evaluate all eight native widths (1,3,5,9,17,33,65,129):

- All 1,701 templates at 17 carriers on each support edge, 17 at the center,
  and the two carriers of M43F's first minimum-factor collision (53 per template).
- The two templates containing the minimum and maximum scan factor, selected
  entirely from the frozen factor matrix, over all 747,793 support carriers.
- Exact equality against direct per-center native-window calculations, using
  float32 sums and the frozen order of integrations; no numerical tolerance.
- Full-grid outputs at two gather chunk sizes (4096 and 32768) must match exactly;
  the direct reference streams chunks of 4096; local gathers use chunks of 7.
- Exact local/full overlap and explicit survival of the frozen collision witness.
- Revalidate all 32 full normalized rows against the independent sort-based
  median/MAD implementation from their stored descending native rows.

The per-scan carrier intervals, selected template indices, collision integration,
source receipts and scan-factor digests are written explicitly in the config.
Denominators count prescribed evaluation cells, including local/full overlap;
they are not independent trials, discoveries or measured sensitivity.

## New source boundary and integrity

`TelescopeSource` and `TelescopeCache` are separate types. Their arithmetic is a
frozen copy of M43G v2, preserving repeated native channels for factors below one.
No telescope arrays are wrapped as `SyntheticSource`. The loader calls M43H
`rehydrate` with an independently pinned receipt and `telescope-remote` kind;
it then rehashes every normalized row loaded into immutable byte-backed storage.
Receipt identity binds the source geometry, normalization scope, row inventory
and transport evidence. Cache identity additionally binds the bank, actual scan
factors, complete proxy grid, width, numerical contract and filtered payload.
Every gather validates source/receipt, dtype, shape, layout, read-only arrays and
payload identity. This is reproducible local integrity under the pinned receipt
trust model, not authentication against a malicious runtime or telescope server.

Tiny unit tests mock only the M43H gate and do not attest telescope provenance.
They exercise the new boundary, all widths, repeats, chunking, altered receipts,
row order, same-byte dtype/shape changes, mutable arrays, and cache substitutions.
The existing M43-family suite remains required. No old calibration/cache is reused.

## Resources, outputs and stop conditions

One source and one native-filter cache are processed at a time. The inherited
512 MiB adapter-owned ndarray bound excludes caller/oracle arrays, transport,
OS caches and process RSS. Full-bank outputs are restricted to short fixed
intervals; exhaustive support vectors are limited to the two prescribed templates.
This is not an exhaustive bank-by-carrier or multi-epoch detector qualification.
A sealed per-source/width checkpoint is written after all its comparisons pass;
a final sealed result is written only after all 16 checks pass. These checkpoints
are reviewable progress evidence; this runner recomputes rather than resumes them.
Stop on any identity or exactness failure, retain the failed attempt and publish
a separate amendment before changing the scientific/numerical endpoint.

## Interpretation and next gate

Passing establishes score transfer only for the explicitly tested real anchors,
not a calibrated search or extraterrestrial evidence. The direct oracle uses a
different filtering/access path but shares the frozen formula, factors and NumPy;
it is not independent scientific replication. Later work must expand real source
and epoch coverage, qualify full detection/stack behavior, and run newly frozen
null and injection/recovery calibration before interpreting search candidates.
