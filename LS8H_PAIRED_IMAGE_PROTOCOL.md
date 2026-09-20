# LS8H — frozen GJ 849 paired CAL/COR image diagnostic

Status: **FROZEN BEFORE IMAGE PAYLOAD ACCESS**.

The metadata-only preflight for the single LS8G positive cluster completed
without opening image pixels. All 29 L2 context rows (61–89) have unique
CAL and COR native exposure joins, for 58 verified joins in total.

The exact future payload is frozen by `config/ls8h_images.json`:

- CAL image planes: 29 contiguous native frames;
- COR image planes: the matching 29 native frames;
- COR smearing rows: the matching 29 rows;
- paired image bytes: **18,560,000**;
- smearing bytes: **46,400**.

Representative and L2 context remain unchanged:

- visit: `CH_PR100018_TG032401_V0300`
- sign: positive
- cluster: 0
- representative start row: 75
- duration: 1 row
- fixed L2 score: 23.4700798115
- context: rows 61–89
- sidebands: local rows 0–11 and 17–28
- guards: local rows 12–13 and 15–16
- event: local row 14.

## Fixed image diagnostics

Reuse the LS8D paired-image implementation and semantics without fitting a new
gate to GJ 849:

- build CAL, COR and DELTA=COR-CAL temporal event maps;
- use the native 200x200 image geometry and recorded window offsets;
- evaluate both predeclared coordinate conventions C0 and C1;
- r<=25 source aperture, 30<r<=40 background annulus;
- fixed column-constant DELTA projection;
- fixed smearing-row regression;
- fixed brightness and displacement spatial regressions.

Classification order is unchanged:

1. **CORRECTION_LINKED** if both coordinate conventions have complete source
   apertures, the COR event sign matches the positive L2 excursion, and either
   |DELTA/COR| or |column-DELTA/COR| is >=0.5 in both conventions.
2. Otherwise **SPATIALLY_STRUCTURED** only if the already frozen displacement
   gate passes in both conventions.
3. Otherwise **UNRESOLVED_WITHIN_FIXED_SCOPE**.

These are diagnostic labels, not astrophysical/artificial classifications.

## Integrity and stopping rules

Require exact HTTP ranges, saved ETags and Content-Disposition identities.
Persist the compressed raw ranges and receipts. Run the existing seven
synthetic paired-image tests before acquisition and an independent
long-double/scalar audit afterward.

Do not open a second GJ 849 visit, alternate aperture, raw imagette or any
additional image row in response to this outcome. Publish the result whether
correction-linked, spatially structured or unresolved.
