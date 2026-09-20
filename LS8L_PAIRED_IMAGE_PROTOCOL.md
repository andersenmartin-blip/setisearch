# LS8L — frozen paired CAL/COR image diagnostic for WASP-189

Status: **FROZEN BEFORE IMAGE PAYLOAD ACCESS**.

Metadata preflight and independent audit are public at
`b0a9d7d7780a026a579dbe44a4446f34d1196a0f`: all 174 CAL/COR joins pass,
with 803 exact checks and zero image bytes read. The exact ETags, object
identities, frame indices, source geometry and future ranges are frozen in
`config/ls8l_images.json`.

| Representative | L2 context (stop-exclusive) | Native CAL/COR frames | CAL bytes | COR bytes | Smearing bytes |
|---|---|---|---:|---:|---:|
| TG000201_P0 | 507:536 | 507:536 | 9,280,000 | 9,280,000 | 46,400 |
| TG000202_P0 | 664:693 | 664:693 | 9,280,000 | 9,280,000 | 46,400 |
| TG000202_N0 | 105:134 | 105:134 | 9,280,000 | 9,280,000 | 46,400 |

Total paired-image payload: **55,680,000 bytes**. Smearing payload:
**139,200 bytes**. Indices were established by native-time joins, rather than
assumed equal to L2 indices. Each context is 29 rows; local event index 14,
sidebands 0–11 and 17–28, and guards 12–13 and 15–16.

Use precisely the LS8D/LS8H `seti_repeater.cheops_image_pair.analyze` function.
No fitting basis, numerical tolerance, radius or closure threshold changes.
CAL, COR and DELTA=COR-CAL maps use the common finite pixel mask, both original
C0/C1 conventions, r<=25 apertures, 30<r<=40 background annuli and r>35
smearing regressions. The center uses only the saved sideband centroids and
the separately recorded window offsets for each visit.

Classification order:

1. **CORRECTION_LINKED:** complete apertures and matching COR/L2 sign in both
   conventions, with |DELTA/COR| or |column-DELTA/COR| >=0.5 in both.
2. Otherwise **SPATIALLY_STRUCTURED:** complete apertures and matching signs,
   with available COR displacement and brightness fits, displacement explained
   energy >=0.8 and its advantage over brightness >=0.2 in both conventions.
3. Otherwise **UNRESOLVED_WITHIN_FIXED_SCOPE**.

Run the seven existing synthetic tests before opening payloads. Require HTTP
206, exact range lengths and saved ETag/Content-Disposition on acquisition.
Identical-range transport retries are permitted (at most three); identity or
contract mismatches stop immediately. Save compressed original bytes and
receipts. The independent struct/long-double/scalar auditor then rechecks
joins, raw values, maps, masks, fits and all classifications at the unchanged
relative 2e-8, native absolute 1e-6 and dimensionless absolute 1e-8 tolerances.

Publish every outcome and audit, including failures. Figures read only retained
outputs and never affect classification. These labels do not uniquely identify
physical cause, astrophysical/artificial origin or detector qualification.

Do not widen image rows, change apertures, add visits or open raw imagettes.
If all three branches close under the two descriptive gates, continue to rank
2 of the reconciled LS8J ledger under a new exact-pair/header freeze. If any is
unresolved, preserve that status and specify the concrete remaining limitation
before separately freezing a diagnostic on already retained data. An unresolved
label does not promote a SETI candidate. No unused TESS or M43 panel is opened.
