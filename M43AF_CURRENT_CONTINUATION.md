# M43AF continuation

**Read [PROJECT_STATUS.md](PROJECT_STATUS.md) first.** It is the maintained
operational status for the project.

M43AF's failed training decision is already public at
`bdab6b0af39d6bc6c81ce9d5f07ef24c103ca833`. All 261 subsequent historical
diagnostic acquisitions are already completed in the saved complete release:
502 records in total, with a passing independent whole-study audit.

The complete-stage archive is now published at `f41ca8a4e88ecf64c0cc2b86fbf8c501d940e00f`.
No M43AF scientific computation remains to be restarted from this checkpoint. The 112 validation
inputs and 128 held-out native nulls remain unopened; no detector is adopted.

## Restore only the evidence needed

The already public training archive restores 244 original files, including
241 training/baseline/null records. It is the input to the completed M43AG and M43AH
retrospective studies; see PROJECT_STATUS.md before any new work. With the archive-recorded Python 3.12.14 / zlib 1.3.2:

```bash
PYTHONPATH=src:scripts python scripts/m43af_archive.py restore --stage training
PYTHONPATH=src:scripts python scripts/m43af_archive.py verify --stage training
```

The 69 complete-stage archive parts are now present on the science branch,
restoring 508 original files including all 502 records. Their byte-identical
reconstruction was verified before publication. Use the current science branch
or the exact complete release commit, not an earlier training-only checkout:

```bash
PYTHONPATH=src:scripts python scripts/m43af_archive.py verify --stage complete
PYTHONPATH=src:scripts python scripts/m43af_archive.py restore --stage complete
```

[Publication record and preserved manifest identities](PUBLICATION_2026-09-12.md).

Native telescope data are unnecessary for publication, archive verification
or the completed training-coordinate studies. Recover them only for a
separately specified native computation.

## Historical records

The previous
[training continuation](https://github.com/andersenmartin-blip/setisearch/blob/4a0a180ea1037113fce6b24ea5524eeeca905520/M43AF_CURRENT_CONTINUATION.md)
is retained in Git history. Its upload-pending and “261 remaining” instructions
are obsolete. Scientific reports, frozen files and sealed manifests retain
their original meaning and hashes.
