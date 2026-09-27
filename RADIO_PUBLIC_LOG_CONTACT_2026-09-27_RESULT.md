# HD1461 public log row and unsent archive request

**Result: a new public target-level row was obtained; original scan pointing
provenance remains unresolved.** The metadata-only lookup declared in the
[scope](RADIO_PUBLIC_LOG_CONTACT_2026-09-27_SCOPE.md) is closed.
`HOLD_POINTING_PROVENANCE_UNRESOLVED` persists. No spectrum was opened.

## New source and exact returned values

The official [Berkeley Listen page](https://seti.berkeley.edu/listen/) links
the [Breakthrough Listen GBT Log](https://docs.google.com/spreadsheets/d/1f8Gzx67_0KN2eP4whE4Qcdj8iSTRSuRZFnXthWRcVB0/edit).
On 27 September 2026, one public query selected A:G for `A = 'HIP1499'`, limit
10, on the first sheet. HTTP 200 returned **one row in 652 bytes**. Its raw
response is retained unchanged, SHA-256
`906ec1a0c2c792373dd7f3972dfabee694bd43315f3a16bff96a957d1c5856ef`.

| Source column label | Returned value |
|---|---|
| Name | HIP1499 |
| RA (hours) | 0.31175 |
| Dec (degrees) | -8.053611 |
| L-band Dates observed | 2016-05-14 16:58:31 |
| S-band | 2016-10-13 08:33:13 |
| C-band | 2017-09-03 08:47:37 |
| X-band | -- |

These are source strings, including the X-band marker. No observation was
selected from the other bands, and the query did not examine other worksheets.
The [exact response](results_radio_public_log_contact_2026-09-27/retrieval_01/response.txt),
[parsed row](results_radio_public_log_contact_2026-09-27/retrieval_01/target_rows.json)
and [receipt](results_radio_public_log_contact_2026-09-27/retrieval_01/transport_receipt.json)
retain the source labels and read details. Google's
[documented public query interface](https://developers.google.com/chart/interactive/docs/spreadsheets)
was used without credentials, edits or full-workbook export.

## Why this does not resolve the hold

The row gives no session ID, scan IDs, original filename, coordinate frame,
epoch, commanded/measured distinction, conversion history or timestamp timezone.
Its independence from a catalogue or the derived archive metadata is unknown.
The displayed L-band time is six seconds earlier than the rounded UTC header
time for scan 0019 **if the clocks are assumed comparable**; that conditional
numeric comparison does not identify a scan or establish the clock convention.

The row's declination is only 0.03456 arcseconds from the retained catalogue
declination. Its declination differences from the three retained ON headers
remain approximately 34.233 arcminutes. These are scalar declination
comparisons, not a new astrometric fit or proof of actual telescope pointing.
All arithmetic uses the retained preparation contract; no product was reopened.
The sheet therefore supplies a useful question for the archive custodian,
but cannot authorize a coordinate correction or spectral access.

## Concrete request prepared

A complete [English metadata request](RADIO_HD1461_ARCHIVE_EMAIL_DRAFT_2026-09-27.md)
now lists all three exact filenames and UTC start times, the discrepancy, the
minimum original evidence needed and the new sheet-row provenance question.
It is **unsent**, in accordance with the owner's explicit instruction against
external messages. No email/ticket was submitted, and no sending capability
was established in this session.

The official [Berkeley collaboration page](https://seti.berkeley.edu/jobs.html)
publishes `bsrc@berkeley.edu`. This was verified on 27 September 2026 as a
general institutional contact, not a dedicated archive helpdesk or a verified
custodian. The draft requests routing; no individual or CC address is guessed.
The official [GBO help page](https://greenbankobservatory.org/portal/help/)
links `https://help.nrao.edu/` as an alternative support route. No login was
attempted. General [GBO archive policy](https://greenbankobservatory.org/portal/policies/)
does not establish that this BL session's original data are retained or available.

## Resource accounting and checks

The row lookup used one direct GET, 652 response-body bytes and 12.798 seconds
elapsed, with zero redirects and no authentication. The prior direct GBO
help-page read used one GET and 222,967 bytes. Thus this continuation's **known
direct web bodies total 223,619 bytes across two reads**. Discovery/contact and
documentation reads through the web reader have unknown transport totals;
they are recorded separately and are not claimed to be zero. This is metadata
research, not telescope acquisition or scientific evaluation expenditure.

An independent offline check compares the raw response with the parsed JSON,
verifies the scope/script snapshots, reconciles the three scan identities in
the draft with the retained contract and checks fifteen prior input pins.
The response is assessed without executing its JavaScript wrapper. Closed
synthetic tests, ledger entries and scientific panels were not replayed.
The [result and offline verification](results_radio_public_log_contact_2026-09-27/)
and `RESULTS_MANIFEST_RADIO_PUBLIC_LOG_CONTACT_2026-09-27.sha256` retain evidence.

New telescope product requests, source headers read from data files, spectra,
reservations, calibration/evaluation trials, target replacements and external
messages are all zero. Original preparation, the exhausted acquisition ledger,
empty telescope genesis, neighbor9 and all five blockers are unchanged.
The 3-calibration / 24-case / 1-evaluation / 0-remedy allowance is unexecuted.
M43AI remains failed/closed; original 112+128 M43AF holdouts untouched;
M15 GJ581 and M33 HD3651 unresolved; LS paused at LS8BD–LS8BE, LS8BF untouched;
CHEOPS unsent.

## Exact continuation

Do not repeat this row query, the closed directory inspection, catalogue/code
diagnoses or generic engineering tests as progress. The missing pointing input
is still an original same-scan RAW/FIL header, GO/observing record or documented
deployed conversion with original input bytes for ON 0015/0017/0019.
The request is ready for the owner to review and send, or to authorize sending
through an available channel. No such authorization or sending is inferred.
A supplied record or genuinely new public original-record link can reopen a
bounded provenance check. The source/observer physics and independent live
admission requirements also remain; a reply alone does not open spectra.
No unblocked telescope step is established. Consolidate on 9 October without
extending the plan or manufacturing repeated empty work.
