# Native-v2 broker accounting and bounded failure closure

30 September 2026. **PASS for deterministic component regression. Complete
native execution and scientific admission remain unqualified.** No native case,
case reservation, RNG draw, receiver computation or telescope read was entered.

The separately published [live02 transport probe](RADIO_NATIVE_V2_BROKER_LIVE02_2026-09-30_RESULT.md)
passed. This work did not repeat it or mutate either shared live-probe namespace.

## Changes for future execution

- Reserve finite operation reply capacity before dispatch. Lost replies retain
  their unknown charge; returned replies settle to exact canonical JSON length.
  Oversized replies and post-call RSS growth stop before the next operation.
- Retain failed publishers in cumulative usage: spent calls/requests, known and
  unknown reply bytes, ambiguity and conservative stored-file charges persist.
- Seal exactly registered interrupted physical prefixes as incomplete using the
  existing reserved allowance. FAILED parents and incomplete physical evidence
  pack/restore without a completion claim. Broken leases or unregistered writes
  cannot enter this path.
- Measure failure closure from before writer closure/inspection through reserved
  writes and terminal journal response. A late returned response raises and
  permanently stops; already-written failure evidence remains. External blocking
  operations still need deadlines in the complete adapter/runner.
- Preserve an existing exact outer footer if failure occurs after registration;
  close the parent FAILED and retain the later full error hash in its reason.
  Refresh failed physical-close receipts so closed/poisoned state is current.
- Bound journal reasons at 4,096 canonical JSON bytes, including escaping. Full
  original text hashes remain in footers. Successful descriptions stay in their
  hashed footer and use empty journal reasons, preserving last-failure margin.

The new bundle freeze pins `radio-native-v2-inline-broker-accounting-v2` and all
reply reservations. Old freezes cannot silently become authority for changed
execution. Historical archive formats, source bytes, outcomes and pins are intact.

## Count and byte evidence

| Eight-case model | Peak revision | Revision limit | Journal incl. reserves | Limit |
|---|---:|---:|---:|---:|
| Completed | 125,548 | 131,072 | 789,981 | 8,388,608 |
| Last case failed with maximum reason | 129,639 | 131,072 | 789,981 | 8,388,608 |

Both models have 168 events and 340 journal files under the existing 48-file,
eight-checkpoint configuration. These receipt/count bounds do not measure a full
native run, compression or runtime. Response counts cover canonical injected
protocol objects; complete external tool/Git envelopes remain to be integrated.

**159 Python tests pass** across broker, physical-case/parent, archive, v2 physical
evidence, event store and journal. Six offline host tests check independent UTF-8
sizes, standard ECMAScript without TextEncoder/Buffer, one-shot ordering and
conflict/ack/corruption/time stops. The final logs and exact code/model pins are in
`results_radio_native_v2_broker_accounting_2026-09-30/`.
An earlier nonexistent-module invocation and the earlier 155-test pass before
closure changes are retained separately; the 159-test log is authoritative.

A zero-call local host preparation error is retained under
`results_radio_native_v2_broker_host_2026-09-30/preparation01/`. It is explicitly
distinct from the canonical live01 result and consumed no live scope. The generic
host executor is offline evidence and was never invoked on live02.

## Exact continuation

Integrate these revised components and the qualified live adapter into the complete
fresh render/threshold/physical/evaluate runner. Preserve raw receipts before
accounting, enforce operation deadlines, charge actual Git fetch/grouped cat-file
and whole transport envelopes, and stop after the first failed/ambiguous case.
Publish and independently read back a new complete runner+broker executable and
runtime freeze before any separate eight-case reservation or RNG. Neither the
prepare-only freeze nor this component record is executable authority.

127/24 is **NOT ACTIVATED**. HD189733/85030 is selected, HD1461/71139 is on
pointing-provenance HOLD and GJ724/73005 is reserve. Spectra and old holdouts
remain unopened; all failures/spent identities persist, LS is paused and CHEOPS
UNSENT. Consolidate 9 October without extending scope. No external message.
