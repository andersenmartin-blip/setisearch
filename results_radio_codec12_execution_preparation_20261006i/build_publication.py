"""Administrative publication manifest; no runtime/scientific authority."""
from pathlib import Path

from contract import canonical, raw_pin


def main():
    here = Path(__file__).resolve().parent
    repo = here.parent
    paths = sorted(path for path in here.iterdir() if path.is_file()
                   and path.name not in {"PUBLICATION_MANIFEST.json", "PUBLIC_READBACK.json"})
    paths += [repo / name for name in ("PROJECT_STATUS.md", "PROJECT_DIRECTION.md",
        "RADIO_TWO_WEEK_PLAN_2026-09-26.md", "README.md", "RADIO_CODEC12_2026-10-06I_IMPLEMENTATION.md")]
    rows = [{"path": path.relative_to(repo).as_posix(), **raw_pin(path.read_bytes())} for path in paths]
    document = {"schema": "codec12-I-publication-manifest-v1", "status": "BLOCKED_PENDING_OUTER_NATIVE_LIFETIME",
                "files": rows, "file_count": len(rows), "total_bytes": sum(row["bytes"] for row in rows),
                "source_freeze_is_live_execution_freeze": False, "control_dispatches": 0,
                "spectra_opened": False, "activation_created": False, "certificate_issued": False}
    with (here / "PUBLICATION_MANIFEST.json").open("xb") as handle:
        handle.write(canonical(document))
    print(f"publication: {len(rows)} bodies / {document['total_bytes']} bytes")


if __name__ == "__main__":
    main()
