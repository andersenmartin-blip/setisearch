# M43AI original native records

This lossless archive contains all 240 original sealed JSON records from the
completed prospective native challenge: 128 null inputs and 112 injection/control
cases. The fixed model failed the zero-control requirement. See the
[complete result](../MILESTONE_43AI_NATIVE_VALIDATION_RESULT.md).

The 31 base64 parts encode an XZ-compressed JSONL transport. Each row contains
the original relative path and the exact UTF-8 file contents. Serialization
does not round or recompute any measured value. `manifest.json` binds the
transport and every original file by size and SHA256.

From the science checkout, restore the records with Python 3.12:

```bash
python scripts/m43ai_archive.py restore --root . --archive results_m43ai_native_archive
```

The restorer checks every part, compressed stream, transport row and original
file before writing. Existing differing records are preserved by an error.
It then writes the original `results_m43ai_native_validation/records/*.json`
paths expected by the complete inventory and audit. No telescope acquisition
or detector rerun is needed.

With the recorded study dependencies available, audit the restored records:

```bash
PYTHONPATH=src:scripts python scripts/m43ai_result_audit.py
```

The independent round trip and comparison with the approved source package
are recorded in `../results_m43ai_native_validation/archive_roundtrip.json`.
This archive is the new M43AI study. The separate M43AF historical full release
retains its own archive and publication status.
