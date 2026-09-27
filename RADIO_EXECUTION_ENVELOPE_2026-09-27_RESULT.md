# HD 1461 prospective execution envelope — 27 September 2026

**Envelope verification: PASS. Execution status: BLOCKED.** Thirteen new tests
pass. Seven preparation gates are now hash-bound; five scientific/transport gates
remain false. No telescope request was made and no spectral value was opened.

## Integrated envelope

The new `radio-hd1461-execution-envelope-v1` binds the published three-window
identity contract, fresh control freeze, blocked original source contract,
source inventory, runtime manifest, codec evidence, direct-factor evidence and
prospective resource namespace. Its identity is
`4f4fc7f477e1f0617632a314a99d95f719d17943ea294700559be675590593f6`.

| Gate | State | Claim boundary |
| --- | --- | --- |
| Exact calibration/validation/pilot payload identities | Pass | Identity only; 18 decoded payloads and 12 normalization blocks |
| Fresh recovery/RFI/null panel | Pass | Preregistered, not executed |
| Runtime manifest | Pass | Pins the previously qualified runtime versions and current implementation hashes; future execution must match |
| Prospective cumulative resource namespace | Pass | Frozen and empty; not activated |
| Local durable ordered-role controller | Pass | Fsync/atomic compare-and-swap qualification only; no network budget |
| Local codec/receipt path | Pass | Published gzip and bitshuffle/LZ4 fixture evidence only |
| Direct-factor arithmetic | Pass | Arithmetic only, not a physical motion model |
| Same-scan pointing provenance | **Block** | No original header/log or documented file-specific conversion |
| Telescope codec-to-direct receipt handoff | **Block** | No telescope-remote receipt has crossed the direct pipeline |
| Physical motion bank | **Block** | Working eccentric scenario is not a qualified ephemeris/model |
| Numeric cross-window calibration transfer | **Block** | Only identity transitions are qualified |
| Fresh recovery/RFI/null evaluation | **Block** | The 24-case panel remains deliberately unexecuted |

The original preparation-contract SHA-256 remains
`c434c6f0615dfec165512195dcae888d8aa4b33a29efdb5037895ba5530d8bcb`
and remains blocked. It was not rewritten to READY. `neighbor9` remains the
primary and the five false gates cannot be bypassed by the envelope.

## Runtime and codec evidence

The runtime manifest consolidates the exact versions retained by the published
codec and direct-factor qualifications: Python 3.12.14, NumPy 2.3.5, h5py
3.16.0, HDF5 2.0.0, hdf5plugin 7.1.0, Astropy 8.0.1, pyerfa 2.0.1.5 and the
corresponding IERS-data package. Nine relevant implementation files are pinned
by content hash. This is an immutable execution requirement, not a claim that
today's envelope-only process re-executed the codec fixtures.

The codec binding retains the seven previously published local-fixture tests,
including gzip and bitshuffle/LZ4 decode, normalization, receipt validation and
restart. It explicitly records `telescope_codec_receipt_handoff_passed=false`.
No synthetic receipt is relabelled as telescope evidence.

The motion binding similarly retains 38,016 independent factor comparisons and
1,015,344 bit-exact native score cells while keeping
`physical_model_qualified=false` and `source_pointing_resolved=false`.

## New cumulative resource contract

A new namespace, `radio-hd1461-cadence71139-prospective-telescope-v1`, is frozen
with zero reservations:

| Limit | Per role | Cumulative maximum |
| --- | ---: | ---: |
| Requests | 500 | 1,500 |
| Accepted/reserved bytes | 512 MiB | 1.5 GiB |
| Wall-clock allowance | 1,200 s | 3,600 s |

The only permitted order is calibration, validation, pilot, with one full
reservation per role. Reservations are non-refundable after failure or an
uncertain publication. The scientific attempt budget remains three calibration
realizations, one evaluation run over 24 cases, zero post-freeze remedy attempts
and zero pilot runs before every gate passes.

The published synthetic acquisition demonstration remains
`CLOSED_EXHAUSTED_NOT_PARENT_NOT_RESET`; its file hash is pinned. The new
genesis is not its child and does not restore any allowance.

### Discovered integration risk

The old v1 ledger calls the per-session transport validator on the *cumulative*
limit. It therefore cannot represent the legitimate three-session 1.5 GiB
total, even though each 512 MiB role session is individually valid. The new
prospective v2 role-ledger validator separates those two levels, binds role
order and proves that exactly three reservations exhaust the cumulative limits;
a fourth is refused. A new local file-backed controller additionally passes
fsync/atomic compare-and-swap, wrong-role, stale-parent and publication-ambiguity
tests. If a publication lands but its response is lost, the reservation remains
spent and an old-parent retry is refused. It returns no transport budget.
The telescope namespace remains `FROZEN_NOT_ACTIVATED`; this is not a GitHub or
production-store activation.

## Verification and continuation

Thirteen tests cover independent input pins, evidence hashes, runtime/codec
claim separation, empty-genesis integrity, non-reset of the old ledger,
three-role exhaustion, fourth-session refusal, scientific attempt caps, the v1
cumulative-limit incompatibility, fsynced local reservation, wrong-role and
stale-parent refusal, spent ambiguous publication, exact blocker retention,
tamper rejection and absence of spectral/candidate authority. Closed science
panels and the old acquisition demonstration were not rerun.

**Exact next autonomous engineering work:** specify and test a fail-closed
codec-to-direct receipt adapter using only the published local-fixture identity
and normalization semantics; do not create a telescope receipt. Separately pin
the v2 publication-store protocol without activating its empty namespace. Actual
telescope handoff, physical motion-bank adoption, numeric cross-window transfer
and panel execution stay blocked by the five gates above; pointing still needs
the same-scan original record or documented conversion.

M43AI, the original 112+128 M43AF holdouts, M15 GJ581, M33 HD3651, LS8BF and
CHEOPS remain untouched. The two-week plan is not extended.

## Reproduction

```sh
PYTHONPATH=src:scripts python scripts/radio_execution_envelope_qualification.py
sha256sum -c RESULTS_MANIFEST_RADIO_EXECUTION_ENVELOPE_2026-09-27.sha256
```

See [result.json](results_radio_execution_envelope_2026-09-27/result.json),
[execution_envelope.json](results_radio_execution_envelope_2026-09-27/execution_envelope.json),
[resource_contract.json](results_radio_execution_envelope_2026-09-27/resource_contract.json)
and [resource_ledger_genesis.json](results_radio_execution_envelope_2026-09-27/resource_ledger_genesis.json).
