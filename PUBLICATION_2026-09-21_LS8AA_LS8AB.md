# LS8AA–LS8AB publication and verification — 21 September 2026

Repository: `andersenmartin-blip/setisearch`; science branch:
`m43-support-qualification`. Standing authorization covers code, protocols,
data, results, logs and the README update on main.

## Immutable sequence

| Stage | Commit | Result |
|---|---|---|
| LS8Y–LS8Z closure parent | `62520522f1a4ac3bf0fc1e1b599200ef353be7b9` | Previous closed study retained |
| LS8AA exact pair/header freeze | `22364505ef80340ac3ce39a95a2286281492264c` | Rank-8 pair, no science values |
| Header result | `1ab2ec20735219cf51d072f0f7fafb7db3da83ee` | 137/134 rows; 60 seconds/NEXP=1 |
| L2 scope freeze | `671690401a5ca180ff01af10287171027da8b2b8` | 37,398 exact table bytes; unchanged screen |
| Audited L2 result | `ae3c8841cb3575c8008f5c85245448ac8b833d16` | 271 rows, 294 windows, one positive cluster |
| LS8AB representative/metadata freeze | `cb11866ed4fd31c1a84ab96f0759d31cd93c41e4` | Complete signed set, metadata only |
| Audited image metadata | `ad0cb8666580b6957aad5d2f1134f7f346d00ce7` | 58 unique joins; exact future ranges |
| Image payload/diagnostic freeze | `c51f365345924e688a3505d4568d7c6052c13a9c` | 18,560,000 image + 46,400 smearing bytes |
| Audited image result | `ca3758bc6c736581eaf532954b7129182ecb3cc1` | TG007801_P0: CORRECTION_LINKED |

All four workflows succeed:

- [LS8AA headers 35635060652](https://github.com/andersenmartin-blip/setisearch/actions/runs/35635060652).
- [LS8AA L2 screen/audit 35635391402](https://github.com/andersenmartin-blip/setisearch/actions/runs/35635391402).
- [LS8AB metadata/joins 35636134333](https://github.com/andersenmartin-blip/setisearch/actions/runs/35636134333).
- [LS8AB image diagnostic/audit 35636758417](https://github.com/andersenmartin-blip/setisearch/actions/runs/35636758417).

All eight header/L2/image-metadata/image URL resolutions succeed on their
first attempt. All three image/smearing range requests also succeed on their
first attempt; the L2 table requests remain unretried. No transport recovery,
source substitution or scientific rerun is needed.

## Verification scope

The five existing URL-timeout tests and two inherited stable L2 tests pass.
The independent L2 audit passes **3,528 numerical/discrete comparisons**.
Image metadata passes **58 unique joins and 269 exact checks** before pixels.
All nine inherited image tests pass before payload. The independent image
audit passes **94,537 numerical comparisons and 160,581
exact checks**, zero disagreements. Both figures were visually inspected.

All 28 L2 metadata files, 22 L2 result files and 57 image metadata files were
locally SHA256/Git-identity verified. Of 22 image-result
manifest entries, 20 were also locally
verified. The two larger compressed CAL/COR inputs were verified, decompressed and
independently decoded by the successful workflow audit. The connector
exposed their Git identities but returned no binary content for an additional
local copy. Their public files, raw/compressed hashes and exact range receipts
are preserved. This is a local retrieval limitation, not missing science data
or a failed audit.


| Compressed input | Git blob identity | Compressed SHA256 | Raw SHA256 |
|---|---|---|---|
| TG007801_P0/SCI_CAL_SubArray.bin.gz | `39e44c85210f3d18ced97b90d57f3617915bd539` | `541adbe69417f561e67d94b502804e7860192963a43a5d883080021da28214e7` | `2ed9c10ec3df8f9f649d1158e18d49dc2f545d418a027b92f2cfb500398239d2` |
| TG007801_P0/SCI_COR_SubArray.bin.gz | `007b72e4689303b74250a04a33f99b1ea49d86df` | `7c6126a19274f98be8e832cc615c5015991d87ab898657b1ec60e1a0a979b03a` | `4099d496fb0864f36e1485a757986932b59dfae0aaeff1b67443e9bb0fcb9758` |

The independent image audit checks raw/compressed hashes, source ranges,
native float decoding, joins, masks, maps, fits and the fixed classification.
Unchanged image tolerances are relative 2e-8 and native/dimensionless absolute
1e-6/1e-8. L2 retains relative 2e-8 / absolute 2e-10. No disagreement,
scientific rerun or result-dependent retuning is omitted.

The complete scientific comparison adds 155 files and
changes no earlier file. Exactly 153 are byte-verified
against locally calculated Git identities; remaining input identities are
recorded above. Final scientific result tree: `ca92f6b766f4efc3d62716fa8bfce730af5d85c5`.

The separate editorial closure adds this record and LS8AB_CONTINUATION.md,
prepends the latest PROJECT_STATUS.md checkpoint, updates its current LS row
and appends the PROJECT_DIRECTION.md decision. The main README receives the
same conclusion and next action. These edits preserve frozen source,
data, reports, checksums and earlier history.

## Scientific state

The fixed image diagnostic classifies the positive event as
**CORRECTION_LINKED**. DELTA/COR is **-0.713546 / -2.797082** in the two
coordinate conventions, with complete apertures and positive COR signs
matching L2. The delivered correction reduces the positive aperture residual;
the amount is sensitive to the coordinate convention, while both satisfy the
original closure gate. The label describes material coupling to processing;
the responsible component and physical cause remain unassigned.

**Immediate next action: prepare LS8AC for rank-9 PG1303-114**, starting
with a separate exact-pair/header freeze for CH_PR100002_TG006401_V0300 and
CH_PR100002_TG006402_V0300. Verify the NEXP=1/60-second ledger exposures,
then freeze exact DEFAULT-L2 ranges and transfer the unchanged signed screen.
Those science values remain unopened; the cohort's three later eligible
visits stay outside scope. The WASP-43 pair is closed.

No qualified SETI candidate, detector, sensitivity or observing coverage is
added. The earlier TESS_260647166 positive remains UNRESOLVED_WITHIN_FIXED_SCOPE
and its bounded study closed. GJ 436 and PG 1245-042 remain closed under
CORRECTION_LINKED. Other closed optical studies and M33 HD 3651 are unchanged.
Reserved TESS/M43 panels remain closed. Calibration is NOT_READY and its
technical request unsent. Standing research/publication authorization
continues; delegation remains deferred.

[L2 result](results_ls8aa_l2_screen/REPORT.md) ·
[Image result](results_ls8ab_images/REPORT.md) ·
[Interpretation and exact continuation](LS8AB_CONTINUATION.md).
