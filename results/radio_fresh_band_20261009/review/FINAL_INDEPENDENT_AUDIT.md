# Independent retained-output audit — fresh native band 151

**PASS.** The acquisition, stationary family, sparse drift family and 18 fixed ON-origin profile cases are complete. All 168 scientific binary artifact hashes agree with their saved receipts. No analysis was rerun and no telescope HTTP or numerical HDF5/NPZ access occurred in this audit.

| Phase | Completeness checked | Process CPU seconds | Peak RSS bytes |
|---|---|---:|---:|
| Acquisition |96 unique exact-range receipts; six compact files; 96 row hashes|3.436158|132395008|
| Stationary |Six complete 1,048,010-carrier directions; 120 rank descriptions; 12 maps/spectra|7.752783|805277696|
| Sparse drift |Three ON scans × 32 cores; 96 maps; 131,072 carriers per ON; 763 drifts × two widths|250.094773|313425920|
| Fixed profiles |18 cases; 108 scan profiles; 1,728 row occurrences; 18 patches; 36 figures|21.603361|525524992|

All declared code/source/acquisition/input-rank/normalization pins match. Every saved fixed-track center was independently checked against the frozen metadata and original selected frequency/drift; all ±64-channel patches remain in bounds. Source-range identities, complete row receipts, rank ordering/suppression, reciprocal adjacency and sparse core geometry pass.

New received telescope application bodies total 305,137,622 bytes. The cumulative same-cadence total is 611,429,683 bytes; conservative charged upper bound is 611,429,779 bytes including 96 one-byte guards. Both the 400 MiB activity ceiling and 2 GiB cadence ceiling pass. Measured science-process CPU components sum to 282.887074009 seconds; they are components, not a measurement of whole-activity or historical total. The 750-second reservation remains charged without refund.

This is new frequency coverage within the same 2016 visit. The drift search covers 32 separated cores rather than the whole chunk. The selected profiles and row counts are dependent post-selection descriptions. A/B remains FAIL_CLOSED; no qualified sky pilot, detection, OFF veto, sensitivity, false-alarm probability or flux result follows. The previous seven unresolved cases and old holdouts remain unchanged.

Binary identity and metadata contracts passed. PNG rendering review remains separate; this audit does not independently rederive numerical scores. Whole-source MD5 is unverified. HTTP status/effective-URL checks were enforced by the frozen reader; receipts retain the checked headers and completed-status marker. Application-body accounting excludes wire/header traffic and separately restored dependency/cache bytes.

Component details are in `ACQUISITION_FINAL_AUDIT.json`, `STATIONARY_FINAL_AUDIT.json`, `DRIFT_FINAL_AUDIT.json` and `PROFILES_FINAL_AUDIT.json`; their hashes are pinned in `FINAL_INDEPENDENT_AUDIT.json`.
