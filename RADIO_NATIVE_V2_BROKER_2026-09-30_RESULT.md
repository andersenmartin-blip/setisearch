# Batched publication-during-execution broker passes deterministic qualification

30 September 2026. **PASS for the deterministic broker component; live connector
semantics and runner integration remain unqualified.** No case was reserved, no
lease or RNG was entered, and no native score, receiver measurement or telescope
value was opened.

The broker accepts one already-terminal v2 case plus the cumulative event
journal. It first validates the physical configuration/checkpoint pins, terminal
parent state and exact base/physical/journal bytes. It then frames every source
file contiguously, splits the payload into 1-MiB pieces, stores each piece as
strict base64 text, and adds a canonical manifest and HEAD. A single Git
`create_tree` request supplies inline contents for all files, replacing the
hundreds of individual `create_blob` calls that caused the earlier serial
transport failure.

The immutable protocol verifies the fresh namespace, parent commit/tree, exact
candidate tree delta, candidate parent/tree, unchanged head immediately before a
non-forced ref update, and unchanged head after one grouped exact-byte readback.
Readback reconstructs every original file and verifies its length and SHA256.
Any conflict, lost update response or bad readback stops the case and the
cumulative broker without retry; a possibly landed update is never repeated.

### Frozen capacity envelope

| Bound | Per terminal case | Eight-case cumulative |
|---|---:|---:|
| Source bytes | 27,262,976 (26 MiB) | — |
| Inline chunks / remote files | 26 / 28 | — |
| Encoded chunk bytes | 36,350,704 | — |
| Stored incl. manifest+HEAD reserve | 36,875,057 / 37,748,736 | 301,989,888 |
| Inline-tree request incl. framing reserve | 37,923,633 / 50,331,648 | 402,653,184 |
| Grouped response incl. framing reserve | 50,215,320 / 67,108,864 | 536,870,912 |
| Calls | 64 | 512 |
| Elapsed seconds | 600 | 4,800 |
| Peak RSS | 512 MiB | 512 MiB |

The cumulative broker prospectively reserves the next case's entire per-case
envelope before any transport call, enforces ordinals 0–7, and checks actual
call/request/response/stored/time/RSS totals after each publication. One case
must finish and publish before the next can enter.

**262 tests pass** across seven new broker tests and all adjacent native-v2
parent, physical evidence, event-store, terminal archive, journal, physical
arithmetic, old native engineering and receiver suites. New tests cover exact
packing/restoration; one inline-tree/commit/update and one grouped readback;
conflict, lost update and corrupt readback; immutable pins/chunks; ordered
cumulative stop; worst-case byte formulas; and RSS refusal before the first
transport call.

This is not yet a live GitHub result. The connected Git transport's support for
inline `create_tree` content and the grouped readback adapter require one fresh,
small, publicly frozen engineering probe. The fresh plan module also does not yet
contain the complete render/threshold/physical/evaluate runner. The published
prepare-only runtime freeze predates this broker code and is therefore historical
preparation evidence only; it cannot be promoted to execution authority.

**Exact continuation:** publish/read back this component, freeze and execute one
small no-RNG live inline-tree/grouped-readback probe, then integrate its qualified
adapter with the complete fresh native runner. Generate and independently read
back a new complete runner+broker executable/runtime freeze before any case
reservation or RNG. Only after that may a separate immutable eight-case
reservation be considered.

127/24 remains **NOT ACTIVATED**. HD189733/85030 remains selected; HD1461/71139
remains on pointing-provenance HOLD and GJ724/73005 remains reserve. Spectra and
old holdouts remain unopened; all failures and spent identities persist, LS is
paused and CHEOPS UNSENT. No external message or plan extension.

