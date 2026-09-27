# Owner-authorized alternate radio data: bounded metadata screen

Declared prospectively on 27 September 2026. Source checkpoint:
`54608c8a8ffbd7d55c77d63a569dcdc83b95f747`.

## Changed direction, preserved evidence

At 22:26 Europe/Copenhagen the owner explicitly directed: do not send messages;
continue with other data. This authorizes moving beyond HD1461. It supersedes
the earlier instruction to stay on that target and the restart protocol's
prohibition on inspecting rank 41. It does not rewrite that completed protocol,
resolve HD1461's pointing discrepancy, change a failed evaluation or authorize
external contact. The archive and CHEOPS requests stay unsent.

Ordinary narrowband radio SETI remains the active track. The plan ends on
9 October; no added targets beyond its three-sequence shortlist are authorized
here. HD1461/71139 retains the first slot and its unresolved hold. This package
allocates the two remaining slots to the following metadata-only alternatives.

## Selection before any new remote read

Reuse the original M16 discovery snapshot and M36 unique-host normalization:
keep the first occurrence of each alphanumeric-normalized host, in the published
order. Ranks 1–40 have already been disposed or reserved. Among remaining ranks,
admit historical primary records with catalogue centre frequency in the fixed
interval [1200,1700] MHz. Order by host rank, then MJD, then numeric cadence ID.
This is an L-band catalogue screen; only current headers can prove coverage.
No amplitudes, spectra or old candidate outcomes enter this choice.

| Order | Original rank | Target | Cadence | Session/date |
|---|---:|---|---:|---|
| 1 | 41 | HD 189733 / HIP98505 | 85030 | AGBT16A_999_97, 2016-03-17 |
| 2, reserve | 43 | GJ 724 / HIP91608 | 73005 | AGBT16A_999_220, 2016-06-13 |

Rank 42 (GJ 740) has only an S-band record in this snapshot. The other records
for ranks 41/43 also fail this catalogue-centre criterion. These exclusions
are metadata eligibility decisions, not new spectral or archive-absence results.
Both admitted sessions/dates differ from HD1461 and M43 development.

Rebuild a conservative deny-list from every committed JSON configuration at
the source checkpoint, preserving URL-to-config provenance and file hashes.
This includes reserved inputs and is not a claim that all listed data were
consumed. Reject a complete new cadence if any fine product overlaps the list.

## Exact allowed operations and qualification

Use the two explicit canonical HTTP catalogue URLs in the new config. This
follows the already published public-API scheme amendment; never follow a
redirect or attempt authentication. Require exactly six distinct fine HDF5
URLs, including the frozen primary URL, within the expected HTTPS session
holding directory. Pin the returned current catalogue before opening headers.

For each admitted product use HEAD then exact conditional byte ranges for
HDF5 attributes/geometry only. Require a strong ETag, consistent size, exact
206 Content-Range and unchanged identity. Read no dataset element, decompress
no spectral chunk and do not plot, normalize or score data. Record root/data
attributes, shape, dtype, chunks and HDF5 filter declarations. Metadata reads
can include adjacent container bytes; they are not a spectral extraction.

Require three alternating ON scans with the selected target and three OFF
scans whose source differs from the ON target, matching telescope/backend and spectral/time
geometry, non-overlapping integrations, span at most 0.04 day and coverage
of 1399.65–1425.85 MHz. Reuse the unchanged qualification and range-reader
functions, but do not adopt old thresholds, widths or coverage claims.

After geometry qualifies, perform one exact selected-planet query to the
official NASA Exoplanet Archive, using the config's explicit URL and columns.
Require one matching planet/host/HIP identity, finite RA/Dec, and compare each
ON header direction (RA hours, Dec degrees) against the returned direction.
The fixed proximity tolerance is 60 arcseconds, without an assumed epoch
propagation. This screens gross identity/coordinate mismatches; it is not
sub-arcsecond astrometry, independent confirmation of measured pointing, or a
full physical motion model. Preserve missing physical fields as missing.

Select the first sequence that completes this metadata/proximity screen.
Stop before reading the reserve when the first qualifies. If the first fails
or cannot be assessed, retain its exact technical/metadata disposition and
assess the predeclared reserve without labelling the first an astronomical
null. No further substitution is permitted in this package. No response may
change the ordering, tolerance, band, target identifiers or budget.

## Bounded resources and publication

This new allocation is at most 200 HTTP attempts, 8 MiB response bodies and
1200 active seconds across both alternatives, with one attempt per request,
25-second maximum socket timeout, 4 MiB per catalogue/NASA response, and
512 KiB of metadata reads per product. Limit overflow sentinel bytes are
included in accounting. No auth/identity failure retry. Charge requests before
transport and preserve every response, error and stopping condition. The output
directory is exclusive; an interrupted attempt may not be restarted with reset
counters. A future recovery must reconcile its retained receipt state first.

The completed restart used 83 requests, 263,066 bytes and 625.844791 seconds.
Retain those unchanged as the preceding source-screen allocation. The combined
two source-screen allocations cannot exceed 283 attempts, 8,651,674 bytes and
1825.844791 active seconds. Other prior metadata investigations remain separately
accounted; web-reader wire totals are unknown, not zero. These are metadata
budgets, not a reset of the closed/exhausted synthetic acquisition ledger or an
activation of the empty telescope ledger. No scientific trial is allocated.

Publish and verify this protocol, selection/config, current deny-list, code
and new boundary tests before execution. The executable requires that published
commit and verifies exact file hashes before any network request. Preserve the
complete outcome, including failed alternatives, source identities and limits.

## Advancement boundary

Success yields a new preparation-only source contract, never a rewrite of
HD1461's contract to ready. Before any spectrum, the new source still needs an
integrated published protocol with exact frequency windows, motion/width bank,
fresh disjoint development/calibration/evaluation identities, recovery/RFI/null
gates, codec/runtime evidence and cumulative acquisition/trial budgets. Primary
remains neighbor9. Transfer none of HD1461's physical support or source receipts.
Do not run the previously unexecuted control panel under a new identity.

M43AI stays failed/closed; original 112+128 M43AF holdouts stay untouched;
M15 GJ581 and M33 HD3651 stay unresolved. Preserve every earlier disposition,
LS8BD–LS8BE pause, untouched LS8BF and unsent CHEOPS request. No messages,
bookings, paid services or additional automations are authorized.
