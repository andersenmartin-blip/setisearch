# LS7R: a concrete CHEOPS input and its temporal response

14 September 2026. **The CHEOPS metadata assessment is complete.** Public
delivery, product identity and the exposure-to-image joins are established
for one visit. Short-cadence pixel calibration and a detector are not yet
qualified. This is progress beyond LS7Q's unresolved HiPERCAM delivery, not
an astronomical detection or additional qualified observing coverage.

## Selected observation and successful delivery

Following [the scope written before acquisition](LS7R_INPUT_SCOPE.md), the
[mission archive](https://cheops.unige.ch/archive_browser/) was queried at
its resolved 55 Cnc coordinates, radius 0.01 degrees, public visits only,
latest versions. All **31 returned visits** are saved. Selection uses the
earliest start, not measured variability: visit **300024000301**, OBSID
**1015522**, target label **55Cnce**, on **9 March 2020**. Its observation
category is **reference transit**, so this early visit is an engineering
input, not a representative sample of all CHEOPS operations.

The exact file key is **CH_PR300024_TG000301_V0300** and pipeline version
**14.1.2**. The [DACE public API](https://dace-query.readthedocs.io/en/latest/dace_query.cheops.html)
returns both archive revisions 2 and 3; revision 3 was retained consistently
with the mission query. The mission list has **49 products**, all matched in
DACE's **81 paths**. DACE additionally lists 30 movies, one processing log
and one housekeeping product. No movie or light curve was examined.

HTTP byte-range delivery succeeds with status 206, consistent object sizes
and ETags. Five FITS files were traversed by their headers without fetching
image bodies. **82 retained ranges contain 1,203,264 bytes**, spanning
**25 HDUs** and five metadata tables with **10,368 rows**. This is the unique
retained range total, not a count of all transport bytes: the initial probe
and some header reads were repeated while the acquisition code was developed.
The separately retrieved processing log contains 60,868 bytes.

| Product | Complete FITS bytes | Image dimensions / role | Image body acquired |
|---|---:|---|---|
| SCI_RAW_Imagette | 30,435,840 | 3,024 × 50 × 50; raw ADU | No |
| SCI_RAW_SubArray | 90,938,880 | 432 × 200 × 200; raw ADU, plus margins | No |
| SCI_CAL_SubArray | 138,343,680 | 432 × 200 × 200; calibrated ADU | No |
| SCI_COR_SubArray | 139,812,480 | 432 × 200 × 200; calibrated/corrected ADU | No |
| PIP_COR_PixelFlagMapSubArray | 92,160 | One 200 × 200 visit-level flag map | No |

The public byte ranges make a bounded future pixel acquisition practical;
there is no need to transfer all five complete products. Saved evidence
includes metadata rows containing on-board PHOTOMETRY_1/2/3 fields. Those
fields were received as part of the table, but are explicitly excluded from
every analysis and timing export. **No science image pixel or photometric
flux value was inspected, and no event search was run.**

## Actual exposure and stacking contract

The individual exposure duration is **2.20000004768372 seconds**. The raw
subarray file contains **6,048 individual-exposure metadata rows**; this
does not mean that 6,048 unstacked pixel images were delivered.

| Delivered image | Individual exposures per image | Nominal light-collection time | Median timestamp interval |
|---|---:|---:|---:|
| Raw imagette | 2 | 4.400000095 s | 4.449005 s |
| Raw/calibrated/corrected subarray | 14 | 30.800001144 s | 31.145472 s |

Every one of the **432 compression-entity counters** joins exactly fourteen
individual exposures, seven imagettes and one subarray. Raw, calibrated and
corrected subarray timestamps/counters are identical. The mean individual
timestamp agrees with its imagette within **16 microseconds** and with its
subarray within **0.809 milliseconds**. MJD values reproduce the TT conversion
of UTC timestamps; UTC and TT are not interchangeable columns.

The exposure timeline has **five segments separated by four long gaps** of
approximately **2,245–2,338 seconds** between individual midpoints. Nominal
light-collection time sums to **13,305.6003 seconds**, while first-to-last
individual midpoint spans **22,515.7906 seconds**. Neither is qualified
search coverage. All 432 CE_INTEGRITY values are zero; this is a processing
integrity check, not an all-purpose photometric or cosmic-ray quality gate.

The imagette offset is (790, 256) in the full array and (75, 75) within the
subarray; the subarray offset is (715, 181). These agree geometrically. The
imagette window is static and circular within the 50 × 50 bounding square.
Pixel inclusion, defects and instantaneous saturation remain uninspected.

## Timestamp-only pulse response

The calculation integrates positive rectangular pulses over each of the
6,048 recorded individual intervals, then averages into the actual pairs
and groups of fourteen. It uses equal exposure weights and linear response,
with no noise, calibration, PSF fitting or threshold. Start times lie on a
fixed one-second grid anchored at the first individual integration start;
the full onset ledger retains starts in long gaps too.

The table reports sampled extrema **only for pulses fully within a timeline
segment**, while retaining the short readout gaps between individual
exposures. These are not guaranteed continuous-phase extrema.

| Pulse width | Onsets wholly within a segment | Imagette peak / input amplitude | Subarray peak / input amplitude |
|---|---:|---:|---:|
| 30 s | 13,304 | 1.000 | 0.481837–0.963670 |
| 60 s | 13,154 | 1.000 | 0.963233–1.000 |
| 100 s | 12,954 | 1.000 | 1.000 |

Across the complete respective onset grids, **8,944 / 8,824 / 8,664** pulses
have zero temporal response because of missing exposure intervals. These
are deterministic model evaluations reusing one visit, not independent
observations, measured missed events or a detector recovery rate. The
imagette result motivates its shorter cadence; it does not establish that
a faint glint can be recovered against native noise or contamination.

## Calibration provenance and remaining response requirements

The calibrated and corrected headers name sixteen reference files, including
the ephemeris. The processing log resolves the truncated flat-field name
and confirms the fifteen REF_APP identities. They include bias V0109,
CCD linearisation LUT100 V0104, gain V0109, temperature-dependent point-source
flat V0104, dark/bad-pixel maps V0201 and white PSF V0106. Exact names are saved
in the calibration extract. Their contents and validity intervals have not
yet been verified; filenames alone are insufficient for an imagette calibration.

Both CAL and COR record completed bias/RON estimation, dark and flat
corrections. COR additionally records jitter, WCS, smearing, hot-pixel and
background/stray-light processing. **Cosmic-ray detection and correction
remain N/A in these headers.** The flag map is two-dimensional and describes
pixel behaviour across the visit; its saturation definition requires a
pixel to exceed the linearity limit for more than 10% of the visit. It cannot
be treated as an instantaneous cosmic-ray or short-pulse saturation mask.

Raw imagettes explicitly have no ground pixel calibration applied. The
[PIPE documentation](https://pipe-cheops.readthedocs.io/en/latest/pipe/installation.html)
identifies gain, flat-field, nonlinearity and PSF inputs for short-cadence
extraction; its [method description](https://pipe-cheops.readthedocs.io/)
also requires supervising PSF assumptions. No PIPE run, tuned PSF library,
uncertainty model or pulse-protection claim is adopted here.

## Verification and decision

All 82 ranges match their saved SHA-256 hashes and lie wholly in headers or
the five allowed metadata tables. All five metadata HDU checksums and data
sums pass. A separate standard-library FITS decoder agrees on **44,928
time/counter/quality field values** with Astropy. The timing joins, UTC/TT
checks and independent scalar pulse calculations pass. This is a second
implementation path, not an external reviewer or a physical calibration audit.

**Decision: retain this exact visit for the next combined calibration and
pixel-response development study.** Its delivery and short sampling are
established. Before a native search, establish reference-file contents and
validity, the imagette calibration/noise mapping, a target-protected PSF and
background fit, instantaneous defect/cosmic/saturation handling and a joint
signal/control endpoint. Preserve the native scene and include 30/60/100-second
positive pulses before any data-dependent correction. Do not promote
metadata arithmetic into detector readiness.

[Evidence and reproduction](results_ls7r_metadata/README.md).
[Concrete continuation](LS7R_CONTINUATION.md). LS7Q's HiPERCAM obstacles and
the separate LS7P publication reconciliation remain open. Historical TESS
outcomes and unused TESS/M43 panels remain unchanged.

This assessment uses public CHEOPS Mission Archive and DACE services. CHEOPS
is an ESA mission in partnership with Switzerland and a European consortium.
