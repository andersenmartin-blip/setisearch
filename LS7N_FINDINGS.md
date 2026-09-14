# LS7N — calibrated native response fails the joint requirement

Completed and independently audited 14 September 2026.

**The calibrated cadence response still makes the measured residuals worse.**
Across the original 420 native windows and both field-column conventions,
combined residual energy rises **12.14–12.36% in sector 29** and
**12.37–12.49% in sector 32**. Zero of ten sector-29 backgrounds and two of
ten sector-32 backgrounds improve; six were required. All 840 model/window
predictions are available. [Full result](results_ls7n_response/REPORT.md).

All **12,600 downstream pulse-response cases pass**. Maximum nominal profile
distortion is **0.015354%**, against 1% allowed. Maximum calibration-entry
stress distortion is **0.226796%**, against 5% allowed. The independent audit
passes 108,604 numeric comparisons; all 146 inherited manifest entries agree.
Five known-answer tests pass, including source-amplitude event exclusion.

The PRF was treated as an effective, already blurred response at the supplied
20-second POS_CORR displacement. No instantaneous quaternion mapping, added
jitter convolution or empirical motion gain was used. Both coordinate
conventions and the common 110-pixel supported domain were fixed beforehand.
The source amplitude is fitted only to protected sideband pixels.

The energy identity separates useful correction alignment from its squared
size. Size exceeds the alignment benefit in both sectors. The result does
not identify whether motion-estimator noise, derivative errors, reference
astrometry, crowding or other scene changes dominate. It does show that a
calibrated PRF and protected background plane alone do not satisfy this test.
The plane-only ablation passes in sector 32 but fails in sector 29; no
replacement is selected from these outcomes.

Close this exact response family without gain/sign/lag/profile tuning. The
next information requirement is an independently measured reference field or
motion estimator with specified target exclusion, time sampling and response
uncertainty. Assess whether such inputs can be obtained for these same
pointings before proposing a bounded acquisition and another fixed comparison.
If they cannot, reconsider the optical data/product choice. Their availability
is not established by this result.

No detector or candidate is adopted and no observing coverage added. Unused
TESS sectors and M43 panels remain unopened. LS7J and every historical
negative result keep their original counts and status.

[Frozen contract and primary-source interpretation](LS7N_SPEC.md),
[independent audit](results_ls7n_response/audit.json),
[current continuation](LS7N_CONTINUATION.md).
