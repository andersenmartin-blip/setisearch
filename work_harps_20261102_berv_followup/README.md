# HARPS wider-date and BERV follow-up — completed 2 November 2026

Two additional archival HD122640 spectra have been acquired, preserved and compared with the six fixed unresolved records on that target. All **24 frame profiles / 12 event–epoch pairs** were measured with the inherited method. The four HD135204 records have no newly selected epochs under the bounded metadata query. **All ten remain U.**

The original survey remains 300 unique exposures, 20 targets and 70.874650833 hours. Its V2 totals remain **403 A / 46 O / 185 U / 35 M / 0 N**. The two new spectra are targeted follow-up inputs, not an extension of the original full-spectrum survey search. No qualified laser candidate, photon-origin assignment or calibrated null is established.

## What the new comparison adds

| HD122640 reference observation | Recorded BERV (km/s) | Role |
|---|---:|---|
| 22 May 2017, 05:20:05 UTC | −11.0816664353 | Larger displacement, low local continuum in the five blue records |
| 20 January 2018, 08:50:34 UTC | +29.2818122856 | Cleaner local profiles; relatively small displacement from discovery |

The available HD122640 BERV span increases from **2.237910 to 40.363479 km/s**, or 15.4834 nominal resolution elements at R=115000. This is a geometric displacement benchmark, not a statistical-power calculation. The cleaner January epoch lies only approximately 0.78–1.13 resolution elements from the discovery observations of the six records.

Five records at approximately 3866–3881 Å have January barycentric correlations **0.9609–0.9743**, versus **0.5046–0.7228** in the topocentric comparison. They are selected, correlated event records, not five independent detections. The May exposure supplies the large BERV separation, but all ten frame profiles for those five blue records carry the inherited low-continuum flag. Its weak or noisy correlations cannot establish absence or resolve origin. No finite positive ERR values are available in either new input.

The separate record **V2E2-0235 at 5548.09 Å** has weak correlations with both new epochs (barycentric −0.0402 and 0.1567). Its earlier raw-image ambiguity remains: weak correlation does not distinguish charge contamination from a transient photon contribution. No classification is changed.

[Complete measurements, all-event accounting and figures](prospective_comparison/results/README.md) · [Machine-readable comparison summary](prospective_comparison/results/SUMMARY.json) · [Independent numerical audit](comparison_independent_audit/NUMERICAL_AUDIT.json)

## Acquisition and prospective controls

The successful metadata queries returned **18 new HD122640 products and zero HD135204 rows** under the exact public, same-target, single-exposure filters. This is not an archive-wide absence claim. The saved inventory was reduced to one latest observation per represented calendar month, before new header or spectrum values. Only January and May were represented. The recorded BERV extrema then selected these same two products under a separate frozen plan.

Both spectra passed exact header identity, raw-progenitor, resolving-power, fiber-state, BARYCENT, air-wavelength/Angstrom, ADU-flux and table-structure checks before array access. Both are processed with HARPS_3.8. Matching metadata does not establish identical instrumental systematics across observing eras. Stellar radial velocity is not removed, wavelength zero-points are not fitted, and the inherited comparison remains descriptive.

The first metadata request failed because ESO rejected qualified ORDER BY names. A separately published syntax-only amendment made the two successful requests. The first legacy header request returned an HTML error because percent-encoded colons were not decoded. A separately published literal-colon amendment obtained both headers. All failed requests, exact responses, stops, amendments and audits are retained. Actual totals: **three target metadata queries, three target-header requests and two spectrum downloads**; no hidden retries or substitute exposures. Documentation lookups are recorded separately.

- [Metadata result](metadata_search_v2/RESULTS.md), with the [original failed request](metadata_search/RESULTS.md).
- [Verified header result](header_acquisition_v2/RESULTS.md), with the [original URL-format failure](header_acquisition/RESULTS.md).
- [Exact spectrum acquisition and restoration](science_acquisition/RESULTS.md).
- [Frozen profile method](prospective_comparison/PLAN.json) and [release](prospective_comparison/COMPARISON_RELEASE.json).

The method/input selection was public in commit `aae61901226d9329be8f8ce333066fa7c9b85954`; exact downloaded input bytes were public and read back in `3e5f38f15da4306d11d443f1e4cc89de925e2ddc` before new spectral arrays were interpreted. The independent numerical reconstruction passed **2,065 checks and 29,712 scalar comparisons**; the largest metric difference was 3.56×10⁻¹⁵. All six event figures and the overview were visually inspected.

## Preserve and resume

Run `python3 science_acquisition/restore_inputs.py` to restore both exact FITS files from four ordered parts. The compressed archive is 3,578,014 bytes; its two members total 10,529,280 bytes. Run `python3 prospective_comparison/restore_profile_evidence.py` to restore all 20 original discovery references and 24 derived profiles from the 382,080-byte evidence archive. Both helpers verify complete hashes and refuse to overwrite differing files. No live ESO download is required to reproduce the saved calculation.

Use a separate copy for numerical reproduction so published timestamps, result files and one-shot execution markers remain intact. The original 100-exposure epoch analysis, completed mapping and normalization work, and Rubin 188+2 screen must not be rerun merely to resume.

[Current continuation state](CONTINUATION_STATE.json) binds this result and the previous checkpoint. [The next handoff](next_followup/README.md) is preparation for a distinct future phase; it does not expand the completed two-spectrum run. Rubin remains at 190 selected objects, only 2 primary and 4 separate forced numerical objects (the primary two are included in the four), minimum 50 unmet and no qualified null. No new Rubin request, paid service, external message or unattended search was added in this continuation.

Based on public data obtained from the ESO Science Archive Facility. Exact product and raw-progenitor identities are retained in the acquisition manifests.
