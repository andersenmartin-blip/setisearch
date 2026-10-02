# Radio native v2 — fresh integrated execution preread

**Result: FRESH_EXECUTION_PREREAD_STRUCTURALLY_VERIFIED_PUBLICATION_PENDING.** A new
4,364-byte preread with SHA256
`cbd46bf18e329df18b04a3f2ce18041e8293a1fc0622678d3b069f908b7a1693`
binds plan `20261002j`, runtime freeze `20261002d`, all 24 material code/test pins and
public integrated preparation commit
`25e9df222af79c677adc1ad247104fd6b0c4d68e`.

The exact preparation commit tree and its plan/freeze blobs match public readback. The
new preread's canonical plan and freeze hashes differ from the old preread, so the old
artifact cannot be reused. Eight ordered source-case/domain/archive identities verify.
Changed plan hashes, a false admission bit and the old preparation commit do not match
the frozen proof.

- [Fresh preread](config/radio_native_v2_execution_preread_20261002b.json)
- [Verification receipt](results_radio_native_v2_execution_preread_20261002b/verification-summary.json)
- [Verifier](results_radio_native_v2_execution_preread_20261002b/verify_execution_preread.py)

Worker bundles are deliberately not materialized yet: their new required activation
receipt can only exist after the marker-only public child is independently read back.
This defers, rather than fabricates, the final preread/receipt/bundle join.

## Disposition and continuation

The plan remains `BLOCKED_PREPARATION_REVIEW`; the historical contract was not
rewritten. No marker, large input, eight-input control, reservation, RNG, telescope
read, native case or science case occurred.

**Exact continuation:** publish this preread and its complete report/evidence as one
fast-forward science commit and independently read back its parent, tree and plan/
freeze/preread blobs. The very next science commit must add only the unique activation
marker as a single-parent direct child; do not insert a documentation/readback commit.
The marker must carry the external preread readback and authorize exactly one fresh
engineering control with no retry. HD189733 remains selected, HD1461 HOLD and GJ724
reserve. 127/24 is NOT ACTIVATED; spectra and original holdouts remain unopened; LS
paused; CHEOPS UNSENT. Consolidate 9 October. No external messages.
