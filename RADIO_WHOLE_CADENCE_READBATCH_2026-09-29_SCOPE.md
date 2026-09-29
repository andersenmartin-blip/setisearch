# Prospective immutable-readback batching — engineering scope

29 September 2026. This is a **new, bounded, engineering-only** transport
scope. It does not reopen `batch-live01`, consume a scientific identity, render
Gaussian values, mutate an old ledger, or authorize telescope spectra. The
closed archive at immutable commit `c054671fdb17555165b1b4b67ad2d13f38338182`
is merely a fixed seven-file read witness.

## Frozen live action

`readbatch-live01` may execute exactly once, only after this scope and its
runtime/recipe files are public and read back. It groups seven independent
immutable `fetch_file` operations in one broker dispatch. Every underlying
request is charged before dispatch; 943,240 response bytes are reserved before
dispatch; and all seven file identities, encoded bounds, Git blob hashes and raw
bytes must verify. The exact paths, commit, blob identities and caps are in
`config/radio_whole_cadence_readbatch_recipe_20260929.json`.

Mutations are prohibited in this scope. Reply order is not trusted: ordinals
bind results. Missing, unexpected or duplicate replies; any partial failure;
retry authorization; wrong encoding/identity; corrupt content; cap overflow; or
an ambiguous broker outcome closes the scope without retry. All individual
errors and charges must be retained. The old archive and old journal remain
unchanged.

The live aggregate has an 80-second engineering elapsed cap, eight-call ceiling
(seven planned plus one unavailable contingency that cannot be used to retry),
8-MiB response ceiling, and 1-MiB result-evidence ceiling. Preparation, freeze,
postflight and publication have a separate conservative 300-second / 24-call /
2-MiB closure allowance. None of these limits belongs to the 40/80-second
scientific phase budget, and no unused amount is transferable.

## Qualification before live work

Eighteen new checks pass: fourteen client checks and four broker checks. They
cover complete charging before one aggregate dispatch, order-independent
identity binding, missing/duplicate replies, retained partial failure, refusal
of retry flags, wrong SHA/encoding, corrupt data, decoded/aggregate/call caps,
duplicate paths, incomplete ordinals, mutable refs and namespace escape. The
combined regression run adds 22 already-existing batch/handoff tests; those are
not counted as new progress. Python compilation, Node syntax and the Node broker
harness pass. The initial helper-import mistake and clean corrected run are both
retained.

## Claim boundary and continuation

This freeze qualifies only the prospective adapter and exact fixed read action.
It makes no timing or scientific claim. After public readback, execute
`readbatch-live01` once and publish the actual timings, all seven receipts and
byte checks. Whether pass or fail, close it permanently. Only afterward create a
separate prospective engineering freeze for actual Gaussian generation, compact
complete-score evidence and the full native physical/recovery/RFI/null chain.

The 127/24 proposal remains **NOT ACTIVATED**. Neighbor9, HD189733 cadence 85030,
HD1461's pointing hold, untouched GJ724, original preparation contracts,
scientific counters, closed ledgers, M43AI, M43AF holdouts, M15/M33, LS pause and
CHEOPS UNSENT remain unchanged. No source/telescope data, messages, paid service,
booking, automation, subagent or plan extension is admitted. Consolidation
remains 9 October.
