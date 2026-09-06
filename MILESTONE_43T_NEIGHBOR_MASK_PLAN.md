# M43T: neighboring support in the isolation mask

Prospective repair-regression experiment, chosen after inspecting M43S losses.
This is not an independent discovery or completeness test. Original M43R/S
results and their calibration remain intact.

## Fixed change

The named `neighbor2` policy flags an epoch value >=10 only when neither other
epoch has a value >=3 within two proxy-carrier bins, at the same spectral width.
Support windows are clipped, never circular. Flags are still ORed over all eight
widths and dilated by nine bins before the full-support mask is cropped. The
`legacy` policy calls the original exact-carrier implementation unchanged.
The radius is fixed at two before new numerical evaluation, motivated by the
displaced native-profile peaks in M43S. No radius sweep is planned.

Before calibration, compare both implementations with an independent
sliding-window/prefix-count reference on every full-support mask bit in the
37-template, six-scan pilot. Require exact agreement and neighbor2-mask inclusion
in the legacy mask. Known-answer tests cover isolated noise, displaced pairs,
threshold equality, clipped edges, width OR and unchanged physical-stage outcomes.

## One grouped numerical experiment

Reuse the identical 4,225-support/4,097-score grid, all eight widths and four
activity subsets. Freeze 256 explicit shift rows with seed 430021 and minimum
circular separation 128 bins. Exclude every old M43R row and duplicates. Use the
same first 128 rows to calibrate each policy and the same remaining 128 for
held-out comparison. Each policy has its own certificate and window identity.
The threshold is max(10, maximum training score); diagnostic rank ceiling .01.
Report all maxima and inclusive held-out exceedances. These are correlated
within-sequence pre-veto resamples, not physical false-alarm probabilities or
independent observing sequences.

Run neighbor2 through the complete detector on the uninjected baseline and on
all 16 unchanged M43S truths at strengths 12 and 32: 32 native-profile trials.
Keep the original normalization, finite smeared profile, native filter/gather,
physical OFF and receiver vetoes, and 10,000-record fail-closed cap. Rebuild and
verify the same 24 native caches. Every regenerated injected score inventory
must exactly match its sealed M43S counterpart before detector evaluation.
The primary recovery endpoint remains exact activity subset plus <=20 Hz
maximum center-track residual over every active ON row, any width/template,
physical survival and diagnostic rank eligibility.

Pair each new endpoint with its already completed M43S endpoint at the same
input and strength. These historical legacy outcomes retain their original
M43R certificate; do not relabel them as newly executed. Separately report
whether the fresh legacy threshold and all historical member rank-eligibility
decisions agree with that historical calibration. If they differ, identify the
calibration confound rather than claiming a mask-only improvement. No automatic
retuning, omitted failures, or rerun legacy panel is authorized by this protocol.

Publish code/configuration before evaluation, then native audit records,
reference anchors, full calibration/held-out maxima, paired results and logs.
An error stops the run and is recorded; completed sealed trials may be resumed
only under the same freeze and input identities. No new telescope requests,
full-bank coverage claim, astrophysical candidate claim, or general adoption
of this mask follows from this targeted repair panel.
