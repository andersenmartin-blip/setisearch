# LS8AF–LS8AH publication and verification — 22 September 2026

Repository: `andersenmartin-blip/setisearch`; science branch:
`m43-support-qualification`. Standing authorization covers code, protocols,
data, results, logs and the README update on main.

## Immutable sequence

| Stage | Commit | Result |
|---|---|---|
| LS8AC–LS8AE closure parent | `1886f6e8fe3aea4f2d95f1df6b7ebd29b4d0516e` | Prior studies retained |
| LS8AF pair/header freeze | `ee96b52952d038d403cada81bc3c2f1c97f38782` | Rank-10 pair; metadata only |
| Header result | `4301fd51c7b0d5a8ad94c428534140726b23b66b` | 81/72 rows; NEXP=1, 60 seconds |
| L2 scope freeze | `0e006ae040146eb868c3512ab1d13049eef252cb` | 21,114 exact table bytes |
| Audited L2 result | `3afc7472cf815da46bdadec8ba0fe5e35528eb63` | 153 rows, 165 windows, one positive cluster |
| LS8AG representative/metadata freeze | `e2fd21766753e713add3aad7e3101b887a24b37c` | Complete signed set; metadata only |
| Audited image metadata | `f1458c934a09c1707cc7f6591a31c84a83debd63` | 58 unique joins and exact future ranges |
| Image payload/diagnostic freeze | `0e1839c93fef24f69fb98cd54d7422ed86417bf2` | 18,560,000 image + 46,400 smearing bytes |
| Audited image result | `45972dd2e8658a2dc743f67b2e790ad6529c456e` | Positive unresolved under fixed gates |
| LS8AH retained-data freeze | `20f083d5c7bc5bd93def089c56d7bdc93a874c31` | One 60-second context; zero new archive bytes |
| Audited residual result | `bb64da03806f4af122ec887921bb4e8610f0e6d8` | 4 native / 96 held / 64 signed cases; bounded study closed |

All five workflows succeed at their exact public freeze commits:

- [LS8AF headers 35693119811](https://github.com/andersenmartin-blip/setisearch/actions/runs/35693119811).
- [LS8AF L2 screen/audit 35693458369](https://github.com/andersenmartin-blip/setisearch/actions/runs/35693458369).
- [LS8AG image metadata/joins 35693709166](https://github.com/andersenmartin-blip/setisearch/actions/runs/35693709166).
- [LS8AG image diagnostic/audit 35693927486](https://github.com/andersenmartin-blip/setisearch/actions/runs/35693927486).
- [LS8AH residual/noise study 35694203227](https://github.com/andersenmartin-blip/setisearch/actions/runs/35694203227).

All eight archive URL resolutions succeed on their first attempt. All three
image/smearing range requests also succeed on their first attempt. The residual
stage accesses retained inputs only. No source substitution, archive transport
recovery or scientific rerun occurs.

## Exact verification scope

The 5 transport and 2 stable L2 tests pass. The independent L2 audit passes
**1,980 numerical/discrete comparisons**. Image metadata passes **58 unique
joins and 269 exact checks** before pixels. All 9 inherited image tests pass
before payload, and the image audit passes **94,537 numerical comparisons
and 160,581 exact checks**. All 18 inherited residual tests pass before
native calculations; the residual audit passes **305,224 numerical
comparisons and 320,118 exact checks**, with zero disagreements. Its maximum
numerical difference uses **0.000228573780** of the frozen allowed tolerance.
All 24 signed known-template, 40 compact and 64 additive checks pass.
All three figures were visually inspected.

All 28 header, 22 L2, 57 image-metadata and 18 residual manifest entries
are locally SHA256/Git-identity verified, together with their manifests.
The future-image config and all new source files are also verified. Of 22
image-result entries, 20 are locally verified. The two compressed CAL/COR
cubes below were not additionally copied locally. Both successful scientific
workflows verify their manifest/raw digests and independently decode native
values. The public inputs and exact receipts remain part of the result.

| Compressed input | Git blob identity | Compressed SHA256 | Raw SHA256 |
|---|---|---|---|
| TG000901_P0/SCI_CAL_SubArray.bin.gz | `a0fbe1c54377a32f5d2f71fd028b6f89ebc523e3` | `4b92c6148d6ed1d278118c048b418e47afccade9a30b92ad832eae2acf28272c` | `4c341240beeb94a051df7023ffc520144b279d60032889160481ebee227906e7` |
| TG000901_P0/SCI_COR_SubArray.bin.gz | `2ea9b4daa8c6bc47f2c082b7e54d038b0e61e0ab` | `d879d718dd47dcb36b222893c4c95e3cbf94782b659dc8ccb6508a91ad5478e5` | `153d73f68f69f8fb62344c90b41c30e40ee63c1af5fd86c2ef5d336a4e3c81f1` |

Additional local known-answer checks pass for all 5 transport, 2 L2 and
18 residual tests. The authoritative pinned image workflow runs all nine
image tests before pixels; no additional local native analysis was performed.
Unchanged L2 tolerances are relative 2e-8 / absolute 2e-10. Image and residual
tolerances remain relative 2e-8, native absolute 1e-6 and dimensionless
absolute 1e-8, with exact discrete checks. The independent image and residual
mathematical functions are AST-identical to their preceding adapters; source
paths and provenance names change without mathematical retuning.

The ten scientific commits add **180 files**, change no earlier blob and
remove no earlier file. Exactly **178** match locally calculated Git blob
identities; the remaining two are identified above.
Final scientific tree: `9ea40647b75262cb29f787aca35d260bbde783d0`.

The separate closure commit adds this record and LS8AH_CONTINUATION.md,
prepends the latest PROJECT_STATUS.md checkpoint, updates its current LS row
and appends the PROJECT_DIRECTION.md decision. The main README receives the
same conclusion and next action. Frozen scientific files and earlier history
are preserved.

## Scientific conclusion and restart

There is one positive cluster and zero negative crossings in 165 eligible
overlapping windows. TG000901_P0 is one 60-second exposure, score
+141.1054591837304, not Gaussian sigma. Its image label remains
UNRESOLVED_WITHIN_FIXED_SCOPE. The CAL/COR figure shows an extended stripe
at the aperture edge, without assigning a cause. The retained-data COR
residual/reference ratios are 278.663206/124.118239, with 0/24 held values
at least as large in each convention and 98.39%/97.84% of weighted residual
energy in the fixed outer ring. These descriptive values are not probabilities
or evidence of artificial origin. Hypothetical displacement subtraction
loses 42.99–43.53% of injected COR brightness flux and is not adopted.

The bounded PG 1207-033 study is closed. Next prepare **LS8AI, rank-11
EC13080-1508**, exact chronological pair CH_PR100002_TG005201_V0300 and
CH_PR100002_TG005202_V0300, beginning with its own metadata/header freeze.
Verify NEXP=1/60-second ledger values before separately freezing L2 bytes.
Those values remain unopened; the third eligible visit TG005203 remains
outside scope. No qualified candidate, detector or coverage is added.

[Full interpretation and exact continuation](LS8AH_CONTINUATION.md) ·
[L2 report](results_ls8af_l2_screen/REPORT.md) ·
[Image report and figure](results_ls8ag_images/REPORT.md) ·
[Residual report and figure](results_ls8ah_residuals/REPORT.md).
