# BZ: prospective nested drift-grid experiment

BY recovered 11/24 medium-amplitude ON-only geometries in all three available
ON scans. Its posthoc diagnostic motivates this explicitly adaptive experiment:
does adding intermediate drift rates improve that conditional recovery?

The exact 264 cases, 24 geometries, five normalized q254 backgrounds,
exposure-integrated triangular injection model, amplitude levels, four kernel
widths, strides, truth-matching tolerance, thresholds and OFF association radius
are inherited from BY. No new observation or blind search is performed.

The closed factor-one results are reused exactly. New factors 2, 4 and 8 use
nested subsets of a 17-rate union inside the same original three-rate interval.
The three original anchors remain exact; only fourteen new rates are computed.
This adds 198,696,960 correlated track sums and 73,920 full-core calibration
vectors. The 1,320 injected matrices must reproduce their BY hashes exactly.

All truth-matched source-scan peaks are projected across the actual scan times.
The original OFF association radius remains unchanged. The endpoints are source
recovery, three-ON recovery, rejection in available OFF scans and partial
retention, with gains/losses against BY and overlapping retained/rejected seed
outcomes reported. Nested inclusion makes any-seed recovery monotone; that is a
construction property, not independent evidence. Twenty-four zero controls and
all-five injections remain in scope.

Production and independent review run separately under the prospective plan's
600-second child CPU/wall caps, 2-GiB address-space cap and 64-MiB per-file cap.
Each uses exclusive tmpfs outputs, natural child closure, source/input hashes
before and after execution and verified closed archive export. Other executor
and agent filesystem activity pauses while a scientific child is active.
There is no automatic retry; any failure remains closed and preserved.

The independent review reconstructs injections, all new full calibration
vectors with direct addition, source peak selection, projected scalar scores,
classification and group summaries. Baseline numerical bytes are bound to the
already-audited BY outputs rather than rerunning the closed coarse detector.

This is development on exposed deterministic cases, not a held-out validation,
global false-alarm calibration, normalization-response measurement, sensitivity
in Jy or a complete cadence. Added templates increase correlated trials at
fixed ESS thresholds. OFF5 remains missing, original archive authority and the
fresh-data queue do not advance, and there is no astronomical candidate claim.

Six additional repositories were inspected for eligible original ON/OFF power
data. No eligible new payload was found; the bounded search receipt accompanies
this plan. Original archive access remains unavailable in the current network
environment. No alternate routing or acquisition workaround is attempted.

Execution requires publication of this scope, all new sources/tests/review and
PLAN_BZ.json, followed by exact content readback and PUBLIC_FREEZE_BZ.json.
