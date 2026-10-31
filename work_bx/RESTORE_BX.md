# Restoring BX evidence

The outer ZIP contains an explicit member manifest. Verify its SHA-256 against the final delivery index, then verify every listed member's size, SHA-256 and ZIP CRC before accepting the evidence. The production and audit ZIPs are closed nested evidence archives with their own manifests and captures. Full numerical results remain in those archives; `SUMMARY_BX.json` is only a compact aggregation.

The two original UVH5 inputs, full headers, source code, frozen plan, public freeze receipt, synthetic-test review, independent numerical review, failure history and original h5py wheel are included. Unpacked h5py files are omitted because they can be reconstructed from that exact wheel. The plan binds the original Python executable and runtime dependencies; a different runtime is not the same frozen execution.

Absolute paths record the original execution environment. Restore evidence for inspection without modifying these receipts. Existing production/audit identities must not be rerun or silently overwritten. Any future scientific run needs a separate declared identity, matching input pins, a new output directory and its own review.

The package receipt and permanent file ID are recorded outside the ZIP in `DELIVERY_BX.json` and the final delivery index, avoiding self-referential hashes. GitHub commit/readback receipts are recorded in that final index after publication. The BW index remains the authority for earlier SETI coverage and the missing OFF5 recovery plan.
