# Independent closed VAL_A review — 8 October 2026

**FAIL_CLOSED. Pilot values remain unopened; A is not replayed.** All 142
distinct frozen identities have retained outcomes, but only 140 completed
successfully. Two required diagnostic cases exhausted their admitted CPU
budget. A partial panel cannot admit the telescope search.

The reviewer checked all 2818 existing case artifact hashes, 840 complete
maps, 43,209 retained OFF comparisons and 16,799 compatible veto witnesses.
Every retained map has the full 4096 ON / 4596 OFF carriers and 21,660 valid
hypotheses per carrier. Hit parameters and threshold membership equal their
maps; pre/final localized recovery agrees with independent endpoint arithmetic.
No generator, detector, RNG, source fetch or analysis replay was invoked.

| Family | Completed successfully / required | All-active pre-OFF recovery | All-active final recovery | Completed cadences with survivors |
|---|---:|---:|---:|---:|
| Strong | 14 / 14 | 14 | 14 | 14 |
| Operating | 48 / 48 | 46 | 46 | 47 |
| Matched RFI | 24 / 24 | 24 | 0 | 0 |
| Noise | 32 / 32 | Not applicable | Not applicable | 0 |
| Single-row transient diagnostic | 10 / 12 | 10 | 10 | 10 |
| Nearby OFF diagnostic | 12 / 12 | 12 | 0 | 0 |

The operating subgroups meet every frozen minimum: activity 8,7,8,8,8,7 of
eight; drift 11,12,12,11 of twelve; intrinsic widths 22/24 and 24/24. Eight
scientific count checks pass, while the complete-integrity check fails.
Completed single-row bursts surviving and all nearby-OFF injections being
vetoed are concrete scope limitations, not calibrated sky behavior.

Failed identities are `VAL_A:single_row_transient:010` (index 128) and `011`
(index 129), both in the full `SETI_RADIO_PILOT_20261008_` namespace. Their CPU
receipts are 250.485232 and 250.985458 seconds, above the admitted 250-second
partitions, with profiling-watchdog `TimeoutError`, false integrity/cap flags
and persistent failed claims. Each lacks six final maps and six other expected
search/recovery artifacts. The failures preserve truth, array hashes,
admissions, traceback and partial receipts. Their default zero-survivor fields
are not EMPTY results or successful rejection.

Actual charged A CPU is **11,143.686462 s**: the larger of job receipts
11,138.534412 and measured reaped children 11,143.517907, plus controller
0.168555. Maximum job wall is 252.30885764399864 s and peak RSS 82,063,360 B.
Both failed-job costs count; global remaining capacity after known jobs and
the conservative CI reservation is 25,492.071999981 CPU s. The unsuccessful
250-second allocations remain failures; no cap or result is relabelled.

The approved plan permits one development correction followed by entirely
fresh validation. A resource-allocation correction may retain all scientific
hashes, preserve A's failure, use new development identities, then validate
the untouched B bank once. Rolling reservations must protect each complete
active job and refuse new starts when a full partition cannot fit. They do
not guarantee completion of B. A failed correction/B or exhausted study cap
closes pilot admission and yields the actually computed method-study fallback.
