# HD189733 receiver score adapter: six development cases complete

The receiver drift bank is now connected to native normalization, filtering and
score gathering through a distinct receiver-specific contract and context.
**All six reserved development cases completed: 2,309,472 score cells agree
bit-for-bit with an independent native-window calculation.** A connected
metadata-only comparison also finds identical cross-window relative channel
maps in **1,539,648 comparisons**. Both tasks are complete; neither is a
scientific signal-recovery result or permission to open telescope spectra.

## Prospective execution and new checks

The [protocol](RADIO_HD189733_ADAPTER_2026-09-28_PROTOCOL.md), code, configuration
and durable reservation were published and read back in
[`4c391970e2cbbf374e78e56d6a785233e2126817`](https://github.com/andersenmartin-blip/setisearch/commit/4c391970e2cbbf374e78e56d6a785233e2126817)
before development values were generated. All six attempt slots were charged
prospectively, preventing an absent result or lost scratch from authorizing a
fresh replay. The [consumption ledger](results_radio_hd189733_adapter_2026-09-28/development_attempt01/consumption.json)
now records all six as spent and completed, with status
`CLOSED_SIX_DEVELOPMENT_IDENTITIES_SPENT`.

**21 distinct new tests pass.** The first test invocation encountered a missing
published geometry file in the sparse checkout: nine renderer checks completed,
but adapter setup failed. The exact file was restored from Git and its published
hash verified; this technical failure is retained. The next invocation passed
20 tests. A subsequent pre-exposure review identified a NumPy weak-scalar
promotion risk in the independent oracle: the divisor must use float64, as the
native filter does. That was corrected before the freeze and a separate regression
test passed. No scientific evaluation or development realization was exposed
during either correction. These are 21 distinct tests, not 30 from counting
repeated checks. No unchanged old test suite was rerun.

The new contract carries explicit rate labels and actual drift `q*r/C`; it
contains no invented orbital phase or projected scale. Source bytes, window,
grid, bank and scan inventory are pinned. Stale cache ancestry is rejected even
if individual score-vector hashes have been recomputed. A calibration from a
different context/window is rejected. The receiver adapter has no telescope
constructor. Legacy orbital providers and numerical mask/retention/OFF/alias/rank
kernels remain unchanged; the new decision adapter changes metadata and provider
identity. Its statistical decision stages have **not yet been exercised** here.

## Six finite-exposure development cases

The six identities reserved earlier were used on the validation geometry, with
rate labels **−3.95, −1.95, −0.05, +0.05, +1.95, +3.95 Hz/s**. Every case has
independent seeded noise, a one-channel rectangular intrinsic signal with 500
digital-power units per integration in all ON scans, and no injected OFF signal.
The case order, widths, amplitudes and rates were frozen before execution.

The renderer integrates uniform exposure analytically. A moving rectangular
spectrum produces the convolution of two uniform frequency intervals; native
pixel-bin integrals preserve its total digital power. This avoids a time-sampling
approximation. The largest observed mass error was 1.11e−16. The model does not
describe the real telescope channelizer or establish flux/EIRP sensitivity.

| Development rate label (Hz/s) | Native score cells compared | Bit mismatches |
| ---: | ---: | ---: |
| −3.95 | 384,912 | 0 |
| −1.95 | 384,912 | 0 |
| −0.05 | 384,912 | 0 |
| +0.05 | 384,912 | 0 |
| +1.95 | 384,912 | 0 |
| +3.95 | 384,912 | 0 |
| **Total** | **2,309,472** | **0** |

Each comparison covers all six scans, eight unchanged widths, 81 templates and
99 support carriers. The independent calculation selects native windows with an
explicit floor/fraction nearest-even rule, sums their samples, and accumulates
rows in the frozen order. It does not read the adapter's filtered cache.

The [retained case evidence](results_radio_hd189733_adapter_2026-09-28/development_attempt01)
contains 576 raw/background/normalized row receipts, 7,776 score-vector hashes,
288 complete comparison summaries and all source/cache identities. Full random
row and score arrays are not archived; exact generator/runtime/seed/code pins and
their hashes support reconstruction. These spent cases must not be replayed as
new work. There are no missing candidate decisions: no threshold, mask, retention,
clustering, OFF veto, receiver-alias or rank decision was run on the six cases.
In particular, **six numerical passes are not six recovered signals**.

Execution took **20.366 seconds**, with peak process RSS **84,254,720 bytes**
(80.35 MiB), below the 1800-second / 512-MiB limits. Modelled pipeline arrays
were 53,366,656 bytes per case. Retained evidence before the final summary was
2,489,765 bytes, below 16 MiB. Python 3.12.14, NumPy 2.3.5 and PCG64 are pinned.
No acquisition ledger, HTTP request, decoder or telescope data was used.

## Connected cross-window score-map result

After the development run, a separate [fixed scope](RADIO_HD189733_SCORE_MAP_2026-09-28_SCOPE.md)
compared the complete 81×96×99 midpoint index tables. Calibration versus
validation has **0/769,824** differing addresses; calibration versus pilot also
has **0/769,824**. All three table hashes are identical. Native spacing,
65,536-channel length, row order, widths and sixteen 4096-channel normalization
blocks agree. The full
[score-map result](results_radio_hd189733_score_map_2026-09-28/result.json)
retains the table hashes, exact contexts and code/source pins.

Thus identical relative raw arrays undergo the same normalization/filter/gather
score operator in the three frozen windows. This is stronger than identity
separation alone, but it does **not** prove noise-distribution exchangeability
between actual frequency regions. Absolute-frequency OFF matching and receiver
alias predicates were not covered. No threshold was rebound or transferred.
This calculation consumed zero new spectra/cases and took 0.133 seconds with
peak RSS 62,689,280 bytes, within its separate 120-second / 256-MiB scope.

## Budget, invariants and exact continuation

The [postflight reconciliation](results_radio_hd189733_adapter_2026-09-28/postflight.json)
verifies case consumption, all retained comparison hashes/counts, the published
code freeze and fifteen old invariant pins. **Development: 6/6, closed.
Calibration: 0/3. Evaluation cases: 0/24. Evaluation runs: 0/1. Remedies: 0.**
Pilot runs, new telescope requests and external messages are all zero. The
exhausted old synthetic acquisition ledger and empty telescope genesis are
unchanged; neither was reset or activated.

The receiver score adapter, finite-exposure development arithmetic and exact
score-map comparison are complete. Do not rerun them or spend the six identities
again. **Next: freeze the remaining calibration/evaluation execution protocol**,
including the already reserved three noise realizations and 24 signal/RFI/null
cases, renderer details for every width/activity pattern, exact scramble/null
construction, thresholds/rank rule and a context-bound numeric transfer mechanism.
Use the score-map proof only for score arithmetic; separately address distribution
and absolute-frequency decision assumptions. Then execute the fixed panel once,
preserving every trigger, veto, loss, unassociated survivor and failure.

Source-specific codec/runtime handoff and a verified integrated prospective
acquisition/trial protocol are still required before telescope spectra. The new
and original preparation contracts remain not-ready. HD1461's unresolved pointing
hold, untouched GJ724 reserve, neighbor9, failed/closed M43AI, original 112+128
M43AF holdouts, unresolved M15/M33, paused LS and unsent CHEOPS persist. The
three-sequence limit and 9 October consolidation date are unchanged.
