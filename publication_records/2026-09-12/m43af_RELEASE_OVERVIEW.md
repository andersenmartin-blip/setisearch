# M43AF complete release package

This package contains the exact completed M43AF report, code, diagnostics,
checksums, lossless scientific archive and proposed main README update.
All 502 scientific records pass the independent full-study audit. The frozen
training grid has no feasible model; validation remains unopened.

## Intended public destination

Repository: https://github.com/andersenmartin-blip/setisearch

- Apply the 95 files under `science/` to branch `m43-support-qualification`,
  removing the `science/` prefix from repository paths.
- Apply `main/README.md` as `README.md` on branch `main`.
- Preserve every unrelated file and all existing scientific history.
- Verify current branch heads and merge any intervening changes before committing.
- Verify all remotely published bytes against the supplied SHA256 manifests.

Expected scientific parent: `4a0a180ea1037113fce6b24ea5524eeeca905520`.
Expected main parent: `60bad761f4aa6eebeeef367f7a4123b80fd33e44`.
Original scientific freeze: `75b271b4b92819783692375687586d6df4f40c57`.

The scientific archive has 69 text parts and reconstructs 508 original files:
502 measurement records plus the fixed training grid, immutable failed model
decision, publication receipt, training audit, complete result and full audit.
Native source arrays and the separate six source backups are not included.

The complete release has not yet been published. The current public repository
contains the earlier verified training release and minimal model-publication
receipt. A prepared README or continuation document in this package describes
the intended completed release, and becomes current only when publication is
verified. Do not rerun closed scientific evaluations to reproduce this package.

Read `science/MILESTONE_43AF_RESPONSE_STUDY_RESULT.md` for the complete findings.
Read `science/M43AF_CURRENT_CONTINUATION.md` for restoration and future scope.
`PACKAGE_MANIFEST.json` binds every included payload file. The scientific
release manifest also binds exact repository paths and the proposed README.
