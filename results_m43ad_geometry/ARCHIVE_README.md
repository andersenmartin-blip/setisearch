# M43AD complete evidence archive

The 150 original `inputs/*.json.gz`, complete `result.json` and
`paired_signal_costs.json` are stored losslessly in the `archive/` directory.
The per-input files preserve source audits, original and centered signatures,
geometry selections, all ten policy decisions, exact historical replay,
native arithmetic checks and sampled aligned profiles.

```bash
python scripts/m43ad_archive.py restore
python scripts/m43ad_archive.py verify
```

The archive contains 152 original files. Their JSON text is packed into an XZ
stream of 6,351,780 bytes, with SHA256
`d6178d0604058c8edf526fb8d8df7cc9ddb8e9ab0f1b8495b2865cff499365c0`.
Base64 transport parts permit ordinary UTF-8 GitHub tree publication. Join
parts in manifest order and decode once to obtain the XZ stream. This encoding
does not change the original scientific files or seals.

`archive/manifest.json` records each part's size/hash, the XZ stream hash,
the original file and uncompressed text hashes, gzip header bytes and the
Python/zlib versions used for reconstruction. Packing and verification both
rebuild every original file and require byte-for-byte equality. Restoration
fails on any hash mismatch, including incompatible gzip output; it does not
replace an existing file with different contents.

Restore the original M43Z and M43AB ledgers before running the scientific audit:

```bash
python scripts/m43z_restore_ledger.py
python scripts/m43ab_archive.py restore
python scripts/m43ad_archive.py restore
PYTHONPATH=src:scripts python scripts/m43ad_audit.py
```

The smaller audit, progress, case summary, mechanism excerpts, logs, frozen
configuration, source code and readable report are stored directly in Git.
Original raw telescope files are not duplicated in this archive. Full native
re-execution additionally requires the source/anchor runtime described in the
completed continuation. No new observing sequence or null realization is
represented by this packaging.
