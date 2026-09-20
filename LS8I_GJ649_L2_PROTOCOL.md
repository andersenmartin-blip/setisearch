# LS8I — frozen two-visit GJ 649 DEFAULT-L2 screen

Status: **FROZEN BEFORE GJ 649 TABLE VALUES**.

The two GJ 649 visits were selected mechanically from the host order fixed
before LS8E science access. Header-only preflight established a compatible
18-field DEFAULT-L2 schema with zero table-data bytes acquired.

Exact products:

1. `CH_PR100018_TG018601_V0300` — 127 rows, table start 20160,
   table bytes 17526, TEXPTIME=22.6499996185303 s.
2. `CH_PR100018_TG031201_V0300` — 75 rows, table start 20160,
   table bytes 10350, TEXPTIME=42 s.

The saved ETags and object identities in `results_ls8i_l2_metadata/` are
binding. The visits intentionally have different cadences; each is evaluated
with its own TEXPTIME.

Use the unchanged prospective screen already frozen for LS8E–LS8G:

- durations 1, 2 and 3 rows;
- 12-row sideband on each side;
- 2-row guards;
- finite BJD/FLUX/FLUXERR, positive FLUXERR and STATUS=0 across context;
- adjacent time steps within 0.5–1.5 times that visit's TEXPTIME;
- sideband-only local linear baseline;
- unchanged robust/formal numerical scale and prediction leverage;
- score endpoints +8.5 and -8.5;
- separate signed clustering and unchanged representative rule;
- implementation `seti_repeater.cheops_l2_stable.stable_score_window`.

Acquire only the two declared first-table ranges using saved ETags. Exact
permitted science-table bytes: **27,876**. No image, raw imagette, alternate
aperture or additional GJ 649 visit may be opened.

Independently audit the retained 138-byte big-endian rows and recompute all
eligibility, scores, clusters and summaries with the existing tolerances.
A zero-eligible visit remains a valid frozen outcome.

Any threshold crossing is only an L2 excursion and requires a separate frozen
CAL/COR image diagnostic before physical interpretation.
