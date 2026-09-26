# Radio SETI work plan — 26 September–9 October 2026

**Active track: ordinary narrowband radio SETI. LS is paused.**
Owner direction, 26 September: prepare a new two-week plan and move from the
light-sail branch back to the ordinary search. This plan starts immediately
and supersedes LS8BF as the active next action. It covers fourteen calendar
days of work. A [scheduled continuation](RADIO_AUTONOMOUS_CONTINUATION_2026-09-26.md)
was enabled after the owner challenged the stop: daily from 27 September through
9 October, around 08:00 Europe/Copenhagen. It performs the next bounded authorized
work package and reports actual progress. This supersedes the original
no-schedule wording; scientific gates and limits are unchanged. The dates are
planning windows, not required waiting times.

## Objective and concrete end product

Complete one bounded, reproducible radio-search pilot on an observing sequence
independent of the sequence used for M43 development, with paired ON/OFF
evidence, a prospectively fixed search and control design, complete candidate
accounting and an explicit decision about further radio searching.

The intended output is actual new radio-data analysis and candidate follow-up,
not another sequence of small threshold adjustments on M43AI. A discovery is
not a deliverable that can be promised. If source access or the scientific
gate fails, the useful endpoint is a complete, bounded failure report and an
exact next information requirement, with further evaluation data left unopened.

## Starting evidence and boundaries

- [M43AI](MILESTONE_43AI_NATIVE_VALIDATION_RESULT.md) is complete and closed:
  **53/64** injected signals recovered, **zero losses among the 53 cases
  recovered by the reference union**, **1/48** controls with a surviving
  member, and **0/128** native-null cases with surviving members. The
  zero-control gate failed. Empty native-null retained sets do not measure a
  conditional false-alarm tail. These are same-sequence digital challenges,
  not independent observing sequences; the selected model is not adopted.
- M43AF/AG/AH/AI records and audits are reusable development evidence. Their
  completed outcomes must not be rerun as new results or tuned into a pass.
  The original **112 M43AF held-out injection/control inputs and 128 held-out
  native nulls** remain reserved and unopened throughout this plan.
- [M33 HD 3651](MILESTONE_33_CANDIDATE_INVESTIGATION.md) remains unresolved.
  Its earlier metadata screen found no second qualifying public cadence.
  A new metadata-only availability check is useful, but a second cadence is
  not assumed to exist. Non-redetection alone is not a physical RFI veto.
  Preserve every other earlier candidate disposition, including M16; the
  restart inventory must not silently replace the older candidate register.
- The [LS period review](TWO_WEEK_REVIEW_2026-09-26.md), its 23-cohort register
  and all 16 unresolved events stay preserved. Pause at **LS8BD–LS8BE**;
  **LS8BF remains the saved LS restart**, not an active task in this period.
  CHEOPS calibration stays NOT_READY and its technical request stays UNSENT.

Source checkpoint for this plan:
`56cb3de92ed267c646f3b013e51644da3f6adf74` on `m43-support-qualification`.

## Work schedule

| Dates | Integrated work package | Deliverable and decision |
|---|---|---|
| **26–27 September** | Restart radio work from the published evidence. Inventory the existing detector entry points, candidate dispositions and already inspected observations. Assess a bounded shortlist of at most three independent ON/OFF sequences using metadata and headers. Separately check whether new independent HD 3651 data exist. | A pinned restart/source inventory, explicit novelty and eligibility checks, and one selected pilot sequence. No spectrum-based target selection. If none is usable, record the exact access or coverage obstruction instead of substituting old data. |
| **28–29 September** | Freeze one primary radio screen, its frequency/motion/width scope, end-to-end injection and interference/null controls, resource limits and numerical gates. Verify acquisition and arithmetic on the selected independent sequence. Use completed software checks wherever code is unchanged. | One executable protocol and integrated transfer/control result. Decide whether the primary screen may proceed to the bounded exploratory pilot. Do not select a different rule from the new results. |
| **30 September–3 October** | Run the frozen pilot and retain every eligible trigger, cluster and physical-veto outcome. If the gate passes and resources permit, extend to at most two additional sequences selected by the already fixed metadata ordering and separately frozen before their values are opened. | A complete radio-search ledger with exact targets, visits, frequencies, masks, tested scope and unassessed scope. At most three sequences in this period; no expansion based on attractive amplitudes. |
| **4–7 October** | Apply the fixed ON/OFF, receiver-frame and recurrence follow-up to every surviving cluster. For an earlier unresolved case, use a newly available independent cadence only under a separate frozen hypothesis test. | Evidence and a disposition for each selected case: supported rejection under the fixed rule, unresolved, or requiring independent observation. No artificial-origin claim from a radio trigger alone. |
| **8–9 October** | Consolidate results, sensitivity limitations, missed injections, controls and candidate follow-up. Publish the readable report, figures, evidence and restart instructions. | A decision to continue a clearly scoped radio search, undertake one named method/information study, or pause a blocked route. State what changed scientifically and what remains unsupported. |

## Selecting genuinely new radio evidence

The M43 source window is the reused HD 156668 sequence at approximately
1412.5 MHz. More translated carriers, new injections or different scramble
rows on that same sequence do not provide independent observations.

The metadata protocol must pin the catalogue snapshot, exact scan identities,
dates, pointing, telescope/backend, frequency coverage, resolution, timing,
ON/OFF pairing, source sizes and content/receipt identities. Check them against
the project's existing observation inventory before reading new spectra.
Prefer a genuinely different observing session/date with a complete usable
ON/OFF cadence. Distinguish interleaved scans within one session from repeated
observations on different dates.

Select the first eligible entry under an explicit metadata ordering fixed
before spectral inspection. The shortlist, eligibility, ordering and reasons
for exclusions must be recorded together. Frequency limits and the motion
bank must follow header coverage and declared physical/model assumptions,
not interesting features seen in the spectra. Do not assume the old numerical
window, cache shapes or score calibration transfer to another source.

Start with one sequence and bounded frequency extraction. Fix byte, memory,
runtime, retry and retention limits in the executable protocol. A source
identity, schema, provenance or integrity mismatch stops access; do not
silently replace a source, truncate retained events or widen the download.

## Method, checks and advancement gate

Use the existing integrated radio pipeline as reusable software. Establish
the exact primary reference endpoint and complete configuration before new
scoring. The recorded `centered_receiver_off_match_aggregate` and `neighbor9`
endpoints are available fixed references; M43AI may be retained as an unchanged
diagnostic comparator. None becomes a generally qualified detector merely by
being called a reference. Do not choose whichever comparator looks best on
the new validation data and then call it the prospective primary method.

The executable protocol, rather than this calendar document, must supply the
exact target/file IDs, extraction ranges, drift/template bank, widths,
thresholds, calibration/null construction, injection design, recovery minima,
control limits and stopping conditions. Publish and verify that freeze before
its evaluation values are opened. Keep any development and evaluation scopes
explicitly disjoint, including native payload identities.

The integrated checks must cover:

1. **Faithful measurement:** headers, channel/time mapping, source receipts
   and normalization; independent direct-native checks for the changed data
   interface. Reuse earlier arithmetic audits for unchanged components.
2. **End-to-end recovery:** signal additions run through retention, clustering,
   ON/OFF tests and final dispositions, not only a score evaluated at known
   injected truth. Report all signal cases and losses by strength, width,
   activity pattern and supported drift scope. Truth labels are for recovery
   accounting only and never input to detection or veto decisions.
3. **Interference and null behavior:** matched ON/OFF interference, single-epoch
   interferers, supported spikes and native controls. Report distinct native
   realizations separately from labelled cases, overlapping windows or
   resampled versions. Empty retained sets are not a calibrated tail sample.
4. **Complete decision accounting:** every failed gate, reference gain/loss,
   unassociated survivor, capacity failure and incomplete interval remains
   visible. A successful software audit is not scientific qualification.

The primary method must meet the separately frozen recovery/rejection gate
and pass source/arithmetic checks before expansion beyond its evaluated scope.
A pass permits only the specified bounded exploratory pilot; it does not erase
old failures or establish a universal false-alarm rate, broad completeness or
general detector adoption. Derive no flux/EIRP sensitivity from uncalibrated
digital injections.

If the gate fails, complete all already specified cases unless an integrity
error prevents execution, publish the result and keep the next sequences
unopened. Allow **one bounded diagnosis on retained evidence**, taking at most
the next two active workdays. It may identify a demonstrated implementation
error or a concrete missing observable; it may not become a threshold, bank
or feature search on failed evaluation outcomes. Record any repair explicitly
and do not relabel exposed data as fresh validation. No automatic return to LS.

## Candidate follow-up and period closure

For every surviving cluster, preserve the original hypothesis and display
the native time-frequency data in each ON and paired OFF scan, with receiver
and celestial-frame mappings kept distinct. Require compatible support for
the same hypothesis, rather than combining unrelated peaks. Apply only the
fixed RFI/alias tests; plot anomalies outside eligibility without counting
them as tested nulls or silently selecting them for confirmation.

A missing repeat can be compatible with intermittency. An ON/OFF survivor is
not evidence by itself of an extraterrestrial origin. A follow-up requiring
new telescope observations is a documented next action; this plan neither
sends messages nor books telescope time.

Publish code, protocols, data extracts, full ledgers, logs, audits and figures
on `m43-support-qualification`, and meaningful overview updates on `main`,
under the owner's standing authorization. No repeated publication approval
is needed. Combine related work into substantial packages rather than counting
routine checks as progress milestones. Review progress around **2 October**
and at closure on **9 October** during active sessions.

**Current continuation, 26 September:** the restart/metadata package is complete.
HD 1461 is selected but its spectra remain on a pointing-provenance hold. The
[new explicit-source interface](RADIO_SOURCE_2026-09-26_RESULT.md) passes local
engineering checks. The [integrated primary/control preparation](RADIO_PIPELINE_2026-09-26_RESULT.md)
also completes all six synthetic cases and passes eight local integration tests.
`neighbor9` is the fixed primary reference; the source-specific scientific
protocol is still unfrozen. The [durable acquisition continuation](RADIO_ACQUISITION_2026-09-26_RESULT.md)
now passes ten local tests and a GitHub-backed crash/restart demonstration using
simulated source HTTP. The [source-specific motion/exposure audit](RADIO_MOTION_2026-09-26_RESULT.md)
is also complete with twelve new tests, a demonstrated circular-to-eccentric
model incompatibility, finite-exposure injection arithmetic and an exact but
unfrozen three-window proposal with disjoint decoded payloads. The
[direct-factor/native continuation](RADIO_DIRECT_FACTORS_2026-09-26_RESULT.md) is
now complete: eight tests, 38,016 independent factor comparisons and 1,015,344
bit-exact native score comparisons on one synthetic cadence. The distinct
direct-table type is not yet connected to the full legacy detector. Continue
with its explicitly versioned downstream calibration/retention/physical-veto/
receiver/clustering contract, preserving arithmetic; then qualify disjoint
calibration-context transfer and finite-exposure integrated controls. Do not
rerun these closed arithmetic checks as a new work package or relabel the old
two-column basis. A new same-scan provenance
observable is still required before unblocking spectra; the
[minimal retrieval specification](RADIO_HD1461_PROVENANCE_REQUEST_2026-09-26.md)
is unsent. Three extra hourly evening continuations support the owner's
request for several hours of work. The LS8BF source stays unopened.
