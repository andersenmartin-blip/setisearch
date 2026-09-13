# LS7I continuation

Integrated model study completed 2026-09-13.

LS7I completed **7,080 digital cases** on the two closed sectors: **6,720 historical cases plus a separately declared 360-case sector-32 shape supplement**. The primary rule fails **6/12 signal cells** and **2/60 control cells**. The joint development requirement is **FAIL**; the independent audit passes.

The fixed model does not satisfy the joint two-sector requirements. The independent arithmetic audit passes. This is a completed negative method result; no detector is adopted and no unused sector is opened.

[Full result and figure](results_ls7i_background/REPORT.md), [every signal loss](results_ls7i_background/SIGNAL_LOSSES.md), [independent audit](results_ls7i_background/AUDIT.json), [two-week result](TWO_WEEK_REPORT_2026-09-14.md).

## Next decision

Close this fixed ridge-prediction route. The next useful information would be an independently measured instrumental state: time-resolved image motion/centroid indicators and pixel variations outside the target aperture, together with a response model that preserves an injected stellar pulse. First establish whether those observables predict the remaining spatial contamination on these same closed contexts. A separately specified auxiliary-observable study is a proposed next project direction, not a hidden ridge, margin or template-bank retry. The present result alone does not establish that those extra observables will succeed.

The fixed protocol and all previous results remain closed. Do not rerun the model with changed parameters or open a new sector as an implicit repair. All files needed to reproduce the completed result are already published; no new FITS download is required.

## Verify or resume review

```sh
sha256sum -c LS7I_BACKGROUND_FREEZE.sha256
(cd results_ls7i_background && sha256sum -c SHA256SUMS)
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src python scripts/ls7i_review_background.py
```

A repeat audit writes AUDIT_RECHECK.json and preserves the sealed audit. Repeating the entire evaluation requires the source freeze or a separate output directory; the runner refuses to overwrite existing results.

Source freeze: `918797f2b33c1062a39c5360d2074700b075e17d`. [GitHub execution](https://github.com/andersenmartin-blip/setisearch/actions/runs/34766057139).

All M43 held-out panels remain untouched. No detector, candidate, physical laser limit or new observing coverage is claimed.
