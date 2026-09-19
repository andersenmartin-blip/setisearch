# LS7X — prospective CHEOPS DEFAULT L2 short-transient pilot

Frozen 19 September 2026 before any L2 table row or FLUX value is read.
The preceding metadata-only preflight is public and records zero table-data
bytes. LS7X is a new prospective study, not reconstruction of the unavailable
local LS7W artifacts.

## Fixed input

Use exactly one product:
CH_PR300024_TG000301_TU2020-03-09T04-59-05_SCI_COR_Lightcurve-DEFAULT_V0300.fits

for file key CH_PR300024_TG000301_V0300, OBSID 1015522, 55 Cnc.

The metadata preflight fixed its identity before scoring:
- total bytes: 80,640
- ETag: "1678908399.9950867-80640-3403295943"
- table starts at byte 20,160
- table payload: 59,616 bytes
- 432 rows, 138 bytes/row, 18 columns
- PIPE_VER=14.1.2, EXT_VER=13.1
- NEXP=14, individual exposure 2.2000000477 s, total stacked exposure 30.8000011444 s
- DEFAULT aperture radius 25 pixels
- FLUX and FLUXERR are delivered in electrons.

Do not inspect another aperture to improve the primary outcome. R15–R40,
RINF and RSUP remain outside the primary pilot.

## Acquisition and eligibility

Request the public DACE lightcurves/default object by exact file-key equality.
Read only the already identified 59,616-byte BINTABLE payload. Require HTTP
206, exact Content-Range, unchanged total size and ETag, expected filename and
exact row-byte accounting. Preserve raw table bytes and receipt.

A row is usable only when BJD_TIME, FLUX and FLUXERR are finite, FLUXERR > 0
and STATUS == 0. For every assessed window, the complete local context,
including sidebands, guards and event rows, must satisfy that rule. Adjacent
BJD gaps throughout the context must be between 0.5 and 1.5 times the declared
30.8000011444-second stacked exposure. EVENT is not an exclusion rule; its
bitwise OR is recorded as a diagnostic.

## Fixed time scales and context

Assess d = 1, 2, 3 consecutive rows: 30.800001, 61.600002 and 92.400003 s.
For an event starting at row i, protect the d event rows, exclude a two-row
guard immediately before and after, and use exactly 12 rows before and 12
rows after the guards as sidebands.

Fit an unweighted straight line to the 24 sideband FLUX values versus seconds
relative to the event midpoint. No event value enters baseline/noise fitting.

Let sideband residuals be r and define:
sigma_MAD = 1.4826 * median(abs(r - median(r))).

The screening scale is max(sigma_MAD, median sideband FLUXERR,
1e-12*abs(median sideband FLUX), 1e-12 electrons).

For the event rows sum observed minus predicted flux. Include ordinary
least-squares prediction uncertainty with
L = x_sum^T (X^T X)^(-1) x_sum,
and score = event_excess_sum / (sigma * sqrt(d + L)).

This score is a local screening statistic, not a calibrated Gaussian
significance or false-alarm probability.

## Fixed primary rule

Positive screen: score >= 8.5.
Negative control: score <= -8.5.

Positive windows are clustered when event intervals overlap or are separated
by at most one row. Retain all members. Representative = highest score; ties
use shorter duration then earlier start. No threshold, sideband, guard,
duration or aperture changes after native scores are visible.

For each positive representative record EVENT, BACKGROUND, SMEARING_LC,
ROLL_ANGLE, contamination and centroid diagnostics. These do not veto the
primary screen. A screen is only a native L2 excursion until image/instrument
follow-up.

If positive clusters exist, a later stage may retrieve only corresponding
bounded SCI_CAL/SCI_COR subarray frames under a separately documented
follow-up. If none exist, report a single-visit pilot null. Do not infer an
occurrence-rate limit, physical laser-energy sensitivity or detector
qualification.

An independent auditor parses the saved 138-byte rows with struct, rebuilds
all eligible scores without importing the producer scoring implementation,
and checks continuous quantities and discrete screen/cluster decisions.
No outcome-driven repair is appended.
