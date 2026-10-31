# BP: prospective fixed24 paired synthetic controls

This new family follows the closed BO engineering work at `b09768a6cec3a251006482028ed35794dbdf81f4`. It does not reopen historical M runs or astronomical powers. The 24 HIP45688 M raw-sum failures and full-QA=false remain unchanged.

Before any RNG or synthetic score, the exact source files, runtime, complete generator/signal specifications and case list in `BP_FIXED24_PLAN.json` are published to a distinct GitHub commit and read back byte-for-byte. Imports and preregistration tests use deterministic, non-random inputs only. The eight seeds and all twelve positive/four association recipes are fixed before results.

One sequential worker runs eight null six-scan cadences followed by twelve known-signal cases and four association cases. Six full 16×1,048,576 arrays per base cadence are generated once. Both methods receive identical immutable float32 inputs. Injection artifacts retain sparse float64 requested increments, exact float32 resulting values, input hashes and analytic conservation/rounding checks. Full base arrays and all evidence are retained.

The legacy method retains its original block normalization, float32 staged sums and global calibration on the complete [4096,1044480) interior including q128. The current method uses the BO-pinned continuous normalizer and guarded float64 kernel, calibrated separately in q63/64/65/127/129. Both use widths 1/3/9/33, strides 1/1/2/8 and original-bank rate indices 0/209/419/629/838.

Association is a specifically declared prospective limited-control rule: seed every ON catalog, propagate with row7.5 epochs, use the destination physical q's calibration and nearest width-grid center, and test OFF neighborhoods with the original 839-bank spacing. This differs from BN's source-q forced calibration. Unsupported measurements cannot pass. Known-truth recovery is restricted to the prescribed truth neighborhood and exact injected rate, and the same endpoints are evaluated in the paired uninjected cadence. No arbitrary unrelated maximum counts as recovery.

All eight current null cadences must have no fully supported three-ON/no-OFF flag. All six strong current cases must recover; a weak legacy success lost by current requires review. All four association controls must reject with supported OFF veto or missing ON evidence. Scalar oracles retain every legacy violation of the original absolute 5e-5 guard; reproducing a legacy value does not make that value numerically qualified.

The entire phase is bounded by 1,800 CPU seconds, 2,400 wall seconds, 2 GiB process RSS and 8 GiB retained execution artifacts. Capture uses the unchanged BO exact-child mechanism, complete stdout/result hashes, natural EOF and explicit process cleanup. Every case identity is reserved once. Failure stops the finite chain and preserves all output, with no automatic retry, threshold change or seed change.

Passing these controls does not qualify the full 839-rate bank, real-data admission, astronomical sensitivity, false-alarm probability, flux/EIRP or sky origin. Full839 paired controls and DATA admission require separate finite plans and review. No actual telescope powers are opened by BP, and no new observation, archive request or BA coverage credit is claimed.
