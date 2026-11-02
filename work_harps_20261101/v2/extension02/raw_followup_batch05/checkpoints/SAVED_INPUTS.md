# Batch05 saved original inputs

Both original ESO products in the one selected HD141937 exposure are preserved in [SETI_HARPS_RAW_BATCH05_INPUTS_PART1_2026-11-02.zip](https://chatgpt.com/library?file_id=libfile_c55e501728348191b32e54ec71cd7439&account_id=personal).

- Archive size: **25,499,413 bytes**.
- Archive SHA-256: `1b05cb6852de3239570ca46b85d91de233f090738f03c1e0607c73e0dcbf1fcc`.
- Canonical product bytes: **27,804,441** (one raw FITS.Z and one ancillary TAR).
- [Saved identities and exact member hashes](LIBRARY_INPUTS.json); [packaging inventory](INPUT_ARCHIVES.json).

Extract into staging, verify archive/member SHA-256, then copy only canonical inputs and matching receipts. Member paths beginning `v2/extension02/` are relative to `work_harps_20261101`. Retain current plans/status rather than overwriting with historical copies. Partial/noncanonical files are excluded. Restore the matching merged science FITS from the earlier extension02 input checkpoint when needed. No new observing exposure or telescope time is created by restoration or follow-up.
