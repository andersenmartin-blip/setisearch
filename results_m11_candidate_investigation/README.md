# Milestone 11 candidate-investigation evidence

These are labelled post-hoc diagnostics for the five formal survivors in
`results_m11/search_summary.json`. They do not alter the frozen v0.4.0 detector
or the preregistered Milestone 11 decision rule.

The investigation classifies all five survivors as `RFI_OR_INSTRUMENTAL`:

- candidates 1 and 2 have adjacent OFF receiver-frame coincidences;
- candidates 3 and 4 are two rest/template aliases of the same topocentric
  feature in both active epochs;
- candidate 5 appears on the same candidate track in the adjacent epoch-1 OFF
  scan at nearly the ON strength.

`candidate_investigation.json` is the authoritative structured result.
`scan_metrics.csv` is a flat view. Each candidate PNG contains all six ABACAD
waterfalls and the corresponding stationary spectrum. The archive JSON records
that no independent LHS 1140 cadence was exposed by the checked public index;
alternate `.0002` and `.8.0001` files belong to the same three observations.

Reproduce from public byte ranges with:

```bash
python scripts/m11_candidate_investigation.py --extract --workers 12
```

The successful evidence run was GitHub Actions run `32330549163`; all eight
detector unit tests remained green.
