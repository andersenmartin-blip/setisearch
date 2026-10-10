# Independent data availability check

Frozen receipt accounting and current local part sizes PASS. This review opened code/JSON and file metadata only; it did not recompute binary hashes, retrieve remote files, run restoration or science. Final interior waves and empirical QA are ongoing.

The new native170/172 RAW is durably saved as three ordered parts. Concatenate part01, part02, part03: **604,399,781 bytes**, SHA256 `b78521c9f51a47d698af1ea1f8949b5676c843656389655191042a0fbc06817f`, confirmed by the root assembly receipt. All three per-item save statuses succeeded. A single saved ZIP is **not** claimed; both failed single-file preparation attempts remain recorded.

| Part | Bytes | SHA256 |
|---|---:|---|
| 01 | 209,715,200 | `ad4be599d3e7da809df1d473c8fa677e0c2581d251fb65d9cc01d90849dd8dbb` |
| 02 | 209,715,200 | `2ad6609f4984c536fc4dbee2223975f756459d681b8c9e1f5c6b8731f149a97f` |
| 03 | 184,969,381 | `d585965102de3ac3cbc9864a92249e0fb660ed6968540249c34e650b880b15ca` |

Use `RAW_ARCHIVE_PARTS_PLAN.json` (SHA `764b48cffa38f72d41b870de4640f5e744339093297c94296b492fa790131a15`) and the reviewed `restore_raw_archive.py`. The immutable plan’s original planned status is preserved; later durability/restoration receipts supply completion.

Prior native171 RAW remains separate: `SETI_S2017_NATIVE171_RAW_2026-10-10.zip`, 466,351,822 bytes, SHA `6e08922aec5c5a6737987887cd62aab6d52495650297cae74745a654728f4786`. The new RAW contains 12 native170/172 H5 files and does not copy native171 H5.

The frozen reference scope, once all selected interiors complete, totals **766/768 cores = 99.73958333%** of this three-native triplet. Outer cores **native170 q0** and **native172 q255** remain excluded. This is reference-carrier coverage within one historical visit; it is not full S-band coverage or a sensitivity statement.

The accompanying JSON contains exact metadata receipts and scope pins. It makes no interior completion or final RESULTS delivery claim.
