# M43L — exhaustive wider integrated real scores pass

All **17,807,942,502 prescribed integrated score cells** match the independently
constructed factorized reference exactly. The complete 1,701-template bank now
spans every one of the 747,793 support carriers at widths 3,5,9,17,33,65,129 for
both first-epoch ON/OFF telescope sources at 1412.5 MHz. All 756 batches pass.

| Native width | Full-support vectors, both sources | Batches | Compared integrated cells | Reference |
| --- | --- | --- | --- | --- |
| 3 | 3,402 | 108 | 2,543,991,786 | Exact |
| 5 | 3,402 | 108 | 2,543,991,786 | Exact |
| 9 | 3,402 | 108 | 2,543,991,786 | Exact |
| 17 | 3,402 | 108 | 2,543,991,786 | Exact |
| 33 | 3,402 | 108 | 2,543,991,786 | Exact |
| 65 | 3,402 | 108 | 2,543,991,786 | Exact |
| 129 | 3,402 | 108 | 2,543,991,786 | Exact |
| **Seven-width total** | **23,814** | **756** | **17,807,942,502** | **Exact** |

Together with M43J's width-one result, the complete bank/carrier integrated
score domain is covered at **all eight widths** on these two sources:
**20,351,934,288 evaluated cells** across the two milestones. This is a numerical
qualification denominator, including correlated/repeated mappings and earlier
M43I overlap. It is not an independent-trial, candidate or sensitivity count.
Every vector includes 747,665 score carriers and 64 support guards on each side.

## Independent reference path and exact lineage

Each width worker rebuilds its own native reference from explicit indexed
normalized channel windows. Production's filter and sliding-window view are not
called by that reference. Its complete valid payload digest and every native
row digest must match M43K before integrated comparisons begin. The reference
stores absolute native channel positions, including NaN invalid guards, and
shares no array storage with the production cache, which uses a half-width offset.

The reference then calculates native coordinates directly and accumulates the
selected values in ascending integration order with the frozen float32 rule.
Every integrated cell is compared to the unchanged receipt-bound M43I gather.
This factorization reuses independently calculated native values rather than
materializing the same native windows anew for each score. Unit tests establish
agreement with the original direct-window oracle at every wider width and
multiple chunk sizes. Both paths share the formula, factors and NumPy runtime;
this is numerical cross-validation, not independent scientific replication.

Every source/cache identity reproduces M43I/K. Full vectors for templates 911 and
1678, recovered from the exhaustive batches, match M43I at each source/width.
All 14 complete source/width checkpoints include the exact ordered 54-batch
inventory, including the final five-template batch. The final audit checks their
seals, ranges, counts, parent identities and reference/overlap digests.

## Disclosed startup failure and public amendment

The initial freeze `65a7f25872074770530436179c8653d6e3e94b3b` failed before submitting any numerical
jobs: Python SyncManager could not create a local listening socket
(`PermissionError: Operation not permitted`). **Zero telescope sources were
loaded and zero M43L score cells were evaluated in that attempt.** Its original
configuration, traceback and sealed failure record remain published.

The public amendment replaced the manager with seven ordinary Python child
processes, lightweight parent coordinator threads, and a cooperative stop file.
It required no socket service, permission change or sandbox escalation. A real
seven-child preflight verified initial markers and stop-file visibility. The
arithmetic, bank, source inputs and 17,807,942,502-cell endpoint stayed unchanged.
The amended freeze `7b602792ad7bb14e8db0daa9700cc748324a6ee2` preceded the successful evaluation.
No subsequent numerical mismatch occurred. Workers would stop at the next batch
boundary after a peer error; partial checkpoints are never aggregate success.

All **76 M43-family tests pass**. Four M43L tests cover direct/factorized oracle
agreement, absolute native guards, full batch/retained-vector assembly, and
rejection of malformed inventories or deliberately incorrect reference outputs.
The ordinary-process preflight is additional runtime evidence, with no spectra.

## Reproduction and saved evidence

- Amended config SHA-256: `6c773140194378755d9058b49766351ac140b3277ce6980790c9ab1c22ea5959`.
- M43L sealed result: `31ceb977281fb03a7c4e1ca7dd2338e31432884e3f848e0e76de60832cacff58`.
- M43I result: `b2f9be7ed22848aaca3d0eab15a1535ee12a5643a06c47a593b15e31db72c41a`.
- M43J result: `3e9ef51c89d4b8d97a4223adb2bcdd3adc0cedbbac08fe3506a546949b098179`.
- M43K result: `dd4f1e66666f2e30e011f2efacf322fa62c324d919fcd6f3fc9fcd2a0b920127`.
- Fixed bank: `84524f7e129c0b414bde5004fe64bfb3ff94877357a7bb4dce399562d945d873`.
- Fixed factor table: `bc5c9e1f7a2db63074be30a946b2e1bd68963966f6c6b11cc5ad30f4e173edcd`.
- NumPy: `2.3.5`.

Source/width files were atomically checkpointed after every successful batch and
marked complete only after full coverage and ancestor-vector agreement. The final
result references all 14 completed checkpoint seals. It retains every batch digest
without publishing enormous score matrices. The manifest binds the delivered code,
protocols, failure/probe evidence, checkpoints, final report and logs. All seven
ON checkpoints were publicly saved while OFF evaluation continued, in commit
`c8526ac271118ac77f568cb5d0bffe062bf88ee4`.

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 .venv/bin/python -m unittest discover -s tests -p 'test_m43*.py'
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/m43l_runtime_probe.py
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/m43l_wider_integrated.py --work-root /path/to/m43h/live --freeze-commit 7b602792ad7bb14e8db0daa9700cc748324a6ee2
PYTHONPATH=src:scripts .venv/bin/python scripts/m43l_result_report.py
sha256sum -c RESULTS_MANIFEST_M43L_WIDER_INTEGRATED.sha256
```

Reproduction needs the two M43H native/normalized source directories or their
reconstruction with the retained receipt hashes. This runner recomputes on restart;
it does not accept arbitrary self-sealed files as authority to skip checks.
Checkpoint/source/reference/output digests must reproduce. Elapsed time and the
final enclosing result seal can differ; the manifest checks published artifact bytes.

## Runtime and next scientific gate

The successful seven-process job took **706.377 seconds** wall
time. This describes this qualification run, including independent reference work;
it is not calibrated detector throughput or a cloud-cost measurement. Seven
numerical subprocesses used the available eight-CPU quota and 20 GiB environment.
Each held one source/cache, one independent native reference and one 32-template
output. The existing 512 MiB adapter bound is per adapter and excludes reference,
caller, process and OS-cache memory; it is not a combined-job or measured RSS cap.
No new remote requests were needed. No AI agents or research delegation were used.

This closes the remaining wider integrated-score combinations for **one window
and the first ON/OFF epoch pair only**. It does not qualify other real epochs,
real multi-epoch stacking, detection thresholds or injection/recovery behavior.
The next gate is additional real epoch coverage and full stack/detection validation,
followed by newly frozen null and injection/recovery calibration. No candidates
were selected; numerical equality is neither an extraterrestrial finding nor a
scientific nondetection.
