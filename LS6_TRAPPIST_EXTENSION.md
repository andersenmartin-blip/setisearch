# LS6 alternative target extension — 2026-09-05

Kepler-446 has no dedicated cadence; Kepler-732 has one but its listed ON
coordinates differ from NASA by about 9.7 arcminutes. Do not treat the catalogue
label as sufficient for stellar attribution. A separate HDF5 pointing-attribute
audit is being recorded; no spectral values have been indexed.

Metadata exploration of the explicit archive labels DIAG_TRAPPIST1 and
DIAG_TRAPPIST1_OFF finds 16 scan times on 2017-02-23. The first query is a
substring query and includes the OFF target: filter exact target labels and
deduplicate URLs before counting. There are 224 medium-resolution filterbank
products distributed across four receiver blocks, with two ON and two OFF
scans per block, and unspliced 187.5 MHz subbands. These are not six-scan ABACAD
cadences, and the existing six-scan search must not be silently reused.

For next-target feasibility, inspect one subband in the X receiver block:
choose the listed center nearest 10000 MHz (ties by lower center then URL).
Read only its four SIGPROC headers to verify duration, sampling, source and
sequence. Record all catalogue grouping counts and the exact four URLs.
The 10 GHz anchor is an operational choice inherited from LS4 motivation,
not a unique physical optimum. No spectral samples or HTR samples may be read
in this metadata phase. A new, separately frozen ABAB search plan is required.
