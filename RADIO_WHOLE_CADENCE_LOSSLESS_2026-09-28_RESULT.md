# Lossless atomic archive — engineering pass, scientific timing not qualified

28 September 2026. This closes the [prospective scope](RADIO_WHOLE_CADENCE_LOSSLESS_2026-09-28_SCOPE.md).
**29 distinct new risk tests pass. The one live scope is CLOSED:** one fixed
archive succeeded and one deliberately over-capacity case was refused and its
failure evidence archived. Neither is a scientific detection, calibration draw
or statistical EMPTY. No telescope values, proposed PRNG or new scientific
allocation were consumed. No external messages were sent.

## Published sequence and independent evidence

The freeze is [`f2af6dec`](https://github.com/andersenmartin-blip/setisearch/commit/f2af6decef6516a1329d5f841020297054b7dec5).
Its recipe, genesis and executable inputs were published and byte-verified before
work: **827 repository Python files, eight other inputs and 1,132 runtime files**.
The unchanged optional unavailable Tk extension is hash-pinned and prohibited
from entering the runtime. This is an engineering freeze, not scientific admission.

| Operation | Immutable commit |
|---|---|
| Consume fixed archive case | `c1f56949ff63f328706ad38a40fc65aeed3a9424` |
| Publish both complete artifacts and archive seal atomically | `6795b7ad73ace872ab33fe5f61b9b1b70191138f` |
| Consume fixed capacity-refusal case | `5f53e89e77b26d33e354052653f2504f9c68dd10` |
| Publish failure envelope and failure seal atomically | `4e9ba1c0ce86dc2e4c88afc61c03a09930b72ba8` |

All four use one exact current parent and `force=false`. Every tree delta was
checked, including preservation of unrelated files. A fresh store read all
envelopes from immutable Git identities and reconstructed every byte. A separate
Git-object verification reproduced the full result and fast-forwarded the local
checkout through only these own commits. See [worker result](results_radio_whole_cadence_lossless_2026-09-28/run01/result.json)
and [independent Git verification](results_radio_whole_cadence_lossless_2026-09-28/independent_git_readback.json).

| Artifact | Raw bytes | Physical ASCII envelope bytes |
|---|---:|---:|
| Fixed binary witness, two full chunks plus 17-byte tail | 524,305 | 700,112 |
| JSON witness | 223 | 870 |
| Bounded capacity-failure receipt | 365 | 1,058 |
| All five ledger versions retained in Git | — | 11,297 |
| **Artifacts plus ledger history** | **524,893** | **713,337** |

Binary SHA-256: `675614b1bccfbe549a913502c96fa5749f49b545ea5228a9da4da09980070f54`.
The second case attempted 1,024 raw bytes against a **256-byte physical normal
quota**. It was refused before normal artifact publication. Its separately
reserved 8-KiB failure allowance retained the complete 365-byte explanation.
It remains a failed case with its reservation charged; the engineering harness
passed because this precise refusal and bounded closure were prescribed.

## What changed and what was tested

The new adapter wraps binary artifacts in canonical base64 ASCII and checks the
actual encoded bytes, per-part hashes, envelope manifest and decoded aggregate.
It publishes all envelope parts and the corresponding journal seal in one
commit. Existing files, links and executable leaves cannot be overwritten.
Every ledger version is charged; normal and failure quotas cannot borrow from
one another. A process-local capability cannot be reconstructed after a crash.
Fresh processes cannot continue to the next case using an archival seal that
lacks the originating process's completed latency check.

The [29 new tests](results_radio_whole_cadence_lossless_2026-09-28/new_tests.txt)
cover atomicity, ambiguous landed writes, concurrent branch changes, changed or
missing remote ASCII bytes, immutable-path protection, physical/history limits,
separate failure reserves, stale capabilities, late consumption/seal readback,
request framing, partial files and response errors. Old closed native,
acquisition, codec and remote fixtures were not replayed as progress.

## Measured timing and unchanged scientific budget

The request/done-file broker made **111 new GitHub calls**: 55 Git metadata reads,
32 immutable file reads, 12 blob uploads and four each of tree/commit/ref writes.
The complete worker took **258.140481 s**, including preflight, transport and
independent fresh-store readback, with **71,290,880 bytes peak RSS**.
Calls plus the conservative preflight charge are **133 calls / 5,205,121 returned
JSON bytes / 318.140481 s**. Separate independent Git verification took 83.134016 s.

Measured case times including consumption, seal publication and readback were
**103.808198 s** and **88.081456 s**, within their fixed 300/120-s engineering
reservations. They do **not** qualify the inactive scientific **40/80-s** case
budgets. Actual tool service time was 63.554 s; the rest also includes file
handoff, local checks, scheduling and supervision. Different artifact/workflow
mixes prevent a controlled speedup claim against the prior failed run.

The [timing admission assessment](results_radio_whole_cadence_lossless_2026-09-28/timing_admission.json)
also records that 18 MiB raw data require **24 MiB of base64 before any manifest**.
The old logical cap cannot be used as an ASCII physical cap. The compressibility
and runtime of actual Gaussian complete-score archives remain unmeasured;
deterministic mock compression is not evidence for them. The scientific ceilings
stay **7,200 s / 1 GiB**, including the protected overhead. No borrowing, cap
increase or fresh scientific allocation is supplied by this result.

## Cumulative accounting and closure

The [postflight](results_radio_whole_cadence_lossless_2026-09-28/postflight.json)
verifies all **17 historical pins**. It preserves the prior remote scopes' 103
charged calls, 964.719075146 s, and spent 1,500-s/1-MiB incomplete case. The new
scope reserves another 420 s of case time and 1,065,216 physical bytes across
normal/failure allowances, plus 65,536 journal bytes; reservations do not refund.
Across these remote scopes: three engineering cases consumed, one archived,
one expected failure closed, one old incomplete failure preserved. Live01 of
the earlier package remains failed before consumption. None may restart.

For this scope the closure accounting charges **671.327405 s / 213 calls**,
including conservative separate reserves of 240 s / 80 calls for the final
report and main README publication. The charged returned-byte total includes a
2-MiB closure reserve and remains below 16 MiB. Archive/ledger plus locally saved
support evidence before the postflight total 1,506,463 bytes, with an additional
64-KiB postflight allowance under the 2-MiB evidence ceiling. Seven branch advances
are planned in total, under eight. These closure reserves are explicit upper
charges, not measurements of publication that had not happened when written.

Full [broker transcript](results_radio_whole_cadence_lossless_2026-09-28/run01/broker_transcript.json.gz),
[transport receipts](results_radio_whole_cadence_lossless_2026-09-28/run01/transport_receipts.json)
and [scope disposition](results_radio_whole_cadence_lossless_2026-09-28/disposition.json)
are retained. The codec's generic `ENGINEERING_PROPOSAL_ONLY` envelope label is
unchanged; this report qualifies precisely this adapter and fixed live scope.

## Exact continuation — supersedes the pending lossless integration step

1. Do not rerun this closed scope or either old failed remote scope. Lossless
   transport, atomic archive/seal publication and bounded expected-failure
   closure now have actual external evidence for these two fixed cases.
2. Resolve the **measured end-to-end budget mismatch** before scientific
   activation: reduce request/handoff/readback overhead under a separately
   bounded engineering scope. Preserve immutable byte verification, fresh
   fast-forward checks, durable consumption and no-resume semantics. Bind
   physical ASCII bytes rather than logical binary sizes. Do not simply raise
   40/80-s quotas or spend the protected scientific overhead.
3. Qualify actual Gaussian rendering, complete compact-score evidence and the
   full native physical/recovery/RFI/null chain using **new explicitly separated
   engineering identities**, with a fresh prospective recipe and executable
   freeze. Do not construct the reserved 127/24 proposal's RNGs for a benchmark,
   spoof a scientific lease, or let engineering results set detection gates.
4. Only after integrated resource/protocol qualification may a separately
   published fresh scientific allocation activate 127/24. No telescope spectra
   follow without their own full prospective source/acquisition protocol.

HD189733/85030 and neighbor9 stay selected. Development 6, failed calibration 3,
the old closed evaluation allocation (24 values unopened/unusable), one closed
diagnosis, remedy/pilot zero are unchanged. Original preparation contracts are
not ready. HD1461's pointing hold, untouched GJ724, failed M43AI, original 112+128
M43AF holdouts, unresolved M15 GJ581/M33 HD3651, LS8BD–BE pause with LS8BF untouched,
and CHEOPS UNSENT all persist. No messages, paid services, booking, subagents,
automation or plan extension. Consolidate the period on **9 October**.
