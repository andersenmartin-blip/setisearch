# Content-addressed v2 archive batch passes

30 September 2026. **PASS for this terminal engineering archive transport.**
The earlier serial publisher remains CLOSED FAILED at its prospective
900-second limit. This new scope neither retries nor repairs it; it publishes
the same 130 immutable archive files under a fresh namespace using their
already public Git blob identities.

## Prospective publication

The [contract](RADIO_V2_BATCH_2026-09-30_CONTRACT.md), implementation and six
new risk tests were published at
`e0cd16eceb694f68a67e4f8eda1147b3890f1bb4`. Together with the two nearest
regression suites, **38/38 tests passed**. The exact
[remote freeze](results_radio_v2_batch_2026-09-30/remote_freeze.json) was then
published separately on `main` at
`64a753c1a0dcd8ef22a4b5887fb83da7ad344245` and independently read back with
blob identity `265ffb301d880641353e68b87244347b19b4b4fb` before the writer opened.

The freeze binds parent `e0cd16e…`, its tree, the complete source and target
inventory, all Git blob/SHA256/byte identities, five deterministic logical
batches, final tree `2ad0ce6…`, the fresh target namespace and unchanged
engineering-only disposition. It contains 130 files and 4,961,274 source bytes.

## Live result

Five bounded tree batches contained **32, 32, 32, 32 and 2** path/blob entries.
They reused every existing content-addressed blob; no source byte was
transcoded and no per-file blob upload occurred. The complete returned tree
matched the independently frozen tree. Exactly one commit and one non-forced
fast-forward ref update exposed the archive at
`70c3b23234c21a9c3ea36192b53ad8b9aad6eb1b`.

| Measurement | Observed / limit |
|---|---:|
| Exact stored files | 130 / 160 |
| Exact stored bytes | 4,961,274 / 6,291,456 |
| Logical tree batches | 5 |
| Tree-entry request JSON | 23,301 bytes |
| Mutation commits / ref updates | 1 / 1 |
| Force update | false |
| Publication wall time | 8.510 / 300 s |

The complete [publication receipt](results_radio_v2_batch_2026-09-30/publication.json)
retains every intermediate base/result tree, batch count/bytes, request size
and elapsed time. The acknowledged ref update was not retried.

## Independent immutable readback

After a fresh fetch, the
[read-only audit](results_radio_v2_batch_2026-09-30/readonly_audit.json) read all
130 candidate paths through **one `git cat-file --batch` operation**. It checked
the complete commit tree plus every file's exact Git blob, SHA256 and length:
all 4,961,274 bytes matched. Audit time was **0.049221 s** and peak process RSS
was **36,466,688 bytes**, below the frozen 120-second and 512-MiB limits.

## Meaning and exact continuation

This removes the measured serial MCP/RPC terminal-archive obstruction. It does
not qualify automatic publication during native execution, complete native
physical/resource feasibility, 127/24 or telescope acquisition. The source
parent/physical disposition remains FAILED/incomplete, and readback does not
reverse any old failure. No RNG value, receiver measurement, score or telescope
spectrum was created or opened.

**Next:** freeze one fresh complete native physical/resource qualification,
integrating receiver batching, full stage timings, complete receiver/alias/
cluster evidence, recovery/RFI/null gates, bounded interruption accounting and
explicit publication during execution. It needs fresh identities and a public
freeze; this terminal archive grants no execution or scientific admission.

127/24 remains NOT ACTIVATED. HD189733/85030 remains selected; HD1461/71139
remains on pointing-provenance HOLD and GJ724/73005 remains reserve. Spectra and
old holdouts stay unopened, LS paused, CHEOPS UNSENT. All historical failures,
spent identities, counters and budgets persist. No external messages or plan
extension; review around 2 October and consolidate 9 October.
