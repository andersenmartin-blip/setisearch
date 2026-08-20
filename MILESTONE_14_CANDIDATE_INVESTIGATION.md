# Milestone 14 candidate investigation

**Status: THREE UNRESOLVED — INDEPENDENT CADENCE REQUIRED**

Milestone 14 reported five weak 1425 MHz clusters that exceeded the frozen
global threshold but had only arithmetic-frequency-family triage flags. This
labelled post-hoc investigation applies the protocol fixed in
`MILESTONE_14_CANDIDATE_INVESTIGATION_PLAN.md`; it does not alter or rerun the
held-out detector.

## Reproducibility record

- GitHub Actions run: `32395584049`
- Artifact: `9416566192` (`milestone-14-candidate-investigation`)
- Artifact digest: `sha256:85ddf2d899fc6e0d7286a0318e252ecc58e9cab0f9473a0ec160a200b70e58f5`
- Scope: six frozen cadence scans, ±100 Hz around each candidate, with a
  bounded free-drift diagnostic over ±2 Hz/s
- Receiver-frame coincidence tolerance: 20 Hz
- Adjacent-OFF candidate-track floor: S/N 5.5

The artifact manifest verifies all eight investigation outputs. The detector
tests also passed before the targeted cutouts were examined.

## Dispositions

| # | Planet-frame frequency (MHz) | Frozen S/N | Post-hoc disposition | Decisive evidence |
|---:|---:|---:|---|---|
| 1 | 1425.315276906 | 9.429 | Unresolved; independent cadence required | No adjacent-OFF peak within 20 Hz and every OFF candidate-track S/N is below 5.5. |
| 2 | 1425.247347169 | 9.377 | RFI or instrumental | Epoch-1 OFF peak is 11.176 Hz from the ON peak; epoch-3 OFF candidate-track S/N is 5.853. |
| 3 | 1425.134884380 | 9.377 | Unresolved; independent cadence required | No adjacent-OFF peak within 20 Hz and every OFF candidate-track S/N is below 5.5; the closest qualifying OFF peak is 22.352 Hz away. |
| 4 | 1425.360145234 | 9.338 | RFI or instrumental | Qualifying OFF peaks lie 5.588 Hz and 8.382 Hz from the corresponding ON peaks in epochs 1 and 3. |
| 5 | 1425.328830443 | 9.317 | Unresolved; independent cadence required | No adjacent-OFF peak within 20 Hz and every OFF candidate-track S/N is below 5.5. |

No candidate shares a receiver-frame alias with another candidate under the
fixed 20 Hz rule. All five selected the widest frozen nine-channel boxcar, but
that morphology and their arithmetic-family membership are triage evidence,
not sufficient physical vetoes.

## Interpretation

Candidates 2 and 4 now have direct adjacent-OFF evidence and are classified as
RFI or instrumental. Candidates 1, 3, and 5 are not detections and are not
technosignature claims; they remain unresolved because this single cadence
cannot establish persistence, sky localization, or an interference-free
origin.

The candidate cutouts and machine-readable scan metrics are in
`results_m14_candidate_investigation/`. Cross-cadence archive work was
deliberately excluded from this morphology stage.

## Next boundary

The next admissible step is a separately labelled search of an independent
GJ 687 cadence at only the three unresolved frequencies. Its data selection,
available ON/OFF scans, frequency coverage, tolerance rules, and disposition
logic must be fixed before inspecting those cutouts. No additional inference
should be drawn from the present cadence alone.
