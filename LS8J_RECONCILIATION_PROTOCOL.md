# LS8J — full-inventory reconciliation before science access

Status: **FROZEN BEFORE REQUERY; SCIENCE VALUES CLOSED**.

The selection at `81692343a774b19d26c28dd9596ad1dd1a31ef01` retained
1,000 chronological public archive rows, 452 eligible visit summaries and
107 ranked cohorts. It selected the first two eligible WASP-189 visits:
`CH_PR100041_TG000201_V0300` and `CH_PR100041_TG000202_V0300`.

An independent offline census audit reproduces the selection and every cohort
ranking, with 17,000 field/decision comparisons. However, the producer discarded
the full product-browser responses and retained only derived flags. This does
not meet the original protocol's full-inventory retention requirement. The
original metadata run is historically incomplete in that respect.

This reconciliation preserves every original byte. It is a new, separately
dated metadata acquisition, not recovery of those discarded responses.

1. Pin the published census and selection to their Git blob identities and
   verify the entire original SHA256SUMS manifest.
2. Independently rebuild basic eligibility, all visit decisions, cohort order
   and selected pair from the saved census and product summaries.
3. Requery the exact 452 previously basic-eligible file keys with the public
   DACE product browser. Save each complete returned column dictionary, query
   key, acquisition time and hash. No new census or other visit is allowed.
4. Independently derive each product summary from the retained fresh response.
   Compare all summary fields with the original. Preserve all mismatches.
5. Rebuild the complete visit ledger and 107-cohort ranking. PASS requires
   identical summaries and identical complete rankings, including the selected
   target and two visits. A missing response, changed summary or changed order
   blocks subsequent science access; do not select a substitute.

Only query_database/browse-style metadata already allowed by LS8J is in scope;
the executable makes only `browse_products` calls. Product download calls,
science bytes, FITS table rows, light-curve values and image pixels remain zero.
Do not infer that the original discarded inventories are thereby recovered.

After PASS is public, freeze a header-only preflight for the unchanged pair.
Opening science-table values requires a subsequent exact-range screen freeze.
The historical raw-imagette, TESS and M43 boundaries remain unchanged.
