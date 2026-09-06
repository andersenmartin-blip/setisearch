# M43S: weaker signals and a defined fractional / off-template / smear profile

M43R recovered all 24 ideal on-template injections at strengths 8, 32 and 64.
It did not locate a sensitivity transition. This prospectively frozen extension
tests lower strengths and a deliberately harder profile, with more carrier
positions. Publish this plan, executable model, exact truth inventory, geometry
and dependency hashes before any new injected evaluation. Preserve M43R and all
earlier denominators and endpoints unchanged.

## Fixed search, reused calibration

Keep the M43R detector, its 37 templates, 4,097 score carriers, eight widths,
four activity subsets, masks and physical vetoes unchanged. Restore the M43R
threshold certificate (threshold 10) and its 128 calibration maxima from the
independently pinned sealed artifact. Validate the exact same baseline score
inventory and all 24 native cache/gather identities. Do not recompute nulls,
reuse held-out shifts as new evidence, or recalibrate injected trials. The
earlier 0/128 pre-veto exceedance result remains a correlated diagnostic.

## Fixed 16 truths and 112 endpoints

Two carrier/anchor groups: parent template 0 at score index 1024, and parent
1700 at index 3072. Cross each with the four exact activity subsets and two
profiles, making 16 truths. Evaluate strengths [0, 2, 4, 6, 8, 12, 32], for
112 endpoints: 96 new nonzero detector executions and 16 zero-level endpoints
explicitly reusing the same M43R background execution. Carrier and anchor are
paired, not independently crossed; their effects cannot be separated here.

Profile A, `ideal-native-bin`: unchanged M43R nearest-even single native channel
along the exact anchor template at the selected grid carrier. Its strength is
the nominal width-1 active-epoch SNR before addition to the background.

Profile B, `fractional-off-template-smear`: perturb anchor 0 toward parent 1,
or anchor 1700 toward parent 1699. Use coefficients anchor + fraction*(partner
- anchor). Select the largest dyadic fraction 2^-k (k=1..24) whose nearest
search member has maximum active-row center-track error <= one native channel
(2.835503418452676 Hz). This selection uses metadata only, separately for each
activity subset, before publication and injected evaluation. Record every tried
fraction and retain the original half-way geometry checks as separate controls.
If no fraction qualifies, fail the preflight rather than drop that truth. The proxy
carrier is +0.5 bin from the selected carrier. At each integration, use its exact
truth center in continuous native-channel coordinates. Spread added power using
a sinc-squared response averaged over 17 equal midpoint time samples of a linear
one-native-channel sweep centered on that integration's truth frequency. Retain
native indices from floor(center-0.5)-16 to ceil(center+0.5)+16 inclusive, and
normalize that finite packet to sum one. Save unnormalized retained masses and
profile hashes. This finite response and imposed sweep are a defined injection
model, not a measurement of the telescope channelizer or physical drift rate.

For both profiles, add total strength/sqrt(16) per active integration after
the existing fixed normalization, before native filtering/gathering. Cast each
native-channel addition to float32, add to the background in float32, then
recompute complete affected native windows and complete affected proxy-column
integrations in the established order. Receiver signatures use those same
patches. OFF and inactive ON data remain unmodified. For B, strength denotes
total profile power on the A normalization scale, not its actual peak or
matched-filter SNR. Combining fractional placement, template mismatch and sweep
tests their combined impact; it does not identify their individual contributions.

## New named association endpoint

M43R's exact-template/exact-carrier endpoint cannot describe an off-grid truth.
M43S's primary endpoint therefore requires the exact injected activity subset,
and a retained member whose predicted center track is within **20 Hz at every
integration of every active ON epoch**. Any of the 37 templates and eight widths
may provide that member. The same member must pass the unchanged physical vetoes
and inclusive rank p <=0.01. This is a new endpoint, not a relaxation applied
retroactively to M43R. Keep retention, physical passage and final recovery
separate. For ideal profile A also retain the old exact-template/carrier criterion
as a secondary diagnostic at these new carrier positions.

Freeze the metadata-only nearest geometric member and its maximum active-row
residual for every selected truth. During pre-freeze drafting, all eight literal
midpoints were outside the 20 Hz association scope of this sparse 37-template
sample (about 43–2,727 Hz nearest residual). Preserve these midpoint controls in
config and the report; they are geometry-only results, not injected trials and
not part of the 112-endpoint denominator. The dyadic supported perturbations
allow the numerical sensitivity test to address signal recovery rather than a
known absence of any associated hypothesis. This samples near-template offsets,
not the full intervening parameter space or the complete 1,701-template bank.
Do not drop misses, search other subsets after inspection, or widen 20 Hz after
results. The 112 endpoints share background data, and profile families are paired;
do not attach independent-binomial confidence intervals or claim population
completeness. Every retained compact ON member decision is kept in audit files.

## Validation and execution

New tests compare the fractional response with a scalar time average, check mass
and symmetry, and compare patch application against full native materialization
for all eight widths and zero/weak/strong additions. Association tests include
the inclusive 20 Hz boundary, wrong activity, one failing active row and an
irrelevant inactive row. A persisted-threshold fixture must produce the identical
M43R pipeline result while calibration calls are disabled. Reuse prior tests
for unchanged code; publish focused test output and pin Python/NumPy versions.

Use the established 10,000-member retention caps and physical-stage limits.
Failure or capacity exhaustion is a failed attempt, never truncation. A restart
may reuse completed sealed trial checkpoints only with matching freeze, config,
truth and strength. Preserve failure records if an amendment becomes necessary.
Publish all 112 endpoints, all 96 compact trial audits, provenance, logs, a
plain-language result report and checksum manifest, and update main README.
No astronomical candidate or scientific nondetection is authorized by M43S.
