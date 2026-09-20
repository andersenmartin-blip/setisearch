# Continue after LS8F

LS8F is complete and independently audited.

## Closed result

- target: **GJ 514**
- exact visits:
  - `CH_PR100018_TG007501_V0300`
  - `CH_PR100018_TG007502_V0300`
- rows: **152**
- exact science-table bytes: **20,976**
- eligible 1/2/3-row windows: **150**
- positive windows/clusters at +8.5: **0 / 0**
- negative windows/clusters at -8.5: **0 / 0**
- first visit max/min score: **5.819043 / -2.311805**
- second visit: **0 eligible windows**
- independent audit: **PASS**, 1,800 comparisons, zero disagreements
- image bytes: **0**
- raw imagettes: **0**

The second visit's zero eligible windows is part of the frozen result. Do not
alter the context, timing, status, duration or aperture rules to manufacture
coverage.

## Immediate next action

Advance mechanically through the host order fixed before LS8E science access.
The next qualifying host in the saved metadata ledger is **GJ 849** (rank 4),
with six eligible V0300 / PIPE 14.1.2 visits.

Start LS8G by selecting the two chronologically earliest eligible GJ 849 visits
from the existing `results_ls8e_selection/selection.json` ledger only. Freeze
their exact identities before reading any new light-curve value.

Repeat the same staged boundary:

1. publish the exact two-visit selection from saved metadata;
2. header-only DEFAULT-L2 preflight with zero table bytes;
3. if schema compatible, freeze the unchanged symmetric 1/2/3-row screen;
4. acquire only the exact declared table ranges and independently audit;
5. open CAL/COR images only after a prospectively screened excursion and a new
   frozen image diagnostic.

Unused TESS sectors, M43 held-out panels and the raw-imagette branch remain
closed under their existing rules.
