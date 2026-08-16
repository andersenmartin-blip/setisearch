# Milestone 10 preregistration record

- Frozen UTC: 2026-08-16T07:26:25Z
- Config: `config/proxima_small_survey_m10.json`
- Frozen config SHA-256: `47b244a596d88ed06edd2dd232edc556c6e92c456f6af99afbf92849d17623ee`
- Frozen detector: seti-repeater v0.4.0
- Frozen detector source digest: `80201e8c2061122dedf5b166c648c7c31c9f223873c231fc9403030ed1f9641e`
- Scan dates: 2021-04-30, 2021-05-02, and 2021-05-03
- Scan rule: six previously unextracted files; a later complete ON/OFF pair on 30 April followed by the earliest complete pairs on the two previously unused campaign dates
- Search bands: 1400.0–1401.0, 1406.0–1407.0, 1412.0–1413.0, 1418.0–1419.0, and 1424.5–1425.5 MHz in the planet frame
- Total search bandwidth: 5 MHz
- Independence status: fresh frequency intervals and source filterbank payloads; same April–May 2021 observing campaign
- Null calibration: 256 complete five-band circular-shift controls, seed 1020260816
- Completeness: S/N 8, 12, 16, 20, 24, 32, and 40; 32 trials per level in the preregistered 1412.0–1413.0 MHz background

Before this record was written, only public archive metadata and the six
SIGPROC headers were examined. Those checks established source identity, start
time, file completeness, cadence, channel width, integration length, and
frequency coverage. No spectral payload from the selected files or bands had
been extracted or inspected.

The paper-specific public API returned April–May 2021 data but no November 2020
or January 2021 files. Those earlier campaigns are therefore not represented in
this milestone, and the result will not be described as independent in
observing campaign.

Each ON product has 120 × 15 s integrations; each following control has 20 ×
15 s integrations. The shorter controls are an explicit sensitivity limitation.
