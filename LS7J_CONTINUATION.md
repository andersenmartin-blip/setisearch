# LS7J continuation — audited FAIL

Completed 2026-09-14.

LS7J completed **420 fixed native windows and 9,480 digital response rows** on the same twenty closed-sector contexts. The combined motion/outside-aperture correction has joint feasibility **FAIL**; the independent audit passes. There are no new detector decisions or added observing days.

Close this fixed unit-gain motion plus protected-plane correction as a failed feasibility route. Use the saved component ratios and full-stamp mismatch responses to identify whether native prediction, source-wing protection or missing motion information limits it. Any next information study must address that measured limitation explicitly; no gain, profile, plane or threshold retry follows within LS7J. No unused sector or detector qualification follows from this result.

[Full result](results_ls7j_auxiliary/REPORT.md), [every failed response](results_ls7j_auxiliary/RESPONSE_FAILURES.md), [protocol](LS7J_AUXILIARY_PROTOCOL.md).

## Reproduce the fixed result

Install `requirements_ls7g.txt`; set `PYTHONPATH=src`, `OPENBLAS_NUM_THREADS=1` and `OMP_NUM_THREADS=1`. Run the evaluator into a new output path; it refuses to overwrite an existing result. The original two light-curve files are fetched and verified when missing from the cache.

```bash
python scripts/ls7j_auxiliary.py --cache data_ls7j_auxiliary --output /tmp/ls7j-reproduction
python scripts/ls7j_review_auxiliary.py --cache data_ls7j_auxiliary --output /tmp/ls7j-reproduction
```

A derived-only audit can omit `--cache`, but cannot replace the original raw-extraction audit. The committed result, source freeze, old baselines and historical ledgers stay unchanged. There is no unattended continuation scheduled between active sessions.
