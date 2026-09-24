# LS8BD–LS8BE publication and verification — 24 September 2026

The rank-23 GJ 494 first pair and its complete signed-event follow-up are
complete and closed. There are 148 retained rows, 165 eligible overlapping
windows and one positive representative, classified CORRECTION_LINKED under
the unchanged two-convention gate. The unresolved set is empty; no residual
study or qualified candidate/detector is added.
[Interpretation and exact continuation](LS8BE_CONTINUATION.md).

## Immutable sequence

| Stage | Commit | Content |
|---|---|---|
| Inherited LS8BC closure | `5682ab2ea03835f4b945a95511fb976b768e5579` | GJ 422 closed; exact GJ 494 first pair next |
| BD header freeze | `c536c25eea1cc0609fd3158ffb5c80e71392da4c` | Pair, 42-second exposure encoding and independent header auditor before access |
| BD header result | `c258bb317464ebeae6b96dc2729ff8aa3df1942e` | Identities, complete schemas, rows, exposures and receipts |
| BD L2 freeze | `905b30a6800a804eef5862e8924636141444306f` | Header audit PASS and exact 20,424-byte scope before values |
| BD audited L2 result | `a5a3fd0e1678c2e77d505d9fac209e1cba55f9a9` | Both full tables, all windows and signed clusters, scalar audit and figure |
| BE metadata freeze | `5fcf8e4e89cc06b68493203fb25eba03e2dc6fad` | Complete signed set and independent join/image auditor before metadata |
| BE metadata result | `0bfee749d24f5a65f8bb93e014ad6b578e3bb851` | 58 unique CAL/COR exposure joins and exact future ranges; pixels closed |
| BE image freeze | `a2b1b19a49b37b5e1b2bac5e64e62105c23e6352` | Exact full context, unchanged gates and tolerances before pixels |
| BE audited image result | `8f376712060244153b92ee462d7f54115ac8d58f` | CORRECTION_LINKED outcome, retained ranges/maps and independent reconstruction |

Final scientific tree: `01b32ffec5ab4b75c1e07fc738e76cb9a8469e92`.
The eight commits add **157 scientific files** and modify/remove no inherited
file. The public compare and independently reconstructed local Git trees and
commit identities agree. Missing large raw blobs are preserved by their
public object identities, not replaced with empty files.

Editorial closure adds this record, LS8BE_CONTINUATION.md, release/scope
verification and code, prefixes PROJECT_STATUS.md and appends
PROJECT_DIRECTION.md. Main README receives the current result and next
action while preserving dated history. Scientific branch:
`m43-support-qualification`. Standing publication authorization applies.

## Terminal execution evidence

| Workflow | Run | Conclusion | Exact trigger |
|---|---|---|---|
| BD own headers | [35954832979](https://github.com/andersenmartin-blip/setisearch/actions/runs/35954832979) | completed / success | `c536c25eea1cc0609fd3158ffb5c80e71392da4c` |
| BD L2 and scalar audit | [35954988639](https://github.com/andersenmartin-blip/setisearch/actions/runs/35954988639) | completed / success | `905b30a6800a804eef5862e8924636141444306f` |
| BE metadata and joins | [35955233577](https://github.com/andersenmartin-blip/setisearch/actions/runs/35955233577) | completed / success | `5fcf8e4e89cc06b68493203fb25eba03e2dc6fad` |
| BE native images and independent audit | [35955467380](https://github.com/andersenmartin-blip/setisearch/actions/runs/35955467380) | completed / success | `a2b1b19a49b37b5e1b2bac5e64e62105c23e6352` |

All four runs succeed at their original freezes. No scientific failure or
result-dependent rerun occurred. All eight bounded URL resolutions and all
three image/smearing ranges succeed on their first attempt. Five transport,
two stable L2 and eleven image tests pass before corresponding calculations.

## Independent verification

| Audit | Numerical/discrete comparisons | Exact checks | Disagreements |
|---|---:|---:|---:|
| BD L2 scalar reconstruction | 1980 | included | 0 |
| BE exposure metadata | — | 269 | 0 |
| BE native image reconstruction | 94537 | 160581 | 0 |

The independent scalar FITS-card auditor verifies each full 18-column,
138-byte-row schema, product identity, receipt, boundary and exposure tuple:
NEXP=1, EXPTIME=TEXPTIME=42 seconds, pipeline 14.1.2, prospective binary32
encoding `42280000`. L2 tolerances remain relative 2e-8 / absolute 2e-10.
Image tolerances remain relative 2e-8 / native absolute 1e-6 / dimensionless
absolute 1e-8. All 68 input-pin checks pass. Independent image mathematical
functions remain AST-identical to LS8BB; the image core is unchanged.

All **155 locally available scientific files** match public Git identities
and SHA256. Two large compressed CAL/COR ranges return empty contents fields
through the local connector and cannot be verified locally. Their public
Git IDs, raw/compressed hashes and exact ranges are preserved below and in
the release record. The published independent image audit verifies both
payloads and reconstructs every map, fit and classification from them.

| File under results_ls8be_images/TG007401_P0/ | Public Git blob | Raw bytes |
|---|---|---:|
| SCI_CAL_SubArray.bin.gz | `5f417b03ebf05cd0ba31b7c976be56770f72c832` | 9280000 |
| SCI_COR_SubArray.bin.gz | `31fb0fc5365295df16142775b06bc68d82914b70` | 9280000 |

| Manifest | Entries | Verified locally | Verified in published independent CI audit, unavailable locally |
|---|---:|---:|---:|
| BD headers | 28 | 28 | 0 |
| BD L2 | 22 | 22 | 0 |
| BE metadata | 57 | 57 | 0 |
| BE images | 22 | 20 | 2 |
| Total | **129** | **127** | **2** |

All three source receipts match frozen identities and ranges. The smaller
smearing payload also passes local compressed/raw hash and length checks.
No additional archive bytes or scientific fit were needed for release
verification. The complete L2 figure and original common-scale image figure
were visually inspected; neither original figure/result was modified.
No optional artifact download or local verification of the two missing raw
payloads is claimed.

See [public file inventory](verification_ls8be/public_file_inventory.json),
[workflow evidence](verification_ls8be/workflow_runs.json),
[release verification](verification_ls8be/release_verification.json) and
[eligible scope](verification_ls8be/eligible_scope.json). Reproduce the
retained local/CI-evidence checks with `python scripts/ls8be_release_verify.py`.
This command reports the distinction between local verification and published
CI evidence; it does not contact the archive or rerun native science.

## Acquisition and stopping

| Scope | Bytes acquired |
|---|---:|
| BD bounded L2 headers | 40320 |
| BD two exact L2 tables | 20424 |
| BE CAL/COR headers and exposure metadata | 119766 |
| BE native CAL/COR context | 18560000 |
| BE smearing context | 46400 |
| Release/scope bookkeeping | 0 new archive bytes |

One 29-row context contains 29 distinct L2 exposures and 58 CAL/COR product
exposures; there are no duplicated representative contexts. The original
positive L2 excess is +0.433469321% in a 42-second integration. Both complete
apertures preserve the positive sign. DELTA/COR is -3.496853 / -3.694644,
passing the first fixed gate. Later displacement thresholds would also pass,
without relabeling. Smearing fits are rank deficient. The signed image
structure and correction coupling establish neither a unique cause nor
artificial origin and do not exclude underlying source variability.

The second visit's row-13 maximum has no eligible context and remains
unassessed. It is not substituted for the selected first-visit event. Both
later GJ 494 visits remain outside the pair. There are no unresolved
representatives and no residual study is triggered.

**Next: LS8BF, rank-24 2MASS J11474440+0048164**, exact pair
CH_PR100018_TG007101_V0300 / CH_PR100018_TG007102_V0300. Own-header checks and
a separate L2 freeze precede values; the ledger gives 60 seconds, which
must be verified independently. Prior labels, unassessed points, closed
studies, census/cohort order and reserved TESS/M43 panels remain unchanged.
Calibration NOT_READY; request UNSENT; delegation deferred.
