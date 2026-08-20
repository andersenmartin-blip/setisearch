# Milestone 13 preregistration: GJ 411 held-out detector-v0.5 validation

Status: **frozen before spectral extraction or inspection**.

## Purpose and evidential boundary

Milestone 13 is the first independent application of detector v0.5.0. It will
search one previously unused public target/cadence without changing any
detector rule after seeing its spectral payload. A retained candidate is a
follow-up trigger, not a technosignature claim. A null result applies only to
the five frozen bands, the frozen motion/activity bank, and the measured
completeness.

The selected target is **GJ 411 (Lalande 21185)**, using GJ 411 b as the motion
template. The data are the complete Green Bank Telescope L-band ABACAD cadence
from 2016-06-03, archive cadence `--72283`.

Before this document was committed, only the public catalogue, archive API,
HTTP metadata, and HDF5 attributes/shape/dtype/chunking were read. No selected
HDF5 `data` slice was indexed, extracted, plotted, summarized, or searched.

## Selection record

GJ 411 was selected as the nearest eligible confirmed-planet host in the
metadata screen that met all of the following:

- not Proxima Centauri or LHS 1140, the project's prior targets;
- not GJ 273 or GJ 1002, whose public result-summary pages were inadvertently
  exposed during archive-path discovery;
- three ON scans interleaved with three distinct OFF pointings;
- one compatible fine-resolution geometry across all six scans;
- full coverage of 1399.65-1425.85 MHz; and
- current products that return HTTP 200 and advertise byte-range access.

The source sequence is:

| Order | Role | Source | Header start MJD | Integrations | Duration (s) |
|---:|---|---|---:|---:|---:|
| 1 | ON | GJ411 | 57542.976493055554 | 16 | 287.779586048 |
| 2 | OFF | HIP52936 | 57542.980833333335 | 16 | 287.779586048 |
| 3 | ON | GJ411 | 57542.984861111110 | 16 | 287.779586048 |
| 4 | OFF | HIP52941 | 57542.988958333335 | 16 | 287.779586048 |
| 5 | ON | GJ411 | 57542.993194444450 | 16 | 287.779586048 |
| 6 | OFF | HIP53002 | 57542.997326388890 | 16 | 287.779586048 |

Every file has shape `[16, 1, 318230528]`, float32 samples, 17.986224128 s
integrations, 2.835503418 Hz channels, and coverage from 1023.9257840855 to
1926.26953125 MHz. The machine-readable selection record is
`metadata/m13_gj411_selection.json`.

The successful structure-only archive run was GitHub Actions run
`32388221712`; its artifact digest is
`sha256:b0efc590048b0af4a11fd1c6177a2c5d07a80a331c23cabfbd979d1a7531e849`.
The official target/orbit metadata run was `32388560852`; its artifact digest
is `sha256:f63db4b1b36373e3614ecdc70ce2e5363f52e280cd88c828aa820e8b55ac9880`.

## Data-format boundary

The current archive exposes this fine product as HDF5 rather than SIGPROC.
This is a source-container difference, documented before payload inspection.
`scripts/m13_hdf5_extract.py` reads only the preregistered frequency slices and
writes the same `data`, `frequency_mhz`, and JSON `metadata` NPZ contract as the
existing SIGPROC extractor. It verifies URL size, ETag, source name, start MJD,
sampling, shape, dtype, and frequency geometry before reading a slice.

The adapter is not a detector change. Detector v0.5.0 remains frozen at commit
`32720a0b5e097403f864e2b84d53a071d65d7c46`.

## Target and orbital template

The target and orbit values in `config/gj411b_heldout_m13.json` come from the
[NASA Exoplanet Archive](https://exoplanetarchive.ipac.caltech.edu/) Planetary
Systems default record for GJ 411 b, which cites Hurt et al. (2022):

- period: 12.9394 days;
- semimajor axis: 0.07879 au;
- eccentricity: 0.063;
- periastron epoch: BJD 2456307.8; and
- archive `pl_orblper`: -30 degrees, used as omega.

The unknown inclination is represented only through the already frozen
projected-scale bank. The motion template predicts a coordinate transform; it
does not establish that any emitter resides on GJ 411 b.

## Frozen detector and search

All v0.4 search settings transferred through Milestone 11 remain unchanged:

- projected scales `[0, 0.25, 0.5, 0.75, 1.0]`;
- phase offsets `[-0.2, -0.1, 0, 0.1, 0.2]` cycles;
- minimum two active ON epochs and minimum per-epoch S/N 3.0;
- minimum-epoch recurrence statistic;
- the same moving per-epoch RFI mask;
- spectral widths `[1, 3, 5, 9]` channels;
- 256 global scrambles, with the new preregistered seed `1320260820`;
- candidate reporting floor 5.5, 20 Hz clustering, and unchanged family flags;
- the same completeness grid and 32 trials per level, with seed
  `131320260820`.

The complete frozen v0.5 veto block is:

```json
"candidate_veto_v0p5": {
  "local_off_tolerance_hz": 20.0,
  "single_epoch_snr_floor": 5.5,
  "receiver_local_half_width_hz": 100.0,
  "receiver_alias_tolerance_hz": 20.0,
  "receiver_alias_minimum_shared_epochs": 2
}
```

Arithmetic-family candidates without a specific automated v0.5 veto remain
manual-review cases and may not be silently promoted.

## Frozen frequency windows

The five Milestone 11 search intervals and their 350 kHz extraction guards are
reused without adjustment:

| Window | Extraction range (MHz) | Search center (MHz) | Search half-width (kHz) |
|---|---:|---:|---:|
| `m13_1400p5` | 1399.65-1401.35 | 1400.5 | 500 |
| `m13_1406p5` | 1405.65-1407.35 | 1406.5 | 500 |
| `m13_1412p5` | 1411.65-1413.35 | 1412.5 | 500 |
| `m13_1418p5` | 1417.65-1419.35 | 1418.5 | 500 |
| `m13_1425p0` | 1424.15-1425.85 | 1425.0 | 500 |

## Decision and interpretation rules

After this preregistration commit:

1. extraction must fail closed if any frozen identity or geometry check changes;
2. detector settings may not be changed in response to the GJ 411 payload;
3. all configured windows and all six scans must complete;
4. the published result must preserve automated veto provenance and manual
   arithmetic-family flags;
5. any code/threshold change after spectral contact ends this held-out test and
   requires a separately labelled development milestone; and
6. any retained candidate requires a genuinely independent observing cadence
   before stronger interpretation.

