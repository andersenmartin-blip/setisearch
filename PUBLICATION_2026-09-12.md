# Verified SETI publication, 12 September 2026

The owner explicitly approved all SETI code, experimental data, reports,
figures and logs for the public repository
`andersenmartin-blip/setisearch`, science branch `m43-support-qualification`,
with README updates on `main`. This completes the previously blocked LS7C,
LS7D and M43AF releases. No scientific evaluation was rerun for publication.

## Preserved payloads

| Payload | Exact identity and scope |
|---|---|
| LS7C sector 32 + LS7D | [fa9f802](https://github.com/andersenmartin-blip/setisearch/commit/fa9f8028287a54d9369abc897c948e640c482c78): 45 science files, including 1,460 closed trials and the 120-link/34-window covariance diagnosis |
| Prepared LS7D main README | [2c6ec5d](https://github.com/andersenmartin-blip/setisearch/commit/2c6ec5d194d28efe8fd72befd99ae865467d6395): exact 46th manifest payload; the current overview also includes completed M43AF publication |
| M43AF complete release | [f41ca8a](https://github.com/andersenmartin-blip/setisearch/commit/f41ca8a4e88ecf64c0cc2b86fbf8c501d940e00f): all 95 science payload files, including 69 archive parts for 508 original files / 502 records |
| Separate LS7C sector 29 development | [Original ZIP and interpretation](archives/ls7c_sector29_development/README.md): 42 package entries, 1,300 retrospective trials, unchanged historical bytes |

The full LS7C/LS7D science tree matches the independently computed prepared
tree `fa2c5f3372a55928ba23f6fed919534f6f9f25fd`. Adding the exact M43AF payload
produces `71480e964fb7d220d60e3c2023326aaa1a629dd7`, also independently matched.
These cryptographic tree checks bind file membership, modes and content.

The LS7D ZIP and all 46 manifest entries passed size, SHA256 and Git-blob checks.
The M43AF ZIP and all 97 package-manifest entries passed size/SHA256 checks;
all 69 parts and the reconstructed archive match their original hashes.
All 508 original M43AF files, including gzip byte identities, were reconstructed
in memory and verified with Python 3.12.14 / zlib 1.3.2. No existing scientific
records were overwritten during verification. The sector 29 archive passed
ZIP integrity, all 41 checksum entries and 1,300-trial ledger accounting.

## Original manifests and historical documentation

- [Complete LS7D original ZIP](publication_records/2026-09-12/setisearch_LS7D_release.zip),
  including original Git bundles and checksums; SHA256
  `29ff270fbd2a13ca9c51544ca727232bd2f1fd0df2d19191d8b430a4da086ac8`.
- [LS7D original publication manifest](publication_records/2026-09-12/ls7d_publication_manifest.json).
- [M43AF original package manifest](publication_records/2026-09-12/m43af_package_manifest.json)
  and [release overview](publication_records/2026-09-12/m43af_RELEASE_OVERVIEW.md).
- [M43AF scientific release manifest](results_m43af_response/complete_release_manifest.json):
  verify its 94 scientific file entries at the exact M43AF release commit above;
  the manifest itself is the 95th science payload.
- Its separate `main_readme` entry describes a historical proposal, preserved
  byte for byte in [the original README](publication_records/2026-09-12/m43af_original_main_README.md).
  It was not applied over the newer concise main overview. The actual main
  update integrates the completed-publication facts into the LS7D overview.

Historical package manifests retain their original base commits and
upload-pending labels. Current continuation files and README have subsequently
been reconciled with the new release, so compare original manifests with their
named payload commits, rather than with current operational document revisions.
The original M43AF ZIP SHA256 is
`82e649f8aa0faffe88d4020cda4eb5fce4cbdcda1a84015cd48774a94f673999`;
the scientific XZ archive SHA256 is
`b66e2a2dbe41d3dda4a63254c4528185e761aae7fdcf4745ef8e3764ca6c9443`.

No failed scientific qualification was changed into a pass. The held-out M43AF
panels remain unopened, no detector is adopted, and no new candidate is promoted.
Resume from [PROJECT_STATUS.md](PROJECT_STATUS.md) and the LS7D development
plan. The separate sector 29 archive must not replace the canonical sector 32
code or result paths.
