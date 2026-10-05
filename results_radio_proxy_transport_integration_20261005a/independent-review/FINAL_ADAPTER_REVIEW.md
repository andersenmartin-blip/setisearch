# Final independent inert adapter review

Date: 2026-10-05. Final reviewed core source is retained in `adapter_final_v2/`.
The copied `proxy_opener.py` and `native_bindings.py` were compared with the
implementer's current files and matched after the targeted checks.
All five reviewed source/fixture hashes are retained in
`adapter_final_v2/reviewed-source-sha256.txt`. The final opener SHA-256 is
`a9e11755fa167838259f45c87407abba793964163fbaae3207c3db3fa9fc5b34`.

**Suitable for publication as inert, synthetic-tested transport integration.**
No unresolved material source defect was found in the reviewed revision.

Five independent targeted checks passed; their exact source and output are
`adapter_final_v2/targeted_review.py` and `adapter_final_v2/targeted_review.log`:

- Second-use refusal uses a separate receipt and leaves the entire primary
  attempt receipt and CONNECT407 prefix unchanged.
- A body read returning three bytes across the deadline retains all three and
  records them exactly once in the actual-received counter.
- A custom injected HTTP response without a `.stream` attribute preserves its
  primary `OSError`, produces `WheelIOError`, and closes the registered response.
- Constructing the native-shaped bindings touches no injected module attribute
  and performs no socket/context operation.
- Optional `pending_body` returning a nonbytes value or raising a property error
  cannot replace the primary body failure or skip registered response cleanup;
  the optional-evidence failure is recorded separately.

The native builder source was also inspected. It fixes the endpoint to numeric
loopback, registers the raw socket before connect, uses explicit trust bytes
whose hash is checked, creates its TLS context without default trust loading,
sets hostname/CERT_REQUIRED/TLS1.2 and HTTP/1.1 ALPN, wraps without implicit
handshake, then registers the TLS socket before its explicit handshake. Deadline
refreshes surround the prospective blocking stages. The supplied fake-module
tests cover these configuration values plus connect, handshake and ALPN refusal
cleanup. Their full suite was not independently repeated; the implementer
retained the 40-test final log.

The predecessor review findings are corrected in this revision. The interim
custom-response regression is retained with exact source and reproduction in
`adapter_fix01/`; the initial adapter defects remain reproducible from
`adapter_snapshot/`. The preceding accepted source/check snapshot remains intact
in `adapter_final/`. These earlier snapshots are historical evidence, not the
accepted final source. The final robustness patch uses a guarded optional raw
evidence reader in both body failure handling and opener metadata collection.

All independent checks used injected synthetic objects. No actual socket,
SSLContext, certificate parsing, installation, scientific-native import or
telescope read was performed. This review supplies no native transport/runtime
qualification and does not reactivate the spent bootstrap.
