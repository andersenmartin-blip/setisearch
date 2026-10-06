"""Build a non-self-referential manifest of the H checkpoint publication."""
import hashlib
import json
from pathlib import Path

from preparation import canonical


def pin(path, relative):
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob_sha1": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}


def main():
    here = Path(__file__).resolve().parent
    root = here.parent
    paths = sorted(path for path in here.iterdir()
                   if path.is_file() and path.name != "PUBLICATION_MANIFEST.json" and path.suffix != ".pyc")
    paths += [root / name for name in ("RADIO_CODEC12_2026-10-06H_PREPARATION.md", "PROJECT_STATUS.md",
                                       "PROJECT_DIRECTION.md", "RADIO_TWO_WEEK_PLAN_2026-09-26.md", "README.md")]
    rows = [pin(path, str(path.relative_to(root))) for path in paths]
    document = {"schema": "codec12-h-publication-manifest-v1", "status": "SOURCE_ONLY_NO_DISPATCH",
                "files": rows, "file_count": len(rows), "total_bytes": sum(row["bytes"] for row in rows),
                "spectra_opened": False, "activation_created": False, "certificate_issued": False}
    with (here / "PUBLICATION_MANIFEST.json").open("xb") as handle:
        handle.write(canonical(document))
    print(f"{len(rows)} files / {document['total_bytes']} bytes")


if __name__ == "__main__":
    main()
