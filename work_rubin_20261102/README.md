# Accelerated Rubin archival dimming pilot — 2 November 2026

The approved Rubin week was advanced from 8–14 November to **2–8 November 2026**, after the complete initial HARPS raw review. Actual public Rubin data are available through Fink. This directory preserves separate development, metadata selection, a frozen main method and subsequent results. No ZTF or simulated data substitutes for Rubin observations.

## Completed first main screen

The exact 188-object main search has finished. It returned 807 source measurements and 77 forced measurements. Only 2 primary objects / 7 October measurements and, separately, 3 forced objects / 14 measurements were numerically evaluable. The forced set includes both primary objects. No row passed both fixed thresholds. All numerical baselines have long gaps and unresolved quality information. **The 50-object pilot minimum is not met; this is a limited feasibility study, not a qualified null result.** Read the [full main result](main_analysis/README.md) and [independent audit](independent_main_audit/AUDIT.json).

The method and exact 188 identities were published before main photometry in [commit 541357e](https://github.com/andersenmartin-blip/setisearch/commit/541357ebea3548836285857b548777723744ae15); all 49 files were read back byte-for-byte. All eight main requests succeeded within the frozen limits, without a retry. No new observation or origin identification was made.

## Preserved preregistration and development

- [Access/development](access_pilot/README.md): 20 metadata-selected development objects, 259 source detections and 326 forced measurements, with six representative FITS products. Development observations span 26 June–31 October 2026 UTC.
- [Gaia selection](gaia_selection/README.md): 188 main stellar associations from 413 unused metadata objects. Exact development IDs, nearby development positions and Gaia counterparts are excluded. The sample is bounded and alert-selected, not representative of all stars.
- [Method and controls](method_review/README.md): direct science flux only; source-position and object-position forced photometry stay separate. The primary event window is October 2026. A 180-day prior baseline needs at least five distinct visits on three earlier UTC dates; the entire tested UTC date is excluded. A numerical trigger requires a ≥0.3 mag drop and conservative deficit score ≥5, which is not a calibrated Gaussian significance.
- [Main acquisition plan](main_acquisition/PLAN.json): exactly 188 frozen identities, two separate photometry streams, bounded retries/bytes and no replacement objects. Acquisition requires verified public publication of selection, method and code.

Development data motivated the 180-day historical baseline before main flux inspection. The original draft local 30-day window could not supply three earlier October dates. The resulting approximately 108-day reference gaps remain explicit; numerical evaluability does not establish local quiescence or a short-lived physical event. Missing withdrawal information remains unknown, and forced photometry lacks measurement flags.

The original minimum of 50 evaluable main objects remains. Counts, full event lists, control recovery and image/quality review determine the final status; merely retrieving 188 objects cannot fulfill that criterion. No calibrated sensitivity, event rate, null result or technosignature candidate is established by this study. The main minimum was not met; its objects remain preserved rather than replaced. A separate bounded metadata feasibility extension is complete: 940 new objects, 8,277 metadata rows and 104 temporal/quality prerequisite passes. These are not 104 evaluable stars: Gaia associations and flux precision remain untested. Their separate Gaia selection is the next step, before any additional flux acquisition.
