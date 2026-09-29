# Radio pilot readiness — blocked route and exact restart conditions

29 September 2026. Evidence checkpoint:
`107bbff9462c199795f14b83839ae88ba54f770d`.

**Decision: the present execution route cannot yet admit the scientific 127/24
validation or the telescope pilot.** The selected HD189733/85030 spectra remain
unopened. This is a resource/readiness review of retained evidence, not a new
experimental failure or a completed search. The two-week plan still ends on
9 October; no candidate or sensitivity result is available from its new pilot.

The owner has reported a sharply reduced compute-credit budget and asked work
to continue. This package makes the blocking evidence and restart sequence
explicit without launching another engineering branch, consuming fresh
experimental identities, or changing any scientific threshold or resource cap.
It supersedes the earlier impression that remote publication is the only step
between the successful storage fixture and the pilot. It does not cancel the
plan or change any scheduled task.

## What the existing measurements actually establish

| Evidence | Observed result | Consequence for readiness |
|---|---|---|
| Native broad ON engineering case | 224.702 s before receipt failure; 9,792 retained ON members | Final recovery, receiver aliases and clustering are unmeasured. It met its own 240-s engineering cap, but does not qualify the proposed 80-s scientific cap. |
| Four engineering noise references | Four complete EMPTY maxima | The smallest possible inclusive rank is 1/5. They cannot qualify the fixed 1/100 cut or replace 127 actual references. |
| Complete local storage fixture | 50.187854 s storage/closure; 17,425,035 case bytes; 263,734 journal bytes | This preserves a partial failed physical report under a 24-MiB engineering case allocation. The scientific evaluation allocation is 18 MiB. |
| Scientific phase reservations | 127 × 40 s + 24 × 80 s + 200 s = 7,200 s; all byte reservations total 1 GiB | No unallocated time/byte reserve is created by the storage pass. All per-case and phase bounds still apply. |

The historical native duration is **2.808775 times** the proposed scientific
evaluation time allocation. This is a warning from a different, failed workload,
not a proof that a corrected implementation cannot fit. Likewise, the local
case leaves **1,449,333 bytes** below 18 MiB arithmetically, but the missing native
receiver/alias/cluster and transport evidence have not been measured. It is not
a demonstrated capacity margin. The separately allocated journal is not charged
again to that case comparison.

Do not add the two timing measurements, multiply this one storage workload by
151, infer a general runtime bound, or reinterpret either historical disposition.
The original failure, later receipt correction and storage PASS all remain as
published. A storage PASS is not a recovery, interference or null-control PASS.

## Bounded continuation

The next substantive engineering deliverable must establish **complete native
physical execution and its resource feasibility**, using the existing receipt
repair and evidence formats. Remote publication remains necessary, but an isolated
transport success cannot settle this missing result. Do not spend the scarce
remaining budget on another sequence of standalone storage demonstrations.

Before any new live engineering experiment, pin one fixed scope, current code and
runtime, full evidence obligations, fresh identities, stage timings and bounded
failure handling; publish and independently verify it. Existing closed cases,
including the three unentered but spent identities, cannot be replayed. Preserve
all final members and losses; do not tune signals, the bank, thresholds or gates
to historical failures, and do not raise historical or scientific limits.

Actual scientific activation still requires, in order:

1. Complete native physical/recovery/RFI/null engineering evidence and integrated
   remote publication/readback, with measured compliance with the scientific
   per-case, journal, failure, runtime and total limits.
2. A separate published executable scientific freeze and fresh allocation for
   the unchanged 127-reference/24-evaluation proposal. Engineering reference
   counts and software test counts cannot replace that experiment.
3. A passing fixed scientific gate, followed by the separately frozen integrated
   telescope source/acquisition/trial protocol. A synthetic pass alone does not
   authorize reading the selected telescope spectra.

If a future bounded qualification fails, retain its outcome and follow its stop
rule. Do not automatically generate successive corrective live scopes. At the
2 October review, assess actual admission evidence; at 9 October, publish either
the completed bounded pilot or a blocked-route report with these exact missing
observations. Credit availability is not a reason to lower scientific standards
or extend the calendar silently.

## Reproducible review and preserved state

`python scripts/radio_readiness_review_20260929.py` reads six immutable Git blobs
at the evidence checkpoint and emits the accompanying
[`result.json`](results_radio_readiness_2026-09-29/result.json). It imports no
project experiment code and performs no random generation, native scoring,
physical reevaluation, telescope access or allocation. It verifies each Git blob
identity and records its SHA256. The numerical comparisons come directly from
the saved results and frozen phase-budget document. This is an audit utility,
not an executable scientific admission gate; no new software test count is
claimed.

HD1461 remains on HOLD; GJ724 remains the reserve. The primary neighbor9 rule,
all original counters, failures and held-out values, LS pause and CHEOPS UNSENT
remain unchanged. No messages, delegation, telescope booking or paid service.
No claim is made that the project is running between active sessions.
