# LS8P publication record — 20 September 2026

Published under the standing authorization for SETI code, data, protocols,
reports and logs in `andersenmartin-blip/setisearch`, science branch
`m43-support-qualification`, with the current overview on main. No messages
were sent to people and no new archive science data were acquired.

| Checkpoint | Commit |
|---|---|
| Previous LS8O status / continuation | `b9108033d537136043209b4ec00a461fbed098d8` |
| LS8P method, code, audit, tests and workflow freeze | `cbee527850ef9d6bc392506cd958961321e0ec5f` |
| Complete producer output; audit serialization failure preserved | `16824ada23afb9c8e66758d2a180a565326f443c` |
| Serialization-only repair and recovery workflow freeze | `f90519d7d1cda3594b5c42fb68cde9238734f443` |
| Complete verified result, independent audit and figures | `65c2f1a0c1da8a7a63c9ace8ca9f06af4c9b491a` |

[Initial run 35523089953](https://github.com/andersenmartin-blip/setisearch/actions/runs/35523089953)
correctly concludes failure. Seventeen tests and the complete native producer
finished, but the independent reference could not serialize NumPy integer
boundary coordinates. Its original scientific status remains
**COMPLETE_UNAUDITED** in `results_ls8p_residuals`.

[Recovery run 35523384774](https://github.com/andersenmartin-blip/setisearch/actions/runs/35523384774)
concludes success, and its scientific status is separately verified as
**COMPLETE_AUDITED_DESCRIPTIVE_ONLY**. The recovery converts only boundary
coordinate scalar types to Python integers and adds one exact regression
test. Original scientific code, raw inputs, arithmetic, tolerance and the
initial failed result are preserved. The producer is not rerun. Twenty
copied input files are recorded in `COPY_RECEIPT.json` before the audit and
report; status metadata is then advanced only in the new output directory.

The final directory is **`results_ls8p_verified`**, with 35 manifest-listed
files: copied model arrays and full diagnostics, all signed controls,
independent reference/controls/audit, the report and five figures, original
producer/test logs, recovery log/test, environment, copy receipt, execution
status, summary and next action. The initial directory remains immutable.

All five contexts, 20 native product/convention cases, 160 held three-row
cases and 320 signed injections are retained. Final audit **PASS**:
**1,400,704 numerical comparisons and 1,529,059 exact checks**, no
disagreements, maximum discrepancy 0.000041389 of the frozen tolerance.
All 120 signed pure-template answers and all additive tests meet their
unchanged 1e-9 bound. The audit counts include duplicate consistency checks;
they are not independent scientific samples.

The local review copies of the report, summary, status, audit, copy receipt,
full diagnostics, injections, original test log, recovery test log and all
five figures match their immutable SHA-256 manifest. Every figure has been
visually inspected. No extra native-data calculation, mask change or figure
rescaling was used to change an outcome during review.

All five LS8O labels remain unresolved. Local three-row variability and the
exact C0/C1 boundary contribution have been quantified; no unique physical
cause is assigned and no event is promoted. The study is closed. The
independent rank-3 HD 136352 transfer is the next planned step, requiring
separate metadata and science-byte freezes before any new science values.

[Immutable verified report](https://github.com/andersenmartin-blip/setisearch/blob/65c2f1a0c1da8a7a63c9ace8ca9f06af4c9b491a/results_ls8p_verified/REPORT.md) ·
[Current scientific interpretation and continuation](LS8P_CONTINUATION.md) ·
[Scientific protocol](LS8P_THREE_SUM_PROTOCOL.md) ·
[Recovery protocol](LS8P_AUDIT_RECOVERY.md) ·
[Current project status](PROJECT_STATUS.md).
