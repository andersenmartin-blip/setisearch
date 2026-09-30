# Corrected native-v2 inline broker live probe passes

30 September 2026. **PASS for the bounded live transport adapter semantics.**
This does not qualify a native case or scientific evaluation.

The public freeze at `04bc5c605129feb26a329481c3a46bfc78a3b5c9`
and tree `c77bd5abd4bd829338646488078bd54d3a231cee` was read back
exactly. The branch equalled that commit and the fresh live02 namespace was
absent before mutation. Its freeze SHA256 is
`93f0ebb57059cd230ebb159a718b95799ccd3f989b50e83ad491ba629c7d79c7`.

The connector accepted one inline-content `create_tree` request with no
`create_blob` calls. The request was counted before mutation as 1,355 bytes;
the raw 143-byte result was preserved before derived accounting. Its returned
tree `aa70c4d060a1a53b201acb99e8626806087029db` exactly matched the
independently constructed content-addressed tree. The call took 1.035 s.

One child commit, `51011e129e4911fa319333afc0ef108675c0e5d8`, was then
created. Its sole parent and tree were independently read back, the branch head
was still the freeze commit, and one `force=false` update succeeded. A fresh
fetch returned that exact child, parent and tree.

One `git cat-file --batch` process read all three landed paths in 0.352 s. It
returned exactly the frozen blob identities and 791 stored bytes: 65-byte HEAD,
52-byte base64 chunk and 674-byte canonical manifest. Strict decoding restored
the exact 38-byte source `native-v2-inline-broker-live-probe-02\n`; its SHA256
is `bd26422d76d8c0d0b93bc5a54640cc0fa357f67f79a82ae448736c8009317a4a`.
Manifest/HEAD, no-restart and no-admission fields all matched.

The complete live sequence used 11/16 bounded connector/Git operations. To
avoid pretending that connector wrapper objects equal HTTP wire frames, the
audit conservatively charges 16 KiB request, 64 KiB response and 30 seconds
against the frozen 64-KiB, 1-MiB and 180-s caps. Actual inline request/result,
mutation timings and grouped readback bytes are recorded above. Stored bytes
are 791/4,096, mutation commits 1/1 and ref updates 1/1.

Live01 remains **CLOSED FAILED** and spent; this pass does not erase or retune
it. Live02's fresh identity fixed only the orchestration defect prospectively.
The result qualifies inline content, receipt preservation, exact candidate
identity, single commit/non-forced advancement and grouped immutable readback
for a small connector payload.

**Exact continuation:** implement this qualified behavior as the injected
adapter for the published broker and the still-missing complete fresh
render/threshold/physical/evaluate runner. Add durable raw-receipt-before-parse
handling and exact call/request/response/time/RSS accounting. Then generate a
new complete runner+broker runtime freeze (the prepare-only freeze predates the
broker), publish it and independently read back every pinned code/input/runtime
identity. No case reservation or RNG may occur before that separate complete
freeze succeeds.

No reservation, lease, RNG, score, receiver computation, spectrum/telescope
read or scientific disposition occurred. 127/24 remains **NOT ACTIVATED**.
HD189733/85030 stays selected; HD1461/71139 stays on pointing-provenance HOLD;
GJ724/73005 stays reserve. Old holdouts remain unopened; all failures, spent
identities and limits persist; LS is paused and CHEOPS remains UNSENT.

