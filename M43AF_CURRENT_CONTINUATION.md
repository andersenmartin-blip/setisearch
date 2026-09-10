# M43AF continuation

**Read [PROJECT_STATUS.md](PROJECT_STATUS.md) first.** It is the maintained
operational status for the project.

M43AF's failed training decision is already public at
`bdab6b0af39d6bc6c81ce9d5f07ef24c103ca833`. All 261 subsequent historical
diagnostic acquisitions are already completed in the saved complete release:
502 records in total, with a passing independent whole-study audit.

The complete-stage archive is still pending publication. No M43AF scientific
computation remains to be restarted from this checkpoint. The 112 validation
inputs and 128 held-out native nulls remain unopened; no detector is adopted.

## Restore only the evidence needed

The already public training archive restores 244 original files, including
241 training/baseline/null records. It is the input to the completed M43AG
retrospective diagnostic; see PROJECT_STATUS.md before any new work. With the archive-recorded Python 3.12.14 / zlib 1.3.2:

```bash
PYTHONPATH=src:scripts python scripts/m43af_archive.py restore --stage training
PYTHONPATH=src:scripts python scripts/m43af_archive.py verify --stage training
```

The saved `setisearch_M43AF_complete_release.zip` contains 69 complete-stage
archive parts restoring 508 files. A checkout of the currently published
training stage alone does not contain those parts. Obtain and verify the saved
package, or a later verified complete publication, before attempting a
complete-stage restoration.

Native telescope data are unnecessary for publication, archive verification
or the completed training-coordinate diagnostic. Recover them only for a
separately specified native computation.

## Historical records

The previous
[training continuation](https://github.com/andersenmartin-blip/setisearch/blob/4a0a180ea1037113fce6b24ea5524eeeca905520/M43AF_CURRENT_CONTINUATION.md)
is retained in Git history. Its upload-pending and “261 remaining” instructions
are obsolete. Scientific reports, frozen files and sealed manifests retain
their original meaning and hashes.
