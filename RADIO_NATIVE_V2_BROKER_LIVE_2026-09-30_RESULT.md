# First native-v2 inline broker live probe closes failed

30 September 2026. **CLOSED FAILED.** The prospectively published freeze was
read back exactly from commit `8b31564dff3abe3611ec315aca632adef7f5d2c0`;
that commit and its tree `5ee054a6970086e2fa8db71fdcc04b8f5e9c252b`
were the branch head and parent immediately before the live call. The target
namespace was absent.

The one permitted `create_tree` call was issued with three inline UTF-8 contents
and no `create_blob` call. Its canonical request is 1,349 bytes and the frozen
stored payload is 785 bytes, within the 64-KiB and 4-KiB limits. After the
connector returned, the local orchestration expression attempted to instantiate
an unavailable `TextEncoder`; the expression failed before preserving the
connector response. Under the prospective no-retry rule this is a lost receipt,
so no second call was made.

A read-only lookup proves that the exact locally predicted tree object
`8e85413f6548f9ab6878852b043296f5a038516e` exists remotely. Since Git tree
identities are content-addressed, this establishes that the inline contents
produced the exact parent-plus-three-file tree. It does **not** recover the lost
receipt and cannot qualify the complete protocol. No child commit was created,
no ref update was attempted, and the branch remained on the freeze commit.
Consequently the required grouped immutable readback was never entered.

The first post-stop tree audit incorrectly requested the whole recursive
repository tree. Its returned representation exceeded the frozen 1-MiB response
cap. It was read-only and occurred after the decisive failure, but is retained
as a second protocol defect; exact response-byte accounting was not recovered
and no capacity pass is claimed.

The probe therefore establishes only a useful partial fact: this connector can
materialize the exact small inline tree without serial blob calls. End-to-end
receipt preservation, commit/ref advancement and grouped readback remain
unqualified. The namespace is spent even though it never became reachable from
the branch.

**Exact continuation:** do not retry live01. Publish a fresh live02 freeze and
namespace. Compute and bound the serialized request before the mutation; store
the raw connector result before any optional derived accounting; compare only
the returned tree SHA with the locally predicted SHA; then make one child
commit/non-forced update and perform one grouped `git cat-file --batch` readback.
Any ambiguity still stops without retry. Only a passing fresh probe may feed a
real adapter into the still-missing complete fresh runner, which itself requires
a new public runtime freeze/readback before reservation or RNG.

No reservation, lease, RNG, score, receiver computation, spectrum/telescope
read or scientific disposition occurred. 127/24 remains **NOT ACTIVATED**.
HD189733/85030 stays selected; HD1461/71139 stays on pointing-provenance HOLD;
GJ724/73005 stays reserve. Old holdouts are unopened, prior failures and spent
identities persist, LS is paused and CHEOPS remains UNSENT.

