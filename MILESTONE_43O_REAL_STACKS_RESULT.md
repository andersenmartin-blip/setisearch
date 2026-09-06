# M43O — real three-epoch sum and active-cut checks pass

The unchanged sum stack now passes exhaustive comparison on the six verified
telescope sources at **1412.5 MHz**, ordered as three ON and three OFF scans.
For every one of **1,701 templates × 747,793 support carriers × eight widths**,
all four activity subsets pass both declared endpoints:

- **81,407,737,152 raw sum-stack cells**, with no minimum-active cut.
- **81,407,737,152 active-cut cells**, requiring every selected epoch to be >=3.

Together, **162,815,474,304 stack comparisons** pass across **16 kind/width
products, 864 template batches and 6,912 batch/rule records**. All raw outputs
are finite and match, so agreement cannot be explained merely by both paths
rejecting the same cells. Before stacking, every replayed per-epoch batch
reproduces its retained M43J/L/N score digest: **61,055,802,864 replayed cells**.
Those replays repeat earlier numerical work and are not independent trials.

| Native width | Raw cells, ON + OFF | Active-cut cells, ON + OFF | Finite active-cut ON cells | Finite active-cut OFF cells | Comparison |
| --- | --- | --- | --- | --- | --- |
| 1 | 10,175,967,144 | 10,175,967,144 | 32,639 | 32,709 | Exact |
| 3 | 10,175,967,144 | 10,175,967,144 | 63,958 | 64,631 | Exact |
| 5 | 10,175,967,144 | 10,175,967,144 | 117,540 | 118,372 | Exact |
| 9 | 10,175,967,144 | 10,175,967,144 | 344,527 | 350,123 | Exact |
| 17 | 10,175,967,144 | 10,175,967,144 | 1,653,856 | 1,685,633 | Exact |
| 33 | 10,175,967,144 | 10,175,967,144 | 9,359,067 | 9,350,453 | Exact |
| 65 | 10,175,967,144 | 10,175,967,144 | 38,525,751 | 37,334,544 | Exact |
| 129 | 10,175,967,144 | 10,175,967,144 | 105,819,966 | 104,983,007 | Exact |

Finite active-cut counts are numerical diagnostics. They include correlated
carriers/templates and four overlapping activity subsets, and have no candidate,
event-rate, false-alarm or discovery interpretation. No candidate selection,
exclusion masks, OFF veto or calibrated detection threshold is applied here.
The >=3 requirement is the existing M43G active rule, not a newly calibrated
search threshold. Raw uncut sums are an additional arithmetic diagnostic.

## Scope and implementation

The four subsets are **(0,1), (0,2), (1,2), (0,1,2)** in chronological order.
ON and OFF are never mixed. The three epochs are repeated scans in one
observing sequence, not independent observing dates. Every support grid includes
747,665 score carriers plus 64 guards on each side.

Production source loading, native filtering and gather use unchanged M43I code;
stacking calls unchanged `stack_hypothesis` with `stack_statistic='sum'` and
`exclusion_mask=None`. The reference independently accumulates each selected
epoch in float32, divides by float32 sqrt(active count), and accumulates the
per-epoch >=3 conditions. Both finite results and rejected -infinity values must
agree exactly in dtype and value. The implementations share the intended formula,
input scores and NumPy runtime; this is numerical cross-validation.

Each job loads three receipt-bound sources/caches. The ordered scan labels,
source/cache identities and exact prior batch hashes are checked before the
score arrays may enter the stack. All six source identities reproduce again in
the final audit. The fixed factor table, bank, support grid, ancestor artifacts,
code and source trust anchors are bound by **123 pinned files**.
The final audit checks all 16 complete product seals, the exact chronological
source inventory, all 54 batches per product, all eight rules per batch,
parent score hashes, cell counts and finite-output bounds.

## Execution and checkpoint format

The public freeze `f69a431629ebdd66a3bcf6b0b019d5779952062b` preceded telescope score evaluation.
No new telescope data requests or downloads were made. At most seven ordinary numerical
subprocesses ran concurrently, scheduled in descending width and ON/OFF order.
They used the tested cooperative file stop mechanism; no AI agents or delegation.
The successful run took **1798.238 seconds** wall time, including
source verification, cache building, score replay and stack comparisons. This
is not calibrated detector throughput or a measured combined memory cap.

Each batch holds three 32-template full-support score arrays, then compares
stacks in 4,096-carrier chunks. Chunk temporaries preserve the epoch, template
and carrier axes before flattening only the final two for the production call.
The last template batch contains five templates. Source and cache arrays remain
bound to their independently retained receipt/ancestor identities.

Every completed batch is sealed atomically, with its three parent score hashes
and eight result records. Stack digests hash a **chunk-major stream**: carrier
chunks in increasing order, and template-major float32 bytes within each chunk.
They are not full template-major vector hashes; the frozen chunk size is part
of their reproducibility contract. Finite counts are retained without storing
large stack matrices. Completed products were checkpointed locally. Automatic approval review
blocked publication of the first three complete M43O products, stating that
the standing continuation request did not specifically authorize this new
public disclosure. No completed M43O product was public during the run;
the protocol/code freeze was public before evaluation. This deviates from
the planned during-run public checkpoint schedule, not from numerical scope
or acceptance rules. Public upload was deferred for separate approval; the block and
local checkpoint history are retained in MILESTONE_43O_PUBLICATION_BLOCK.md.
No numerical run failure occurred. A failure would stop peers at the next batch boundary,
retain incomplete checkpoints and prevent an aggregate success result.

All **85 M43-family tests pass**. Four new tests cover scalar agreement at and
immediately below/above the active boundary, all subsets and both modes, multiple
chunk sizes, deliberate output corruption, swapped epochs, mixed ON/OFF,
changed payloads/dtypes and invalid rules/chunks. The seven-child runtime probe
is additional no-spectra evidence. The artifact manifest binds the delivered
protocol, code, test/probe evidence, complete checkpoints, run log and report.

## Reproduction and next gate

- Configuration SHA-256: `229f6d14b1bc9f0dadae4f60b652a97b2a4825448bb6a4d1b1c17a33776b6574`.
- Sealed result: `7e96a1bec7f95c625812e34a89da3832f9ff4a6e0a5dd1761106b32b9c6c7590`.
- Bank SHA-256: `84524f7e129c0b414bde5004fe64bfb3ff94877357a7bb4dce399562d945d873`.
- Factor table SHA-256: `bc5c9e1f7a2db63074be30a946b2e1bd68963966f6c6b11cc5ad30f4e173edcd`.
- Support grid SHA-256: `18739188d199ffeaf1854911efc590c2cb2c5a0817704ed7f9f9bb86358c6429`.
- NumPy: `2.3.5`.

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/m43o_real_stacks.py --work-root /path/to/m43h_work/live --freeze-commit f69a431629ebdd66a3bcf6b0b019d5779952062b
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/m43o_result_report.py --work-root /path/to/m43h_work/live
sha256sum -c RESULTS_MANIFEST_M43O_REAL_STACKS.sha256
```

Reproduction needs all six M43H/M source directories and the pinned parent
checkpoints. Reruns recompute rather than trusting self-sealed files as authority
to skip evaluation. Numerical digests must reproduce; elapsed time and enclosing
result seals can differ. The manifest checks the exact published artifact bytes.

This closes the real-data **sum arithmetic and active-cut** endpoint only.
Exclusion-mask construction, event association, OFF vetoes and scramble/detection
logic remain to be qualified, followed by separately frozen null and injection/
recovery calibration. M43O establishes neither a candidate nor a scientific
nondetection and does not qualify the detector as a whole.
