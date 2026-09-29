# Receiver cache batching — equivalent arithmetic, lower software cost

29 September 2026. Parent evidence checkpoint:
`a5fcb1b36aa890916442a7c1b3a1dd7903358dca`.

**The receiver query path now avoids rehashing the same large source/cache
payload for every retained member.** Fifteen targeted tests pass. On two fixed
deterministic software workloads, 1,024 queries take about 0.04 seconds instead
of about 12 seconds, with exactly identical signature and receipt bytes.
This is a measured component improvement, not an 80-second whole-chain pass.

## Change and correctness boundary

The previous `pipeline_receiver_radio.NativeRun.receiver` grouped queries by
scan and filter width but still called `synthetic_signature` separately for
every member/epoch. Each scalar call invokes `gather_bank_slice`, which validates
and hashes the complete normalized source and filtered cache before checking a
single guard cell. Thus many queries repeatedly hash the same multi-megabyte
arrays. This is a demonstrated avoidable cost; the old 224.702-second failed
experiment has no stage profile that would assign all of its time to this code.

The new bounded batch entry point validates the complete source/cache before
and after processing a group. It requires immutable byte-backed source, cache
and factor arrays; merely read-only views of mutable owners are rejected. Every
requested template retains its guard-cell validation. No cached validation or
execution authority survives the call. Duplicate template/carrier requests
reuse arithmetic but receive separate output dictionaries in the original
order. Every record/epoch still has its individual signature and original
receipt. A failed exit check returns no completed batch.

The original scalar entry point remains available. Its numerical body was
extracted unchanged, and an AST comparison with the immutable parent verifies
that every arithmetic statement is identical. The native receiver wrapper now
uses batches. Thresholds, factor calculations, float32 integration order,
inclusive 100-Hz neighborhood, tie-breaking, masks, physical vetoes and
receipt canonicalization are unchanged.

## Fixed software measurements

The prospective local software recipe, code hashes and runtime are saved in
[`fixed_before_measurement.json`](results_radio_receiver_batch_2026-09-29/profile01/fixed_before_measurement.json).
The benchmark calls the original scalar function extracted from the immutable
parent, then the new batch function on the same newly constructed deterministic
software cache. It uses 16 rows, 65,536 channels, eight templates and 256 unique
queries repeated four times per width. No RNG, historical experimental arrays,
telescope values or scientific case identity is used. It is neither a fresh
native scientific experiment nor a replay of the closed failed case.

| Width, channels | Queries | Original scalar, s | Batch, s | Observed ratio | Complete output bytes identical |
|---|---:|---:|---:|---:|---|
| 1 | 1,024 | 12.065848 | 0.046094 | 261.8× | Yes, 625,618 bytes |
| 129 | 1,024 | 11.793298 | 0.037633 | 313.4× | Yes, 625,158 bytes |

The whole software profile takes **24.178081 seconds**, with **58,425,344 bytes**
peak RSS, below its fixed 90-second/512-MiB limits. All signature/receipt outputs
are saved losslessly, with both original and batch hashes. A read-only decoder
verifies all 2,048 pairs and all eight frozen source-code hashes. The profile
is closed; these measurements need not be repeated as a new milestone.

This is one scalar-first measurement per width, without a confidence interval
or counterbalanced order. Repeated queries contribute to the measured gain.
Do not multiply the observed ratio into an estimate of full pipeline speed or
claim that the historical failed case now passes. Cache construction, scoring,
retention, OFF decisions, receiver aliases, clustering, complete evidence,
remote transport and failure handling remain outside this timing comparison.

## Verification and next action

Nine new tests cover all eight widths, carrier boundaries, ordering/duplicates,
an independent direct native-window oracle, exact ties, immutable backing,
source/cache/factor corruption, invalid queries, the batch cap, exit-validation
failure and receiver record/epoch receipt assembly. Six existing receipt-bridge
tests also pass: **15 tests total**, not 15 new scientific trials. The initial
14-test log is preserved separately; the final log adds the orchestration test.

Code, tests, fixed benchmark recipe, outputs and logs are in this commit and
[`results_radio_receiver_batch_2026-09-29/`](results_radio_receiver_batch_2026-09-29/).
The numerical code is changed, so a future native experiment must freeze these
new bytes and the current runtime explicitly. It cannot reuse an older freeze.

**Next:** one prospectively fixed complete native physical/resource qualification
using fresh engineering identities, with all receiver/alias/cluster outcomes,
stage timing, complete evidence and bounded failure handling. Integrated remote
publication/readback and scientific case/phase capacity still need qualification.
Do not open the 127/24 scientific proposal or telescope spectra on the strength
of this software profile. The later separate scientific and telescope admission
requirements in the readiness decision still apply.

All closed attempts and spent identities, source selection, prior holds/counters,
unopened holdouts, LS pause and CHEOPS UNSENT remain unchanged. No external
messages or delegation. Review around 2 October and consolidate 9 October;
no schedule or plan end date is changed.
