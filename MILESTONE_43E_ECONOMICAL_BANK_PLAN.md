# M43E: remaining coverage causes and a smaller bank

Publish this protocol, executable, tests and pinned configuration before any
new M43E bank/truth evaluation. M43D is the exposed development baseline:
the 889-template bank failed its fresh 95% gate; 3,301 templates gave a
promising descriptive result but were not the preselected confirmation bank.
M43E does not retrospectively change either conclusion.

## Fixed geometry and bank construction

Retain the same HD 156668 b factor basis, m37_1412p5 proxy-carrier grid,
20 Hz inclusive binary64 endpoint, every active integration, one common
carrier and one template. Reuse the tested M43D interval prefilter, including
its numeric-domain restrictions and capacity abort, followed by the literal
<=20 Hz check. No tolerance, carrier range, activity rule, score or mask change.

The candidate `checker32` preserves the entire 889-record disk16 prefix.
From disk32's remaining points append exactly those with even i+j, where
(i,j)=(32*x,32*y). Preserve the original order and attach the original template
index to appended records before assigning sequential new indices. Because
all even/even points are already present, the additions are odd/odd points.
This geometric rule yields **1,701 templates**, compared with 3,301 in disk32.
It uses no individual truth coordinates or residuals to place templates.
The bank is a subset of disk32 and a superset of disk16; sample support must
obey that ordering. Its trial-count ratio is 1701/3301, not a measured runtime.

## Stage 1: retrospective replay, diagnosis and nomination

Reconstruct the exact M43D basis/table. For all 2,560 exposed associations
(512 historical plus 512 M43D new tracks under four activity patterns),
reproduce every candidate-pair hash, candidate count and published witness
for ALL four original banks, including disk8. Any mismatch aborts M43E.
Compute the checker32 subset with explicit index remapping.

For every unsupported disk16 or disk32 association, diagnose every template
using the already tested M43C continuous-carrier minimax/interval calculation:
track-shape incompatibility, outside-range solution, between-carrier-cell gap,
or unresolved numerical boundary. Keep the predeclared 0.001 Hz ambiguity
guard and longdouble diagnostic; it does not change exact 20 Hz support.
Publish per-cause template counts, best fit, full-diagnostic inventory hashes,
association counts and distinct truth IDs so repeated activity tests do not
become falsely independent cases. No cause-driven change to the bank or range
is allowed within M43E.

Nominate the first of **checker32, disk32** reaching >=95% in EACH of five
exposed development groups: historical 512, then each of the four original
M43D 512-track activity groups. These original M43D groups are now development
data, never relabelled as independent confirmation of M43E. If neither bank
qualifies, stop and report that outcome without opening the fresh endpoint.

Write the development result and seal `selection.json` with its result hash,
bank identities and config hash. **Publish and verify this nomination before
executing Stage 2.** The code has separate stage commands to enforce the
workflow break. Nomination cannot switch after fresh results are observed.

## Stage 2: genuinely new parameter draws on the same cadence

Generate 1,024 fresh deterministic tracks from 32 equal-area radial strata
and 32 phase strata using label `m43e-fresh-confirmation-disk-v1-2026-09-06`.
Jitter uses the top 53 SHA-256 bits divided by 2^53, with the exact canonical
inputs in the pinned executable. Carriers are continuous draws between
score_hz[256] and score_hz[-257], the same allowed proxy interval as M43D.
Reject exact coefficient overlap with any M43D truth or disk32 template and
reject duplicates. This stage is not generated/evaluated on the real cadence
until the nomination is public; generator fixtures use an unrelated small grid.

Test each track under (0,1), (0,2), (1,2), (0,1,2), using every active
integration: 1,024 unique tracks and 4,096 paired associations. Confirm only
the nominated bank, requiring >=95% (at least 973/1024) in EVERY group.
Publish baseline, disk16, checker32 and disk32 descriptive counts for all
groups, without substituting a different passing bank if the nominee fails.
Do not pool the paired activity tests into 4,096 independent trials.

All 1,024 tracks remain in every denominator, including carrier-edge failures.
The sample gate is an engineering criterion, not a global parameter-domain
certificate or a detection/recovery rate. It uses the same cadence and orbital
metadata, not independent sky observations. No spectral width or S/N enters
this endpoint. Historical M43D carriers and activity allocations need not have
the same distribution as this fresh inventory.

## Costs, verification and interpretation

Report template count, bank identity, exact score cells per window
(templates * 747665 * 32), relative cells against both 93 and 3,301 templates,
factor-table bytes and observed metadata-geometry time. This is no benchmark
of the full spectral pipeline, mask construction, cache I/O or calibration.
Checkpoint and losslessly publish every association's identity, bank pair
hashes and witness. Tests cover subset remapping, bank preservation/parity,
inclusive all-group selection, disjoint deterministic generation on fixtures,
and tamper-evident restarts, in addition to existing M43 tests. Final review
re-evaluates witnesses from physical coefficients and audits all denominators.

If confirmed, nominate the fixed bank for source/cache extraction coverage,
score/false-association validation, exhaustive real-data anchors and renewed
threshold calibration. A larger bank invalidates naive transfer of the old
threshold. A passed geometric gate alone does not enable production adoption.
If failed, preserve the failed confirmation and require a new separately
frozen design and new confirmation tracks. No new spectra, injections or
scores are opened in either stage; no astronomical sensitivity or
technosignature claim follows.
