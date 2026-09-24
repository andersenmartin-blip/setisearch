# LS8BE — GJ 494 complete signed-event paired-image follow-up

Completed 24 September 2026. **COMPLETE_AUDITED**, independent audit **PASS**.

The separately frozen diagnostic retains the complete LS8BD signed representative
set: one positive event and no negative events. No representative is added or substituted.
The image outcomes are: **{"CORRECTION_LINKED": 1}**.
These are descriptive image labels, not a determination of artificial or
astrophysical origin, and not detector qualification or a SETI-candidate claim.

| Representative | Sign | Fixed classification | DELTA/COR C0 / C1 | COR brightness explained C0 / C1 | COR displacement explained C0 / C1 |
|---|---|---|---:|---:|---:|
| TG007401_P0 | positive | CORRECTION_LINKED | -3.49685 / -3.69464 | 0.08148% / 0.08193% | 81.79546% / 81.79735% |

The representative is one 42-second exposure with NEXP=1 in the first
visit. Native BJD times and full verified header values are retained.

| Representative | L2 row, zero-based | Duration | Original L2 score | L2 excess / local baseline |
|---|---:|---|---:|---:|
| TG007401_P0 | 53 | 42 s | +17.588818768661 | +0.433469% |

Scores are not Gaussian significances. The two original positive crossing
windows form one cluster in TG007401. TG007402 has 48 eligible windows and
no crossings. Its large unassessed points and other ineligible L2 rows remain
retained without reselection. The two later visits stay outside the pair.

## Scope and method

The metadata-only preflight established **58 unique CAL/COR exposure joins**,
each matched within 1 ms MJD/BJD with exact UTC and CE agreement. The single
29-row context contains 29 distinct L2 exposures and 58 distinct CAL/COR
product exposures, without duplicated representative contexts. The public
config fixed every source identity and exact range before image access. The run acquired exactly
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

All 11 inherited image known-answer tests run before payload access. They protect signed
event sums, guards, masks, brightness preservation and both conventions.
Scientific functions and gates are unchanged. The independent
struct/long-double/scalar-normal-equation audit checks source ranges and
hashes, metadata joins, masks, event maps, fits and classifications:

- numerical comparisons: **94,537**;
- exact checks: **160,581**;
- disagreements: **0**.

LS8BD's L2 audit remains PASS. Historical LS8B's original FAIL and later
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

### TG007401_P0

![TG007401_P0: CAL, COR and DELTA event maps](TG007401_P0_CAL_COR_DELTA.png)

## Next action

Close this GJ 494 follow-up under its fixed descriptive label without widening. The next independent target is rank 24 of the unchanged reconciled LS8J ledger, 2MASS J11474440+0048164; freeze its exact pair and header preflight before science values.
