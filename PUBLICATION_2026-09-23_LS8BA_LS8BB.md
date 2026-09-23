# LS8BA–LS8BB publication and verification — 23 September 2026

The rank-21 2MASS J11285624+1010395 pair and every original signed representative
are complete and closed. Both events are CORRECTION_LINKED under the fixed
two-convention gate. The second visit has zero eligible windows and supplies
no tested null. No qualified SETI candidate, detector, sensitivity or observing
coverage is added. [Interpretation and exact continuation](LS8BB_CONTINUATION.md).

## Immutable sequence

| Stage | Commit | Content |
|---|---|---|
| Inherited LS8AX–LS8AZ closure | `dcb61841485349e90d3e221ba749f9da1f000e63` | Parent before this cohort's access |
| BA header freeze | `33b40d51da6f6dda5c46e403610c3f77cdea1886` | Exact pair, bounded reader and independent auditor before headers |
| BA header result | `1c8cce6b2f52c99589841b3edd3272cc107d97cd` | Own identities, complete schemas, rows, exposure tuples and receipts |
| BA L2 freeze | `b3bc02afda0e468e8ebb6b78c53c748823d9fdc7` | Scalar header PASS and exact 13,386-byte scope before values |
| BA audited L2 result | `f2fd067eec26e3d3b3002e14c3c2e616f8433675` | Both full tables, all eligible signed windows and independent audit |
| BB metadata freeze | `e675b980d999baf062ceb73eea088058f7169141` | Complete P0/N0 set and independent audit code before image metadata |
| BB metadata result | `e9389d961e98879e8203f26daf18aebece352b48` | Exact exposure joins, sources and future ranges; pixels closed |
| BB image freeze | `90a4e7c81fe02c08b9ddfb0761de364e5f14d76a` | Fixed CAL/COR/smearing ranges and unchanged gates before pixels |
| BB audited image result | `0031edaebfcb221bd9b381fb524ace39d3f91342` | Both original signs CORRECTION_LINKED; independent reconstruction |
| BB retained verification freeze | `e665e67113b5232fd5e6e4fdb502c2a4f438b14e` | Pinned retained bytes, exact overlap check and layout-only overview |
| BB retained verification result | `49e18596abfdc291f55d7cb36283febffda70021` | All receipts/overlaps PASS and unchanged-map overview |

Image-result tree: `432aca8c4b6d6f96e9773b5597a8c7cc4cae33dc`.
Final retained-verification tree: `c1b090f99ece38060789593f4d07b38bb7ce0ea3`.
Ten commits after the inherited closure add **175 files** and change/remove no
inherited file. The retained check adds no archive bytes or native fitting.
No original scientific output is overwritten.

Editorial closure adds this publication, LS8BB_CONTINUATION.md and the release
verification, prefixes PROJECT_STATUS.md and appends PROJECT_DIRECTION.md.
Main README receives the current result/next action while keeping dated history.
The science branch is `m43-support-qualification`.

## Terminal workflow evidence

| Workflow | Run | Verified conclusion | Exact trigger |
|---|---|---|---|
| BA own headers | [35889131789](https://github.com/andersenmartin-blip/setisearch/actions/runs/35889131789) | completed / success | `33b40d51da6f6dda5c46e403610c3f77cdea1886` |
| BA L2 screen and scalar audit | [35889780292](https://github.com/andersenmartin-blip/setisearch/actions/runs/35889780292) | completed / success | `b3bc02afda0e468e8ebb6b78c53c748823d9fdc7` |
| BB metadata and joins | [35890597351](https://github.com/andersenmartin-blip/setisearch/actions/runs/35890597351) | completed / success | `e675b980d999baf062ceb73eea088058f7169141` |
| BB native images and independent audit | [35891220941](https://github.com/andersenmartin-blip/setisearch/actions/runs/35891220941) | completed / success | `90a4e7c81fe02c08b9ddfb0761de364e5f14d76a` |
| BB retained bytes and figure | [35892887328](https://github.com/andersenmartin-blip/setisearch/actions/runs/35892887328) | completed / success | `e665e67113b5232fd5e6e4fdb502c2a4f438b14e` |

All four data-reading/analysis workflows and the one retained-file workflow
succeed at their original freezes. There is no scientific failure or
result-dependent rerun in this cohort. Previous AX checkout failure and older
scientific failures remain preserved in their original records.

## Tests, independent audits and fixed identities

The **5 transport / 2 stable L2 / 11 image tests** pass before corresponding
data calculations. Independent scalar FITS-card decoding verifies both complete
18-column, 138-byte-row schemas, identities, full exposure values and receipts
without producer imports. Both NEXP=1 / EXPTIME=TEXPTIME=60 s tuples pass the
prospective ledger binary32 check (`42700000`), with pipeline 14.1.2.

| Independent audit | Comparisons | Exact checks | Disagreements |
|---|---:|---:|---:|
| BA L2 scalar reconstruction | 1080 numerical/discrete | included | 0 |
| BB exposure joins | — | 534 | 0 |
| BB native image reconstruction | 189074 numerical | 321158 | 0 |

The second visit's empty eligible set and signed clusters are verified; it has
no numerical event comparisons. Tolerances remain L2 relative 2e-8 / absolute
2e-10, and images relative 2e-8 / native absolute 1e-6 / dimensionless absolute
1e-8. The image core remains SHA256
`54255f3b8a21ebb4c279243ce152b1501549f588630833d862657bc96131463f`.
All 14 L2, 11 representative-scope and 33 payload-scope input pins match.

The final independent public compare and local Git tree agree on all 175 added
paths. **171 locally available files match their public Git blob identities and
SHA256.** Four compressed CAL/COR range files exceed the connector contents
payload limit and have not been downloaded locally. Their exact public blob
identities, packed/raw hashes and byte counts are preserved in
[release verification](verification_ls8bb/release_verification.json). They pass
both the published independent image audit and the later frozen retained-data
manifest, raw-receipt and byte-overlap checks. This is explicit CI verification,
not a claim that all raw payloads were locally checked.

| Manifest | Entries | SHA256 verified locally | Verified in published CI, unavailable locally |
|---|---:|---:|---:|
| BA headers | 28 | 28 | 0 |
| BA L2 | 22 | 22 | 0 |
| BB metadata | 57 | 57 | 0 |
| BB images | 31 | 27 | 4 |
| BB retained verification | 5 | 5 | 0 |
| Total | **143** | **139** | **4** |

All six image/smearing gzip and raw receipts pass in the frozen retained check;
both smaller smearing payloads are also decompressed and checked locally. All
three 28-row overlaps are byte-exact. The public retained summary includes the
shared-byte hashes. No additional archive access or native fit was performed.

## Acquisition accounting and local transport limit

| Acquisition | Bytes actually read, including repeated contexts |
|---|---:|
| BA bounded L2 headers | 40320 |
| BA two exact science tables | 13386 |
| BB bounded CAL/COR headers and metadata | 110118 |
| BB CAL/COR image contexts | 37120000 |
| BB smearing contexts | 92800 |
| Later retained verification | 0 new archive bytes |

Metadata ranges match local bytes, source hashes and HTTP 206 receipts. All
eight bounded URL-resolution requests succeed on their first attempt. All six
image/smearing ranges succeed on their first attempt with no prior transport
failure. Two overlapping 29-row contexts account for 58 row occurrences but
only 30 distinct exposures. The distinct image union is 19,200,000 bytes and
the distinct smearing union 48,000 bytes. The 116 join occurrences cover only
60 distinct CAL/COR exposure rows. These are not independent repeats.

Local Git refresh was unavailable. Approved connector reads and exact offline
reconstruction verified every new public tree and commit identity, while
preserving the four missing large blobs by their public IDs. The published
branch remains authoritative. The optional Actions artifact was successfully
uploaded (ID 10765400729, 23,078,602 bytes; service-reported SHA256
`3d0e225fe71c188d35e3a8906f38cbff5ca99d683861fbdb7276101bf42039c4`).
Its returned local download gave HTTP 403. No ZIP bytes or local ZIP checksum
are claimed, and no temporary signed URL is published. The retained CI check
uses the already public files and does not depend on this optional artifact.

## Visual review and exact continuation

All **four figures** were visually inspected: the complete L2 screen, both
original CAL/COR/DELTA figures and the combined retained-map overview. The
overview fixes crowded axis labels using unchanged native maps, scales and
apertures. Broad predominantly negative DELTA structure and signed source
features are visible; no unique physical cause is assigned. The first visit's
large unassessed edge point and the second visit's zero eligibility are retained.

Both original labels stay CORRECTION_LINKED. The unresolved set is empty and
no residual study is triggered. Close this pair without widening. **Next:
LS8BC, rank-22 GJ 422**, exact pair CH_PR100018_TG012201_V0300 /
CH_PR100018_TG012202_V0300. Own-header verification precedes its separately
frozen L2 scope; its science values remain unopened.

The complete 1,000-row census / 452 eligible visits / 107-cohort order still
matches the independent reconciliation. Prior labels, unassessed points and
closed studies stay unchanged. Calibration NOT_READY; request UNSENT.
Standing publication authorization continues; delegation is deferred.
