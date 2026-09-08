# Complete M43AB evidence

The human-readable result is `MILESTONE_43AB_ATTRIBUTION_RESULT.md` in the
repository root. `summary.json` exposes all signal/control counts and frozen
development gates without extracting the full evidence.

The complete 149 sealed input ledgers, full `result.json`, and
`paired_signal_costs.json` are stored losslessly in `archive/`. The archive
manifest lists each original file hash, the hash of every archive part, and the
hash of the assembled xz stream. Publication preserves the original JSON and
checks byte-identical reconstruction of every original gzip wrapper locally.

From the repository root:

```bash
python scripts/m43ab_archive.py restore
sha256sum -c RESULTS_MANIFEST_M43AB_ATTRIBUTION.sha256
PYTHONPATH=src:scripts python scripts/m43ab_audit_report.py
```

Restoration preserves existing matching files and refuses to overwrite any
different file. Compatible Python/zlib compression is required to reproduce
the original gzip bytes; the manifest records the exact versions. On a mismatch,
restoration stops rather than weakening a checksum or rewriting an original
result. The decompressed archive still contains every original JSON record.

Each input ledger contains the frozen input specification, original member
audit, all seven policy decisions, original and centered receiver signatures,
both alias products, ON/OFF agreement evidence, direct native checks and truth
associations. These are correlated development cases on one observing sequence,
not new astronomical candidates or independent false-alarm trials.
