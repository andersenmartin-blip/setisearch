# Milestone 37 detector-v0.6 resource-artifact persistence checkpoint

Status: **NON-FROZEN SYNTHETIC CHECKPOINT — PHYSICAL RESOURCE ARTIFACT
PERSISTENCE PASSED — PRODUCTION GATE BLOCKED — NO SPECTRAL ACCESS**.

This checkpoint makes the bounded physical-evidence resource envelope
restartable across processes. It was implemented and tested without opening,
requesting or inspecting an HD 156668 / HIP 84607 telescope spectral payload.
It is not a detector release, preregistration, search, completeness result,
null result or signal claim.

## Closed bounded gates

- A validated physical resource envelope can now be published as canonical
  JSON with a 16,777,216-byte hard cap. Publication requires an existing
  parent directory, creates a read-only file, fsyncs its contents, refuses to
  replace an existing destination and fsyncs the parent directory.
- Reopening requires an independently supplied artifact-file hash, envelope
  hash, run ID, cache-run manifest file hash, factor-bundle manifest hash and
  ON-retention certificate hash. The complete inner envelope and both stream
  certificates are revalidated before a receipt is returned.
- The artifact receipt binds the file and envelope identities, run and window,
  the three external ancestry roots and exact canonical byte count.
- M37 publication validates the exact M37 resource contract before creating a
  destination. M37 reopening first performs the generic file and ancestry
  checks and then reapplies the exact M37 gate.
- Wrong file identity, wrong independently supplied ancestry, destination
  reuse and expansion of the generic synthetic artifact into an M37 artifact
  all fail closed.

The stored object is deliberately the compact aggregate envelope. It binds
the receiver and adjacent evidence identities and resource certificates, but
does not duplicate their complete evidence payloads. It therefore supports
restartable verification of the resource proof; it does not reconstruct
physical dispositions or authorize a journal transition to physical-
disposition completion.

## Synthetic known answers

The fixture publishes the envelope produced from six real read-only synthetic
native-cache files, reopens the artifact against independently supplied roots
and reproduces the original envelope exactly.

| Artifact | Value |
|---|---|
| Resource artifact file SHA-256 | `7a4c5e36042f687265a0ac3844ae29c6cd7803742e5d61f1512d340e5f178e48` |
| Resource artifact canonical bytes | `8,474` |
| Physical resource envelope SHA-256 | `f64d93cdb027d09ca6486bd533b48990b11c16451fc5c8b2b57c89bd4e898191` |
| Complete execution result SHA-256 | `6d323d2142bfc195514ccd8955331d8e30f2175f37fa8b26324baf89b9e919e7` |
| Offline wheel SHA-256 | `7099aa010c01b4e1d6de9046b729d15abba2c15a78f279c1057e77c31a8b7881` |

The execution known answers and measured aggregate peak remain unchanged:
81,600 mapped bytes, three simultaneous handles, two batches and six cache
opens. These are bounded synthetic contract values, not M37 production
working-set measurements.

## Verification

| Check | Result |
|---|---|
| Targeted cache-stream, receiver, adjacent and resource suite | 30 passed, 0 skipped, 0 failed |
| Full repository suite | 266 run, 265 passed, 1 expected benchmark skip, 0 failed |
| Offline wheel build, isolated install and import | Passed |
| Canonical read-only round trip | Exact |
| Existing destination | Rejected without replacement |
| Wrong file or external ancestry identity | Rejected |
| Generic synthetic artifact published as M37 | Rejected before file creation |
| HD 156668 spectral files contacted | No |
| Spectral dataset values read | No |

## Claim boundary and remaining blockers

This closes persistence only for the bounded synthetic physical-resource
envelope. Production receipt ancestry, production cache artifacts and a
complete primary-search or completeness resource envelope remain unproved.
The persisted resource envelope is not yet attached to the restartable run
journal or joined with the phase-3 final physical-disposition receipt.

No production M37 artifact can be created because authorized extraction has
not occurred and no production cache-run, retention certificate or physical
evidence result exists. The final pinned runtime, completeness feasibility
and authorized extraction-through-outcome lifecycle remain blocked.

The machine-readable checkpoint is
`results_m37_v0p6_resource_persistence/progress.json`.
