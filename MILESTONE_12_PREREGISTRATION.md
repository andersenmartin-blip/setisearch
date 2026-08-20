# Milestone 12 preregistration: detector v0.5

Status: preregistered before the v0.5 implementation is run on the Milestone 11 development candidates.

## Purpose and evidential boundary

Milestone 12 is detector development, not a blind technosignature search. It uses the labelled Milestone 11 LHS 1140 outcomes to repair known candidate-veto failure modes. Consequently, neither a veto nor a retained candidate in this milestone is independent evidence for or against a technosignature.

The fixed development set is:

- the five formal Milestone 11 survivors classified by the candidate investigation;
- the sixteen above-threshold clusters already marked for arithmetic-family manual review;
- synthetic recurrent signals with quiet OFF scans, used to guard against over-vetoing; and
- the existing v0.4 regression tests.

No threshold or rule may be changed after examining its outcome on this set without recording a new detector-development milestone. Milestone 13 will apply the frozen detector to a newly selected held-out target/cadence, with no M12-driven retuning.

## Preregistered v0.5 vetoes

The new logic is opt-in under `search.candidate_veto_v0p5`; v0.4 configurations without that block must remain reproducible.

1. **Local multi-hypothesis OFF recurrence.** Search each candidate's OFF-source neighbourhood over all configured spectral widths, Doppler templates, and permitted epoch subsets. The fixed neighbourhood is +/-20 Hz. Flag the candidate when the best OFF recurrence meets the same operational global threshold and per-epoch floor used for ON-source reporting.
2. **Single adjacent-OFF track coincidence.** At the candidate's own spectral width, Doppler template, and predicted frequency track, flag the candidate if any corresponding active-epoch OFF scan has S/N >=5.5. This threshold is the existing candidate-reporting floor, not a threshold fitted to the five survivors.
3. **Receiver-frame template alias.** Reconstruct the strongest local topocentric feature within +/-100 Hz of each candidate track. Flag two candidate clusters as aliases when their reconstructed peaks agree within 20 Hz in at least two shared active epochs and each compared local peak has S/N >=5.5.

Veto provenance must be serialized with the candidate, including the winning OFF hypothesis or the matching receiver-frame candidate IDs and epoch measurements.

## Acceptance criteria

- Existing v0.4 configurations produce unchanged candidate dispositions.
- All existing unit tests pass, plus focused tests for the three new veto modes and a clean-candidate control.
- The five formal M11 survivors are rejected for their pre-labelled reasons: local/track OFF recurrence for candidates 1, 2, and 5; receiver-frame aliasing for candidates 3 and 4.
- All sixteen arithmetic-family review clusters receive an explicit recorded v0.5 disposition or remain conservatively marked for manual review; they are not silently promoted.
- Synthetic recurrent ON signals with quiet OFF scans remain follow-up candidates.
- The released detector version is `0.5.0`, and Milestone 13 is declared held out before its target data are searched.

## Interpretation rule

Passing these criteria means only that detector v0.5 addresses the failure modes exposed by Milestone 11 without failing its controls. It does not validate the detector on independent observations. Scientific validation begins with the frozen, held-out Milestone 13 search.
