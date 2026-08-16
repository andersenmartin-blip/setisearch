# Milestone 11 preregistration record

- Frozen UTC: 2026-08-16T10:10:22Z
- Config: `config/lhs1140b_new_target_m11.json`
- Frozen config SHA-256: `bff867ce097051dbb4a2a426ba774c18347705d4bb692d1a544be8eeb8375e3a`
- Frozen detector: seti-repeater v0.4.0
- Frozen detector source digest: `80201e8c2061122dedf5b166c648c7c31c9f223873c231fc9403030ed1f9641e`
- Target/motion hypothesis: LHS 1140 b
- Observation: Green Bank Telescope L-band cadence --114914, 2017-01-21
- Scan rule: the complete public ABACAD cadence, with three LHS 1140 pointings interleaved with HIP 2579, HIP 2586, and HIP 3249 controls
- Search bands: 1400.0–1401.0, 1406.0–1407.0, 1412.0–1413.0, 1418.0–1419.0, and 1424.5–1425.5 MHz in the selected planet frame
- Total search bandwidth: 5 MHz
- Transfer status: new target, telescope, date, cadence, and source payload; the Milestone 10 frequency intervals are intentionally reused
- Null calibration: 256 complete five-band circular-shift controls, seed 1120260816
- Completeness: S/N 8, 12, 16, 20, 24, 32, and 40; 32 trials per level in the preregistered 1412.0–1413.0 MHz background

Before this record was written, only public archive metadata and the six
SIGPROC headers were examined. Those checks established source identity, start
time, file completeness, cadence, channel width, integration length, and
frequency coverage. No spectral payload from the selected search intervals had
been extracted or inspected.

Each filterbank contains 16 × 18.253611008 s integrations at
2.7939677238464355 Hz channel spacing. ON and OFF products therefore have equal
exposure in the extracted data. All three ON pointings occur within one
28-minute ABACAD session; they are recurrence opportunities within one cadence,
not independent observing nights.

The orbit is a transparent working motion hypothesis. The NASA Exoplanet
Archive composite parameters provide the period, semimajor axis, transit
midpoint, and an eccentricity limit, but no unique periastron phase for this
nearly circular transiting orbit. The preregistered template adopts e = 0,
uses the transit midpoint as phase zero, and sets omega = pi/2 so the modeled
line-of-sight velocity is zero at inferior conjunction and increases
immediately afterward. The unchanged phase-offset bank searches ±0.2 cycles.

Finally, the planet is not assumed to be the physical source. It supplies the
motion law under which an intermittent line would add coherently. Any feature
would still require RFI, instrumental, spacecraft, sidelobe, and broader
telescope-response checks before a source location could be inferred.
