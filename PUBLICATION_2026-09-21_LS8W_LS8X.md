# LS8W–LS8X publication and verification — 21 September 2026

Repository: `andersenmartin-blip/setisearch`; science branch:
`m43-support-qualification`. Standing owner authorization covers code,
protocols, data, results, logs and the README update on `main`.

## Immutable scientific sequence

| Stage | Commit | Result |
|---|---|---|
| LS8V documentation parent | `0a272628865396d354e72f9519d7b3a31b56fa7f` | Previous closed study retained |
| LS8W exact pair/header freeze | `13b1883b82b8e4178336e8b60390ef8474923d53` | Rank-6 GJ 436, zero science bytes authorized |
| Header result | `d4e4d2fd07d11c28e95bab3b495d9cf0152d6d04` | Both 60-second/NEXP=1 products compatible |
| L2 scope freeze | `95036f22c891e49e7355dc0893a469879850009d` | 88,320 exact table bytes; unchanged screen |
| Audited L2 result | `6038a0dfac58d9c74a6f88ce3afafda8eeffa1bf` | 640 rows, 936 windows, one positive representative |
| LS8X representative/metadata freeze | `62add7db6a5d6b244825f7f13d4e465935668985` | All representatives, metadata only |
| Audited image metadata result | `40cf5b1ad94d8397f3884bf790d0dd0dda4d3a7d` | 58 unique joins; exact future ranges |
| Image payload/diagnostic freeze | `947f46338b46ce10bef58b3b53f31b516b7f509f` | 18,560,000 image + 46,400 smearing bytes |
| Audited image result | `207e6b08e651ee42818d0e19dc9092710929ae94` | TG000302_P0: CORRECTION_LINKED |

All four workflows succeed:

- [LS8W header preflight 35625384783](https://github.com/andersenmartin-blip/setisearch/actions/runs/35625384783).
- [LS8W L2 screen and audit 35625861352](https://github.com/andersenmartin-blip/setisearch/actions/runs/35625861352).
- [LS8X image metadata and joins 35626390112](https://github.com/andersenmartin-blip/setisearch/actions/runs/35626390112).
- [LS8X image diagnostic and audit 35626841437](https://github.com/andersenmartin-blip/setisearch/actions/runs/35626841437).

All URL resolutions and science-range requests succeed on their first attempt.
The bounded URL-timeout helper is separately tested, retries only timeouts and
does not relax source identities, HTTP range contracts or scientific rules.
No failed scientific run or retuned result is omitted.

## Verification scope

The five URL-timeout tests and two stable L2 known-answer tests pass. The L2
audit independently decodes tables and passes **11,232 numerical/discrete
comparisons**. Nine inherited synthetic image tests pass before pixels in the
full workflow; this satisfies the gate despite the partial local checkout's
previously documented missing historical import. Image metadata passes
**58 joins and 269 exact checks** without pixels. The independent image audit
passes **94,537 numerical comparisons and 160,581 exact checks**. There are
no disagreements or tolerance changes.

All 28 L2 metadata, 22 L2 result and 57 image metadata manifest entries were
retrieved from their immutable commits and locally SHA256/Git-identity verified.
The image result has 22 manifest entries: 20 were likewise locally verified,
including the smearing input, maps, independent reference, audits, receipts,
logs and figure. The two larger compressed CAL/COR input files could not be
copied through the connector's binary response, which returned empty content
or an unsupported UTF-8 decode. They were not treated as empty scientific files.
The successful workflow independently checks both compressed and raw hashes,
decompresses them, verifies the exact ranges and decodes their float values
before reconstructing all maps and diagnostics. This local-copy limitation
does not affect the completed workflow audit.

| Retained compressed input | Git blob identity | Compressed SHA256 | Raw SHA256 |
|---|---|---|---|
| TG000302_P0/SCI_CAL_SubArray.bin.gz | `79cb3cb4896bdaa6d5f8ea70ef4a30c6731ea274` | `51de908b291ae9a62ef343bd7ffb903addb1b8c820a2bb7b1034a3eb4271a86f` | `01206893833a69b453dfa931fc5479f89e0aef222a363914ce465451fba509c9` |
| TG000302_P0/SCI_COR_SubArray.bin.gz | `61d8e7b3b9a77b8d569a579891e2690bc19c0bba` | `f0f7adce3e5af7648ed42ab94b8bd8a82979d9d194125c6ebc4dd351ea4c0069` | `8786e61031f508a44c327b47b667ac8f268c38a1cb199ed37c5db38605e9d181` |

Both files are under `results_ls8x_images/`. Their individual JSON receipts
retain successful HTTP 206, source ETags/filenames, byte counts and first-attempt
acquisition. The manifest and receipts agree. Both report figures passed
visual inspection; the image figure uses one common signed ADU scale and
shows both original aperture conventions.

The public comparison from the LS8V documentation parent through the LS8X
result contains **157 added files**, with no earlier file changed or removed.
Exactly **155** match locally calculated Git blob identities; the two remaining
public identities and workflow verification are explicitly recorded above.
The complete scientific result tree is
`95e07968d45638c2c7c8699349e77a79e9dda766`.

The subsequent editorial closure adds this record and LS8X_CONTINUATION.md,
prepends the latest PROJECT_STATUS.md checkpoint, updates its current LS row
and appends the PROJECT_DIRECTION.md decision. The main README receives the
same scientific conclusion and next action. These edits preserve all frozen
source files, data, reports, checksums and earlier history.

## Scientific state and next step

The sole positive 60-second event has original L2 score +9.634235209975396,
which is not Gaussian sigma. Both absolute DELTA/COR ratios exceed 2; the
negative DELTA reduces a larger positive CAL residual. CORRECTION_LINKED
describes material coupling to processing, not a proven physical cause or
artificial origin. No qualified candidate, detector or coverage is added.

Close the GJ 436 pair under its fixed stopping rule. Next prepare LS8Y for
rank-7 PG 1245-042, exact pair CH_PR100002_TG008601_V0300 and
CH_PR100002_TG008602_V0300, beginning with a separately frozen header preflight.
Those science values remain unopened. The earlier TESS_260647166 positive
remains unresolved; reserved panels remain closed and the separate calibration
request remains unsent.

[L2 result](results_ls8w_l2_screen/REPORT.md) ·
[Image result](results_ls8x_images/REPORT.md) ·
[Scientific interpretation and continuation](LS8X_CONTINUATION.md).
