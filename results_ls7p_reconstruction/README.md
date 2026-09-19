# LS7P reconstruction provenance and offline verification

The earlier original run and its claimed publication were not recovered.
The retained 15 September reconstruction follows the existing public source
freeze. Its 50 input files and 16 original result files are preserved unchanged
in `results_ls7p_inputs/` and `results_ls7p_response/`; new explanatory READMEs
and the result report are additional files. `search_record.json` preserves
the earlier bounded search and the explicit reconstruction decision.

The present fresh offline verification checks the retained reconstruction,
not the identity of the missing original. `verification.json` records the
actual execution timestamps, pinned environment, source/driver hashes, all
16 reproduced output hashes, seven passed known-answer tests and the separate
1,496,872-comparison audit. The original response `audit.json` is itself one
of the 16 byte-identical files. `evaluation.log`, `audit.log` and
`known_answers.log` are console logs from this fresh verification.

`frozen_source_inventory.json` binds 695 locally available source and
prerequisite files to their Git identities in the complete public freeze
tree. It is a verified subset of that tree, not a claim that the complete
repository was downloaded. `release_inventory.json` binds the exact new and
updated release payload; it excludes itself to avoid self-reference.

## Reproduce

Use Python 3.12.14 and `requirements_ls7g.txt` from the public source freeze
(NumPy 2.3.5, SciPy 1.17.0, Astropy 7.0.2, Matplotlib 3.10.8). Check out
`f42aa216b25779d55cd1fabd25545d3277abcfa5` in a separate directory and restore
the files named in `frozen_source_inventory.json` from that commit. Copy the
50 original input files and 16 original response files from this release into
that source checkout; omit the newly added input README and response report
when reproducing the exact file-count check. Their exact membership is listed
in `retained_result_inventory.json` (66 files in total).

Run the new verification driver from the release, keeping the frozen checkout
and a new empty verification directory separate:

```sh
python /path/to/release/scripts/ls7p_verify_reconstruction.py \
  --source-root /path/to/frozen-source \
  --verification-root /path/to/new-verification \
  --source-inventory /path/to/release/results_ls7p_reconstruction/frozen_source_inventory.json
```

The driver requires HEAD at the freeze, verifies every listed source hash,
runs the frozen seven analytical tests, then executes the unchanged producer
and independent auditor with only their `OUT` directory rebound. It compares
all 16 result files byte-for-byte and checks that the retained inputs/outputs
did not change. It calls no acquisition function. It refuses an existing
verification destination. Source/input verification occurs before evaluating
the reconstructed outputs.

This release adds no target correction, new native trial, pulse recovery,
candidate or qualified observing time. [Full interpretation](../results_ls7p_response/REPORT.md).
