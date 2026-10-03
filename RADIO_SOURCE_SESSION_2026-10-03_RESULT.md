# Durable source sessions joined to receiver handoff — 3 October 2026

The original acquisition session implementation now completes a fresh **synthetic engineering** route through 18 source imports and three receiver contexts. All 288 normalized receiver rows reproduce the independently pinned prior fixture rows. Each import uses a newly charged, non-resumable session; its exact journal, reservation, ledger prefix and completed source receipt are verified before receiver arrays are constructed.

This checkpoint qualifies the declared local engineering checks. It grants no telescope access, source admission, statistical qualification, scientific score, sensitivity result or non-detection.

| Component | Observed result |
|---|---|
| Candidate reservation store and strict replay | 28 tests pass; earlier 23- and 26-test passing logs retained |
| Independent semantic replay review | 19 focused checks pass, including honestly recomputed invalid chains |
| Independent actual-attempt audit | All 1,044 generated files, all 19 ledger prefixes/journals, 576 NPY files and all three handoff links verify |
| Fresh original DurableBudget source imports | 18 completed sessions; 18 products and 288 rows |
| Source-to-receiver join | Three contexts; 96 normalized row comparisons each, 288 total |
| Negative source session | Wrong strong ETag refused at HEAD; one request, zero body bytes and no completed product |
| Permanent cumulative charge | 19 sessions: 608 request slots, 637,534,208 bytes and 190 seconds |
| Actual positive simulated transport | 114 requests; 168,255,053 reserved bytes and 168,254,957 accepted bytes |
| External observation | 8.951 seconds; sampled peak RSS 283,901,952 bytes; exit 0, no cap failure |
| Actual generated evidence | 323,600,474 logical bytes including the final index, below the fixed 384 MiB cap |

Every session prospectively reserves 32 requests, 32 MiB and 10 seconds. The original total cap remains 1,000 requests, 1 GiB and 600 seconds; unused reservation portions are never refunded. Remaining capacity is 392 request slots, 436,207,616 bytes and 410 seconds. The candidate's separate observed process caps are 60 seconds, 512 MiB RSS and 384 MiB generated logical file bytes. Local reservation accounting and generated file bytes are different quantities.

## Implementation and evidence boundary

The original project acquisition, transport, source decoding, receipt and receiver modules remain unchanged. The candidate adds a local engineering SQLite Store implementing the original `read()/publish()` protocol. Full-synchronization rollback transactions, exact compare-and-swap and bounded canonical histories preserve every committed reservation. A read-only reopening may inspect that history or support a newly charged reservation; it does not reconstruct an old process-local DurableBudget.

The strict journal reader joins a supplied Checkpoint, reservation, final head and ordered synthetic source scopes to bounded regular-file bytes. It rejects duplicate JSON fields, noncanonical lines/separators, Boolean/integer aliases, altered metadata, changed scopes, nonfinite or regressing recorded times, invalid accounting and torn or rolled-back histories. A completed session cannot hide an unaccepted GET behind a later request or scope. Error/interrupted evidence keeps failed request reservations charged. Tests include two competing processes, uncertain publication and fsync/short-write failure before dispatch.

The unchanged old reader accepted eight honestly recomputed examples, including a baseline and seven semantic exceptions. Those witnesses are preserved, not described as cryptographic hash bypasses. The new reader's independent review refuses the malformed cases under the declared checkpoint and scope.

Before each receiver handoff, the new join checks all six journals and completed source receipts. All prefixes must belong to the same final 19-session ledger and location, with unique session identities and increasing prefixes. It verifies source definition, descriptor, exact source receipt file bytes, simulated request accounting and complete GET acceptance before invoking the unchanged local-fixture receiver bridge. All three handoff receipts remain bound to the joined manifests and all 288 normalized row hashes.

## Input reuse, versions and limitations

The HDF5 fixture bytes and raw/normalized comparison hashes are reused from the previous independently pinned source checkpoint. URLs and strong ETags name fresh synthetic `.invalid` objects; labels, roles, headers, chunks, filter declarations and windows are preserved. This is a fresh extraction and session-accounting experiment over those retained bytes, not a new independent random draw or a new numerical oracle. The current local encoder is not claimed to identify the historical archive encoder.

All 165 frozen project files, 1,044 held runtime files and additionally observed loaded/mapped inputs retain their recorded payloads. The retained runtime file device/inode/time checks also pass. These snapshots and RSS sampling do not certify the complete process tree, imports before observation, intervals between samples, hostile concurrent filesystem mutation or an entire future runtime lifetime. The inherited source rehydrator still reopens paths.

A late edit to the driver initially produced a conservative NOT_SELECTED disposition. The original disposition is retained unchanged. The observer record was written after `child.wait()`; the edit timestamp is **8.731103304 seconds later**. The ordering uncertainty is resolved without rerunning or resetting the ledger. The executed original bytes, SHA256 `811de5828f3bc4f5af5e2bb1a2312fa262bd5aed58da3685e6fcd56ae917d78f`, are restored and separately retained. The failure-handler revision `3e921cc7…` is an unexecuted future candidate. The executed original's disclosed emergency failure tail was not used; general exhaustion behavior of that driver is not qualified by this passing run.

Local SQLite fsync/CAS and later public byte preservation are not an authenticated hosted reservation service or a live source transport certificate. No source-specific executable contract is created, and all eleven immutable scientific/source fields remain pending.

## Project state and continuation

The separate primary F invocation was permanently spent before dispatch at public commit `b24874373c8560bac30da5424d019ac7c7e38c71`; the observed primary branch tip was `111a34e666a64220db8d8237b3cac88645e4a8bd`. This source-session candidate neither resumes that invocation nor creates a second F/G control or changes the primary branch.

Preserve A/B/C/E permanent spend, D uncreated, HD189733 selected, HD1461 HOLD, GJ724 untouched reserve, unopened telescope spectra/holdouts, native8 unreserved, 127/24 NOT ACTIVATED, LS paused and CHEOPS UNSENT. Consolidation remains **9 October 2026**, without automatic extension, restart or target change. No person messages or schedule changes occurred.

Next is an authenticated hosted reservation/transport boundary with independently verifiable publication and code/input/runtime/resource evidence. Scientific qualification and live telescope processing remain separate unopened gates.

## Immutable records and restoration

Actual integration index SHA256: `5f62787cd2fd3205366ca8b3605297a7f47dae35d0be277f92f35214a7d35c91`.
Store/replay implementation SHA256: `ee48b3e3cb7647c31694d42ce2ff2b4b011b00d8189eed2f04f309225cc166f9`.

The branch descends from the prior source-handoff checkpoint `9ebbf017c2c69263ec7acf85bfecf59d57d1b50a`, which retains the complete fixture/source snapshot evidence used here. The new archive preserves every included new session file byte, including raw/normalized products, sparse mirrors, SQLite history, journals, manifests, audits, test logs, version dispositions and unexecuted driver revision. Deduplication preserves bytes and paths, not original inodes, sparse allocation or historical custody. Restoration verifies bytes without executing evidence. Restored absolute paths and candidate invocations require fresh reviewed pins; the archived commands are not restart authorization for closed sessions.

Verified archive publication supplement: **1102 files / 324,006,799 original file bytes** are captured in **7,267,497 compressed bytes**, split into 14 parts of at most 512 KiB. Streamed comparison, full safe restoration and a separate restored-copy hash process all pass. Archive SHA256: `69ae1154c31ff974748a11550c003026feebfb97dfb5cab1e53a4954d3d6fbc3`. The first 1,101-file archive captured the attempt before a 776-byte audit wording clarification was added; latest-inventory verification refused that earlier capture. Its original compressed stream and the failure log are retained separately, and the final 1,102-file archive includes the clarification. No experimental file or session was changed or rerun. The archived original report predates this publication supplement.
