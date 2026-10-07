# Independent retained-output review — 7 October 2026

Reviewed the distinct second/final local engineering route; no detector was
invoked by this reviewer and no source-array search was repeated.

Disposition: **core reference analysis and corrected presentation pass review**.
The earlier GitHub Actions reference remains FAILED_CLOSED.

- Independently parsed the header only: 382 header bytes, 16 complete rows of
  4,194,304 bytes, zero remainder, 32-bit little-endian one-IF power; actual
  observation start MJD57650.78209490741, 19 September 2016 18:46:13 UTC.
- Read the prospective contract, frozen config and source. Signed channel width
  is -2.7939677238464355 Hz; time offsets r*18.253611008 seconds reference the
  first integration midpoint. Index shifts drift*time/signed-channel-width have
  the correct direction. The 785-trial grid covers ±4 Hz/s, and its half-step
  endpoint displacement is 0.4999915 channels. Complete 522-channel halos also
  cover the running-median radius without wrap or source-edge truncation.
- The numeric grid's nominal zero is -4.440892098500626e-16 Hz/s due to floating
  representation. Its maximum displacement is 4.352e-14 channels, producing the
  exact zero rounded-index trajectory. This has no effect on the detector.
- Source receipt precedes header/values and plots precede detection/judgment,
  according to retained timestamped log and filesystem ordering.
- Audited every CSV threshold row against the saved all-channel NPZ: all 2,369
  qualifying channels appear, with matching frequency, winning drift and score.
  All 28,633 searched channels are contiguous and all maximum scores are finite.
  The 116 representative maxima are a separate descriptive list.
- Strongest known carrier: 8419.297027867287 MHz at the first midpoint,
  -0.377551020408164 Hz/s, custom engineering score1004.1205388466. The declared
  known-carrier gate passes. Its negative drift agrees with the waterfall.
- Resource receipt passes: wall3.750069s, CPU3.747761s, peak RSS224,813,056B.
  The completed download and documentation are outside analysis-command timing.
- Original spectrum tick formatting made dB values ambiguous and original
  waterfall frequency ticks crowded. Separate presentation figures use explicit
  decimal dB ticks and frequency offsets in kHz. They are visually clear and
  retain the correct negative carrier drift. This was presentation only.
- All original output-manifest hashes and executed script/config/contract hashes
  remain unchanged. The source, pipeline, thresholds and acceptance gate were
  not modified after inspecting telescope power values.

The engineering-only scope is explicit: a public known single-scan Voyager
reference, no OFF data, no new SETI candidate, no calibrated sky significance,
no fresh scientific validation and no pilot/holdout access. The threshold rows
are correlated channels, not independent signals. There are no outstanding
material issues blocking this engineering reference disposition.
