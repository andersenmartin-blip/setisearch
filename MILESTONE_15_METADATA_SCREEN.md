# Milestone 15 held-out target metadata screen

Status: **FIXED BEFORE NEW SPECTRAL CONTACT**.

## Purpose

Milestone 15 will apply frozen detector v0.5.0 to one new public Breakthrough
Listen cadence.  This first stage is limited to catalogue records, HTTP object
identity, HDF5 attributes, dataset geometry, scan timing, frequency coverage,
and official planet/host metadata.  It may not index, extract, summarize,
plot, or search any HDF5 `data` value.

The screen covers the three remaining archive aliases already declared in the
Milestone 13 catalogue adapter:

1. Tau Ceti (`TAUCETI` or `HIP8102`);
2. GJ 581 (`GJ581` or `HIP74995`); and
3. GJ 667 C (`GJ667C` or `HIP84709`).

Ross 128 is not eligible for a held-out Milestone 15 search because a
target-specific public Breakthrough Listen result page was exposed while
planning this screen.  Proxima Centauri, LHS 1140, GJ 411, and GJ 687 are
excluded because this project has already contacted their data.  GJ 273 and
GJ 1002 retain their earlier exclusion after result-page exposure.

## Eligibility rule

A target can advance only if the metadata evidence establishes all of the
following before spectral contact:

- a complete six-scan GBT L-band ABACAD cadence with three ON scans and three
  interleaved OFF scans;
- compatible fine-resolution HDF5 geometry across all six scans;
- byte-range-accessible current products with no header errors;
- coverage of the established 1400.0-1401.0, 1406.0-1407.0,
  1412.0-1413.0, 1418.0-1419.0, and 1424.5-1425.5 MHz search bands plus a
  target-specific extraction guard; and
- an official planet solution and host astrometry sufficient to construct the
  frozen planet-frame template bank.  At minimum, period, semimajor axis,
  eccentricity, periastron epoch, longitude of periastron, sky position,
  proper motion, parallax, and radial velocity must be present.

If more than one target qualifies, the nearest host by the official metadata
distance/parallax advances.  Ties are broken by the earliest complete archive
cadence.  If no target qualifies, Milestone 15 stops without spectral contact
and the result is recorded as a technical no-selection outcome.

## Boundary after the metadata run

The metadata artifact may be used only to select and freeze one cadence,
construct its identity checks, and prove full-template extraction coverage.
Detector thresholds, recurrence logic, activity subsets, spectral widths,
vetoes, five search bands, scramble count, and completeness procedure remain
unchanged from Milestone 14.  A separate target-specific preregistration must
be committed before any selected spectral slice is read.
