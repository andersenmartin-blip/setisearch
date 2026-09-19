# CHEOPS exact-visit imagette grouping evidence — 19 September 2026

This note narrows the retained visit's onboard `gcoadd` contract using a
peer-reviewed publication about the exact same CHEOPS observation. It does not
open target-image pixels and does not infer arithmetic that the source does not
state.

## Exact observation match

Morris et al. (2021), *CHEOPS precision phase curve of the Super-Earth
55 Cancri e*, A&A 653, A173,
https://doi.org/10.1051/0004-6361/202140892,
describes the CHEOPS In-Orbit Commissioning observation on **9 March 2020**.

The paper states that the effective 30.8-second exposure was made by stacking
**14 individual 2.2-second readouts**. It further states that **imagettes were
stacked onboard in pairs**, so one 30.8-second stacked image was accompanied by
**seven stacked imagettes**, with an imagette cadence of about **4.4 seconds**.

Those values independently match the retained visit metadata already established
in LS7R:

- individual integration: 2.20000004768372 s;
- raw subarray: `NEXP=14`;
- raw imagette: `NEXP=2`;
- exactly seven imagettes per fourteen-readout compression entity;
- median imagette interval: 4.449005 s.

The date, target and integration structure identify the same IOC visit retained
as `CH_PR300024_TG000301_V0300`, OBSID 1015522.

## What this resolves

For this visit, the `gcoadd` grouping is no longer an unspecified possibility:
**each delivered raw imagette combines two consecutive constituent readouts**.

The grouping result is observationally specific and agrees with the FITS
`NEXP=2` metadata and the saved exposure-to-imagette joins.

## What it does not resolve

The paper uses the word “stacked” and establishes the pair grouping, but it does
not provide the pixel-level implementation. It does not specify whether
`gcoadd` stores:

- a literal integer sum;
- a normalized/rounded sum;
- a weighted combination;
- clipping or saturation handling;
- intermediate numeric width/overflow behavior;
- any generalized rule that differs from ordinary `coadd`.

Therefore this source closes **group size and cadence**, not the numerical
operator. The exact implementation/RD-11 or equivalent flight-source evidence
is still required before a raw pixel value can be mapped unambiguously back to
its constituent-exposure domain.

## Decision impact

The remaining `gcoadd` blocker is now narrower:

**resolved:** two-readout grouping, seven grouped imagettes per 14-readout
subarray, temporal placement/cadence.

**unresolved:** pixel arithmetic, normalization, clipping/saturation and numeric
representation.

The prospective hard gate remains closed and no target-image range is opened.
