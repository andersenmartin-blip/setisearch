# Continue after LS8C

The frozen retrospective auxiliary study is complete for all eight original
LS8B representatives. Six synthetic tests and an independent 60-decimal audit
pass: **11,635 numerical comparisons and 1,009 exact checks**. All 112 field
diagnoses and 56 sideband-only couplings are retained. No new archive science
bytes, image pixels, apertures, representatives or visits were opened.

## What the diagnosis establishes

All seven positive representatives coincide with large positive smearing
residuals, **205,662–293,495 electrons** in the delivered SMEARING_LC units,
against local side MADs of 344–459 electrons. Their mean event roll angles
are **16.39–20.42 degrees**. The negative control has a smearing residual of
−24,225 electrons against a 47,409-electron side MAD, at mean roll 83.86 degrees.
The positive backgrounds also all depart downward from their local trends.

This common auxiliary pattern is a concrete reason to examine the delivered
image correction and spatial structure. The L2 columns alone do not establish
the DRP operator, common aperture/pixel normalization, a unique instrumental
cause or an astrophysical/artificial origin. Sideband smearing fits extrapolate
between −0.42 and 31.78 times the positive FLUX residuals, so they supply no
reliable event correction. The report gives every predictor and both signs.

Every representative remains **L2_ONLY_UNRESOLVED**. Do not convert the observed
roll interval or smearing amplitude into a retrospective veto or new screen.
The large MAD displacements are not Gaussian significances. The single
negative representative is a diagnostic control, not a null-rate estimate.
The original LS8B audit remains **FAIL**, including its original two failed
near-zero comparisons. The separately validated arithmetic repair stays intact.

## Next integrated study

Prepare one bounded CAL/COR image-and-correction comparison for **all eight**
fixed representatives, including the negative control. Begin with metadata
and exposure-time joins only. Identify exact native CAL/COR products and
versions for TG000302, TG000303 and TG000304, preserving the DEFAULT-L2
association. TG000305 has no representative and needs no image study here.

Retain these L2 contexts as the requested exposure joins:

| Visit | Sign / cluster | Start / duration | Context rows, half-open |
|---|---|---|---|
| TG000302 | positive 0 | 217 / 2 | [203, 233) |
| TG000302 | positive 1 | 517 / 3 | [503, 534) |
| TG000302 | positive 2 | 1064 / 2 | [1050, 1080) |
| TG000302 | negative 0 | 738 / 1 | [724, 753) |
| TG000303 | positive 0 | 444 / 3 | [430, 461) |
| TG000303 | positive 1 | 681 / 3 | [667, 698) |
| TG000304 | positive 0 | 274 / 2 | [260, 290) |
| TG000304 | positive 1 | 434 / 1 | [420, 449) |

These are 241 L2 context rows: 192 sideband, 32 guard and 17 event rows.
Do not assume L2 row numbers equal native image-plane numbers. Establish
unique exposure joins using the delivered metadata and matching integration
semantics; any ambiguous or missing mapping stays explicitly unavailable.
The intended target SOC location is (280,828) in these L2 contexts, but image
origin, axis order and pixel-coordinate conversion require native metadata.

Before reading any image payload, publish exact file/ETag identities, HDUs,
row joins, byte ranges, fixed pixel regions, models and stopping criteria.
Use the existing LS7Y/LS7Z comparisons as methodological precedents, preserving
their closed outcomes. The new study should compare CAL and COR event-minus-
sideband maps and the CAL→COR change, with predeclared brightness and spatial
motion/correction diagnostics. Fit spatial reference templates on sidebands
only. Retain the same models and accounting for both signs and all eight
representatives; no event-driven aperture, row widening or peak replacement.

Package acquisition, paired image analysis, independent audit and readable
results as one useful study after the metadata/scope freeze. Freeze evidence
needed to close a correction-linked or spatially structured branch, and a
stop-with-unresolved outcome when the bounded information is insufficient.
Do not extend to more visits or alternative apertures to improve the outcome.
Image acquisition is outside the completed LS8C scope; this is the next
analysis to prepare under the existing standing project authorization.

The separate raw-imagette study still requires its missing physical operator
and reference contract. It remains NOT_READY; its technical request is unsent
and no reply is pending. LS7X/Y/Z's two earlier branches stay closed. Unused
TESS and M43 panels remain closed. No detector qualification, candidate or
qualified observing coverage is added by LS8C.

[Report and all plots](results_ls8c_auxiliary/REPORT.md),
[frozen protocol](LS8C_AUXILIARY_PROTOCOL.md),
[input and representative manifest](config/ls8c_auxiliary.json).
