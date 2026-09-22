# LS8AR — exact GJ 581 paired-image payload and unchanged diagnostic

22 September 2026. **FROZEN BEFORE IMAGE OR SMEARING VALUES**.
Metadata freeze: a29525dfa1096cbca008db37e732a85b60f81a8e.
Metadata result: ffb7201ddabebe017240afa2053bd34729dfdeed.
Audited L2 result: 051d973dffe52f151f3948e38070b40bbc32cdf4.

The independent metadata audit passes 814 unique exposure joins and
3723 exact checks with zero pixels. All 57 metadata manifest
entries and the future-image config were locally byte verified. All 14 signed
representatives from LS8AR_INPUT_SCOPE.md are included, with no substitutions:

| Representative | L2 row, zero-based | Duration | Original L2 score | L2 excess / local baseline |
|---|---:|---|---:|---:|
| TG023701_P0 | 1070 | 60 s | +10.117099458039316 | +0.248385% |
| TG023701_P1 | 2033 | 60 s | +11.029749181602263 | +0.352781% |
| TG023701_P2 | 2209 | 60 s | +15.415871544973099 | +0.653250% |
| TG023701_P3 | 2528 | 60 s | +61.514729501873468 | +1.502999% |
| TG023701_P4 | 2581 | 60 s | +15.370472148046623 | +0.534193% |
| TG023701_P5 | 2761 | 60 s | +29.757440687203143 | +1.089442% |
| TG023701_P6 | 2833 | 60 s | +9.187940675968894 | +0.224409% |
| TG023701_P7 | 3044 | 60 s | +11.554082508851558 | +0.282332% |
| TG023701_P8 | 3133 | 60 s | +59.493137161459714 | +1.504279% |
| TG023701_N0 | 975 | 60 s | -17.154258654577312 | -0.433973% |
| TG023701_N1 | 1511 | 120 s | -10.622953693161483 | -0.187652% |
| TG023701_N2 | 1587 | 60 s | -9.189141427759484 | -0.224489% |
| TG023701_N3 | 2679 | 60 s | -21.763188969336206 | -0.532478% |
| TG023701_N4 | 3264 | 60 s | -8.693767275408362 | -0.212390% |

All are in the first visit CH_PR100011_TG023701_V0300: nine positive and
five negative. Thirteen events are one 60-second exposure; N1 sums two
exposures over 120 seconds. The 14 original contexts are disjoint, 407 rows
total. Scores are not Gaussian sigma. No extra comparison is selected.

## Source identities and exact ranges

Use only the first visit's CAL/COR products. config/ls8ar_images.json retains
exact filenames, ETags, total sizes, metadata identities and unique joins.
Both image arrays are unscaled big-endian float64, 200x200 native ADU,
320,000 bytes per frame. NEXP=1, EXPTIME=TEXPTIME=60 s and PIPE_VER=14.1.2
match L2 independently for both products.

| Exact visit | Product | Frames | Image first byte | Detector offsets | Unit |
|---|---|---:|---:|---|---|
| CH_PR100011_TG023701_V0300 | SCI_CAL_SubArray | 3545 | 17280 | (157, 759) | ADU |
| CH_PR100011_TG023701_V0300 | SCI_COR_SubArray | 3545 | 17280 | (157, 759) | ADU |

| Representative | Product | First byte | Count | Last byte inclusive |
|---|---|---:|---:|---:|
| TG023701_P0 | SCI_CAL_SubArray | 337937280 | 9280000 | 347217279 |
| TG023701_P0 | SCI_COR_SubArray | 337937280 | 9280000 | 347217279 |
| TG023701_P0 | SMEAR | 1137213120 | 46400 | 1137259519 |
| TG023701_P1 | SCI_CAL_SubArray | 646097280 | 9280000 | 655377279 |
| TG023701_P1 | SCI_COR_SubArray | 646097280 | 9280000 | 655377279 |
| TG023701_P1 | SMEAR | 1138753920 | 46400 | 1138800319 |
| TG023701_P2 | SCI_CAL_SubArray | 702417280 | 9280000 | 711697279 |
| TG023701_P2 | SCI_COR_SubArray | 702417280 | 9280000 | 711697279 |
| TG023701_P2 | SMEAR | 1139035520 | 46400 | 1139081919 |
| TG023701_P3 | SCI_CAL_SubArray | 804497280 | 9280000 | 813777279 |
| TG023701_P3 | SCI_COR_SubArray | 804497280 | 9280000 | 813777279 |
| TG023701_P3 | SMEAR | 1139545920 | 46400 | 1139592319 |
| TG023701_P4 | SCI_CAL_SubArray | 821457280 | 9280000 | 830737279 |
| TG023701_P4 | SCI_COR_SubArray | 821457280 | 9280000 | 830737279 |
| TG023701_P4 | SMEAR | 1139630720 | 46400 | 1139677119 |
| TG023701_P5 | SCI_CAL_SubArray | 879057280 | 9280000 | 888337279 |
| TG023701_P5 | SCI_COR_SubArray | 879057280 | 9280000 | 888337279 |
| TG023701_P5 | SMEAR | 1139918720 | 46400 | 1139965119 |
| TG023701_P6 | SCI_CAL_SubArray | 902097280 | 9280000 | 911377279 |
| TG023701_P6 | SCI_COR_SubArray | 902097280 | 9280000 | 911377279 |
| TG023701_P6 | SMEAR | 1140033920 | 46400 | 1140080319 |
| TG023701_P7 | SCI_CAL_SubArray | 969617280 | 9280000 | 978897279 |
| TG023701_P7 | SCI_COR_SubArray | 969617280 | 9280000 | 978897279 |
| TG023701_P7 | SMEAR | 1140371520 | 46400 | 1140417919 |
| TG023701_P8 | SCI_CAL_SubArray | 998097280 | 9280000 | 1007377279 |
| TG023701_P8 | SCI_COR_SubArray | 998097280 | 9280000 | 1007377279 |
| TG023701_P8 | SMEAR | 1140513920 | 46400 | 1140560319 |
| TG023701_N0 | SCI_CAL_SubArray | 307537280 | 9280000 | 316817279 |
| TG023701_N0 | SCI_COR_SubArray | 307537280 | 9280000 | 316817279 |
| TG023701_N0 | SMEAR | 1137061120 | 46400 | 1137107519 |
| TG023701_N1 | SCI_CAL_SubArray | 479057280 | 9600000 | 488657279 |
| TG023701_N1 | SCI_COR_SubArray | 479057280 | 9600000 | 488657279 |
| TG023701_N1 | SMEAR | 1137918720 | 48000 | 1137966719 |
| TG023701_N2 | SCI_CAL_SubArray | 503377280 | 9280000 | 512657279 |
| TG023701_N2 | SCI_COR_SubArray | 503377280 | 9280000 | 512657279 |
| TG023701_N2 | SMEAR | 1138040320 | 46400 | 1138086719 |
| TG023701_N3 | SCI_CAL_SubArray | 852817280 | 9280000 | 862097279 |
| TG023701_N3 | SCI_COR_SubArray | 852817280 | 9280000 | 862097279 |
| TG023701_N3 | SMEAR | 1139787520 | 46400 | 1139833919 |
| TG023701_N4 | SCI_CAL_SubArray | 1040017280 | 9280000 | 1049297279 |
| TG023701_N4 | SCI_COR_SubArray | 1040017280 | 9280000 | 1049297279 |
| TG023701_N4 | SMEAR | 1140723520 | 46400 | 1140769919 |

Acquire exactly **260,480,000 paired-image bytes and 651,200 smearing bytes**,
42 ranges determined by unique joins, not assumed indices. The separate
payload scope pins config, representatives, metadata/L2 manifests, audits,
unchanged mathematics and tests. Verify all pins, public freeze HEAD and
clean tracked tree before acquisition.

Retain HTTP 206, exact range/length/total, ETag and filename. Image fetch
keeps at most three identical-range transport attempts and the 90-second
timeout; identity/contract assertions stop immediately. Preserve successful
receipts, raw/compressed hashes, failures and partial outcomes. URL resolution
retains the tested timeout-only three-attempt helper with 45-second timeout
and five-second spacing. No alternate endpoint, product, frame, visit,
aperture or raw imagette. Verified ranges may be reused offline; completed
diagnostics cannot be overwritten.

## Unchanged mathematics and gates

Use hash-pinned cheops_image_pair.py unchanged. Median-center and linearly
fit each pixel on the original 12-row sidebands, excluding two guards on
each side. Event rows are local [14,14+d), d=1 or 2; contexts have 28+d rows.
Common finite CAL/COR masks use sidebands and event rows, excluding guards.
Keep CAL/COR/DELTA=COR-CAL maps, analogous smearing maps, column projections
and r>35 smearing regression. All temporal residuals are native event sums.

C0 uses the saved sideband mean centroid minus verified offsets; C1 shifts
both coordinates by -1. Retain r<=25 apertures, 30<r<=40 annuli and unweighted
brightness+constant, displacement-gradients+constant and combined fits.
No recentering, new mask, weights, subtraction or cut.

Both conventions require complete apertures, nonzero COR denominators and
COR agreement with the representative's original positive or negative sign.
Keep the order:

1. CORRECTION_LINKED when both conventions have |DELTA/COR| or
   |column-DELTA/COR| >=0.5.
2. Otherwise SPATIALLY_STRUCTURED when displacement explained energy>=0.8
   and advantage>=0.2 over brightness in both conventions, with available fits.
3. Otherwise UNRESOLVED_WITHIN_FIXED_SCOPE; unavailable fits stay unavailable.

Labels describe delivered processing or morphology, not unique physical cause
or artificial origin. No new screen or correction is adopted.

## Verification and stopping

All nine inherited synthetic tests and two additional two-row known answers
at native 60-second cadence must pass in the full workflow before pixels.
These protect signed sums, guard exclusion and brightness preservation in
both conventions; no scientific function changes. The local partial checkout
lacks the historical test audit module, so only the four duration tests ran
locally; full 11-test validation is a mandatory pre-pixel workflow gate.

The independent event_map, regression, columns_projection and rebuild
functions remain AST-identical to LS8AP/LS8T. Independently struct-decode
retained bytes, check raw/compressed hashes and metadata joins, reconstruct
temporal maps with long-double equations and spatial fits with scalar normal
equations. Retain relative 2e-8, native absolute 1e-6 and dimensionless absolute
1e-8 tolerances and exact masks/membership/counts/labels. Preserve failures.

Publish all inputs, receipts, maps, diagnostics, audit/reference, environment,
logs and checksums. Inspect all 14 common-scale CAL/COR/DELTA figures before
interpretation. Stop at the original representatives. If all close, close this
GJ 581 pair and prepare rank-16 EC14599-2047 with header/table freezes. If any
remain unresolved, state the limitation before at most one separately frozen
retained-data study. No new pixels or visits to force closure. Five other
eligible GJ 581 visits stay outside this pair. Closed WASP-103 and HD 106315,
other prior studies and reserved TESS/M43 panels remain unchanged. No detector,
candidate, significance, sensitivity or coverage is qualified. Calibration
NOT_READY; request UNSENT. Publication authorized; delegation deferred.
