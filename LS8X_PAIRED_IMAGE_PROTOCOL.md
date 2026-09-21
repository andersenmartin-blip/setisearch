# LS8X — exact GJ 436 image payload and unchanged diagnostic

21 September 2026. **FROZEN BEFORE ANY LS8X IMAGE OR SMEARING VALUES**.
Metadata freeze: `62add7db6a5d6b244825f7f13d4e465935668985`.
Metadata result: `40cf5b1ad94d8397f3884bf790d0dd0dda4d3a7d`.
Audited L2 source: `6038a0dfac58d9c74a6f88ce3afafda8eeffa1bf`.

The independent metadata audit passes **58 unique exposure joins and 269 exact
checks**, with zero image bytes. All 57 metadata-manifest files and the exact
future-image config have been retrieved and byte-verified. This diagnostic
includes the complete signed representative set: **TG000302_P0**, positive,
L2 row 33, one 60-second exposure, original score +9.634235209975396.
The second selected visit and both negative cluster sets are empty. The
score is not Gaussian sigma, and this is not a qualified SETI candidate.

## Exact source identities and byte intervals

Use only CH_PR100041_TG000302_V0300 CAL/COR products. Exact filenames, total
sizes, ETags, metadata identities and native row matches are retained in
`config/ls8x_images.json`. Image arrays are unscaled big-endian float64,
200x200 native ADU, 320,000 bytes per frame, 340 frames, data start 17,280
and detector offsets (564,196). These were checked separately for CAL/COR.
NEXP=1 and EXPTIME=TEXPTIME=60 seconds agree with L2, PIPE_VER=14.1.2.

| Product | Context image rows [start,stop) | Start byte | Count | Last byte inclusive |
|---|---|---:|---:|---:|
| SCI_CAL_SubArray | 19:48 | 6097280 | 9280000 | 15377279 |
| SCI_COR_SubArray | 19:48 | 6097280 | 9280000 | 15377279 |
| SCI_COR_SmearingRow | 19:48 | 108986560 | 46400 | 109032959 |

Acquire exactly **18,560,000 paired-image bytes plus 46,400 smearing bytes**.
The row indices coincide with L2 only after the successful unique metadata
joins. Every smearing row contains 200 float64 values. Pin source config,
representatives, full metadata/L2 manifests, metadata audit, mathematical
source, independent audit and inherited tests in `config/ls8x_payload_scope.json`.
Verify all pins, freeze HEAD and a clean tracked tree before access.

Require HTTP 206, exact range/length/total size, ETag and filename. The
unchanged image fetch permits at most three identical-range attempts for
transport failures; identity/contract assertions stop immediately. Preserve
successful receipts, raw/compressed hashes, failures and partial results.
The tested URL helper permits at most three resolution calls after timeout,
with the original 45-second timeout and five-second spacing, recording every
attempt without temporary URLs. No alternate endpoint, product, frame,
aperture, visit or raw imagette is authorized. Existing verified range bytes
may be reused offline; completed diagnostics must not be overwritten.

## Unchanged pixel calculation and gate order

Use the unchanged pinned `cheops_image_pair.py`. Fit median-centered local
linear pixel baselines to 12 sideband rows each side, leaving two guards each
side. The original event is local row 14 in the 29-row context. The common
finite CAL/COR mask uses sideband and event rows; guards enter neither mask
nor fit. Retain CAL, COR and DELTA=COR-CAL event maps, analogous smearing
maps, common-mask column projections and the original r>35 smearing regression.

C0 is the mean saved sideband centroid minus the verified detector offsets;
C1 subtracts one from each C0 coordinate. Retain both r<=25 apertures and
30<r<=40 background annuli. Fit unchanged unweighted brightness+constant,
x/y displacement gradients+constant and combined models. Do not move centers,
mask pixels, change templates, weight residuals or choose a convention from
its outcome. No earlier hypothetical correction becomes a veto.

Both conventions require complete apertures, valid COR denominators and
COR signs matching the original positive selection. Apply the existing order:

1. **CORRECTION_LINKED** if both conventions have |DELTA/COR| or
   |column-DELTA/COR| >=0.5.
2. Otherwise **SPATIALLY_STRUCTURED** if both have available fits,
   displacement explained energy >=0.8 and advantage over brightness >=0.2.
3. Otherwise **UNRESOLVED_WITHIN_FIXED_SCOPE**, preserving unavailable fits.

Labels describe processing coupling or morphology; none identifies a unique
physical cause or excludes source variability. An unresolved result is not
evidence of artificial origin or an adopted detection rule.

## Verification, reporting and stopping

All **nine inherited synthetic image tests** must pass in the full workflow
checkout before values. They cover original image mathematics, signed
one/three-row sums, guard exclusion and brightness preservation. The two
mixed-duration tests passed locally; the seven-test module could not load
locally because the partial working copy lacked its historical audit import.
That environment limitation does not waive the full nine-test gate.

The independent event-map, regression, column-projection and rebuild functions
are AST-identical to LS8T. Independently decode floats, recheck source receipts
and joins, reconstruct maps with long-double equations and spatial fits with
scalar normal equations. Keep relative tolerance 2e-8, native absolute 1e-6
and dimensionless absolute 1e-8; masks, membership, counts and labels are exact.
Preserve any failed audit without tolerance relaxation or scientific reruns.

Publish all exact ranges, data, receipts, maps, diagnostics, independent
reference/audit, transport logs, environment and checksums. The CAL/COR/DELTA
figure uses one common symmetric native-unit scale and both aperture outlines;
visually inspect it before interpretation. Stop after this one original event.
If it closes under the fixed gates, close the GJ 436 pair and prepare rank-7
PG 1245-042 with new header and table freezes. If unresolved, specify its
remaining limitation before a separate retained-data study. Do not acquire
additional pixels or visits to force closure. Prior unresolved events and
closed studies remain unchanged; reserved TESS/M43 data remain closed,
calibration is NOT_READY and its request unsent. Publication is authorized.
