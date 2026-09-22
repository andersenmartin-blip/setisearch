# LS8AQ–LS8AS publication and verification — 22 September 2026

The rank-15 GJ 581 pair and single bounded residual study are complete and
closed. All original labels remain: nine CORRECTION_LINKED, three
SPATIALLY_STRUCTURED and two UNRESOLVED_WITHIN_FIXED_SCOPE.

## Immutable scientific sequence

| Stage | Commit | Content |
|---|---|---|
| Inherited WASP-103 closure | [cc3941c9e9f01b09a31994278e642dc490dc51a0](https://github.com/andersenmartin-blip/setisearch/commit/cc3941c9e9f01b09a31994278e642dc490dc51a0) | Parent before GJ 581 access |
| LS8AQ header freeze | [1e92edfc9fad9025e963a9ed4a9303ab34f4ff52](https://github.com/andersenmartin-blip/setisearch/commit/1e92edfc9fad9025e963a9ed4a9303ab34f4ff52) | Exact rank-15 pair; bounded headers only |
| LS8AQ header result | [ccd12a0597adb66fee10fa36ee52b672f8654be4](https://github.com/andersenmartin-blip/setisearch/commit/ccd12a0597adb66fee10fa36ee52b672f8654be4) | Own schemas, exposure tuples and rows |
| LS8AQ L2 freeze | [f45a0b9ca21a2e5a3ffc4e1efe5450a83614df02](https://github.com/andersenmartin-blip/setisearch/commit/f45a0b9ca21a2e5a3ffc4e1efe5450a83614df02) | 499,974 exact L2 bytes; unchanged signed scorer |
| LS8AQ audited result | [051d973dffe52f151f3948e38070b40bbc32cdf4](https://github.com/andersenmartin-blip/setisearch/commit/051d973dffe52f151f3948e38070b40bbc32cdf4) | Both tables; 7,869 windows; all signed clusters |
| LS8AR metadata freeze | [a29525dfa1096cbca008db37e732a85b60f81a8e](https://github.com/andersenmartin-blip/setisearch/commit/a29525dfa1096cbca008db37e732a85b60f81a8e) | All 14 representatives; zero pixels |
| LS8AR metadata result | [ffb7201ddabebe017240afa2053bd34729dfdeed](https://github.com/andersenmartin-blip/setisearch/commit/ffb7201ddabebe017240afa2053bd34729dfdeed) | 814 unique joins; 3,723 exact checks |
| LS8AR payload freeze | [0ca865e5de2054dbeedb1252b8191d135d240851](https://github.com/andersenmartin-blip/setisearch/commit/0ca865e5de2054dbeedb1252b8191d135d240851) | 260,480,000 image and 651,200 smearing bytes |
| LS8AR audited result | [af1de44c32b524d8438adb23e0cf9003928e94b4](https://github.com/andersenmartin-blip/setisearch/commit/af1de44c32b524d8438adb23e0cf9003928e94b4) | Nine correction-linked, three spatial, two unresolved |
| LS8AS residual freeze | [d768f32008fc72c9dd9ec37f59d28ad7e937da7d](https://github.com/andersenmartin-blip/setisearch/commit/d768f32008fc72c9dd9ec37f59d28ad7e937da7d) | Complete unresolved set; retained inputs only |
| LS8AS audited result | [daf3a48abb60990406b03ef0677a7e857f0d959c](https://github.com/andersenmartin-blip/setisearch/commit/daf3a48abb60990406b03ef0677a7e857f0d959c) | Single bounded study closed; every image label preserved |

Final scientific tree: 9557dcc97e857532e40467a8f7124dcb2f5447ca.
Ten scientific commits add **302 files**, changing or removing no earlier
file. Verification combines the complete eight-commit 273-file image sequence
and two-commit 29-file residual sequence, avoiding a truncated 300-file
comparison response. All paths are distinct. The editorial closure adds this
record and LS8AS_CONTINUATION.md, prefixes PROJECT_STATUS.md and appends
PROJECT_DIRECTION.md. Main README receives the current result and next action
while retaining its prior dated history. No scientific output is edited.

## Successful workflows and tests

| Workflow | Run | Verified conclusion |
|---|---|---|
| LS8AQ headers | [35769065085](https://github.com/andersenmartin-blip/setisearch/actions/runs/35769065085) | completed / success |
| LS8AQ L2 and audit | [35769636447](https://github.com/andersenmartin-blip/setisearch/actions/runs/35769636447) | completed / success |
| LS8AR metadata and joins | [35770623441](https://github.com/andersenmartin-blip/setisearch/actions/runs/35770623441) | completed / success |
| LS8AR images and audit | [35771276994](https://github.com/andersenmartin-blip/setisearch/actions/runs/35771276994) | completed / success |
| LS8AS retained-data study | [35772433101](https://github.com/andersenmartin-blip/setisearch/actions/runs/35772433101) | completed / success |

Every recorded freeze identity equals its trigger. Five transport tests pass
before headers; two stable L2 tests before values; all nine inherited image
tests plus two native-cadence two-row known answers before pixels; and all
18 inherited residual tests before derived native calculation. The first
partial-local image test invocation lacked the historical audit module;
four duration tests passed locally and the complete 11-test suite subsequently
passed in the mandatory pre-pixel workflow. No scientific run failed or was
rerun to seek a pass. Transport/source identities and tolerances are unchanged.

Independent audits pass 94,428 L2 comparisons; 3,723 metadata checks;
1,323,518 numerical and 2,248,091 exact image checks; and 610,448 numerical
and 640,222 exact residual checks, with zero disagreements. Residual controls
include 48 signed known-template, 80 compact and 128 additive checks. Largest
residual error/tolerance ratio is 0.00011326592982094795. The 18 tests include
training exclusion, covariance, duration, guard, boundary and reconstruction
known answers. No mathematical module or tolerance is changed for LS8AS.

## Exact acquisition boundary

Both L2 products verify NEXP=1, EXPTIME=TEXPTIME=60 s, pipeline 14.1.2,
18 columns and 138-byte rows. Header access reads 20,160 bytes/product within
64 KiB, with zero table values. Exact later L2 ranges are:

| Product | Rows | Inclusive range | Bytes |
|---|---:|---|---:|
| CH_PR100011_TG023701_V0300 | 3,545 | 20160–509369 | 489,210 |
| CH_PR100018_TG008301_V0300 | 78 | 20160–30923 | 10,764 |
| Total | 3,623 | — | 499,974 |

Only the first visit has signed representatives and receives image metadata
or pixels. CAL metadata reads 602,425 bytes; COR 909,065 bytes, total 1,511,490,
each within 20,000,000. The 14 disjoint contexts contain 407 original rows;
814 unique joins agree within 1 ms, exact UTC/counters/integrity. Native arrays
are unscaled 200x200 float64 ADU and match the original exposure tuple.
Exact filenames, ETags, sizes, offsets and all 42 image/smearing intervals
are frozen in config/ls8ar_images.json and LS8AR_PAIRED_IMAGE_PROTOCOL.md.
Acquire exactly 260,480,000 CAL/COR bytes and 651,200 smearing bytes.
All eight archive URL resolutions and all 42 image ranges succeed on their
first attempts. No alternate product, aperture, raw imagette or later visit.

LS8AS uses only the complete unresolved set P3/P5, eight native cases,
192 held cases and 128 signed controls. Both producer and auditor verify the
full original 14-ID/label ledger and derive that exact set, independently of
any residual outcome. The 12 closed representatives are not refitted. The
study rereads 37,120,000 retained CAL/COR bytes and acquires zero source bytes.

## Published bytes and additional local verification

All 302 new files have public Git identities; **274** also match locally
recomputed identities. The **28** larger compressed CAL/COR inputs exceed the
known GitHub contents local-copy limit and were not re-transferred through
that route. Their published complete bytes were SHA256-verified, decompressed
and independently struct-decoded by the successful image workflow. The entire
image manifest was checked again by the residual workflow before native use.
This is a local-copy limitation, not missing published data or skipped audit.

| Manifest | Entries | Local SHA256 checks | Larger inputs verified in workflow |
|---|---:|---:|---:|
| results_ls8aq_l2_metadata | 28 | 28 | 0 |
| results_ls8aq_l2_screen | 22 | 22 | 0 |
| results_ls8ar_metadata | 57 | 57 | 0 |
| results_ls8ar_images | 139 | 111 | 28 |
| results_ls8as_residuals | 22 | 22 | 0 |

Every manifest itself also matches its published Git identity. Exact raw and
compressed SHA256 hashes are public in each input receipt and SHA256SUMS.
The larger input objects have these Git identities:

| Representative / input | Git blob SHA1 | Compressed bytes |
|---|---|---:|
| TG023701_N0 / SCI_CAL_SubArray.bin.gz | 78411a2ba0243190b14f5cf9bf37bdacd1d58cb9 | 3,752,992 |
| TG023701_N0 / SCI_COR_SubArray.bin.gz | 6d90f0bb95cbab3148cfa195b1dd1b572b289c35 | 6,930,699 |
| TG023701_N1 / SCI_CAL_SubArray.bin.gz | 28c63b99ab70f902a99250382d703da07a619ee0 | 3,883,742 |
| TG023701_N1 / SCI_COR_SubArray.bin.gz | 3f4d9faa115ebd60a7c81cf6a69abda9fa3d03ed | 7,171,904 |
| TG023701_N2 / SCI_CAL_SubArray.bin.gz | a8b03c48948188758e3c30414ebb8f53079bec48 | 3,778,322 |
| TG023701_N2 / SCI_COR_SubArray.bin.gz | a596ef3455548ebe0f20ce23a528891e164a4ffd | 6,944,551 |
| TG023701_N3 / SCI_CAL_SubArray.bin.gz | 6aef48d43507b2ddb479c5ae30af6fb33a37bd2d | 3,772,777 |
| TG023701_N3 / SCI_COR_SubArray.bin.gz | 505e2683314671374d8405e015ec789139d300e0 | 6,943,131 |
| TG023701_N4 / SCI_CAL_SubArray.bin.gz | d830737a79e21797f7dc64d9d77d69a89f862ae3 | 3,797,774 |
| TG023701_N4 / SCI_COR_SubArray.bin.gz | f5f84ee663ca2681eef890f749b4a73ce0ae6286 | 6,955,202 |
| TG023701_P0 / SCI_CAL_SubArray.bin.gz | 367b0de249b84e37e498755d131a92f961158cbd | 3,756,412 |
| TG023701_P0 / SCI_COR_SubArray.bin.gz | 1c62705cd26f13fec7b4f406ee10160a85f0b5a1 | 6,933,986 |
| TG023701_P1 / SCI_CAL_SubArray.bin.gz | 789006db825173c5d944058cc9dc40a830dc8a3f | 3,768,698 |
| TG023701_P1 / SCI_COR_SubArray.bin.gz | dc228ce3667203d9e3f03a7e4b15c396d750b74c | 6,942,136 |
| TG023701_P2 / SCI_CAL_SubArray.bin.gz | 537268eaa5e4530ed7d3cbb03055f376955ceaef | 3,787,397 |
| TG023701_P2 / SCI_COR_SubArray.bin.gz | 19792d2f2c0453602b50c550d525c296cf524338 | 6,947,486 |
| TG023701_P3 / SCI_CAL_SubArray.bin.gz | aed0eed33fbd62980a0522161cdf3fc4ca73778d | 3,787,148 |
| TG023701_P3 / SCI_COR_SubArray.bin.gz | 914cf6e7a055fcff32928a0f8728e3ee34b10e38 | 6,945,926 |
| TG023701_P4 / SCI_CAL_SubArray.bin.gz | 818b87e41bea3a3bddc8570d1684cf1850ee06b1 | 3,770,943 |
| TG023701_P4 / SCI_COR_SubArray.bin.gz | cb35cc34bb10673ff852d5a32938fa17299123aa | 6,942,927 |
| TG023701_P5 / SCI_CAL_SubArray.bin.gz | 27b311dea907c94f368ded99598d2b66b1755dd0 | 3,771,429 |
| TG023701_P5 / SCI_COR_SubArray.bin.gz | b5c1b4e94d8b9ef2381d518f93fd47a4af163959 | 6,942,832 |
| TG023701_P6 / SCI_CAL_SubArray.bin.gz | ed218fd7c55f0c7b616d164e144ae2449349da6c | 3,789,749 |
| TG023701_P6 / SCI_COR_SubArray.bin.gz | 5c9c706871005b0f87caff47381436c08c49453d | 6,949,881 |
| TG023701_P7 / SCI_CAL_SubArray.bin.gz | 58565e25ee9b3ef560173feda2877f9c0d78c436 | 3,781,822 |
| TG023701_P7 / SCI_COR_SubArray.bin.gz | df5637668e97e8c518addb30b5dec49809489851 | 6,946,760 |
| TG023701_P8 / SCI_CAL_SubArray.bin.gz | a88dfbcbd6949c2f1072c740b474652eefce0e26 | 3,779,992 |
| TG023701_P8 / SCI_COR_SubArray.bin.gz | 7acb4f902e3058355a03c9e3e7a65c02b1883cc4 | 6,946,495 |

The original reconciliation remains pinned; the header workflow verifies full
equality of all 107 ordered cohorts before new headers. Forty image-parent
files and 31 residual-parent files additionally match their remote Git identities.
The independent image event-map/regression/column/rebuild functions and all
independent residual functions outside main, including recursive comparison
tolerances, are AST-identical to their pinned parents. Metadata scope, exact
input selection, names and fixed counts are the documented adaptations.

All 17 figures were visually inspected: one retained L2 figure, all 14 paired
image figures and both residual figures. The original status/context and
edge exclusions explain the large displayed noneligible points; no visual
selection, new mask, color-driven cut or classifier is introduced.

## Interpretation and continuation

P3's COR residual/reference ratios are 1.179547128 / 1.161620190, with 9/24
held values at least as large in each convention. P5's are 3.192675934 /
3.078003177, with 1/24 and 2/24. P5 is larger than most local controls;
these dependent counts neither identify a cause nor provide a calibrated
significance. Both remain unresolved; the bounded study is closed regardless.
Hypothetical subtraction removes 10.41–11.21% of injected COR brightness
flux and is not adopted. No qualified SETI candidate, detector, sensitivity,
completeness or observing coverage is added.

Prepare LS8AT for rank-16 EC14599-2047, first pair
CH_PR100002_TG010301_V0300 / CH_PR100002_TG010302_V0300, under separate
header and L2 freezes. Those values remain unopened; its third visit and
five later GJ 581 visits remain outside their pairs. Prior closed studies,
unresolved labels and reserved TESS/M43 panels stay unchanged. Calibration
NOT_READY; request UNSENT. Publication authorized; delegation deferred.

[Interpretation and exact continuation](LS8AS_CONTINUATION.md) ·
[L2 report](results_ls8aq_l2_screen/REPORT.md) ·
[Image report](results_ls8ar_images/REPORT.md) ·
[Residual report](results_ls8as_residuals/REPORT.md) ·
[Project status](PROJECT_STATUS.md).
