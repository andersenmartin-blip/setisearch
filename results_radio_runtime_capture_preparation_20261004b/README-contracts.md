# Capture-b preparation contracts and headroom

This directory prepares a new one-shot metadata capture with identity
`e3d5aae494ef041c668a9fbec11edc2ac821a0e27bef15588181d166e125736c`.
The builder never runs the supervisor or collector, opens runtime binaries,
imports native scientific packages, creates an activation marker, or writes to
either capture output root. The original closed capture remains unchanged.

`build_contracts.py` requires a root-supplied final `inputs-ready.json` before
writing the two new contracts and `headroom.json`. Its exact readiness schema is
`radio-runtime-capture-b-inputs-ready-v1`, the new capture identity, status
`FINAL_FOR_CONTRACT_PREPARATION`, six sorted `input_pins` and six sorted
`validation_pins`. Each pin binds an absolute path, bytes, SHA-256 and filesystem
mode. The six inputs are the three final producer files, new completed runtime
preread manifest, new B protocol and unchanged original materialization plan.
The six validation-only artifacts are the final three test sources and their
three final successful producer logs. The builder checks those full bytes but
does not promote them to capture execution dependencies.

The child inventory preserves the original closure: 765 freshly checked current
runtime files plus the three producer files, new B protocol and original plan,
for 770 files. The parent has seven source pins, adding the new child contract
and new preread manifest to those five preparation sources. The child does not
pin its own contract; the supervisor does not pin its own freeze or detached
proof. Preparation scripts and readiness checks are not dispatched dependencies.

The new root must be empty, mode `0700`, device 27 and inode 1575156. The new
activation path is `config/radio_runtime_metadata_capture_20261004b.activate.json`
and must still be absent. Output files use exclusive creation; a rerun cannot
overwrite a contract or rearm a capture. All arithmetic precedes the first
write. Repository inputs are read through held no-follow ancestors, bounded
sole-link regular descriptors, with before/after identities checked.

The published contracts retain 60 seconds and 8 MiB, a 50-second child window,
5-second reap window, 512 MiB address-space limit, 256 MiB joined explicit-read
limit, 1 MiB raw stream limits and at most 1200 proc samples. The entire 140 MiB
child explicit-read reservation remains charged conservatively; it is never
refunded from a smaller observed count. Parent allocation is therefore 116 MiB.
The child result cap is 1,048,575 bytes, leaving one byte for its CLI newline.

The headroom report derives the exact parent two-pass selected inventory and
adds the supervisor CLI freeze, full-body proof and marker, the preliminary
child-contract read and marker re-read. The proof bound includes every selected
source body as base64, fixed-length Git identities and the maximum 2048-scalar
provenance string at twelve escaped ASCII bytes per scalar. The complete proof
must fit the child's 2 MiB witness cap. The child bound adds its contract, plan
and witness CLI reads, two complete selected-file passes and both full 1 MiB
`/proc/self/maps` allowances.

The report distinguishes the producer's 2 MiB admission read slack from its
artifact reserves: 128 KiB group evidence, 512 KiB next-sample and terminal
report reserves, and 64 KiB filesystem accounting slack. The static artifact
bound includes both full raw streams plus their received overflow probe bytes,
both selected inventories, the proof and conservative spent/report space.
Actual allocated blocks and root directory bytes still require the producer's
dynamic checks. A 1200-sample count ceiling does not guarantee that every sample
can consume its maximum individual allowance.

Optional proc reads preserve a terminal floor for the full after-pin pass plus
one EOF/overflow byte and a 16,385-byte final pidfd record. Mandatory reap
observation releases only its own pidfd portion; the terminal regular-file phase
releases the remaining file portion. The unchanged aggregate cap still applies
to every actually received byte. Constructor, successful samples, group partial
failures and terminal raw proc observations remain bounded retained evidence.

`test_contracts.py` exercises readiness/source/log drift, prior identity refusal,
hash-cycle refusal, unchanged plan bytes, inventory totals and modes, finite
joined read and proof caps, bootstrap source cap, unselected distribution bytes,
duplicate/nonfinite JSON, and no-follow/sole-link preparation reads. These are
synthetic preparation tests; no science data, native runtime inventory or live
collector is invoked. The final `contract-tests-05.log` records 23 passing tests.
Earlier successful development logs remain retained. `contract-preparation-01.log`
records the sole exclusive build from final root readiness.

The generated preparation values are:

| Item | Bytes |
| --- | ---: |
| Child contract | 179,265 |
| Supervisor contract | 164,445 |
| Complete source-proof upper bound | 1,045,804 |
| Parent selected inventory, one pass | 54,555,773 |
| Parent selected inventory, two passes | 109,111,546 |
| Parent known explicit-read upper bound, including CLI and EOF allowance | 110,501,843 |
| Remaining parent proc read headroom | 11,132,973 |
| Protected terminal file/pidfd floor | 54,572,159 |
| Child explicit-read upper bound | 111,253,452 |
| Remaining child reserved read headroom | 35,547,188 |
| Conservative fixed logical artifact reservation | 4,124,006 |
| Remaining logical artifact space for bounded samples | 4,264,602 |

The parent headroom covers 45 conservative maximum-size sample units after
constructor and reap allowances. This arithmetic describes an upper bound for
the fixed scope; it does not predict sample size/count or certify future runtime
success. The terminal floor is part of the existing parent allocation and is
already included in the two selected-file passes, not an added charge. The full
child reservation plus parent known bound and retained 2 MiB admission slack is
259,399,635 bytes, below the unchanged 268,435,456-byte joined ceiling.

The generated child contract SHA-256 is
`a3c7f9b85bd57a340f2b585b96e982a056e797bce65fc05284af68d827c9e8d2`;
the supervisor contract SHA-256 is
`b4e38001dde17995c3b43f59254f117a55ff12c85e3a19365908010a148db821`.
`headroom.json` is 3763 bytes with SHA-256
`83556d40141c0420dc559810c773c2e98d6d0b885e5e964a2edf45318cd40826`.

Preparation leaves the engineering subtotal at 970 seconds / 48 MiB and all
11 scientific fields pending. A separately published, fully read back fresh
activation would reserve a further 60 seconds / 8 MiB, yielding 1030 seconds /
56 MiB. Contract preparation itself creates no new live allocation or scientific
authority.
