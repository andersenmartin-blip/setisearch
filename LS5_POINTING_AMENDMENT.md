# LS5 header-name/pointing amendment — 2026-09-05

The first complete header pass is preserved in results_ls5_header/preflight.json.
It rejects every cadence under LS4's source-name ON/OFF rule: these files all
carry source_name=KEPLER-160, including the OFF scans. No spectrum was read.

Perez et al. (2020), observations section, explicitly states that these products
are labelled KEPLER-160 and alternate ON/OFF from scan 0010 (L) and 0025 (S).
The dedicated API separately labels OFF scans KEPLER-160_OFF. For L and S only,
use agreement of these two sources plus exact consecutively numbered scans
as the role assignment. Preserve every original header; do not rewrite names.
This is a metadata-role amendment before spectral access, not a changed veto.
C remains ineligible because its dedicated listing has only five scans.

Header coordinates show the final designated ON scan offset by ~0.231 degrees
(L) or ~0.248 degrees (S) from the published pointing. Their origin is unresolved;
we do not assert all three pointings centered on the star. The run is a screen
of the published archival ON/OFF sequence, with a pointing qualification flag.
Any surviving event requires independent pointing verification before attribution
to Kepler-160. A null cannot be turned into a calibrated target sensitivity.
No angular threshold is tuned to promote a scan.

The inherited geometric rank places S ahead of L, both near 32 stellar radii:
this is not a close conjunction. Kepler-160 c has published transit-timing
variations; the linear-ephemeris corner range omits them and is not a reliable
conjunction confidence interval. This does not change the broadband detector.

Sources:
- [Perez et al. (2020)](https://seti.berkeley.edu/kepler160/BL_Kepler160.pdf).
- [Heller et al. (2020)](https://arxiv.org/abs/2006.02123).

Perez et al. already searched these observations for narrowband drift signals
and short artificially dispersed broadband pulses. LS5 is a new project target
and a seconds-to-tens-of-seconds envelope reanalysis, not first SETI coverage of
the system. Their published sensitivity limits do not apply to our detector.
