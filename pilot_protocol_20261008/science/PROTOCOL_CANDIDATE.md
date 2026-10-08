# New radio pilot: prospective scientific definition, 8 October 2026

**CANDIDATE_NOT_FROZEN_NOT_EXECUTED.** This is a separately scoped exploratory
study under the approved 7–20 October plan. Its candidate configuration,
engine, control generator, exact case manifests and source admission must be
reviewed and pinned together before development values are generated. No
pilot power array or new control realization was opened to write this document.
The historical preparation and its failures remain unchanged. Ordinary version,
input-byte, command, settings and output reproducibility replace the old
historical-runtime/loader/custody execution contract only for this new study.

The executable definitions are `pilot_engine_20261008/detector.py`,
`pilot_controls_20261008/generator.py` and
`pilot_controls_20261008/summarize.py`. The exact source/control geometry is
`pilot_controls_20261008/control_contract.json`; panel membership and recipes
are `development_cases.json`, `validation_a_cases.json` and
`validation_b_cases.json` in that same controls directory. The accompanying
science config binds these actual paths and their hashes. No differently named
generator or implied panel is an executable substitute.

## Exact pilot geometry

The first source candidate is HIP98505/HD189733, cadence 85030,
AGBT16A_999_97 scans 0003–0008: ON, OFF, ON, OFF, ON, OFF. Historical metadata
are input to planning, not proof of present spectral access. Current URL,
ETag/size, headers, physical shape, codec and bounded stored-byte evidence are
separate source gates. Physical shape is (16, 1, 264503296) with time, feed,
frequency axes; the contradictory DIMENSION_LABELS attribute is retained and
must be reconciled against the published filterbank representation before
source admission.

Every file has channel spacing −2.835503418452676 Hz and integration length
17.986224128 s. Preserve actual file epochs and gaps. Row times are integration
midpoints, not a concatenated 96-row uniform series. The common reference time
is the midpoint of the first and last row midpoint of the whole cadence:
MJD 57464.7012082152. Float64 relative seconds are calculated from a common
MJD anchor to avoid repeated large absolute-frequency/time subtraction.

The ON search contains exactly 4,096 native reference-frequency centers,
half-open original channel interval **[159905792,159909888)**. Their descending
endpoint frequencies are approximately 1423.0514239036174–1423.039812517119 MHz.
The interval is chosen from metadata around the previously unopened pilot
region, not from signal values. Nominal bandwidth is 4,096 channel widths;
the endpoint-center span is 4,095 widths. Both quantities are reported.

Use linearly drifting receiver-frame frequencies f(t)=f0+d(t−Tref), with
d in [−4,+4] Hz/s. The fixed grid is linspace(−4,+4,2n+1),
n=ceil(4*Tspan/min|df|). Here Tspan=1918.7933614068413 s, n=2707,
5,415 grid values and step 0.0014776505356483192 Hz/s. Half-step displacement
over the **entire** span is 0.4999651949 channel, conservatively satisfying
the half-channel grid rule. This is narrower than arbitrary planetary or
curved-track coverage; no such completeness is asserted.

The largest midpoint distance from Tref is 959.3966807034207 s. Drift alone
needs 1,354 channels of halo. OFF matching additionally needs a conservatively
derived 250-channel reference-frequency halo. Add maximum box half-width 16,
frequency-filter half-width 250 and one rounding guard. Decode the declared
interval **[159903921,159911759)**, 1,871 channels beyond each ON-band edge.
This remains wholly within HDF frequency chunk 152, whose actual bounds are
[159383552,160432128). Required stored ranges and decoded bytes are distinct;
their actual byte counts are recorded before any power access.

## Statistic and fixed search rule

For each scan, use the same fixed 4,096 original channels as the normalization
core. Every requested row must be complete. Zero power is allowed;
nonfinite, missing or negative power fails the input. No source-value-selected
channel mask, DC mask or amplitude mask is introduced. The native pilot's
predeclared validity mask is all-valid; synthetic mask/edge source fixtures do
not silently change this pilot policy.

For every row: divide power by the core median; subtract a 501-channel running
frequency median. Let m0 be the median core residual and
s=1.4826*median(|core residual−m0|). Its background location is
m0+mean(clip(core residual−m0,−5s,+5s)). Subtract that location and divide by s.
Fail if the power median or scale is nonpositive/nonfinite. The winsorized mean
addresses the positive mean-minus-median of skewed Gamma controls while
bounding the influence of strong narrow RFI. It is an explicit prospective
location estimator, not a calibration of native noise.

Score each nearest-channel linear track with widths 1, 3, 9 and 33:
sum of standardized values over every row and the odd frequency box,
divided by sqrt(Nrow*width). Round the complete absolute-frequency mapping
with rint, ties to even; do not separately round a drift shift and base carrier.
Every declared track must retain width/filter support. Track masking or absent
support is an explicit accounting item or input failure, never an empty hit.

The statistic is **robust_box_track_score**, not turboSETI SNR, a Gaussian
significance, received flux or EIRP. For each ON reference center retain its
maximum over the complete drift/width bank; ties choose first width in
1/3/9/33 order and then first ascending drift. A primary ON hit is such a
maximum **>=10**. Retain all primary ON hits and all six score/drift/width
maximum maps, including rejected hits. This explicitly defines the primary hit
inventory; it does not promise a retained full width×drift×frequency score cube.
No repeat requirement removes a single-ON occurrence.

## OFF rejection: coupled originating-ON fit, not winner-only matching

For an ON hit (f0,d,wON) and trial OFF width wOFF, define
C=(wON+wOFF)/2+2 channels. An OFF hypothesis (f0′,d′,wOFF) is compatible only
when **both first and last row midpoint of the originating ON scan** satisfy
|(f0′−f0)+(d′−d)*tON| <= C*max(|dfON|,|dfOFF|), using seconds from Tref.
For each trial drift, intersect the two allowed f0′ intervals and enumerate
the native reference centers in the OFF band plus its fixed halo. This couples
frequency and drift uncertainty from the short ON scan before projecting that
same global hypothesis into the OFF scan. A broad box does not imply localization
to two tiny global-grid steps.

Score every allowed OFF hypothesis until a **>=8** witness is found or the
family is exhausted. Any witness in any of the three OFF scans gives
OFF_MATCHED; otherwise the original ON hit is SURVIVOR_EXPLORATORY. Do not use
only the OFF carrier's winning drift: a stronger incompatible track can hide a
weaker compatible RFI track. Save the witness, originating-ON endpoint tolerance,
checked count, scan identity and exhausted/nonexhausted status. Early stopping
proves an existential veto; it does not claim the entire family's maximum or
complete count. A frozen traversal makes witness selection reproducible.

This is a conservative rejection rule, not a joint trajectory fit or proof of
origin. Its loss of genuine ON-only signals under unrelated OFF contamination
is measured explicitly in fresh controls. A survivor remains unresolved.

## Fresh control allocations and injection law

The generator and full deterministic manifests define DEV24, VAL_A142 and
reserved VAL_B142 in separate namespaces. The exact case ID is
`SETI_RADIO_PILOT_20261008_{DEV|VAL_A|VAL_B}:family:serial`, with the serial
zero-padded to three decimal digits. SHA256 of that complete ASCII case ID
produces a 64-hex-digit seed identity. Interpret the **entire 256-bit digest**
as an integer and initialize `numpy.Generator(numpy.random.PCG64(seed))`;
do not truncate the digest or substitute a per-run seed. No old realization, seed namespace,
127/24 identity or 112+128 holdout is imported. VAL_B is permitted only after
one separately frozen development revision, preserving VAL_A's failure.
Only new DEV cases may guide that revision. Validation is not replayed.

Signal/RFI controls use independent Gamma(shape16,scale1/16) power, mean 1,
sigma 0.25. An intrinsic uniform line of width 1 or 3 native channels is
convolved with the uniform frequency sweep |d|*tsamp during each integration.
Integrate that distribution into each channel bin with the exact convolution
CDF. Needle-per-row injections at 4 Hz/s would unrealistically omit the
approximately 25-channel within-integration sweep and are not used.

Per active scan, compute B from the unfiltered, noise-free, unit injected
profile: its maximum true-trajectory odd-box sum/sqrt(Nrow*width) over the four
declared widths. Injection amplitude is target*0.25/B. Targets are 24 for
strong cases and 12 for operating cases. This nominal ideal statistic fixes
the injected difficulty prospectively; it is not a measured detector score.
Truth is allowed only in generation and recovery evaluation, never detector
normalization, thresholding, masks, matching or ranking.

VAL_A and VAL_B each contain:

- **14 strong signal cases:** all seven nonempty ON activity subsets × drift
  −4/+4 Hz/s; every case must recover all injected active ON scans.
- **48 operating signal cases:** three single-ON and three two-ON patterns ×
  drift −4/−1.25/+1.25/+4 × intrinsic width 1/3. Require >=44 complete case
  recoveries, >=7/8 in each activity pattern, >=10/12 at each drift and
  >=22/24 at each intrinsic width. Edge/interior and fractional-bin placements
  are frozen in the exact manifest; no edge loss is silently omitted.
- **24 matched RFI cases:** trajectory present in ON and OFF at equal nominal
  strength. Every primary ON scan must first detect the injected trajectory;
  no final ON carrier may survive in any of the 24 cadences. A subset adds a
  stronger incompatible OFF trajectory, testing the winner-only failure mode.
- **32 fresh noise cadences:** eight each of stationary Gamma16, positive
  Gaussian mean1/sigma0.05, row-gain Gamma16 and frequency AR1 Gaussian with
  rho0.25. At most one cadence may have any final survivor. Row-gain and AR1
  initialization/equations are fixed in the manifest; no clipping repairs a
  negative/nonfinite draw. This gate qualifies only these synthetic laws.
- **12 single-row ON transients and 12 near-OFF contamination cases:** diagnostic
  groups, outside the 48 recovery denominator. Keep their complete hits and
  losses; no new veto is adopted from their outcomes.

A recovery requires, for **every active injected ON scan**, a localized final
survivor. For that scan, use C_recover=2+max(winning width, oracle injection
width)/2 channels. At both its first and last row midpoint the winning and
true frequency trajectories must differ by <=C_recover*|df|. Report raw-ON,
any-active final and all-active final recovery separately. This states the
physical resolution of the tested boxes without demanding unrealistically
precise global intercept/drift recovery from a single short scan.

All gates are joint. For **all 24** matched RFI cases require
`pre_OFF_all_active_recovery=true`: all three injected ON trajectories must
first be correctly localized above the ON threshold. Then require zero
surviving ON carriers anywhere in each cadence. The aggregator reads this
explicit field; an absent/false field fails the RFI gate. An RFI case with no
initial localized ON hit is not a successful RFI rejection. A zero hit list from a fully completed computation
is a valid EMPTY result. Missing rows, incomplete controls, budget failure or
missing outputs are failures, not EMPTY. Default rank calibration is disabled;
no conditional-null finite-support requirement is introduced. If a later new
scope uses ranks, EMPTY ordering and inclusive ties must remain explicit.

## Retention, limits and admissions

Keep immutable per-case recipes/seeds, raw-array hashes, all six maximum maps,
all primary ON hits and their OFF dispositions, localization/loss accounting,
versions, logs, resource use and partial failures. Synthetic arrays can be
reproduced from their frozen recipe rather than all retained in the 8 GiB
workspace. Do not store the full drift×width cube per case. Pilot raw decoded
patches or byte-identical durable inputs and range manifests must support replay.

Limits remain 0 kr, 4 GiB RAM, 2 GiB source bodies per pilot cadence,
4.25 GiB source bodies for the approved plan, 8 GiB workspace, 30 minutes wall
per job and 12 CPU-hours across new calculations. Count failed attempts too.
Preserve the ordinary cumulative resource ledger; no old reservation resets.

Before DEV: pin and review the complete engine/generator/config/manifests and
resource state. Before VAL: close DEV, freeze the exact final settings and
allocated fresh panel; change no scientific setting after the first value.
Before pilot: pass complete fresh joint control gates and actual source
metadata/codec/range-byte admission. An engineering reference or old test
receipt cannot substitute for this validation.

The allowed conclusion is an exploratory receiver-frame linear search and
digital method behavior on the stated controls. No sky false-alarm probability,
flux/EIRP bound, population limit, planetary/curved completeness, independent
multi-visit confirmation or extraterrestrial origin follows from this pilot.
