# Continue after LS8O

The GJ 1132 pair is fully screened (LS8N), and all five negative control
clusters have completed their separately frozen image follow-up (LS8O).
Image-result commit: **`51cc3cee0b803ad2d41b6564758b6b91df693a2a`**.

## Fixed results

LS8N evaluated **615 L2 rows and 699 eligible overlapping windows**. There
were **zero positive threshold crossings**, and 12 negative crossings formed
five clusters. The two visits contribute 381 and 318 eligible windows. The
largest positive score is +4.765690830, below the unchanged +8.5 endpoint.
All 8,388 independent numerical/discrete comparisons pass. These scores are
not Gaussian significances; the positive null is not a completeness or
population-limit result.

LS8O retains every negative representative, each spanning three 60-second
rows. All have complete apertures, valid denominators, matching COR/L2 signs
in C0/C1 and 31,415 common finite pixels. The table gives COR displacement
explained energy and signed aperture correction ratios; original gates are
unchanged.

| Representative | L2 score | Displacement explained C0 / C1 | DELTA/COR C0 / C1 | Fixed result |
|---|---:|---:|---:|---|
| TG000401_N0, row 88 | -8.529277829 | 18.77967% / 18.95020% | 0.09797 / 0.09704 | UNRESOLVED_WITHIN_FIXED_SCOPE |
| TG000403_N0, row 69 | -17.739594988 | 56.27990% / 61.67326% | -0.05773 / -0.06337 | UNRESOLVED_WITHIN_FIXED_SCOPE |
| TG000403_N1, row 132 | -9.164247856 | 79.74861% / 83.79823% | 0.10614 / 0.08875 | UNRESOLVED_WITHIN_FIXED_SCOPE |
| TG000403_N2, row 191 | -9.124594182 | 16.37823% / 20.10730% | 0.37227 / -0.03201 | UNRESOLVED_WITHIN_FIXED_SCOPE |
| TG000403_N3, row 297 | -8.838439333 | 68.78136% / 73.39195% | 0.14757 / 0.15517 | UNRESOLVED_WITHIN_FIXED_SCOPE |

Neither the absolute DELTA/COR nor the column-DELTA/COR term reaches 0.5 in
the required two conventions. TG000403_N1 passes the displacement energy
gate only in C1: its C0 value is **0.25139 percentage points below 80%**.
It remains unresolved without rounding the value up or choosing the favorable
convention. All five pure-brightness fits explain only **0.214–4.016%** of COR
event-map energy. A pure stellar dimming is therefore poorly represented by
this fixed image template; that does not uniquely identify the actual cause.

## Specific remaining limitation

The unresolved statuses are **model limitations, not missing source bytes or
exposure joins**. Several events have substantial displacement-like structure,
but the unchanged first-order model does not meet both coordinate gates.
Two observations make the next question concrete:

- TG000403_N1 is sensitive to the one-pixel convention change around the
  fixed displacement gate. The other cases also retain substantial residual
  energy. LS8O's unweighted energies have no calibrated local-noise meaning.
- TG000403_N2 has strong coordinate sensitivity in its correction budget:
  CAL aperture sums are -27,595.54 and -46,928.07 ADU, while COR sums are
  -43,960.64 and -45,472.37 ADU. The resulting DELTA/COR ratio changes sign.
  This motivates explicit accounting of the two existing masks' boundary
  contributions; it does not authorize moving the aperture to obtain closure.

The full-frame plots also retain spatial structure outside the source aperture
and compact correction features. Their common per-event scales can make faint
central structure visually weak. The numerical diagnostics, not visual
contrast, determine the labels. No event is promoted to a SETI candidate.

## Immediate next action: one integrated study on the retained five contexts

Before any new native-derived calculation, freeze a single bounded study
asking: **how much of the five negative controls' residual and coordinate
sensitivity is accounted for by local image variability and the exact
boundary difference between C0 and C1?**

1. Use only the existing five 31-row CAL/COR/SMEAR contexts, their retained
   L2 rows, exposure metadata and published maps. Keep all five controls,
   both coordinate conventions, their original masks/radii and original
   representatives. Do not acquire new pixels, rows, visits or products.
2. Specify residual accounting, sideband-only variability and the
   brightness/displacement comparison together. Account explicitly for the
   C0-only and C1-only pixels using the existing two apertures. Do not choose
   a preferred convention, remove event-selected pixels or vary the radius.
3. Respect the **three-exposure event sums**. Specify their temporal noise
   propagation and fixed held-out three-row sideband controls prospectively,
   including temporal covariance/limitations. LS8M's single-row leverage and
   leave-one-row procedure cannot simply be copied onto these events.
4. Include known-answer three-row brightness, displacement and compact-defect
   controls in **both signs**, even though this native sample has no positive
   cluster. Retain explicit signal-loss accounting for any proposed removal
   or veto. No correction or new detection cut is adopted merely because it
   describes these already selected controls better.
5. Publish every case and independent audit, preserve LS8N/LS8O thresholds
   and labels, and stop after that bounded study regardless of outcome. A
   closed-data diagnostic is retrospective development, not independent
   validation or qualified observing coverage.

The existing LS8M closed-data machinery can inform implementation only after
the changed event duration and coordinate accounting are explicitly frozen
and independently tested. Do not reopen the closed WASP-189 study.

**Rank-3 HD 136352 stays next in the independent target ledger**, with
CH_PR100041_TG000901_V0300 and CH_PR100041_TG000101_V0300 as its existing
chronological pair. Its science values remain unopened; any later transfer
requires its own exact-pair/header and science-byte freeze. Do not re-run the
population census or change the host order based on these outcomes.

## Verification and boundaries

Image metadata established 310 unique CAL/COR joins with 1,423 exact checks
before pixels. The separately frozen run then acquired exactly **99,200,000
paired-image bytes plus 248,000 smearing bytes**. Nine synthetic tests pass,
followed by **472,685 independent numerical comparisons and 802,983 exact
checks**, with zero disagreements. All five image figures and the L2 figure
were visually reviewed; retained review files match their result manifests.

No qualified candidate, detector or observing coverage is added. Historical
failures, including the original LS8B audit failure, remain preserved. Raw
imagettes, alternative apertures, reserved TESS sectors and M43 held-out panels
stay closed. The separate raw-imagette calibration gate is still NOT_READY;
its technical request remains unsent, with no pending reply. Standing research
and publication authorization continues without a new per-stage request.

[All image outcomes and maps](results_ls8o_images/REPORT.md) ·
[L2 screen and figure](results_ls8n_l2_screen/REPORT.md) ·
[Image protocol](LS8O_PAIRED_IMAGE_PROTOCOL.md) ·
[Publication identities](PUBLICATION_2026-09-20_LS8N_LS8O.md).
