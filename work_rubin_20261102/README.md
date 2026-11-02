# Accelerated Rubin archival dimming pilot — 2 November 2026

The approved Rubin week was advanced from 8–14 November to **2–8 November 2026**, after the complete initial HARPS raw review. Actual public Rubin data are available through Fink. This directory preserves separate development, metadata selection, a frozen main method and subsequent results. No ZTF or simulated data substitutes for Rubin observations.

## Before main photometry

- [Access/development](access_pilot/README.md): 20 metadata-selected development objects,259 source detections and326 forced measurements, with six representative FITS products. Development observations span26June–31October2026 UTC.
- [Gaia selection](gaia_selection/README.md):188 main stellar associations from413 unused metadata objects. Exact development IDs,nearby development positions and Gaia counterparts are excluded. The sample is bounded and alert-selected, not representative of all stars.
- [Method and controls](method_review/README.md): direct science flux only; source-position and object-position forced photometry stay separate. The primary event window is October2026. A180-day prior baseline needs at least five distinct visits on three earlier UTC dates; the entire tested UTC date is excluded. A numerical trigger requires a>=0.3mag drop and conservative deficit score>=5, which is not a calibrated Gaussian significance.
- [Main acquisition plan](main_acquisition/PLAN.json): exactly188 frozen identities, two separate photometry streams, bounded retries/bytes and no replacement objects. Acquisition requires verified public publication of selection,method and code.

Development data motivated the180-day historical baseline before main flux inspection. The original draft local30-day window could not supply three earlier October dates. The resulting approximately108-day reference gaps remain explicit; numerical evaluability does not establish local quiescence or a short-lived physical event. Missing withdrawal information remains unknown, and forced photometry lacks measurement flags.

The original minimum of50 evaluable main objects remains. Counts, full event lists, control recovery and image/quality review determine the final status; merely retrieving188 objects cannot fulfill that criterion. No calibrated sensitivity, event rate, null result or technosignature candidate is established by this preregistration.
