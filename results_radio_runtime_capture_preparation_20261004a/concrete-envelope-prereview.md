# Read-only prospective envelope review — superseded draft

This is the root's retained transcription of the gate implementer's additional
read-only review. It reviewed collector contract SHA256
b7746d06cc2ad006b6746db597d5e8504924e6003d4eec7c252714971f3e8055 and
supervisor SHA256
6e17e817c13760f66a8ebdb0b47208f1d6303bbd8db74d05a9fb04e1b0be7b2f,
before the protocol's storage/terminal scope clarification. Those exact drafts
are retained under superseded-contract-draft-01. It is not the final independent
concrete review or an actual capture result.

No blocker found in the concrete prospective specs.

Both child file-observation passes serialize to 510,746 bytes, leaving about
538 KB within the 1 MiB result limit. The publication witness is comfortably
below its 2 MiB cap. Known parent reads leave 13,058,178 bytes for startup and
procfs observations; the child's known reads fit its 140 MiB reservation.

Identity, plan, interpreter, import prohibition, source-contract hash, and
directory bindings agree. Unexpectedly large maps, output, or procfs
observations may still cause proper terminal failure. Final CLI serialization
and provider termination must remain explicitly outside the retained
final_scope claim. No capture or tests were run.

The later clarification adds 426 protocol bytes, increasing known two-pass
parent content reads by 852 bytes. Root pure validation passed for the new
contracts; the final independent concrete review records their actual hashes.
