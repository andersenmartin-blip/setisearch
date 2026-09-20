# Continue after LS8H

LS8G found one positive GJ 849 DEFAULT-L2 excursion and LS8H completed its
predeclared paired CAL/COR image diagnosis.

## Closed result

- target: **GJ 849**
- visit: `CH_PR100018_TG032401_V0300`
- representative: row 75, duration 1 x 42 s
- fixed L2 score: **23.470080**
- paired image bytes: **18,560,000**
- smearing bytes: **46,400**
- image classification: **SPATIALLY_STRUCTURED**
- |DELTA/COR|: **0.03536 / 0.03276** for C0/C1
- COR displacement explained: **87.801% / 87.800%**
- COR brightness explained: **0.912% / 0.914%**
- independent image audit: **PASS**
- raw imagettes: **0**
- SETI candidate claims: **0**

The image morphology passes the frozen displacement-based spatial gate and
does not pass the correction-coupling gate. This does not identify a unique
physical cause. The branch is closed under its predeclared diagnostic scope.

## Immediate next action

Advance mechanically through the host order fixed before LS8E science access.
The next qualifying host in the retained metadata ledger is **GJ 649**
(rank 5), with five eligible V0300 / PIPE 14.1.2 visits.

Start LS8I by selecting the two chronologically earliest eligible GJ 649 visits
from the already saved `results_ls8e_selection/selection.json` ledger only.
Freeze their exact identities before opening any new light-curve value.

Repeat the established staged boundary:

1. metadata-only two-visit selection;
2. header-only DEFAULT-L2 preflight with zero table bytes;
3. if compatible, freeze the unchanged symmetric 1/2/3-row screen;
4. acquire only the exact declared first-table ranges and independently audit;
5. perform a separately frozen CAL/COR image diagnostic only for a
   prospectively screened excursion.

Do not reopen the GJ 849 cluster, unused TESS sectors, M43 held-out panels or
the raw-imagette branch as an outcome-driven repair.
