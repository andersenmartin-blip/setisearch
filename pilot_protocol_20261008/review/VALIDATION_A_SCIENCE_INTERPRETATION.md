# Fresh validation A: scientific interpretation, 8 October 2026

**The numerical science criteria pass, but validation A is FAIL_CLOSED because
two diagnostic jobs timed out. It does not admit the telescope pilot.** All
142 case identities have outcomes; 140 computations completed. The 118 primary
eligibility cases completed, but the frozen integrity requirement also covers
the diagnostic cases. Do not remove those cases after exposure or count their
timeout-generated zeros as measured nonrecoveries.

The completed primary panel recovers 14/14 strong signals and 46/48 operating
signals in every active ON scan. All activity, drift and intrinsic-width
subgroup minima pass. In all 24 matched RFI cases the three primary ON
trajectories were detected before OFF rejection, and no final ON carrier
survived. All 32 noise cadences completed with no survivors.

The two operating misses occur before OFF rejection:

| Case | Injection | Missing ON result |
|---|---|---|
| Operating 014 | One active second ON; +4 Hz/s; intrinsic width 1; interior frequency; nominal ideal score 12 | Its highest retained score is 9.810068, below the frozen ON threshold 10. No ON hit was produced. |
| Operating 040 | Second and third ON active; −4 Hz/s; intrinsic width 1; near the declared band edge; nominal ideal score 12 | Second ON recovered. Third ON's highest retained score is 9.004625, below 10, so the all-active case fails while any-active recovery succeeds. |

These are genuine measured recovery losses, not data-integrity errors or OFF
veto losses. They remain in the denominator. Thus 46/48 all-active recovery
and 47/48 any-active recovery describe different performance. The nominal
injection level is a noise-free ideal projection, not a guarantee that the
observed robust statistic exceeds the cut or a calibrated received flux.

The diagnostic groups expose two substantial limitations:

- **Single-row transients:** all ten completed cases produce surviving ON
  hits. A signal confined to one integration can pass this detector; a survivor
  therefore need not be a persistent narrowband track. The remaining two cases,
  transient 010 and 011 in the last row of the third ON, hit their admitted
  approximately 250-second watchdog. Their zero counts mean missing computation,
  not successful rejection. The correct result is ten completed survivors and
  two failed jobs, not zero of twelve or a measured ten-of-twelve recovery rate.
- **Nearby OFF contamination:** all twelve genuine ON-only injected signals
  are detected before OFF and all twelve are rejected afterward. Their unrelated
  paired-OFF nuisance lies 2 or 8 reference channels away, about 5.671 or
  22.684 Hz. The broad compatible-family veto deliberately trades sensitivity
  for conservative rejection. A rejected ON hit is not proof that the ON signal
  itself was interference, and the raw ON records remain necessary.

The finite matched RFI panel covers specified strengths, drift rates, widths,
locations and a few stronger incompatible OFF nuisances. It does not cover
arbitrary intermittent RFI, weak or absent OFF emission, nonlinear tracks or
all telescope artifacts. Each of the four synthetic noise laws has only eight
independent cadences. Zero of 32 mixed-law survivors is useful method evidence,
not a universal native-data false-alarm rate or a probability of artificial
origin. The robust score is neither turboSETI SNR nor calibrated significance.

Preserve A's closed failure and all numerical results. The independently
proposed operational runtime correction must be tested prospectively with new
development identities. Only a completely fresh, fully completed validation B
meeting the same complete joint criteria can supply the next pilot admission;
the scientific thresholds, generator and score laws stay fixed. No A case is
regenerated or retuned to obtain a pass.

This review reads retained outcomes, definitions, localization records and
maximum maps only. It generates no controls, reruns no detector, opens no
validation-B or sky values and introduces no new rejection rule. A later real
pilot would still cover one historical observing session, not independent
visits or confirmation of an astronomical signal.
