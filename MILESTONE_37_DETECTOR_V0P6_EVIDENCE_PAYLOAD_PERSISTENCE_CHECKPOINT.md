# Milestone 37 detector-v0.6 evidence-payload persistence checkpoint

Status: **NON-FROZEN SYNTHETIC CHECKPOINT — COMPLETE PHYSICAL EVIDENCE
PAYLOAD PERSISTENCE PASSED — PRODUCTION GATE BLOCKED — NO SPECTRAL ACCESS**.

This checkpoint makes the complete receiver-frame and single-adjacent-OFF
execution result restartable instead of preserving only its compact resource
envelope. It was implemented and tested without opening, requesting or
inspecting an HD 156668 / HIP 84607 telescope spectral payload. It is not a
detector release, preregistration, search, completeness result, null result or
signal claim.

## Closed bounded gates

- The complete execution result now has a public validator. It independently
  verifies the top-level result identity, the full receiver-signature product,
  the full single-adjacent-OFF evidence product and the compact aggregate
  resource envelope.
- The validator requires the complete evidence payloads to reproduce the
  receiver result, receiver certificate, adjacent evidence, adjacent
  certificate and ON-retention identities already bound by the resource
  envelope. A rehashed top-level object cannot hide a changed inner payload.
- A complete execution result can be published as canonical read-only JSON
  with a 208,777,216-byte hard cap. The cap is the sum of two frozen
  96,000,000-byte evidence caps and the 16,777,216-byte resource-envelope cap.
  Publication is no-replace, fsyncs the file and fsyncs its parent directory.
- Restart opening requires independently supplied file, execution-result,
  resource-envelope, run, cache-manifest, factor-bundle and ON-retention
  identities before returning the complete receiver and adjacent products.
- The M37 wrappers reapply the exact M37 window, width, grid, bank, factor,
  scan and 512-MiB mapped-resource contract. The bounded synthetic fixture is
  rejected before an M37 artifact can be created.

## Synthetic known answers

The one-window fixture persists the complete evidence generated from six real
read-only synthetic native-cache files and reproduces both inner products
exactly after a process-style reopen.

| Artifact | Value |
|---|---|
| Complete evidence artifact file SHA-256 | `a2560965b199ca8c1dbeeb81982d3679341f39f0f6fb5951450ff36c34aa0c91` |
| Complete evidence artifact canonical bytes | `17,632` |
| Complete execution result SHA-256 | `6d323d2142bfc195514ccd8955331d8e30f2175f37fa8b26324baf89b9e919e7` |
| Physical resource envelope SHA-256 | `f64d93cdb027d09ca6486bd533b48990b11c16451fc5c8b2b57c89bd4e898191` |
| Receiver result SHA-256 | `be886ec787b23625f9e63a5b9bd2b16c422c01cea4aa85d22ce4f7d3b3eda1f5` |
| Adjacent evidence SHA-256 | `0a52766c9d4aee16a4f814fc9dce79f896395e16db5080d37ac369de4a387bd8` |
| Offline wheel SHA-256 | `6ab621004c62c2b8358cbeb2f6c3c686a3780981458ac6e7e33f60a6c2956ecb` |

The measured aggregate peak remains 81,600 mapped bytes and three handles,
with two sequential batches and six cache opens. These are bounded synthetic
contract values, not M37 production measurements.

## Verification

| Check | Result |
|---|---|
| Targeted cache-stream, receiver, adjacent and resource suite | 36 passed, 0 skipped, 0 failed |
| All Astropy-independent repository tests | 210 run, 209 passed, 1 expected benchmark skip, 0 failed |
| Dependency-complete repository suite | Blocked in this runtime: declared `astropy>=6.0` is absent; expected total is now 272 tests |
| Offline wheel build, isolated install and evidence-module import | Passed |
| Complete canonical read-only round trip | Exact |
| Rehashed inner receiver payload | Rejected |
| Wrong independently supplied ancestry | Rejected |
| Generic synthetic execution published as M37 | Rejected before file creation |
| HD 156668 spectral files contacted | No |
| Spectral dataset values read | No |

## Claim boundary and remaining blockers

This closes complete evidence-payload persistence only for the bounded
one-window synthetic resource fixture. The existing run manifest still points
to compact per-window resource artifacts; it does not yet inventory these
complete execution artifacts. No exact five-window M37 resource/evidence
inventory exists.

The persisted receiver and adjacent products are not a final physical-
disposition result. They still need to be joined to the retained-OFF and
receiver-alias disposition receipt, then bound through a complete five-window
inventory before any journal transition can honestly represent physical-stage
completion. Production cache and retention ancestry, the completeness
feasibility gate, the pinned runtime and the authorized extraction-through-
outcome lifecycle remain blocked.

The machine-readable checkpoint is
`results_m37_v0p6_evidence_payload_persistence/progress.json`.
