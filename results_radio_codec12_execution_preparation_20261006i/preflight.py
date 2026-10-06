"""Read-only source integration check; never dispatches or imports native code."""
import argparse
import sys
from pathlib import Path

from contract import H_COMMIT, canonical, sha, verify_inputs, verify_receiver_contexts


def inspect(repo_root):
    inputs = verify_inputs(repo_root)
    contexts = verify_receiver_contexts(inputs)
    if any(name in sys.modules for name in ("numpy", "h5py", "hdf5plugin")):
        raise ValueError("preflight cannot accept a native-imported process")
    return {
        "schema": "codec12-I-source-preflight-v1", "status": "BLOCKED_PENDING_OUTER_NATIVE_LIFETIME",
        "authority_commit": H_COMMIT, "original_input_files": len(inputs["manifest"]["files"]),
        "original_input_bytes": inputs["authority_bytes"], "handoff_count": 12, "rows_per_handoff": 16,
        "original_input_manifest_sha256": sha(inputs["h_raws"]["INPUT_MANIFEST.json"]),
        "receiver_metadata_roles_validated": list(contexts),
        "receiver_contexts": {role: {key: value[key] for key in ("context_sha256", "receiver_bank_sha256")}
                              for role, value in contexts.items()},
        "native_imports": 0, "hdf5_operations": 0, "controlled_payloads_created": 0,
        "archive_values_read": 0, "rng_draws": 0, "control_dispatches": 0,
        "missing_before_activation": [
            "fresh exact runtime inventory and effective loader/native graph",
            "complete process/descendant/native-loader/terminal-IO lifetime integration",
            "immutable executable outer scope and independent full public preread",
            "distinct one-shot marker-only activation and cumulative allocation",
        ],
        "source_freeze_is_live_execution_freeze": False, "codec_certificate_issued": False,
        "scientific_readiness": False,
        "next": "integrate actual current native lifetime inputs and source-pinned outer admission; preserve H limits and original contracts",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args()
    print(canonical(inspect(args.repo_root)).decode(), end="")


if __name__ == "__main__":
    main()
