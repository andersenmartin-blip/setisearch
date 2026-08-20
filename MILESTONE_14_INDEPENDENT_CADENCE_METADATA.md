# Milestone 14 independent-cadence metadata probe

**Status: ONE PARTIAL INDEPENDENT L-BAND CADENCE IS USABLE**

This metadata/header-only probe enumerated every public GJ 687 cadence returned
by the Breakthrough Listen catalogue. It did not read spectral dataset values.

## Reproducibility record

- GitHub Actions run: `32396758942`
- Artifact: `9416940844` (`milestone-14-independent-cadence-metadata`)
- Artifact digest: `sha256:6cd4e23bc9df4ca4c1891dc56cd244460f1c2ce4119c3582a166beeee1ffe56b`
- Catalogue cadences returned: 3
- HDF5 headers inspected: 16
- Header errors: 0
- `spectral_payload_inspected`: `false`

## Cadence inventory

| Cadence | Date | Fine HDF5 sequence | Frequency range (MHz) | Use |
|---|---|---|---:|---|
| `--517803` | 2016-07-15 | GJ687, HIP85098, GJ687, HIP85612 (`A-B-A-D`) | 1023.926–1926.270 | Partial independent 1425 MHz follow-up |
| `--75045` | 2016-07-22 | Complete `A-B-A-C-A-D` | 1023.926–1926.270 | Original Milestone 14 cadence; not independent |
| `--520487` | 2016-10-23 | Complete `A-B-A-C-A-D` | 1797.949–2802.832 | Excluded: does not cover the candidates |

The four `--517803` products share the same 16-integration geometry,
18.253611008 s sampling, 2.793967724 Hz channels, byte-range support, and full
coverage of the three unresolved candidate frequencies. The two missing fine
products are the expected `C` control and third `A` target scan; neither is
silently reconstructed or substituted.

## Interpretation boundary

Cadence `--517803` is independent in observing date and spectral payload, but
it is incomplete. It can test whether a candidate recurs in both available
GJ 687 scans and whether either available OFF scan contains receiver-frame
evidence. It cannot provide a complete ABACAD confirmation or support a new
global-search significance claim.

The machine-readable catalogue responses and all HDF5 header identities are
stored in `results_m14_independent_cadence/metadata_probe.json`.
