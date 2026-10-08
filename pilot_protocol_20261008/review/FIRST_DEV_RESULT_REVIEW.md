# Independent first DEV result review — 8 October 2026

**PASS for the retained first DEV result; no validation or sky-pilot admission.**
The reviewer read existing JSON/NPZ files and checked their identities, hashes,
counts and recovery arithmetic. No RNG, generator, detector, source payload
fetch or analysis replay was invoked.

The admitted case is exactly `SETI_RADIO_PILOT_20261008_DEV:strong:000`, bound to
public freeze `cbc27ebfb10fc09f58a8ab4a1f00adad47ab1960`. The observed six code,
contract and case-bank hashes equal the admission hashes. All 16 case artifact
manifest entries have the exact retained SHA256 and size.

All six maps are present: 4096 carriers in each ON and 4596 in each OFF. Every
carrier records 21,660 valid hypotheses, matching 5415 drifts × four widths.
The 5415-member grid includes exactly −4, 0 and +4 Hz/s. The native signed
frequency spacing, complete 16-row timing and all-valid 4096-channel
normalization cores agree with the frozen contract.

All 18 threshold ON carriers appear in the full hit table with scores,
frequencies, drift and width equal to their maps. All survive. Independent
endpoint arithmetic localizes all 18 to the injected trajectory. There are 54
OFF comparisons; every compatible family was exhausted without a veto, and
the largest checked OFF score is 4.000026042518285, below the frozen threshold 8.

The frozen truth injects only `epoch1_on`, so successful all-active recovery in
this case means recovery in that one active ON. The other two ON maps have
maximum scores 5.905566207545243 and 5.787519538619728. This is one synthetic
development result and cost measurement; the full development panel and the
independent validation panels remain separate requirements.

The whole-job resource receipt passes its admitted caps: wall
64.67167712599985 s, process CPU 66.326375 s, peak RSS 73,912,320 B. Case-only CPU
64.321877 s excludes startup and flushing, so budget accounting must use the
whole-job CPU receipt. The development summary correctly reports one observed
case out of 24 and `NOT_EVALUATED_DEVELOPMENT_ONLY`.

No material issue blocks the remaining 23 distinct frozen DEV identities.
They must use new output directories and decremented, exclusively reserved
budgets. They must not regenerate the first case via an unfiltered panel run.
