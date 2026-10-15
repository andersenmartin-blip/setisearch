# Final public metadata builder

This helper prepares local GitHub payloads after closure. It never calls GitHub,
updates a ref, runs numerical code, retries a case, draws random values, or edits
the frozen trial. It does not decide scientific gates. Root reviews and publishes
the concrete payload with the existing GitHub connector.

Keep the original stopped study and separate resource extension in their own
namespaces. Original failed qualification and original SUMMARY remain unchanged.
The nine exposed bands remain unavailable when the original admission guard
blocked them. Missing or failed evidence is never changed to a measured zero.
The derived report may have a scientific joint-gate failure while its complete
metadata/QA binding still passes. A terminal derivative integrity failure may be
published as failure, with no all205 integrity claim.

## Before invoking against real evidence

Wait for every present original and extension phase and scheduler to close. Build
the original report and byte-evidence index with the reviewed helpers. Build the
separate derivative report if used. Do not run this publication helper against
live studies. In the extension mode it reads the existing derivative report and
uses the same pure `check_union_documents` metadata function as the final
transport wrapper. It performs no numerical QA/search.

Save fresh immutable Git commit and **non-truncated** tree API JSON for the
current research head. The three full local overview bases are verified against
the root blobs in that tree. The default expected research parent is
`fc0922ec078bc28d203e3680edf810e3183a46d1`; if the branch moves, fetch the new full
bases and rebuild with its explicit head. Never force an update.

Example only; substitute actual closed directories and branch name:

```bash
python reporting_publication_20261015/build_publication.py prepare-research \
  --mode resource-extension --branch ACTUAL_RESEARCH_BRANCH \
  --stage sixscan_burst_20261015 \
  --report-dir CLOSED_ORIGINAL_REPORT \
  --evidence-dir CLOSED_ORIGINAL_EVIDENCE_INDEX \
  --base-dir repo_publish_sixscan_20261015 \
  --base-commit-json IMMUTABLE_RESEARCH_COMMIT.json \
  --base-tree-json IMMUTABLE_RESEARCH_ROOT_TREE.json \
  --original-scheduler checkpoints_sixscan_20261015/SCHEDULER_STATE.json \
  --extension-root ACTUAL_EXTENSION_ROOT \
  --extension-report-dir CLOSED_DERIVATIVE_REPORT \
  --extension-state ACTUAL_EXTENSION_ROOT/checkpoints/SCHEDULER_STATE.json \
  --extension-terminal-status ALL_RESOURCE_EXTENSION_PHASES_CLOSED \
  --out NEW_PUBLIC_PAYLOAD_DIRECTORY
```

`--mode complete` requires all five original phases and the fully verified
original report. `--mode failure` accepts the terminal original stopped study
without inventing its missing phases. Extension inputs require the explicit
`resource-extension` mode. Supply `--extension-terminal-status
RESOURCE_EXTENSION_STOPPED_RETAINED_NO_RETRY` for an actually stopped extension; its report must then
retain the incomplete/failed derivative qualification. Explicitly supply every
accepted terminal status; the helper never guesses an unfamiliar dispatcher.

The extension report directory must contain its own reviewed
`README_PREPEND.md`, `PROJECT_STATUS_PREPEND.md`, `PROJECT_DIRECTION_PREPEND.md`
and `MAIN_README_PREPEND.md`; alternatively point `--prepend-dir` at a separately
reviewed prefix directory. The original report helper supplies the four same
files. All historical bytes are retained as an exact suffix after the new prefix
and separator. Prefix/base byte counts and exact Git blob pins are recorded.

The final 15 October closure is a bounded **original failure**. Extension
admission was rejected and the extension remained PREPARED_NOT_ADMITTED.
Use `--mode failure`, the actual bounded-failure report/prefix directory, and
the existing `reporting_20261015/evidence` directory; do not rerun its indexer.
The `SETI_BOUNDED_FAILURE_REPORT_METRICS_V1` contract requires the exact original
SUMMARY and evidence-index SHA256 plus verified metadata-binding flags while
retaining false scientific integrity/joint gates. Include the CPU breach/
admission-rejection audit and prepared extension tool status as explicit extra
files/trees. Do not activate a prospective amendment or extension GO.

Include final resource witnesses, durable delivery IDs/receipts, recovery or
closure proofs, and reviewed non-numerical helpers through repeated:

```text
--extra-file analysis/sixscan_burst_20261015/delivery/DELIVERY_RECEIPT.json=/absolute/local/DELIVERY_RECEIPT.json
--extra-tree analysis/sixscan_burst_20261015/resource_witnesses=/absolute/closed/witness_directory
```

Extra trees must be separate from the output. Check that the actual delivery
receipt contains all durable file IDs and ordered part hashes before using it.
Delivery IDs generated after the result commit can be published in a separate
receipt commit; never imply a not-yet-verified upload succeeded.

## Public subset and exact byte preservation

The default public subset includes original summary/calibration/tables, full
phase closures, scheduler closure, report, byte-evidence indexes, all small QA,
claim, COMMITTED/artifact-manifest/admission receipts and worker logs. The
separate extension contributes its protocol/code, admission, union/resource
gates, full states/logs, receipts and derived report. The final archive retains
all raw arrays and larger raw search payloads; they are not copied to GitHub.
No NPZ/NPY/native/checkpoint ZIP or other binary is uploaded by this helper.

Per-case receipt text is packed into JSONL shards. Each record stores the safe
original relative path, exact UTF-8 source string, SHA256, byte count and Git
blob SHA. `content_utf8.encode('utf-8')` reconstructs the original bytes,
including CRLF, whitespace and trailing newline. `RECEIPT_INDEX.json` maps every
source to its shard and line. No receipt is summarized or numerically edited.

The default public blob cap is4MiB. Larger text is split at valid UTF-8 byte
boundaries, with `.PARTS.json` recording the original hash, exact bytes and
ordered parts. Concatenation adds no separators. Inspect these indexes when
linking a split file. No file is silently truncated. The archive remains the
canonical complete evidence transport with its unchanged native source ZIP.

## Connector publication and mandatory readback

The local bundle contains `payload/`, `EXPECTED_BLOBS.json`,
`BLOB_UPLOADS.jsonl`, `TREE_PAYLOAD.json`, and `COMMIT_AND_REF_PLAN.json`.

1. Read the concrete report/prefixes and manifest. Confirm all needed closure,
   resource and delivery receipts are present; inspect failure limitations.
2. For each upload row, pass its exact UTF-8 file contents to `create_blob` and
   require the returned SHA equals `expected_sha`. Unchanged existing blobs may
   be reused by exact SHA. Do not submit literal local filenames as content.
3. Call `create_tree` with the recorded base-tree SHA and exact tree elements;
   create one commit with the recorded sole parent. Save both returned SHAs.
4. Update the intended branch with `expected_sha` equal to the recorded parent
   and `force:false`. A moved head requires a new base read and payload build.
5. Read the immutable new commit/tree and download **all expected public blob
   bytes** into a new mirrored readback directory outside `payload/`. Tree JSON
   must expose full expected repo paths and must not be truncated. It may be a
   verified recursive tree readback; a root-only tree does not contain nested
   paths. Preserve the API response bytes/metadata as separate local receipts.
6. Verify locally:

```bash
python reporting_publication_20261015/build_publication.py verify-readback \
  --bundle NEW_PUBLIC_PAYLOAD_DIRECTORY \
  --commit ACTUAL_NEW_COMMIT_SHA \
  --commit-json IMMUTABLE_NEW_COMMIT.json \
  --tree-json IMMUTABLE_NEW_FULL_TREE.json \
  --blob-root SEPARATELY_DOWNLOADED_IMMUTABLE_BLOBS \
  --receipt NEW_PUBLICATION_READBACK.json
```

The verifier rejects a changed parent, tree binding, mode, path, Git blob SHA,
SHA256, byte count, missing blob, truncation, or reuse of the local payload as
the readback source. Only successful all-blob verification emits
`ALL_EXPECTED_PUBLIC_BLOBS_EXACT`. Separately reread the branch ref to confirm it
still points at the intended commit; the receipt deliberately does not claim a
ref-head check it did not perform.

## Main overview after research readback

Only after successful research readback, fetch the exact current main head/tree
and its **full** README. Use the complete stored base
`repo_publish_matched/MAIN_README.md` only if its Git blob still matches that
immutable current main tree. Supply the reviewed final `MAIN_README_PREPEND.md`:

```bash
python reporting_publication_20261015/build_publication.py prepare-main \
  --base-file repo_publish_matched/MAIN_README.md \
  --base-commit ACTUAL_CURRENT_MAIN_SHA \
  --base-commit-json IMMUTABLE_MAIN_COMMIT.json \
  --base-tree-json IMMUTABLE_MAIN_ROOT_TREE.json \
  --prepend-file CLOSED_DERIVATIVE_REPORT/MAIN_README_PREPEND.md \
  --research-readback NEW_PUBLICATION_READBACK.json \
  --out NEW_MAIN_PAYLOAD_DIRECTORY
```

Main changes only README and links to the verified immutable research commit.
Its local provenance manifest is not an additional main repo file. Publish and
read back its sole expected blob with the same parent lease and byte checks.

## Preparation-only verification

`test_publication_dummy.py` uses dummy text/metadata in a temporary directory.
It does not read any study outputs, scopes, states or raw arrays. Run it before
the final helper hash freeze. Actual report derivation and publication remain
root-coordinated post-closure operations.
