# Extension02 bounded raw/native follow-up — preparation only

The prospective selection rule was frozen in PLAN.json before this agent read extension02 accepted-hit contents. The completed production has 100 analyzed exposures, six V1E2 events and 336 V2E2 events. This follow-up selects eight exposures, covers all six V1E2 events and 59 V2E2 events, and adds no new observing exposure to the survey totals. It is an initial raw-review subset, not complete triage of extension02.

Selection is by frozen MAIN100 order within two tiers: first exposures bearing V1E2 accepted events, then remaining V2-bearing exposures. No score, wavelength, morphology, target preference or product availability changes that order.

| Selected rank | MAIN100 index | Target | Tier | V1 events | V2 events |
|---:|---:|---|---|---:|---:|
| 1 | 14 | HD109833 | V1 priority | 1 | 6 |
| 2 | 33 | HD114386 | V1 priority | 1 | 5 |
| 3 | 38 | HD114783 | V1 priority | 1 | 5 |
| 4 | 51 | HD120411 | V1 priority | 1 | 13 |
| 5 | 53 | HD120411 | V1 priority | 1 | 15 |
| 6 | 55 | HD120411 | V1 priority | 1 | 5 |
| 7 | 1 | HD103991 | V2 fill | 0 | 4 |
| 8 | 2 | HD103991 | V2 fill | 0 | 6 |

All 16 product identities and advertised lengths were checked by HEAD requests. No response body was read. The planned eight raw plus eight ancillary files total 210,108,924 bytes, below the fixed 350,000,000-byte returned-payload cap. No selected exposure was omitted or replaced. Acquisition is limited to three workers and two attempts per product; bytes from failed/retried transfers count toward the cap. A shared reservation ledger bounds concurrent reads. After independent preflight review, failed reads conservatively consume their full reserved allowance, including unknown progress; known-returned bytes and charged bytes are reported separately. HTTP redirects are rejected before response-body draining, and rejected HTTPError streams are closed without reading. Completed products require archive/date/container checks plus exact native raw-parent basename, HARPS instrument, normalized source target and BERV checks before becoming usable; partial products are deleted and never passed to extraction.

FOLLOWUP_FREEZE.json pins the selection, code, metadata and production-input hashes. Download remains blocked until the root agent publishes and independently verifies this exact package, then supplies the full commit and freeze SHA256 to acquire.py. This is an internal publication requirement from the assigned workflow, not a request for further user permission. prepare_selection.py is one-shot and must not silently replace an existing freeze. acquire.py also refuses implicit restarts or existing product replacement.

The native extraction code reuses byte-identical registration.py and local_registration.py from triage_batch02: six fixed reference orders, four fixed windows, candidate exclusions, eight coordinate conventions, and the original global/local usability rules. Every accepted event in selected exposures is retained, including duplicate V1/V2 selections of the same physical feature. All overlapping native orders are examined. V1 mapping centers use the accepted peak; V2 centers use the accepted fitted center. Every event is accounted for when a product pair is missing or an order is edge-truncated. Raw/header fiber-B context is retained; B presence alone does not imply a sky control. The extraction itself does not assign origins. The inherited local_mapping_usable flag gates the two local spatial offsets only; it does not threshold local correlations. Those correlations remain descriptive. This is the original baseline, not the stronger later mapping43 post-hoc gate.

Any wider raw inspection or revised mapping beyond this baseline requires a separately documented post-hoc plan. All extension02 inputs and production outputs remain immutable; only this new follow-up directory is written.

Prepared scripts and guard checks:

- prepare_selection.py: completed-input/provenance checks, deterministic selection, metadata-only HEAD checks, jobs and freeze.
- acquire.py: publication gate, bounded downloads, payload ledger and raw/native identity checks.
- extract_native.py: fixed native/raw context for all 65 selected event records, with no classification.
- common.py, registration.py, local_registration.py: integrity and unchanged mapping helpers.
- transfer_guards.py and test_transfer_guards.py: import-safe transport/budget guards and11 offline tests, including receipt construction from all16 actual frozen jobs.

The initial unpublished code/freeze remains in attempts/prepublication_v1/. PREPUBLICATION_AMENDMENT.json explains the pre-download corrections; the selected8 exposures and all HEAD metadata remain unchanged. No science payload was requested during guard testing. The first redirect test harness bypassed the opener fallback chain; its failure is preserved, and the corrected test exercises that actual error-dispatch chain.

Execution after root publication verification:

```sh
python v2/extension02/raw_followup/acquire.py --published-commit VERIFIED_COMMIT --published-freeze-sha256 VERIFIED_SHA256
python v2/extension02/raw_followup/extract_native.py
```

Actual products, raw inspections and provisional morphology results do not yet exist at preparation time. Source spectra and event catalogs remain unaltered.
