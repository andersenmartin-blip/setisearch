# Local codec/direct boundary and v2 publication protocol

Scope: engineering continuation of execution envelope
`4f4fc7f477e1f0617632a314a99d95f719d17943ea294700559be675590593f6`.
This protocol grants no telescope access or candidate-selection authority.
The parent envelope and original preparation contract remain immutable.

## Codec-to-direct boundary

The entry point is `codec_direct_radio.fixture_run(context, binding, directories)`.
Its independently retained binding SHA identifies an ordered six-scan manifest.
Each entry binds an exact codec receipt and canonical source scope, including
definition, URL/ETag/size, header, extraction interval, ascending geometry and
the new-extraction normalization origin. Only `local-fixture` sources at
`.invalid` hosts are accepted. Telescope receipts cannot be converted here.

Before reading native rows, validate the binding, codec runtime, direct-factor
bank, source-contract hash, complete scan inventory, context window and modeled
cadence memory bound. The bank's relative clock must agree with the fixture
headers to 1 microsecond. This is a fixture consistency tolerance, not a new
astronomical timing or ephemeris qualification.

Then validate each receipt against its external manifest pin, check local
simulated-transport ancestry and checkpoint integrity, and use the existing
row rehydration checks. Hash the actual owned raw bytes again at use time to
detect a change after rehydration. Reverse descending native channels and apply
the unchanged float32 normalization. Every normalized row must have the codec
receipt's exact hash. Inputs are immutable `SyntheticSource` objects whose
scope retains the binding, codec receipt, scan, window and direct-bank identity.
They remain synthetic/local fixture evidence.

The new test compares this entire boundary with the independent sort-based
normalization and direct-window score oracle for both actual gzip and
bitshuffle/LZ4 decoders, all six scans and all eight supported widths. Its
synthetic three-template bank is an interface fixture, not the HD1461 bank.
No calibration, threshold selection, detector execution, trigger retention or
scientific control panel is performed.

## Ordered-role publication boundary

`publication_role_radio.BoundRoleStore` binds the local store location,
resource-contract hash, source-inventory hash and empty-genesis identity.
Callers must also supply their independently retained revision and ledger hash
on every reservation. The underlying `LocalRoleStore` remains a low-level
atomic CAS primitive; it is not by itself an append-only policy boundary.
Future v2 controllers must use the guarded boundary.

One permitted publication must preserve the entire root and old reservation
prefix, append exactly one role reservation, bind its prior-ledger hash, and
pass the existing ordered-role/cumulative-limit validator. A locally coherent
reset or identity replacement is insufficient and is rejected. The backend
must compare revision and content under its exclusive lock before atomic
replace and directory fsync. A successful caller also verifies the returned
location, next revision and exact persisted content.

The protocol never refunds an ambiguous publication or retries it automatically.
A lost reply can leave a durable spent reservation. Caller-held stale parents
must be refused. A failed confirmation returns no network budget. The local
proof assumes a trusted CAS backend; it is not protection against a privileged
external writer replacing the entire filesystem and every caller-held pin.

## Frozen future GitHub store

The machine-readable specification is
`results_radio_codec_publication_2026-09-27/publication_store_spec.json`.
It fixes the repository, science branch, prospective ledger path, resource and
genesis hashes, canonical document encoding and these publication obligations:

1. Read the branch head/tree and the ledger at that exact commit. A missing
   ledger is a stop, never permission to create or reset it.
2. Require the caller's expected branch head and ledger hash. Verify all pinned
   identities and the full single-append transition before creating Git data.
3. Create a tree changing only the pinned ledger path, with a commit whose sole
   parent is the expected head. Update with `force=false`.
4. Verify the committed bytes and current branch ancestry. If a competing writer
   changed the head, a response is lost, or confirmation is inconsistent, stop;
   no quota is issued or refunded automatically.

The named prospective ledger path does not exist and is not created by this
package. Initialization requires a separately published activation after the
scientific/source gates and integrated prospective protocol are satisfied.
This is a pinned remote specification, not a qualified remote backend.

## Budget and scientific boundaries

Local temporary stores may simulate the fixed calibration, validation and pilot
reservations to verify policy. Such files are discarded test fixtures; no
reservation is added to either published ledger. The old exhausted synthetic
demonstration is preserved, and the prospective telescope genesis remains at
zero reservations. The 500-request/512-MiB/1200-second per-role and cumulative
1500-request/1.5-GiB/3600-second ceilings are unchanged.

All five parent blockers remain false: pointing provenance, telescope codec
handoff, physical motion qualification, numeric cross-window transfer and the
fresh recovery/RFI/null evaluation. `neighbor9`, prior failed evaluations and
reserved holdouts are unchanged. No closed science result is rerun as evidence.
