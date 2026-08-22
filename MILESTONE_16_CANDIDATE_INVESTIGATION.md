# Milestone 16 candidate investigation

**Status: TWO UNRESOLVED CASES — INDEPENDENT CADENCE REQUIRED**

Milestone 16 produced one automated follow-up survivor at 1412 MHz and one
manual arithmetic-family review case at 1425 MHz. This labelled post-hoc
investigation applies the protocol fixed in
`MILESTONE_16_CANDIDATE_INVESTIGATION_PLAN.md`; it does not alter or rerun the
held-out detector.

## Reproducibility record

- GitHub Actions run: `32569998608`
- Artifact: `9475103347` (`milestone-16-candidate-investigation`)
- Artifact digest:
  `sha256:3bb3520708a01e7e4bf3c0deccbd2c7455fb3b8fbc207766e20ec30fce10bc26`
- Scope: six frozen cadence scans, plus/minus 100 Hz around each case, with a
  bounded free-drift diagnostic over plus/minus 2 Hz/s
- Receiver-frame coincidence tolerance: 20 Hz
- Adjacent-OFF candidate-track floor: S/N 5.5

All frozen-input and protocol hashes, the 15 detector tests, 12 targeted HDF5
extractions, and the five result-file hashes passed.

## Dispositions

| # | Planet-frame frequency (MHz) | Frozen S/N | Local ON track S/N | Local OFF track S/N | Post-hoc disposition |
|---:|---:|---:|---|---|---|
| 1 | 1412.485745177 | 9.145 | 14.787, 5.923, 2.286 | 1.122, -0.410, 0.433 | Unresolved; independent cadence required |
| 2 | 1425.136278570 | 7.478 | 4.300, 4.909, 3.786 | 2.472, 2.143, 1.735 | Unresolved; independent cadence required |

Candidate 1 reproduces above S/N 3 along the frozen track in both originally
active ON epochs. The nearest qualifying OFF peaks are 39.116 Hz from the ON
peaks in both epochs, outside the fixed 20 Hz coincidence tolerance, and the
corresponding OFF track values remain below 5.5. It therefore passes the fixed
post-hoc rejection rules.

Candidate 2 also remains above S/N 3 along the frozen track in all three ON
scans. Its only qualifying adjacent-OFF peak is 27.940 Hz from the epoch-2 ON
peak, outside the fixed tolerance, and every OFF track value remains below
5.5. Arithmetic-family membership is cautionary context, not a physical veto,
so this case also remains unresolved under the preregistered rules.

## Interpretation

Neither case is a detection or a technosignature claim. Both select the widest
nine-channel boxcar. The 1412 MHz waterfall contains strong, differently
offset structures in several ON and OFF scans; the 1425 MHz case is weak and
does not show a visually compelling isolated track. These observations lower
the qualitative plausibility of an astrophysical interpretation but were not
predeclared rejection rules and therefore do not change the formal
dispositions.

## Next boundary

The corrected header-only archive screen identified four complete qualifying
HD 219134 cadences independent of the 2016-08-22 search. The earliest is the
complete GBT L-band ABACAD cadence `--65393` beginning 2016-10-01, about 40
days later. A separately frozen targeted recurrence test of exactly these two
hypotheses in that cadence is the next direct check.

Machine-readable scan measurements and diagnostic figures are in
`results_m16_candidate_investigation/`.
