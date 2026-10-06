"""Source-only artifact freeze builder; creates no runtime or activation."""
from pathlib import Path

from contract import H_COMMIT, canonical, raw_pin, read, verify_inputs


def main():
    here = Path(__file__).resolve().parent
    inputs = verify_inputs(here.parent)
    names = sorted(path.name for path in here.iterdir() if path.is_file()
                   and path.name not in {"SOURCE_FREEZE.json", "PREFLIGHT.json", "PUBLICATION_MANIFEST.json", "PUBLIC_READBACK.json"})
    files = {name: raw_pin(read(here, name)) for name in names if (here / name).stat().st_size > 0}
    freeze = {"schema": "codec12-I-source-freeze-v1", "status": "BLOCKED_PENDING_OUTER_NATIVE_LIFETIME",
              "execution_enabled": False, "authority_commit": H_COMMIT, "files": files,
              "total_raw_bytes": sum(row["bytes"] for row in files.values()), "self_hash_excluded": True,
              "original_inputs": inputs["manifest"]}
    with (here / "SOURCE_FREEZE.json").open("xb") as handle:
        handle.write(canonical(freeze))
    print(f"source-only freeze: {len(files)} artifacts / {freeze['total_raw_bytes']} bytes; no activation")


if __name__ == "__main__":
    main()
