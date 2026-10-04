# Hosted exact-CAS control 20261004a: CLOSED_FAILED, first update observed

The original attempt ran once. GitHub accepted the first exact E -> A update,
but the stale E -> B request returned a generic internal GraphQL error. It did
not return the preregistered expected-head conflict evidence. The control closed
failed, its child exited with code 1 and was reaped; no retry or replacement was run.
Lossless control/observer evidence was successfully published and read back.
This is not a passing service qualification or scientific-store certificate.

## Immutable preparation and actual run

The [prospective protocol](RADIO_HOSTED_CAS_CONTROL_2026-10-04_PROTOCOL.md), ten
selected source files, manifest and retained development evidence were published
at `c14b63dd0cbbc70b6c78d43c52b8c6cea618fef1`, tree
`339cd8fbb89ee37e572b2207f39dbb9c5efe6b48`, sole parent
`3cbe40846602a3f8964639db0d1b6d1252bf44a7`. Every one of the 50 changed files
was read back in full and compared exactly. The ten execution/source files total
179,599 bytes. Final 90 synthetic tests passed with unchanged before/after source
hashes; all named development failures and their available snapshots remain.

Manifest SHA256:
`250fbb31bb183d2ba0ee380901617a008f44d896d9b4f5a2f9c120758c543da3`.
Canonical ten-source inventory SHA256:
`5202bebc5334c5a261d50eec11f9acdff4ba443c41fa35be7918b2d3b2b5dc10`.
Marker-only activation E was
`d4d38a0a4316b36197c3a18e33c1369f96e7d29a`, sole preparation parent,
tree `b75a4db629539e78649fe68aae8c48cf0928d71b`. Marker content and sole added
path were read back before the branch update triggered the original push.

[Actions run 37201924254](https://github.com/andersenmartin-blip/setisearch/actions/runs/37201924254),
job 111435213248, is completed/failure, run number 1 and attempt 1. Service timestamps
record 12:23:17Z–12:23:41Z on 4 October. The activation gate passed. The supervisor
exited with code 1; `continue-on-error` makes the displayed control-step conclusion success,
while its actual outcome is failure, confirmed by the final workflow assertion.
Administrative evidence publication succeeded. No rerun/dispatch occurred.

## Accepted edge, then an unqualified server error

The retained 29 numbered request/response/journal records show:

| Calls | Actual observation |
| --- | --- |
| 1–14 | Original workflow/head/source/manifest checks and immutable A preparation/readback; head E immediately before mutation |
| 15 | Fixed `updateRefs`, expected E, exact A, `force:false`, fixed namespace; successful exact acknowledgement |
| 16–20 | A immutable commit/root/owned tree/blob readback and head A |
| 21–28 | Pre-create B, sole parent A, distinct added conflict metadata blob; immutable readback and head A |
| 29 | Stale expected E -> B mutation; HTTP200, generic internal-error JSON, then immediate closure |

A is `596f0fb45337f2af475f73fabef34073c3c74a2c`, sole parent E,
tree `cab55fd9eae72bc27ed1c316f4186d95ad05aaf7`. Its only addition is normal
`results_radio_hosted_cas_control_20261004a/service-state.json`, blob
`0e522c0cbfb36a97bbcbff77cf2e8c9ac8b268bf`. Fixed unsigned UTC commit metadata
and complete modified Git object identities matched their intrinsic hashes.

B is `82dc9309f398f9499ada0212bfa704a147151dda`, sole parent A. It separately
adds `conflict-test-state.json` and preserves A's state and all unrelated tree
entries. Thus B was a fast-forward from actual A, while the expected revision
was deliberately stale E. The retained graph contains no accepted publication
of B; the administrative commit instead has parent A. The raw-service
negative probe intentionally differs from a valid scientific candidate-parent
contract and grants no scientific authority.

The actual response at 29 contains only an `errors` entry referring to an internal
failure at `2026-10-04T12:23:31Z`, diagnostic
`C7D5:37A3EE:B3BEE2:25412FB:6AC24543`. It has no `data.updateRefs:null`, no
error path and no named expected-OID condition. The unchanged frozen checker
therefore refused it. There was no 30th control call, direct post-negative head
check, post-negative B readback or child runtime-after inventory. Later publisher
head A and independent immutable B checks do not retrospectively complete those
missing control steps or prove an authenticated expected-head conflict.

## Whole-child observation and bounded archive

The child ran 9.300751151 seconds, exited with code 1, wait status 256, and was reaped at
9.297172021 seconds. Full stdout is 14 bytes (`CLOSED_FAILED` plus newline); stderr
is empty. wait4 peak RSS is 30,617,600 bytes. 155 procfs samples record a sampled
aggregate child peak 28,971,008 bytes and parent point-sample peak 23,322,624 bytes.
The sampled limits and short-lived/escaped-descendant limitations are unchanged.

The child recorded 29 HTTP calls, two mutation attempts and 2,445,260 charged
request-envelope/reply bytes. These numbered retained application records are
independently countable. Headers/TLS framing and hidden provider work are outside
this declared accounting domain. The archive's original scope records 3,083,774
logical and 3,469,312 allocated bytes including directories, below 8 MiB. These
allocation values are original runner observations; copying the archive does not
independently reproduce the runner filesystem's physical allocations.

The supervisor's ten sources and selected runtime hashes matched before/after.
The child captured its selected current Python 3.12/runtime inventory before the
calls but did not reach its own after inventory. The hosted image is logged as
Ubuntu 24.04.5 / image 20260927.320.1, runner 2.337.0. The job log also records that
pinned checkout's Node 20 action was forced to Node 24 by the provider. No complete
bootstrap/hosted-image/ELF/session freeze is inferred from these observations.

The separate publisher reports 19 calls, 5,401,964 charged application bytes and
successful administrative exact-CAS publication. Its complete HTTP transcript is
runner-local and excluded from the archive; the final safe receipt is retained in
the job log. Those publisher totals are self-reported, rather than independently
recomputed from a public full publisher transcript.

Administrative commit `c253ba95e096f983c0bc3afa81b6e669f8fc0cb7`, tree
`92a21c4a392985c239a19cac5557df4bf1e9f01d`, has sole parent A and exactly one
normal added [evidence.json](results_radio_hosted_cas_control_20261004a/evidence.json).
Its blob is `9854ea7b9c59f163a237f81f7cc0728a08137449`, length 941,861 bytes,
SHA256 `e1a61f7497490b8530771bff6ab16f643b241982f0618c6285c53ff954b6eba3`.
All 117 gzip/base64 members decoded losslessly with exact declared lengths and
SHA256. Full public archive readback and the entire current local Git tree matched
the administrative publication, independently preserving every earlier object.

Readonly independent reviews are retained in
[actual-independent-review.md](results_radio_hosted_cas_control_20261004a/actual-independent-review.md)
and [actual-service-object-review.json](results_radio_hosted_cas_control_20261004a/actual-service-object-review.json).
They separate the genuine initial acceptance, retained server error and eventual
publication graph from the failed prospective negative-control claim.

## Permanent closure and remaining genuine gate

The original identity is CLOSED_FAILED and permanently spent. Its 300-second/
20-MiB allocation is not refunded; selected live engineering reservation subtotal
is now 910 seconds/40 MiB. This is not complete historical/bootstrap/hidden-platform
accounting. All prior spends, retired identities and 54 old connector-call
reservations remain unchanged. No new live successor is allocated by this report.

The actual missing service input is a definitive authenticated expected-head
conflict outcome, followed by the frozen immutable/head confirmation. Any future
scientific integration still requires a fresh complete prospective contract,
unchanged candidate-parent law, complete authentic callback/runtime/source/session
certificates and fresh irrevocable scientific allocation. This original attempt
cannot be retuned or resumed. Preserve the concrete failure until genuinely new
capability/input exists; no automatic replacement probe, target change or plan
extension. Consolidate **9 October 2026**.

All eleven genuine scientific fields remain pending: complete execution/code/input/
runtime freeze; HDF5 runtime; source-specific codec/case-law certificate; complete
127/24 certificate; joined hosted transport certificate; source-specific executable
trial protocol; cumulative limits; reservation store; public acquisition-ledger
revision/hash; fresh irrevocable acquisition/trial allocation; and new executable
source-contract hash. The original scientific store is unchanged. HD189733/neighbor9
remain selected, HD1461 HOLD and GJ724 untouched reserve. Original 112 M43AF spectra
and 128 null holdouts stay unopened, native8 unreserved and 127/24 NOT ACTIVATED.
All native/M43/M15/M33 dispositions, LS pause/BF restart and CHEOPS UNSENT remain.
No person messages were sent.
