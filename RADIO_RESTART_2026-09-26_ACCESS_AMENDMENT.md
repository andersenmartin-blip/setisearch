# Radio metadata access amendment: canonical catalogue scheme

The initial frozen run `c0c1e07cc44162b4da8dbf07b39575bfdaefc1f8` stopped both
independent tasks at the first API request. The archive returned redirects
from the HTTPS cadence URL and target-list URL to the same HTTP host, path and
query. The code refused to follow either redirect, as required. Two requests,
zero response-body bytes and no HDF5 source access occurred. The result and
transport receipts are preserved unchanged in the parent result directory.

This amendment is a transport compatibility correction before new metadata
or spectra, not a retry of a scientific result. The historical M36 catalogue
already identifies `http://seti.berkeley.edu/opendata/api/get-cadence/--71139`.
Use that explicit public API scheme for cadence, target-list and target queries.
Allow HTTP only on this exact host and `/opendata/api/` prefix, with no credentials.
All HDF5 product requests remain HTTPS on `bldata.berkeley.edu`. Redirects still
fail closed; a second transport obstruction is reported, without changing
hostnames, proxies, authentication, source identities or the scientific scope.

The original selection, six-source pin, HD 3651 query scope, caps and eligibility
are unchanged. Cumulative byte/request/runtime accounting includes attempt 1.
Attempt 2 writes a separate `results_radio_restart_2026-09-26/attempt02/`
directory, verifies this amendment and the old result against its published
freeze, and cannot overwrite either result. The original metadata-only protocol
continues to apply except for the explicit API scheme above.
