# M43U: native signal and interference challenge at additional carriers

## Question and fixed scope

M43T recovered known strong signals, but its uninjected masks were empty. This
combined development experiment asks whether neighboring support also protects
undesired power, and whether strong neighboring power causes true-signal loss.
Compare `legacy`, `neighbor2` and `neighbor9` prospectively in one experiment.
The rules differ only in support radius (0, 2 or 9 proxy bins); the same-width
thresholds >=10 / >=3, eight-width OR and final nine-bin dilation remain fixed.
Use the exact M43T implementations for legacy/neighbor9. The two-bin policy is
the same mathematical rule as the separately published M43T neighbor2 test.
No radius optimization or production adoption is authorized by this panel.

Reuse the verified six scans, 37 templates and 4,097 score carriers from M43T.
No new observing coverage or telescope download is planned. Four new injection
centers are score indices 512, 1536, 2560 and 3584; previous centers 1024 and 3072
are excluded. Cross each with parent anchors 0 and 1700 (local templates 0,36).
The four carrier positions use activity subsets [0,1], [0,2], [1,2], [0,1,2]
respectively. Thus carrier and activity remain confounded; this is eight strata,
not a complete factorial completeness estimate. All detection widths, activity
subsets and templates are searched in every execution.

## Seventy-two shared native inputs, three policies each

Each of the eight strata has nine cases, in the declared order:

| Case | Native additions | Ground-truth endpoint |
|---|---|---|
| nearest | Strength 32, snapped native single-bin profile, exact anchor | Signal recovery |
| fractional-only | Strength 32, continuous native positions, +0.5 proxy bin, finite sinc-squared, no smear | Signal recovery |
| template-offset-only | Strength 32, snapped native single-bin profile, inherited M43S near-template coefficients | Signal recovery |
| smear-only | Strength 32, native-snapped centers, finite sinc-squared averaged over one native-channel sweep | Signal recovery |
| combined | Strength 32, inherited near-template coefficients, +0.5 proxy bin, one-channel sweep | Signal recovery |
| single-epoch | Strength 32 at the first active epoch only, snapped anchor track | Synthetic interference control |
| supported-spike | Same strong component; strength 4 at center+6 proxy bins in the other active epochs | Synthetic interference control |
| ON-OFF | Strength 32 on the same anchor hypothesis in all active ON and corresponding OFF scans | Synthetic interference control |
| mixed | Combined true signal plus strength 128 snapped-anchor component at center+12 bins in the first active epoch | Signal recovery under interference |

There are 40 clean signal cases, 24 controls and 8 mixed cases: 72 distinct
native inputs and 216 new detector executions. Three baseline executions are
reported separately, not reused as independent trial endpoints. Only strength
32 true signals are tested. The component strengths are nominal integrated
added power, not observed output SNR. Controls deliberately do not carry an
astrophysical true-signal label; their known origin is the constructed injection.
They model specific instrumental/interference-like patterns, not the observed
population of terrestrial interference. Their leakage fraction is not a FAP.

Profiles are added after the unchanged normalization and before filtering.
All components sharing a scan are added in declared order to complete float32
native windows, then filtered once. Overlapping profile supports must not
overwrite one another. Recompute complete affected gathers; include all ON
additions in native receiver signatures and all OFF additions in OFF retention
and paired-OFF measurements. Preserve original source receipts. Validate all
96 original arrays and all 48 ON/OFF native cache/gather anchors before trials.
Metadata-only geometry must give <=20 Hz center-track support for every signal
case; fail rather than selecting replacement positions after seeing scores.

## Calibration, endpoints and immutable decisions

Publish this plan, code, focused independent known-answer tests and hash-pinned
configuration before new score evaluation. Seed 430022 generates 256 unique
[0,a,b] circular shifts with separation/edge guard 128, excluding all M43R,
M43T neighbor9 and M43T neighbor2 training/held-out rows. All three policies use
the same first 128 training and last 128 held-out shifts. Compute each threshold
as max(10, maximum training score), with inclusive rank p<=0.01. Seal all three
calibration bindings before any held-out or injected evaluation. There are 768
policy-specific maxima from 256 shared shifts, not independent noise trials.
As before, masks are estimated on full-support uninjected data, then cropped
and co-rolled with scores; they are not regenerated after scrambling. This
conditional baseline comparison does not calibrate the new interference cases.

Signal recovery uses the exact active subset and <=20 Hz maximum center-track
error at every active ON integration, followed by unchanged physical vetoes
and rank eligibility. Report retained, physical and final association counts.
For controls report all ON/OFF retention, physical dispositions and the number
of final diagnostic survivors, plus whether a case has any survivor. Never
call these survivors astronomical candidates. Report mask occupancy by policy,
every signal gain/loss and every control-case leakage gain/loss versus legacy.
The 10,000-record and inherited exact-comparison limits fail closed: a cap
overflow is an incomplete experiment, never a truncated successful endpoint.

For each alternative separately, broader validation requires no recovery loss
among the 48 signal-present cases, no increase in control cases with any final
survivor versus legacy, no final survivors in any of the eight ON-OFF controls,
and no additional held-out threshold exceedances. These are development gates;
passing does not establish general noise safety or completeness. A failure is
reported without retuning radii, amplitudes, positions or truth definitions.
Choose subsequent work from the measured failure stage, including further
carrier/activity combinations and independent observing sequences as needed.

Keep every sealed per-case checkpoint, full compact member dispositions,
component/patch receipts, exact input hashes, null arrays and logs. Publish the
entire 72-record checkpoint set in a deterministic lossless gzip JSONL ledger,
with compressed and uncompressed checksums. Compare three-policy input and
overlay identities. Completed results are protected from overwrite; restarts
must match the public freeze, config and all three calibration bindings.
