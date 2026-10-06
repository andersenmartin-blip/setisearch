"""Administrative J publication manifest. Not an executable admission freeze."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
files = [p for p in sorted(HERE.iterdir()) if p.is_file() and p.name not in ("PUBLICATION_MANIFEST.json", "PUBLIC_READBACK.json")]
files += [ROOT / name for name in ("RADIO_LOADER_LIFETIME_2026-10-06J_PREPARATION.md", "PROJECT_STATUS.md",
                                  "PROJECT_DIRECTION.md", "RADIO_TWO_WEEK_PLAN_2026-09-26.md", "README.md")]
rows = []
for path in files:
    raw = path.read_bytes()
    rows.append({"path": str(path.relative_to(ROOT)), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                 "git_blob_sha1": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()})
value = {"schema": "loader-J-publication-manifest-v1", "status": "SOURCE_COMPONENT_NO_COLLECTOR_NO_DISPATCH",
         "files": rows, "file_count": len(rows), "total_bytes": sum(row["bytes"] for row in rows),
         "collector_created": False, "native_target_executions": 0, "kernel_traces_collected": 0,
         "activation_created": False, "allocation_created": False, "source_freeze_is_executable_freeze": False,
         "self_excluded": True, "codec_certificate_issued": False, "spectra_opened": False}
with (HERE / "PUBLICATION_MANIFEST.json").open("xb") as handle:
    handle.write((json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode())
