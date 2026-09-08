# Complete M43Z case ledger

These three ordered byte segments preserve the complete original 352-case gzip
ledger exactly. Packaging is required because the publishing connection accepts
requests up to 16 MiB and the original gzip is 19,828,119 bytes. Direct Git push
is unavailable without GitHub command-line credentials. No record is omitted,
recompressed, resealed or numerically rerun.

After cloning the branch, run from the repository root:

```sh
python scripts/m43z_restore_ledger.py
sha256sum -c RESULTS_MANIFEST_M43Z_JOINT_CONTROLS.sha256
```

The helper verifies each segment and the reassembled original ledger against
index.json before writing. It refuses to overwrite a differing existing ledger.
Run it before the frozen audit or any postprocessing that reads the gzip path.
The final manifest includes the reconstructed original as well as these parts.
Scientific result seals, audit values and the original gzip SHA256 are unchanged.
