# Fixed C001 joint profile context

This analysis treats V2E2-0001 and V2E2-0016 as one overlapping C001/R001 profile group around 3852.3925 Å. It includes all six HD103991 spectra in the original extension02 epoch cohort, both discovery exposures' native orders 2 and 3, and all four preserved raw-order panels. This scope is not archive-wide completeness. Both U labels and all historical epoch/mapping/extraction outputs remain unchanged.

[PLAN.json](PLAN.json) fixes the method before observed arrays are interpreted. [INPUT_INVENTORY.json](../inputs/INPUT_INVENTORY.json) and the [header-only input audit](../input_audit/INPUT_AUDIT.json) bind the exact archived bytes, header representations and coverage. [SYNTHETIC_PREFLIGHT.json](SYNTHETIC_PREFLIGHT.json) records a compact no-observational-data check.

## Common coordinates and complete accounting

The shared grid is `arange(-300,301)/100` Å: 601 centers across ±3 Å. The union of the two former ±0.25 Å event cores is |offset| ≤ 0.265 Å, selecting 53 grid centers from −0.26 through +0.26 Å. The surrounding-pattern comparison uses the other 548 centers, 0.265 < |offset| ≤ 3 Å.

The barycentric center is `cb=3852.3925`. The single fixed topocentric anchor is `ct=cb/(1+16.9196571680147/c)`, using the first catalog discovery's recorded BERV and `c=299792.458 km/s`. Every epoch, including both discovery references and their native orders, shares this anchor. Barycentric panels sample `cb+x`; topocentric panels sample barycentric wavelengths `(ct+x)*(1+BERV_epoch/c)`.

Native order wavelengths follow the unchanged zero-based header polynomial and inherited topocentric-air convention. Multiplication by `(1+BERV_epoch/c)` converts them to barycentric coordinates once. Equivalently, native topocentric queries are `(cb+x)/(1+BERV_epoch/c)` for barycentric panels and `ct+x` for topocentric panels. No shift, center, width, drift or stellar-RV fit is introduced.

| Output family | Complete fixed slots |
|---|---:|
| Six merged epochs × two frames | 12 profiles |
| Two discovery exposures × two native orders × two frames | 8 profiles |
| Six merged epochs × both discovery references × two frames × two regions | 48 comparisons |
| Four native discovery/orders × same-epoch merged spectrum × two frames × two regions | 16 comparisons |
| Preserved raw/order context | 4 raw/excess panel pairs |

Self-pairs and shared-exposure relationships are flagged. Neither discovery reference is selected based on the result. Invalid inputs or normalization retain their declared slots and reasons.

## Signed flux and fixed-flank scaling

The signed source flux is always preserved. Native and merged scales differ: merged FLUX is header-confirmed ADU; native e2ds BUNIT is absent and is labeled **native extracted flux, unit unspecified**. No physical native/merged or cross-order flux ratio is inferred.

Each profile and frame has its own fixed flank reference: the pooled signed median of native samples at 1.5 ≤ |frame offset| ≤ 3 Å. Each flank must contain at least 20 finite native samples and the pooled reference must be strictly positive. Left/right coverage counts, finite counts, medians and nonpositive fractions are reported separately. The available-sample median remains distinct from a valid reference. There is no fitted continuum or linear background; the broader absorption/emission pattern remains in the comparison.

Native order 3 has no left normalization-flank coverage under this exact window, as established from the header polynomial. Its new raw-only status therefore means **missing coverage**, distinct from the historical local low/nonpositive continuum. The flank is not moved or narrowed to make it usable. Signed raw/core values and adequately covered raw correlations remain available, but they do not independently corroborate a line.

The first-difference MAD × 1.4826 / √2 proxy uses adjacent finite samples with both endpoints in the same flank and without crossing large wavelength gaps. It is descriptive, not formal SNR. The reference ≤ 3×proxy flag is reported only where the reference is valid. Positive finite ERR coverage and nonpositive flux fractions remain explicit.

Interpolation is linear without extrapolation. Brackets exceeding 1.51 times the full-source median barycentric spacing are masked. Zero-shift raw Pearson correlation requires nonzero exact range and at least 80% common finite region samples: 43 in the core or 439 in the broad pattern. Normalized RMS uses the same coverage threshold and requires valid positive flank references for both profiles. Raw-only profiles can therefore retain a raw core correlation while normalized RMS and/or broad correlation are explicitly blocked.

## Bounded evidence and release

Before flux access, all six merged and both native product headers are checked for identity, recorded metadata, numerical BERV, representation, required columns/shapes and native wavelength coefficients. The release requires exact hashes and verified public method publication. All sources and the release are checked again after execution; an existing results directory is never overwritten. There is no acquisition/network code.

The script saves ten compact pre-interpolation windows with source indices, original-frame and barycentric wavelengths, signed flux, ERR values (NaN where native errors are unavailable), full-source median-spacing metadata, recorded BERV and full-input hashes. Each window is the union needed by the two fixed frames plus the necessary bracketing samples. These artifacts permit independent arithmetic without restoring all full spectra. Full merged wavelength coordinates are read to locate the bounded slices; flux outside those slices is not copied or analyzed.

All four archived raw-order NPZs are copied exactly. Their stored raw cutout and historical raw-excess panels are displayed as preserved context; no new detector mapping, raw subtraction, registration or extraction is fitted.

Root may execute once after the public release:

```bash
python work_harps_20261102_c001_context/analysis/compare_group.py
python work_harps_20261102_c001_context/analysis/plot_group.py
```

`ROOT_RELEASE.json` uses schema `HARPS_C001_GROUP_RELEASE_V1` and binds publication commit/readback, plan/script hashes and inventory path/hash. Four figures retain every declared merged/native/raw context, signed values and raw-only annotations. The original epoch pipeline is not rerun.

The six-epoch BERV span is only about 3.193 km/s, or 1.225 nominal resolution elements. Core-versus-surrounding-pattern correlations describe shape agreement; they do not establish frame-discrimination power, origin, line identity, measured linewidth, false-alarm probability or completeness. The flanks can contain spectral structure and are not asserted to be quiet continuum. The two overlapping catalog records and reused discovery references are correlated observations, not independent detections.
