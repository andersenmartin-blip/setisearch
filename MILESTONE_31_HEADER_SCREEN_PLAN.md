# Milestone 31 higher-smearing target extension and HDF5-header-only screen

Status: **FIXED BEFORE ANY RANK 31--35 TELESCOPE PRODUCT IS OPENED**.

Milestones 16--30 resolved all thirty unique hosts below the frozen 1 Hz/s
conservative acceleration-smearing bound. The unchanged Milestone 16 result
also retained thirteen higher-smearing matched hosts in `all_matches`. They
were never spectrally screened or searched. Milestone 31 advances mechanically
to the first five of that preserved sequence.

## Frozen extension

| Extension rank | Archive target | Planet template | Drift proxy at 1425 MHz (Hz/s) | Frozen cadence ID |
|---:|---|---|---:|---|
| 31 | HIP99711 | HD 192263 b | 1.05365446 | `-66435` |
| 32 | HIP120005 | GJ 338 B b | 1.12777460 | `-76649` |
| 33 | HIP55848 | HD 99492 b | 1.66346922 | `-70969` |
| 34 | HIP3093 | HD 3651 b | 2.27163433 | `-73274` |
| 35 | HIP4872 | Gl 49 b | 4.37191614 | `-69318` |

The source is `results_m16_discovery/discovery.json`, SHA-256
`0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750`.
Targets are not re-queried or reranked. Ranks 31--35 mean the next five unique
hosts in the already stored `all_matches` sequence after the thirty-host
low-smearing block.

## Qualification and selection rule

This stage may read public catalogue records, HTTP object identity, HDF5
attributes, dataset geometry, timing, and frequency coverage. It may not index
or read any HDF5 `data` value.

A cadence qualifies only if all six current fine HDF5 products:

- form a time-ordered three-ON/three-OFF alternating sequence within 0.04 day;
- have compatible shape, dtype, integration time, and channel width;
- respond without header errors and support HTTP byte ranges; and
- cover 1399.65--1425.85 MHz, containing all five established one-megahertz
  search windows and their guards.

The first host in frozen extension order with a qualifying cadence is selected;
its earliest qualifying cadence becomes the blind primary search. All five
hosts are screened so the complete technical outcome is preserved. If none
qualifies, Milestone 31 stops without spectral contact.

## Frozen higher-smearing adaptation

If a target qualifies, the later preregistration must keep detector software
v0.5.0 but extend the config-driven odd boxcar bank from `[1, 3, 5, 9]` to
`[1, 3, 5, 9, 17, 33]`. At 1425 MHz the widest rank-35 conservative proxy
sweeps about 28.6 native channels per 18.253611008 s integration, inside the
33-channel template. The complete report cap must rise from 1200 to 1600,
above the finite 1512 pre-clustering peaks per window. Scramble calibration,
completeness injections, and all physical OFF-source vetoes remain mandatory.

This adaptation is frozen because the next metadata regime is known, not in
response to any spectral feature. A target-specific 630-case coverage proof
must still pass before spectral contact; the expanded width bank and fresh
random seeds must then be committed in the held-out preregistration.

