# Radio native v2 — runtime-custody remediation protocol

**Result: RUNTIME_CUSTODY_TOPOLOGY_AUDITED_PROTOCOL_FROZEN.** A read-only audit of
all 1,366 paths in freeze `20261002d` found 151 hardlinked paths, all confined to the
Git runtime, across six inodes and 53,115,687 unique bytes. Bounded enumeration of
`/usr/local/bin` and `/usr/local/libexec/git-core` closes 157 aliases; no material
Python, Node, library or repository/input hardlink was found.

- [Prospective protocol](config/radio_native_v2_runtime_custody_remediation_20261002a.protocol.json)
- [Audit summary](results_radio_native_v2_runtime_custody_20261002a/audit-summary.json)
- [Reproducible verifier](results_radio_native_v2_runtime_custody_20261002a/verify_runtime_custody_audit.py)

The protocol partitions Git as activation-only runtime: a future freezer must bind its
complete hardlink group topology, activation must re-enumerate and hash it through
stable `O_NOFOLLOW` descriptors, and Git use must cease before the receipt returns.
Every runtime used after activation remains sole-link. A future receipt must bind the
custody-manifest hash and all worker gates must recheck it.

This is not a correction of the failed evaluation and grants no activation, retry,
reservation, RNG, native/scientific case or telescope access. A new plan, freeze,
preread and marker would be required after implementation and negative tests; the
spent marker and invocation remain permanently closed.
