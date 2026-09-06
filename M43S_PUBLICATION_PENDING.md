# M43S publication resolved

The complete M43S result package is public in commit
`dbbd430cf350d14a601aeed73949db6c50438469` on `m43-support-qualification`.
Its tree `32f91d4727f86bbee983b5cb51b3a588d408eb80` exactly matches the saved
continuation package, whose 113 artifact checksums were verified.
The main README now links the result report in commit
`6fa615a7a8738f8e4dd3ca40a8b70f1fd7df8d5b`.
No trial reruns or scientific result changes were needed for publication.

The block record below is retained as historical provenance. Its pending status
and restart instructions are superseded by this resolution; do not republish or
rerun the completed M43S package. The next scientific step remains a prospective
isolation-mask comparison with fresh null calibration and paired injections.

---

# M43S complete locally; publication blocked by approval-review context failure

The owner has repeatedly authorized autonomous analysis, publication of results
and logs, and README updates. That authority remains in force and is recorded in
PROJECT_DIRECTION.md. This is not a request for renewed scientific permission.

## Completed result

- Public prospective freeze: `95eeaa74eb0eb52f8c0a782dc9010175d269ba53` on
  `m43-support-qualification` in `andersenmartin-blip/setisearch`.
- Local complete result commit: `c6b388e61e6e12b238b6674d791a733be49d790a`.
- Complete result tree before this status file: `87e00cd17df6f6b0d88f024044ead5127f53cd1b`.
- Result seal: `e47ae9c30c32be355e5022c40ea7e50d8ee3cacf15b983d4bb21a869e2857645`.
- Report: MILESTONE_43S_PROFILE_SENSITIVITY_RESULT.md.
- All 96 new injection runs / 112 endpoints are complete in 556.503 seconds.
- All 10 focused tests and 113 artifact manifest entries pass.
- Retrospective diagnosis replays all four strongest-level misses exactly:
  the original mask removes 31 associated above-threshold cells per case.
- No detector, mask, threshold or original endpoint was altered to improve results.

## Actual upload rejections

The GitHub `create_tree` action for the 107-file, 7,004,651-character result
package was rejected by automatic approval review:

> Automatic approval review failed: Codex ran out of room in the model's context
> window. Start a new thread or clear earlier history before retrying.

After explicitly checking the allowed scientific file inventory, all manifest
hashes, existing publication authority and absence of credential patterns, a
smaller fully reviewable batch was submitted through the same approval control.
That action was also rejected:

> Automatic approval review failed: Error running remote compact task: Codex ran
> out of room in the model's context window. Start a new thread or clear earlier
> history before retrying.

No result tree or branch update was returned as successful. Upload attempts
stopped; do not bypass the approval control. The earlier M43S freeze is public,
but the completed M43S result package and README update are not public yet.

## Concrete restart point

Use a fresh conversation/review context as suggested by the actual error.
First publish the already completed work through the normal approval-reviewed
GitHub connector, then update main. Do not rerun the 96 trials or request the
owner's scientific approval again merely to continue previously authorized work.
If review rejects the upload again, preserve and report the new reason.

Local qualification checkout:
`/workspace/scratch/19793b4e23ff/setisearch`, branch `m43-support-qualification`.

Main README worktree:
`/workspace/scratch/19793b4e23ff/setisearch-main`, branch `m43e-readme`.
Prepared README commit: `b544d33`.
Public main at preparation: `b3f200e55dcec507e2753a958c8b6408957c7aeb`.
After successful result publication, replace its temporary publication-pending
paragraph with a link to the now-public result report and publish the README.

**There are multiple unpublished qualification commits after the freeze.**
Build the complete diff from public `95eeaa74eb0eb52f8c0a782dc9010175d269ba53`
to the current local HEAD. The historical single-commit export helper only
exports HEAD~1..HEAD and would omit the actual result package here.
Do not force-push or move a ref to an incomplete tree. Verify the final uploaded
tree against the complete intended local tree before updating refs.

After publication, the next scientific task is a prospectively frozen
isolation-mask comparison with fresh null calibration and paired M43S injections.
The full 1,701-template bank and broader carrier/profile populations remain
outside the present sensitivity result.
