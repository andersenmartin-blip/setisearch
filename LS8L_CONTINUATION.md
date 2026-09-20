# Continue after LS8L

LS8L is complete and independently audited. The exact image-result commit is
`e86c3d15ca8ab6aed0e1a6a9cecaa95f0061efb0`. All 283,611 numerical comparisons
and 481,739 exact checks pass, after seven synthetic tests before image access.
The retained payload is 55,680,000 paired-image bytes plus 139,200 smearing
bytes. No raw imagette or alternative aperture was opened.

| Fixed representative | L2 score | Image outcome | Specific evidence |
|---|---:|---|---|
| TG000201_P0, row 521 | +8.982074701 | UNRESOLVED_WITHIN_FIXED_SCOPE | Complete apertures and matching signs; absolute DELTA/COR 0.10789–0.11186; displacement explains 48.614% and brightness 5.660–5.661% of COR event-map energy |
| TG000202_P0, row 678 | +60.894785514 | SPATIALLY_STRUCTURED | Displacement explains 88.331%; brightness below 0.5%; absolute DELTA/COR about 0.0504–0.0509 |
| TG000202_N0, row 119 | -23.271648387 | CORRECTION_LINKED | Absolute DELTA/COR 0.92196–0.94371 in the two conventions |

These are the unchanged descriptive rules, not unique physical explanations,
astrophysical/artificial classifications or qualified SETI candidates.

## Immediate next action: a bounded diagnostic on retained data

The smaller positive event is unresolved because neither of the two fixed
closure gates passes, not because its source bytes or exposure joins are
missing. Its image is also poorly described by the existing pure-brightness
template. This does not justify promoting a stellar signal.

Before calculating a new diagnostic, freeze one integrated saved-data study
with the following question: **which observable spatial residual and local
noise contribution prevents the fixed image model from describing TG000201_P0?**

1. Use only the three already retained 29-row CAL/COR/SMEAR contexts, their
   L2 rows and metadata. Preserve the two other events as signed comparison
   cases. Keep the exact masks, center conventions, aperture and temporal
   sidebands unless a separately justified model explicitly declares changes.
2. Specify the residual accounting, use of sideband-only pixel variability,
   and brightness/displacement comparison together before calculation. Do not
   choose pixels, weights or cuts from the unresolved event to force closure.
3. Include synthetic known-answer brightness/displacement/compact-defect
   controls and explicit signal-loss accounting for any proposed new removal
   or veto. The existing unweighted energy fractions are descriptive and
   supply no noise-calibrated source probability.
4. Retain all outputs and both signs. Keep LS8L's original classification and
   80%/20%-advantage and 50%-correction gates unchanged. A successor diagnostic
   on these closed data is retrospective development, not new validation.
5. Stop after the bounded study whether it resolves the limitation or not.
   No new native rows, alternate aperture, raw imagette or additional visit
   follows automatically. Any future independent transfer needs its own
   freeze; rank 2 of the unchanged LS8J ledger remains GJ 1132.

Do not repeat the LS8J inventory, LS8K screen or LS8L source acquisition.
The raw-imagette physical calibration gate and unsent technical request remain
separate; unused TESS sectors and M43 held-out panels remain closed.

[Image result and maps](results_ls8l_images/REPORT.md) ·
[L2 result and figure](results_ls8k_l2_screen/REPORT.md) ·
[Image protocol](LS8L_PAIRED_IMAGE_PROTOCOL.md).
