# LS5 metadata selection amendment — 2026-09-05

The initial five-host round found zero exact host-alias matches among 12087
public archive target strings. All five query results are retained.

Before any expanded catalogue query or spectral access, extend selection to
all NASA default PS rows with tran_flag=1 and sy_pnum>1. Group by host and
require at least two transiting rows; match host, HD, HIP and TIC identifiers
exactly after conservative normalization. Exclude the four previously searched
LS hosts (HD 219134, HD 260655, HD 63433, LHS 1140).

Inspect GBT primary-target cadence metadata for the nearest ten matched hosts
(distance ascending, then hostname). Retain empty outcomes. Advance the first
host in this order with two geometry-eligible planets and a complete medium
HDF5 sequence. Inherit the original header and spectral-freeze boundary.
This operational expansion is declared after a negative metadata round; it is
not an independent preregistered population test. No spectra have been read.
