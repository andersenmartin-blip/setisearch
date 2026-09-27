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

**Current continuation, 27 September:** the restart/metadata package is complete.
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
receiver/clustering contract, preserving arithmetic. That
[continuation is now complete](RADIO_DIRECT_DOWNSTREAM_2026-09-26_RESULT.md):
eight new tests and eight targeted regressions pass, but the engineering control
gate fails because a matched ON/OFF signal leaves 13 unassociated width-129
members in two clusters. The intended track is vetoed; retained evidence shows
one-epoch signal intersection plus marginal support in another epoch. No setting
is retuned. The [identity-bound cross-window contract and fresh control freeze](RADIO_CROSS_WINDOW_CONTRACT_2026-09-26_RESULT.md)
are now complete: 13 tests pass, exact-context reuse is refused and a new
24-case panel zero-gates broad-width unassociated leakage without rerunning the
closed failed panel. Its blocked execution envelope is now published below;
numeric transfer and panel execution remain blocked. Do not
rerun the closed arithmetic checks or relabel the old two-column basis. A new same-scan provenance
observable is still required before unblocking spectra; the
[minimal retrieval specification](RADIO_HD1461_PROVENANCE_REQUEST_2026-09-26.md)
is unsent. Three extra hourly evening continuations support the owner's
request for several hours of work. The LS8BF source stays unopened.

The [execution-envelope continuation](RADIO_EXECUTION_ENVELOPE_2026-09-27_RESULT.md)
is now complete with thirteen tests. Runtime, local codec evidence, factor
arithmetic, windows, fresh controls and a zero-reservation cumulative namespace
are bound together, but five gates remain false and spectra stay closed. The
new v2 ordered-role ledger separates valid 512 MiB session caps from the 1.5 GiB
three-session cumulative cap; the old exhausted synthetic ledger is not reset.
Local durable v2 reservation/controller integration now passes fsync/CAS,
wrong-order, stale-parent and ambiguous-publication tests without a network
budget. The fixture-only codec-to-direct receipt boundary and pinned
publication-store protocol are now complete as described below. Do not execute the frozen panel,
adopt a physical motion bank or qualify numeric transfer from missing evidence.

The [local codec/publication package](RADIO_CODEC_PUBLICATION_2026-09-27_RESULT.md)
now passes 24 tests. Twelve local codec receipts feed the direct score store;
1,634,496 normalized and 14,112 score cells agree bit-for-bit with independent
references. This is one synthetic cadence encoded with two codecs. The new
publication guard closes a demonstrated low-level reset/rebinding gap and
retains ordered role limits under contention and lost replies. No published
ledger or original contract was changed. The remote v2 protocol is frozen but
unactivated; five execution blockers and zero telescope reservations remain.

The [bounded motion-contract continuation](RADIO_MOTION_CONTRACT_2026-09-27_RESULT.md)
is now complete with 20 tests. New primary/reference metadata identify e=0.172
as a 99% upper credible limit and expose mixed sources in the old snapshot.
The unchanged bank remains a conditional engineering scenario. One fixed
scale/phase witness has 112.396874 Hz minimum maximum center mismatch across
all three ON epochs, even with a free carrier; no detector recovery claim is
made. The new analytic emitter interpolation bound covers only that conditional
subcomponent. Full physical accuracy remains blocked with named missing terms.
Three direct artifact requests used 2,552,106 response bytes; telescope requests,
reservations and new scientific evaluations remain zero.

The [injected GitHub v2 backend](RADIO_GITHUB_V2_2026-09-27_RESULT.md) is now
implemented and passes 31 new tests with actual local Git objects/ancestry.
Its 638 simulated calls in 53 isolated repositories cover identical/distinct
writer races, response loss, immutable reads, single-file changes and read-back
ancestry. A duplicate-ack baseline motivates unique publication-attempt IDs.
All 579 archived Git objects verify. The backend is fixture-qualified only:
there is no HTTP adapter, live namespace activation or telescope reservation.

**Prior continuation, now completed below:** prepare and publish one bounded
prospective live rehearsal contract, with a separate qualification namespace/genesis, finite
GitHub-only operation budget, bounded transport, durable attempt journal and
explicit crash/restart rules. Preparing it must not initialize a namespace,
reserve quota, activate the telescope path or reuse/reset the closed demo.
Do not relabel fixture tests as live qualification or repeat them unchanged
as progress. Further physical work needs the motion report's specific inputs
or an explicit prospective domain/convention contract. No bank expansion,
failed-control tuning, fresh 24-case evaluation or spectrum opening. Pointing
still needs genuinely new same-scan provenance. Closure remains 9 October.

The [prospective rehearsal contract/journal package](RADIO_REHEARSAL_CONTRACT_2026-09-27_RESULT.md)
is complete with 25 new final tests. Two actual child-process exits establish
local crash behavior before/after a simulated side effect; replay grants zero
dispatch rights. All stop/failure evidence and both development runs are retained.
A separate inactive namespace/genesis and 160-tool-call / 32-MiB returned-text /
1,200-second proposal are pinned. There is no live activation or source access.
Connector HTTP/version/retry/pre-decode/cancellation terms remain unavailable;
local fsync does not establish remote ownership or loss-of-scratch recovery.

**Prior continuation, now investigated below:** complete the offline typed
connector/phase-ownership/recovery boundary under this fixed contract. Include remote
grant bootstrap, immutable confirmation, checkpoint retention, read-only recovery
and closure in its total; never create an unmetered administrative path or restore
spent allowance through a fresh namespace. Preserve the backend's one-append,
unique-attempt and ancestry guards without disguising live calls as fixtures or
inventing HTTP response guarantees. Publish/verify this new evidence and an
explicit transport disposition before any live activation. The contract/journal
preparation is complete; do not repeat it as progress. Five science blockers and
the same-scan pointing requirement remain unchanged. No control tuning, new
physical bank, 24-case evaluation or spectrum opening. Closure remains 9 October.

The [typed connector/ownership continuation](RADIO_CONNECTOR_2026-09-27_RESULT.md)
now passes 20 new offline tests. Typed envelopes, commit-message identity,
immutable confirmation and the phase-wide journal compose with an explicitly
supplied independent admission fixture. Fresh-client recovery does not resend
the uncertain mutation. All 371 simulated calls, 14 journals and 196 verified
Git objects from the final run are retained. No live namespace, remote grant or telescope access
was created. The original proposal and five science blockers are unchanged.
A new regression exposed an initially missed phase-veto gap: a fresh store could
reuse the old journal/owner after a semantic rejection. The correction terminates
the phase and revokes ownership; the reproduced failure and all three local
qualification runs remain archived. Twenty final cases are counted once.

The bootstrap investigation exposes a concrete remaining requirement: calls
cannot safely create their own prior admission record after local state loss.
The unsafe baseline reaches 13 calls against initialization's 12-call cap and
161 against the total 160, with unchanged branch/grant state. Live startup needs
an independently durable admission authority with accounted provisioning before
the first call, plus the missing transport controls; the SQL fixture is not one.

**Latest continuation:** close this offline engineering investigation. Do not
repeat the fixtures or construct another self-funding GitHub grant loop. Reopen
live engineering only for concrete new admission/transport capability or a
published prospective alternative that preserves frozen contracts. Continue the
independent prospective phase-agnostic motion-domain/convention item using
retained metadata: declare conditional support and emitter/relative-axis/time/
frequency meanings, keeping unqualified error terms explicit. Do not adopt a
physical bank, infer a joint confidence region from marginal errors, refresh the
closed catalog/paper lookup, create templates, retune controls or open spectra.
Pointing still requires genuinely new same-scan evidence. Closure is 9 October.

## 27 September: conditional motion-domain and convention declaration complete

The [prospective phase-agnostic declaration](RADIO_PHASE_DOMAIN_2026-09-27_RESULT.md)
passes **16 new tests**. It explicitly declares a conditional P/a/e rectangle,
all phases/orientations and the planet-COM projection identity, with no joint
probability or real-source membership claim. The e=0.172 endpoint remains an
upper credible limit. Relative, emitter and projected axes; legacy phase sign;
circular degeneracy; reception/emission time; and received-carrier meaning are
now distinguished. Zero radial speed is not assumed to mean zero total speed.
Nine full physical terms remain null, and every authorization flag stays false.

No catalogue refresh, template, bank, spectrum, scientific control or old phase
witness was evaluated. All nine pinned old inputs and all five execution
blockers are unchanged. The single test run and three scalar axis examples are
retained. This completes the declaration, not physical motion qualification.

**Exact continuation:** proceed to conditional source-time/Doppler error and
continuous parameter sensitivity bounds using this declared support. Derive
varying light-travel delay and proper/coordinate frequency distinctions; test
new equations against independent scalar oracles. Do not adopt real-source
support, build templates, tune widths/controls or fill unknown total errors
with partial bounds. Connector/admission work remains closed at its named live
capability requirement. Pointing still needs genuinely new same-scan evidence.
Keep the original preparation and ledgers immutable; closure remains 9 October.

## 27 September: conditional emission-time and Doppler terms bounded

The [time-transfer continuation](RADIO_TIME_TRANSFER_2026-09-27_RESULT.md) passes
**15 new tests**. For the published conditional domain, all-phase bounds give
0.962743 s of varying orbital delay and, at 1500 MHz, 10.954242 Hz for wrong
clock use, 21.919242 Hz for reciprocal versus first-order Doppler, and 10.959621 Hz
for the normalized transverse term. Their 43.833105-Hz sum bounds only a fixed-
LOS stationary-receiver emitter comparison; full physical error remains null.

Four fixed scalar endpoint examples retain every signed contribution, spanning
-12.286907 to +3.439298 Hz combined difference. They are equation examples,
not bank coverage, telescope evidence or detector-recovery cases. Independent
bisection/fixed-point and Decimal checks pass. No new template, old phase sweep,
control or spectrum was evaluated. All twelve pinned old inputs remain intact.

**Exact continuation:** derive continuous-parameter sensitivities for the
conditional retarded proper-frequency model, including implicit emission time,
and calculate a sufficient covering cost without constructing templates. Use
periodic-angle distances; do not mistake a loose sufficient grid for a necessary
minimum or measured runtime. No physical adoption, confidence claim, width
change or control tuning. Full error, all five blockers and the same-scan
pointing hold persist. The original plan still closes on 9 October.

## 27 September: continuous conditional sensitivity and covering cost quantified

The [continuous covering study](RADIO_MOTION_COVERING_2026-09-27_RESULT.md)
passes **13 new tests**, bringing this connected domain/time/coverage work to
44 distinct new tests. Six global parameter derivatives include implicit
emission time, full-speed proper-time effects and circular-angle geometry.
Two independent scalar gradient points agree with the envelopes and bracketed
clock inversion. No search bank or scientific control was computed.

One equal-error Cartesian construction would use about 4.333e36 nodes and
9.983e39 bytes of dense factors at the illustrative half-channel tolerance.
That is a loose sufficient construction, not a necessary bank-size bound,
source expenditure, runtime measurement or proof that searching is impossible.
It discards normalization cancellations and parameter/trajectory structure.
All seventeen pinned old inputs and all five execution blockers are unchanged.

**Exact continuation:** do not construct or optimize this grid. Continue with
bounded analytic temporal compression: uniform low-order polynomial remainder
bounds for the same conditional retarded emitter setting, using derivative
majorants and a prospectively fixed small set of orders. No templates, detector
runs, width changes or physical adoption. Then document the combined work's
compatibility limits with the immutable execution envelope and unexecuted panel.
Pointing and live admission still need their concrete missing evidence; the
plan remains limited to 9 October.

## 27 September: conditional temporal certificate and integration disposition complete

The [temporal-majorant result](RADIO_TEMPORAL_MAJORANT_2026-09-27_RESULT.md)
passes **14 new tests**. Exact rational derivative majorants with outward pi/
square-root enclosures bound degree-5 and degree-6 temporal remainders by
**0.458764711 Hz** and **0.057497818 Hz** at 1500 MHz over the declared numeric
cadence extent. Both are below the illustrative half-channel tolerance for the
conditional retarded emitter model. No polynomial, template or bank was made;
this does not qualify coefficient coverage, runtime, recovery or actual-source
physics. The full physical error remains null.

The connected four-part investigation is complete with **58 distinct new tests**:
16 domain, 15 time/Doppler, 13 parameter-covering and 14 temporal-majorant checks.
Each package was advanced from the latest verified publication. New metadata/
source requests, telescope reservations, spectra, scientific trials and evaluation
exposures are all zero. The old preparation, exhausted ledger, empty telescope
genesis, exact windows and all five blockers are unchanged.

A separate integration disposition preserves the 3-calibration / 24-case / one-
evaluation / zero-remedy limits. The unexecuted synthetic panel is not evidence
for the new conditional family or a polynomial bank. A small new-model
truncation bound cannot certify the unchanged old first-order factor pipeline,
or turn its omitted terms into a complete physical error budget.

**Exact continuation:** this conditional investigation is closed. Do not repeat
its tests, increase polynomial degree, build the huge grid, create another
arbitrary box or run the fresh panel. The next evidenced route to the HD1461
pilot needs (a) genuinely new same-scan RAW/FIL/log/file-specific conversion
provenance for AGBT16A_999_189 ON 0015/0017/0019; (b) evidence-backed physical
support, source/observer clock/frame and omitted-motion/instrument allowances;
and (c) concrete independent live admission/provisioning and transport evidence,
or an explicit prospective alternative preserving frozen contracts. Reopen
engineering only for a specific new input or concrete implementation risk with
a prospective bounded scope. Do not manufacture progress through repeated empty
checks. No unblocked telescope-execution step is established. Preserve the
same target and all earlier dispositions; period consolidation remains 9 October.


## 27 September: score reconstruction gap guarded; local restart verified

A [new score-handoff package](RADIO_SCORE_HANDOFF_2026-09-27_RESULT.md) addresses
one concrete implementation risk found after the closed motion investigation.
A reconstructed legacy store can pass its self-computed vector checks while
retaining stale native-cache hashes. The separate guarded path rejects that
mismatch and preserves all 4,752 score cells / 48 vector identities exactly.
**26 new tests pass**, including bounded pinned checkpoint loading, concurrent
writers and process-crash recovery. The two harness errors are retained.

This is opt-in local engineering: old numerical modules remain unchanged and
do not automatically gain the guard. A separately retained receipt pin is
mandatory for restoration. No detector, calibration, telescope request,
reservation or scientific evaluation ran. Power-loss/remote durability and live
admission are not qualified. All fifteen old input pins, the exhausted ledger,
empty telescope genesis, original preparation and five blockers are unchanged.

**Exact continuation:** the score-handoff/checkpoint task is closed. Future
integration must use its guarded API and external receipt pin. Do not replay
closed tests or invent a generic hardening task. The scientific path still needs
new same-scan RAW/FIL/log/file-specific conversion evidence for AGBT16A_999_189
ON 0015/0017/0019, evidence-backed source/observer physics, and concrete independent
live admission/transport capability. No unblocked telescope step is established.
Reopen only for a named new input or demonstrable new risk with a bounded scope.
Preserve HD1461, neighbor9 and every prior disposition; consolidate on 9 October.

## 27 September: selected public directory route closed without original provenance

A [new directory-level check](RADIO_DIRECTORY_PROVENANCE_2026-09-27_RESULT.md)
examined the two publicly linked subdirectories of AGBT16A_999_189, without
opening any product. All **78 listed files** have .h5 names; nine match the
three selected ON scans, including all three pinned fine-resolution URLs.
No RAW/FIL or log/header/conversion sidecar is listed. This limited absence in
two indexes does not establish that originals are absent elsewhere.

Three direct HTML GETs consumed 14,089 bytes. Three prior web-reader opens
have unknown wire totals and are separately recorded. Raw child-index bodies,
complete hrefs, transport receipts and an independent offline inventory check
are retained. Fifteen prior input pins are unchanged. No telescope product,
header in a data file, spectrum, reservation or scientific trial was opened.

**Exact continuation:** close this particular directory route; do not repeat its
unchanged indexes or count the derived HDF5 products as original provenance.
The next pointing input remains a same-scan RAW/FIL header, observing/GO record
or file-specific conversion proof for AGBT16A_999_189 ON 0015/0017/0019.
The unsent retrieval specification already lists the exact requirements;
external contact is outside the current instructions. A genuinely new public
original-record link or supplied record may reopen a bounded investigation.
No unblocked telescope step is established. The source/observer physics and
independent live admission requirements, all five blockers, HD1461, neighbor9
and all earlier dispositions persist. Do not invent generic engineering work or
repeat empty checks. Period consolidation remains 9 October.

## 27 September: public HIP1499 log row retained; archive request ready and unsent

A [new targeted lookup](RADIO_PUBLIC_LOG_CONTACT_2026-09-27_RESULT.md) found
HIP1499 in the official-linked public GBT progress sheet: Dec −8.053611 degrees,
L-band date `2016-05-14 16:58:31`. The row does not identify the session/scans,
original coordinate source/frame or clock convention. Its date is six seconds
earlier than the rounded scan-0019 UTC header only if clocks are comparable.
It cannot resolve the approximately 34.23-arcminute header discrepancy.

One public query returned one row in 652 bytes; the exact response, receipt,
scoped retrieval code and offline reconciliation are retained. Fifteen earlier
input pins remain unchanged. No telescope product, spectrum, scientific trial,
reservation or external message was opened/sent. All five blockers persist.

A complete [metadata request](RADIO_HD1461_ARCHIVE_EMAIL_DRAFT_2026-09-27.md)
now lists all three scans and asks the official general Berkeley SETI contact
to route it to the archive custodian. **It is unsent**, as required by the
owner's prohibition on external messages. No custodian or sending capability
is assumed merely from finding a public routing address.

**Exact continuation:** close this particular sheet lookup. The owner can
review/send the prepared request, authorize sending through an available
channel, or supply the original same-scan metadata. Reopen only for a new
original RAW/FIL/GO/log record or documented deployed conversion with original
input bytes for AGBT16A_999_189 ON 0015/0017/0019. Do not repeat closed directory,
catalogue, converter or generic engineering checks. Source/observer physics
and independent live admission also remain required; a reply alone does not
authorize spectra. HD1461, neighbor9 and every prior disposition are unchanged.
No unblocked telescope step is established. Consolidate on 9 October.
