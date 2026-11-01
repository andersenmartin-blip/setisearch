# Extension02 raw follow-up batch02

This prospective batch advances the 277-event raw-review queue from the verified `09424fbd2d169f646ebeb09bbdc58af1668583dd` checkpoint. It selects the first16 pending exposures in frozen MAIN100 order and all68 of their accepted V2 events (V2E2-0011–0058 and0065–0084). Availability and morphology do not change selection; omissions remain explicit. Original production catalogs and previous adopted dispositions are preserved.

`PLAN.json`, `VISUAL_REVIEW_PLAN.json`, input snapshots and source code define the work before new raw arrays are read. `prepare_selection.py` verifies metadata with HEAD requests only; `FOLLOWUP_FREEZE.json` then hashes the exact selected IDs, jobs, source files and analysis code. Root must publish and independently verify that package before invoking `acquire.py`. This is an internal reproducibility gate under the user's existing GitHub authorization.

Acquisition is limited to16 original public raw products and16 corresponding ancillary products, three workers, two bounded attempts and700,000,000 total charged payload bytes including failed reads/retries. Redirects and authentication/access denials are not worked around. Failed or oversized pairs are not replaced.

Mapping retains the inherited global reference-grid orientation and local two-sided checks. The already-established wider five-window check is applied prospectively to **every covering order** in this batch. Coordinates and thresholds remain fixed. Each stored31×33 raw cutout contains the exact central21×25 baseline cutout; native profiles contain41 points. A record is mapping-qualified only when global and five-window gates hold for every covering order and complete cutouts are available. Historical local flags are retained separately, so these controls do not erase earlier limitations.

Two separate AI-agent visual reviews will inspect every selected event/order before root adoption. Their judgments are descriptive and provisional, not independent human validation. No wavelength-only origin decision, qualified laser candidate, calibrated null, global false-alarm rate or sensitivity estimate follows from this follow-up.

This initial package is a preregistration. Acquisition, numerical checks, visual dispositions and the exact remaining queue will be added after execution; they are not claimed complete here. See the repository's `CONTINUE_SETI.md` for the current adopted checkpoint.
