# LS8AC–LS8AE publication and verification — 22 September 2026

Repository: `andersenmartin-blip/setisearch`; science branch:
`m43-support-qualification`. Standing authorization covers code, protocols,
data, results, logs and the README update on main.

## Immutable sequence

| Stage | Commit | Result |
|---|---|---|
| LS8AA–LS8AB closure parent | `64915731da3ce06a577f1438bb022fe15c883366` | Prior studies retained |
| LS8AC pair/header freeze | `479b7390da988917ebd18f78a8781ae085deb733` | Rank-9 pair, metadata only |
| Header result | `12cd274141861fd6ba7d7ec8add4ae549c93ff41` | 78/87 rows; NEXP=1, 60 seconds |
| L2 scope freeze | `125088a654731b9bd14c9f5a83841ede1d6165d2` | 22,770 exact table bytes |
| Audited L2 result | `289aae686b9503b555311d41f9306460d02d431a` | 165 rows, 222 windows, one negative cluster |
| LS8AD representative/metadata freeze | `e6a0b6b557b13c7c0ce6a80d4336186e90b76eba` | Complete signed set, metadata only |
| Audited image metadata | `ea62b2549ef31a725069a657b1ec620272af339b` | 58 unique joins and exact future ranges |
| Image payload/diagnostic freeze | `908c14f0ece6c51e0085e45e598d329346f0f3dd` | 18,560,000 image + 46,400 smearing bytes |
| Audited image result | `37a90e57be86e0e631417a8b0d2acb36bdcd7711` | Negative unresolved under fixed scope |
| LS8AE retained-data freeze | `6001b1351bb8b017b71e8e7ba4605f59c3f389e0` | One 60-second context; zero new archive bytes |
| Audited residual result | `0145b5a2f2eb953a6365ff2b8b7316eee8655cdf` | Four native / 96 held / 64 signed cases; bounded study closed |

All five workflows succeed:

- [LS8AC headers 35683438208](https://github.com/andersenmartin-blip/setisearch/actions/runs/35683438208).
- [LS8AC L2 screen/audit 35683620732](https://github.com/andersenmartin-blip/setisearch/actions/runs/35683620732).
- [LS8AD image metadata/joins 35683864823](https://github.com/andersenmartin-blip/setisearch/actions/runs/35683864823).
- [LS8AD image diagnostic/audit 35684105814](https://github.com/andersenmartin-blip/setisearch/actions/runs/35684105814).
- [LS8AE residual/noise study 35684448087](https://github.com/andersenmartin-blip/setisearch/actions/runs/35684448087).

All eight archive URL resolutions succeed on their first attempt.
All three image/smearing range requests also succeed on their first attempt.
The residual stage accesses retained inputs only. No source substitution,
archive transport recovery or scientific rerun occurs.

## Exact verification scope

The 5 transport and 2 stable L2 tests pass. The independent L2 audit passes
**2,664 numerical/discrete comparisons**. Image metadata passes **58 unique
joins and 269 exact checks** before pixels. All 9 inherited image tests pass
before payload, and the image audit passes **94,537 numerical comparisons
and 160,581 exact checks**. All 18 inherited residual tests pass before
native calculations; the residual audit passes **305,356 numerical
comparisons and 320,126 exact checks**, with zero disagreements. Its maximum
numerical difference uses 0.000034725 of the frozen allowed tolerance.
All 24 signed known-template, 40 compact and 64 additive checks pass.
All three figures were visually inspected.

All 28 header, 22 L2, 57 image-metadata and 18 residual manifest entries
are locally SHA256/Git-identity verified, together with their manifests.
The image config and all new source files are also verified. Of 22 image
result entries, 20 are locally verified. The two compressed CAL/COR cubes
below were not additionally copied locally. Both successful scientific
workflows verify their manifest/raw digests and independently decode the
native values. Their public files and exact acquisition receipts remain
part of the reproducible result.

| Compressed input | Git blob identity | Compressed SHA256 | Raw SHA256 |
|---|---|---|---|
| TG006402_N0/SCI_CAL_SubArray.bin.gz | `bbc02aeaf5053a3b5d82a4e79e9e180f06a854b6` | `dc4d6a631473c7b235e0c11f3c0a9809894b7e412ca2932fe62013089590f2e8` | `4965d17bfec3a70a175b34a10333c65a3114ae3d66b5ac77ffcb90d101fc19d9` |
| TG006402_N0/SCI_COR_SubArray.bin.gz | `1db04e916b83b5cbac097b6228cb888f9619c0ac` | `d7163911df4993f6b5a6d714b6969df4f67b3582d1323e8af034e04d1fa33246` | `bee6e355cdfe8f0758f7d6aceb30b6c17a8fcbf52baee78b315712282fc4c10c` |

Additional local synthetic checks pass for the transport, L2 and residual
suites. The optional local image suite could not complete in the partial
workspace: its first attempt lacked a historical audit module; restoring
that source exposed a missing Astropy installation. No native analysis
occurred in those local attempts. The authoritative pinned image workflow
runs all nine tests successfully before image access. Its evidence is retained
in results_ls8ad_images/ls8ad_tests.log.

Unchanged L2 tolerances are relative 2e-8 / absolute 2e-10.
Image and residual tolerances are relative 2e-8, native absolute 1e-6 and
dimensionless absolute 1e-8, with exact discrete checks. The LS8AE independent
mathematical functions are AST-identical to LS8U; source paths, provenance
names and case counts change without mathematical retuning.

The ten scientific commits add **180 files**, change no earlier blob and
remove no earlier file. Exactly **178** match locally calculated Git blob
identities; the remaining two are identified above.
Final scientific tree: `d6d54b43ed2a72feb43e7dcdb2a2f0e5445f9312`.

The separate closure commit adds this record and LS8AE_CONTINUATION.md,
prepends the latest PROJECT_STATUS.md checkpoint, updates its current LS row
and appends the PROJECT_DIRECTION.md decision. The main README receives the
same conclusion and next action. Frozen scientific files and earlier history
are preserved.

## Scientific conclusion and restart

There are **zero positive crossings** in the 222 eligible overlapping windows.
The single negative retains UNRESOLVED_WITHIN_FIXED_SCOPE. Its COR modeled
residual/reference energy is 0.876726–0.878666; 19/24 and 20/24 held controls
are at least as large. This does not identify its cause or supply a calibrated
false-alarm probability. Hypothetical displacement subtraction loses
38.17–38.23% of injected COR brightness flux and is not adopted.

The bounded PG1303-114 study is closed. Next prepare **LS8AF, rank-10
PG 1207-033**, exact chronological pair CH_PR100002_TG000901_V0300 and
CH_PR100002_TG000902_V0300, beginning with its own metadata/header freeze.
Verify the NEXP=1/60-second ledger values before separately freezing L2 bytes.
Those science values remain unopened; PG1303-114's three later eligible
visits remain outside scope. No new candidate, detector or coverage is added.

[Full interpretation and exact continuation](LS8AE_CONTINUATION.md) ·
[L2 report](results_ls8ac_l2_screen/REPORT.md) ·
[Image report](results_ls8ad_images/REPORT.md) ·
[Residual report and figure](results_ls8ae_residuals/REPORT.md).
