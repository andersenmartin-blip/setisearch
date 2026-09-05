# LS4F v1: resource abort

Status: **ABORTED — NO SCIENTIFIC CONCLUSION**.

The frozen v1 run stopped during the A1 download with `No space left on device`, after its last progress receipt reported at least 6,979,321,856 bytes. No full source digest was verified, no native spectral values were evaluated, and neither source completed.

The initial filesystem check reported approximately 28 GB free. After failure, the runtime directory contained 28 temporary files totalling 23,767,285,760 bytes, including additional copies beyond the primary transfer. These extra copies explain the actual disk pressure; their creation was external to the downloader's one-part-file strategy. All files in this task-owned raw-data directory were then removed, restoring approximately 28.8 GB free.

The original freeze and abort receipts remain unchanged. A separate v2 resource amendment relocates disposable raw downloads to a unique directory under `/tmp`, outside the workspace being synchronized. The source inventory, hashes, per-source size check, method, thresholds and 4 GB free-headroom requirement are unchanged. It is a new execution; its transfer budget does not conceal the additional bytes spent in v1.

See `results_ls4f_reanalysis/abort.json`, `abort_context.json` and `runtime_context.json`.
