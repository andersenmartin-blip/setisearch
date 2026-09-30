# Native-v2 inline broker live probe: prospective scope

30 September 2026. This is a minimal `ENGINEERING_ONLY` qualification of two
transport assumptions used by the already-published deterministic native-v2
broker. It is not a native case, scientific evaluation or telescope operation.

## Immutable order and identities

1. Publish this scope and
   `results_radio_native_v2_broker_live_2026-09-30/live01/freeze.json` in one
   ordinary commit. The literal `SELF_COMMIT_CONTAINING_FREEZE` means that the
   resulting immutable commit is the sole permitted parent of the live probe.
2. Independently read back the freeze from that commit; require the branch head
   to equal it and derive the exact parent tree from the same commit.
3. Submit exactly one `create_tree` operation whose three entries carry inline
   UTF-8 `content`. Do not call `create_blob`.
4. Verify that the candidate tree is the exact parent tree plus the three frozen
   blobs, make exactly one child commit, recheck the head, and update the branch
   once with `force=false`. There is no automatic retry after an ambiguous
   response, conflict or failed verification.
5. Fetch the landed commit and issue one grouped `git cat-file --batch`
   readback for all three paths. Verify every Git blob, byte length and SHA256;
   verify canonical manifest/HEAD; decode strict base64; reconstruct and verify
   the 35-byte source.

The exact source is `native-v2-inline-broker-live-probe\n`, SHA256
`e01219aa6dcb93bbb6025ff76f5335363ca1defeaef5f3b874f3ba5396f9070a`.
The namespace is
`results_radio_native_v2_broker_live_2026-09-30/live01/archive`. It must be new
in the frozen parent.

## Prospective hard limits

The entire probe has at most 16 connector/Git calls, 64 KiB request bytes,
1 MiB response bytes, 4 KiB stored bytes, three new files, 180 elapsed seconds,
one mutation commit and one ref update. Any limit failure stops before the next
mutation. Request/response accounting is reported conservatively from canonical
JSON payloads and returned objects; it is connector-protocol evidence, not a
claim about HTTP wire framing.

The probe authorizes zero reservation, lease, RNG, score, receiver computation,
telescope read, spectrum access or scientific disposition. It neither reopens
the closed synthetic ledger nor changes any previous failure, holdout, target,
hold, counter or resource allocation. Passing only qualifies the small live
adapter behavior; it cannot promote the older prepare-only runtime freeze.

