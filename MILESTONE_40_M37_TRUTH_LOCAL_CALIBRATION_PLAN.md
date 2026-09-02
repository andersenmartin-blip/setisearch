# Milestone 40 M37 conditional truth-local calibration plan

Status: **EXECUTION PREPARATION — M39 GATES PASSED; NO M40 TRIAL EXECUTED**.

## Purpose

Milestone 40 executes the complete retrospective calibration frozen by M38
and authorized by M39. It retains all 512 continuous physical truths at all 12
exact ideal single-epoch S/N levels, for exactly 6,144 trials in the frozen
M37 1412.5 MHz background.

Each trial deterministically circular-shifts the three normalized ON epochs,
injects the truth in native channels before filtering, rebuilds every required
spectral width, recomputes the two-pass mask, and evaluates the M39-qualified
truth-local score adapter. Recovery is the inclusive condition that the best
finite truth-local score is at least the frozen M37 operational threshold of
126.20158386230469.

## Pre-execution freeze

Before the first M40 injection, the runner publishes a deterministic start
certificate binding:

- the M39 qualification certificate, source/cache completion, and three-anchor
  aggregate;
- the unchanged 512-truth and 6,144-trial inventory identities;
- the M39 adapter, M37 completeness implementation, runner source, output
  schema, threshold, and execution configuration; and
- an explicit authorization flag.

Existing completed trial records are immutable restart checkpoints. Trials
may be split into deterministic modulo shards, but the final aggregate is
forbidden unless every expected trial appears exactly once and no extra file
exists.

## Resource and persistence boundary

The three injected native scans exist only for the current trial. Filter
caches are constructed and opened one epoch/width at a time, then released;
their payload identities remain bound in the adapter receipt. Large transient
cache payloads are not accumulated or committed to Git.

Every completed trial is published as canonical JSON below the execution run
root. At completion, the ordered ledger is exported as deterministic gzip
JSONL together with a compact aggregate and hash manifests.

## Permitted result

M40 may report only pointwise conditional truth-local recovery fractions and
their predeclared Wilson 95% intervals at the 12 exact S/N levels. It may not
interpolate between levels or claim calibrated physical-veto survival, replay
of the global false-positive field, end-to-end detector completeness, an
occurrence-rate constraint, or a technosignature.

This plan is retrospective: the M37 candidate outcome was already known when
M38 selected this endpoint. M40 does not change the closed M37 Run 006 outcome
or rehabilitate the permanently invalid Run 004.
