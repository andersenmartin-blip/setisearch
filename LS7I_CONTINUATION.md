# LS7I continuation

Integrated model study completed 2026-09-13.

**Follow-on completed 14 September:** the proposed auxiliary-information study
is now [LS7J](LS7J_CONTINUATION.md). Its native correction requirements fail
while all pulse-protection checks pass. The current next information
requirement is documented in [LS7J_LIMITATIONS.md](LS7J_LIMITATIONS.md).
The LS7I outcome and reproduction instructions below remain historical.

LS7I completed **7,080 digital cases** on the two closed sectors: **6,720 historical cases plus a separately declared 360-case sector-32 shape supplement**. The primary rule fails **6/12 signal cells** and **2/60 control cells**. The joint development requirement is **FAIL**; the independent audit passes.

The fixed model does not satisfy the joint two-sector requirements. The independent arithmetic audit passes. This is a completed negative method result; no detector is adopted and no unused sector is opened.

[Full result and figure](results_ls7i_background/REPORT.md), [every signal loss](results_ls7i_background/SIGNAL_LOSSES.md), [independent audit](results_ls7i_background/AUDIT.json), [two-week result](TWO_WEEK_REPORT_2026-09-14.md).

The [completed limitation analysis](LS7I_LIMITATIONS.md) accounts for the
extra losses without new fits or cuts. Against LS7H on sector 29, all 165
additional losses first fail the source-score gate. Against LS7F on sector
32, 331 of 365 additional losses first fail source score and 34 fail nuisance
margin. This is first-failure accounting, not an exclusive causal attribution.
The median conditional/static covariance trace ratio is 1.063 on sector 29
and 6.233 on sector 32, while native energy ratios remain 1.008294 and 1.001058.
Pulse protection is exact; the new decision statistic is insufficient.

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

Audited result commit: `1cd89b896a46b666b9328a5db00c1720af341190`.
All workflow steps, including automatic publication, succeeded. The nineteen
published result-file hashes match the retrieved package; the comparison
figure has been visually checked.

The sealed `summary.json` retains its runner-stage `EVALUATED_AWAITING_AUDIT`
label. The subsequent `AUDIT.json`, complete workflow and published report
record the successful audit; that historical stage label is not a pending job.

All M43 held-out panels remain untouched. No detector, candidate, physical laser limit or new observing coverage is claimed.
