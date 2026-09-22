# LS8AL–LS8AN publication and verification — 22 September 2026

The rank-13 HD 106315 screen, complete signed image follow-up and one bounded
retained-data study are complete. All three original positive labels remain
UNRESOLVED_WITHIN_FIXED_SCOPE, and the bounded study is closed. The exact
results, limits and next action are in LS8AN_CONTINUATION.md.

## Immutable scientific sequence

| Stage | Commit |
|---|---|
| Inherited LS8AK closure | [168883e39bd65abd82e9423e9ec81c729e9cc481](https://github.com/andersenmartin-blip/setisearch/commit/168883e39bd65abd82e9423e9ec81c729e9cc481) |
| LS8AL pair/header freeze | [6840dc50cf06e552ef6c24fb4533db7813bd45f5](https://github.com/andersenmartin-blip/setisearch/commit/6840dc50cf06e552ef6c24fb4533db7813bd45f5) |
| LS8AL header result | [f7ca069560b1ca38c32c0b2feef8749496b1467d](https://github.com/andersenmartin-blip/setisearch/commit/f7ca069560b1ca38c32c0b2feef8749496b1467d) |
| LS8AL exact L2 freeze | [cb8adaf38d69bba75928cd2572d34b0e6df2b53f](https://github.com/andersenmartin-blip/setisearch/commit/cb8adaf38d69bba75928cd2572d34b0e6df2b53f) |
| LS8AL audited L2 result | [36d081fac65ca35bccbfde5220660fd547d44bc9](https://github.com/andersenmartin-blip/setisearch/commit/36d081fac65ca35bccbfde5220660fd547d44bc9) |
| LS8AM representative/metadata freeze | [a6fc2353a4e9bd4dd81bc919b219c2f99a84d507](https://github.com/andersenmartin-blip/setisearch/commit/a6fc2353a4e9bd4dd81bc919b219c2f99a84d507) |
| LS8AM audited metadata result | [b62a0c945c47ad40a0fcc42b21ad6c1f2ca8f3d8](https://github.com/andersenmartin-blip/setisearch/commit/b62a0c945c47ad40a0fcc42b21ad6c1f2ca8f3d8) |
| LS8AM exact image freeze | [3d85939564b715a8622d0ba470a6811a47e61242](https://github.com/andersenmartin-blip/setisearch/commit/3d85939564b715a8622d0ba470a6811a47e61242) |
| LS8AM audited image result | [b1e41666134779895f8ed643ddb71e00b74a0816](https://github.com/andersenmartin-blip/setisearch/commit/b1e41666134779895f8ed643ddb71e00b74a0816) |
| LS8AN retained-data freeze | [d8863681d322ecf03c4a00240fd544f5066fd8c7](https://github.com/andersenmartin-blip/setisearch/commit/d8863681d322ecf03c4a00240fd544f5066fd8c7) |
| LS8AN audited residual result | [0e18b1b599755a639fb2ac995c048d9f3dfbe2d4](https://github.com/andersenmartin-blip/setisearch/commit/0e18b1b599755a639fb2ac995c048d9f3dfbe2d4) |

The final scientific tree is 18cb0b29230dd28546964c88d8539572ad7e45f4.
The ten scientific commits add **253 files**, with
no earlier file changed or removed. Exactly **247** match
locally recomputed Git blob identities; the record below identifies the scope
of additional local-copy limitations. The complete scientific files are public.

## Successful workflows and tests

| Workflow | Run | Verified conclusion |
|---|---|---|
| LS8AL headers | [35755759497](https://github.com/andersenmartin-blip/setisearch/actions/runs/35755759497) | completed / success |
| LS8AL L2 screen/audit | [35756158854](https://github.com/andersenmartin-blip/setisearch/actions/runs/35756158854) | completed / success |
| LS8AM image metadata | [35756858734](https://github.com/andersenmartin-blip/setisearch/actions/runs/35756858734) | completed / success |
| LS8AM image diagnostic/audit | [35757332060](https://github.com/andersenmartin-blip/setisearch/actions/runs/35757332060) | completed / success |
| LS8AN residual/noise study | [35758750779](https://github.com/andersenmartin-blip/setisearch/actions/runs/35758750779) | completed / success |

All 5 transport and 2 stable L2 tests pass before their acquisitions.
The L2 audit passes 56,376 numerical/discrete comparisons. Image metadata
passes 174 unique joins and 803 exact checks before pixels. All 9 inherited
image tests pass before payload; its independent audit passes 283,611 numerical
comparisons and 481,739 exact checks. All 18 inherited residual tests pass
before native calculations; the independent residual audit passes
916,452 numerical comparisons and 960,362 exact
checks, with zero disagreements. The maximum residual-audit error uses
0.000876752721524 of the frozen tolerance.
All 72 signed known-template controls, 120 compact controls and 192 additive
checks pass. All seven figures were visually inspected.

L2 tolerances remain relative 2e-8 / absolute 2e-10. Image and residual
tolerances remain relative 2e-8, native absolute 1e-6 and dimensionless absolute
1e-8, with exact discrete checks. The independent image and residual mathematical
functions remain AST-identical to their preceding adapters. The metadata-set
41-second cadence, routing, provenance names and fixed case counts change;
no mathematical function, threshold, aperture or tolerance is retuned.

## Acquisition and verification scope

Both visits individually verify NEXP=1, EXPTIME=TEXPTIME=41 seconds and
pipeline 14.1.2. Each L2 preflight reads 20,160 header bytes within its
64-KiB budget, with no values. A subsequent exact-range freeze authorizes
120,336 + 208,380 = **328,716 L2 science bytes**. Separate image-metadata
acquisition reads **1,130,364 header/metadata bytes across four products** and
zero pixels. The next public freeze authorizes **55,680,000 paired-image
bytes plus 139,200 smearing bytes**. The residual study reads the retained
CAL/COR bytes only, with **zero new archive/source bytes**.

All 12 archive URL resolutions succeed on their first attempt. All nine
image/smearing requests also succeed on their first attempt. No source
substitution, scientific rerun, archive retry or changed scope occurs.
The image workflow's initial checkout takes several minutes; it subsequently
completes its tests, acquisition and independent audit successfully.

All 28 L2-header, 22 L2-result and 104 image-metadata manifest entries are
locally SHA256/Git verified, together with their manifests and the future-image
config. Of 40 image-result manifest entries, 34 are additionally verified
locally. The six larger compressed CAL/COR inputs below were not additionally
copied locally: the connector returned their identities without binary content.
The image and residual workflows each verify their complete manifests/raw
digests and independently decode the retained native values. This is a local
retrieval limitation; the original public inputs and receipts remain complete.

| Compressed input | Git blob identity | Compressed SHA256 | Raw SHA256 |
|---|---|---|---|
| TG000801_P0/SCI_CAL_SubArray.bin.gz | d56b0a119dddac617ed2c2b1dd497825adbf23f2 | 7ddaff6ad0f7dd244435b96ce75ba549c32359c89657d3370614ef69026e42ac | f3523e58af0eb46e256b863ac5af2c0c54629b53877f89450756364bab61ea90 |
| TG000801_P0/SCI_COR_SubArray.bin.gz | 2a9160625bc846c60f1af2299cd5b26013642563 | b8343d4a020c8d9f82476264b509a35eecd53b442f19d9f2eeea451fc1ebec57 | 628b3bf251d0ecaaf8df21f7d28b96600d779c5f10808b45a50bcba0a09090fd |
| TG000801_P1/SCI_CAL_SubArray.bin.gz | 47527d168a5c04f967329b47b92c520eb4e14974 | f3629aa90e1ae30981cb7bd7b5eee09be9a02a6502180527a6f5d971654e29bf | e1201ff28abba3b4de5e57077ca9a1ffbae2b9626ef5956ac987c8cd1d8d7479 |
| TG000801_P1/SCI_COR_SubArray.bin.gz | 4c052f959be7624ce0c030a8eb0eb966d41f97ec | 12129a553240cbbd1f1ef4f59bf2e14d37f062ca1ae79f46dec56a3ffdf2b9fb | 9558c9df191a8b48bfa4d0ec35c723eaa738a602f1ef017352cafb8eee0a8462 |
| TG001401_P0/SCI_CAL_SubArray.bin.gz | 6acc1e02650be67f91a0679c9aacfeba75455370 | 4f17ca15ed4dff1701f691fc4bce77baef0f506e51a11d9d5d242bb43efe0cb7 | 2d3c6c5e6a4bfedc0cd7fdae7d80e84c31bc764badb2948d249702dde53f2a1a |
| TG001401_P0/SCI_COR_SubArray.bin.gz | 2edfa21a04263ae4feb781e5d4436121ad56c9d7 | 1585ae2550787668aa9273afaf3571ebc0a7097a31f3d988efb8dc2791d15438 | 105a612fb7742c42e16d5eb60fd7ff5ecd90a072c10d2e6abdf5c90f6954c315 |

All 26 of
26 residual manifest entries additionally pass
local SHA256 verification, plus the manifest's Git identity. The five larger
residual JSON files were retrieved through their exact Git blob identities
after the contents-file interface could not supply them; their complete bytes
match the public Git identities and SHA256 manifest. All new
code/config/protocol/workflow files are locally Git-identity verified.

The large inherited reconciliation JSON was not recopied locally during this
turn. Its original SHA256 pin is preserved; the successful header workflow
verifies that complete file and equality of all 107 original/reconciled cohorts
before new headers. The target order is not reconstructed from partial data.

## Editorial closure and next action

The separate closure adds this record and LS8AN_CONTINUATION.md, prefixes the
current PROJECT_STATUS.md checkpoint, updates its current LS row and appends
PROJECT_DIRECTION.md. The main README receives the same result and next action.
Earlier dated history and all frozen scientific files are preserved.

The three positives retain their original unresolved labels and the bounded
HD 106315 study is closed. No hypothetical subtraction, new cut, qualified
candidate, detector, sensitivity or coverage is adopted. Next prepare LS8AO
for the rank-14 WASP-103 chronological pair, beginning with its own header
freeze and independent exposure verification. Its science values remain unopened.

[Scientific interpretation and exact continuation](LS8AN_CONTINUATION.md),
[L2 report and figure](results_ls8al_l2_screen/REPORT.md),
[image report and all three figures](results_ls8am_images/REPORT.md),
[residual report and all three figures](results_ls8an_residuals/REPORT.md),
[publication identities and verification](PUBLICATION_2026-09-22_LS8AL_LS8AN.md).
