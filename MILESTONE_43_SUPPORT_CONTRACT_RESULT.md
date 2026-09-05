# Milestone 43: support-contract checkpoint

Status: **FIRST CHECKPOINT COMPLETE; NO CONTRACT-PRESERVING REPAIR
DEMONSTRATED; FULL M43 REPAIR QUALIFICATION REMAINS OPEN**.

The milestone track has resumed after LS6A. The complete M41 ledger was
reassembled and its 6,144 records validated by the unchanged M42 code. The
M42 diagnostic reproduces byte for byte: 98/512 truths have geometric
support, and 414/512 do not. Original recovery counts and denominators are
preserved.

## What the first M43 check establishes

Seven small fixtures make the support requirements explicit. The bounded
interval planner, the legacy materialized planner and an independent
exhaustive Boolean calculation agree in all seven. The two legacy planners
also return identical complete plan records, including identities and mask
dependency indices.

| Fixture | Joint template/carrier cells | Support separately at each epoch? |
|---|---:|---|
| Aligned tracks, inclusive 20 Hz | 41 | Yes |
| Incompatible carrier intervals | 0 | Yes |
| Different templates fit different epochs | 0 | Yes |
| Inactive-epoch mismatch | 0 | Yes |
| Continuous solution between carrier cells | 0 | No grid cells |
| Exact match, zero tolerance | 1 | Yes |
| Tolerance one binary64 step below 20 Hz | 39 | Yes |

The rule requires one template and one carrier cell to match the truth at
every integration of all three ON epochs. Separate matches using different
templates or carriers at different epochs do not satisfy it. These fixtures
have one integration per epoch to isolate that logical requirement; existing
regression tests also cover multiple integrations and dense score replay.

In the inactive-epoch example, using only the first two epochs yields 41
cells instead of zero. That is an explicitly labelled demonstration of a
different association rule, not a correction adopted by this checkpoint.
The published M41 rule includes all ON epochs even for pairwise injections.
Injected width and S/N do not enter the geometric candidate calculation.

## Scientific and implementation decision

There is no demonstrated implementation discrepancy in these fixtures to
repair. Broadening the tolerance, omitting inactive epochs, adding bank
templates, or allowing different carriers across epochs would change the
endpoint. Such a change cannot inherit M41's calibration or M39's anchor
qualification merely because it increases the number of supported truths.

Production code, search thresholds and historical artifacts remain unchanged.
The fixtures are not a proof that every possible planner input is correct.
Nor do they determine which geometric constraint excludes each of the 414
individual M41 truths: their support is revalidated from the sealed ledger,
not recomputed from a newly reconstructed real factor bundle here.

The agreed M43 sequence required a reproducible example before a small repair,
then regression tests and a separate deterministic real-data replay. This
checkpoint completes the baseline and contract diagnosis. A new real-data
replay was not executed because no contract-preserving repair was established.
Historical M39 anchor receipts remain historical evidence, not a new replay.
No telescope spectrum, injected cache, or new calibration trial was opened.

## Next restart point

Before another injection campaign, define a separately named prospective
association endpoint. A candidate specification should say explicitly which
activity epochs must match, how native spectral width enters association,
and whether one fixed template and carrier are required throughout. Evaluate
the geometric coverage of all 512 original truths without deleting unsupported
ones. This stage must distinguish bank coverage from mask and threshold losses.

Only after that definition is frozen should a new implementation be qualified
against exhaustive real-data anchors, including newly supported and unsupported
cases and narrow/wide injected lines. The original all-epoch, 20 Hz endpoint
must remain available as a baseline. No additional S/N extension is justified
by the current result alone.

This is consistent with the owner's explicit multi-year project horizon:
validated negative results and a well-defined limitation are useful progress.
LS remains an open research branch; its recent outcomes do not establish that
the light-sail search should be abandoned. See [the recorded project
direction](PROJECT_DIRECTION.md).

## Reproduction and evidence

`config/m43_support_contract.json` fixes the fixture implementation and source
hashes before its first execution. This is a local retrospective fixture
freeze, not a claim of public preregistration or unseen-data evaluation.
`results_m43_support_contract/qualification.json` contains all fixture inputs,
per-integration support counts, interval limits, candidate cells and plan
identities.

Result identity:
`b80763df9bb22dd40105cdaa183aa0f34d88259ff3921a0c833e5eb42b2eea94`.

The completed baseline suite ran 511 tests successfully with two expected
skips. All four new M43 tests also pass in a separate focused run. An additional
combined-suite attempt ended without a unittest summary and is not counted
as a completed run. No production code changed between baseline and the new
fixture tests. Verification status and log digests are recorded in
`results_m43_support_contract/validation.json`.
The initial baseline run started from the README/main checkout, which lacks
the branch-published M42 implementation. It was cancelled after the complete
analysis branch was selected; only the completed runs on the analysis branch
are used for validation. No conclusion is drawn from the cancelled run.

```bash
PYTHONPATH=src:scripts python scripts/m43_support_contract.py
PYTHONPATH=src:scripts python -m unittest discover -s tests -v
```
