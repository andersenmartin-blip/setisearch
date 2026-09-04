# LS4A — frozen LHS 1140 filterbank-header and resource preflight

The expanded LS3 inventory found four complete public Green Bank Telescope ABACAD listings for LHS 1140 on 2017-01-21: L, S, C and X band. Each contains six medium-resolution and six high-time-resolution SIGPROC filterbank products. None is HDF5, so LS4A introduces a separately tested header parser rather than silently treating the files as LS1-style inputs.

This phase may stream and decode serialized SIGPROC header fields only. The parser must stop immediately after `HEADER_END`; it may not unpack a filterbank spectral sample. File length, data dimensions and duration may be derived algebraically from the archive size and decoded header geometry.

## Scientific inputs

The two-planet ephemeris and stellar radius are frozen from Cadieux et al. (2024), [Table D1](https://arxiv.org/html/2310.15490v2). The geometry calculation retains the LS1–LS3 circular, edge-on, common-node approximation and evaluates the observation midpoint plus the same 81-point period/epoch input-corner diagnostic.

Guillochon & Loeb report an optimum beam frequency on the order of tens of GHz. LS4A freezes 10 GHz only as a deterministic ranking anchor among the available radio bands. It is not asserted to be a unique optimum for an unknown sail system.

## Gate

Each cadence must provide a header-confirmed six-scan ABACAD sequence, 0.5–2.0 s medium sampling, 1–5 kHz channels, at least 700 MHz bandwidth, six valid 0.1–1.0 ms HTR headers and exact agreement with the archived file sizes. The selected six-file medium download must not exceed 12 GB. HTR payloads remain closed.

Among passing cadences, the smallest logarithmic frequency distance from 10 GHz wins, followed by better nominal conjunction geometry, earlier observation and cadence URL. A selection authorizes only a separately frozen signal-search design.

## Claim boundary

LS4A is not a signal search. It cannot support a technosignature, sensitivity, occurrence-rate or light-sail-exclusion claim.
