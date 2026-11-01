# Restore the extension02 raw follow-up inputs

Extract both `SETI_HARPS_EXTENSION02_RAW_INPUTS_PART*_2026-11-01.zip` archives into `work_harps_20261101`. Archive members retain project-relative paths beginning with `v2/extension02/raw_followup/` and the paths of supporting frozen inputs. The previously created two `SETI_HARPS_EXTENSION02_INPUTS_PART*` archives provide the separate 100 one-dimensional science spectra.

The raw checkpoint includes every downloaded raw detector and ancillary TAR product, all selected product receipts, frozen selection and code, and the completed acquisition manifest. Shared metadata are repeated identically in both parts. Failed jobs, if any, remain explicit in the manifest and checkpoint index; they are not replaced by other observations.

Check each archive's SHA256 against `RAW_INPUT_CHECKPOINTS.json`, then verify every extracted member's byte length and SHA256. For scientific work, respect the original acquisition and follow-up freezes and use an isolated rerun directory; restoring inputs does not authorize overwriting existing analysis products. The checkpoint packager does not interpret scientific array values.

Three unexpected partial-file prefixes (4 MiB total) are preserved once, in part 1, under `diagnostics/stale_partial_files/`, with `PARTIAL_FILE_ANOMALY.json`. Their cause is unknown. They are excluded diagnostic evidence and must never be substituted for the verified raw/TAR products. The acquisition manifest records 210,108,924 bytes; the checkpoint does not claim that ledger explains the extra filesystem entries.
