# LS4O: independent-control feasibility after LS4N

This metadata-only study determines what the current LHS 1140 archive can
offer for repeatability and pointing checks. It does not promote any LS4
feature, open a reserved HTR product or change acceptance rules.

## Previously available evidence

Use hash-pinned LS4A headers and the LS4H scan partition to compute all six
X-band scan start/end times and the five original ON/adjacent-OFF angular
separations, gaps and overlaps. Decode SIGPROC packed HHMMSS.S and signed
DDMMSS.S explicitly and use spherical angular separation. Coordinates are
the recorded pointing coordinates; no beam response or pointing-accuracy
model is inferred. Compare native center extents of all four known bands
with the two LS4I digital-injection frequencies.

Distinguish development A1/B1, bridge A2 and reserved-validation A3/C1/D1.
All six medium-resolution products were previously searched. Only the A1/B1
HTR products have been read in the development stream; the other HTR products
remain unopened here. A separate file is not automatically an independent
epoch, and prior medium exposure is not erased by HTR reservation.

## Expanded live archive scope

Freeze the ten archive aliases already listed in the LS3 target configuration.
For each alias query the public Berkeley `query-files` endpoint with only
`target` and `limit=3000` parameters. No telescope, cadence or primary-target
restriction is explicitly supplied. Add one control query reproducing LS4D's
GBT/cadence=True/primaryTarget=True request for `LHS1140`.

This is an expansion beyond the earlier single-alias restricted query. It
does not assume undocumented API defaults, exhaustive alias coverage or
coverage of other archives. Compare returned URLs with the restricted query
to document whether target-only requests actually expose additional products.
Filter returned target names against the normalized frozen aliases, preserve
all responses and mismatching-record counts, deduplicate exact product URLs,
and flag conflicting metadata or a reached record limit.

Group metadata by telescope, normalized target, exact scan MJD and frequency
center rounded to the nearest 100 MHz. This is an inventory grouping, not
header-confirmed frequency coverage. Flag every group whose product centers
are all 8–12 GHz and whose start is at least 24 hours from the original X-band
start. These are possible independent-epoch follow-up leads, not validated
cadences or evidence of statistical independence. Retain groups regardless
of product readiness; annotate availability of medium and HTR product suffixes.

Perform exactly eleven requests, one attempt each, 20 s timeout and at most
2,000,000 response bytes per request (one extra byte may detect overflow).
Never open a linked radio product. Save each response and a checkpoint before
the next request. A failed query, reached record cap, metadata conflict or
missing restricted-query URL makes the scoped inventory incomplete; a missing
lead is then not a completed exclusion. The runner refuses an existing output
directory and retains any abort.

## Decision boundary

If a new >=24-hour X-center lead appears, the next task is a separate header
and cadence-adjacency preflight before spectral access. If none appears in a
complete scoped inventory, state that limited negative result. Same-session
HTR validation can test method transport under a separately frozen protocol,
but cannot be sold as independent-epoch confirmation. Other bands cannot
confirm a signal outside their observed frequency support.

Report the exact query scope, completeness, cadence/time/pointing geometry,
spectral overlap limits and reserved-data budget. No beam-response fit,
physical sensitivity, false-alarm probability or new sky candidate follows.
Freeze code, tests, config and input identities before the live query run.
