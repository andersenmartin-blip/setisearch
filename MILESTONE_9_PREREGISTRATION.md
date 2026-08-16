# Milestone 9 preregistration record

- Frozen UTC: 2026-08-15T19:02:57Z
- Config: `config/proxima_temporal_confirmation_m9.json`
- Frozen config SHA-256: `35cc5deb4546b64f660a9905c60e891636dea0fc76787b789f35e1d5ea684d0f`
- Frozen detector: seti-repeater v0.4.0
- Frozen detector source digest: `80201e8c2061122dedf5b166c648c7c31c9f223873c231fc9403030ed1f9641e`
- Temporal confirmation dates: 2021-04-29, 2021-04-30, and 2021-05-01
- Scan rule: earliest complete 30-minute Proxima ON scan on each date, followed by the immediately subsequent complete 5-minute 1421−490 blank-sky scan
- Confirmation band: 1405.25–1405.75 MHz in the planet frame, identical to the lower Milestone 8 band
- Confirmation status: independent in observing epoch, not in frequency
- Null calibration: 256 full-search circular-shift controls, seed 920260815
- Completeness: S/N 8, 12, 16, 20, 24, 32, and 40; 32 trials per level

Before this record was written, only the archive catalogue and the six SIGPROC
headers were examined. Those checks established source identity, start time,
file completeness, cadence, channel width, integration length, and frequency
coverage. No spectral payload from the selected files had been extracted or
inspected.

The selected ON products have 120 × 15 s integrations and 2 Hz channels. The
paired OFF products have 20 × 15 s integrations and are consequently less
sensitive; that asymmetry is an explicit limitation, not a post-search choice.
