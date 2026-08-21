# Milestone 16 metadata-only target discovery plan

Status: **FIXED BEFORE ANY NEW TELESCOPE PRODUCT IS OPENED**.

## Purpose

Milestone 16 will discover a new public GBT L-band exoplanet cadence while
avoiding the severe intra-integration acceleration smearing measured for GJ
581 b. This first stage reads only the Breakthrough Listen catalogue API and
NASA Exoplanet Archive tabular metadata. It may not open a telescope product,
read an HDF5 header, or inspect a spectral value.

## Eligibility and ranking

A planet/target pair is discoverable only if:

- the archive exposes it as the primary target of a GBT fine-grade cadence at
  the established L-band centre-frequency metadata value;
- the official composite record supplies period, semimajor axis, eccentricity,
  periastron epoch, longitude of periastron, sky position, proper motion,
  parallax, radial velocity, and distance; and
- its conservative periastron-acceleration proxy corresponds to no more than
  1 Hz/s at 1425 MHz.

Eligible pairs are ranked by host distance, then acceleration proxy, planet
name, and archive target name. At most the first five unique hosts advance to a
separate HDF5-header screen. That later screen must prove six-scan geometry,
ON/OFF alternation, byte-range access, and coverage of all five established
bands before one host can be selected.

## Exclusions

All targets already contacted by this project are excluded. Tau Ceti and GJ
667 C are excluded after their Milestone 15 metadata ineligibility. GJ 273, GJ
1002, and Ross 128 remain excluded after target-specific public result-page
exposure. No spectral result from an excluded target is used in this screen.

## Boundary after discovery

This run cannot select a cadence for spectral search. If no low-smearing match
is found, Milestone 16 stops as a technical no-selection outcome. If matches
are found, only the frozen top five unique hosts may enter the separate
header-only screen. Detector thresholds, activity subsets, vetoes, five search
bands, scramble count, and completeness rules remain unchanged.
