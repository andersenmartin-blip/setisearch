# Milestone 15 candidate investigation

**Status: ONE RFI/INSTRUMENTAL; ONE UNRESOLVED — INDEPENDENT CADENCE REQUIRED**

Milestone 15 reported two 1406 MHz clusters that exceeded the frozen global
threshold but had only arithmetic-frequency-family triage flags. This labelled
post-hoc investigation applies the protocol fixed in
`MILESTONE_15_CANDIDATE_INVESTIGATION_PLAN.md`; it does not alter or rerun the
held-out detector.

## Reproducibility record

- GitHub Actions run: `32505373627`
- Artifact: `9455107249` (`milestone-15-candidate-investigation`)
- Artifact digest:
  `sha256:a40a364a3121e155ac70d167eb100edc4b9282e0bd0ee32ee8111a76b10b3cdc`
- Scope: six frozen cadence scans, plus/minus 100 Hz around each candidate,
  with a bounded free-drift diagnostic over plus/minus 2 Hz/s
- Receiver-frame coincidence tolerance: 20 Hz
- Adjacent-OFF candidate-track floor: S/N 5.5

The artifact manifest verifies all five investigation outputs. The detector
tests and all frozen-input hash checks passed before the targeted cutouts were
examined.

## Dispositions

| # | Planet-frame frequency (MHz) | Frozen S/N | Post-hoc disposition | Decisive evidence |
|---:|---:|---:|---|---|
| 1 | 1406.118344073 | 16.246 | RFI or instrumental | Epoch-1 OFF peak is 17.013 Hz from the ON peak, within the fixed 20 Hz tolerance. |
| 2 | 1406.118273185 | 13.857 | Unresolved; independent cadence required | No adjacent-OFF peak within 20 Hz; both active ON tracks reproduce above S/N 3 and every OFF candidate-track S/N is below 5.5. |

Candidate 1's epoch-1 ON peak has S/N 23.276 at 1406.300928477 MHz. The
adjacent OFF scan contains a S/N 19.489 peak at 1406.300911464 MHz, separated
by 17.013 Hz. The fixed rule therefore classifies it as RFI or instrumental.

Candidate 2 reproduces along its frozen track at S/N 8.904 and 12.793 in its
two claimed active ON epochs. Its corresponding OFF-track values are 4.398 and
0.851, and its nearest qualifying epoch-1 OFF peak is 87.901 Hz away. It has no
cross-candidate receiver-frame alias under the fixed two-epoch rule, so it
remains unresolved.

## Interpretation

The unresolved case is not a detection and is not a technosignature claim. Its
waterfalls show a structured, RFI-rich local scene in the first two ON scans,
and the feature is absent from the third ON scan. The single cadence cannot
establish persistence, sky localization, or an interference-free origin. The
widest nine-channel boxcar and arithmetic-family membership remain cautionary
context, not sufficient vetoes.

The candidate cutouts and machine-readable scan metrics are in
`results_m15_candidate_investigation/`. Cross-cadence archive work was
deliberately excluded from this morphology run.

## Next boundary

The only direct confirmation test would be a separately labelled search of an
independent GJ 581 cadence covering the predicted 1406 MHz receiver window.
The public target metadata exposes no such cadence at present; the separate
availability note records that limitation. The case therefore remains open but
untested, not positive.
