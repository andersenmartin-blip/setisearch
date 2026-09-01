# Milestone 37 v0.6.1 physical-disposition continuation plan

Status: **FROZEN AFTER RETENTION, BEFORE PHYSICAL EVIDENCE EVALUATION —
POST-CONTACT CAPACITY-ONLY CONTINUATION; NO SIGNAL OR NULL CLAIM**.

Run 006 has completed immutable ON/OFF retention under the published v0.6.1
capacity amendment. This plan controls the next restartable transition from
`off_retention_complete` to `physical_disposition_complete`. It does not
change the detector score, operational threshold, motion bank, spectral
widths, activity subsets, physical veto definitions or veto precedence.

## Input boundary

- Run ID: `m37-v0p6p1-primary-006`.
- Current journal head: `4e67cea9081156f365dd33e8f0fb58dd421c48496c80031ede99845de8b7e990`.
- Operational threshold: S/N `126.20158386230469`.
- Exact retained inventory: 43,883 ON and 2,160 OFF records across the five
  ordered M37 windows.
- Largest child: 41,640 ON records in `m37_1418p5`.
- Capacity amendment SHA-256:
  `544e6eb0696034b1c10a7665d2f46d8e9767dc3af8be26c59e5d9ca2924c4127`.
- Official cache-run manifest SHA-256:
  `c92798fcea88470bd2ee61f448a7ac6bb46621d16dd58ece4ceee928e7eded41`.
- Official ordered cache inventory SHA-256:
  `50de36cb3c1f6a78f0f81d0c0deda050d6a3e10774543b5227c77c1d96e7a313`.
- Independently reopened cache inventory SHA-256:
  `3bc5e5c745043cb5d738b85a89c9f4e8b5917c842c48f32b83f8e8ee43774c97`.

The large cache payloads were not committed. A deterministic replay is
permitted only if every cache file re-hashes to the official ordered
inventory and replacing only the replay factor-bundle provenance field with
the official Run 006 identity reproduces the official cache-run manifest
byte for byte. Failure of either equality stops the continuation before a
physical child is accepted.

## Unchanged physical decision sequence

Each window is evaluated independently and completely in this order:

1. build receiver-frame signatures from the retained ON members;
2. evaluate the frozen single-adjacent-OFF evidence;
3. match exact same-hypothesis and local-track retained OFF members;
4. apply receiver-frame alias connected components; and
5. seal exactly one final physical disposition for every retained ON member.

The frozen precedence is exact retained OFF, local retained OFF,
single-adjacent OFF, receiver-frame alias, then
`pending_receiver_alias_evaluation`. No record may be truncated and no
threshold may be adapted.

## Amended resource envelope

The v0.6 limits remain unchanged in their original modules. The v0.6.1
adapter admits only the single sealed amendment and applies these ceilings:

| Resource | v0.6.1 ceiling |
|---|---:|
| Retained records per window | 50,000 |
| Receiver or adjacent queries per window | 150,000 |
| OFF or alias bucket entries per window | 150,000 |
| OFF exact candidate visits per window | 125,000,000 |
| Alias identity comparisons per window | 125,000,000 |
| Alias distinct candidate visits per window | 125,000,000 |
| Receiver local-channel visits | 25,000,000 |
| Canonical evidence bytes per window | 480,000,000 |
| Live mapped ndarray bytes | 536,870,912 |
| Complete physical child bytes | 1,953,554,432 |

The receiver local-channel bound is the proportional fivefold continuation of
the frozen v0.6 value. The complete-child bound is derived from four amended
evidence envelopes plus two 16-MiB structural allowances; it changes storage
capacity only.

## Restart and completion rules

- A child is immutable and is reused only after complete receipt reopening.
- The five-window run manifest is published only after all five children pass
  the amended validator in exact window order.
- The journal advances only from that fully reopened manifest and records the
  capacity-amendment identity.
- Any exceeded declared ceiling or identity mismatch stops fail-closed. It
  must not be repaired by truncation, a changed threshold or a changed veto.

This stage can classify physical controls only. Global rank significance and
final scientific outcome assembly remain separate later transitions. Until
both are complete, Run 006 supports neither a technosignature claim nor a
scientific null claim.
