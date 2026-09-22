#!/usr/bin/env python3
"""Report every fixed LS8AJ image outcome without altering the diagnostics."""
import json
import math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_ls8aj_images'


def number(value, digits=5):
    return 'NA' if value is None else f'{value:.{digits}f}'


def main():
    summary=json.loads((OUT/'summary.json').read_text())
    audit=json.loads((OUT/'audit.json').read_text())
    rows=json.loads((OUT/'diagnostics.json').read_text())
    cfg=json.loads((ROOT/'config/ls8aj_images.json').read_text())
    assert len(rows)==1 and [r['id'] for r in rows]==[c['id'] for c in cfg['contexts']]
    assert summary['status']=='COMPLETE_AUDITED' and audit['status']=='PASS'
    table=[];figures=[]
    for row in rows:
        ident=row['id']; c0=row['conventions']['C0']; c1=row['conventions']['C1']
        fits=[c['fits']['COR'] for c in (c0,c1)]
        table.append(f"| {ident} | {row['sign']} | {row['classification']} | {number(c0['delta_over_cor'])} / {number(c1['delta_over_cor'])} | "+
                     ' / '.join(number(100*f['brightness'].get('explained'))+'%' if f['brightness'].get('explained') is not None else 'NA' for f in fits)+' | '+
                     ' / '.join(number(100*f['displacement'].get('explained'))+'%' if f['displacement'].get('explained') is not None else 'NA' for f in fits)+' |')
        with np.load(OUT/ident/'event_maps.npz') as z:
            maps={k:z[k].copy() for k in ('CAL','COR','DELTA')}
        finite=np.concatenate([np.abs(v[np.isfinite(v)]) for v in maps.values()])
        limit=float(finite.max()) if finite.size else 1.
        if not math.isfinite(limit) or limit==0:limit=1.
        fig,axes=plt.subplots(1,3,figsize=(12,4.1),layout='constrained')
        for ax,kind in zip(axes,('CAL','COR','DELTA')):
            image=ax.imshow(maps[kind],origin='lower',cmap='RdBu_r',vmin=-limit,vmax=limit)
            for c,style in [(c0,'-'),(c1,'--')]:
                ax.add_patch(Circle(c['center'],25,fill=False,color='#222222',linestyle=style,linewidth=.9))
            ax.set_title(kind);ax.set_xlabel('Native x pixel');ax.set_ylabel('Native y pixel')
        unit=cfg['sources'][row['file_key']]['SCI_COR_SubArray']['bunit']
        fig.colorbar(image,ax=axes,shrink=.8,label=f'Event residual sum [native {unit}]')
        fig.suptitle(f"{ident} · {row['sign']} · {row['classification']}",fontsize=12)
        filename=f'{ident}_CAL_COR_DELTA.png'
        fig.savefig(OUT/filename,dpi=180);plt.close(fig)
        figures.append(f"### {ident}\n\n![{ident}: CAL, COR and DELTA event maps]({filename})")
    unresolved=[r['id'] for r in rows if r['classification']=='UNRESOLVED_WITHIN_FIXED_SCOPE']
    if unresolved:
        next_action=('Preserve '+', '.join(unresolved)+' as unresolved under this fixed diagnostic. '
                     'Any next analysis must first state the specific limitation and freeze a separate diagnostic using only the already retained tables/maps. '
                     'Do not widen image ranges, switch apertures or classify these as SETI candidates merely because the two descriptive closure gates did not pass.')
    else:
        next_action=('Close this EC13080-1508 follow-up under its fixed descriptive label without widening. '
                     'The next independent target is rank 12 of the unchanged reconciled LS8J ledger, PG 1343-102; '
                     'freeze its exact pair and header preflight before science values.')
    count=audit['comparisons']
    text=f'''# LS8AJ — EC13080-1508 negative-event paired-image follow-up

Completed 22 September 2026. **COMPLETE_AUDITED**, independent audit **PASS**.

The separately frozen diagnostic retains the complete LS8AI signed representative
set: zero positive and one negative event. No representative is added or substituted.
The image outcomes are: **{json.dumps(summary['outcomes'],sort_keys=True)}**.
These are descriptive image labels, not a determination of artificial or
astrophysical origin, and not detector qualification or a SETI-candidate claim.

| Representative | Sign | Fixed classification | DELTA/COR C0 / C1 | COR brightness explained C0 / C1 | COR displacement explained C0 / C1 |
|---|---|---|---:|---:|---:|
'''+ '\n'.join(table)+f'''

The negative representative is TG005201 row 65, one 60-second exposure,
with NEXP=1. Its original L2 score is -13.17039181262956, not a Gaussian
significance. Both selected visits' complete signed cluster sets were checked;
no image was acquired for the zero-crossing second visit.

## Scope and method

The metadata-only preflight established **58 unique CAL/COR exposure joins**
for the 29 fixed L2 context rows, with <=1 ms MJD/BJD differences and exact UTC
and CE agreement. The public config fixed every source identity and future
range before image access. The run acquired exactly
**{summary['image_bytes']:,} paired image bytes** and
**{summary['smearing_bytes']:,} smearing-row bytes**.

The unchanged LS8D/LS8H method constructs CAL, COR and DELTA=COR-CAL temporal
event maps on the common finite mask. It retains the original 12-row sidebands,
two-row guards, both coordinate conventions C0/C1, r<=25 source aperture,
30<r<=40 background annulus and r>35 smearing regression. Source pixel centers
come only from the saved sideband centroids; none is moved to fit the event.

CORRECTION_LINKED is evaluated first: complete apertures and matching COR/L2
signs in both conventions, plus |DELTA/COR| or |column-DELTA/COR| >=0.5 in both.
Otherwise SPATIALLY_STRUCTURED requires displacement explained energy >=0.8
and an advantage >=0.2 over brightness in both conventions. Remaining events
are UNRESOLVED_WITHIN_FIXED_SCOPE. Missing/rank-deficient fits stay unavailable.

A correction-linked label identifies material coupling to delivered processing;
it does not identify one physical correction component or exclude source
variability. A spatial label identifies a morphological fit, not a unique
physical cause. An unresolved label does not establish that the event is
astrophysical or artificial.

## Verification

The nine existing synthetic image tests, including one/three-row known-answer
controls and brightness preservation in both signs, run unchanged before
payload access. The independent
struct/long-double/scalar-normal-equation audit checks source ranges and
hashes, metadata joins, masks, event maps, fits and classifications:

- numerical comparisons: **{count['numeric']:,}**;
- exact checks: **{count['exact']:,}**;
- disagreements: **{len(audit['disagreements'])}**.

LS8AI's L2 audit remains PASS. Historical LS8B's original FAIL and later
arithmetic repair remain unchanged. This is diagnosis of already selected
events, not an independent sensitivity or false-alarm calibration. Raw
imagettes, alternative apertures and additional visits remain unopened.

[Summary](summary.json) · [all diagnostics](diagnostics.json) ·
[independent audit](audit.json) · [independent reference](independent_reference.json) ·
[checksums](SHA256SUMS).

## Event maps

Each three-panel figure uses one common signed scale for its representative.
Solid/dashed circles show the C0/C1 apertures. Figures are presentation only;
they do not feed the diagnostic or any threshold.

'''+ '\n\n'.join(figures)+'\n\n## Next action\n\n'+next_action+'\n'
    (OUT/'REPORT.md').write_text(text)
    (OUT/'next_action.json').write_text(json.dumps({'unresolved':unresolved,'next_action':next_action},indent=2)+'\n')
    print(json.dumps({'status':summary['status'],'outcomes':summary['outcomes'],'next_action':next_action},indent=2))


if __name__=='__main__':main()
