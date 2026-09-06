# M43J — exhaustive real anchors at native width one

## Question and reason for this stage

M43I compared all bank templates only at prescribed local carriers and exhausted
the carrier grid for two factor-extremum templates. Does its receipt-bound score
adapter agree with the direct native-window oracle at EVERY template/carrier
combination for the two existing first-epoch ON/OFF sources at 1412.5 MHz?

This endpoint fixes native width to one. It exhausts channel mapping and
integration arithmetic across the whole bank, isolating those operations before
expensive exhaustive wider-window sums. Wider filters retain only their M43I
qualification scope. This staging is chosen from algorithmic work and existing
metadata, not observed score values, peaks or pass rates.

## Frozen inputs and exact pass condition

Retain the M43E 1,701-template bank, its complete factor table and exact M43H
source receipts. Reuse the unchanged M43I telescope adapter and M43G direct
native-window oracle. Publish protocol, code, tests and config before evaluation.
The config binds all inherited M43I pins, its final result and the new scheduler.

For EACH of epoch1_on and epoch1_off, at width one:

1. Rehydrate the retained M43H native/normalized products through the real source
   gate, then require the same M43I source/cache identities and payload hashes.
2. Visit all template indices 0 through 1700 in contiguous batches of 32,
   with a final five-template batch. Each template spans ALL 747,793 support
   carriers, including 64 guard carriers at each end of the 747,665 score grid.
3. Gather full-support vectors in chunks of 4096 and compare every cell exactly
   to direct per-center native-window calculations streaming chunks of 4096.
   Retain float32 arithmetic and ascending integration order. Preserve repeated
   native-channel mappings without deduplication or reweighting.
4. Record the bank-major float32 score digest of every batch only after all its
   comparisons succeed. Require the exact ordered 54-batch inventory per source,
   with no missing, repeated or reordered template ranges.
5. Collect the two preselected M43I full vectors (indices 911 and 1678) from
   these exhaustive batches and require their combined digest to match M43I.

There are 3,402 full-support template vectors and 2,543,991,786 comparison cells.
These are numerical evaluation cells, not independent trials or candidate counts.
M43I overlap is included in this denominator. No candidate selection, threshold,
null calibration, injection/recovery measurement or real multi-epoch stack is
performed. No new remote requests are needed for the existing verified products.

## Resource and failure policy

The unchanged adapter uses its 512 MiB modelled ndarray cap. With 32 templates,
full-support output is about 95.7 MB; the gather allocation model, including its
source/cache allowance and mapping scratch, remains below the cap. This excludes
oracle/caller arrays, process RSS and OS caches. One source/cache is handled at
a time. Retained ancestor vectors occupy about 6 MB per source. Reference
coordinates/windows are chunked; no full bank-by-carrier matrix is retained.
Observed timing is descriptive and does not establish production throughput.

A sealed checkpoint binds config, source/cache identity and each passing batch.
Checkpoints are published progress evidence, not a promise of unattended work.
This runner recomputes on restart; it does not trust arbitrary self-sealed files
as permission to skip numerical evaluation. Final success requires all 108
batch comparisons and both ancestor overlaps. Stop on any identity, coverage or
exactness failure, preserve that attempt and publicly amend before any repair
or endpoint change. Existing frozen modules and historical outcomes stay intact.

The required M43-family tests include new coverage checks for the final partial
batch, missing/repeated/reordered records, retained vector order and deliberate
oracle mismatch. Unit fixtures mock M43H only; actual evaluation uses its real gate.

## Interpretation

Passing exhausts the specified bank/carrier domain at width one on these two
sources only. It does not imply that all widths, observing windows, epochs,
stack/detection statistics or false-alarm behavior have been qualified. The
oracle uses independent native-window access code but shares the frozen formula,
factors and NumPy runtime; this is not independent scientific replication.
Next work extends exhaustive width coverage and real observation/epoch coverage,
then qualifies the full detection endpoint before newly frozen calibration.
