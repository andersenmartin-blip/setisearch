# LS5 filterbank qualification amendment — 2026-09-05

The expanded round matched four new systems. Dedicated cadences for GJ 9827,
LHS 1903 and HIP 41378 were empty. Target-only queries found individual HDF5
observations but do not supply complete dedicated ON/OFF sequences.
Kepler-160 has three listed cadences, stored as rawspec SIGPROC filterbanks.

Accept SIGPROC medium/HTR products using the already qualified LS4 adapter.
This format expansion follows metadata inspection, not signal inspection.
One L-band ON header was already checked for format/access feasibility;
its parser stopped at HEADER_END after 298 bytes. No spectral samples were read.

Select Kepler-160 for header preflight. Inspect all three dedicated cadences
(--813610 L, --813641 S, --813675 C), preserving incomplete outcomes. Require
six alternating ON/OFF medium products, compatible LS1 time/frequency sampling,
32-bit one-IF data, and at least 700 MHz bandwidth. Prefer six compatible HTR
headers, then minimize nominal b-c projected separation, then earliest epoch
and cadence URL. Require selected medium downloads <=12 GB. Do not substitute
single observations from the target-only query. The selection is operational,
not a statistical test of the population.

Use the NASA default Heller et al. (2020) b/c ephemerides, stellar radius 1.118
solar radii, and the inherited circular edge-on common-node model. Period/epoch
corner ranges are sensitivity diagnostics, not confidence intervals; stellar
radius, orbital eccentricity and unknown mutual node are not propagated.
Commit exact spectral configuration separately before reading samples.
