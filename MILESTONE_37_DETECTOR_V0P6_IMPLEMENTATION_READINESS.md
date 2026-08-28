# Milestone 37 detector-v0.6 implementation readiness

Status: **NON-FROZEN IMPLEMENTATION CANDIDATE — NOT READY TO FREEZE OR
AUTHORIZE SPECTRAL ACCESS**.

This is a prospective software-readiness inventory. It is not a
preregistration, detector release, spectral authorization, or scientific
analysis. During this Milestone-37 readiness activity, no rank-37 telescope
spectral value was opened, read, or inspected, and no signal, null,
sensitivity, occurrence, or population claim is made.

The machine-readable inventory is
`results_m37_v0p6_implementation_readiness/readiness.json`. It records the
local environment separately from the candidate pinned environment and marks
every unresolved gate fail-closed.

## Implementation snapshot

The readiness inventory was produced from a candidate based on commit
`e22ea2297185202defd366356ed6fe9053cd6643`, while the implementation was
still a dirty working-tree snapshot. That exact 31-file snapshot was
subsequently preserved in local checkpoint
`130babbc2f462be9fde8920c5648f4eb745b2ea4`; it remains unpublished. The
candidate inventory has aggregate SHA-256
`fb2cb962b4fa4cd20b7aa4c5f8f57bed56bf8dd73d814d4da0059d9da35011ea`.
That inventory covers `.gitignore`, `pyproject.toml`, the extractor, all v0.6
Python/C modules, all v0.6 tests, and the five code-pinned scramble resources.

Detector v0.6 remains isolated from the historical v0.5 source. The package
metadata still says `0.5.0`, while the new core identifies itself as
`0.6.0-development`; this mismatch is intentional during development but is a
release blocker.

The candidate now implements and locally tests:

- direct `P_v_i(q) = q * F_v_i` tracks for the code-pinned candidate
  93-template bank;
- native-channel width filtering before q-track gathering, with a 747,793-bin
  support grid cropped to 747,665 scored bins;
- immutable native caches, two-pass moving masks, 256 explicit scramble
  shifts, native OpenMP calibration, exhaustive threshold retention, exact
  OFF and adjacent-OFF evidence, receiver-frame signatures and alias
  components, global rank-p significance, and the five-window final join;
- an authorization-gated HDF5 adapter that retains header-native descending
  order until the source factory performs the single canonical reversal and
  exact float32 normalization; and
- a provisional 512-truth by 12-S/N completeness allocation with 6,144
  exhaustive trial identities and synthetic/candidate receipt objects and
  schemas;
- a deliberately non-production sparse/local reference layer for capped,
  synthetic truth-local gather, mask-closure, and score equivalence checks.

## Local verification completed

The local v0.6 unittest discovery ran 162 tests in 69.756 seconds: 161 passed,
no test failed or errored, and the environment-gated exact-grid benchmark was
the one expected skip. That benchmark was then enabled separately and passed
over 747,665 q bins and 256 scrambles:

- kernel wall time: `0.365522 s`;
- coded Python-loop comparison baseline: `9.696 s`;
- observed local speedup: `26.53x`;
- process peak RSS: `95,846,400 bytes`, below the 512-MiB cap;
- output SHA-256:
  `ec7baa1b7e7f5089dac5cf321c7f5294806057aaf1a2a68f7b56dcb99a8321d4`;
- local native identity:
  `8e9da16a0c3d6823efcfb02d120b0611031a1e8abfdc139a60a09b52a0e83e52`.

That native identity and timing describe only this local GCC 13.3/OpenMP host;
they are not final frozen execution identities.

Seven Astropy-independent v0.5 tests also passed. Four additional legacy test
modules could not be collected because Astropy is absent locally, so the full
legacy regression must be repeated in the final pinned environment.

The packaging audit built an sdist from a staged-like source snapshot, then
built and installed a wheel only from the unpacked sdist. All 29 packaged
Python, C and scramble payloads were byte-identical across source, sdist and
wheel, including exactly five 6,144-byte scramble tables. No `.h5`, `.fil`,
`.raw`, `.npy`, or `.npz` payload was present. The local artifacts were:

- sdist SHA-256:
  `a5af70db371194d977904d930501d301ba04ad4656fbe9c75fbc3227e96815e0`;
- wheel SHA-256:
  `d175f5ebb63584c91cd45445668c3cab5de04030c4acdd21c292975859ea3b65`.

The installed wheel also imported the sparse/local module, exposed all five
scramble resources with their code-pinned hashes, and compiled the packaged
native kernel to the same local execution identity.

The repository-wide `data/` ignore rule initially hid those five package
resources. Narrow unignore rules now expose only
`src/seti_repeater/data/m37_scrambles/*.bin`, and both distribution artifacts
contain them. This is not yet a clean-clone certificate because the files
still need to be included in the eventual implementation commit.

## Capacity evidence and remaining feasibility gate

The candidate source-accounting gate projects the permitted scan-at-a-time
background peak at `418,203,096 bytes`. A forbidden design retaining three
source products plus three normalization rolls requires `550,168,200 bytes`
and is rejected before `np.roll` against the `536,870,912-byte` cap. A
separate mask-accounting known-answer test reaches `522,000,000 bytes` and
proves that template-stage scratch participates in the gate; it is not a
measured production peak.

Production completeness remains deliberately disabled. Each trial requires
`2,225,051,040` observed score cells, and the full 6,144-trial design requires
`13,670,713,589,760` score cells.

A seven-test phase-1 sparse/local KAT now passes for three synthetic templates,
all eight widths, three epochs and all four activity subsets. Its label-keyed
inventory contains 72 non-vacuous per-epoch gathers, 24 distinct isolated
width-mask cases, three final masks and 96 distinct scores that each contain
both finite unmasked and negative-infinity masked cells. Its dense gather is
produced by `materialized_reference_gather(...)`; the native-cache full gather
and sparse gather reproduce the selected cells bit for bit. The same is true
for coordinate-aware two-pass masks and hypothesis scores. Concrete witnesses
cover the circular roll seam, nearest-native half-bin tie, both inclusive
20-Hz score endpoints, and overlapping/touching clipped mask closure. Literal
fixture, artifact and receipt roots reject zero-payload, relabelled-epoch and
alternative-plan substitutions. A second-agent adversarial review of this
phase-1 sparse-KAT code found no remaining blocker or high-severity issue
within that scope. This is not the independent verification required for
release. The observed, code-pinned local KAT identities are:

- fixture SHA-256:
  `b3ec37255a43219a7bc6bb84d4e22df60a98458910c02262096b69c72817fcc1`;
- plan inventory SHA-256:
  `02fbcb46e7766fe042563f284cdb18ab1e84f6aafd2b16e873aa64356b96f66d`;
- receipt SHA-256:
  `32e9208579e435be0cefa72c13e579c8020ec361f23fa9650e9adbf25cfe9201`.

The later phase-2 synthetic reference now extends this numerical-core receipt
through byte-identical ON/OFF retention, all three retained-OFF disposition
branches, and inclusive rank-p values below, equal to and above the scientific
ceiling. It deliberately requires a complete dense-score oracle capped at
1,000,000 cells. The phase-3 physical reference binds that exact ancestry
through complete synthetic single-adjacent-OFF evidence and receiver-frame
alias connected components. It covers the inclusive adjacent threshold, a
transitive five-node/two-component identity partition, match/no-match branches
and all five final dispositions. The phase-2 receipt SHA-256 is
`1d70d05ac7b7888cf8071bcbe894bd67bae24fba87636c6c17945b982cf0ca09`.
The phase-3 receipt SHA-256 is
`ef46ff54d69fdad918ca2d05d2c27896ae3ee53ecd0c2a20970003738d9a1f11`.
Neither phase proves a production sparse algorithm, production receipt
ancestry or production resource feasibility.

Accordingly, the production wrapper still hard-fails with
`mandatory-full-replay-benchmark-not-yet-passed` until either:

1. the complete replay is benchmarked successfully, or
2. a separately reviewed sparse/local path extends the passed phase-1 and
   phase-2/phase-3 KATs through production receipts and the full resource
   envelope without relying on a production-scale dense oracle.

## Blocking gates before a freeze

1. Commit the complete implementation and package-resource inventory, then
   repeat the sdist-to-wheel audit from that exact clean commit.
2. Implement a concrete end-to-end M37 operational runner.
   `CompletenessOperationalPipeline` is currently only an interface Protocol;
   component integration tests are not a production replay. The missing
   artifacts, streaming APIs and restart contracts are mapped in
   `MILESTONE_37_DETECTOR_V0P6_OPERATIONAL_RUNNER_GAP_ANALYSIS.md`.
3. Close the production-completeness feasibility gate described above.
4. Reproduce the factor table, derived analysis contract, all v0.5/v0.6 tests,
   native identity, exact-grid timing, and peak-resource measurements in the
   final pinned environment.
5. Add and pin the extractor runtime (`fsspec`, `h5py`, `hdf5plugin`) and bind
   the OS, compiler, OpenMP runtime, CPU/ISA policy, and a host supplying the
   required eight execution threads.
6. Resolve the distribution/detector version mismatch.
7. Publish a final v0.6 preregistration, immutable manifests, atomic execution
   and stopping workflow, and independent verification.

Only after all seven gates pass may a separate authorization permit the six
rank-37 HDF5 payloads to be contacted. The future threshold, extraction and
cache receipts, data manifest, candidate outcome, and measured completeness
are intentionally absent at this phase.
