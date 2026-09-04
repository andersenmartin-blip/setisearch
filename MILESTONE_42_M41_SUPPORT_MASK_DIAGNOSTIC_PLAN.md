# Milestone 42 M41 truth-local support and mask diagnostic plan

Status: **FROZEN BEFORE SUBGROUP DIAGNOSTIC EXECUTION — LEDGER ONLY; NO NEW
SPECTRAL READ, INJECTION, OR CALIBRATION CURVE**.

## Motivation

M41 completed all 6,144 frozen trials but found truth-local candidate-score
cells for only 98 of 512 truths at each S/N level. Recovery reached 46/512 at
S/N 192 and remained 46/512 at S/N 256. Before any further S/N extension,
M42 will determine how much of this ceiling is fixed by truth-to-bank geometry
and how much arises later from mask/finiteness and the unchanged threshold.

## Frozen input and scope

M42 reads only the hash-pinned M41 aggregate and deterministic ledger transport
already published by commit `65404156df95070f98201b8d485c9d46a6ce5b09`.
The seven transport parts must reconstruct the exact 3,318,065-byte ledger
with SHA-256
`429789c591f44cb1ea87a5b340bf79a72905b44af3aa71bef964b3d002cc50fb`.
All 6,144 canonical records must pass the frozen M41 validator before an M42
result is emitted.

No telescope product, sparse mirror, cache, factor payload, or network source
may be opened. M42 performs no injection and does not rerun the score adapter.

## Predeclared nested accounting

For every truth and level, M42 will report these nested states without changing
the original 512-truth denominator:

1. **Geometric support:** `candidate_score_cell_count > 0`.
2. **Finite post-mask score:** `best_truth_local_score_snr` is finite.
3. **Threshold recovery:** the immutable M41 `score_recovered` bit is true.

The candidate-cell count, mask-dependency-cell count, and plan inventory must
be invariant across the 12 S/N levels for each truth. M42 will fail closed if
that structural invariant or the nesting `recovered <= finite <= supported`
does not hold.

The following truth fields are frozen for descriptive subgroup tables:

- `spectral_width_channels`
- `activity_subset_index`
- `line_index`
- `radial_stratum_index`
- `phase_stratum_index`

M42 will also publish the distribution of per-truth candidate-score-cell
counts and hash-pinned supported and unsupported truth-ID inventories. The
S/N 256 record is the predeclared highest-level cross-section.

## Decision rule

If fewer than 256 of the 512 truths have geometric support, the original M41
endpoint cannot reach 50% recovery under the frozen truth-local adapter,
regardless of a further S/N increase, because unsupported truths have no score
cell. In that case, M42 recommends a separately prospective adapter-support
repair or endpoint redesign before more injections. It does not authorize
either change.

If at least 256 truths have support but finite or recovered counts remain below
50%, a separately frozen mask/score diagnostic may be considered. M42 itself
stops after publishing the ledger-only diagnostic.

## Claim boundary

M42 is a retrospective engineering diagnosis of M41's fixed endpoint. It may
report exact descriptive fractions and a structural ceiling for that endpoint.
It may not discard unsupported truths, reinterpret a supported-only fraction
as completeness, interpolate a transition, change the threshold, transport
sensitivity, estimate occurrence rates, or make a technosignature claim.
