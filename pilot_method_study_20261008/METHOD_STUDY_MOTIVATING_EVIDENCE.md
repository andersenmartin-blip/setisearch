# Retained B evidence motivating the method study

This is a read-only interpretation of five completed B cases, with committed artifact hashes checked. It is not whole-panel closure or a new test. No arrays were generated, tracks rescored, thresholds changed or telescope values opened. The METHOD64 bank and scientific protocol remain unchanged.

| B case | Measured loss or leakage | Interpretation |
|---|---|---|
| operating019 | ThirdON maximum9.683702761<ON10; zero ON hits | Pre-threshold miss, before OFF. |
| operating021 | ThirdON maximum9.792757617<ON10; zero ON hits | Pre-threshold miss, before OFF. |
| operating045 | SecondON maximum9.859521556<10; thirdON has10 localized survivors, maximum11.642404327 | ALL-active fails while ANY-active succeeds; OFF did not cause the missing secondON. |
| matched_rfi002 | All3ONs have initial localized detections; all localized hits are vetoed, but13 nonlocalized firstON carriers survive | The frozen requirement is zero ANY survivors, so true-track rejection does not rescue the RFI gate. |
| matched_rfi003 | All3ONs have initial localized detections; all localized hits are vetoed, but1 nonlocalized firstON carrier survives | The same interference-leakage failure. |

The two RFI cases inject intrinsic width1, drift−4Hz/s and nominal ideal level24 across all six scans. Integration smearing makes the noiseless oracle box width33. For RFI002 the leaked firstON carriers771–783 use width33, drifts−3.174 to−3.215Hz/s, and ON scores10.070–10.611. Their errors relative to the true path at the two originating ON endpoints are approximately−26 to−24 and+50 to+52 native channels. RFI003’s lone survivor uses carrier2816, width33, drift−3.140007388Hz/s and ON score10.055698261, with endpoint errors−36.230 and+45.597 channels. None is localized by the frozen recovery definition.

Each survivor’s entire compatible OFF family was exhausted. Its strongest checked OFF score stays below8: RFI002 ranges up to7.865466139, and RFI003 reaches7.926772881. At the same time, the retained OFF global maxima show the bright injected RFI at scores approximately22–24. Those global winning paths fail the surviving ON alias’s coupled endpoint compatibility constraints. With width33 against width33 the matching allowance is35 native channels; the true path’s endpoint errors exceed it. Thus the detector can correctly reject the true RFI core while preserving a different ON track that responds above10 and fails to find a compatible OFF response above8.

This pattern is consistent with broad-box, off-drift responses to strong integration-smeared RFI, followed by extrapolation away from the RFI between scans. That causal attribution is an inference from retained scores and path geometry; the available summaries do not provide a fresh counterfactual noise-only comparison. The recorded failure is certain: interference-containing cadences left surviving ON carriers despite the predeclared zero-survivor gate. It should be reported as a scientific filter limitation rather than erased by redefining the gate around truth-localized hits.

The exploratory64-cell study measures fixed-method signal recovery across declared strengths, drifts, widths and activity patterns. It can describe the observed threshold losses and clarify ALL-active versus ANY-active behavior. Its signal-only design cannot establish interference rejection, transient morphology rejection or sky false-alarm probability. Retained A/B RFI, noise and diagnostics provide those complementary measured method results, with both failed-qualification decisions intact. The study was selected after these B observations and cannot serve as blind qualification.

The associated JSON retains exact selected cases, per-ON recovery, six global map maxima, every leaked carrier’s geometry and OFF exhaustion result, and artifact integrity bindings. Full B closure, complete-panel integrity review and actual resource reconciliation are separate requirements before any METHOD generation.
