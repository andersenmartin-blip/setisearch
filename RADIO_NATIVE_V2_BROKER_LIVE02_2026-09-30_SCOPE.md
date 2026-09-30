# Native-v2 inline broker live02 probe: prospective scope

30 September 2026. This is a fresh `ENGINEERING_ONLY` probe after live01 closed
failed. It is not a retry: live01 and its unreachable namespace remain spent;
live02 uses a new source identity and namespace while retaining every original
gate and limit.

The freeze is published first. `SELF_COMMIT_CONTAINING_FREEZE` then names its
immutable public commit as the only allowed live parent. Public readback must
verify that commit, tree, freeze bytes, branch head and absence of the new
namespace before a mutation.

Exactly one `create_tree` call may submit the three frozen UTF-8 contents. The
serialized request length must be computed and checked before that call. The raw
connector result must be saved immediately after return and before derived
accounting. `create_blob` is forbidden. The returned tree SHA must equal a local
content-addressed prediction; no recursive repository-tree request is allowed.

After candidate verification, exactly one child commit may be made. Its parent
and tree are read back, the branch head is rechecked, and exactly one
`force=false` update may be attempted. Any ambiguous response, conflict or bad
identity stops without retry. After landing, one `git fetch` and one grouped
`git cat-file --batch` process must read all three immutable paths from the
landed commit. Every blob, length and SHA256, manifest/HEAD relation, strict
base64 decoding and the 38-byte source identity must pass.

Hard limits remain 16 calls, 64 KiB request bytes, 1 MiB response bytes, 4 KiB
stored bytes, three new archive files, 180 elapsed seconds, one mutation commit
and one ref update. The exact source is
`native-v2-inline-broker-live-probe-02\n`, SHA256
`bd26422d76d8c0d0b93bc5a54640cc0fa357f67f79a82ae448736c8009317a4a`.
The fresh namespace is
`results_radio_native_v2_broker_live_2026-09-30/live02/archive`.

This scope authorizes zero reservation, lease, RNG, score, receiver calculation,
spectrum/telescope read or scientific disposition. A pass qualifies only this
small transport adapter behavior. It cannot promote the old preparation freeze
or activate 127/24.

