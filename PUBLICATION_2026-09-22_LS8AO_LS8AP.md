# LS8AO–LS8AP publication and verification — 22 September 2026

The rank-14 WASP-103 pair is complete and closed. Its one positive cluster
is CORRECTION_LINKED under the unchanged paired-image diagnostic. This record
identifies the immutable scientific sequence and subsequent editorial closure.

## Immutable scientific sequence

| Stage | Commit | Content |
|---|---|---|
| Inherited LS8AL–LS8AN closure | [466032bcb3669e320c73fc74821462670d27117d](https://github.com/andersenmartin-blip/setisearch/commit/466032bcb3669e320c73fc74821462670d27117d) | Parent before any WASP-103 acquisition |
| LS8AO header freeze | [094430641b3ea57dbc376aa18214156d9e9259ae](https://github.com/andersenmartin-blip/setisearch/commit/094430641b3ea57dbc376aa18214156d9e9259ae) | Exact pair and bounded header reader |
| LS8AO metadata result | [3ac15f4973461879f47449a3a0925548ae99df00](https://github.com/andersenmartin-blip/setisearch/commit/3ac15f4973461879f47449a3a0925548ae99df00) | Identities, schemas, exposures, rows and receipts |
| LS8AO exact L2 freeze | [c188bfca876b1c01084aa00d22ba5bd9da17e83f](https://github.com/andersenmartin-blip/setisearch/commit/c188bfca876b1c01084aa00d22ba5bd9da17e83f) | 77,970 bytes; unchanged scorer and independent audit |
| LS8AO audited result | [f88f350278e8814b7d88303a36a5b7f05c58457b](https://github.com/andersenmartin-blip/setisearch/commit/f88f350278e8814b7d88303a36a5b7f05c58457b) | Both tables, all windows and signed clusters, figure and audit |
| LS8AP metadata freeze | [b4024a865ff0fc98e8e3f74af793c146e3b2aaea](https://github.com/andersenmartin-blip/setisearch/commit/b4024a865ff0fc98e8e3f74af793c146e3b2aaea) | Complete representative, 29 context rows and zero image bytes |
| LS8AP metadata result | [445adf1ad583e04b989bc27daf42a73631af7988](https://github.com/andersenmartin-blip/setisearch/commit/445adf1ad583e04b989bc27daf42a73631af7988) | 58 unique joins, 269 audit checks and exact future ranges |
| LS8AP image freeze | [77ce7e40fae21ef24e7f77e81a0fde1ab7b9d822](https://github.com/andersenmartin-blip/setisearch/commit/77ce7e40fae21ef24e7f77e81a0fde1ab7b9d822) | 18,560,000 CAL/COR and 46,400 smearing bytes |
| LS8AP audited image result | [eaecf09e3d8153d929bdee53e0ea4a5fdb60bec0](https://github.com/andersenmartin-blip/setisearch/commit/eaecf09e3d8153d929bdee53e0ea4a5fdb60bec0) | CORRECTION_LINKED; full diagnostics and independent audit |

The final scientific tree is 8b3f057ec6de0b4e19cef312d42fdff758cbae08.
Eight scientific commits add 155 files and change or remove no earlier file.
The editorial closure adds this record and LS8AP_CONTINUATION.md, prefixes
PROJECT_STATUS.md and appends PROJECT_DIRECTION.md. The main README receives
the current result and next action while retaining all prior dated history.
No scientific output, method, original threshold or earlier label is edited.

## Successful workflow sequence

| Workflow | Run | Verified conclusion |
|---|---|---|
| LS8AO headers and transport tests | [35763942387](https://github.com/andersenmartin-blip/setisearch/actions/runs/35763942387) | completed / success |
| LS8AO screen, independent audit and report | [35764260506](https://github.com/andersenmartin-blip/setisearch/actions/runs/35764260506) | completed / success |
| LS8AP image metadata and independent joins | [35764860464](https://github.com/andersenmartin-blip/setisearch/actions/runs/35764860464) | completed / success |
| LS8AP images, independent audit and report | [35765239036](https://github.com/andersenmartin-blip/setisearch/actions/runs/35765239036) | completed / success |

Each workflow's recorded freeze identity equals its trigger commit. The five
URL/transport tests pass before headers, the two stable L2 tests before science
values and the nine inherited image tests before pixels. The independent audits
pass 9,648 L2 comparisons, 269 image-metadata checks and 94,537 numerical /
160,581 exact image checks, with no disagreement or tolerance change.
The image job spent several minutes checking out the repository and then
completed successfully; no failed scientific attempt or rerun was needed.

## Retained data and exact acquisition limits

Both visits verify NEXP=1, EXPTIME=TEXPTIME=60 seconds and pipeline 14.1.2.
Header preflight reads 20,160 bytes per product within 64 KiB, no table values.
The 18-column L2 row is 138 bytes. Exact later science ranges are:

| Product | Rows | Inclusive range | L2 bytes |
|---|---:|---|---:|
| CH_PR100013_TG000101_V0300 | 269 | 20160–57281 | 37,122 |
| CH_PR100013_TG000102_V0300 | 296 | 20160–61007 | 40,848 |
| Total | 565 | — | 77,970 |

The first visit has zero signed crossings in 384 eligible windows. The second
has three positive crossings in one cluster and no negative crossing in 420
eligible windows. The sole representative is TG000102_P0, row 274, duration
one 60-second exposure, native context 260:289, score +13.672258341090284,
and excess/local baseline 1.3013708558552712%.

Only the second visit receives image follow-up. Metadata reads 79,336 CAL and
126,056 COR bytes: 205,392 total, within 20,000,000 per product. Both native
arrays are 296 x 200 x 200, unscaled float64 ADU, with offsets (157,759).
The 29 context rows have 58 unique joins before any image payload.

| Payload | Inclusive range | Bytes |
|---|---|---:|
| SCI_CAL_SubArray | 83217280–92497279 | 9,280,000 |
| SCI_COR_SubArray | 83217280–92497279 | 9,280,000 |
| COR smearing rows | 95277440–95323839 | 46,400 |

Every identity, range and receipt is retained. All eight archive URL resolutions
and all three image payload requests succeed on the first attempt. There is no
extra aperture, later visit, raw imagette, source substitution or scientific rerun.

## Verification and local-copy boundary

All 155 new scientific files have public Git identities. 153 were retrieved
and locally byte-verified against those identities. The two compressed CAL/COR
inputs exceed the GitHub contents response's local-copy limit: that response
returned their identities but no binary content. Their complete public bytes
were SHA256-verified, decompressed and independently decoded in the successful
image workflow, before reconstruction and classification checks. This limit
does not represent missing published data or skipped scientific verification.

| Manifest | Entries | Local SHA256 checks | Remaining verification |
|---|---:|---:|---|
| LS8AO headers | 28 | 28 | Complete |
| LS8AO L2 screen | 22 | 22 | Complete |
| LS8AP metadata | 57 | 57 | Complete; future-image config also Git-verified |
| LS8AP images | 22 | 20 | Two CAL/COR inputs checked by independent workflow |

All four manifest files also match their published Git identities. The two
larger inputs in results_ls8ap_images/TG000102_P0 have these exact identities:

| File | Git blob SHA1 | Compressed SHA256 | Decompressed SHA256 |
|---|---|---|---|
| SCI_CAL_SubArray.bin.gz | 942b4b1c2b68c6724d3da032648ea12fea3a5d45 | eed504b49922e9c7dadb2f057fc1f49a2c62db1a47667035cc50e73e7dc6768a | d5d734ca56024ded1eb2ef12201883c3590ae183c31793f8d152dfdde0be2925 |
| SCI_COR_SubArray.bin.gz | df7442f17714dd6d56367ad4a6498476cd40ede5 | 99eb596fae7969c2b38fa565ed2b12a82dc15f3aac0d03b921d03f0ea4131a83 | 580829d268bd4eb1177e3efb2709d051e41601c5d646c76b0a8b7208649727b1 |

The inherited original reconciliation file was not newly copied locally in
this turn. Its existing SHA256 pin and complete equality of all 107 cohorts
with the original selection were verified by the successful header workflow
before any new headers. Seventeen other header/screen parent files and forty
image-parent dependencies were locally checked against their original Git
identities. The image mathematics, independent event-map/regression/column/
rebuild functions and numerical tolerances remain unchanged.

Both figures were visually inspected. The largest displayed table points are
STATUS=1 (TG000101 row 201 and TG000102 row 185), and remain retained under
the original eligibility rule. The CAL/COR/DELTA image uses a common signed
native-unit scale and both original apertures. No visual selection is added.

## Interpretation and continuation

The fixed correction gate passes in both conventions: DELTA/COR is
5.906077918509 / 5.915583013352 and the column ratio is
6.087909211050 / 6.093572064600. CAL event-residual sums are negative while
COR sums are positive and match L2. The label is CORRECTION_LINKED, indicating
substantial coupling to delivered processing, not a unique physical correction
component or proof that source variability is absent. The smearing fits are
rank deficient and remain unavailable. No residual study is triggered.
Scores and overlapping windows do not supply calibrated false-alarm rates,
sensitivity, completeness or qualified observing coverage. No SETI candidate
or detector qualification is added.

Prepare LS8AQ for rank-15 GJ 581, exact first pair
CH_PR100011_TG023701_V0300 and CH_PR100018_TG008301_V0300. Their ledger
tuples are NEXP=1, EXPTIME=TEXPTIME=60 seconds, pipeline 14.1.2; require their
own header verification and later exact L2 freeze. Science values remain
unopened and five later eligible GJ 581 visits remain outside the pair.
WASP-103's nine later visits stay outside its now closed pair. HD 106315's
three unresolved labels and closed bounded study remain unchanged.

[Interpretation and exact continuation](LS8AP_CONTINUATION.md) ·
[L2 report](results_ls8ao_l2_screen/REPORT.md) ·
[Image report](results_ls8ap_images/REPORT.md) ·
[Project status](PROJECT_STATUS.md).
