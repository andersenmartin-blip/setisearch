# Voyager engineering reference review — 7 October 2026

Status: **ORIGINAL RUN FAILED CLOSED; RETAINED OUTPUT REVIEWED WITHOUT REPLAY**.

The prospectively frozen package at `5b1e23e13252a17c2ef30fd2320f1cd93bcb2e31`
ran once in [workflow 37666576130](https://github.com/andersenmartin-blip/setisearch/actions/runs/37666576130).
The workflow installed Python 3.10.15, blimpy 2.1.4 and turboSETI 2.3.2,
read the public Voyager HDF5 with the exact frozen header, and completed the
turboSETI search. It retained a three-row DAT and complete command/install/test
logs in result commit `f929b11d4d390b72b82165c89eb950ffd8b9c49e`.

The original run remains `FAILED_CLOSED`. Its exact error was
`reference hit SNR mismatch`: the middle hit was 245.709610 rather than the
frozen 245.707984, a difference of +0.001626 against the package's strict
absolute tolerance of 0.001. The other S/N differences were +0.000205 and
+0.000206; all three retained frequencies exactly match the frozen six-decimal
values. No setting is changed and the run is not repeated.

## Validator discrepancy

The package incorrectly described its strict absolute comparison as the
upstream test's complete tolerance. The pinned upstream test actually calls
`numpy.isclose(actual, expected, atol=0.001)` without overriding its default
relative tolerance of `1e-5`. The independently pinned source is
UCBerkeleySETI/turbo_seti commit
`7d9b4fde9bc98d834dc11cfc0acd2380e6676f0e`,
`test/test_turbo_seti.py`, blob
`475e6d7ac728bd6ab3fd65bc8c95c1d91714394a`.

The deterministic post-hoc audit verifies all eight original manifest members
and applies both rules only to the already retained DAT. Exactly one row fails
the original absolute S/N rule. Zero frequency and zero S/N rows fail the actual
upstream `isclose` rule. This explains the incompatibility; it does not convert
the original run to pass, authorize a retry or constitute new reference/science
execution.

## Evidence limits

The failure path deleted the transient HDF5 as required but wrote the transfer
receipt only on success. Consequently source byte count and SHA256 were not
retained. The failure also occurred before waterfall creation. Runtime CPU/RAM
and search-only duration were not measured. The complete workflow lasted about
521 seconds; the compressed Actions artifact was 7,976 bytes and the nine
committed result-directory files total 19,703 bytes.

This is partial engineering capability evidence: the runner installed the
stack, read an authentic telescope array with the frozen header and produced
the expected three-frequency turboSETI output. It is not a completed reference
package because its frozen gate failed and the source receipt/waterfall are
absent. HD189733, every pilot value, all fresh validation identities and the
historical holdouts remain unopened. No scientific or pilot authority changes.

Exact continuation: do not replay this route or relax its disposition. At the
new plan's start, freeze a distinct second engineering route before invocation,
with transfer receipt written immediately after download and before later
validation, waterfall creation before compatibility judgment, measured resource
fields, and validator semantics copied exactly from a pinned upstream source.
That is the final available infrastructure route under the two-route limit.
Pilot-source and validation contracts remain later, separate gates.
