# Milestone 34 fail-closed diagnostic-tolerance repair

Status: **FROZEN BEFORE THE COMPLETE AUDITS ARE RERUN**.

The initial frozen audit workflow run `32965249217` stopped without publishing
combined results. Milestone 17 completed every gate. Milestone 21 reproduced
the source, tests, detector validation, 30 extracted-slice hashes, and the full
search, then failed in the verification step before an audit summary was
written.

The failing assertion compared every value in `diagnostics_for_on_best`
bit-for-bit. Read-only comparison of the failed search artifact identified one
and only one difference within that structure:

- window: `m21_1425p0`;
- field:
  `acceleration_smearing_by_active_epoch[0].planet_start_m_s`;
- primary: `9956.045436600267` m/s;
- rerun: `9956.045436600265` m/s;
- absolute difference: `1.8189894035458565e-12` m/s.

No candidate list, candidate disposition, or newly exposed cluster count was
queried or used to choose this repair. The failed M21 job was `98166205410`;
its preserved artifact was `9605865243`, with artifact SHA-256
`c4a55cd7bb56075defec3f335b68b8ca2331ebc7cdefa9eebb44092358fb3def`.

## Sole verification repair

Only floating fields inside each
`diagnostics_for_on_best.acceleration_smearing_by_active_epoch` record may now
reproduce with zero relative tolerance and an absolute tolerance of
`1e-9`. All non-floating diagnostic structure remains exact. This tolerance is
roughly 550 times the observed roundoff but only `1e-12` of a 1 km/s velocity;
it has no practical effect on a Hz-scale track.

Every scientific search quantity remains bit-for-bit constrained: extracted
data hashes, hypothesis and cluster counts, maxima, null calibration,
completeness, known-answer recovery, RFI masks, candidate S/N values,
hypotheses, top members, OFF diagnostics, and receiver-frame signatures.
Cap-dependent alias/family annotations retain the already frozen transition
rules.

Both audits must rerun from extraction onward. No artifact from the failed run
may be reused or combined. The unchanged stopping and classification rules in
the original frozen plan continue to govern the result.
