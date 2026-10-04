# Independent review of the original hosted CAS control

The actual control remains **CLOSED_FAILED**. Its first exact expected-revision CAS was observed as accepted, with candidate A unchanged across complete immutable readbacks and the subsequent head readback equal to A. The second, stale expected-revision CAS returned a generic GitHub internal error. That response does not meet the frozen conflict criterion; no immediate post-negative control was completed. The service component and all eleven authentic scientific gates therefore remain unqualified.

This review read retained local evidence, independently reconstructed Git objects and checked raw bytes with Python standard-library code. It made no network call, imported no project validators, ran no tests or control, changed no frozen source, and created no successor. An independent archive/resource subreview checked the same retained archive.

| Evidence | Verified observation |
|---|---|
| Run / job / attempt | 37201924254 / 111435213248 / 1; push event; completed failure |
| Preparation / activation | `c14b63dd0cbbc70b6c78d43c52b8c6cea618fef1` / `d4d38a0a4316b36197c3a18e33c1369f96e7d29a` |
| Full raw freeze SHA-256 | `250fbb31bb183d2ba0ee380901617a008f44d896d9b4f5a2f9c120758c543da3` |
| Lossless archive | 941,861 bytes; 117 members; SHA-256 `e1a61f7497490b8530771bff6ab16f643b241982f0618c6285c53ff954b6eba3` |
| Archive intrinsic Git blob | `9854ea7b9c59f163a237f81f7cc0728a08137449` |
| Complete child request/response sequence | 29 calls, 2 mutations; every journal hash and cumulative count agrees |
| Conservative child byte charge | 2,445,260 request-descriptor-plus-response bytes; does not represent complete HTTP/TLS overhead |
| Full frozen sources | Exactly ten selected source bodies, 179,599 bytes, agree with lengths, SHA-256, intrinsic Git blobs, proof and local files |
| Direct child | PID 2349; exit 1; wait status 256; reaped once; total elapsed 9.300751151 s |
| Captured streams | Exactly 14-byte `CLOSED_FAILED\n` stdout, empty stderr, complete retention, no credential refusal |

The archive's 117 strict base64/gzip entries decode to 3,075,582 original bytes with matching lengths, hashes and exact local-copy bytes. There are no missing or extra decoded members. Inventory and subsequent accounting reconcile, including two directories, the accounting reserve and excluded accounting files. Publisher scope is 3,083,774 logical bytes including directory allocations and 3,469,312 allocated bytes, within the 8 MiB child retention cap. The envelope is below its 1 MiB cap.

A (`596f0fb45337f2af475f73fabef34073c3c74a2c`) has the activation as its sole parent and adds only the regular engineering `service-state.json`. Complete candidate commit, root tree, owned subtree and blob were read before call 15 and again at calls 16–19; their reconstructed Git identities and raw content agree exactly. Calls 2 and 14 observed the activation head, call 15 retained the exact successful updateRefs acknowledgement, and call 20 observed A. This supports the initial acceptance observation. It does not alone qualify the complete two-outcome service or the scientific store.

B (`82dc9309f398f9499ada0212bfa704a147151dda`) was pre-created as A's sole-parent child, preserving A's state and adding only the regular engineering `conflict-test-state.json`. Calls 24–27 verify its complete immutable identities, and call 28 observes A. Both CAS requests use the frozen repository ID, namespace, branch, identical activation beforeOid and force:false; their afterOid values are A and B respectively. B is a valid fast-forward child of the observed current head, so the negative request tests the stale expected revision.

Call 29 returned HTTP 200 with only an errors list containing a generic internal-error message, timestamp and diagnostic ID. It contains no data/updateRefs:null and no error path or expected-revision reason. The control correctly stopped CLOSED_FAILED without call 30, retries or fallback. No immediate post-negative head readback, immutable-B readback or child runtime-after exists. The later archive publication on A cannot replace those missing controls, and this review makes no claim that B ever or never became the branch head. The separate retained fresh candidate-object review agrees with the candidate commit/owned-tree/blob bytes.

All ten supervisor-selected source records match before/after, including recorded stat metadata. All fifteen supervisor-selected runtime records also match. The child captured twelve runtime-before records; six overlap and agree with the supervisor selection, while six have only child-before evidence. This is a selected observation, not complete ELF/runtime custody or an authenticated scientific execution certificate. Archived copies cannot restore the original host inode or execution custody. The marker digest binds the canonical source list without a final newline; the manifest SHA-256 binds the complete raw freeze-file bytes. Gate proof and the child activation proof agree exactly.

The single recorded wait4 disposition agrees with the direct child and its reaping at 9.297172021 s. Recorded wait4 maximum RSS is 30,617,600 bytes; sampled aggregate RSS peaks at 28,971,008 bytes and per-process HWM at 29,523,968 bytes. There are 155 observations of one process. These samples do not certify every short-lived or escaped descendant, complete peak memory, or enforced kernel memory limits.

Administrative evidence publication succeeded at `c253ba95e096f983c0bc3afa81b6e669f8fc0cb7`, sole parent A, tree `92a21c4a392985c239a19cac5557df4bf1e9f01d`. The retained fresh publication metadata independently reconstructs that commit identity; root separately verified its sole added regular evidence blob and unchanged existing tree. The final receipt in the retained job log matches the archive identity. Its 19 publisher calls and 5,401,964 request/reply bytes are **self-reported**: the publisher's full raw HTTP transcript and publication receipts are not in the archive, so those totals were not independently reconstructed. Successful archiving does not change the control failure.

The one-shot allocation remains spent: 300 s and 20 MiB, bringing the supplied selected-allocation ledger subtotal to 910 s and 40 MiB. Actual elapsed time or archive compression does not refund that allocation. No retry or successor was created. Scientific execution, allocation, store qualification, source execution and full runtime qualification remain false; the eleven scientific gates remain pending, and this review opened no spectra or holdouts.
