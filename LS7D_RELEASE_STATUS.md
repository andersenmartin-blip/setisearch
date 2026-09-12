# LS7C sector 32 + LS7D release status

12 September 2026. **Complete locally; public release is blocked.**

The prepared release preserves the completed LS7C sector 32 1,460-trial result
and adds the completed LS7D noise/covariance diagnosis, full numerical records,
analytical tests, scalar audit, figures and continuation documentation. The
main README update is prepared separately from the current public main head.

## Automatic approval rejection

One GitHub `create_blob` attempt for the exact LS7D report was rejected. The
automatic review described the report as derived from local/private research
and said the user had not explicitly authorized that payload's publication to
the public destination. The raw TESS products used by the project are public;
the rejected action would newly disclose the derived report. The repository
was checked as public and owner-controlled, with push permission, before the
attempt. The owner's standing publication authorization remains documented in
PROJECT_DIRECTION.md, but the automatic review did not accept it for this action.

No blob, tree, commit or branch update succeeded during this release attempt.
No alternative GitHub upload mechanism or retry was used after rejection.

## Concrete scope requiring explicit release approval

Publish all files in `setisearch_LS7D_release.zip` intended for the science
branch—**the complete LS7C sector 32 result plus all LS7D code, protocol,
configuration, tests, ledgers, matrices, logs, checksums, figures, reports and
operational notes**—to `andersenmartin-blip/setisearch` on
`m43-support-qualification`, together with its exact README update on `main`.
The archive's `publication_manifest.json` specifies each repository-relative
path, Git blob identity, SHA256, byte count and intended branch.

This is public disclosure of the derived research package. Raw FITS, the
separate LS7C sector 29 development package and the blocked M43AF historical
complete archive are not included. Their prior states remain unchanged.

## Restore and resume

The ZIP contains readable `science/` and `main/` payloads, two Git bundles
relative to the recorded public bases, the exact main README patch and a
manifest covering every intended release file. Verify ZIP integrity and all
payload hashes, then use an isolated checkout. Do not replace newer remote
work with this snapshot.

Last checked science base: `baa514347c8466b78a82689a84ffb5b82f83237d`.
Last checked main base: `33fe843e96325a2f14767e132b17397d63ef1b44`.
Recheck both heads after approval, integrate later work without force-pushing,
publish the science payload before the README, and verify all destination blob
identities. Record the actual public commits and update operational publication
status while preserving this rejection as historical provenance.

The scientific next step is the combined covariance/residual/nuisance
development described in `results_ls7d_noise/REPORT.md`. Existing LS7C and LS7D
numeric outputs are closed; do not rerun or retune them to address publication.
