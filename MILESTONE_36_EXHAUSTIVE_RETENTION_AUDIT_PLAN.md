# Milestone 36 exhaustive above-threshold retention audit

Status: **FROZEN AFTER THE PRIMARY RESULT AND BEFORE RAW-DATA
RE-EXTRACTION**.

This is a retrospective, significance-neutral supplement. It does not alter
the Milestone 36 preregistration, detector, primary files, empirical p-value,
operational threshold, or completeness result. It closes or exposes one
specific proof gap in the candidate-retention layer.

## Why the supplement is required

Detector v0.5.0's `collect_hypothesis_peaks()` examines only the 15 largest
score cells in each width/orbit/activity hypothesis and then stops after at
most three non-adjacent peaks. The prospective proof that `2200 > 2016`
shows only that the later cluster report cap did not truncate those already
admitted records. It does not prove that the earlier 15-cell pool and
three-peak stop retained every threshold-crossing feature.

The published summary itself establishes a concrete boundary:

- 3,360 frozen hypotheses were searched;
- 3,165 can be closed without reopening spectra;
- 192 remain logically exposed to the 15-cell pool;
- three additional width-129/all-epoch hypotheses in `m36_1425p0` hit the
  three-peak stop while their third retained peak was still above the global
  threshold;
- therefore 195 hypotheses cannot be certified from the summary alone.

The exact summary-only inventory is
`MILESTONE_36_RETENTION_BOUND.json`, SHA-256
`35fd0d940dd73af6c49b274e686fa0230bfb756427f6473b76f93107d2a8e3f3`.
Its sorted unresolved-tuple CSV has SHA-256
`8d9504a3845f4f80d9d4e51187d1c4ef009d7d8579cab0d4d8bb4d8521d86a13`.
The raw-data audit nevertheless recomputes all 3,360 hypotheses, avoiding a
post-result subset optimization and supplying a direct full-space
certificate.

## Frozen primary anchors

| Item | Frozen value |
|---|---|
| Detector commit | `32720a0b5e097403f864e2b84d53a071d65d7c46` |
| Primary preregistration commit | `c17f362028132629b5fbcc9b1c47001acc934e6f` |
| Primary execution commit | `a0ceebcf1fd8fc72c81aedd20ceef93e9e5e00bb` |
| Primary publication commit | `88db2596090e3a79620bff7e0e2c42dd63560431` |
| Primary config SHA-256 | `b2c483a9db4075524319a0cd8e336969de4556bd0f9e5b66266a0b687f84b43c` |
| Search-summary SHA-256 | `4da75de622f0ba1bb0427a54998a287a0b0dc7e641bb64bdea829bc235d01211` |
| Data-manifest SHA-256 | `a1c32960a21bf650433a4ff4a505aa6869d227764f1bcb2c6718121242f69aba` |
| Result-manifest SHA-256 | `c6e85b7016a11fa89b727bfdfd0fda9883e0804852894cea641986c4df3eb5a4` |
| Held-out provenance SHA-256 | `11ed24d83a83b35030ed65f9b90ecc66a90a2f0da4a62cc3367eaac9def5d53b` |
| Operational threshold | S/N `15.89224910736084` |

The machine-readable specification is
`config/hip48714b_m36_exhaustive_retention_audit.json`. It also freezes the
primary artifact identity, source-file hashes, exact runtime, dimensions,
enumeration rules, and stopping outcomes.

## Spectral boundary and integrity gates

Only the six scans and five extraction windows already opened for the HIP
48714 primary cadence may be re-extracted. All 30 reproduced NPZ files must
match `DATA_MANIFEST_M36.sha256` exactly by logical path and SHA-256. Ranks 37
and 38, every other target or cadence, candidate-local cutouts, and reserved
data remain closed.

The runtime is Python 3.12.14, NumPy 2.5.2, Astropy 8.0.1,
astropy-iers-data 0.2026.8.24.0.24.29, pyerfa 2.0.1.5, Matplotlib 3.11.1,
h5py 3.16.0, fsspec 2026.7.0, and hdf5plugin 6.0.0. Detector source and its
package definition must remain identical to the frozen detector commit.

Before interpreting any supplementary record, the audit rebuilds each ON and
OFF bank and moving mask, reruns the original top-15/top-three collector, and
requires exact reproduction of every published per-window maximum and full
`candidate_reduction` object. Any input-hash, data-hash, environment,
reproduction, enumeration, coverage, serialization, or capacity failure
invalidates the audit.

## Complete enumeration and two coverage ledgers

The audit visits all 1,202,587,680 frozen score cells: five windows times
357,913 frequency bins times eight widths times 21 orbital templates times
four activity subsets. Eligibility is unchanged: the minimum-epoch statistic,
single-epoch S/N floor, and moving single-epoch RFI mask are applied exactly
as in the primary detector. Every finite cell with score greater than or equal
to the frozen operational threshold enters both ledgers.

Each ledger sorts cells by descending S/N, with ascending frequency index as
the deterministic tie-break. A cell is selected if it has not already been
covered; otherwise the ledger records the equal-or-stronger selected owner.
There is no 15-cell pool, three-peak stop, record cap, or cluster cap.

1. The **legacy-compatible ledger** uses inclusive radius
   `max(1, width // 2)` channels. It is the unbounded extension of the
   detector's intended per-hypothesis reduction.
2. The **literal-20-Hz ledger** uses the largest whole-channel radius whose
   actual frequency offset does not exceed 20.0 Hz. At the frozen channel
   spacing this is seven channels, or approximately 19.557774 Hz. It prevents
   a broad width's legacy radius (up to 64 channels) from silently suppressing
   a feature outside the final cluster tolerance.

The candidate audit set is the union of representatives selected by the two
ledgers plus every published primary above-threshold member as a dedicated
tie crosswalk. This preserves the primary representative even if NumPy's old
partial-sort tie order differs from the audit's deterministic tie-break, and
adds any feature needed for literal-20-Hz coverage. For every hypothesis, the
audit emits counts, a canonical ledger hash, and the assertion
`unaccounted_above_threshold_cells = 0`. The compressed raw ledger maps every
threshold-crossing cell to its selected owner; suppressed cells are coverage
evidence, not independently classified candidates.

The union records are grouped with the unchanged 20 Hz frequency-clustering
rule, but every member is retained in a separate full ledger. The detector's
`top_members[:20]` presentation limit is not used as evidence. Receiver-alias
witnesses are found with a deterministic two-epoch frequency-bucket index,
not an unbounded all-pairs loop. A frozen capacity gate of 10,000 union
records per window and 95,000,000 bytes per generated file never truncates
evidence: exceeding either makes the audit invalid with no scientific
conclusion.

## Physical dispositions

Every union member is evaluated independently. A physical veto cannot be
inherited from the cluster's strongest member or from another redundant
hypothesis. The permitted physical mechanisms are:

1. matched-OFF recurrence at the same frozen hypothesis and threshold;
2. recurrent local-OFF evidence at an actual absolute offset no greater than
   20.0 Hz and the same threshold;
3. an adjacent-OFF single-epoch match on the same candidate track at the
   frozen S/N 5.5 floor;
4. receiver-frame alias evidence satisfying the frozen 20 Hz, two-shared-
   epoch, and S/N 5.5 rules, evaluated from that member's own receiver
   signature against a record in a different frequency cluster.

Detector v0.5.0 rounds its configured local 20 Hz radius upward with `ceil`,
which admits eight channels, approximately 22.351742 Hz. The audit records
that legacy disposition in parallel, but closure uses the stricter actual
`|delta f| <= 20.0 Hz` result. Arithmetic-frequency families, high template
multiplicity, and width labels remain contextual, not physical vetoes.

## Fixed stopping outcomes

- `PRIMARY_CADENCE_NULL_AFTER_COMPLETE_RETENTION_AUDIT` is permitted only if
  all integrity and coverage gates pass and every union member has at least
  one strict physical disposition.
- `UNRESOLVED_REQUIRES_INDEPENDENT_CADENCE` is mandatory if any union member
  lacks strict physical coverage. Its exact record is published, and work
  stops before plots or targeted morphology inspection. A separate
  candidate-local protocol must precede any such inspection.
- `AUDIT_INVALID_NO_CONCLUSION` applies to any technical or capacity failure.
  Resource pressure is not permission to introduce an adaptive scientific
  cap.

HIP 48714 has no second qualifying archive cadence. An unresolved member
therefore requires a genuinely new observation and is not a detection. A
closed audit remains a primary-cadence null limited to the five bands, frozen
motion and activity model, and measured completeness. It cannot improve the
primary p-value, establish independent recurrence, create a population or
EIRP bound, resolve Milestone 33, or remove Milestone 35's limitations.

## Publication sequence

The plan, specification, non-spectral inventory, audit implementation, tests,
and their manifest are committed first. Only a subsequent commit may add the
execution workflow. That workflow pins the protocol hashes and commit
ancestry, runs all detector and audit tests, re-extracts the primary slices,
executes the audit, uploads the complete evidence, and atomically publishes
either valid stopping outcome. No final Milestone 36 report may claim an
exhaustive null before the published audit satisfies the closed outcome.
