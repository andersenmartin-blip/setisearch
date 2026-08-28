# Milestone 37 detector-v0.6 operational-runner gap analysis

Status: **NON-FROZEN, NON-SPECTRAL ARCHITECTURE ANALYSIS**.

Progress update (2026-08-28): the factor bundle, cache-plan rehydration,
run-level cache manifest, global-null artifact, fail-closed journal and real
metadata-only bootstrap described below now exist locally and pass the full
repository suite. See `MILESTONE_37_DETECTOR_V0P6_RUNNER_PROGRESS.md`.
Width-streaming physical evidence, completeness equivalence and the complete
production runner remain open; this document therefore remains non-frozen and
does not authorize spectral access.

This document maps the remaining path from the tested detector-v0.6
components to a restartable M37 operational run. It does not implement or
attest a production runner, authorize spectral access, calibrate a threshold,
or make a scientific claim.

## Why a top-level runner is not yet honest

The current candidate M37 factories require the exact 96-row `FactorBasis` and
the derived 93-by-96 `TemplateFactorTable`. The factor-basis and label
identities are code-pinned, but the final factor-table and derived
analysis-contract identities remain unreproduced blockers. None of these
arrays is stored as a rehydratable repository artifact. Reproduction requires
the pinned Astropy/ephemeride environment, which is not available in the
present local runtime.

The live path also depends on factory-attested normalized scan products and
several process-local artifacts. A callback shell could be written around
those APIs, but it would not prove the M37 lifecycle, restart behavior,
resource ownership, or cross-process provenance. Such a shell must not be
called a production runner.

## Required stage order

### 1. Metadata bootstrap before spectral access

1. Validate the published M37 scan definitions.
2. Reproduce the exact factor basis in the pinned runtime.
3. Derive the canonical 93-template factor table.
4. Build the five proxy-carrier grids.
5. Load and hash-gate the five explicit 256-by-3 scramble tables.
6. Compile and attest the native calibration kernel on the selected host.
7. Atomically publish a factor bundle and execution-environment receipt.

The factor bundle must contain the arrays, labels, row selections, source
metadata hashes, environment identity, and canonical hashes—not only their
expected digest strings.

### 2. Authorized extraction and normalization

Only after a separate authorization may
`iter_m37_normalized_scan_products(...)` contact an HDF5 source. The adapter
must attest the published URL, size, ETag, header, extraction interval and
header-native descending axis before `normalize_m37_extracted_scan(...)`
performs the single canonical reversal and exact float32 normalization.

The runner must consume one product at a time and publish its extraction and
normalization receipt before releasing it. A valid local byte seal is evidence
about the supplied bytes and metadata; it is not by itself proof of their
remote origin.

### 3. Native cache materialization

For each of five windows, six scans and eight widths:

1. build the production `NativeFilterCachePlan` from the attested source;
2. filter on the native channel axis;
3. publish the payload and cache receipt atomically;
4. reopen it through the trusted disk verifier; and
5. release the source and temporary cache arrays before advancing.

A run-level cache manifest must bind all 240 cache plans, payloads, logical
paths and source products. The current single-cache receipt is insufficient
for restartable aggregate discovery.

### 4. ON calibration and threshold

Per window, the runner must iterate template by template. For each template it
opens three ON cache handles for one width at a time, constructs all eight
three-epoch products, builds the width-OR mask, updates all eight native
calibration passes, and releases the products and mask.

After all 93 templates, the window accumulator must seal its observed maximum,
256 null maxima, complete cache/epoch/mask inventories, native execution
identity and exact score-cell count. `finalize_m37_threshold(...)` may combine
only the five complete windows in the code-pinned candidate order.

### 5. Exhaustive ON and OFF retention

With the final threshold fixed, both ON and OFF passes rebuild the same
deterministic products. Every template, width, activity subset and q cell is
visited, and every finite score at or above threshold is retained. The ON
pass must reproduce the provenance inventories bound during calibration.

Any record, byte, shard or memory cap failure invalidates the run. Truncation,
threshold adaptation and report-only NMS are not permitted as evidence.

### 6. Physical disposition

Exact/local retained-OFF matching, single adjacent-OFF evidence and
receiver-frame signature measurement all consume retention/cache artifacts
and may execute independently. Receiver-alias connected-component
classification is the mandatory join: it consumes the complete outputs from
all three without rewriting their upstream evidence.

OFF, adjacent and receiver-alias certificates must each bind the complete ON
record inventory they consumed. A member cannot inherit a physical veto from
another member.

### 7. Significance and five-window outcome

Global rank-p is evaluated against the original retained ON records and the
exact global null-maxima vector. The five-window outcome joins independently
trusted retention, physical-disposition and significance receipts and applies
the candidate preflight-listed stopping outcomes.

### 8. Completeness

Each of 6,144 trials must obtain a one-shot, seed-selected three-ON background,
inject into normalized native float32 arrays before filtering, rebuild masks,
run the operational detector and physical passes, derive rank-p, and add one
complete trial receipt. Production remains disabled until the full replay or
a complete bit-identical sparse/local replacement is proven feasible. Phase 1
covers synthetic truth-local gathers, mask closure and hypothesis scoring. The
bounded phase-2 KAT adds byte-identical ON/OFF retention, all three
retained-OFF branches and rank-p boundaries, but only by requiring a complete
dense-score oracle capped at 1,000,000 cells. Phase 3 binds that receipt
through complete synthetic adjacent-OFF evidence and receiver-alias connected
components, including transitive identity closure and all five final
dispositions. Production receipts, the full resource envelope and this runner
lifecycle remain open.

## Memory lifecycle

- One largest normalized source product owns `124,704,792` ndarray bytes.
- Three retained source products plus three rolls require `550,168,200` bytes
  and exceed the `536,870,912-byte` cap.
- One full epoch product owns `8,971,980` bytes; eight own `71,775,840` bytes.
- One full template mask owns `2,242,995` bytes.
- The conservative full template-mask stage is approximately
  `500,969,911` bytes including retained source/background arrays and scratch.

Consequently, the proposed runner must release source products and cache-build
scratch before the template stage, open cache handles three scans at a time
for one width, and retain eight epoch products plus one mask only for one
template. Completeness already charges these payloads explicitly. Receiver,
adjacent and the primary-run envelope do not yet enforce the same aggregate
mapped-byte cap, so their future receipts must add ownership and measured or
conservatively projected peak bytes rather than assuming the bound is already
proved.

## Concrete API and artifact gaps

1. **Factor bundle:** no persisted/rehydratable factor-basis and factor-
   table artifact exists.
2. **Global null artifact:** the threshold binds the global null hash, but
   significance also needs the exact vector; no receipt-bound export
   and rehydration API exists.
3. **Cache plan records:** a cache receipt does not carry the complete plan,
   and there is no candidate `NativeFilterCachePlan.from_record` verifier.
4. **Run-level cache manifest:** aggregate cache completeness, paths and
   source ancestry are not sealed in one inventory.
5. **Process-local products:** epoch vectors, masks and calibration
   accumulators have live receipts but no lightweight checkpoint
   format. Threshold certificates and normalized source arrays can be
   rehydrated, so the chain can be split by expensive reproduction; it is not
   literally restricted to one process. Cheap restart from the calibration
   or cache stages is nevertheless unproved.
6. **Receiver stage integration:** the width-streaming receiver interface is
   bit-identical to full-inventory execution, but the runner does not invoke,
   checkpoint or bind its resource receipt.
7. **Adjacent stage integration:** the width-streaming adjacent-OFF interface
   is bit-identical to full-inventory execution, but the runner does not
   invoke, checkpoint or bind its resource receipt.
8. **Completeness implementation:** `CompletenessDataSource` and
   `CompletenessOperationalPipeline` remain interfaces, not production
   implementations.
9. **Run envelope:** no run-directory schema, stage journal, restart rule,
   aggregate manifest, or atomic final-publication contract exists.
10. **Pinned runtime:** extractor dependencies, OS/compiler/OpenMP runtime,
    CPU/ISA policy and the eight-thread host requirement are not yet frozen.

## Prioritized closure sequence

1. Reproduce and publish the exact factor bundle in the pinned non-spectral
   environment.
2. Add canonical, independently verifiable artifacts for the factor bundle,
   global null vector, cache plans and run-level cache inventory.
3. Integrate the existing width-streaming receiver and adjacent interfaces
   into the runner and bind their explicit arena accounting to the run-level
   receipt.
4. Define a run-state journal whose transitions require the prior stage's
   trusted aggregate receipt and whose invalid state is permanent.
5. Build a synthetic/reference runner against those persistence and streaming
   interfaces, including crash/restart, duplicate, missing-stage and cap
   failures.
6. Close the completeness feasibility gate.
7. Only then implement the M37 production runner, pin its environment and
   benchmark, publish the preregistration, and obtain independent verification.

Until that sequence passes, the defensible statement is that the v0.6
components and several real cross-stage joins are locally tested; an
operational M37 lifecycle is not yet established.
