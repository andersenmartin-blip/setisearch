# Actual publication failures, retained evidence and lossless-envelope preparation

28 September 2026. Started from `42552a973f941915783592a9b783e5b48fc656dd`.
**Both live transport scopes are CLOSED FAILED.** There is no completed live case,
scientific allocation, new Gaussian value, source request or telescope spectrum.
**55 distinct new tests pass**; this does not turn either live failure into a pass.

## What was actually exercised

The [original prospective scope](RADIO_WHOLE_CADENCE_REMOTE_2026-09-28_SCOPE.md)
was published and all 22 changed files read back at
[`b0574d0`](https://github.com/andersenmartin-blip/setisearch/commit/b0574d0c1ebaa9a68d8da52828ba888889906d47).
Live01 stopped on its sixth read: the connection returned decoded JSON content
rather than the REST blob metadata assumed by the adapter. Its original genesis,
error, runtime snapshot and complete compressed transcript remain unchanged.
No consumption or branch mutation occurred in this first exercise.

The [transport amendment](RADIO_WHOLE_CADENCE_REMOTE_2026-09-28_TRANSPORT_AMENDMENT.md)
was separately published and its 21 files read back at
[`4b73352`](https://github.com/andersenmartin-blip/setisearch/commit/4b733525195a0eb641149afae612490bbe6d3dca).
Two read-only capability probes preceded it. One verified the already published
6,633-byte engineering crash archive through immutable-path/base64 access; no
crash study was rerun. Prior resources remained charged against the same ceiling.

Live02 made **four actual fast-forward commits**: consume the fresh engineering
case; publish the fixed JSON witness; register that witness; publish the two binary
chunks and their manifest. The first three commits passed exact tree-delta and
byte-readback checks. The fourth landed, but readback then failed. No retry occurred.

| Item | Preserved disposition |
| --- | --- |
| Live01 | Failed before consumption; original genesis remains untouched |
| Live02 case | Consumed, incomplete; 1,500 s and 1 MiB reservation stay charged |
| Witness | 146 bytes, published and registered |
| Binary payload | 262,161 bytes, published but **not registered** in the case journal |
| Final completion / Gaussian start | Neither exists |
| Last live branch commit | `b49a315e6312839d423a3be65b08a7935c759b74` |

[Live01 result](results_radio_whole_cadence_remote_2026-09-28/run01/result.json) ·
[Live02 result](results_radio_whole_cadence_remote_2026-09-28/run02/result.json) ·
[Independent Git readback](results_radio_whole_cadence_remote_2026-09-28/independent_git_readback.json).
The latter checks all four single-parent commits, confirms only this engineering
prefix changed, and verifies every original artifact byte. It is read-only recovery
of evidence, **not resumption or completion of the failed case**.

## The observed binary corruption

The 262,144-byte first chunk came back intact. The final **17-byte** chunk came
back as **31 bytes**, while the response still reported the original Git blob ID.
Its seven high bytes had become seven UTF-8 replacement characters. The returned
bytes exactly equal `original.decode('utf-8', errors='replace').encode('utf-8')`.
This describes the observed output; the connector's internal implementation has
not been inspected. The stored Git object itself is intact.

The encoded-size guard rejected the response. A separate retained-response test
shows that a looser size allowance would still fail the content hash. **Do not
relax either check or accept the replacement bytes.** Both full broker transcripts,
the original binary chunks, metadata, failed response and technical dispositions
are retained. The [diagnosis](results_radio_whole_cadence_remote_2026-09-28/binary_failure_diagnosis.json)
and [exact short response](results_radio_whole_cadence_remote_2026-09-28/short_binary_response.json)
make the failure reviewable without a new live request.

## Further completed engineering work

An [offline scope](RADIO_WHOLE_CADENCE_ASCII_2026-09-28_SCOPE.md) prepares a canonical
ASCII/base64 envelope from the same retained deterministic bytes. It verifies
encoded/raw chunk hashes and sizes, an independently pinned case/artifact manifest,
chunk order, canonical padding and the restored aggregate. Storage admission counts
**encoded chunks plus manifest**. The 262,161 raw bytes occupy **350,353 stored
bytes**, so raw-only accounting would undercharge evidence. Exact roundtrip takes
0.004694 s at 26,812,416-byte peak RSS in the recorded fixture.

The [proposed envelope](results_radio_whole_cadence_remote_2026-09-28/ascii01/result.json)
is **not integrated into the remote store or scientific journal, and is not live
qualified**. The current Lease still charges raw artifact lengths; integrating
encoded storage requires explicit physical-byte accounting without borrowing
phase overhead. Both failed live scopes remain closed. No third live exercise
was run or admitted by the amendment.

| New distinct test family | Passing tests |
| --- | ---: |
| Remote transport faults, exact phase quotas and runtime files | 40 |
| Actual retained corrupt response | 2 |
| Canonical ASCII envelope and physical storage cap | 12 |
| Missing tracked code in a sparse checkout | 1 |
| **Total new** | **55** |

The original 32 journal tests and eight repeated runtime tests are regressions,
not additional new tests. No old native/mock/acquisition fixture was rerun.
The phase validator now rejects case-specific quota changes and protects the
200-second/76-MiB overhead reserve; its overhead ledger remains a metadata helper,
not a durable scientific allocation service.

## Runtime and resource limits

The two engineering freezes pinned 360 **materialized** repository Python files
and 1,132 measured runtime files; the corrected freeze additionally pins six inputs.
A later Git inventory audit found 821 tracked source/script Python files before
the two new ASCII files. The old snapshots are therefore **not complete Git
inventories or scientific execution freezes**. The code now rejects capture when
tracked Python files are missing from the checkout. Additional code was restored,
not executed; LS and CHEOPS remain paused/unsent. Current code needs a new freeze.

The initial runtime capture also exposed missing Tcl/Tk libraries for an unused
optional extension. That failure is preserved. Its file is hash-pinned as
unavailable and rejected if loaded; it is not silently described as executable.
These snapshots provide file identity evidence, not OS isolation or arbitrary
import interception. Codec/Gaussian/full-physical-chain qualification is still absent.

Live02 stopped after **707.719 s**, using 94 new connector calls and 67,342,336-byte
peak RSS. Conservative carryover charges make the live total **102 calls,
2,793,476 returned JSON bytes and 767.719 s**. One post-stop branch inspection is
separately counted: **103 calls total**, with a conservative extra 16,384-byte charge.
The observed post-stop verification interval is charged as 137 s, and offline
preparation as 60 s: **964.719 s charged**, within the original 1,800 s ceiling.
The evidence directory occupied 1,374,455 bytes before postflight. There are six
science branch advances before this report; report plus main README make eight
advances in total, below the original twelve-advance bound. Normal freeze/report
publication calls are outside the live-transport call benchmark.

[Handoff timing](results_radio_whole_cadence_remote_2026-09-28/run02/handoff_timing.json)
records filesystem request/response intervals, approximately seven seconds per
call; these include broker/orchestration latency and are **not GitHub server-only
measurements**. The supervisor performs an empty `write_stdin` poll after each
response, a concrete latency suspect to remove and measure prospectively.
This small, incomplete publication took far longer than a proposed 40/80-second
scientific case. It supplies no evidence those quotas can be met. The completion
record also cannot attest its own future commit/readback time; integrated
finalization and bounded failure publication remain required.

## Exact continuation

1. Keep live01 and live02 closed. Do not resume their worker or regenerate their
   case, replay old fixtures, or substitute intact Git bytes to relabel a pass.
2. Integrate a lossless artifact representation (the proposed ASCII envelope is
   available) into a **new** prospective engineering namespace. Charge actual
   stored bytes in the journal/phase budget, including manifests and failure
   evidence. Preserve all old raw evidence. Do not reset or enlarge any ledger.
3. Remove and measure the broker's avoidable per-call wait; specify bounded
   completion/failure publication and finalization accounting. A different
   readback architecture may be assessed prospectively, with exact Git identities.
4. Publish/read back a fresh executable freeze using the corrected Git inventory
   guard and actual transitive code/runtime/codec files. Only a newly bounded
   engineering scope may qualify the revised live path; the current amendment
   grants no remaining live retry.
5. Then qualify actual Gaussian success and the full native physical/gate chain
   on fresh engineering identities. Only after the complete integrated scientific
   protocol and a fresh separately authorized allocation may 127/24 be activated.
   New telescope values still require separate source/acquisition/trial admission.

All 17 historical invariant pins pass [postflight](results_radio_whole_cadence_remote_2026-09-28/postflight.json).
The 127/24 proposal remains PROPOSED_NOT_ACTIVATED. Development 6, failed calibration
3, the old evaluation allocation and diagnosis stay spent/closed; old evaluation
values stay unopened. HD189733/85030 remains active; HD1461/71139 remains on its
pointing hold, GJ724/73005 untouched, neighbor9 unchanged. M43AI stays failed/closed;
112+128 M43AF holdouts remain untouched; M15 GJ581/M33 HD3651 unresolved; LS8BD–LS8BE paused,
LS8BF untouched; CHEOPS unsent. No external messages or plan extension.
Consolidation remains **9 October**.

API semantics consulted: [Git references](https://docs.github.com/en/rest/git/refs)
and [Git blobs](https://docs.github.com/en/rest/git/blobs). `force=false` protects
fast-forward ancestry; it is not a server-side expected-head CAS argument. The
actual connector output, rather than an assumed REST response shape, is decisive.
