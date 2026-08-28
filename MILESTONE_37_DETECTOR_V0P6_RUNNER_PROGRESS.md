# Milestone 37 detector-v0.6 runner progress

Status: **NON-FROZEN BOOTSTRAP AND PERSISTENCE CHECKPOINT — NO SPECTRAL
ACCESS**.

The original component implementation is preserved in local checkpoint
`130babbc2f462be9fde8920c5648f4eb745b2ea4`. This follow-on closes the first
operational-runner gaps without opening, requesting or inspecting an HD 156668
/ HIP 84607 telescope payload. It is not a detector release, preregistration,
search, null result or signal claim.

## What now works

- The exact 96-row M37 factor basis was reproduced under Astropy 8.0.1 and
  NumPy 2.5.2. All published basis, label, scan, ON-row and OFF-row identities
  match. The derived 93-by-96 factor-table identity is
  `a4d87d8813ec63ff7f3392f5073038f3dc47a9707796a745dd4e752588255fa4`.
- One read-only atomic factor bundle persists the basis, labels, template
  bank, scan inventory, factor table, proxy-grid identities, scramble
  identities, environment and source hashes. A new process rehydrates it only
  against independently supplied file, manifest and factor-table digests.
- A persisted native-cache plan can be reconstructed from its canonical
  manifest record and independent plan digest.
- A run-level cache manifest binds an exact ordered cache-key inventory,
  plans, logical paths and receipts. Its M37 wrapper requires exactly 240
  entries: five windows, six scans and eight widths. Actual M37 cache creation
  remains inapplicable before authorized extraction.
- The exact global-null vector now has a threshold-certificate-bound
  persistence format. Actual M37 use remains inapplicable before calibration.
- The run journal is append-only and hash chained. It rejects a stale restart
  head, missing/repeated/reordered stages, altered history and every attempt to
  continue after `invalid` or `published`.
- The journal cannot cross the spectral boundary unless the next event carries
  the exact `m37-hd156668-six-hdf5-extraction-only` scope and an independent
  authorization-receipt SHA-256.

## Real metadata-only bootstrap

The new bootstrap runner reproduced the factor bundle, created the journal and
then stopped at `factor_bundle_ready` as required. A separate process reopened
and revalidated all three artifacts.

| Item | Result |
|---|---|
| Bootstrap identity | `9edb59cbfcc2c20ac64eb9748cf10e8b545096fbf3705d3f53140ab295a1a569` |
| Factor-bundle manifest | `bac04d6b7c8a4e0949373a8971b9f02d0b525ff022d8e5c48b19adbdae403691` |
| Factor-bundle file | `f71cd0c0d9f5aae9299d41783e549947e6bb72bcc5c92028a139736830e5fc8a` |
| Analysis contract | `726571e7b56b684f06ff69bbd6ae70b4c191268d25db8eadfcb8b6e841dc9f2e` |
| Journal stage | `factor_bundle_ready` (2 events) |
| Spectral access authorized | `false` |
| Spectral dataset values read | `false` |

## Verification

- Expanded v0.6 suite: 188 tests, 187 passed, one expected benchmark skip,
  zero failures or errors.
- Full repository suite with Astropy present: 247 tests, 246 passed, the same
  expected skip, zero failures or errors. This removes the earlier local test-
  collection blocker for the legacy modules.
- The exact-grid benchmark passed separately in 0.307609 seconds, 31.52 times
  faster than the recorded 9.696-second Python baseline, at 100,712,448 bytes
  peak RSS. Its output hash remains
  `ec7baa1b7e7f5089dac5cf321c7f5294806057aaf1a2a68f7b56dcb99a8321d4`.

## Remaining blockers

1. Receiver-frame and adjacent-OFF evidence still need width-at-a-time cache
   streaming, arena accounting and bit-identical comparison with the present
   full-inventory functions.
2. The sparse/local completeness reference must extend through exhaustive
   retention, OFF/adjacent disposition, receiver-alias dependencies, rank-p,
   production receipts and the full resource envelope.
3. Only after those pass can the bootstrap become a complete production
   runner and receive a final preregistration.
4. The final runtime must still pin Python, extractor dependencies, OS,
   compiler, OpenMP runtime, CPU policy and the eight-thread execution host.
5. The implementation checkpoint and this runner extension are not yet on
   `main`; publication requires the separately requested default-branch
   approval.

The machine-readable status is
`results_m37_v0p6_runner_progress/progress.json`.
