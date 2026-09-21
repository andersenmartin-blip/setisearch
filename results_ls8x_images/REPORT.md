# LS8X — GJ 436 positive-event paired-image follow-up

Completed 21 September 2026. **COMPLETE_AUDITED**, independent audit **PASS**.

The separately frozen diagnostic retains the complete LS8W signed representative
set: one positive and zero negative events. No representative is added or substituted.
The image outcomes are: **{"CORRECTION_LINKED": 1}**.
These are descriptive image labels, not a determination of artificial or
astrophysical origin, and not detector qualification or a SETI-candidate claim.

| Representative | Sign | Fixed classification | DELTA/COR C0 / C1 | COR brightness explained C0 / C1 | COR displacement explained C0 / C1 |
|---|---|---|---:|---:|---:|
| TG000302_P0 | positive | CORRECTION_LINKED | -2.08927 / -2.00164 | 3.82004% / 3.78564% | 39.02952% / 39.02890% |

The positive representative is TG000302 row 33, one 60-second exposure,
with NEXP=1. Its original L2 score is +9.634235209975396, not a Gaussian
significance. Both selected visits' complete signed cluster sets were checked;
no image was acquired for the zero-crossing second visit.

## Scope and method

The metadata-only preflight established **58 unique CAL/COR exposure joins**
for the 29 fixed L2 context rows, with <=1 ms MJD/BJD differences and exact UTC
and CE agreement. The public config fixed every source identity and future
range before image access. The run acquired exactly
**18,560,000 paired image bytes** and
**46,400 smearing-row bytes**.

The unchanged LS8D/LS8H method constructs CAL, COR and DELTA=COR-CAL temporal
event maps on the common finite mask. It retains the original 12-row sidebands,
two-row guards, both coordinate conventions C0/C1, r<=25 source aperture,
30<r<=40 background annulus and r>35 smearing regression. Source pixel centers
come only from the saved sideband centroids; none is moved to fit the event.

CORRECTION_LINKED is evaluated first: complete apertures and matching COR/L2
signs in both conventions, plus |DELTA/COR| or |column-DELTA/COR| >=0.5 in both.
Otherwise SPATIALLY_STRUCTURED requires displacement explained energy >=0.8
and an advantage >=0.2 over brightness in both conventions. Remaining events
are UNRESOLVED_WITHIN_FIXED_SCOPE. Missing/rank-deficient fits stay unavailable.

A correction-linked label identifies material coupling to delivered processing;
it does not identify one physical correction component or exclude source
variability. A spatial label identifies a morphological fit, not a unique
physical cause. An unresolved label does not establish that the event is
astrophysical or artificial.

## Verification

The nine existing synthetic image tests, including one/three-row known-answer
controls and brightness preservation in both signs, run unchanged before
payload access. The independent
struct/long-double/scalar-normal-equation audit checks source ranges and
hashes, metadata joins, masks, event maps, fits and classifications:

- numerical comparisons: **94,537**;
- exact checks: **160,581**;
- disagreements: **0**.

LS8W's L2 audit remains PASS. Historical LS8B's original FAIL and later
arithmetic repair remain unchanged. This is diagnosis of already selected
events, not an independent sensitivity or false-alarm calibration. Raw
imagettes, alternative apertures and additional visits remain unopened.

[Summary](summary.json) · [all diagnostics](diagnostics.json) ·
[independent audit](audit.json) · [independent reference](independent_reference.json) ·
[checksums](SHA256SUMS).

## Event maps

Each three-panel figure uses one common signed scale for its representative.
Solid/dashed circles show the C0/C1 apertures. Figures are presentation only;
they do not feed the diagnostic or any threshold.

### TG000302_P0

![TG000302_P0: CAL, COR and DELTA event maps](TG000302_P0_CAL_COR_DELTA.png)

## Next action

Close this GJ 436 follow-up under its fixed descriptive label without widening. The next independent target is rank 7 of the unchanged reconciled LS8J ledger, PG 1245-042; freeze its exact pair and header preflight before science values.
