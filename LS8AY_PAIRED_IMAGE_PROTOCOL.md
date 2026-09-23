# LS8AY — exact GJ 536 paired-image payload and unchanged diagnostic

23 September 2026. **FROZEN BEFORE IMAGE OR SMEARING VALUES**.
Metadata freeze: `4c34714c0eb4e14bc3041514811f1746eda0ee87`.
Metadata result: `6fd13368ec9b08a05aa5ec69500fc0877a0359f1`.
Audited L2 result: `a5e343f7b5b6fee73514f2d06bda8e2b64feb85b`.

The independent metadata audit passes **522 unique exposure joins and 2,393
exact checks**, with zero pixels read. All 104 metadata-manifest entries and
all 106 result files, including the future-image config, match local SHA256
and public Git identities. All nine original signed representatives are retained:

| Representative | L2 row, zero-based | Duration | Original L2 score | L2 excess / local baseline |
|---|---:|---|---:|---:|
| TG023501_P0 | 1816 | 40.169998 s | +18.968233631134 | +0.576269% |
| TG023501_P1 | 1849 | 40.169998 s | +9.877824201574 | +0.226988% |
| TG023501_P2 | 2573 | 40.169998 s | +13.572894443593 | +0.384290% |
| TG023501_P3 | 2770 | 40.169998 s | +31.864099484625 | +0.759873% |
| TG023501_P4 | 3082 | 40.169998 s | +20.039903364472 | +0.462369% |
| TG023501_P5 | 3323 | 40.169998 s | +15.723832564690 | +0.361474% |
| TG023501_P6 | 3408 | 40.169998 s | +2923.687794814557 | +69.592873% |
| TG023501_N0 | 802 | 40.169998 s | -14.861686433842 | -0.387849% |
| TG007801_P0 | 17 | 40.200001 s | +47.629871839031 | +1.104699% |

There are eight positive and one negative representatives. All are one
exposure, with NEXP=1; the first eight use 40.1699981689453 seconds and
TG007801_P0 uses 40.2000007629395 seconds. Display durations above are rounded;
all arithmetic uses actual retained BJD times. Their original nine contexts
are disjoint within each visit and contain 261 rows. Scores are not Gaussian
significances. No extra comparison or excluded point is selected.

## Source identities and exact ranges

config/ls8ay_images.json retains filenames, ETags, total sizes, metadata
identities and unique joins for both visits. Image arrays are unscaled
big-endian float64, 200x200 native ADU, 320,000 bytes per frame. Exposure
fields and pipeline match each own L2 header independently for CAL and COR.

| Exact visit | Product | Frames | Image first byte | Detector offsets | Unit |
|---|---|---:|---:|---|---|
| CH_PR100011_TG023501_V0300 | SCI_CAL_SubArray | 4133 | 17280 | (157, 759) | ADU |
| CH_PR100011_TG023501_V0300 | SCI_COR_SubArray | 4133 | 17280 | (157, 759) | ADU |
| CH_PR100018_TG007801_V0300 | SCI_CAL_SubArray | 121 | 17280 | (157, 759) | ADU |
| CH_PR100018_TG007801_V0300 | SCI_COR_SubArray | 121 | 17280 | (157, 759) | ADU |

| Representative | Product | First byte | Count | Last byte inclusive |
|---|---|---:|---:|---:|
| TG023501_P0 | SCI_CAL_SubArray | 576657280 | 9280000 | 585937279 |
| TG023501_P0 | SCI_COR_SubArray | 576657280 | 9280000 | 585937279 |
| TG023501_P0 | SMEAR | 1326744320 | 46400 | 1326790719 |
| TG023501_P1 | SCI_CAL_SubArray | 587217280 | 9280000 | 596497279 |
| TG023501_P1 | SCI_COR_SubArray | 587217280 | 9280000 | 596497279 |
| TG023501_P1 | SMEAR | 1326797120 | 46400 | 1326843519 |
| TG023501_P2 | SCI_CAL_SubArray | 818897280 | 9280000 | 828177279 |
| TG023501_P2 | SCI_COR_SubArray | 818897280 | 9280000 | 828177279 |
| TG023501_P2 | SMEAR | 1327955520 | 46400 | 1328001919 |
| TG023501_P3 | SCI_CAL_SubArray | 881937280 | 9280000 | 891217279 |
| TG023501_P3 | SCI_COR_SubArray | 881937280 | 9280000 | 891217279 |
| TG023501_P3 | SMEAR | 1328270720 | 46400 | 1328317119 |
| TG023501_P4 | SCI_CAL_SubArray | 981777280 | 9280000 | 991057279 |
| TG023501_P4 | SCI_COR_SubArray | 981777280 | 9280000 | 991057279 |
| TG023501_P4 | SMEAR | 1328769920 | 46400 | 1328816319 |
| TG023501_P5 | SCI_CAL_SubArray | 1058897280 | 9280000 | 1068177279 |
| TG023501_P5 | SCI_COR_SubArray | 1058897280 | 9280000 | 1068177279 |
| TG023501_P5 | SMEAR | 1329155520 | 46400 | 1329201919 |
| TG023501_P6 | SCI_CAL_SubArray | 1086097280 | 9280000 | 1095377279 |
| TG023501_P6 | SCI_COR_SubArray | 1086097280 | 9280000 | 1095377279 |
| TG023501_P6 | SMEAR | 1329291520 | 46400 | 1329337919 |
| TG023501_N0 | SCI_CAL_SubArray | 252177280 | 9280000 | 261457279 |
| TG023501_N0 | SCI_COR_SubArray | 252177280 | 9280000 | 261457279 |
| TG023501_N0 | SMEAR | 1325121920 | 46400 | 1325168319 |
| TG007801_P0 | SCI_CAL_SubArray | 977280 | 9280000 | 10257279 |
| TG007801_P0 | SCI_COR_SubArray | 977280 | 9280000 | 10257279 |
| TG007801_P0 | SMEAR | 38815680 | 46400 | 38862079 |

Acquire exactly **167,040,000 paired-image bytes and 417,600 smearing bytes**,
27 ranges determined by unique joins. The separate payload scope pins the
config, representatives, metadata/L2 manifests, audits, unchanged mathematics
and tests. Verify all 31 pins, public freeze HEAD and clean tracked tree
before acquisition. The sparse checkout includes every pinned input and
output path; result preservation requires checkout success.

Keep HTTP 206, exact range/length/total, ETag and filename. Image fetch retains
at most three identical-range transport attempts and the 90-second timeout;
identity/contract assertions stop immediately. Preserve successful receipts,
raw/compressed hashes, failures and partial outcomes. URL resolution retains
the tested timeout-only three-attempt helper, 45 seconds per call and five-second
spacing. No alternate endpoint, product, frame, visit, aperture or raw imagette.
Verified ranges may be reused offline; completed diagnostics cannot be overwritten.

## Unchanged mathematics and gates

Use hash-pinned cheops_image_pair.py unchanged. Median-center and linearly
fit each pixel on the original 12-row sidebands, excluding two guards per
side. Event rows are local [14,15); contexts have 29 rows. Common finite
CAL/COR masks use sidebands and event rows, excluding guards. Keep CAL/COR/
DELTA=COR-CAL maps, analogous smearing maps, column projections and r>35
smearing regression. All temporal residuals are native event sums.

C0 uses the saved sideband mean centroid minus verified offsets; C1 shifts
both coordinates by -1. Keep r<=25 apertures, 30<r<=40 annuli and unweighted
brightness+constant, displacement-gradients+constant and combined fits.
No recentering, new mask, weighting, subtraction or cut.

Both conventions require complete apertures, nonzero COR denominators and
COR agreement with the representative's original positive or negative sign.
Keep the order:

1. CORRECTION_LINKED when both conventions have |DELTA/COR| or
   |column-DELTA/COR| >=0.5.
2. Otherwise SPATIALLY_STRUCTURED when displacement explained energy>=0.8
   and advantage>=0.2 over brightness in both, with available fits.
3. Otherwise UNRESOLVED_WITHIN_FIXED_SCOPE; unavailable fits stay unavailable.

Labels describe delivered processing or morphology, not unique physical cause
or artificial origin. No new screen or correction is adopted.

## Verification and stopping

All 11 inherited image known-answer tests must pass in the workflow before
pixels. These protect signed one/two/three-row sums, guards, masks, brightness
preservation and both coordinate conventions. Four duration tests already pass
locally; the full 11-test pre-pixel gate remains mandatory. Scientific functions
and classification gates are unchanged.

Independent event_map, regression, columns_projection and rebuild are
AST-identical to LS8AR. Independently struct-decode retained bytes, check
raw/compressed hashes and metadata joins, reconstruct temporal maps with
long-double equations and spatial fits with scalar normal equations. Keep
relative 2e-8, native absolute 1e-6, dimensionless absolute 1e-8 tolerances and
exact masks, membership, counts and labels. Preserve any failure.

Publish all inputs, receipts, maps, diagnostics, independent reference/audit,
environment, logs and checksums. Inspect every common-scale CAL/COR/DELTA
figure before interpretation. Stop at these nine representatives. If all
close, close the GJ 536 pair and prepare rank-21 2MASS J11285624+1010395
under new header/table freezes. If any remain unresolved, state the limitation
before at most one separately frozen retained-data study. No new pixels or
visits to force closure. The three other eligible GJ 536 visits stay outside
the pair. Earlier labels, unassessed points, closed studies and reserved
TESS/M43 panels stay unchanged. No candidate, detector, sensitivity, significance
or observing coverage is qualified. Calibration NOT_READY; request UNSENT.
Publication authorized; delegation deferred.
