# Cross-window calibration contract and fresh control freeze — 26 September 2026

**Identity contract: PASS. Numeric calibration transfer: NOT QUALIFIED. Fresh
control panel: FROZEN, NOT EXECUTABLE.** No telescope values were opened and no
source request was made.

## Three exact window identities

The new `radio-cross-window-calibration-contract-v1` binds the complete decoded
payload identities proposed in the motion audit. Each role has six source URLs,
16 exact time/feed/frequency chunk coordinates per source and four independent
4096-channel normalization blocks. The 18 decoded payload identities and 12
normalization blocks are pairwise separated by role.

| Role | Archive chunk | Native interval | Frequency interval (Hz) | Window identity |
| --- | ---: | --- | --- | --- |
| Calibration | 150 | 157802496–157818880 | 1478773560.349–1478820014.402 | `b97b750a…f40808` |
| Validation | 151 | 158851072–158867456 | 1475800319.517–1475846773.569 | `6db7f2db…409a7` |
| Pilot | 152 | 159899648–159916032 | 1472827078.684–1472873532.737 | `b6934036…7f24f` |

The complete contract identity is
`9297c5f244bd6448fba9bf23f35a9c268ca8ed4725c7ecfae6d2ddb7a871cf97`.
It preserves the original blocked source-contract identity
`c434c6f0615dfec165512195dcae888d8aa4b33a29efdb5037895ba5530d8bcb`;
it does not rewrite that preparation contract as ready.

An exact-context calibration certificate validates only against its source
window and context. A request using it as the validation certificate is
refused. The contract also refuses identical source/destination contexts,
payload-coordinate crossing and a calibration-to-pilot shortcut. A separate
calibration-to-validation request can be identity-bound, but it remains
unauthorized. Its eight explicit blockers include pointing provenance, a
qualified motion bank, positive codec and runtime receipts, the cumulative
resource ledger, the fresh panel, lack of independent observing realizations
and numeric cross-window qualification.

## Fresh prospective control freeze

The failed direct-downstream panel remains closed development evidence and was
not rerun. Its thresholds, widths and outcomes were not altered into a pass.
Instead, a new unexecuted freeze has 27 disjoint identity namespaces: three
calibration realizations and 24 evaluation cases.

The evaluation inventory is fixed before any new outcome:

- two noise nulls;
- ten finite-exposure ON-signal cases covering widths 1, 5, 33, 65 and 129 at
  total digital powers 100 and 500;
- the same ten-cell factorial bank as matched ON/OFF controls; and
- two single-adjacent-OFF controls at widths 65 and 129.

The values are digital engineering units, not flux or EIRP. Every final member
must be retained, classified as associated or unassociated and assigned to
exactly one complete cluster. Noise requires zero final members and clusters.
Matched and single-adjacent RFI cases require zero associated and zero
unassociated final members/clusters. In addition, detector widths 65 and 129
each have explicit zero gates for unassociated final members and clusters, so
the previously observed broad-width leakage cannot be hidden inside an
aggregate count. ON-signal cases require at least one associated final member
and cluster; their unassociated counts must be reported but are not silently
used as a recovery pass criterion.

The freeze identity is
`80d3df727d40fc9fd6a440fc59dac5f7f3a49ef446f28ee455e9347840f7275e`.
The prospective budget is one evaluation run across the 24 cases, three
calibration realizations, zero post-freeze remedy attempts and zero pilot runs.
It is not executable while its six external evidence slots remain unresolved.

## Verification and claim boundary

Thirteen new tests pass: eight for window/receipt identity and transition
rejection, and five for factorial coverage, disjoint identities, complete
accounting, broad-width gates, tamper rejection and access denial. Four explicit
negative controls are retained in `rejection_evidence.json`. The closed direct
downstream panel and synthetic acquisition ledger were not rerun or reset.

This package qualifies the identity and preregistration boundary only. It does
not qualify a threshold transfer, physical orbit, false-alarm tail, recovery
performance or telescope codec. Adjacent spectral windows are disjoint decoded
payloads, but they are not independent observing realizations. The source
remains `HOLD_POINTING_PROVENANCE_UNRESOLVED`; the three ON-coordinate mismatch
is unchanged. `neighbor9` remains primary and no candidate authority exists.

**Exact continuation:** bind the frozen panel into a prospective execution
envelope containing a positive codec/receipt contract, immutable runtime
manifest, qualified motion-bank identity and cumulative resource ledger. Keep
the panel unexecuted until those items and same-scan pointing provenance are
available; then cross-window calibration still needs its own numeric
qualification before validation, and pilot remains last.

M43AI, the original 112+128 M43AF holdouts, M15 GJ581, M33 HD3651, LS8BF and
CHEOPS remain untouched. The two-week plan is not extended.

## Reproduction

```sh
PYTHONPATH=src:scripts python scripts/radio_cross_window_qualification.py
sha256sum -c RESULTS_MANIFEST_RADIO_CROSS_WINDOW_2026-09-26.sha256
```

See [result.json](results_radio_cross_window_2026-09-26/result.json),
[contract.json](results_radio_cross_window_2026-09-26/contract.json),
[control_freeze.json](results_radio_cross_window_2026-09-26/control_freeze.json),
[prepared_request.json](results_radio_cross_window_2026-09-26/prepared_request.json)
and the complete qualification log.
