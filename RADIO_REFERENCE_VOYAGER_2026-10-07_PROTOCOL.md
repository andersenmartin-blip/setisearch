# Voyager engineering reference protocol — 7 October 2026

Status: **FROZEN, ONE ENGINEERING INVOCATION; NO PILOT AUTHORITY**.

This is the first concrete execution package supporting the separately
authorized [10–23 October plan](RADIO_TWO_WEEK_PLAN_2026-10-10.md). It uses the
official Voyager-1 test product named by UCBerkeleySETI/blimpy and turboSETI.
Voyager is an already public, already analysed engineering reference. It is
excluded from development/validation/pilot novelty and from any sky-candidate
claim. HD189733 and every alternate pilot value remain unopened.

## Immutable inputs and expected result

- Source URL: `http://blpd0.ssl.berkeley.edu/Voyager_data/Voyager1.single_coarse.fine_res.h5`.
- Official declaration: blimpy `tests/download_data.sh` at commit
  `3ebf04342227a95405aa32e5bc75832d1dd17f28`; turboSETI uses the same HDF5 in
  its README and tests at commit `7d9b4fde9bc98d834dc11cfc0acd2380e6676f0e`.
- Expected source/shape: Voyager1, `[16,1,1048576]`, with the exact frequency,
  time resolution and MJD fields frozen in
  `config/radio_reference_voyager_20261007.json`.
- Search: turboSETI 2.3.2, maximum drift 4 Hz/s, S/N 25. The three published
  reference hits at 8419.319368, 8419.297028 and 8419.274374 MHz, with their
  published S/N values, must each match once within the official test's stated
  tolerances. Additional reported hits are retained.
- Output: complete DAT file, a waterfall covering the three known signals,
  source SHA256/byte count and redirect, exact environment, command log,
  result/failure JSON and SHA256 manifest. The downloaded HDF5 is deleted after
  analysis and is never committed.

The official distribution does not publish a checksum in the inspected source.
Therefore this single bootstrap run may record one complete observed SHA256; it
may not call that hash independently known. Any reproduction must freeze that
observed hash prospectively before downloading.

## Limits and failure rules

One invocation only, 20-minute job timeout, 300-second download timeout,
40,000,000-byte minimum and 256-MiB received/artifact caps. Redirects may remain
only on `blpd0.ssl.berkeley.edu`. An unexpected host, file size, header, output,
hit, package failure or timeout closes the invocation as failed. There is no
automatic retry; a distinct later action must first classify the cause under
the new plan's two-route/90-minute limits.

The workflow stores results as an Actions artifact regardless of success and,
when repository write access works, publishes only its result directory and a
generated result report on `m43-support-qualification`. A publication failure
does not authorize repeating the analysis. The artifact/run identifiers remain
the recovery path.

## Non-authority

Passing demonstrates that one ordinary Linux runner can install the frozen
stack, download a bounded authentic telescope test array, read it with blimpy,
run turboSETI and preserve outputs. It does not approve a pilot source, band,
threshold, OFF rule, validation panel or scientific result. It does not satisfy
the planned fresh signal/RFI/noise gates. No old 112+128 holdout, inactive
127/24 allocation, HD1461 hold, unresolved candidate, LS or CHEOPS state changes.

Eight local contract tests must pass before publication. They exercise the new
risks: JSON ambiguity, authority promotion, URL escape, exact header binding and
missing/changed known reference hits. They do not replay a historical scientific
or native test.
