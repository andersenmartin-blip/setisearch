# Exact archived inputs for C022 / HD114783

Header-only restoration verifies **16 exact files**: all seven existing HD114783 merged spectra, three discovery ancillary TARs, three complete native-A FITS products and three original native/raw NPZ panels. Four complete cached archives and every selected member were verified. No observed flux, ERR or raw-pixel array was decoded. No new download, live acquisition, historical edit, new registration or completed-diagnostic replay was performed.

## Seven observations and three fixed references

Original queue row 36 fixes the complete C022 / R023 group at rows 36/45/49. Keep all three discovery products as references. The February 5 2022 and March 22, May 15 and July 1 2023 observing epochs remain in the seven-product cohort without becoming C022 references.

| Record | Queue row | Discovery product | Exact catalog center (Å) | Original ±0.25 Å core (Å) |
|---|---:|---|---:|---|
| 0117 | 36 | ADP.2022-01-22T01:09:14.958 | 4312.245 | 4311.995 to 4312.495 |
| 0127 | 45 | ADP.2022-05-06T01:04:00.123 | 4312.245 | 4311.995 to 4312.495 |
| 0131 | 49 | ADP.2023-01-17T01:07:48.581 | 4312.237499999999 | 4311.987499999999 to 4312.487499999999 |

The exact catalog-extrema midpoint evaluates to **4312.241249999999 Å**. Preserve that float; it is not a fitted peak. The common metric core is [4311.991249999999, 4312.491249999999] Å and ±3 Å context [4309.241249999999, 4315.241249999999] Å. Fixed common edges differ from original member edges by up to 0.00375 Å and do not contain the complete original-core union. Retain exact individual intervals and markers separately without post-value expansion.

First queue discovery 0117 was observed on **2022-01-21T06:51:10.597**, BERV **29.658729150824 km/s**. It fixes the independently recomputed common topocentric anchor **4311.814678415948 Å**, using `4312.241249999999 / (1 + 29.658729150824 / 299792.458)`. Each historical event-specific topocentric center is separately verified using its own exact member center and discovery BERV. Other references do not redefine the coordinate anchor.

The same seven HD114783 observations run from January 2022 through July 2023. BERV ranges from −29.0643174950811 to +30.0089342598494 km/s, span **59.073251754930496 km/s**. Three references each compare six other epochs: **18 directed nonself rows per frame/region represent 15 unordered observation pairs plus three reciprocal duplicates**, sharing only seven observations. Preserve exact source/reference identities and per-reference summaries; rows and pairs are not independent detections.

## Direct C021 shared-pixel and reference-flank exposure

C022 reuses the same seven observing products and native lineage as completed C021. Their bounded barycentric windows overlap on **[4309.241249999999, 4312.82625] Å**, width **3.585000000000946 Å**, sharing source pixels. The common metric cores are disjoint, but each is fully contained in the other's fixed reference context:

| Exposed common core | Interval (Å) | Containing fixed flank |
|---|---|---|
| C022 | 4311.991249999999 to 4312.491249999999 | C021 positive flank: 4311.32625 to 4312.82625 |
| C021 | 4309.57625 to 4310.07625 | C022 negative flank: 4309.241249999999 to 4310.741249999999 |

The entire C022 common core has already been sampled in C021's surrounding/positive reference context. Conversely, C021's core is included in C022's negative reference flank. All structured flank samples must remain under the separately frozen signed-reference rules, without masks or an assumed line-free continuum. Selection and these geometric dependencies were fixed in the [C021 handoff](../../work_harps_20261103_c021_context/scientific_review/NEXT_STEP.md) before C021 values. The additional C022 context extends beyond the overlap but adds no observations or untouched-core evidence. Fresh C022 flux/reference quality remains a runtime outcome; earlier quality values are not transferred.

Original C022 epoch/profile/raw evidence and the completed wider 0131 mapping diagnosis also already exist. Complete original historical raw crops remain separately preserved; neither equality nor independence of their full contents follows from bounded spectral geometry. Earlier same-target C018/C019 blue windows are disjoint. Numeric wavelength overlaps with C006/C007 use HD106515A and share no products or source pixels. This is dependent post-detection context, not blind, untouched or independent new data; it adds no observing time or archive-wide completeness. Completed mapping and normalization diagnostics are not replayed.

## Fresh headers in all three discoveries

[INPUT_INVENTORY.json](INPUT_INVENTORY.json) binds exact product identities, dates, BERV, raw progenitors, archive members and hashes. Each restored native product has a fresh scan of **all 72 order headers**, totaling **216 flat records keyed by product/order**. Every polynomial has a positive wavelength derivative over pixels 0–4095. Each discovery independently selects **order 19 only**, matching its own original covering-order record. All three covering pairs remain; none is excluded.

| Event | Order | Topocentric-air endpoints (Å) | Barycentric-air endpoints (Å) |
|---|---:|---|---|
| 0117 | 19 | 4285.09715793688 to 4333.250210121655 | 4285.521086333344 to 4333.6789023415395 |
| 0127 | 19 | 4285.09737976191 to 4333.250218570714 | 4284.911242127251 to 4333.061989255349 |
| 0131 | 19 | 4285.09576714302 to 4333.2484424843005 | 4285.524701072949 to 4333.682196450326 |

**Every selected product covers the full common context, core and both fixed reference flanks in both frames.** All six native frame rows have coordinate support for 601 grid centers, 51 core centers and 550 surrounding centers. Exact coefficients, event centers, endpoints and fixed-frame geometry remain in the inventory. This new scan determines C022 scope independently of earlier contexts. Coordinate coverage does not establish finite flux, reference positivity, normalization quality, calibrated uncertainty or physical origin. Each runtime missing, nonpositive, low-reference or blocked outcome must remain explicit in the separately frozen analysis.

Every native header shape is 72×4096, with degree 3 wavelength and degree 4 trace polynomials evaluated at zero-based pixels 0–4095. Merged wavelengths are barycentric air angstrom and uncalibrated ADU; ERR is declared unavailable. The historical native convention remains topocentric air angstrom. Native BUNIT is absent in all three products, so extracted units remain unspecified. NPY headers preserve panel/native-snippet shapes without reading array values. Publication identifiers and observation timestamps remain distinct.

## Original failed stages and distinct 0131 review history

| Original event / order | Global support | Original local usable | Original baseline verified | Later five-window support |
|---|---|---|---|---|
| 0117 / 19 | true | **false** | **false** | true |
| 0127 / 19 | true | **false** | **false** | true |
| 0131 / 19 | true | **false** | **false** | true |

`mapping_records` preserves original native pixels, raw rows/columns, event centers, source paths and baseline-field basis. Batch03 explicitly stores `baseline_mapping_verified`; original 0131 raw_followup uses `mapping_verified`. Later support for 0131 comes from its completed wider mapping-followup order record at exactly the original coordinates. Later reference support does not rewrite any original failed local/baseline stage. No earlier mixed true/false matrix or absent-later assessment is transferred to C022. No new mapping or registration diagnostic is run.

Two batch03 events, 0117/0127, retain exact original primary/secondary/adopted **U/U/U** reviews. Separate raw_followup event **0131** retains original primary **I**, secondary **M**, explicitly normalized to **I**, and adopted baseline **I / INSUFFICIENT_LOCAL_RAW_MAPPING**. Its completed wider diagnosis and separate later visual reviews at unchanged coordinates retain **U/U/current U**. All three current labels remain U. Broad native and diffuse trace-associated raw structure remains unresolved; mapping support and morphology do not qualify a laser or assign a specific origin.

`historical_raw_review_records` separates `batch03_original` (two exact original sets), `separate_raw_followup_0131` (exact original/later records, verification, archive identity and historical preservation declarations), `current_adopted` (three current source rows) and `per_event_history` (three staged summaries). Preserve each source-specific history rather than transferring 0130/0129 stages or declaring blanket original U reviews. The recorded unchanged-coordinate/preserved-sample declarations remain historical metadata; restoration does not decode arrays to re-prove them or replay the completed 0131 diagnosis.

## Three exact original raw panels

The two original batch03 NPZs retain stored raw/background/excess, baseline and native arrays. The original 0131 baseline NPZ retains five arrays: raw cutout, background, excess, native wavelength and native flux. Exact original container identities are:

| Original panel | Bytes | SHA256 |
|---|---:|---|
| 0117 / 19 | 8,110 | `bdf4c1bf1775cd726b01a397e6b312a99c2bae41423258eb17e341c0e364aaa1` |
| 0127 / 19 | 8,119 | `810d2409f222af838ff3744f36ca883ffa7aaba5ab76886e8c92e43e1fb4ece6` |
| 0131 / 19 | 3,602 | `ddba2ac8fc401e59cf646ff6c70ebb598da650d45f1c3decea5b34176f6069bb` |

Original 0131 is not replaced by its distinct later wider NPZ, **5,497 bytes**, SHA256 `a1d0e34caa677b4d235d23fa30cac276d705ad27dfdd1a5d6645e5f574a464f1`. Original baseline ZIP/member and historical preserved-input hashes are verified; the later wider archive and its declarations remain separately bound. No panel is newly fitted, cropped or subtracted. Complete historical crops remain intact without a new pixel-equality or independence claim.

## Restore exact bytes

Four complete cached archives supply the inputs:

| Archive | Selected contents | Original registries |
|---|---|---|
| `SETI_HARPS_EXTENSION02_INPUTS_PART1_2026-11-01.zip` | Seven HD114783 merged spectra | [Restore](../../work_harps_20261101/v2/extension02/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART3_2026-11-01.zip` | 0117 ancillary product | [Batch03 saved inputs](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/SAVED_INPUTS.md), [registry](../../work_harps_20261101/v2/extension02/raw_followup_batch03/checkpoints/LIBRARY_INPUTS.json) |
| `SETI_HARPS_RAW_BATCH03_INPUTS_PART4_2026-11-01.zip` | 0127 ancillary product | Same batch03 instructions and registry |
| `SETI_HARPS_EXTENSION02_RAW_INPUTS_PART1_2026-11-01.zip` | Separate original 0131 ancillary product | [Original raw restore](../../work_harps_20261101/v2/extension02/raw_followup/checkpoints/RESTORE.md), [registry](../../work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) |

The inventory binds complete archive sizes/hashes and exact selected members. No new transfer, duplicate archive upload or live telescope query was needed. Two batch03 panels are reconstructed from unchanged committed evidence parts; original 0131 comes from unchanged `RAW_BASELINE_EVIDENCE.zip` and its manifest, cross-checked against the preserved-input ledger. Full detector products remain in existing saved archives and are not extracted for profile arithmetic.

In a separate reproduction checkout:

```sh
python3 work_harps_20261103_c022_context/inputs/restore_inputs.py \
  --archive-dir /path/to/merged/archive/cache \
  --archive-dir /path/to/batch03/archive/cache \
  --archive-dir /path/to/original/raw/archive/cache
```

One cache may hold all four archives. The helper verifies whole archives and selected members, rejects differing destinations, reuses identical bytes and writes deterministic metadata without local cache paths. Its FITS/NPY inspection is header-only; it executes no scientific comparison, completed diagnostic or network request. Preserve published methods and completed outputs; reproduce separately. Full restored FITS/TAR and temporary panel copies are excluded from Git.
