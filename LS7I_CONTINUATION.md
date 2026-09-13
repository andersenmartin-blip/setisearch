# LS7I continuation

Input preparation completed, 13 September 2026.

The two-week plan has started. Both closed TESS sectors now have verified individual-cadence inputs. All **6,720 historical trial recipes** and **300 training vectors** reproduce from **20 background contexts**. The independent sector-32 FITS restoration check passes exactly; sector 29 reuses its sealed LS7G cutouts. This completes input preparation, not evaluation of the new model.

Next implement and freeze the integrated time-dependent background/residual study from [the two-week plan](TWO_WEEK_PLAN_2026-09-14.md). Keep both closed sectors in the joint evaluation. Sector 32 lacks the 360 historical cross/ring/triangle cases present in sector 29; declare any supplement separately before its evaluation. The input freeze does not specify or approve a new detector rule. Preserve LS7G/LS7H outcomes and the original denominators.

Use `results_ls7i_inputs/datasets.json` as the entry point. Each dataset records its context path and source-ledger hash. The common recipes are truth-labelled evaluation data; do not pass their labels, amplitudes or known native realization into inference. Both sectors retain their original 18/21-pixel apertures and ten contexts. No further FITS download is needed for model development.

[Input report and exact interface](results_ls7i_inputs/REPORT.md), [independent audit](results_ls7i_inputs/AUDIT.json), [restoration protocol](LS7I_INPUT_PROTOCOL.md).

```sh
sha256sum -c LS7I_INPUT_FREEZE.sha256
(cd results_ls7i_inputs && sha256sum -c SHA256SUMS)
OPENBLAS_NUM_THREADS=1 python scripts/ls7i_review_inputs.py
```

The derived-only audit command above does not overwrite the sealed raw-FITS audit. To repeat the complete raw-source audit, use the protocol with its original input files in a cache. Original spatial-fit audits are reused by hash; no detector challenge is rerun here.

Published input freeze: `44040ac87de1fab261191dd19f7f3ebd2d04e073`. [Complete GitHub job](https://github.com/andersenmartin-blip/setisearch/actions/runs/34763103507). The model stage remains pending. PROJECT_STATUS.md is the maintained operational entry point.

The complete input package is published at
`b5d456d9142c49f291c1eaafeb246048d6d1f89b`. Its output checksums and both
context/ledger identities match after retrieval. The maintained two-week
plan records the first block as completed. Continue directly with the model
implementation and its separately frozen evaluation; do not rerun restoration
or rename successful input verification as a detector qualification.
