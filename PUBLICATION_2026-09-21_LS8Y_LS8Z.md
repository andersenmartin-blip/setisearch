# LS8Y–LS8Z publication and verification — 21 September 2026

Repository: `andersenmartin-blip/setisearch`; science branch:
`m43-support-qualification`. Standing authorization covers code, protocols,
data, results, logs and the README update on main.

## Immutable sequence

| Stage | Commit | Result |
|---|---|---|
| LS8W–LS8X closure parent | `3d1081ecce68467fa982f13a4d7440679276a3f0` | Previous closed study retained |
| LS8Y exact pair/header freeze | `32fb831f02cec5bea3f8d2c35d22f5eefaa73e92` | Rank-7 pair, no science values |
| Header result | `7bea9c90c40fb36fa75f2826fbc2e6e51f70555c` | 85/79 rows; 60 seconds/NEXP=1 |
| L2 scope freeze | `5918f923186e0006a14a91330eefde33732a6c46` | 22,632 exact table bytes; unchanged screen |
| Audited L2 result | `588398eacf6316324d24954150b57e69422f2d0a` | 164 rows, 228 windows, one negative cluster |
| LS8Z representative/metadata freeze | `a4256a35cfc7c983297c6d8802932d8fa7b7a6af` | Complete signed set, metadata only |
| Audited image metadata | `f74c8d4834e2b4e40a6cdedc039d29dfc067945c` | 58 unique joins; exact future ranges |
| Image payload/diagnostic freeze | `d3f719b99010e4cad00c3178d8e1dc7201752d50` | 18,560,000 image + 46,400 smearing bytes |
| Audited image result | `320d6b9e326d54294d6f58009aa297b0648b5afe` | TG008601_N0: CORRECTION_LINKED |

All four workflows succeed:

- [LS8Y headers 35631863442](https://github.com/andersenmartin-blip/setisearch/actions/runs/35631863442).
- [LS8Y L2 screen/audit 35632212818](https://github.com/andersenmartin-blip/setisearch/actions/runs/35632212818).
- [LS8Z metadata/joins 35632860622](https://github.com/andersenmartin-blip/setisearch/actions/runs/35632860622).
- [LS8Z image diagnostic/audit 35633541939](https://github.com/andersenmartin-blip/setisearch/actions/runs/35633541939).

All eight header/L2/image-metadata/image URL resolutions succeed on their
first attempt. All three image/smearing range requests also succeed on their
first attempt; the L2 table requests remain unretried. No transport recovery,
source substitution or scientific rerun is needed.

## Verification scope

The five existing URL-timeout tests and two inherited stable L2 tests pass.
The L2 audit passes **2,736 numerical/discrete comparisons**. Metadata-only
image checks pass **58 unique joins and 269 exact checks** before pixels.
All nine inherited image tests pass before payload. The independent image
audit passes **94,537 numerical comparisons and 160,581
exact checks**, with no disagreements or changed tolerances. Both figures
were visually inspected.

All 28 L2 metadata files, 22 L2 result files and 57 image metadata files were
locally SHA256/Git-identity verified. Of 22
image-result manifest entries, 20
were also locally verified. The two larger compressed CAL/COR inputs were verified, decompressed and
independently decoded by the successful workflow audit. The connector
exposed their Git identities but returned no binary content for an additional
local copy. Their public files, raw/compressed hashes and exact range receipts
are preserved. This is a local retrieval limitation, not missing science data
or a failed audit.


| Compressed input | Git blob identity | Compressed SHA256 | Raw SHA256 |
|---|---|---|---|
| TG008601_N0/SCI_CAL_SubArray.bin.gz | `50161647ccbf909f29b51eeb7beffb9c3fe5c9e2` | `35071b0aae1adeed1f404dc5afc8ad778e24e693cb68fbc441ae73a98bf523d6` | `af46fa284fb18e3e0f67ab730245878e44b2c985d1d140dd5e569ba4444b6c4d` |
| TG008601_N0/SCI_COR_SubArray.bin.gz | `2a0edef08ddecc4dba8e83f50c84b48f3835ade5` | `c77244116bc77b9383b0a4f97bbea6f9c9861bd6b591271ea1b1671b58f7551c` | `35fc7a3d0099e3900f1f4e11c36d7e3dd6bb3c6ec3fec6830ad1c28b8f04f733` |

The independently implemented image audit checks raw and compressed hashes,
source ranges, native float decoding, joins, masks, maps, fits and the fixed
classification. It retains unchanged relative 2e-8 and native/dimensionless
absolute 1e-6/1e-8 tolerances. The L2 audit retains relative 2e-8 / absolute
2e-10. There are no disagreements, omitted failures or scientific retunings.

The complete scientific comparison adds 155 files and changes no
earlier file. Exactly 153 are byte-verified against locally calculated
Git identities; any remaining input identities are recorded above. The final
scientific result tree is `74fd96327ebb12277e98aefe08a1c7c76bff3849`.

The separate editorial closure adds this record and LS8Z_CONTINUATION.md,
prepends the latest PROJECT_STATUS.md checkpoint, updates its current LS row
and appends the PROJECT_DIRECTION.md decision. The main README receives the
same conclusion and next action. These edits preserve all frozen source,
data, reports, checksums and earlier history.

## Scientific state

The fixed image diagnostic classifies the negative event as
**CORRECTION_LINKED**. DELTA/COR is **+1.688786 / +1.717959** in the two
coordinate conventions, with complete apertures and negative COR signs
matching L2. The delivered correction reverses a positive CAL aperture
residual into a negative COR residual. The label describes material coupling
to processing; the responsible component and physical cause remain unassigned.

**Immediate next action: prepare LS8AA for rank-8 WASP-43**, beginning
with a separate exact-pair/header freeze for CH_PR100016_TG007801_V0300 and
CH_PR100016_TG007802_V0300. Verify their NEXP=1/60-second ledger exposures,
then freeze exact DEFAULT-L2 ranges and transfer the unchanged signed screen.
Those science values remain unopened. The PG 1245-042 pair is closed.

No qualified SETI candidate, detector, sensitivity or observing coverage is
added. The earlier TESS_260647166 positive remains unresolved; prior bounded
studies, reserved panels and the unsent calibration request are unchanged.

[L2 result](results_ls8y_l2_screen/REPORT.md) ·
[Image result](results_ls8z_images/REPORT.md) ·
[Interpretation and exact continuation](LS8Z_CONTINUATION.md).
