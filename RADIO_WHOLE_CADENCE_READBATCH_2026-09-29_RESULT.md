# Immutable readback live01 closed — byte-correct, response reservation failed

29 September 2026. `readbatch-live01` is **CLOSED ENGINEERING FAILED** and may
not be retried. Its public prospective freeze is commit
[`9086218`](https://github.com/andersenmartin-blip/setisearch/commit/90862188478f4532e55d02731dd67e38a4371d8c).
No branch mutation, scientific identity, Gaussian value or telescope/source
value was used.

All seven independent immutable reads returned successfully in one grouped
dispatch. Their Git blob identities and every one of **703,392 raw bytes** match
commit `c054671fdb17555165b1b4b67ad2d13f38338182`. Observed aggregate elapsed time
was **0.605 s**; individual calls were 0.353–0.605 s. This is a transport
observation, not a scientific calibration benchmark.

The scope nevertheless fails its pre-dispatch response reservation. The exact
broker frame occupied **971,981 bytes**, versus **943,240 reserved**: an overrun
of **28,741 bytes**. The raw normalized base64 contents total 937,864 bytes.
Connector line wrapping added 15,634 newline characters, which occupy 31,268
bytes when JSON-escaped; after stripping those line breaks the frame is 940,713
bytes. Connector display metadata accounts for the remaining avoidable overhead.

The live evidence is retained in
`results_radio_whole_cadence_readbatch_2026-09-29/live_result.json`. All seven
underlying requests remain charged. No automatic retry, cap increase or
retroactive pass is permitted.

## Prospective correction

The [separate amendment](RADIO_WHOLE_CADENCE_READBATCH_2026-09-29_AMENDMENT.md)
projects each successful connector reply to exactly `content`, `encoding` and
`sha`, removes CR/LF before durable handoff, and uses a different seven-file
witness at immutable commit `9086218`. This corrects a wire-format accounting
error; it does not tune a scientific evaluation or reopen live01. Its tests and
freeze must be published and independently read back before one live02 action.

The 127/24 proposal remains **NOT ACTIVATED**. The 40/80-second scientific
budgets, Gaussian/native physical chain and source-acquisition admission remain
unqualified. All prior holds, counters and dispositions are unchanged.
