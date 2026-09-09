# Reconstruct the M43AE evidence

The archive contains all 262 sealed input records, the complete result and
416 signal-only/mixed policy comparisons: 264 original files. The manifest
records both compressed-file and uncompressed-text SHA256 identities. Text
records are compressed together with XZ, then transported as ordered base64
parts. Every original gzip header is retained. Reconstruction must match every
original byte; it fails if the installed zlib produces different gzip output.
Use the Python and zlib versions recorded in `archive/manifest.json`.

From the scientific branch, restore dependencies and the new evidence:

```bash
PYTHONPATH=src:scripts python scripts/m43z_restore_ledger.py
PYTHONPATH=src:scripts python scripts/m43ab_archive.py restore
PYTHONPATH=src:scripts python scripts/m43ad_archive.py restore
PYTHONPATH=src:scripts python scripts/m43ae_archive.py restore
PYTHONPATH=src:scripts python scripts/m43ae_audit.py
```

The first three commands recover existing ledgers. They do not rerun the old
experiments. The M43AE audit reads the sealed scientific evidence and does not
require the large native runtime. It independently checks profile coordinates,
interpolation, correlations, center amplitudes, evidence links, direct-check
inventories, decisions, associations, panel counts and gates.

```bash
PYTHONPATH=src:scripts python scripts/m43ae_archive.py verify
```

This last command reconstructs all original bytes in memory one record at a
time and verifies existing local files without writing missing ones. It checks
every transport-part hash and the combined XZ archive hash first.

For a new native execution, the six original closed source identities, all
96 anchor arrays, all 48 native gathers, dependency versions and public freeze
receipt must match. Consult `MILESTONE_43AE_JOINT_RESPONSE_PLAN.md` and the
completed continuation. Do not replace a completed result or create new null
rows merely to reconstruct the published evidence.
