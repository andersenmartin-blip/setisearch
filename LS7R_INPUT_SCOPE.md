# LS7R: bounded CHEOPS input and timing assessment

14 September 2026. Written before CHEOPS product contents are acquired.
This follows LS7Q_CONTINUATION.md's secondary CHEOPS route. It is an
exploratory input assessment, not a frozen detector qualification.

Select 55 Cnc as a bright, known planet-host target for an engineering pilot;
the choice uses target identity, not light-curve structure or reported events.
Query the official archive at its resolved coordinates, radius 0.01 degrees,
public visits only, latest versions. Save the returned visit metadata and
choose the earliest public science observation in that result by start time
(ties by visit identifier). Record any delivery failure without silently
replacing that visit with an outcome-selected alternative.

Use archive/DACE metadata to identify raw imagettes, stacked subarrays,
calibrated and corrected subarrays, pixel flags, reference/calibration files
and processing provenance for that exact visit. Establish transfer sizes
before a large transfer. Limit each diagnostic data transfer to 100 MB and
the total acquired product bytes in this stage to 250 MB; stop when an
unbounded or incompatible access route is encountered. Metadata may establish
a smaller byte-range acquisition instead. Do not inspect science flux,
light-curve plots, movies, residual peaks or candidate events in this stage.

Inspect FITS headers and time/quality metadata only. Keep single-exposure
duration distinct from on-board stacking, delivered cadence, live time and
gaps. Calibrated and corrected products are not interchangeable, and a raw
imagette is not a calibrated short-cadence light curve. Record the actual
pipeline version and any calibration identities that are present; label
missing provenance explicitly.

If the input exposes precise timing, evaluate idealized 30, 60 and 100 second
positive rectangular-pulse averaging across sampling phase, distinguishing
this temporal response calculation from end-to-end pixel injection recovery.
This is a descriptive sampling calculation with no detector threshold and
no physical sensitivity claim. Preserve failed or unavailable inputs.

A viable input package leads to one integrated prospective pixel-response
protocol including spatial source/reference masks, calibration and flag
policy, time intervals, pulse and nuisance controls, native-window endpoint,
decision requirements and the failure branch. Freeze that protocol before
opening science arrays. No unused TESS sector or M43 held-out panel is opened.
LS7P's separate publication reconciliation remains unresolved.
