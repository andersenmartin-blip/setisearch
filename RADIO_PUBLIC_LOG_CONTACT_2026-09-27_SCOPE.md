# HD1461 public observing-log lookup and unsent contact preparation

Declared on 27 September 2026 before the targeted row request, from science
commit `b2ad32adf074b3ac85be92838f8b1a4348f6ab51`.

The official Berkeley [Listen page](https://seti.berkeley.edu/listen/) links
the public [Breakthrough Listen GBT Log](https://docs.google.com/spreadsheets/d/1f8Gzx67_0KN2eP4whE4Qcdj8iSTRSuRZFnXthWRcVB0/edit).
The web reader exposed only its opening rows. This previously unexamined link
justifies one bounded lookup for the selected target, not a new catalogue sweep.

Query only columns A:G where A equals `HIP1499`, limit 10 rows, on the default
first sheet. Use the documented public Google Visualization query interface
with two header rows. Make at most one direct GET, no retries or redirects,
30-second socket timeout, at most 65,536 response-body bytes plus one overflow
sentinel byte. Retain the exact response and receipt. No credentials, sign-in,
workbook changes, full-workbook export, telescope product or spectrum access.
An error or absent row closes this particular lookup without an absence claim
about other worksheets or the underlying observatory archive.

Assess whether a returned row independently identifies AGBT16A_999_189 and
ON scans 0015/0017/0019 with original pointing units/frame and time provenance.
A target-level date/direction alone cannot resolve the existing pointing hold.
Do not adopt coordinates, repeat converter investigations or change targets.

Also prepare an actual unsent metadata-only request using the existing
[retrieval specification](RADIO_HD1461_PROVENANCE_REQUEST_2026-09-26.md).
Verify a public institutional contact from its official site; label a general
routing address accurately, with no guessed individual or CC list. Preserve
the user's prohibition on sending external messages.

Discovery/contact web reads preceded this scoped row query. Their underlying
wire totals are unknown and must not be called zero or charged as telescope
acquisition. One earlier direct GBO help-page read returned 222,967 bytes;
only its routing-link observation was retained, not its body or a body hash.
The row-query receipt supplies its own measured direct request/body totals.

All five science blockers, neighbor9, the original preparation contract,
exhausted synthetic ledger, empty telescope genesis, frozen trial/resource
caps and prior dispositions remain in force. No closed test or scientific
panel is rerun. Finish with the exact missing-input frontier; do not open an
unbounded metadata search or extend the two-week plan.
