# Context for all 90 unresolved extension02 records

**The 90 unresolved records correspond to 39 groups of centers within the adopted nominal resolution scale, or 37 groups whose ±0.25 Å profile windows overlap.** These are two bookkeeping views of correlated records; neither number estimates distinct physical signals. Every original record remains U. The grouping adds no observations, flux measurements, origin assignments or qualified laser candidates.

The selected cohort spans 10 targets and 38 discovery exposures. The work reuses 1,142 already-computed frame-measurement rows (180 discovery and 962 other-epoch rows) involving 60 distinct archived exposures. Event-specific rows share input data and must not be added as independent observations or telescope time. The earlier 95 U records are outside this derivative analysis and remain unchanged.

## Evidence routes after the mapping queue

Pending raw reviews and the project’s mapping limitations remain first priority. [ACTION_QUEUE.csv](ACTION_QUEUE.csv) supplies the next evidence type for every one of these 90 records in original catalog order. It is not a significance or likelihood ranking. The first matching route is assigned below; the orthogonal flags and both group memberships are retained in every row.

| Next evidence type | Records | Required work |
|---|---:|---|
| Normalization context | 2 | Inspect unnormalized native orders, backgrounds and overlapping-order agreement before interpreting normalized profiles. |
| Broader frame baseline | 10 | Add independently selected same-target archival epochs with a larger BERV span; retain stellar radial-velocity uncertainty. |
| Joint neighboring-profile context | 63 | Review whole groups, raw covering orders and the broader absorption/emission pattern together. |
| Individual profile context | 15 | Review all raw covering orders and broader stellar/template context; seek independent controls. |

**Normalization cases:** V2E2-0092 (3823.0275 Å) and V2E2-0104 (3859.5550 Å), both HD114386, have at least one inherited low-continuum flag among their discovery/comparison profiles. This flag does not exhaust every possible continuum/background concern. Their normalized correlation values cannot repair uncertain continuum support.

**Frame-baseline cases:** all six selected HD122640 records have BERV span 0.89251 km/s; all four selected HD135204 records have span 0.72557 km/s. Both are below the inherited nominal resolution velocity 299792.458/115000 = 2.60689 km/s. For HD135204 around 3871.08 Å, event-wise median other-epoch correlations are 0.99254–0.99597 in the barycentric frame and 0.97657–0.98514 in the topocentric frame. Both remain similar with this short baseline; these values do not establish an origin. Spans above one nominal resolution element do not by themselves resolve the origin either.

**Shared spectral neighborhoods:** 66 of the 90 records belong to HD106515A (20), HD114783 (23) and HD126093 (23). Their complete group entries below show why joint template/context review is more useful than treating each recorded detection as independent. For example, C018 contains seven HD114783 records around 3869.33 Å from seven discovery exposures; the existing barycentric event-median correlation range is 0.98982–0.99476. That is evidence of persistent profile resemblance in these data, not evidence of a laser or a confirmed stellar line.

**Wider overlapping windows matter:** HD106515A C006 covers three records at 4310.305–4310.605 Å from two exposures. HD126093 C030 covers eight records at 3866.935–3867.3275 Å from five exposures. Each combines two nominal-resolution groups. The centers are not merged into one line; their correlation windows share spectral context. Each of the 39 nominal-resolution groups is retained separately.

## Fixed method and interpretation

[PLAN.json](PLAN.json), its five byte-preserved input snapshots and [FREEZE.json](FREEZE.json) were fixed before these new aggregations. Source tables and a few example values were already visible, so this is explicitly post-detection, non-blind work and not a public preregistration.

For a pair of records on the same canonical target, the narrow grouping connects centers separated by at most their mean wavelength divided by 115000. The second grouping connects centers separated by at most 0.5 Å, corresponding to touching/overlapping ±0.25 Å core windows used by the completed epoch comparison. Connected components include singletons; all edges are recorded. Endpoint-span flags disclose possible transitive chains; none of the present components exceeds its corresponding single-edge scale. The groups omit neither weak profiles nor singleton events. Coordinates are barycentric air wavelengths, with no stellar radial-velocity correction.

**No physical linewidth has been measured here.** `nominal_resolution_angstrom = center/115000` and the production `fwhm_model_angstrom` are prescribed template scales. The latter uses the production seed convention and can differ slightly from the fitted-center value. [EVENT_CONTEXT.csv](EVENT_CONTEXT.csv) imports the existing discovery and other-epoch narrow-versus-three-times-broader fixed-template residual RMS ratios. A ratio below one only says the broader fixed template has lower residual RMS in that prescribed window. The comparison does not estimate intrinsic FWHM, prove a resolved line, calibrate significance or decide whether a laser exists. Uncertainty/calibration-aware free-width fitting would be a separate analysis.

No raw array or stored profile array was opened and no completed epoch extraction was repeated. Original epoch summaries, amplitudes, correlations, source identities and raw-review evidence are retained. Both frame correlations are continuous descriptive quantities. Barycentric coherence can arise from ordinary spectral structure; topocentric coherence does not prove terrestrial origin.

## Complete core-window group inventory

The table is ordered by target and wavelength. “Exposures” counts distinct discovery exposures within that group. It is not a count of independent detections. The exact members, continuous correlations and provenance are in the CSV files.

| Group | Target | Barycentric center span (Å) | Records | Exposures |
|---|---|---:|---:|---:|
| C001 | HD103991 | 3852.3775–3852.4075 | 2 | 2 |
| C002 | HD106515A | 3868.6025 | 1 | 1 |
| C003 | HD106515A | 3869.7450–3869.7575 | 5 | 5 |
| C004 | HD106515A | 3872.2450 | 3 | 3 |
| C005 | HD106515A | 3882.0350–3882.0400 | 5 | 5 |
| C006 | HD106515A | 4310.3050–4310.6050 | 3 | 2 |
| C007 | HD106515A | 4312.7000 | 1 | 1 |
| C008 | HD106515A | 5182.0050 | 1 | 1 |
| C009 | HD106515A | 6802.0200 | 1 | 1 |
| C010 | HD112410 | 3823.0650 | 1 | 1 |
| C011 | HD112410 | 3865.6775 | 1 | 1 |
| C012 | HD112410 | 3869.2675 | 1 | 1 |
| C013 | HD114386 | 3823.0275 | 1 | 1 |
| C014 | HD114386 | 3859.5550 | 1 | 1 |
| C015 | HD114386 | 3869.9150 | 1 | 1 |
| C016 | HD114386 | 4303.7850–4303.7900 | 4 | 4 |
| C017 | HD114783 | 3868.1750 | 1 | 1 |
| C018 | HD114783 | 3869.3325–3869.3350 | 7 | 7 |
| C019 | HD114783 | 3881.6125–3881.6150 | 5 | 5 |
| C020 | HD114783 | 4303.1300 | 1 | 1 |
| C021 | HD114783 | 4309.8250–4309.8275 | 5 | 5 |
| C022 | HD114783 | 4312.2375–4312.2450 | 3 | 3 |
| C023 | HD114783 | 5944.9650 | 1 | 1 |
| C024 | HD122640 | 3866.9600 | 1 | 1 |
| C025 | HD122640 | 3868.9250–3868.9275 | 3 | 3 |
| C026 | HD122640 | 3881.2050 | 1 | 1 |
| C027 | HD122640 | 5548.0900 | 1 | 1 |
| C028 | HD126093 | 3864.5550 | 1 | 1 |
| C029 | HD126093 | 3866.1250 | 3 | 3 |
| C030 | HD126093 | 3866.9350–3867.3275 | 8 | 5 |
| C031 | HD126093 | 3868.1450–3868.1550 | 4 | 4 |
| C032 | HD126093 | 3869.2950–3869.2975 | 2 | 2 |
| C033 | HD126093 | 3880.3475–3880.3525 | 4 | 4 |
| C034 | HD126093 | 4312.2025 | 1 | 1 |
| C035 | HD128582 | 5758.2675 | 1 | 1 |
| C036 | HD135204 | 3871.0800–3871.0850 | 4 | 4 |
| C037 | HD1397 | 3872.3750 | 1 | 1 |

## Reproduction and evidence

- [EVENT_CONTEXT.csv](EVENT_CONTEXT.csv): all 90 records, source hashes, fixed template scales, imported metrics, original U evidence and route.
- [RESOLUTION_GROUPS.csv](RESOLUTION_GROUPS.csv) and [CORE_OVERLAP_GROUPS.csv](CORE_OVERLAP_GROUPS.csv): both exhaustive group views.
- [RESOLUTION_PAIR_EDGES.csv](RESOLUTION_PAIR_EDGES.csv) and [CORE_OVERLAP_PAIR_EDGES.csv](CORE_OVERLAP_PAIR_EDGES.csv): every qualifying pair (113 and 130 respectively).
- [ACTION_QUEUE.csv](ACTION_QUEUE.csv): all 90 next-evidence assignments, preserving catalog order.
- [SELECTED_EXISTING_EPOCH_MEASUREMENTS.csv](SELECTED_EXISTING_EPOCH_MEASUREMENTS.csv): exact selected rows from the previously completed comparison.
- [SUMMARY.json](SUMMARY.json), [OUTPUT_HASHES.json](OUTPUT_HASHES.json), `inputs/`: counts, output hashes and frozen source snapshots.
- [Independent audit](independent_audit/AUDIT.json): PASS, 7,377 checks of all 90 records, five snapshot identities, 1,142 reused epoch rows, exact pair edges and separately reconstructed disjoint-set components, all routing assignments and scalar imported/rederived metrics. No analysis-module imports or pixel reads; this verifies derived bookkeeping, not physical origin.

Run `python3 build_context.py` inside this directory. It verifies the frozen plan, script and five input snapshots, then deterministically regenerates derived tables. It cannot modify any production/current catalog or consume raw arrays. Reproduction overwrites this directory’s derivative outputs only; preserve published copies as appropriate.

All 90 labels remain unresolved. Post-detection grouping and reused measurements provide no false-alarm rate, survey completeness, flux estimate, calibrated null result or qualified exclusion of artificial light.
