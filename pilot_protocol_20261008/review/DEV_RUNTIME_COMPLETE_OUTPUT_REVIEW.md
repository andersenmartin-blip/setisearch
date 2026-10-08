# Retained-output review: operational development correction 1

PASS_OPERATIONAL_DEVELOPMENT_ONLY. Both fresh DEV_RUNTIME identities closed once with exit zero and durable COMMITTED markers. Original A remains FAIL_CLOSED. No B or telescope arrays were opened, and no generation, detector search or rerun was performed by this review.

Verified 40 original artifact hashes, all 12 complete maps, 5,415 drift hypotheses × four widths = 21,660 valid hypotheses per carrier, all 3,630 ON threshold carriers, and all 10,890 retained compatible OFF comparisons. Frequency axes use negative native Hz spacing; all row midpoints are seconds from the common reference and use 17.986224128-second sampling. Each retained carrier agrees exactly with its saved map winner and all OFF families are explicitly exhausted below threshold eight. OFF expanded axes agree with ON axes within 4e-7 Hz floating-point roundoff.

Case 000 retains 1,816 surviving carriers, with 66 localized at both injected-track endpoints. Case 001 retains 1,814 surviving carriers, with 64 localized. This confirms the operational correction finishes these expensive cases. It also preserves the scientific limitation that a single-row transient can survive the detector. These are development controls, not independent validation.

The two case snapshots total 591.923606 CPU seconds; whole reaped children consume 592.019303, and controller CPU is 0.034510. Charge the larger child measure plus controller: **592.053813 CPU seconds**. Maximum RSS is 87,801,856 bytes and coordinator elapsed time is 296.677738 seconds. The 3,600-second live reservation may now refund 3007.946187 seconds. Scientific source and frozen control banks remain unchanged.
