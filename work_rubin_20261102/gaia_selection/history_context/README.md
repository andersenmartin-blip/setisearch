# Supplementary Gaia source-position history context

All **188 frozen main objects** have retrieved metadata histories. This check propagates their already selected Gaia counterpart to each of **807 distinct DiaSource metadata rows**. The main selection and ordering remain byte-identical; no main Rubin flux values were read.

- All807rows have finite coordinates and times.
- Median source/Gaia separation: **0.124arcsec**.
- **30rows across18objects** fall outside1arcsec; none fall outside2arcsec.
- Maximum separation: **1.640arcsec**.
- Retrieved source metadata spans **2025-11-08T06:38:55.297to2026-10-31T02:37:11.543UTC**; this is not necessarily the final main photometry window or an exhaustive history.

[Every source row](SOURCE_POSITION_CONTEXT.csv) and [every object's summary](OBJECT_POSITION_CONTEXT.csv) remain explicit. The original1arcsec rule selected using the cone object coordinate; individual source centroids can differ. These30offsets are supplementary diagnostic flags, **not a new rejection gate**. They may arise from centroid uncertainty, blends, association problems or other processing. No such cause is established from metadata alone.

The supplementary check uses the same fixed Gaia counterpart and proper-motion/RV conventions at each source observation time. It does not independently reselect the nearest Gaia source at every epoch. Source astrometric error, detector quality flags and photometry are outside this diagnostic. Missing/retrieved-history limitations remain distinct from association eligibility.

[PLAN.json](PLAN.json) froze the exact five metadata responses and the main-selection hash before computation. The first file-discovery preflight included receiptJSONs in a broadglob and stopped before calculation; exact response filenames were then used, as recorded in the plan. The code refuses metadata files containing flux fields. The retained [summary](SUMMARY.json) verifies unchanged selection SHA256`0983fb2d308c1c734fd89cf57368f6539c81149f12328089c516f077aa1ea14a`.

Reproduce in a separate copy with`python3 check_histories.py`; no network request is made. Outputs are descriptive and do not alter the main selection or original catalogs.
