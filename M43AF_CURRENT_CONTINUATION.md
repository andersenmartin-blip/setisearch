# Current M43AF continuation: training complete, publication pending

**10 September 2026. The frozen training stage is complete locally and has no
feasible joint boundary. No GitHub publication completed in this session.**

Read `MILESTONE_43AF_TRAINING_RESULT.md` and the executable protocol. The old
M43AF preparation draft and the public README's earlier running status are
superseded by this local checkpoint, not by an already published result.

## Closed training stage

- Scientific freeze: `75b271b4b92819783692375687586d6df4f40c57`.
- Configuration SHA256:
  `a2c39320fd4e7a4972d989108282a2ac1f5887069c990dcb8df079e5eff7a9a3`.
- All 940 pinned files match; the original 55 focused tests pass.
- Six original sources, 96 anchor arrays, 48 inherited native gathers and the
  full native preflight are exact. All 7,503,600 score values and 432 direct
  zero-translation probes reproduce the published preflight.
- 128 native nulls, 112 injection/control inputs and one reused baseline:
  241 recorded inputs. The nulls and baseline have zero eligible members;
  their absence of conditional profiles is explicit.
- 1,156 training-grid points independently audited; zero feasible points.
  Removing every control costs at least 4 of 57 required signal cases.
  Preserving all 57 leaves at least 8 leaking controls /48.
- All 12,560 profiles and 3,497 member measurements are complete and defined.
  There are 104 distinct training payloads and no prior-payload overlap.
- Model decision seal:
  `e1ef8cfc261a4b155695cc61d3cbda875ca35ff9aef7c8b0cff20b03c48bf7a3`.
- Grid seal:
  `1e4d4e215ebff496620d888ffb8c9810062c169b1af4d664a0302c21e4ec0a2a`.
- Training audit seal:
  `fffcede84d651778480cf58e568207653483fc70107e3dfd1b4f7c86bd0d557e`.

The training archive preserves 244 original files, including all 241 records,
the full grid, model decision and training audit. Restore or verify it with
`scripts/m43af_archive.py restore --stage training` or `verify --stage training`.
Do not rerun closed training or treat repeat executions as new independent
trials. Both validation panels remain unopened. No production detector,
additional sky coverage or astronomical candidate is claimed.

## Operational recovery and incomplete source backup

The initial sparse-mirror recovery was stopped by automatic approval review
because of disk-exhaustion risk. A bounded replacement was tested and then
reproduced all four remaining real sources exactly. It uses approximately
457 MB of ordinary segment files per source, caps each file at 8 MiB, and
enforces a 2 GiB free-space reserve. It never allocates a telescope-sized file.
Six focused recovery tests pass. All scientific code and data identities remain
unchanged; see `M43AF_RUNTIME_RECOVERY.md`.

The active checkout was `/workspace/scratch/c3bc7bf7bbcc/setisearch`, with native
data in sibling `m43af_runtime` and the Python environment in `seti-venv`.
Those temporary paths no longer contain the checkout, environment or native
data. The training checkpoint was recovered with its exact expected SHA256.
The separate `setisearch_M43AF_native_sources.zip` had been built and verified
against all 300 original source files, but its backup is incomplete: only
`.zip.part002` was located after saving; `.zip.part001` and the complete ZIP
are unavailable. Do not promise a restart without redownloading native data.

Restore a checkout at the scientific freeze and the exact Python dependencies,
restore the prior archives, and recover all six original sources with the
bounded helper in a new receipt directory. Rebuild the approximately 5 GiB of
anchors and rerun the native preflight before the historical phase. Restore
closed training from this checkpoint; do not rerun it.

The package's `NATIVE_SOURCE_PARTS.json` retains the original exact hashes and
records the incomplete availability. This native backup is separate from the
proposed GitHub publication.

## Publication status and required next action

The scientific branch was verified at `75b271b4b92819783692375687586d6df4f40c57`
and `main` at `6179b183ac001105df21382e49b4e82874742d5f`. Two attempts to upload
an earlier 21-file recovery checkpoint were rejected by automatic approval
review. The stated reason was insufficient accepted evidence of a user-controlled
destination and user-authored authorization, even after the connected account,
repository ownership and admin/push access were checked. No alternate upload
route was used and no GitHub tree, commit or ref update was confirmed.

The ongoing owner authorization in `PROJECT_DIRECTION.md` remains unchanged.
The current automatic block must nevertheless be resolved with an explicit
approval for the concrete prepared publication package before another GitHub
write. The package's manifest identifies the exact scientific files and the
separate README update. Its destination remains
`andersenmartin-blip/setisearch`, scientific branch `m43-support-qualification`,
with only the README update on `main`. Recheck both remote branch heads before
applying it; preserve concurrent work if either has advanced.

Once publication succeeds, independently fetch the published model-decision
bytes and compare them with the sealed local file. Fetch that commit into the
checkout. Only then create the genuine `model_publication.json` receipt with
the verified commit, `remote_verified=true`, and the model decision seal above.
Do not fabricate this receipt or open a scientific phase merely because a
local package exists.

## Remaining M43AF science after publication

Run the original historical phase with the verified model-publication commit:

```bash
PYTHONPATH=src:scripts python scripts/m43af_response_study.py \
  --runtime-root ../m43af_runtime \
  --freeze 75b271b4b92819783692375687586d6df4f40c57 \
  --phase historical --model-publication VERIFIED_COMMIT
PYTHONPATH=src:scripts python scripts/m43af_study_audit.py \
  --runtime-root ../m43af_runtime
```

There are **261 historical acquisitions remaining**, reusing their original
detector endpoints and exact overlays. Together with the current 241 records,
they form the predefined 502-record no-model branch. Publish its full audit and
lossless complete-stage archive. Do not open the 112 validation inputs or 128
held-out nulls, relax the failed gates, tune on historical diagnoses, or count
a descriptive projection as a recovered detection. No delegation or unattended
work is promised between sessions.
