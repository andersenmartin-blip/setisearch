# M43Q — integrated Cartesian-bank detector qualification

Connect the qualified M43 components to one explicit diagnostic entry point:
mask construction, global-null/threshold handoff, exhaustive ON/OFF retention,
same-hypothesis and 20-Hz local OFF-track matching, paired single-OFF rejection,
native stationary receiver signatures, receiver-alias identity partition and
inclusive rank-p evaluation. Preserve the existing numerical and physical
rules. This is the integration gate before fresh null/native-injection work.

## Catalogue and provenance bridge

The M43E bank is Cartesian. Most templates lack the line-bank presentation
fields required by the generic v0.6 retention schema. Create a new catalogue
identity with the exact original coefficient_x/coefficient_y and explicit
parent bank/template identifiers. For compatibility, line_index identifies
the parent template, line_coefficient/projected_scale give its radius, and
phase_cycles gives its individual Cartesian angle. These do not assert a
common one-dimensional line. Calculations continue to use the unchanged
Cartesian coordinates. Assert bit-exact factors for the complete 1,701-entry
bank and for the 37-entry diagnostic selection. Never reuse the old catalogue
identity or insert fabricated M37 provenance products.

The score store verifies every full M43P ancestor array against its retained
batch hash. It then checks copied template-row bytes at every handoff against
the initial verified inventory. The detector snapshots the expected identities
before calibration, so changing an array and its supplied identity cannot
silently change the experiment. Legacy generic algorithms accept arrays;
their optional M37 provenance flags remain false. An outer M43 inventory binds
all source/score evidence instead. This is a named interface, not an attested
M37 production run.

Paired OFF queries use the already verified full native-gather output vectors
at the exact requested score index, with no mask. Each width/epoch vector
cache has its own M43Q plan and a hash of actual template-major float32 payload
bytes. Those plans are recorded explicitly; they are not M37 native caches.
Receiver signatures use the original receipt-bound M43I native-filter caches,
the arithmetic mean of predicted integration frequencies, a literal ±100-Hz
native receiver window, and the first ascending-channel maximum on ties.
The adapter must reject incomplete windows and changed cache identities.

## One combined execution

1. Run a synthetic whole-pipeline fixture containing a same-hypothesis OFF
   match, a local OFF-track match, an exact 5.5 paired-OFF veto, a mask formed
   at another width, two distinct receiver-alias identities, and a member
   whose only strong OFF epoch is inactive. Require the predeclared member
   dispositions, including a physical-veto survivor. These are score-level
   known-answer additions, not native injection/recovery trials.
2. Reuse the M43P full-support arrays for templates 0–31 and 1696–1700 in
   six scans at all eight widths. No new downloads and no new full-bank score
   census. Refuse missing, changed or incorrectly ordered inputs.
3. Independently check 144 real stationary-receiver signatures: three ON
   scans × eight widths × parent templates 0 and 1700 × first/middle/last
   score carriers. Compare directly summed native windows and literal winner
   selection to the new adapter, even if no real diagnostic member is retained.
4. Run the integrated entry point on all carriers of the 37-template sample.
   Reuse the same four M43P scramble rows to exercise the global threshold
   handoff. The diagnostic threshold is max(50, maximum of four global null
   maxima), with inclusive retention. Require global maxima to equal the
   independently retained M43P per-template maxima aggregated by scramble.
   The reference floor 50 is an engineering setting, not a calibrated science
   threshold. No threshold adjustment or adaptive rerun is permitted here.
5. Retain every eligible member, capped at 10,000 per kind with no truncation.
   Run all physical stages and join each final disposition to its inclusive
   rank-p evidence by exact record identity. Preserve the inherited survivor
   label while exposing a clear `passes_evaluated_physical_vetoes` Boolean.
   Four nulls have minimum rank p=0.2; none can meet the 0.01 science cutoff.
   Every result remains explicitly diagnostic, with scientific_candidate=false.

The 20-Hz association rule and physical precedence remain unchanged. The
receiver algorithm's capacity gates are retained. One process runs the
integration; native receiver caches are reused by source and width. Reuse
the existing test suite and add focused integration/provenance/capacity and
literal receiver tests. Freeze code/configuration/test evidence publicly
before real evaluation. Keep complete output stages and the run log together;
on failure write a failure artifact and refuse an aggregate success result.

## Claim boundary and next work

M43Q tests a complete connected diagnostic path, with a full-bank geometry
bridge and a 37-template real-data sample in one window. It is not a full-bank
spectral search or a fresh null calibration. Native injected signals have
not been tested in this milestone. Synthetic signatures test logical outcomes;
the 144 real native-window controls independently test signature measurement.
No candidate or scientific nondetection is established.

After a pass, freeze a joint fresh null/native-injection programme using the
integrated entry point, with its own search scope, source provenance, resource
limits and reporting denominator. Existing source/filter/score arithmetic
should be reused; the next purpose is measured false-alarm behavior and
recovery, not another unchanged-arithmetic census.
