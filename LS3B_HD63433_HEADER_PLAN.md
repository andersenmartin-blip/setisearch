# LS3B — frozen HD 63433 header and geometry preflight

LS3 found two complete public Green Bank Telescope cadences for HD 63433 under the archive alias `HIP38228`: L band on 2016-05-21 and S band on 2017-03-12. Each listing contains six medium-resolution and six high-time-resolution HDF5 products.

This phase may read HTTP metadata plus HDF5 attributes, dimensions and data types. It must not index or read a value from the spectral `data` dataset. It is therefore not a signal search.

## Frozen ephemeris

All three planets use the free-eccentricity solution in Table 5 of Mallorquín et al. (2024), [arXiv:2401.04785v1](https://arxiv.org/html/2401.04785v1). TJD epochs are converted to BJD by adding 2457000. The stellar radius, 0.912 ± 0.034 solar radii, is from Table 2 of the same paper. The table directly supplies the semi-major axes that are absent for planets b and c in the NASA Exoplanet Archive default rows used by LS3.

The ranking calculation retains the LS1/LS2 approximation: circular, edge-on, common-node orbits, with the archive MJD treated as BJD. It evaluates both adjacent orbital pairs, d–b and b–c, at the midpoint of the first ON scan. Published one-sigma errors on periods and transit epochs define a deterministic 81-point input-corner range per pair. This range is not a confidence interval and does not include the quoted semi-major-axis or stellar-radius errors.

## Frozen gate and selection

A cadence qualifies when its six medium-resolution headers form ABACAD, share the expected medium-resolution geometry, cover at least 700 MHz, and have 0.5–2.0 s sampling. Complete HTR support requires six matching HTR headers with 0.1–1.0 ms sampling.

Among qualifying cadence-pair combinations, prefer complete HTR support, then the smallest nominal projected separation, then the earliest observation and stable lexical tie-breakers. Any selected combination requires a separately frozen signal-search phase before spectral values may be opened.

## Claim boundary

LS3B can establish cadence structure, frequency/time resolution and approximate conjunction ranking. It cannot detect or exclude a light-sail signal, state a calibrated sensitivity or support an occurrence-rate claim.
