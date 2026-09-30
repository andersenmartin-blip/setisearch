# Fresh native v2 parent capacity passes; execution remains blocked

30 September 2026. **PASS for the prospective multi-case parent and exact
journal-capacity gate. PREPARED, NOT EXECUTED.** No case was reserved, no RNG was
opened, and no native score, receiver measurement or telescope value was read.

The previously qualified v2 policy carried one scalar configuration pin. That
cannot safely represent eight distinct fresh case/plan configurations in one
cumulative parent. The manifest now accepts a backward-compatible exact
case-identity-to-v2-configuration map. Its keys must equal the complete ordered
manifest inventory; missing, extra, malformed and cross-case pins are rejected
before physical reservation bytes are written. Old scalar manifests and their
readers remain valid.

The fresh parent is frozen as `radio-native-v2-engineering-20260930a` with:

| Bound | Frozen value |
|---|---:|
| Cases | 8 |
| Active time per case | 600,000 ms |
| Stored allocation per case | 18,874,368 bytes (18 MiB) |
| Cumulative case allocation | 150,994,944 bytes |
| Cumulative journal allocation | 8,388,608 bytes |
| Total evidence reservation | 159,383,552 bytes |
| Durable physical checkpoints per case | 8 |
| Physical files per case | 48 |
| Artifact-batch events per case | 8 |
| Maximum journal events | 168 / 1,536 |
| Maximum journal files | 340 / 4,096 |

The eight physical checkpoints are the seven meaningful algorithm boundaries
(admission; matched-OFF complete; adjacent-OFF complete; receiver returned;
receiver verified; identity partition complete; receiver-alias/decisions
complete) plus the terminal or failure snapshot. The old every-1,024-row
duplicates were forensic copies, not resumable state. Removing them changes no
numeric or veto result and preserves the final partial failure snapshot, while
preventing metadata-only exhaustion of the unchanged 128-KiB live revision cap.

An exact canonical worst-count model uses all 168 events, all 340 event/pointer
files, all 48 physical file receipts per case and six-digit legal artifact
sizes. Its peak reconstructed revision is **125,548 / 131,072 bytes**. Its peak
durable event store including transient HEAD and the 512-KiB closure reserve is
**789,981 / 8,388,608 bytes**; terminal stored metadata is 269,223 bytes. The
model creates no payload or random values.

Physical configurations are prospectively frozen with an empty prior-artifact
inventory. The v2 reservation is therefore created immediately after parent
consumption and before RNG. Later Gaussian base artifacts remain mandatory and
are charged by the outer 18-MiB parent; they cannot consume the two outer closure
reserves. A new integration test proves this ordering through terminal readback.

**252 tests pass** across the new capacity suite, v2 parent/evidence, event
store, terminal archive, journal, physical arithmetic, old native engineering,
receiver batching/bank/adapter/panel and their failure paths. Existing tracked
HD189733 receiver/score-map inputs were restored verbatim from the checked commit
for the clean sparse checkout; no evidence was regenerated.

This does **not** complete the fresh runner or the publication-during-execution
broker. In particular, the earlier terminal publisher's 256-file scope is not a
prospective proof for the 340-file cumulative journal plus case artifacts. The
next step is to implement the fresh plan/runner identities and a bounded broker
that publishes each terminal case and cumulative journal in immutable batches,
including crash, conflict, lost-response, request/response, time and grouped
readback evidence. Then publish and independently read back the complete
executable/runtime freeze. Only after that may a separate immutable reservation
be considered; this result itself grants none.

127/24 remains **NOT ACTIVATED**. HD189733/85030 remains selected; HD1461/71139
remains on pointing-provenance HOLD and GJ724/73005 remains reserve. Spectra and
old holdouts remain unopened, all prior failures and spent identities persist,
LS remains paused and CHEOPS UNSENT. No external message or plan extension.

