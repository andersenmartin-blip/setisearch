# LS4J: qualify fragment-local injection recovery

LS4I's published evidence shows strong injected bands retained as narrow
spectral events. This is a **post-LS4I development amendment**, informed by
that outcome. It does not replace LS4I, retroactively preregister it, or
constitute independent validation. The new endpoint is recovery of a resolved
part of the injected band, not reconstruction of its full spectral extent.
No detector event is merged, widened, reranked or newly generated.

## One fixed association rule

Keep the 50% bilateral overlap requirement in time. For frequency, require
both (a) at least 50% of the detected event interval to intersect the injected
truth, and (b) an intersection at least half the smaller of the truth width
and one detector base-bin width. One bin is 1024 native channels times
0.00286102294921875 MHz = 2.9296875 MHz. Published event endpoint spans can be
one native-channel spacing shorter; the nominal bin width is the resolution
unit used here. Thresholds are inclusive. Nonfinite or reversed intervals
fail, rather than count as nonmatches silently.

The absolute resolution requirement prevents arbitrarily tiny intersections
from counting. Event containment rejects a very broad unrelated event. A
fragment can associate without spanning half the truth; this is intentionally
a different recovery definition from LS4I. No physical bandwidth completeness
is inferred. Existing LS4I associations form a subset of the new associations.

## Qualification and fixed comparison

Before evaluating the revised accounting on the stored event ledgers, test
narrow fragments, exact boundaries, tiny/sliver overlaps, broad unrelated
events, short or displaced time intervals, malformed geometry, an independent
discrete-set geometry oracle, legacy inclusion, exact score/OFF behavior,
event-window preservation and abort-on-cap behavior. Keep the entire original
detector and residual test suite passing. Freeze this plan, configuration,
implementation and tests with dependency identities before classification.

Reclassify all 36 LS4I injected medium searches from the complete lossless
A1 ledger, using the complete B1 search and unchanged score-8 ON/score-6 OFF
thresholds and frequency-only adjacent-OFF veto. Replay LS4I associations
exactly first. Preserve every associated event and its veto evidence, including
vetoed events. Abort above 64 matches or on truncated source retention.
No new medium spectra need be read; no normalization or injection is repeated.

For each trial, classify five deliberately displaced truth regions: the other
original 32 s envelope at unchanged frequency, bands shifted -24 and +24 MHz
at the original time, and those same shifted bands at the other envelope.
These disjoint controls reveal chance associations on reused data; they do
not estimate a calibrated false-alarm probability. Keep all 180 injected-case
control records. Also classify the 12 width-labelled uninjected baseline
truths and their 60 controls; these repeat only four and twenty unique
geometries respectively. Pulse width is a label at this Stage-1 step, not an
extra independent observation.

## Conditional HTR continuation

If no injected event survives the unchanged Stage-1 OFF veto, the paired
conjunction has zero passes by that gate. Report zero HTR evaluations and do
not download HTR data merely to evaluate an already-false conjunction.
Otherwise follow all associated retained events through the **unchanged LS4I
HTR evaluator**, including vetoed matches for descriptive accounting, and
preserve its actual detected windows/bands, 0.5 MHz padding, channel-center
selection, separate digital amplitudes, truth-pulse association and LS4E
control vetoes. Retain the same 144 paired configurations and 12 baseline
comparisons. Replay all 48 separate fixed-window diagnostics against LS4I
within its frozen tolerances before claiming a complete continuation.

Only the known A1/B1 HTR products may be downloaded: 18,870,174,378 bytes in
total, each SHA256-verified before use. Permit at most two full attempts per
source, charging at most 37,740,348,756 bytes, with 4 GB free-disk headroom.
Keep one raw file at a time outside the synchronized workspace, delete raw
and partial files on completion or failure, and publish only derived event
evidence. Cap extraction at 64 unique bands. The runner refuses to overwrite
existing execution evidence; an interrupted/aborted HTR run is incomplete.

## Claims and next boundary

Report association counts before and after Stage-1 OFF, every displaced
control, actual selected-event HTR evaluations and paired conjunctions, if
executed. Distinguish an injected pass from a baseline-present result.
Do not multiply marginal rates or identify the two products' amplitude units.
LS4F sky-candidate dispositions and LS4I's 0/144 endpoint are unchanged.
A3/C1/D1 remain unopened. Even a successful development replay needs separate
validation and does not establish physical transfer, survey completeness,
independent confirmation, or a technosignature.
