# Radio native v2 — distinct execution-preread preparation

**Result: DISTINCT_EXECUTION_PREREAD_PUBLIC_READBACK_VERIFIED_EXECUTION_STILL_BLOCKED.**
A separate preread artifact now binds the exact public preparation commit
`39c8a4dee4f8c59357617e602855bea705217051`, its verified tree, current plan,
runtime freeze and every material code-file pin. The historical plan remains
`BLOCKED_PREPARATION_REVIEW`; it was not rewritten to ready.

The 4,082-byte preread has SHA256
`582a98eb42a704c6b1ef8a629734a7aae1e515ad287ddf11652e821c807b73cc`.
Its `engineering_control_admitted` field is true as required by the existing
worker-admission schema, while execution, reservation, scientific, native, RNG,
telescope and network authority all remain false. No execution route was opened.

## Verification and retained failure

The verifier confirms that the exact plan and freeze blobs are present in the
public preparation commit and constructs all eight fixed worker-admission identities.
Changed plan hashes and a false admission bit are refused. A first negative test
incorrectly expected the structural schema alone to authenticate an arbitrary valid
40-hex commit and closed failed. That failure is retained. The corrected check keeps
the structural boundary explicit and independently compares the claimed commit tree;
the deliberately wrong published commit is rejected because its tree differs.

- [Preread artifact](config/radio_native_v2_execution_preread_20261002a.json)
- [Verification summary](results_radio_native_v2_execution_preread_20261002a/verification-summary.json)
- [Retained failed first attempt](results_radio_native_v2_execution_preread_20261002a/failed-first-attempt.json)
- [Reproduction script](results_radio_native_v2_execution_preread_20261002a/verify_execution_preread.py)
- [Publication readback](results_radio_native_v2_execution_preread_20261002a/publication-readback.json)

## Disposition and continuation

The immutable preread publication and independent public readback are complete.
Science commit `fda127b40e0781c4a4b750615563693bb557c95f` has the expected parent and
tree, and its preread, report and verification-summary blobs match. Main commit
`19ee0d83fd1ba029a0cd4bbf8f332ea6164efb5d` has the expected parent, tree and
README blob. The global activation guard nevertheless remains false: publication
does not bypass the separate pre-admission gate. The prospective plan remains
blocked, and no large source or eight-input control has run.

**Exact continuation:** specify and verify the separate one-control activation
transition while preserving every published pin and the immutable blocked historical
preparation contract. Do not open large inputs before that transition is independently
closed.
HD189733 remains selected, HD1461 HOLD and GJ724 reserve. 127/24 is NOT ACTIVATED;
spectra and original holdouts remain unopened; LS paused; CHEOPS UNSENT. Consolidate
9 October without extension. No external messages.
