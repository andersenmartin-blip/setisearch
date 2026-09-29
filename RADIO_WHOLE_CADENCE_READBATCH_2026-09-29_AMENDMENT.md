# Prospective readback live02 amendment — canonical reply projection

29 September 2026. This is a **distinct, bounded engineering-only amendment**
after readbatch-live01 closed failed. It does not retry live01 or raise its
943,240-byte reservation. The observed failure and all seven charges remain.

## Single permitted action

After this amendment, corrected code, recipe02, runtime freeze and the live01
result are public and independently read back, `readbatch-live02` may execute
exactly once. It reads a fresh seven-file witness at immutable commit `9086218`;
none of live01's seven archive paths is reused. The exact paths, Git blob hashes,
caps and ordinals are frozen in
`config/radio_whole_cadence_readbatch_recipe02_20260929.json`.

The broker now validates the connector response, removes CR/LF only from the
base64 representation, and projects the durable reply to exactly `content`,
`encoding` and `sha`. Display metadata is discarded before response accounting.
Raw bytes remain protected by the frozen Git blob identity and full equality
check. Missing, duplicate, reordered, partial, malformed, corrupt or over-cap
results still close without retry.

The one action charges seven underlying requests before dispatch, reserves
619,816 response bytes, and has an 80-second engineering elapsed cap, eight-call
ceiling and 1-MiB evidence ceiling. Closure retains a separate 300-second /
24-call / 2-MiB allowance. Mutations are prohibited. Unused reservations do not
transfer to science or any later scope.

The amended Python and Node checks pass together with the 22 retained regression
tests. The broker harness now proves that line breaks and display metadata are
removed from the exact response frame and that partial failure remains explicit
and nonretryable. This is not an estimate of Gaussian/native scientific runtime.

After public readback, execute live02 once and permanently close it. If it passes,
the next scope is a fresh engineering-only Gaussian/compact-score/full-native
physical/recovery/RFI/null freeze. If it fails, preserve the failure and do not
invent another readback sequence within this plan without a new prospective
decision. The 127/24 scientific proposal remains NOT ACTIVATED; all old source,
pointing, holdout, counter, LS and CHEOPS dispositions remain unchanged.
