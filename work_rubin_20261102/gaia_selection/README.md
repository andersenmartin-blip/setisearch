# Rubin main-sample Gaia DR3 association

**188 unique stellar associations are retained from the 413-object main metadata pool.** Their eligibility is an astrometric association criterion; this does not establish that 50 or more objects have enough usable Rubin photometry for analysis. No main Rubin flux values were requested or read by this work.

## Scope and frozen rule

The input consists of 433 DiaObjects from the fixed October 2026 ELAIS-S1 cone query: 20 development objects and 413 remaining metadata candidates. This is an alert-selected bounded field/time sample, not an all-star, all-sky, or demonstrably exhaustive cone catalog. Selection was frozen in [PLAN.json](PLAN.json) before Gaia retrieval; all original DiaObject and Gaia source IDs remain exact decimal strings.

A public ESA Gaia DR3 TAP query retrieved all 3,933 catalog sources in a fixed 0.6-degree circle centered at RA 8.986275°, Dec −42.709834°, without a magnitude, parallax, or stellar-class prefilter. This adds 360 arcsec of spatial margin beyond the 0.5-degree Rubin field. The first request succeeded (HTTP 200, 926,958 bytes); exact ADQL, receipt, and original CSV are retained. There was no retry or account access.

For every one of the 433 objects, Gaia positions were propagated from their reference epochs using proper motion to the object's Rubin `midpointMjdTai`, converted to TCB Julian years. Positive Gaia parallaxes supply distance for perspective propagation; available radial velocities are used, otherwise zero radial velocity. Missing-distance solutions use angular-only propagation. Missing-proper-motion neighbors retain their catalog coordinates and cannot qualify as the sole main association.

A candidate requires exactly one catalog source within **1 arcsec**, no additional catalog source within **2 arcsec**, a finite proper-motion solution, and either **parallax/error ≥ 3** or **two-dimensional proper-motion significance ≥ 5** using its covariance. These guards were fixed before inspecting Gaia matching outcomes. “Unique” always means unique under this bounded catalog rule; it does not exclude unresolved companions or uncatalogued sources. No main source failed a second-neighbor ambiguity guard in this field, but those checks were explicitly computed from all catalog neighbors.

All neighbors within 10 arcsec plus the nearest two catalog entries are recorded, giving 867 evidence rows. All 1,702,989 object/catalog pairs were recomputed by a separate numerical checker. The checker uses Cartesian linear motion and radial perspective plus an atan2 separation, without importing the matching code. Its maximum difference from the ERFA propagation is 2.39×10⁻⁸ arcsec and no 1/2/10-arcsec boundary count changes. This is a separate implementation by the same agent, not independent external review or astrophysical validation.

## Selection and exclusions

| Step | Objects |
|---|---:|
| Metadata objects, including development | 433 |
| Development objects reserved | 20 |
| Main metadata pool | 413 |
| Main objects failing association or stellar-evidence guards | 224 |
| Same-source duplicate removed within otherwise eligible main pool | 1 |
| Final unique main stellar associations | **188** |
| Selected with parallax S/N ≥ 3 distance ordering | 95 |
| Selected with uncertain/missing distance, placed last | 93 |

One main record also lies within 2 arcsec of a development object and shares a development Gaia identity; these exclusion reasons overlap a guard failure and must not be added as independent counts. All reasons are preserved in [REJECTED_MAIN.csv](REJECTED_MAIN.csv) and [ALL433_ASSOCIATIONS.csv](ALL433_ASSOCIATIONS.csv).

Development leakage checks exclude the exact 20 IDs, objects within 2 arcsec of any development coordinate, and matches to any Gaia neighbor within 2 arcsec of development objects. Historical Fink Gaia annotations from the development inventory supplement this conservative exclusion set; they never establish main eligibility. The inventory identity is retained in [ADDITIONAL_INPUTS.json](ADDITIONAL_INPUTS.json).

Remaining duplicates of the same Gaia source retain the smallest exact numeric DiaObject ID. Final ordering uses ascending `1000/parallax` pc only where positive parallax S/N ≥ 3, then exact numeric DiaObject ID. The 93 uncertain-distance objects follow in numeric ID order. This inverse-parallax value is a ranking proxy, not a calibrated distance posterior; no zero-point correction is claimed. Neither variability nor flux values enter selection.

[MAIN_SELECTION.csv](MAIN_SELECTION.csv) and [SELECTION_FREEZE.json](SELECTION_FREEZE.json) contain the exact ordered 188 objects for publication before any main photometry retrieval. The original 413-object pool cannot support a 500-object main sample without a separately specified metadata expansion.

## Important limits

- The precise DiaObject astrometric reference epoch and covariance are absent from the cone metadata. A contemporary midpoint time is an explicit proxy. Gaia propagation does not remove this Rubin-side uncertainty.
- Annual observer parallax is not applied because the full Rubin coordinate convention and reference epoch are not established. The 1/2-arcsec rules are fixed screening criteria, not calibrated association probabilities.
- Null proper motion, unknown radial velocity and weak/negative parallax limitations remain explicit. ERFA distance-override warnings for angular-only or very uncertain-distance catalog solutions are retained in the summary; the separate propagation check shows they do not change the discrete matching guards here.
- Completeness remains conditional on Gaia catalog coverage and the fixed field/motion margin. The largest proper motion actually returned is about 325 mas/year; no claim about all sources outside the retrieved field is made.
- RUWE, duplicate-source and astrometric-solution flags are retained as context rather than adding outcome-dependent thresholds.
- Stellar association does not demonstrate an unusual signal, telescope exposure completeness, sensitivity, or a SETI detection.

## Reproduce

From this directory, with the committed original Gaia CSV and unchanged parent input metadata:

```bash
python3 match_gaia.py
python3 audit_selection.py
```

These commands rewrite outputs, so reproduce in a separate copy to preserve timestamps. The first analysis run completed the CSVs but failed summary serialization of a NumPy scalar; the serialization-only fix and rerun are documented in [RUN_HISTORY.json](RUN_HISTORY.json). Matching thresholds and selection logic were unchanged.

Primary catalog reference: [ESA Gaia DR3 `gaia_source` datamodel](https://gea.esac.esa.int/archive/documentation/GDR3/Gaia_archive/chap_datamodel/sec_dm_main_source_catalogue/ssec_dm_gaia_source.html), including exact 64-bit IDs, ICRS coordinates, reference epochs, units, proper motions, parallaxes and covariance fields. The original query used the [public ESA TAP endpoint](https://gea.esac.esa.int/tap-server/tap/sync). [ESA programmatic access documentation](https://www.cosmos.esa.int/web/gaia-users/archive/programmatic-access) was identified; its page returned a browsing-service HTTP 451, while the datamodel and public TAP service were accessible.
