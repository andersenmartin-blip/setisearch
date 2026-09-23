# LS8AX–LS8AZ publication and verification — 23 September 2026

The rank-20 GJ 536 pair and its one bounded residual study are complete and
closed. All nine original image labels remain: three CORRECTION_LINKED,
four SPATIALLY_STRUCTURED and two UNRESOLVED_WITHIN_FIXED_SCOPE (P1/P6).
The largest peak coincides with a broad oblique band across the saved CAL/COR
subarray. Its large residual is not a qualified candidate or evidence of
artificial origin. No detector or observing coverage is qualified.

## Immutable scientific sequence

| Stage | Commit | Content |
|---|---|---|
| Inherited LS8AW closure | [271c72c71afff7ba5bb3dee507e80931d11d3732](https://github.com/andersenmartin-blip/setisearch/commit/271c72c71afff7ba5bb3dee507e80931d11d3732) | Parent before GJ 536 access |
| AX original header freeze | [b28022d5ac230ce70906e651ea9d2df71f96df63](https://github.com/andersenmartin-blip/setisearch/commit/b28022d5ac230ce70906e651ea9d2df71f96df63) | Exact pair, bounded reader and header auditor before archive access |
| AX checkout recovery freeze | [2a7d3fad3bbcb9670880ec9b6339d0e3fc3a403c](https://github.com/andersenmartin-blip/setisearch/commit/2a7d3fad3bbcb9670880ec9b6339d0e3fc3a403c) | Preserved failed checkout; sparse checkout and preservation guard before archive access |
| AX header result | [328c1d234217d1737edc69d7012641f46a6847c7](https://github.com/andersenmartin-blip/setisearch/commit/328c1d234217d1737edc69d7012641f46a6847c7) | Each visit's own identity, schema, rows and exposure tuple |
| AX L2 freeze | [2d7eaf36c801f52bfc0d247b40adeba601660e74](https://github.com/andersenmartin-blip/setisearch/commit/2d7eaf36c801f52bfc0d247b40adeba601660e74) | Scalar header PASS and 587,052 exact table bytes before values |
| AX audited L2 result | [a5e343f7b5b6fee73514f2d06bda8e2b64feb85b](https://github.com/andersenmartin-blip/setisearch/commit/a5e343f7b5b6fee73514f2d06bda8e2b64feb85b) | Both tables, all eligible windows, signed clusters and independent audit |
| AY metadata freeze | [4c34714c0eb4e14bc3041514811f1746eda0ee87](https://github.com/andersenmartin-blip/setisearch/commit/4c34714c0eb4e14bc3041514811f1746eda0ee87) | All nine representatives and image-audit source, before metadata and pixels |
| AY metadata result | [6fd13368ec9b08a05aa5ec69500fc0877a0359f1](https://github.com/andersenmartin-blip/setisearch/commit/6fd13368ec9b08a05aa5ec69500fc0877a0359f1) | 522 unique exposure joins and exact future image ranges; pixels closed |
| AY image freeze | [7e9d89c611b80c58dd584a9b54f8dd6229786521](https://github.com/andersenmartin-blip/setisearch/commit/7e9d89c611b80c58dd584a9b54f8dd6229786521) | Exact CAL/COR/smearing scope and unchanged image gates before pixels |
| AY audited image result | [ccd3645aaecd6d79c34d2ccdf800e9609e68ec72](https://github.com/andersenmartin-blip/setisearch/commit/ccd3645aaecd6d79c34d2ccdf800e9609e68ec72) | Every original signed representative, all nine labels and image audit |
| AZ retained-study freeze | [9a15ac5201ad84e6d393069e27b7425d238541d2](https://github.com/andersenmartin-blip/setisearch/commit/9a15ac5201ad84e6d393069e27b7425d238541d2) | Complete unresolved P1/P6 set and unchanged residual method before native calculation |
| AZ audited result | [07182093f93d24b5a22dbc047324e510bce4676d](https://github.com/andersenmartin-blip/setisearch/commit/07182093f93d24b5a22dbc047324e510bce4676d) | Eight native cases, 192 held cases, 128 signed controls and independent reconstruction |

Final scientific tree: `a3054bce99f52d3463bf8512134ac584344a28c8`.
The 11 commits after LS8AW add **309 files**, changing/removing no inherited
file. All 309 are locally verified against public Git blobs and SHA256.
The newly introduced AX workflow was prospectively amended after its failed
checkout; no acquired scientific outcome was overwritten. Editorial closure
adds this record, LS8AZ_CONTINUATION.md and release verification, prefixes
PROJECT_STATUS.md and appends PROJECT_DIRECTION.md. Main README receives the
current result/next action while preserving dated history. Scientific outputs
are not edited by closure.

## Workflow outcomes and preserved infrastructure failure

| Workflow | Run | Verified conclusion |
|---|---|---|
| Initial AX checkout attempt | [35879603888](https://github.com/andersenmartin-blip/setisearch/actions/runs/35879603888) | completed / cancelled; timed out in full Git checkout; archive step skipped |
| AX headers after prospective recovery | [35881800241](https://github.com/andersenmartin-blip/setisearch/actions/runs/35881800241) | completed / success |
| AX L2 screen and scalar audit | [35882153415](https://github.com/andersenmartin-blip/setisearch/actions/runs/35882153415) | completed / success |
| AY metadata and exposure joins | [35882721570](https://github.com/andersenmartin-blip/setisearch/actions/runs/35882721570) | completed / success |
| AY paired images and independent audit | [35883288126](https://github.com/andersenmartin-blip/setisearch/actions/runs/35883288126) | completed / success |
| AZ retained residuals and independent audit | [35884597982](https://github.com/andersenmartin-blip/setisearch/actions/runs/35884597982) | completed / success |

All trigger head SHAs match their exact freezes. The initial job reached its
15-minute limit while fetching the full repository. The scientific step was
skipped and acquired **zero archive bytes**. An attempted fallback commit from
the incomplete checkout could not advance the branch; its non-fast-forward
push was rejected. Full decoded job log and terminal run evidence are retained
in verification_ls8ax_checkout_failure. Executor-local fallback status and
environment files were not published and have not been reconstructed.
LS8AX_CHECKOUT_RECOVERY.md records these limits.

The recovery changed checkout to the required sparse directories and guarded
preservation on successful checkout. It did not change targets, readers,
scientific methods or thresholds. The same checkout pattern was frozen into
the subsequent workflows. All five data-reading/analysis workflows succeeded;
there was no scientific failure or result-dependent rerun.

## Tests, independent audits and identities

The **5 transport / 2 stable L2 / 11 image / 18 residual tests** pass before
their corresponding data calculations. Independent scalar FITS-card parsing
verifies both complete 18-column, 138-byte-row schemas, identities, receipts,
exposures and byte boundaries without astropy or producer imports. Header
audit source was public before headers and its PASS result before L2 values.
Ledger/header exposure comparison uses the prospectively defined binary32
equivalence; actual full header values are retained and used independently.

| Audit | Numerical or combined comparisons | Exact checks | Disagreements |
|---|---:|---:|---:|
| AX L2 scalar reconstruction | 122580 numerical/discrete | included | 0 |
| AY exposure joins | — | 2393 | 0 |
| AY native image reconstruction | 850833 | 1445201 | 0 |
| AZ residual/control reconstruction | 610586 | 640224 | 0 |

L2 tolerances remain relative 2e-8 / absolute 2e-10. Image/residual tolerances
remain relative 2e-8, native absolute 1e-6 and dimensionless absolute 1e-8.
AZ's maximum fraction of its allowed numerical tolerance is 0.01265386.
Its 48 signed known-template cases, 80 signed compact cases and all 128
additive checks pass the unchanged 1e-9 control error bound.

The image core remains SHA256
`54255f3b8a21ebb4c279243ce152b1501549f588630833d862657bc96131463f`.
Image reconstruction functions retain their inherited independent equations.
All AZ auditor functions outside main and its recursive comparison function
are AST-identical to LS8AS; adaptation covers source identities, the complete
unresolved set, verified cadence and counts. No new mathematical module or
duration was introduced.

All **272 manifest entries** match locally recomputed SHA256: 2 retained
checkout-failure entries, 28 AX header entries, 22 AX L2 entries, 104 AY
metadata entries, 94 AY image entries and 22 AZ residual entries. All 27
compressed CAL/COR/smearing payloads also pass both packed and uncompressed
receipt digests and exact lengths. Every one of the 12 URL resolutions
succeeded on its first attempt, as did all 27 image/smearing ranges.

File identities, run evidence, acquisition counts, original-label checks,
retained scope review and next-cohort identity are in
verification_ls8az/release_verification.json. The full L2 plot, all nine
CAL/COR/DELTA figures and both residual figures were visually inspected:
**12 figures total**. Readable plots retain the largest peak, other retained
extrema, signed image structure and all plotted local controls.

## Exact acquisition and bounded outcomes

| Stage | Acquired payload bytes | Scope |
|---|---:|---|
| AX headers | 40320 | 20160 bytes per visit; zero table values |
| AX DEFAULT-L2 tables | 587052 | 570354 + 16698 bytes; 4133 + 121 rows |
| AY FITS headers and metadata tables | 1882908 | 64 exact ranges across four CAL/COR source products; zero image pixels |
| AY image arrays | 167040000 | Nine original 29-row contexts, both CAL and COR |
| AY smearing arrays | 417600 | Nine matching contexts |
| AZ new archive payload | 0 | 37120000 bytes re-read from retained CAL/COR inputs |

AX inclusive table ranges are 20160–590513 and 20160–36857. The visits verify
NEXP=1, EXPTIME=TEXPTIME=40.1699981689453 / 40.2000007629395 seconds and
pipeline 14.1.2. There are 10,032 / 183 eligible windows and 7/1 positive
clusters, plus one negative cluster in the first visit. All 261 image context
rows match uniquely in CAL/COR within 1 ms under UTC/MJD/BJD and counter/
integrity checks. Image products are unscaled 200x200 float64 ADU frames,
offsets (157,759), with exactly frozen byte ranges. Raw imagettes, alternative
apertures and the three later GJ 536 visits stay unopened.

P1/P6 remain unresolved by the fixed gates. P1's COR residual/reference is
0.257893 / 0.263414 with 23/24 local controls at least as large; P6's is
3841.994548 / 3951.598570 with 0/24. The latter coincides with a broad band
in both saved CAL and COR images and leaves broad signed residual structure.
No probability, unique physical cause or technical-origin interpretation is
assigned. Hypothetical subtraction would lose 10.97–11.48% of injected COR
brightness flux; no subtraction, veto, mask or new classifier is adopted.

Retained first-visit row 1977 is approximately 51.10% above its STATUS=0
visit median but has STATUS=1 and no eligible event window. Its cause remains
unassigned. The largest point, row 3408, is the eligible P6 event and received
all prescribed follow-up. Other retained extrema outside complete context
are documented without reselection. Search eligibility is not sensitivity,
completeness, a population limit or qualified observing coverage.

## Continuation

Prepare **LS8BA, rank-21 2MASS J11285624+1010395**, exact chronological pair
CH_PR100018_TG010801_V0300 / CH_PR100018_TG010802_V0300. Ledger starts are
58973.0988567193 / 58976.88448678 MJD. Both ledger tuples are NEXP=1,
EXPTIME=TEXPTIME=60 seconds and pipeline 14.1.2, subject to each own header
audit before separately frozen L2 access. Its science values remain unopened.
The original 1,000-row census, 452 eligible visits and 107-cohort order are
unchanged and match the independent reconciliation. All prior labels,
unassessed points, closed studies and reserved TESS/M43 material remain
unchanged. Calibration NOT_READY; request UNSENT. Publication is authorized;
delegation remains deferred.

[Interpretation and exact continuation](LS8AZ_CONTINUATION.md) ·
[L2 report](results_ls8ax_l2_screen/REPORT.md) ·
[Image report](results_ls8ay_images/REPORT.md) ·
[Residual report](results_ls8az_residuals/REPORT.md) ·
[Current project status](PROJECT_STATUS.md).
