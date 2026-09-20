# LS8P audit serialization recovery

The LS8P scientific freeze is `cbee527850ef9d6bc392506cd958961321e0ec5f`.
The initial completed producer result is preserved at
`16824ada23afb9c8e66758d2a180a565326f443c` in `results_ls8p_residuals`.
All five contexts, 20 native product/convention cases, 160 held-block cases
and 320 signed controls were computed. Seventeen tests passed.

The independent auditor reconstructed all five contexts and reached its
output-writing loop, then raised `TypeError: Object of type int64 is not
JSON serializable`. Its pixel-coordinate sets contain NumPy integer scalars.
No audit verdict was serialized, so the preserved scientific status is
**COMPLETE_UNAUDITED**, and the workflow correctly reports failure.

This repair is restricted to converting the C0-only/C1-only boundary
coordinate scalars to Python `int` when the independent boundary function
returns them. The numbers, memberships and all scientific arithmetic remain
unchanged. The original auditor, producer, protocol, config, source inputs,
numerical tolerances and failed result directory remain untouched.

Before rerunning the audit, the adapter verifies pinned source files and
the complete initial result manifest, copies the required producer outputs
byte-for-byte to `results_ls8p_verified`, and records each copied checksum.
It does not run the producer again. It runs the original auditor with that
one representation adapter and a new output path, then invokes the original
reporter only after PASS. No new archive data, alternative scientific model,
coordinate choice or threshold change is introduced.

One regression test reproduces the exact NumPy-integer serialization failure,
proves the repaired structure is value-identical, and checks a JSON round
trip. The recovery workflow publishes either its success or failure with a
separate freeze identity, logs and checksum manifest. The initial failure
remains visible. After a passing complete audit and visual review, update
the project overview and close the bounded LS8P study as originally planned.
