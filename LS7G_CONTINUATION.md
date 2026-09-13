# LS7G continuation

13 September 2026.

LS7G completed **3,540 fixed transfer trials** on the ten already closed sector-29 backgrounds. The primary joint descriptive gate **fails**. Nominal recovery at the fixed margin −1 is **37/40, 40/40, 40/40**; displaced recovery is **135/160, 153/160, 158/160**. **4/30** instrumental control cells exceed their allowance. The independent audit passes; no detector is adopted and no candidate is promoted.

All six primary signal-recovery cells pass, as do strength matching, fixed
10% recovery, base nulls, confounding and bounded-pointing checks. The immediate
limitation is these four control cells:

| Control | Target score | Accepted / trials | Allowed |
|---|---:|---:|---:|
| 2x2 block | 8.5 | 4/40 | 2/40 |
| 3x3 cross | 8.5 | 8/40 | 2/40 |
| 3x3 triangle | 8.5 | 9/40 | 2/40 |
| 3x3 triangle | 12 | 3/40 | 2/40 |

Next, diagnose these weak/medium morphology confusions using the saved
backgrounds, patterns, model matrices and trial vectors. Account for the
stellar pulses lost by any proposed change. Keep the LS7G rule and outcomes
closed; do not rerun its completed challenge, add a threshold sweep or open
another sector as an undocumented repair.

Result publication: `05fdbf457835df23ed67cced26666dad6ded2cf7`.
The [complete GitHub run](https://github.com/andersenmartin-blip/setisearch/actions/runs/34754959873)
passed acquisition, computation and independent auditing, then published the
result. Source and result checksums reproduce after retrieval; the figure is
visually checked. No raw FITS recovery is needed for continuation.

The margin −1 was chosen from LS7F sector-32 development before this run. It permits a nuisance model to fit better; 21 accepted primary rows do so. Sector 29 was already inspected in earlier work. This is not independent validation or source identification.

[Read the complete report and figure](results_ls7g_transfer/REPORT.md). The backgrounds, models, training vectors and every trial are public; raw FITS downloads are unnecessary for the independent audit.

```sh
sha256sum -c LS7G_FREEZE.sha256
(cd results_ls7g_transfer && sha256sum -c SHA256SUMS)
OPENBLAS_NUM_THREADS=1 python scripts/ls7g_review.py
```

Source freeze: `4ca4d558a79d72ceec45a9ab482820b92dd45512`. All historical LS7B/LS7C/LS7E/LS7F results remain unchanged, and the original M43 held-out panels remain unopened. The canonical status is PROJECT_STATUS.md.
