# METHODS64 preservation wrappers: static peer review

Status: **PASS_STATIC_PRESERVATION_WORKFLOW**. This is a source/AST review only; it does not authorize invocation, confirm that methods have run, or change either failed validation gate.

Reviewed files and SHA256:

- `pilot_protocol_20261008/package_method_study.py`: `bb0f9a3cf5d4a09450e1fcca99d5e7fd5e691896da76880ef658981b32003e22`
- `pilot_protocol_20261008/run_method_study_packaging.py`: `ff6501a9526c31830143637d38d90c68a8971b03ca5e40fb652066114c7809c8`

Both entry points require explicit parent confirmation that the coordinator/processes and independent review have closed. Before copying original bytes, the packager requires the retained aggregate, resource, rolling-ledger and planned-slot files, the final panel marker for coordinator exit zero or a closed-no-retry ledger for failed closure, the admission/freeze/scope/audit files, and the original controller claim. Parent confirmation remains the invocation authority; preparation grants none.

The new archive directory refuses overwrite/replay. Every one of the 64 planned slots receives an archive and a manifest, including absent directories or empty original file sets. Missing normal-completion maps and metadata are listed without reconstructing them. All present original files, controller files, claims and prerequisite evidence are retained. Member receipts bind exact byte sizes and SHA256 digests; deterministic tar/gzip headers do not alter member bytes. The packager checks ordinary files and rejects observed size/mtime changes during copying.

The wrapper has one archival child and records its whole-process CPU, wall time and peak RSS, including imports and the child's final receipt write. Its separate wrapper CPU is retained. The declared 1200-second preparation reserve remains a planning reserve, not measured consumption; upstream preparation/upload CPU is explicitly unmeasured. Archive child CPU/wall limits are 120/180 seconds.

No scientific code, native array API, RNG, detector, reader, codec or network call was executed by this review. No retained map, array or telescope value was read. Syntax was checked by parsing source text with the standard-library AST module.
