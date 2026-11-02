Quantify the spatial support of **V2E2-0235 in its existing discovery exposure**, using a frozen detector-space diagnostic. This is one proposed follow-up task, pending a separate plan; this handoff has not performed acquisition or array analysis. The user’s standing instruction permits preparing and executing the bounded diagnostic after its method is fixed.

The new May-quality epoch supplies useful context at a large BERV displacement with adequate local continuum. It follows the surrounding spectrum but does not reproduce the discovery's central excursion at comparable normalized amplitude. The unresolved question for 0235 is therefore the already documented detector morphology: the prior review found a compact asymmetric patch below and left of the trace and could not distinguish a charge deposit from a photon/charge mixture. A quantitative spatial comparison adds information beyond another temporal correlation or another visual inspection.

Use only this fixed identity and mapping:

| Item | Existing evidence |
|---|---|
| Event | V2E2-0235, HD122640, barycentric center 5548.09 Å |
| Discovery product | ADP.2023-02-23T01:01:36.791 |
| Raw progenitor | HARPS.2023-02-22T07:40:53.531 |
| Ancillary package | ADP.2023-02-23T01:01:36.792 |
| Native location | order 50, pixel 956; recorded topocentric center 5547.594351454701 Å |
| Registered detector location | row 3139, column 2323.7701943175816 |
| Existing raw/native review | `work_harps_20261101/v2/extension02/raw_followup_batch03/` |

The prospective implementation should have four bounded stages:

1. Inventory the preserved evidence archive and exact raw/ancillary members, verifying their hashes. First use the existing native cutout and stored trace-control evidence. If the saved cutout lacks the required control pixels, restore the previously archived discovery raw/ancillary bytes. Stop if those bytes are unavailable; this proposal does not authorize a new archive fetch or replacement exposure.
2. Freeze the exact registered central cutout, masking, background rule and comparison statistic before reading those arrays. Estimate the spatial photon-trace template exclusively from the two previously fixed flank intervals, relative dispersion rows `[-280,-80)` and `[81,281)`. Keep the accepted trace registration and order mapping unchanged. Use a deterministic, nonoverlapping set of same-order control cutouts from these intervals, chosen by coordinates rather than visual morphology or target-like residuals.
3. Fit the fixed trace template plus background to each central dispersion row, then report the observed and predicted cross-dispersion profiles, residual spatial concentration, centroid displacement and off-trace residual fraction. Apply exactly the same diagnostic to the frozen control cutouts. This should quantify whether the central excess follows the local photon-trace shape or requires a compact off-trace residual; it must not silently alter the historical extraction or discard suspect pixels to make the feature disappear.
4. Publish the target/control residual map and metric table alongside the prior U adjudication and the temporal profiles. If the comparison remains ambiguous or lacks appropriate noise/calibration support, retain U explicitly. Do not turn empirical control ranks into calibrated significance, a cosmic-ray classifier or a physical-origin claim.

This is a posthoc diagnostic of one known ambiguity, not an expansion of the May sample. Keep the twelve-profile quality follow-up and the earlier twenty-four-profile run closed and unchanged. Do not select another unused May epoch, retune wavelength centers or template widths, or change any of the ten U labels as part of this proposal.
