# Milestone 37 v0.6.1 significance and outcome continuation plan

Status: **FROZEN AFTER PHYSICAL DISPOSITION, BEFORE RANK-P EVALUATION —
POST-CONTACT CAPACITY-ONLY CONTINUATION; NO SIGNAL OR NULL CLAIM**.

Run 006 has completed immutable five-window physical disposition under the
published v0.6.1 capacity amendment. This plan controls the two remaining
adjudication transitions from `physical_disposition_complete` through
`significance_complete` to `outcome_complete`. It changes no score, threshold,
null vector, scientific p ceiling, veto definition, veto precedence or final
outcome vocabulary.

## Input boundary

- Run ID: `m37-v0p6p1-primary-006`.
- Current journal head:
  `4cf7067a8f0059ada3458bd1115fb1a4fef26f586828aba27ad359e602d01a7f`.
- Physical-disposition manifest file SHA-256:
  `602a36eaff509c463275a4ab3dda79663ee4eeb40ca01b4ce3fe0d7777cb3bb5`.
- Physical-disposition manifest SHA-256:
  `521de85e946c514e179fbb9bb530cd7031b0aadab4eb9c36297ed508382aeeda`.
- Physical child inventory SHA-256:
  `bdb4553ba41bc509159c1e83c6abd107039b0d2a8b70e936d15f06ab3f83a738`.
- Threshold certificate SHA-256:
  `d65048bd962a247a3763eb58c9cad530d9f7db06586f52a01a34e03b4ba0ad71`.
- Global-null maxima SHA-256:
  `9f1ced12ece55f149a0f3331a69f11450ef4235b0d23272c38f1b268441bd3d1`.
- Operational threshold: S/N `126.20158386230469`.
- Exact retained and physically disposed inventory: 43,883 ON records.
- Capacity amendment SHA-256:
  `544e6eb0696034b1c10a7665d2f46d8e9767dc3af8be26c59e5d9ca2924c4127`.

Every physical child must be reopened against its independent file and
certificate receipts. Every retained ON artifact and the adopted global-null
artifact must likewise reproduce their committed receipts before rank-p is
evaluated.

## Completed physical distribution

| Window | Exact OFF | Local OFF | Adjacent OFF | Receiver alias | Unvetoed |
|---|---:|---:|---:|---:|---:|
| `m37_1400p5` | 1,115 | 548 | 137 | 0 | 0 |
| `m37_1406p5` | 75 | 61 | 82 | 0 | 0 |
| `m37_1412p5` | 128 | 93 | 4 | 0 | 0 |
| `m37_1418p5` | 0 | 0 | 41,640 | 0 | 0 |
| `m37_1425p0` | 0 | 0 | 0 | 0 | 0 |
| **Total** | **1,318** | **702** | **41,863** | **0** | **0** |

These are physical-control results only. The absence of an unvetoed member
does not bypass the independently required complete significance product or
authorize an outcome before the exact five-window join.

## Frozen significance rule

For every original retained ON record, independently of its physical
disposition:

1. count global-null maxima satisfying `null_maximum_snr >= retained_on_snr`;
2. compute inclusive rank-p as `(1 + exceedances) / (256 + 1)`;
3. mark scientific eligibility only when rank-p is at most the frozen
   empirical-p ceiling; and
4. bind the evidence item to the exact retained-record SHA-256.

Evidence remains sorted by lowercase record ID and covers every input exactly
once. No physically vetoed member may be removed before this calculation.

## Frozen five-window join

The outcome join consumes, in exact `M37_WINDOW_IDS` order, independently
trusted receiver-alias results, significance results and ON-retention
certificate receipts. It joins only on the exact retained `record_id`,
reconstructs and re-hashes the retained record from the physical annotation,
and requires identical record inventories on both branches.

Physical vetoes retain precedence. An unvetoed record becomes
`scientific_candidate_unresolved` only when its inclusive rank-p is eligible;
otherwise it becomes `retained_but_not_scientifically_eligible`. The global
outcome is open if and only if at least one unresolved scientific candidate
remains.

## Capacity-only continuation

The original v0.6 entry points remain limited to 10,000 records and 96,000,000
canonical evidence bytes per window. The v0.6.1 adapters admit only the sealed
amendment and use:

| Resource | v0.6.1 ceiling |
|---|---:|
| Records per window | 50,000 |
| Record canonical bytes | 6,144 |
| Significance/branch canonical bytes per window | 480,000,000 |
| Outcome records across five windows | 250,000 |
| Outcome-record canonical bytes | 2,400,000,000 |
| Single compressed output file | 475,000,000 |

Any missing record, changed receipt, exceeded ceiling, noncanonical artifact
or disagreement between retention, physical and significance identities stops
fail-closed. Truncation, threshold adaptation and veto reinterpretation remain
forbidden.

Only a fully reopened significance manifest may advance the journal to
`significance_complete`. Only a fully reopened five-window outcome may advance
it to `outcome_complete`. Until both transitions succeed, Run 006 supports
neither a technosignature claim nor a scientific null claim.
