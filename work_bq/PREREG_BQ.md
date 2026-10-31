# BQ: saved A04 association postprocessing

The original BP_FIXED24_V1 remains **FAIL: 23 passed cases, one resource failure**. A04 completed and saved all six paired scan calculations, then exceeded the original 2 GiB RSS limit while constructing its complete association list. The exact child was killed and reaped; EOF and cleanup were recorded. No BP output, source, score, threshold, candidate or failed status is modified.

This new finite identity reads only the existing A04 scan score archives, their corresponding seed4 uninjected controls and bound source/evidence metadata. It draws no random values, renormalizes no input, computes no new track sums or search scores, and opens no astronomical data.

The prospective BP association policy is unchanged: same candidate order, all ON sources, source rate/width, destination physical-q calibration, support, ON10/OFF5, original839 spacing, source cap and truth endpoints. Each association is immediately written to an exclusive JSONL file; only counters and the fixed truth endpoints remain in memory. Both methods' complete associations and full JSONL hashes/counts are retained. The expected A04 gate remains no supported current ON/no-OFF flag and a supported OFF-veto or three-ON rejection at the known location.

The exact BP plan, sources, terminal failure, failed capture, all twelve input score archives and results, seed4 base file/receipt hashes, and A04 sparse deltas are pinned before this operation. Source, inputs, recipes, resource limits and tests are published and read back before the first new association evaluation. Limits for this separate identity are 180 CPU seconds, 240 wall seconds, 1 GiB RSS and 2 GiB new stored output. Failure is retained without retry or increased cap.

A successful BQ result completes the saved A04 association evidence under a new identity. It does not turn BP into PASS, erase the resource failure, qualify the full839 search, admit DATA or justify astronomical sensitivity/FAP claims. A separate independent review checks the streamed lines against the saved arrays and verifies both identities remain unchanged.
