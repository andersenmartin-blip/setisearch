# Weak complete-truth-path rank diagnostic

This directory contains the bounded 14 October 2026 follow-up to the exact
native-channel path family. It reads only the preserved `INJECTIONS.json`,
`PROFILES.json` and 54 `*_paths.npz` arrays from
`SETI_NATIVE_SPOR_2026-10-14.zip`. It does not open telescope files or rerun
the search.

The computation ranks the best known complete four-bin truth path in every
one of the 1,512 weak amplitude-2 conditional injections. `TRIAL_RANKS.csv`
contains every trial. `SUMMARY.json` records the aggregate result, and
`QA_RECEIPT.json` records a separate saved-array recomputation of 21,189
values and aggregate checks.

Reproduction, after extracting the archive's
`rounding_followup/results/` directory:

```bash
python analysis/weak_truth_rank_20261014/analyze.py \
  EXTRACTED/rounding_followup/results \
  analysis/weak_truth_rank_20261014/results
python analysis/weak_truth_rank_20261014/qa.py \
  EXTRACTED/rounding_followup/results \
  analysis/weak_truth_rank_20261014
```

The proposed top-five retention rule is development-only and was selected
after this exposed diagnostic. It cannot qualify the current result and must
be frozen before any fresh validation. The accompanying morphology review is
descriptive visual inspection of the fourteen already saved waterfalls; it
adds no score or decision threshold.
