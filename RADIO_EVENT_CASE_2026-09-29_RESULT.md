# Event journal and parent physical evidence — closed byte-integration PASS

The new local event journal completes the full fixed storage workload:
**22/22 physical snapshots and all 208 original journal revisions restore
exactly**, within the unchanged case and journal budgets. **127 tests pass.**
The previous full-snapshot integration remains CLOSED FAILED; this is a separately
scoped storage allocation with a fresh identity, not a restart of that case.

The source is still the historical failed native report. Both its saved physical
status and this storage case's parent disposition stay FAILED. The PASS refers
only to complete, bounded storage and restoration of that prescribed evidence.
No native physical computation is repeated or reclassified.

## Complete measured workload

The [scope](RADIO_EVENT_CASE_2026-09-29_SCOPE.md) fixes the same already-public
report, seven base artifacts and 22 independently pinned serialization views.
Source identity inside those bytes remains provenance. The new parent storage
identity is `726010a2bcc027ac662ddb5866520a9c5b925b3fd04390d095e30a658993724a`.
Manifest, allocation, scope/code/test hashes and input pins were saved before
journal creation and consumption. Intermediate views are constructed storage
fixtures, not historical physical time points.

| Measurement | Actual |
|---|---:|
| Exact physical snapshots | 22 / 22 |
| Registered case artifacts | 205 |
| Complete case artifact bytes | 17,425,035 |
| Journal versions / retained pointer versions | 208 / 208 |
| Physical journal bytes, including every event/pointer, HEAD and LOCK | 263,734 |
| Reconstructed original journal revision bytes | 9,214,754 |
| Complete case plus journal bytes | 17,688,769 |
| Dynamic inventory seal | 32,817 bytes |
| Physical / outer footer | 641 / 792 bytes |
| Parent case elapsed time | 50.120 s |
| Storage and parent closure phase | 50.187854 s |
| Readback and complete history audit phase | 5.138175 s |
| Whole fixture, including setup | 55.785488 s |
| Peak process RSS | 292,925,440 bytes |

The complete case fits its 24-MiB cap and the journal fits its separate 8-MiB
cap. Together they fit the unchanged 32-MiB allocation. All protected seal,
footer and journal-finalization reservations remain inside those original caps;
unused space is not refunded into a new trial. There are no physical or journal
orphan files in this new closed fixture. Source artifacts count exactly once.

The preceding [full-snapshot integration](RADIO_PHYSICAL_CASE_2026-09-29_RESULT.md)
stopped safely after 19 views. Its original 193 revisions, four uncommitted parts,
failure footer, charges and failed disposition remain public and unchanged.
The present journal stores different new revision identities belonging only to
the new storage case. This is not a controlled timing comparison between runs.

## Live journal representation and verification

`whole_cadence_event_store_radio.py` writes one immutable genesis, each event
once and **every** immutable pointer version. Events bind the exact before/after
original revision SHA256 and after length; pointer versions bind the prior pointer,
latest event, original revision and genesis. All original journal documents remain
reconstructible exactly, without writing duplicate complete snapshots.

Publication writes event, pointer version and a durable temporary HEAD before
atomic HEAD replacement and directory sync. Compare-and-swap prevents stale
publication. Any uncertain write stops the publisher. Existing directories cannot
reopen a publisher, and the independent history reader supplies no consume,
publish or lease API. Read-only crash inspection can expose a committed prefix
and explicitly charged orphan tails; it does not authorize continuation.

The case uses the previously added strict dynamic-artifact policy. Every physical
part/checkpoint/config/footer is registered as an ordinary immutable parent
artifact, and the final seal enumerates the exact full inventory. The scientific
and existing remote adapters cannot acquire this new local publisher. Old fixed
manifests keep their existing requirements.

The 127-test run combines **10 new event-store tests with the preceding 117
parent/journal/physical/receipt tests**. New checks cover original revision and
pointer preservation, complete physical integration, prohibited reopen/reconsume,
corrupt/missing/stale bytes, torn events and HEAD writes, lost acknowledgements,
unknown files/symlinks and protected cumulative capacity. The actual test log is
retained. No test or large storage fixture is substituted for scientific evidence.

After closure, a fresh history reconstruction independently checks all event and
pointer bytes, every original revision hash/length and the exact final journal
prefixes. The complete registered case archive passes, and all 22 decoded physical
reports match the prewritten independent source size/hash schedule.

The current immutable anchors are:

- Genesis: `8fbedfd552dea512a88797e44745f8c7b90518a6aa291e406e5bc60326d68461`
- Final pointer: `c5fba3eea777ea9fcda7ad3ea6ae20ff47290d435592f4bcb89913c1c8895dc8`
- Final original journal revision: `87c88f3844fd66dec7db193344a93f726470d2c25d89a6bc3477f4efb05101ca`
- Final physical checkpoint: `8bd550e298b9a79e91a426845872edd071f4a773907442e5e74d17d1caa5ab43`

## Public evidence and continuation

[`results_radio_event_case_2026-09-29/`](results_radio_event_case_2026-09-29/)
contains the fixed inputs, exact result and original revision inventory, test and
stdout logs, lossless archive and publication/readback receipts. The manifest
pins all original files and transport parts. Verify the archive without executing
the closed fixture:

```sh
python scripts/radio_physical_evidence_archive.py --archive results_radio_event_case_2026-09-29
```

The large fixture generates **zero new random values, native scores or physical
decisions**. It qualifies local dynamic-artifact/event-journal storage on the
preserved partial-report workload. It does not establish that complete native
receiver/alias evidence fits or that physical recovery/RFI/null gates pass.

**Next:** bind the measured complete event/pointer/physical inventory into bounded
batched remote publication with immutable readback, preserving atomic advancement,
lost-response stops and full cumulative transport charges. Administrative
publication of this package is measured separately and is not that scientific
adapter. Any later native physical run needs its own prospective executable freeze
and fresh identities. Scientific 40/80-second timing remains unqualified; local
storage alone took about 50 seconds, before native computation or remote transport.

**127/24 remains NOT ACTIVATED.** All older failures and spent identities remain;
telescope spectra and old holdouts stay unopened. Source selections, holds,
counters, LS pause and CHEOPS UNSENT are unchanged. No messages or delegation.
Consolidate 9 October without extending the plan.
