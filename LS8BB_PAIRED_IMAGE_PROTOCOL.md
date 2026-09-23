# LS8BB — exact paired-image diagnostic for both signed 2MASS events

23 September 2026. **FROZEN BEFORE IMAGE AND SMEARING PAYLOAD ACCESS**.
L2 result: `f2fd067eec26e3d3b3002e14c3c2e616f8433675`.
Metadata freeze: `e675b980d999baf062ceb73eea088058f7169141`.
Metadata result: `e9389d961e98879e8203f26daf18aebece352b48`.

Both metadata and independent joins pass: **534 exact checks**, 116
context-specific unique matches, zero image bytes. The 58 context-row
occurrences cover 30 distinct L2 rows and 60 distinct CAL/COR exposures.
Both original signed events must be followed; the second original L2 visit
has zero eligible windows and no image follow-up is selected for it.

## Exact scope and overlap

Both contexts are in CH_PR100018_TG010801_V0300. CAL/COR each have 59 frames,
unscaled float64 200x200 ADU images, frame size 320,000 bytes, detector offsets
(157,759), first image data byte 17,280. NEXP=1, EXPTIME=TEXPTIME=60 seconds
and pipeline 14.1.2 agree with the own L2 header. Retain exact ETags, filenames,
total sizes and layouts in config/ls8bb_images.json. No row-index equality
was presumed when establishing the exposure joins.

| Context | Event row | Context rows [start,stop) | CAL and COR start, each | Bytes per CAL/COR range | Smearing start | Smearing bytes |
|---|---:|---|---:|---:|---:|---:|
| TG010801_P0 | 25 | 11:40 | 3537280 | 9280000 | 18968000 | 46400 |
| TG010801_N0 | 24 | 10:39 | 3217280 | 9280000 | 18966400 | 46400 |

Acquire exactly **37,120,000 CAL/COR bytes and 92,800 smearing bytes**, in six
fixed ranges. The two contexts overlap in 28 rows. Their union contains only
19,200,000 distinct image bytes and 48,000 distinct smearing bytes; repeated
ranges are preserved for the original separate contexts, not counted as
independent data or additional coverage. Verify overlap consistency on the
retained bytes. Neither adjacent event enters the other's baseline: it lies
in the original guard region. Do not merge or alter either context.

Require public freeze HEAD, clean tracked checkout, all 33 pinned inputs and
the complete metadata manifest before access. HTTP 206, exact range/length/
total, matching If-Match ETag and exact filename are mandatory. Preserve raw
and compressed SHA256, receipts, attempted transports, source identities and
partial failures. Reuse unchanged acquisition: up to three identical range
attempts for OSError/TimeoutError, never retry identity or contract assertions.
URL resolution has its separately bounded timeout-only policy. No other
pixels, apertures, raw imagettes or visits are authorized.

## Unchanged diagnostic and independent audit

Run all 11 inherited image known-answer tests before pixels. Use the unchanged
hash-pinned image core and prospectively frozen independent auditor.
The independent event_map, regression, columns_projection and rebuild remain
AST-identical to LS8AY. Native event sums use retained BJD times, 12-row
sidebands and two guard rows per side; the common finite mask uses event and
sideband pixels. Source centers come only from the saved sideband centroids.
Preserve C0/C1 conventions, r<=25 apertures, 30<r<=40 background annuli,
column projection and r>35 smearing regression. Missing/rank-deficient fits
remain unavailable; no new mask, center, template or subtraction is selected.

Gate order remains fixed. Require complete apertures and original COR/L2
sign agreement in both conventions. First, CORRECTION_LINKED if absolute
DELTA/COR or column-DELTA/COR >=0.5 in both conventions. Otherwise,
SPATIALLY_STRUCTURED requires displacement explained energy >=0.8 and an
advantage over brightness >=0.2 in both. All others remain
UNRESOLVED_WITHIN_FIXED_SCOPE. These labels identify neither unique physical
causes nor astrophysical/artificial origin.

Independent struct decoding, long-double temporal equations and scalar spatial
normal equations reconstruct every context, map, fit and classification.
Retain exact discrete comparisons and relative 2e-8, native absolute 1e-6
and dimensionless absolute 1e-8 tolerances. Any failure stops promotion and
is retained; do not relax thresholds or rerun native science to seek a pass.
Publish both common-scale CAL/COR/DELTA figures and inspect both.

## Preservation, transport and stopping

Publish all raw ranges, arrays, diagnostics, audits, reports, figures, logs,
environment, freeze identity and checksums to the existing scientific branch.
Use the existing sparse checkout and successful-checkout preservation guard.
The terminal Git refresh was unavailable in this turn, so connector retrieval
is used for local verification. Prospectively include an optional seven-day
GitHub Actions artifact containing only the same retained results directory,
using upload-artifact v4 with compression level 0. This transport copy changes
no scientific input or result. Git remains the durable publication. Artifact
failure does not repeat native calculations or relax the scientific success
gate; independently checksum any downloaded copy.

After both signed outcomes, close the pair if both receive descriptive closure
labels. Then prepare **LS8BC, rank-22 GJ 422**, chronological pair
CH_PR100018_TG012201_V0300 / CH_PR100018_TG012202_V0300, under separate header
and L2 freezes. If any label is unresolved, state its specific limitation
before at most one separately frozen study of the complete unresolved set
using retained data only. No wider acquisition to force closure.

Original L2 rules and prior labels/studies remain unchanged. A zero-eligible
visit supplies no tested null; overlapping contexts supply no independent
replication. No detector, candidate, probability, sensitivity or qualified
observing coverage is claimed. Reserved TESS/M43 panels stay closed.
Calibration NOT_READY; request UNSENT. Standing publication authorization
continues; delegation is deferred.
