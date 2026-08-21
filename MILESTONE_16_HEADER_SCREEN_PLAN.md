# Milestone 16 HDF5-header-only cadence screen

Status: **FIXED BEFORE SHORTLISTED TELESCOPE PRODUCTS ARE OPENED**.

This stage follows discovery publication commit
`24965b3ae00b508049cf0094f96e03f7cb5bfdba`. It may read public catalogue
records, HTTP object identity, HDF5 attributes, dataset geometry, timing, and
frequency coverage. It may not index or read any HDF5 `data` value.

## Frozen shortlist

1. GJ876 / GJ 876 e: cadence `-76697`
2. HIP114622 / HD 219134 h: cadences `-63424`, `-65393`, `-66869`, `-67073`,
   and `-67169`
3. HIP65859 / GJ 514 b: cadence `-82035`
4. HIP109388 / GJ 849 b: cadences `-73890` and `-74424`
5. HIP83043 / GJ 649 b: cadence `-70291`

The exact catalogue URLs include the archive's `-grades:fine;` prefix and are
frozen in `scripts/m16_header_screen.py`.

## Qualification rule

A cadence qualifies only if all six current fine HDF5 products:

- form a time-ordered three-ON/three-OFF alternating sequence within 0.04 day;
- have compatible shape, dtype, integration time, and channel width;
- respond without header errors and support HTTP byte ranges; and
- cover 1399.65-1425.85 MHz, which contains every established search band and
  the prior target guard.

The nearest discovery-ranked host with at least one qualifying cadence is
selected. If that host has several, its earliest qualifying cadence is chosen.
If no cadence qualifies, Milestone 16 stops without spectral contact.

## Boundary after this run

The selected record, if any, may be used only to construct a target-specific
configuration and prove full-template extraction coverage. A separate
preregistration and successful coverage proof must be committed before a
spectral slice is read.
