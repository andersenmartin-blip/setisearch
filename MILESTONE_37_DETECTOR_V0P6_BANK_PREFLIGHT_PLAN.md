# Milestone 37 detector-v0.6 bank preflight

Status: **FROZEN METADATA-ONLY BANK DESIGN BEFORE DETECTOR IMPLEMENTATION OR
SPECTRAL CONTACT**.

This document freezes a cadence-specific circular-orbit template bank, a
discrete nuisance-carrier lattice, a redundant q-support guard, the mandatory
native-raw filtering coordinate, extraction
coverage, and fail-closed capacity arithmetic for HD 156668 b.  It does not
freeze the detector-v0.6 implementation, calibrate a threshold, inspect a
telescope sample, or authorize a held-out run.

## Why v0.6 is separate

The historical 21-template v0.5 bank is not a full phase/scale sensitivity
cover.  A first continuous calculation found that 89 line templates cover a
free additive carrier, but v0.5 does not implement that coordinate: it resets
the carrier at every scan and combines a fixed-center shift with a
template-dependent start mapping.  That semantic mismatch was caught before
rank-37 spectra were opened.

The prospective v0.6 contract is therefore direct and explicit.  For orbital
template `v`, nuisance carrier `q`, and integration midpoint `i`, it evaluates

`P_v_i(q) = q * F_v_i`.

The raw-row index is the nearest native channel to this frequency.  No carrier
is restarted between scans.  This path must later be implemented beside, not
inside, the frozen v0.5 detector.

## Truth domain and coefficient basis

All 96 midpoints from the six frozen ABABAB scans enter the proof.  For the
exact circular working orbit,

- `B_i = F_i(scale=0)`;
- `X_i = F_i(scale=1, phase=0) - B_i`;
- `Y_i = F_i(scale=1, phase=0.25) - B_i`;
- `F_u_i = B_i + x X_i + y Y_i`, where `x^2 + y^2 <= 1`.

The unit disk is the complete projected-scale `[0,1]`, all-phase domain.  The
five physical truth bands remain the same central `±500 kHz` bands used by the
survey.  Orbit-parameter uncertainties are not covered.

For physical carrier `f`, template `v`, and allowed center-track error `E`, a
proxy carrier is feasible exactly when it belongs to

`L = max_i((f F_u_i - E) / F_v_i)` through
`U = min_i((f F_u_i + E) / F_v_i)`.

The proof must contain an actual frozen lattice point, not merely a continuous
carrier.

## The 93-template bank

The bank direction in the circular coefficient disk is
`(-0.6558897197989564, 0.75485672512209)`, equivalent to phase
`0.3638531880461531` cycles.  For `m=-46,...,+46`,

`v_m = (2m/93) * direction`.

Canonical order is zero followed by `+1,-1,+2,-2,...,+46,-46`.  Its canonical
SHA-256 is
`8b0c5488944133db9bf500f7ed108971f42ef4d29ce36aa67f9a89ffac3a2d63`.

For each `m`, truth points assigned to that template occupy the unit-disk
strip between the adjacent line midpoints.  A linear functional on such a
strip reaches its extrema either at the unconstrained disk support point or at
one of the two strip boundaries.  The preflight evaluates those exact cases
for every ordered pair of the 96 times, both physical band endpoints, all 93
strips, and all five windows.  Each feasible-interval endpoint receives a
`0.01 Hz` outward guard.  That guard exceeds twice a frozen 4,096-operation
IEEE-754 forward-error envelope plus the measured circular-basis reconstruction
residual: the derived per-endpoint bound is `0.0015261962037544491 Hz`, and
twice that bound is below `0.01 Hz`.

The selected count is 93 because the production carrier is discrete and the
width budget below covers every time inside an integration.  Under the same
contract and guard, the 91-template bank has only
`1.4490267792554437 Hz` of guaranteed interval in the highest window, shorter
than one `2.835503418452676 Hz` lattice spacing; it also fails the 1418.5-MHz
window.  The 89-template bank fails all five windows.  For 93 templates, the
minimum guarded interval is `4.891987244442117 Hz`, exceeding one spacing by
`2.0564838259894405 Hz`.  This is a sufficient certificate for this fixed
uniform-line family and contract, not a claim of global optimality.

## Width and carrier support

The width bank remains `[1,3,5,9,17,33,65,129]`.  Sampling the two integration
endpoints gives a non-normative full-disk diagnostic of
`79.05702037789543 Hz`, but endpoints alone do not prove the interior.  The
normative bound instead differentiates
`F=(1+v_observer/c)(1-v_planet/c)` and applies the mean-value theorem over half
an integration.  The circular working orbit gives a maximum planet speed of
`117092.49980661187 m/s` and acceleration of
`1.8330011579451448 m/s^2`.  The observer velocity and acceleration bounds are
explicit frozen design assumptions of `50000 m/s` and `0.05 m/s^2`; they are
not measurements from the six headers.  They conservatively exceed simple
Earth-orbit-plus-terrestrial-rotation envelopes.  Together these values bound
the factor rate by `6.282100660979252e-09 s^-1` and the center-to-any-time
motion by `80.53452803677948 Hz` at the highest physical frequency.

A width-129 filter supplies a 64-bin radius.  Two conservative
nearest-channel composition channels are reserved.  The checker separately
proves that the center-track rounding bound is 34 channels and the
integration-motion rounding bound is 29 channels, totaling 63 and therefore
fitting inside the 64-channel radius.  The carrier lattice itself is proved
explicitly and consumes no hidden rounding allowance.  The remaining
center-track budget is

`(64 - 2) * 2.835503418452676 - 80.53452803677948`
`= 95.26668390728645 Hz`.

That 63-channel statement is a native-raw-channel bound.  Every frozen
template factor is slightly above one (`1.0000516645097706` through
`1.0000633684742861`), so nearest-channel mapping from the q lattice into a
raw spectrum is injective but not surjective.  Across all 44,640
window/scan/integration/template mappings, a full 747,793-bin q-support vector
skips between 38 and 48 raw channels.  A boxcar after q gathering could
therefore omit the exact truth channel even when its raw-index distance is at
most 63.

The spectral contract consequently requires each width boxcar on the native
observed-channel axis **before** direct q-track gathering.  A q-domain boxcar
is forbidden.  Under that order, the gathered raw-channel center and every
allowed truth/smear channel differ by at most 63, so width 129 includes them
inside its 64-channel native radius.  This preflight certifies that geometry;
the later implementation and completeness suite must still verify compliance
and recovery before any sensitivity claim.

The nuisance-carrier score grid is

`q[k] = window_center + k * 2.835503418452676 Hz`,
`-373832 <= k <= 373832`.

It contains 747,665 normative score bins.  Its extent slightly exceeds
`±1.060 MHz`: the physical `±500 kHz` truth interval plus a conservative
`560 kHz` recenter guard.  An extra 64 q bins on each side produce a
747,793-bin support grid.  This is a redundant extraction guard for the native
filter—not q-domain boxcar input—and it is cropped and never scored.  The
mapping diagnostic proves that each q guard supplies 64 or 65 native raw
channels, at least the required filter radius.

`q` is a nuisance coordinate, not automatically the signal's physical rest
frequency.  Candidate schemas must call it `proxy_carrier_mhz`, and the wider
grid must not be reported as a 2.12-MHz physical truth band.  Every widened
score cell nevertheless enters the observed maximum, empirical null, and
complete retention replay.

## Extraction result

The direct `q * F_v` support, including both redundant 64-bin q guards and an
additional explicit 64-native-channel boxcar radius, fits inside every already
frozen `±1.3 MHz` HDF5 extraction.  Across 30 scan-window checks, the minimum
proxy-support headroom is 52,707 native channels before the raw filter and
52,643 channels after it.  The minimum physical truth headroom is 56,831
channels at integration centers and 56,802 channels after the 29-channel
all-integration-time motion guard.  No wider extraction is required under this
direct v0.6 contract and its stated observer-motion assumptions.

These are geometry calculations from the six published headers.  No HDF5
`data` value or remote telescope object is accessed.

## Exact dimensions and fail-closed retention

There are 93 templates, four activity subsets, and eight widths: 2,976
hypotheses per window.  With 747,665 score bins, the primary dimensions are:

- `2,225,051,040` score cells per window;
- `11,125,255,200` score cells across five windows;
- `2,848,065,331,200` null score cells for 256 scrambles;
- `2,859,190,586,400` observed-plus-null score cells.

A fully materialized spectral bank would require 6,675,153,120 bytes per
ON/OFF kind per window.  The required architecture is template-at-a-time and
width-at-a-time.  The irreducible core arrays for one template are 23,180,687
bytes, before implementation scratch, under a prospective 512-MiB live-array
gate.  The exact-grid benchmark and actual peak-memory measurement remain
mandatory implementation gates.

After the final calibrated threshold is known, a second pass must retain every
finite unmasked cell with `score >= threshold`.  NMS and clustering are
report-only.  Every retained member gets its own OFF and receiver-frame
disposition.  More than 10,000 above-threshold records in any window, a file
or memory cap breach, or any incomplete shard is `M37_INVALID_NO_CONCLUSION`.
Threshold adaptation and truncation are forbidden.  The derived canonical
evidence ceiling is 89,967,424 bytes per window beneath the frozen 96-MB cap.

## Remaining gates before spectral access

1. Implement native-raw width filtering before direct q-track gathering,
   crop the redundant q-support guard, and add streaming masks, scrambles,
   retention, OFF track-distance tests, and completeness in new v0.6 modules
   while leaving v0.5 numerically unchanged.  Q-domain boxcars are forbidden.
2. Prove bitwise agreement with a fully materialized small reference and
   invariance to chunking, shard order, and ties.
3. Freeze seeds, scramble tables, OFF semantics in the nuisance coordinate,
   completeness witnesses, environment, benchmark, and atomic publication.
4. Publish and independently verify the full v0.6 preregistration.
5. Only then may the six rank-37 HDF5 spectral payloads be extracted or read.

Until every gate passes, this phase remains metadata-only and makes no M37
signal, null, sensitivity, occurrence, or population claim.
