# Read-only audit after the closed parent integration failure

The one permitted `integration01` has CLOSED FAILED at the cumulative full-history
journal bound, with 19 committed physical checkpoints. Its small failure footer
and parent FAILED event were retained. Do not rerun, resume, extend its cap or
relabel its outcome. This supplement changes none of that scope's requirements.

Perform one read-only audit of its retained files. Before the audit, inventory
every closed file by exact size/hash, pin the existing history codec and audit
script, and save the expected journal head and physical checkpoint anchor from
the terminal failure record. Block consumption, journal publication, physical
writers, RNG and native computation entry points during the audit.

Verify the exact registered parent archive, restore the 19 committed views against
the original 22-view schedule, and explicitly count every physical part not yet
referenced by a committed checkpoint. Verify all original journal revisions,
then use the already-existing read-only `whole_cadence_history_radio.py` format
to encode and restore the same complete history byte for byte. Retain every old
full revision unchanged. This representation comparison authorizes neither a
writable incremental store nor renewed execution.

Limits: 60 seconds, 512 MiB RSS, 8 MiB encoded history, 32 MiB decoded history and
8 MiB new audit output. Preserve all actual results and stdout. The package's
previously fixed publication limits still apply to the combined delivery.
Report this read-only result separately from the failed live storage integration.
