# LS6 TRAPPIST-1 9.92 GHz subband pilot — prespectral amendment

Date: 2026-09-05. The user requested moving to another target after LS5.

Select the four 2017-02-23 X-band scan products in the subband whose catalogue
center is nearest 10 GHz: 9920.213413 MHz, native coverage
9826.466274–10013.963413 MHz. Two ON and two OFF scans form ABAB; each has
56 samples at 1.073741824 seconds. Total medium input: 58,721,848 bytes.
This is a narrowly scoped pilot on archived target-labelled observations,
not the previously planned full six-scan, multi-band or conjunction-ranked run.

Amend the metadata phase's ephemeris requirement for this pilot only: no orbital
ranking or conjunction claim is made. NASA default rows lack all seven transit
epochs; a later geometry analysis must adopt and validate published dynamical
ephemerides. The existing LS6 metadata record remains intact.

Use the unchanged LS1 broadband detector parameters and the LS4B SIGPROC
adapter. Keep ON=8, adjacent OFF=6, frequency overlap=0.5, clip=(-6,12),
1024 native-channel base bins, widths=(1,4,16,32,64), duration bank
(4,8,16,32,64) seconds, and cap=2048. The inherited implementation cannot
evaluate a 64-second template inside a 60.13-second scan; only fitting
templates contribute. No scores are used to choose the band or sequence.
A1 uses B1; A2 uses B1 and B2. OFF scans are named DIAG_TRAPPIST1_OFF and
are at a different sky position. Do not substitute other blocks or subbands.

Header coordinates alone are not validated tracking histories: designated ON
positions differ from the current catalogue by tens of arcseconds. No beam
centering, calibrated sensitivity or target-origin claim is inferred. Any
survivor requires pointing and interference checks, a separate HTR freeze,
and independent data before any technosignature interpretation.

The exact product URLs, sizes, headers, role mapping and implementation hashes
are frozen in config/ls6_trappist1_x_subband.json and publicly committed before
spectral contact. Process one raw product at a time, checkpoint, then delete it.
No HTR values are read. No raw telescope product is published.

Kepler-446 was not promoted (no dedicated cadence). Kepler-732 remains held
because both catalogue and HDF5 pointing attributes disagree with NASA by
9.68 arcminutes; no Kepler-732 spectrum has been read.
