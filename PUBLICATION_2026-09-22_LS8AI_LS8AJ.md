# LS8AI–LS8AJ publication and verification — 22 September 2026

Repository: `andersenmartin-blip/setisearch`; science branch:
`m43-support-qualification`. Standing authorization covers code, protocols,
data, results, logs and the README update on main.

## Immutable sequence

| Stage | Commit | Result |
|---|---|---|
| LS8AF–LS8AH closure parent | `f23d7021d7a36317ce5d94ccbae19c2e72bf2567` | Previous closed study retained |
| LS8AI exact pair/header freeze | `113ccaf61fa911d1fcaba4b424606e4c282441df` | Rank-11 pair, no science values |
| Header result | `073a580976082b9340505c1f67a98ca590362f3f` | 93/86 rows; 60 seconds/NEXP=1 |
| L2 scope freeze | `822a2ebf88603fcaf57a3ef649ad46c3e3c7a787` | 24,702 exact table bytes; unchanged screen |
| Audited L2 result | `b8724b092cf8f6a348b9f652b65cde080df21622` | 179 rows, 288 windows, one negative cluster |
| LS8AJ representative/metadata freeze | `260a5b2ed88bc94102d8f679110f8be1272a8f05` | Complete signed set, metadata only |
| Audited image metadata | `0bdaaf90f64a091999c2fee42e5ff7fbde388fb2` | 58 unique joins; exact future ranges |
| Image payload/diagnostic freeze | `b1aaac670ab3ae2b1e3526bc77d89d0da105e254` | 18,560,000 image + 46,400 smearing bytes |
| Audited image result | `04980eab35ae262e1eb422a2999fc18e24021dfa` | TG005201_N0: CORRECTION_LINKED |

All four workflows succeed:

- [LS8AI headers 35735230400](https://github.com/andersenmartin-blip/setisearch/actions/runs/35735230400).
- [LS8AI L2 screen/audit 35735575780](https://github.com/andersenmartin-blip/setisearch/actions/runs/35735575780).
- [LS8AJ metadata/joins 35735994073](https://github.com/andersenmartin-blip/setisearch/actions/runs/35735994073).
- [LS8AJ image diagnostic/audit 35736377404](https://github.com/andersenmartin-blip/setisearch/actions/runs/35736377404).

All eight header/L2/image-metadata/image URL resolutions succeed on their
first attempt. All three image/smearing range requests also succeed on their
first attempt; the L2 table requests remain unretried. No transport recovery,
source substitution or scientific rerun is needed.

## Verification scope

The five existing URL-timeout tests and two inherited stable L2 tests pass.
The independent L2 audit passes **3,456 numerical/discrete comparisons**.
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
| TG005201_N0/SCI_CAL_SubArray.bin.gz | `0d081ba8f593e9b8552d0ac02b12fa1123185240` | `2de9f2d31ab73f4285a8b37a1c5bbc74c612b4e29f7ce59bdabd6f303df463be` | `6326c7eb53005e799822acb28dd108b79ad6998e4e6a11c783a7ee8727cb8654` |
| TG005201_N0/SCI_COR_SubArray.bin.gz | `b535a14a6532160be2bc20b2f903da0b2ce0355d` | `edf55cd1ef1f6c716bad6567bd18b74d7fd339562d3ed6387b224528625ec56b` | `c46cf1ae73a1dfca3c16c334ae8597bdce69cef3eea21394062997035b144f7c` |

The independent image audit checks raw/compressed hashes, source ranges,
native float decoding, joins, masks, maps, fits and the fixed classification.
Unchanged image tolerances are relative 2e-8 and native/dimensionless absolute
1e-6/1e-8. L2 retains relative 2e-8 / absolute 2e-10. No disagreement,
scientific rerun or result-dependent retuning is omitted.

The complete scientific comparison adds 155 files and
changes no earlier file. Exactly 153 are byte-verified
against locally calculated Git identities; remaining input identities are
recorded above. Final scientific result tree: `8e6df46bfa3996b25b4e30d385220957280bc52b`.

The separate editorial closure adds this record and LS8AJ_CONTINUATION.md,
prepends the latest PROJECT_STATUS.md checkpoint, updates its current LS row
and appends the PROJECT_DIRECTION.md decision. The main README receives the
same conclusion and next action. These edits preserve frozen source,
data, reports, checksums and earlier history.

## Scientific state

The fixed image diagnostic classifies the negative event as
**CORRECTION_LINKED**. DELTA/COR is **-3.380189 / -3.413528** in the two
coordinate conventions, with complete apertures and negative COR signs
matching L2. The delivered correction substantially reduces a larger CAL
deficit while leaving a negative COR residual. The label describes material
coupling to processing; the responsible component and physical cause remain
unassigned. No new correction or screening cut is adopted.

**Immediate next action: prepare LS8AK for rank-12 PG 1343-102**, starting
with a separate exact-pair/header freeze for CH_PR100002_TG008701_V0300 and
CH_PR100002_TG008702_V0300. Verify the NEXP=1/60-second ledger exposures,
then freeze exact DEFAULT-L2 ranges and transfer the unchanged signed screen.
Those science values remain unopened; the cohort's two later eligible visits
stay outside scope. The EC13080-1508 pair is closed, with its third visit
TG005203 outside the completed transfer.

No qualified SETI candidate, detector, sensitivity or observing coverage is
added. The earlier TESS_260647166 positive remains UNRESOLVED_WITHIN_FIXED_SCOPE
and its bounded study closed. PG1303-114’s negative and PG 1207-033’s positive also retain their unresolved
labels and closed bounded studies. WASP-43, GJ 436 and PG 1245-042 remain
closed under CORRECTION_LINKED. Other closed optical studies and M33 HD 3651 are unchanged.
Reserved TESS/M43 panels remain closed. Calibration is NOT_READY and its
technical request unsent. Standing research/publication authorization
continues; delegation remains deferred.

[L2 result](results_ls8ai_l2_screen/REPORT.md) ·
[Image result](results_ls8aj_images/REPORT.md) ·
[Interpretation and exact continuation](LS8AJ_CONTINUATION.md).
