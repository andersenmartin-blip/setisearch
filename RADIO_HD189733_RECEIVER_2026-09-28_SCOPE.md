# HD189733: bounded receiver-coordinate motion preparation

Prospective scope, 28 September 2026. Starting science commit:
`bece5c09ea4b27abe3db20b24bf8af35c7930173`. The alternate metadata acquisition,
header replay and widened window identities are complete; do not repeat them.
This work uses their retained bytes and opens no telescope spectral values.

## Scientific scope choice

Prepare a conventional **received linear-drift** search, with neighbor9 unchanged.
The hypothesis is expressed in recorded topocentric frequency versus elapsed
header-clock seconds. It is not a planetary orbit prediction. Source motion,
Earth motion and instrumental drift are included only insofar as their *combined
received track* falls inside the stated linear family. Do not assign an observer
multiplier of one and call it a barycentric calculation. No actual HD189733
planetary completeness, orbital posterior or absolute clock calibration is claimed.

An intentionally limited receiver-coordinate search is permitted by the ordinary
narrowband pilot objective. It does not resolve or adopt the earlier circular
planet scenario. The 27 September calculation showing that this scenario needs
width 257 remains valid and unchanged; that scenario is outside this proposed
linear pilot except for individual tracks satisfying its domain. Its 65,536-channel
extractions and three disjoint native chunk selections are retained unchanged.

Primary methodological context: Price et al., *The Breakthrough Listen Search for
Intelligent Life: Observations of 1327 Nearby Stars over 1.10–3.45 GHz* (2019),
https://seti.berkeley.edu/listen2019/BL1327stars.pdf, reports a ±4 Hz/s search.
The official https://github.com/UCBerkeleySETI/turbo_seti documentation describes
narrowband drift searching. These sources motivate a bounded scope only; their
pipeline, sensitivity and detections are not imported into neighbor9. Our full
cadence linearity requirement is more restrictive than a per-scan drift search.

## Fixed bank and conditional geometry check

For each frozen window centre C, use `F_r(t)=1+r*t/C`, with 81 rate labels
`r=j/10 Hz/s`, integer j from −40 to +40. At carrier q the actual slope is q*r/C;
report that value, not r, as the physical Hz/s. Time zero is the first ON midpoint.
Clock arithmetic starts from exact rational representations of retained binary64
header MJDs and integration times. Preserve all 96 start/mid/end rows.

Use 81 scored carrier centres C+k*df, k=−40..40, plus nine non-scored support
bins on each side: 99 support centres. The continuous carrier domain is the
closed span of scored centres, without extrapolation beyond its endpoints.
The rate-label domain is the closed interval [−4,+4]. Include zero drift;
it is not by itself evidence of RFI or permission to discard a trigger.

Use the unchanged native width bank [1,3,5,9,17,33,65,129]. Check only whether
the largest width geometrically contains a linear signal of intrinsic total
width at most one native channel, including rate quantization, carrier
quantization, integration sweep, predicted-bin rounding and occupied-bin
rounding. Use exact rational upper bounds for these separate terms. The smaller
widths have no asserted continuous-family coverage. Geometric containment is
not recovered power, sensitivity or a recovery test. No curvature allowance is
silently added. Nonlinear tracks, frequency steps, intermittency within an
integration, oscillator errors and broader intrinsic signals remain unqualified.

At most three distinct 81×96×3 binary64 factor tables may be constructed for the retained
windows. Independently check every table element against exact rational
arithmetic, with frequency-equivalent error <=1e-4 Hz. Bind input hashes, clock,
rates, role and window identities and array hash in a new receiver-specific
type. Do not impersonate DirectFactors or an orbital FactorBasis. No downstream
constructor, score, decoder or old scientific certificate is authorized here.

## Fresh identities and budgets

Reserve distinct deterministic SHA-derived namespaces for six development,
three calibration and 24 evaluation cases, separate from every earlier
configured seed/namespace. Development is synthetic-only. Telescope calibration,
validation and pilot retain their three disjoint native-chunk inventories;
multiple challenges within one role are not independent observations.

The existing *unexecuted* 3-calibration/24-case/one-evaluation/zero-remedy ceiling
is reassigned prospectively to this source-specific panel; it is not doubled.
The previous HD1461 panel remains archived, unexecuted and inactive under this
plan. No failed panel is reopened. The exhausted acquisition ledger stays closed
and the old telescope genesis stays empty. This task executes zero development
spectral cases, calibration cases, evaluation cases or pilot runs.

Preserve the prior panel's case-kind allocation (10 ON signals, 10 matched ON/OFF,
two single-adjacent-OFF controls, two nulls), widths/powers and numerical
recovery/RFI/null gates, but bind fresh identities to this receiver scope.
Assign rate labels cyclically [-4,-2,0,2,4] in retained case order and carrier
offset zero. The assignment is prospective, not a tuning result. Development
identities reserve distinct off-grid rates [-3.95,-1.95,-0.05,0.05,1.95,3.95];
their eventual injection renderer and outcome criteria must be frozen before use.
Do not claim this identity reservation is an executable integrated protocol.

New engineering verification budget: at most 20 tests, one retained analytical
qualification result, no telescope network request, no synthetic acquisition,
no detector/calibration run. Stop on any scope, binding or coverage mismatch;
retain technical errors. Do not optimize rate spacing/width against outcomes.

The next integrated protocol must still supply and verify numerical transfer,
control rendering/recovery, source-specific codec/runtime handoff and cumulative
attempt/resource accounting before spectra. The original and new preparation
contracts remain not-ready. Preserve HD1461's hold, M43AI's closed failure,
112+128 untouched M43AF holdouts, unresolved M15/M33, LS pause and unsent CHEOPS.
No external messages, other target selection or plan extension is authorized.
