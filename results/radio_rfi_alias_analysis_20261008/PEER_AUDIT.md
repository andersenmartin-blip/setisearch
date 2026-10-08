# Independent retained RFI derivation audit — 8 October 2026

Status: **PASS_RETAINED_DERIVATIONS_ONLY**.

Independently checked the two original case manifests (40 artifact SHA256 hashes and byte lengths), 12 saved maps, all 14 survivor ON winners, 42 original OFF comparison records, 84 truth trajectory rows and 42 global OFF winner compatibility rows. All four CSV files match the JSON evidence and independently derived values. Maximum arithmetic disagreement is 4.46338788151e-08 against an absolute tolerance of 1e-6.

The auditor does not import the root analysis, detector or generator. It uses 45-digit Decimal arithmetic and intersects the reference-frequency intervals required by the two ON endpoints at the injected true slope. All 56 combinations of 14 survivors and four frozen OFF widths have empty intersections, even before restricting reference frequency to the OFF carrier grid. The minimax endpoint distance and reported slope bound agree.

An independent endpoint localization check finds 472 original truth-localized ON hits; all are OFF_MATCHED. The surviving carriers are outside that truth localization.

Saved original OFF scores and exhaustive-family flags were authenticated and transcribed, not recomputed. The incompatibility of the 42 saved global winning OFF paths is only a diagnostic comparison; the original exhaustive compatible-family records remain the source for absence of a veto. The geometry supports the alias interpretation but does not prove a universal physical cause. A/B remain FAIL_CLOSED, with no qualification, draws, new scoring or detector change.
