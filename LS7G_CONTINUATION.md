# LS7G continuation

13 September 2026.

LS7G completed **3,540 fixed transfer trials** on the ten already closed sector-29 backgrounds. The primary joint descriptive gate **fails**. Nominal recovery at the fixed margin −1 is **37/40, 40/40, 40/40**; displaced recovery is **135/160, 153/160, 158/160**. **4/30** instrumental control cells exceed their allowance. The independent audit passes; no detector is adopted and no candidate is promoted.

Next, diagnose the failed transfer cells from the saved sector-29 extracts, keeping the frozen LS7G rule and outcomes unchanged. Separate temporal, source-score, residual and nuisance-separation losses before proposing another model or observing sector.

The margin −1 was chosen from LS7F sector-32 development before this run. It permits a nuisance model to fit better; 21 accepted primary rows do so. Sector 29 was already inspected in earlier work. This is not independent validation or source identification.

[Read the complete report and figure](results_ls7g_transfer/REPORT.md). The backgrounds, models, training vectors and every trial are public; raw FITS downloads are unnecessary for the independent audit.

```sh
sha256sum -c LS7G_FREEZE.sha256
(cd results_ls7g_transfer && sha256sum -c SHA256SUMS)
OPENBLAS_NUM_THREADS=1 python scripts/ls7g_review.py
```

Source freeze: `4ca4d558a79d72ceec45a9ab482820b92dd45512`. All historical LS7B/LS7C/LS7E/LS7F results remain unchanged, and the original M43 held-out panels remain unopened. The canonical status is PROJECT_STATUS.md.
