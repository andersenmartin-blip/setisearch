# Native-v2 shared transport contract: bounded, execution still closed

1 October 2026. A new versioned contract joins the portable caller's complete
visible transcript to the local host's durable publication evidence without
hiding polls, final-delivery custody or caller memory. **171 Python and 98
JavaScript native-v2 tests pass.** This is engineering component evidence only.
No case reservation, RNG, score, telescope value or external message occurred.

## Exact accounting correction

The public live04 control remains a valid small transport component. Read-only
validation reconstructs all 31 visible SDK calls, four conservative Git process
charges, 17 idle polls, six connectors and six deliveries. Its caller-only tail
(the poll replies plus final delivery acknowledgement) would be 9,382 canonical
bytes across 18 records. That tail was not independently persisted during
live04, and caller-runtime RSS was not measured, so live04 is correctly refused
as execution authority.

The previous 57-call structural estimate omitted actual polls and was therefore
not an actual full-size result. Replacing live04's one source read with the 39
maximum-size reads while retaining its 17 polls and adding one caller-tail
custody call requires **74 calls**, above the unchanged 64-call case cap. This
is a deterministic extrapolation, not a new transport measurement.

The corrected prospective runner split reserves, before start:

| Scope | Caller | Git | Tail | Total |
| --- | ---: | ---: | ---: | ---: |
| One zero-poll maximum-size case | 52 | 4 | 1 | 57 / 64 |
| Eight zero-poll cases | 416 | 32 | 8 | 456 / 512 |

The caller itself may use at most 59 calls, 40 MiB request bytes and
63.75 MiB response bytes. A distinct final tail operation reserves one call,
8 MiB request bytes and 256 KiB response bytes, preserving the original
64-call, 48-MiB request and 64-MiB response limits. This leaves at most seven
poll calls per case; the append-only run ledger also enforces 512 calls and the
original cumulative byte/time ceilings across exactly eight ordered cases.

The portable courier now supports a prospectively pinned 30-second supporting
wait, instead of only the historical 10-second wait. Unit tests verify its
exact arguments and unchanged allocations. This may reduce polling but is not
claimed to do so until a fresh actual measurement exists. Any eighth poll,
unknown reply, changed envelope, missing tail readback, RSS above 512 MiB,
out-of-order case or cumulative overflow permanently stops without retry.

## Custody and remaining blocker

Large source-read replies are not copied into the final tail. They remain
reconstructible from the pinned request source and host descriptors, while the
host retains connector, startup and preceding-delivery custody. The separate
tail contains only raw poll envelopes and the final delivery acknowledgement,
with exact byte/hash/readback proof. The controller cannot self-certify that
last acknowledgement.

The code does not yet claim that a production launcher has performed this tail
write or measured the outer caller's RSS. Consequently every execution,
reservation, RNG, restart and transport-integration authority flag remains
false.

**Exact continuation:** integrate the caller-only tail saver and shared
transcript receipt into the runner/launcher, reserve the reduced caller caps
before startup, and run one fresh maximum-size no-RNG transport control with
actual caller RSS, host custody, storage and immutable public readback. If and
only if it fits, freeze and independently read back the complete executable
runner+transport runtime. A separate irrevocable eight-case reservation must
still precede any RNG.

HD189733/85030 remains selected; HD1461/71139 stays on pointing-provenance
HOLD; GJ724/73005 remains reserve. Spectra and old holdouts remain unopened,
LS is paused, CHEOPS is UNSENT, and consolidation remains 9 October without
extension.

Evidence: `results_radio_native_v2_transport_contract_2026-10-01/`.
