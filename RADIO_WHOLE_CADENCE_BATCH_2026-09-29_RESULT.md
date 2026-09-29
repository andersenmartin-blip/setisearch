# Batched publication qualified — 48.619-second archive, calibration timing hold

29 September 2026. The [prospective scope](RADIO_WHOLE_CADENCE_BATCH_2026-09-29_SCOPE.md)
is **CLOSED ENGINEERING PASS**. **22 distinct new risk tests pass**. One fresh
fixed binary archive was consumed, published and independently reconstructed.
The measured case took **48.618922 s**, within its fixed 80-s engineering quota.
The earlier same-size archive measurement was 103.808198 s. This is a descriptive
comparison of two fixed engineering cases, not a controlled performance benchmark.
**Scientific calibration's 40-s budget remains unqualified.**

No telescope data, reserved proposal RNGs, scientific allocation or external
messages were used. Neighbor9, HD189733/85030, all original preparations and the
127/24 proposal's NOT ACTIVATED status are unchanged.

## Implementation and new risks tested

The new adapter submits all ASCII envelope files and the ledger in a single
Create Tree request using `content` entries. It computes the exact expected Git
root locally from verified immutable parent trees, preserving every unrelated
entry. The server must return that root hash before a commit is created. Both
fresh parent/ref checks, `force=false`, durable prior consumption and atomic
artifact/ledger publication remain mandatory. Existing artifact paths, changed
modes, conflicting file/directory paths, deletions, mixed SHA/content entries and
non-ASCII contents are refused.

Locally predicted trees enter the immutable cache only after the server's exact
root matches. This saves repeated tree retrieval; it does **not** populate blob
caches from upload values. Every stored artifact part still receives fresh
immutable-path external byte/hash verification. A new store then discards caches
and independently decodes all raw bytes. The process-local capability and
post-publication time checks prevent crash resume and late authorization.

The broker combines response delivery and next-request framing in one operation,
reads large immutable request chunks concurrently, and no longer pauses for
periodic model yields. Mutations remain sequential. The
[22 tests](results_radio_whole_cadence_batch_2026-09-29/new_tests_initial.txt)
cover the new batching/handoff risks, including an independent **Git `mktree`**
oracle, server root mismatch, overwrite/mode/path collisions, fresh readback
corruption, branch races, ambiguous landed writes, deadline/call/response caps,
duplicate delivery, malformed response frames and actual waiting-worker failure.
The closed predecessor code and its tests were not rerun as new progress.

The API ability was checked against
[GitHub's Create Tree documentation](https://docs.github.com/en/rest/git/trees#create-a-tree)
on 29 September: `content` creates a blob and must not be combined with `sha`.
The following actual live evidence, rather than documentation alone, qualifies
this connector path for the fixed engineering case.

## Frozen and published sequence

The [freeze commit](https://github.com/andersenmartin-blip/setisearch/commit/2dd19d346157d77813c554bf20fb519d3c226e73)
precedes consumption and binds **831 repository Python files, eight other inputs
and 1,132 runtime files**. Sixteen changed files were read back and verified.
The unchanged unavailable optional Tk extension remains prohibited from runtime
use. This is an engineering-only freeze.

| Transition | Immutable commit |
|---|---|
| Consume the single fresh case | `5dbdb5decdf6f83b5e5945ba81fc2d37c5651cd9` |
| Publish both envelopes and the archive seal atomically | `c054671fdb17555165b1b4b67ad2d13f38338182` |

Case identity: `c202db6296e6de3ae20295e23fca4db75ef16d63694bf6e517b4d89374a863bf`.
All exact parent/tree/path deltas were checked independently through Git. The
seven distinct immutable blobs were fetched together for independent verification;
that postflight took **9.580206 s**. Only these two own commits were integrated
with fast-forward. See [independent readback](results_radio_whole_cadence_batch_2026-09-29/independent_git_readback.json).

| Evidence | Raw bytes | Physical encoded bytes |
|---|---:|---:|
| Fixed binary witness | 524,305 | 700,112 |
| JSON witness | 217 | 862 |
| All three ledger versions | — | 3,878 |
| **Total archive and ledger history** | **524,522** | **704,852** |

The binary SHA-256 is
`7a79dc44d02c4b2e984327a565d581d07d46c6ab4f68b41af489aaad01257c6f`.
Its recipe is `bytes((i*31+19)%256 for i in range(524305))`; the 17-byte tail and
two full chunks are all preserved. Actual encoded sizes remain charged even
where Git deduplicates identical blobs. No logical-size substitution is allowed.

## Timing evidence and remaining risk

[The worker](results_radio_whole_cadence_batch_2026-09-29/run01/result.json)
used **48 new GitHub calls**, with no standalone blob upload: 24 metadata reads,
18 immutable file reads, and two each of tree/commit/ref operations. Its full
elapsed time was **114.526863 s**, including preflight, the initial supervisor
handoff, the case, fresh-reader archive verification and final runtime checks.
The broker itself ran for 88.926 s. Peak RSS was **69,865,472 bytes**.
The initial read included a 27.207930-s supervisor-start round trip; it remains
charged, not subtracted to create a faster end-to-end result.

| Operation | Calls | Tool service time | Complete client round trips |
|---|---:|---:|---:|
| Git metadata reads | 24 | 10.816 s | 66.706201 s |
| Immutable file reads | 18 | 8.084 s | 32.443817 s |
| Create tree | 2 | 2.349 s | 5.916079 s |
| Create commit | 2 | 1.312 s | 4.000156 s |
| Update ref | 2 | 1.558 s | 3.888355 s |

Round trips include file handoff, scheduling and supervision, not just network
service. The [receipt-derived assessment](results_radio_whole_cadence_batch_2026-09-29/timing_assessment.json)
retains these components without a Gaussian/detector run. The observed case is
still **8.618922 s above calibration's 40-s quota**, before any actual Gaussian
native/physical computation has been qualified. Being below 80 s for this binary
archive does not qualify scientific evaluation or the 151-case phase overhead.
The scientific ceilings remain 7,200 s and 1 GiB with protected overhead.

## Budget and preserved failures

The scope's actual live calls plus conservative preflight are **70 calls /
2,719,121 returned JSON bytes**. The original worker input charged 60 preflight
seconds. The [separate adjustment](results_radio_whole_cadence_batch_2026-09-29/preflight_charge_adjustment.json)
preserves that input and adds 40 seconds, charging **100 s** for the observed
84.209-s freeze/publication interval plus preparation/tests. No quota was raised.

The [postflight](results_radio_whole_cadence_batch_2026-09-29/postflight.json)
charges **494.292233 s / 130 calls** including separate 240-s / 60-call final
report-and-README reserves, independent Git verification and a conservative
30-s post-live fetch/metadata charge. Returned bytes include a further 2-MiB
closure reserve. The physical evidence bound includes the complete runtime
freeze, support evidence, all archive/ledger bytes and a 64-KiB postflight/report
allowance: **1,603,887 bytes**, below 2 MiB. These publication reserves are explicit
upper charges for work not yet completed when this report was written.
Five branch advances including freeze/report/main are planned, below six.

All 17 historical invariants and five additional closed-code/journal pins remain
unchanged. Initial read-only postflight hit a sparse-checkout missing file;
[the error](results_radio_whole_cadence_batch_2026-09-29/postflight_initial_error.json)
is retained. The audit recovered that metadata from immutable Git objects and
completed; no live case was resumed or repeated.

The new 80-s / 1-MiB case, separate 8-KiB failure allowance and 64-KiB ledger
reservation remain nonrefundable. Prior scopes retain their conservative
**316 calls / 1,636.04648012 s** and 1,920 s of case reservations. Across the four
remote scopes: four cases consumed, two archives completed, one expected failure
closed, one old consumed-incomplete failure retained; the earliest failure still
occurred before consumption. Cumulative case reservations are 2,000 s and
3,170,560 normal/failure bytes, excluding separately reserved ledgers. No closed
scope may restart. Full [transcript](results_radio_whole_cadence_batch_2026-09-29/run01/broker_transcript.json.gz),
[transport receipts](results_radio_whole_cadence_batch_2026-09-29/run01/transport_receipts.json)
and [disposition](results_radio_whole_cadence_batch_2026-09-29/disposition.json) are public.

## Exact continuation

1. Close batch-live01 permanently. Content batching, exact locally predicted
   trees and combined handoff now have actual external evidence. Do not repeat
   this fixed test or reset any predecessor ledger.
2. Under a **new bounded prospective engineering scope**, group independent
   immutable file readbacks. Charge **every underlying request**, reserve the
   aggregate response bytes before dispatch, preserve each error, and check every
   file's Git identity, envelope and raw bytes. Keep mutations sequential and
   all exact-parent/consumption/no-resume guarantees. Test partial batch failure,
   missing/reordered/duplicate replies, response caps and corrupted parts before
   live execution. The current 32.443817-s read total motivates this change; it
   does not establish the future runtime or justify dropping checks.
3. Then qualify fresh explicitly engineering-only Gaussian generation, compact
   complete-score evidence and full native physical/recovery/RFI/null execution
   with new identities and its own prospective executable freeze. Never use the
   reserved 127/24 RNGs for a benchmark or impersonate a scientific lease.
4. Activate a fresh scientific allocation only after integrated protocol,
   runtime, physical-byte and cumulative phase-budget qualification. Telescope
   spectra still need the complete source/acquisition protocol. Do not raise
   40/80-s quotas or borrow protected overhead to force admission.

Scientific counters stay development 6 closed, calibration 3 failed/closed, one
old closed evaluation allocation with 24 values unopened/unusable, one closed
diagnosis, remedy/pilot zero. Original preparations are not ready. HD1461's
pointing hold, untouched GJ724, failed M43AI, original 112+128 M43AF holdouts,
unresolved M15 GJ581/M33 HD3651, LS8BD–BE pause with LS8BF untouched and CHEOPS
UNSENT remain unchanged. No messages, paid services, booking, subagents,
automations or extension. Consolidate on **9 October**.
