Close C005 with all five records still U. The next bounded continuation is the entire C006 group on HD106515A, fixed from original ACTION_QUEUE row 5 before the C005 results. C006 contains both resolution neighborhoods R006 and R007; keep them together rather than following numerical group order or selecting a favorable correlation.

| Original queue row | Candidate | Resolution group | Discovery product | Catalog barycentric-air center (Å) |
|---:|---|---|---|---:|
| 5 | V2E2-0025 | R007 | ADP.2022-01-06T01:08:04.689 | 4310.5850 |
| 12 | V2E2-0042 | R006 | ADP.2023-01-01T01:10:52.479 | 4310.3050 |
| 13 | V2E2-0043 | R007 | ADP.2023-01-01T01:10:52.479 | 4310.6050 |

All three records remain U. They represent only two distinct discovery exposures: 0042 and 0043 share the same 2022-12-31 observation/product. Keep all three event identities and original raw cutouts, but use two unique discovery-product references in any shared-frame comparison. Do not count the repeated product or overlapping raw pixels as independent observations. The centers span 0.3000 Å, approximately eight nominal resolution elements; core-overlap grouping does not imply one physical line or emitter.

The same seven existing cohort epochs are available, with observation dates, BERV and exposure times fixed in NEXT_GROUP_METADATA.json. Their BERV range remains −29.2347518620376 to +30.3750612537025 km/s, span 59.6098131157401 km/s. The two discovery products themselves are close in BERV (30.1380355615464 and30.3750612537025 km/s); discrimination must not be inferred from that near-matched pair alone. The other five existing epochs supply the wider coordinate context. C006 at 4310.305–4310.605 Å is entirely outside C005's window, while the exposure products are shared.

One useful next action is a separately frozen joint context for this complete neighboring-feature group. Inventory the exact seven saved merged products, the two unique discovery native products and every historical event-specific raw panel before inspecting new windows. Existing adjudication describes order 19 broad/native and trace-associated enhancements, including a separate off-trace feature for 0042. Preserve the separate 0025/0042/0043 mappings and all earlier qualifications. Verify covering-order identity, wavelength support and units from metadata afresh; do not transfer C005's two-order/full-window outcome.

A metadata-derived starting geometry is midpoint 4310.455 Å with the union of the three original ±0.25 Å cores, halfwidth 0.400 Å, and a fixed ±3 Å surrounding window. Preserve both R006/R007 feature locations in the displays. Freeze the exact grid, comparison regions, unique references, first-discovery frame anchor and quality/coverage gates before opening arrays. A correlation of the joint window must not be presented as separate proof for each of its neighboring features. Keep signed flux, fixed two-sided reference normalization and any missing/low support; the fixed topocentric anchor may sample other structure when barycentric features move outside its core.

This is one future group context, not a new acquisition or an extension of the completed fits. Do not replay C001/C003/C005, the mapping diagnostics or the original epoch pipeline. Do not add free width/lag/center/RV fitting, choose extra favorable epochs, merge record identities, or assign origin from broad shape agreement. The fixed-template widths remain unmeasured physical widths. After the bounded C006 result, preserve its limitations and return to original queue order.

Pre-result metadata binding (SHA-256):

- `scientific_review/NEXT_GROUP_METADATA.json`: `b1f5272ead302b94779d95d7339d738c4a770ac0fac9b680ca426e7de2d5a85f`
- `work_harps_20261101/v2/extension02/unresolved_context_20261102/ACTION_QUEUE.csv`: `d789d5ad03963cfe68c0e8d70d0e7e7c199599fb36a2ff2760426e8e69f7267b`
- `work_harps_20261101/v2/extension02/unresolved_context_20261102/EVENT_CONTEXT.csv`: `2d8129e7963e2678035cf4b915c3c3503529b399d61fe6e8233484d0ee2321d7`
- `work_harps_20261101/v2/extension02/unresolved_context_20261102/CORE_OVERLAP_GROUPS.csv`: `39cbcc225161abfb8a986fec91583dd3591806d589c7154171fb80d026b305ab`
- `work_harps_20261101/v2/extension02/epoch_followup/ALL_EPOCH_MEASUREMENTS.csv`: `de5b7175959ce7d25aec435d68def4b4e5d471292fd9de19c62ed17567b3f649`
- `work_harps_20261101/v2/CURRENT_V2_DISPOSITIONS.csv`: `f2bbb73b08ae7dc60b9387495a05d1d6e98ece7571eff9a979ae0b1af139a279`
