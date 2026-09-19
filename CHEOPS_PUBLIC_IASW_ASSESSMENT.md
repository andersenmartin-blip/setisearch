# CHEOPS public IASW/source assessment — 19 September 2026

Operational follow-up after LS7V and the completed LS7P reconstruction release.
This is a documentation/source assessment, not a new target-image experiment.
No CHEOPS target image values, new pulse trials, candidate decisions or qualified
observing coverage are added.

## New concrete public source lead

The University of Vienna CHEOPS project page explicitly states that the CHEOPS
Instrument Flight Software (IFSW/IASW) was developed as open-source software and
links the public CHEOPS Instrument Application Software repository:

- University project page:
  https://space.univie.ac.at/en/projects/cheops/
- Public CHEOPS-IASW repository:
  https://gitlab.phaidra.org/ottensr5/cheops

The public GitLab project identifies itself as **CHEOPS Instrument Application
Software**. An indexed repository file confirms that a public branch is exposed.
The University page describes the upper software layer as the configurable
science-data processing chain used for real-time image processing/compression.

This corrects the earlier bounded-search note that no IASW repository lead had
been found. The repository is a valid concrete source lead. This assessment
does not claim that the exact flight revision used in March 2020 has yet been
identified.

## What the public mission documentation resolves

ESA's CHEOPS Data Products Definition Document (issue 1.16) lists the stacking
enumeration as:

- `coadd`
- `mean`
- `gmean` (used for imagettes)
- `gcoadd` (used for imagettes)
- `none`

It explicitly assigns the exact processing definitions to
**On-Board Data Processing Steps, CHEOPS-UVIE-INST-TN-001, issue 2.0 (RD-11)**.
Public DPD:
https://www.cosmos.esa.int/documents/1416855/12897414/CHEOPS-UGE-SOC-DD-002-i1.16_data_products_definition_document.pdf/c0980d2d-595b-b0bd-6413-c569501eb242?t=1687517012308

The CHEOPS mission technical paper, section 7.2, independently states that when
ordinary window stacking is required, window images and corresponding margins
are **co-added pixel-by-pixel**. It also describes the nominal short-exposure
scheme in which imagettes are cropped before the window stack and retained at
full cadence. This is high-level operational documentation; it is not a complete
numeric specification for `gcoadd`.
Mission paper:
https://doi.org/10.1007/s10686-020-09679-4

The University/ESA OBDP 2019 presentation places stacking as the first lossy
stage in the configurable onboard data-processing chain and shows the available
keys `NONE, COADD, MEAN, GCOADD, GMEAN`. The conference page states that the
complete CHEOPS IFSW sources are available under GPL2.
Conference record:
https://indico.esa.int/event/225/contributions/4306/

## What remains unresolved

For the retained visit `CH_PR300024_TG000301_V0300`:

- raw imagettes record `NEXP=2`, `STACKING=gcoadd`, `ROUNDING=0`;
- raw subarrays record `NEXP=14`, `STACKING=coadd`, `ROUNDING=0`.

The public material above establishes that these are distinct defined onboard
modes and gives the ordinary window-coaddition description, but it does **not**
yet establish the exact `gcoadd` arithmetic for this visit: normalization,
grouping, weighting, clipping/saturation handling, integer/floating arithmetic,
or the precise relation between the two constituent imagette exposures and the
delivered pixel values.

The exact technical note RD-11 was not located in the bounded public-web search.
The public IASW repository is therefore the next primary lead for the operator
definition. In the current execution environment the project and indexed file
pages are visible, but a complete repository archive/code search was not
retrievable. Do not infer the implementation from the names `gcoadd` or
`gmean`.

The separate offline calibration requirements also remain: gain/units,
LUT100 ordering/normalization, exact flat contents, and the dark/bad-map
validity/selection rule. None is resolved by the high-level stacking material.

## Revised decision

**PARTIAL_OPERATOR_DOCUMENTATION_ONLY — NOT_READY_FOR_TARGET_IMAGE_STUDY.**

The ordinary `coadd` description is now externally supported at high level,
and a concrete public IASW source repository has been identified. The exact
`gcoadd` contract and the required calibration references remain blocking.
Next inspect a version-relevant IASW implementation or RD-11 issue 2.0; if
those still do not supply the exact operator and applicability rules, use the
prepared technical clarification request. Do not evaluate source-image pixels
before the integrated calibration/operator contract is frozen.
