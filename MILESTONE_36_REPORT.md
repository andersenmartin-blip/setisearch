# Milestone 36 report: HIP 48714 b primary search and exhaustive retention audit

## Outcome

Milestone 36 is a **primary-cadence null after a complete above-threshold
retention audit**. The prospectively frozen detector v0.5.0 primary search
reported 1,676 frequency clusters formed from its retained hypothesis peaks.
Of those reported clusters, 239 exceeded the frozen operational threshold and
received a primary v0.5 physical control disposition.

The primary report cap did not truncate those 1,676 clusters, but a later
review found that the upstream collector examined only 15 score cells and
retained at most three peaks per width/orbit/activity hypothesis. A
retrospective, significance-neutral supplement was therefore frozen after the
primary result and before re-extracting the same spectra. It visited all
1,202,587,680 frozen score cells and accounted for all 7,571 cells at or above
the primary threshold with two complete non-maximum-suppression ledgers.

The audit candidate set contains 1,081 member records in 637 frequency
clusters. It includes all 404 primary retained above-threshold hypothesis
records and 677 newly exposed records. Under the strict physical rules, 692
members match the OFF data at the same hypothesis, 229 have recurrent local
OFF evidence within an actual 20 Hz, and 160 are reproduced on the exact
candidate track in an adjacent OFF scan. No receiver-frame alias was needed
as the final disposition of any member. There are zero unaccounted
above-threshold cells, zero unresolved members, and zero unresolved clusters.
The published stopping outcome is
`PRIMARY_CADENCE_NULL_AFTER_COMPLETE_RETENTION_AUDIT`.

This is a null for one archive cadence under the frozen frequency, motion,
activity, width, and completeness model. It is not an independent recurrence
test and is not a statement that no transmitter exists. HIP 48714 b is used
only as a motion template; the analysis neither assumes nor tests that a
transmitter is on the planet. No second qualifying HIP 48714 archive cadence
was identified.

## High-smearing extension and frozen data

Milestones 31--33 consumed the eligible targets in the frozen ranks 31--35
extension. Milestone 36 then screened ranks 36--40 without reading spectral
values. HIP 48714 at rank 36 was the first compatible host. HD 156668 at rank
37 and HD 1461 at rank 38 each retain one spectrally untouched qualifying
cadence for later work; ranks 39 and 40 have none.

HIP 48714 b's conservative full-projection periastron proxy is 5.30654596 Hz/s
at 1425 MHz. Before any rank 36--40 spectrum was opened, the boxcar bank was
expanded to `[1, 3, 5, 9, 17, 33, 65, 129]` channels and the downstream report
cap was set to 2,200. Detector software v0.5.0, the 21-template motion bank,
four activity subsets, physical control rules, 256 scrambles, and completeness
procedure otherwise remained frozen.

The prospective cap proof established that 2,200 exceeded the maximum 2,016
records that v0.5.0 could admit per window after its three-peak-per-hypothesis
stop. It therefore protected the downstream report from truncating already
admitted records. It did not establish complete upstream retention, because
the collector also used a 15-cell pool and stopped after three peaks. The
supplementary audit described below repairs that specific proof gap without
changing the primary detector, threshold, empirical p-value, or completeness
calibration.

The primary archive cadence is `--76348`, beginning MJD
57619.72236111111 (2016-08-19 17:20:12 UTC), with the sequence:

`Hip48714 -- Hip47655 -- Hip48714 -- Hip47791 -- Hip48714 -- Hip48132`.

All six scans have 16 integrations of 18.253611008 s and 2.793967724 Hz
channels. The metadata-only motion-plus-width proof passed all 630 checks. It
included the 64-channel half-width of the widest filter; the smallest
extraction-edge headroom after motion and width margins was 200,607 channels,
approximately 560.489 kHz. The largest within-scan dedoppler margin was 362
channels.

## Prospectively frozen primary search

Detector v0.5.0 searched five disjoint 1 MHz planet-frame bands with 21 motion
templates, four activity subsets, and eight spectral widths: exactly
**1,202,587,680 nominal score cells**. The 256 complete scrambles gave:

- observed global maximum: S/N **7131.717410099474**;
- empirical global p-value: **1/257 = 0.0038910505836575876**;
- null median: S/N **13.519803047180176**;
- operational global threshold: S/N **15.89224910736084**.

With 256 scrambles, 1/257 is the smallest add-one empirical p-value available.
It shows that the cadence contains extremely strong structured features, but
does not establish an astrophysical or artificial origin and does not
override physical control evidence.

The following table is the accounting of the **primary v0.5 retained cluster
set**, not the later exhaustive audit set.

| Window | Primary retained clusters | Primary clusters above threshold | Maximum S/N | Reported `on_best` frequency (MHz) | Primary above-threshold cluster disposition |
|---|---:|---:|---:|---:|---|
| `m36_1400p5` | 197 | 44 | 7131.717410 | 1400.262878753 | 35 matched-OFF, 7 local-OFF, 2 single-adjacent-OFF |
| `m36_1406p5` | 216 | 52 | 4619.225112 | 1406.212668359 | 42 matched-OFF, 8 local-OFF, 2 single-adjacent-OFF |
| `m36_1412p5` | 203 | 24 | 6104.569542 | 1412.026140280 | 17 matched-OFF, 6 local-OFF, 1 single-adjacent-OFF |
| `m36_1418p5` | 293 | 50 | 46.725056 | 1418.815321609 | 37 matched-OFF, 11 local-OFF, 2 single-adjacent-OFF |
| `m36_1425p0` | 767 | 69 | 40.255371 | 1424.862891622 | 39 matched-OFF, 12 local-OFF, 18 single-adjacent-OFF |
| **Total** | **1,676** | **239** |  |  | **170 matched-OFF, 44 local-OFF, 25 single-adjacent-OFF** |

`m36_1406p5` has two primary clusters tied exactly at the reported maximum
S/N: 1406.212668359 MHz, which the detector records as `on_best`, and
1406.113345601 MHz. Both have a matched-OFF disposition, so the tie does not
affect the primary retained-set accounting.

Within the primary retained set, 1,437 clusters were below the global
threshold. The remaining historical v0.5 dispositions were 170
`rfi_veto_off_source`, 44 `rfi_veto_local_off_source`, and 25
`rfi_veto_single_adjacent_off`.

The configured 20 Hz primary local rule was implemented by v0.5.0 as an
integer native-channel radius. For this cadence, `ceil(20/2.793967724)` gives
eight channels, or at most 22.351742 Hz. Those historical cluster dispositions
are therefore reported as v0.5 accounting rather than as literal-20-Hz
accounting. The exhaustive supplement independently uses a seven-channel
radius, approximately 19.557774 Hz, for strict local closure.

## Retrospective complete-retention audit

The published primary summary showed that 3,165 of the 3,360 frozen
hypotheses could be certified without reopening spectra. Of the remaining 195,
192 were exposed to the 15-cell pool and three width-129/all-epoch hypotheses
in `m36_1425p0` reached the three-peak stop while their third retained peak was
still above the operational threshold. The primary retained set alone could
therefore not support an exhaustive null.

The supplementary protocol was frozen after that primary result but before
raw-data re-extraction. It is explicitly retrospective and significance
neutral. The workflow re-extracted only the same 30 HIP 48714 slices and
required every logical path and SHA-256 to match `DATA_MANIFEST_M36.sha256`.
It also required exact source and environment hashes and reproduced every
published per-window maximum and complete primary `candidate_reduction`
object before interpreting supplementary records.

For every width/orbit/activity hypothesis, the audit enumerated every finite
score cell at or above S/N 15.89224910736084. The legacy-compatible ledger
used inclusive radius `max(1, width // 2)` channels. A second ledger used a
literal-20-Hz radius of seven channels so that a broad filter could not
suppress a feature outside the final cluster tolerance. Each suppressed cell
is mapped to an equal-or-stronger selected owner. The audit member set is the
union of the two ledgers plus a frozen primary-representative tie crosswalk;
the crosswalk added no records in this execution. Suppressed score cells are
coverage evidence, not separately classified candidates.

| Window | Above-threshold score cells | Legacy representatives | Literal-20-Hz representatives | Audit members | Newly exposed members | Audit clusters | Strict member dispositions: exact/local/single | Unresolved members |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| `m36_1400p5` | 1,489 | 86 | 195 | 195 | 126 | 105 | 160 / 33 / 2 | 0 |
| `m36_1406p5` | 1,167 | 78 | 164 | 164 | 87 | 109 | 123 / 39 / 2 | 0 |
| `m36_1412p5` | 708 | 70 | 103 | 109 | 42 | 49 | 73 / 35 / 1 | 0 |
| `m36_1418p5` | 1,221 | 77 | 164 | 164 | 97 | 106 | 132 / 30 / 2 | 0 |
| `m36_1425p0` | 2,986 | 189 | 444 | 449 | 325 | 268 | 204 / 92 / 153 | 0 |
| **Total** | **7,571** | **500** | **1,070** | **1,081** | **677** | **637** | **692 / 229 / 160** | **0** |

“Exact,” “local,” and “single” in this audit table are mutually exclusive
member-level dispositions in priority order: matched-OFF recurrence at the
same hypothesis and threshold; recurrent local-OFF evidence at an actual
absolute offset no greater than 20 Hz; and a same-track adjacent-OFF match at
the frozen single-epoch S/N 5.5 floor. Receiver-frame alias evidence was also
permitted by the protocol, but no audit member needed it as its final
disposition. Arithmetic-frequency families, template multiplicity, and width
labels were not accepted as physical closure.

The audit also recorded the rounded v0.5 member classification separately:
692 exact, 230 local, and 159 single-adjacent dispositions. Enforcing the
literal 20 Hz boundary moves one member from local to single-adjacent control
evidence; it does not create an unresolved member.

All 3,360 hypotheses and all 1,202,587,680 score cells were visited. Every
above-threshold cell has a valid ledger owner, every one of the 1,081 audit
members has a strict physical disposition, and every audit cluster has all of
its members physically disposed. The result is therefore the protocol's
closed outcome. The audit neither changes the primary empirical p-value nor
reruns or improves the primary completeness calibration.

## Strongest primary event and physical control evidence

The primary global maximum is centered at 1400.262878753245 MHz, uses the
65-channel boxcar and template 8, and is active in ON epochs 1 and 3. A
recurrent OFF feature reaches S/N **9953.360729163656** under the same motion
template only **8.381903171539307 Hz** away. The candidate track also exceeds
the frozen single-epoch S/N 5.5 floor in an adjacent OFF scan. This specific
event satisfies the original v0.5 `rfi_veto_local_off_source` rule and also
lies within the audit's strict literal-20-Hz local radius.

## Measured completeness

Completeness injections used real `m36_1412p5` background, 32 trials per
level, active epochs 1 and 3, four exact truth templates spanning the
high-smearing bank, and frozen seed `362120260826`.

| Ideal single-epoch S/N | Multichannel recovered | One-channel recovered |
|---:|---:|---:|
| 8 | 0/32 | 0/32 |
| 12 | 0/32 | 0/32 |
| 16 | 0/32 | 0/32 |
| 20 | 5/32 | 4/32 |
| 24 | 16/32 | 8/32 |
| 32 | 24/32 | 9/32 |
| 40 | 24/32 | 9/32 |

The first tested level with an observed multichannel recovery fraction of at
least 50% is ideal single-epoch S/N 24, where 16/32 injections were recovered.
Observed multichannel recovery was 24/32 at both S/N 32 and 40, so no 90%
level was measured on the frozen grid. The one-channel result was 9/32 at the
two highest levels and never reached 50% on the tested grid.

At S/N 40, the truth templates with projected scales 0, 0.5, and 0.75 each
recovered 8/8 multichannel injections, while the most extreme scale-1,
phase-+0.2 template recovered 0/8. The extreme injections cross a mean 23.829
channels per integration. The measured comparison supports an advantage for
the multichannel configuration over one channel for the tested low- and
moderate-smearing templates; it does not isolate a benefit from the widest
filters and does not make the high-smearing envelope uniformly complete.
These measurements apply only to the tested activity pattern and exact truth
templates. They are point estimates from 32 trials per level, not guarantees
for other duty cycles or orbital-model errors.

## Scope and interpretation

- The audited primary-cadence null covers five disjoint bands totaling 5 MHz,
  not the full receiver band.
- All three ON scans belong to one approximately 34-minute six-scan cadence,
  not independent observing nights.
- The null applies only to emission present in at least two ON epochs and
  represented by the frozen motion, activity, and spectral-width bank.
- The audit reuses the primary cadence. It does not establish independent
  recurrence.
- The high-smearing edge has poor measured completeness even at the largest
  tested injection level, so the null must be carried with the full
  completeness table.
- No second qualifying HIP 48714 archive cadence was identified. A future
  unresolved feature would require genuinely new data rather than another
  slice of this cadence.
- Milestone 33 remains `UNRESOLVED_REQUIRES_INDEPENDENT_CADENCE` and is not
  changed by Milestone 36.
- Milestone 35's end-to-end calibration limitations remain. Milestone 36 does
  not justify a new occurrence bound, population claim, or EIRP statement.

## Reproducibility and provenance

The frozen detector commit is
`32720a0b5e097403f864e2b84d53a071d65d7c46`. The primary preregistration,
execution, and publication commits are respectively
`c17f362028132629b5fbcc9b1c47001acc934e6f`,
`a0ceebcf1fd8fc72c81aedd20ceef93e9e5e00bb`, and
`88db2596090e3a79620bff7e0e2c42dd63560431`. Primary workflow run
`32993229561` published artifact `9616909400` with SHA-256
`a09c022c39ddc3e3e246731955b621ba741ddd9a0dfd601415fba846ef386c82`.

The primary configuration and search-summary SHA-256 values are
`b2c483a9db4075524319a0cd8e336969de4556bd0f9e5b66266a0b687f84b43c`
and `4da75de622f0ba1bb0427a54998a287a0b0dc7e641bb64bdea829bc235d01211`.
The primary data- and result-manifest SHA-256 values are
`a1c32960a21bf650433a4ff4a505aa6869d227764f1bcb2c6718121242f69aba`
and `c6e85b7016a11fa89b727bfdfd0fda9883e0804852894cea641986c4df3eb5a4`.

The exhaustive-audit protocol commit is
`3b75e26e88bce835936c8653c3d1c8274cb40710`, and its protocol-manifest
SHA-256 is
`c582e32c4e1ff271105f0c70ce2491bb4f7153248ce7a929783dbefed756e278`.
The audit execution commit is
`7f42ea59396d7fbb5d317043f4d99f6146632c7f`; the atomic audit-publication
commit is `bd7ff6c196d052d952af18b578d29fe5aad6e20c`. Audit workflow run
`33002845444` published artifact `9619833897` with SHA-256
`6ccdea821e31bb4fa8f2f1fb17543c452a6857efd2913690b3da59b59efae58c`.

The published audit-summary SHA-256 is
`2f2f375b92e3b3d887ebdb49b422a877020f0d77e38287cc5b70e69ae9a8f088`.
`RESULTS_MANIFEST_M36_EXHAUSTIVE_RETENTION_AUDIT.sha256` contains 28 files
and has SHA-256
`c9bb82a0e96aedffb9a3d39b8b6c5600877cb3280cb5e5c552c930baccc9dfc4`.
The audit-provenance SHA-256 is
`c2b53fed780bfa818f9fef7c27bf39d8717f74bf7328afb0c4d5832e0372657b`,
and the publication-manifest SHA-256 is
`4975802eab995833c1897cd01c7624c17356b3a8c0ec6114dbfd72d61af927c3`.
Extracted telescope slices are not committed.

## Independent final publication verification

Workflow run `33006228557` independently revalidated both the primary and exhaustive-audit artifact ZIP digests and every archived byte, all published manifests, 3,360 hypothesis certificates, all 7,571 above-threshold coverage-ledger rows, all 1,081 audited union records, the member-level physical dispositions, the closed stopping outcome, execution provenance, atomic audit publication, and the frozen pre-verification report hash. Its machine-readable receipt is `MILESTONE_36_PUBLICATION_VERIFICATION.json`.
