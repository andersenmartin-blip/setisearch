# LS7D continuation and experiment identities

12 September 2026. LS7D is completed retrospective noise accounting, based on
the completed LS7C **sector 32** challenge. Resume from the saved results and
the [report's next experiment](results_ls7d_noise/REPORT.md), not by repeating
the 1,460 LS7C injections or opening another sector.

## Canonical chain

- Public LS7B result base: `10a8e36bcb938e63e94e01c6c02bed81dd17f00b`.
- Public LS7C sector 32 method freeze: `baa514347c8466b78a82689a84ffb5b82f83237d`.
- Preserved local LS7C sector 32 result: `9955f7fd4f7bc99db49daa96c8b1c91c8af3102d`.
- Local LS7D diagnostic freeze: `13ab25a` (full identity in `results_ls7d_noise/summary.json`).

LS7D checks the original LS7C scientific and result manifests. Its 120 trial
links point only to the sector 32 nominal matched-signal records. The 34 unique
windows share ten backgrounds. No threshold or acceptance decision changes.
The new result identifies a covariance limitation but does not qualify a model.

## Prevent the historical LS7C name collision

A separate saved package, `setisearch_LS7C_results.zip`, contains a **sector 29
retrospective development** experiment with **1,300 trials**, locally frozen
at `27709b72be76f260be10f3d85239eddef575937a`. Its source base is LS7B, not the
public sector 32 freeze. Automatic review previously blocked that package's
publication; this continuation does not publish or overwrite its contents.

The sector 29 development package and the **1,460-trial sector 32 challenge**
are different experiments despite using the same historical LS7C filenames.
Keep that package intact and refer to it as “LS7C sector 29 development” when
discussing it. Never extract it over the canonical sector 32 paths, replace
the sector 32 `light_sail_tess_v3.py` with its version, or combine the denominators.
If the sector 29 supplement is released later, use an isolated archival path
with its original byte identities and explicit retrospective provenance.

## Scope of the present release

Publish the preserved LS7C sector 32 result and LS7D code, protocol, numerical
ledgers, audit, figures, report and operational documentation to
`andersenmartin-blip/setisearch` on `m43-support-qualification`, with a concise
README update on `main`, under the owner's standing publication authorization.
Raw FITS stay in the source cache; their exact public identifiers and hashes
are in the source manifest. The separate historical M43AF complete-archive
block is unchanged and is not part of this release.

Recheck current branch heads before publication, use a normal fast-forward,
and verify the destination Git blob identities against every intended file.
Record the actual remote commits in release status. A local commit message
containing “publish” is not evidence that its branch was updated remotely.

Current release is blocked by automatic review; [exact scope and restart](LS7D_RELEASE_STATUS.md).
