# M43R: frozen joint null / native-injection pilot

This is the first fresh calibration and native-injection recovery pilot of the
connected M43 detector. Publish this plan, executable code, exact shift rows,
truth inventory and dependency hashes before reading new evaluation outputs.
Preserve any failed attempt; changes after evaluation require an amendment.

## Scope and reuse

Use the 37 M43P/Q parent templates 0–31 and 1696–1700, all eight widths and
four activity subsets, and the same six receipt-verified scans from one observing
sequence. Use 4,097 central score carriers (half-width 2,048 bins) at 1412.5 MHz
with 64 support guards each side. Require the new 4,225 support frequencies to
be bit-identical to the central slice of the M43P grid. Original normalization,
filtering, masking, integration, retention, OFF and receiver vetoes are unchanged.
This is neither the complete bank nor the full frequency interval.

Reuse all 96 verified M43P anchor arrays. Rebuild 24 original ON native caches
once, require their ancestor identities, and verify every cropped row-integrated
baseline score against the anchors. Do not repeat completed full-band censuses.
Original code and endpoints remain unchanged; M43R has separately named adapters.

## Joint design fixed before evaluation

Generate 256 distinct circular-shift rows with NumPy PCG64 seed 430018, each
beginning with zero. Reject rows whose circular pairwise epoch separation is
less than 128 bins. First 128 rows calibrate; the last 128 are held out. The exact
rows, split and hash are written in config before publication. Each row is shared
by all templates, widths and subsets. Shift scores and existing masks together.

The threshold is max(10, maximum of the 128 calibration global maxima), using
the inherited inclusive retention rule and inclusive rank p with ceiling 0.01.
Freeze that certificate before running held-out shifts or any injected trial.
Never recalibrate on injected data. Report held-out counts both >= and > this
threshold, all maxima and their ranks. This measures resampled **pre-veto**
score exceedances. Shared data and overlapping shifts are correlated; do not
give an independence-based binomial confidence interval, or call this a measured
physical false-alarm rate. No physical-veto interpretation of circularly shifted
receiver frequencies is attempted.

Eight truths: parent templates 0 and 1700 crossed with the four exact activity
subsets, each at central score index 2048. Nominal active-epoch SNR levels are
0, 8, 32, 64; all 32 truth/level endpoints are kept. Execute the common zero-signal
background once and reuse it explicitly for eight zero-level denominators.
At each active ON integration, add float32(SNR/sqrt(16)) to the single
nearest-even native channel of that truth's exact template factor. OFF scans and
inactive ON epochs receive no addition. Insertion is after fixed normalization
and before filtering and gathering. This idealized bin-centered profile has no
fractional-channel leakage or intra-integration smearing; it is not an astrophysical
population completeness model and cannot measure off-template sensitivity.

The overlay retains its original source identity as background ancestry and gets
a separate injection receipt. It never impersonates an unaltered telescope source.
Recompute complete affected native windows and integrate complete affected proxy
columns in ascending float32 order. No analytic increment is added to integrated
scores. Stationary receiver signatures use these same native filter patches.

The primary recovery endpoint requires a retained member at the exact injected
parent template, exact activity subset and exact score carrier, any of the eight
widths, passing all evaluated physical vetoes and the fixed inclusive rank cut.
Also report retention, physical-veto passage and final recovery separately;
preserve every compact member decision. This intentionally strict on-template
endpoint must not silently expand to neighboring carriers after seeing results.
Report nominal score increments at width 1 and the truth mask to explain losses.
Maximum 10,000 records per retention ledger; inherited physical-stage caps apply.
Capacity exhaustion fails the attempt; never truncate and report success.

## Validation, outputs and claim boundary

Before freezing, test native patches against full materialized injection/filter/
gather for every width, including zero additions and duplicate/skipped mappings;
require bit identity. Verify the fixed-calibration entry point preserves all six
M43Q known-answer dispositions and cannot call calibration during retention.
Reuse previous unchanged tests. Runtime Python and NumPy versions are pinned.

Save baseline and every injected trial as sealed compact audit files: pipeline
hashes, stage certificates, all retained ON member decisions, source overlay
receipts, truth diagnostics and all denominators. Save calibration and held-out
maxima, run logs, result report and checksum manifest. Publish results and update
main README under the owner's standing approval. No astronomical candidate is
authorized by this pilot, including any unmodified background member. Report
the practical next step from actual results; no claim of a completed SETI search.
