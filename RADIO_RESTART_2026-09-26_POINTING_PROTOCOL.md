# Bounded HD 1461 pointing-provenance diagnosis

The completed six-file identity/header check passed its frozen catalogue,
size, ETag and geometry conditions. A separate comparison with the newly
retrieved official HD 1461 record now exposes a contradiction: all three ON
headers have declination approximately −8.62416 degrees, while the official
record gives −8.0536206 degrees. The angular separation is approximately
34.23 arcminutes. This is an observed metadata inconsistency, not a new signal
criterion or a reason to tune a detector. Spectral readiness is **ON HOLD**.

The currently pinned Blimpy HDF5 reader interprets `src_dej` as degrees and
`src_raj` as hours. Its historical SIGPROC converter does not establish an
alternative HDF5 encoding or a file-specific correction. Exact upstream
commit and blob identities are in `coordinate_format_sources.json`.
Do not apply a numerical correction chosen to make the target agree.

This diagnosis uses the retained six headers and official catalogue record
to calculate the separation independently with a spherical formula and Astropy.
It also makes one bounded **target-only** public archive query for HIP1499 on
GBT, with no cadence, resolution or file-format filter, limit 2000 rows.
Preserve the complete response. Hitting the cap or a schema/access failure is
an incomplete diagnostic, not proof that an original product is absent.

Identify original `.fil` or `.raw` products only when both target identity and
start MJD match one of the three selected ON scans. Record all exact matches.
This script reads catalogue JSON only; it does not open those products, other
observations or any spectral data. If no matching original is listed, report
the bounded obstruction. If originals exist, their exact identities become
the input to a separately fixed header-only verification. Do not substitute
another target or cadence in this package.

The added scope has at most 2 MiB of JSON, two requests only on transient errors,
25 seconds per request and a 60-second active request budget. Use the explicit
canonical HTTP API endpoint already verified in attempt 2, without credentials
or redirects. Publish this protocol, script and its retained inputs before
execution. Existing results, controls, source identities and candidate labels
remain unchanged. No message to an archive maintainer is sent.
