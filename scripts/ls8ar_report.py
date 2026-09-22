#!/usr/bin/env python3
"""Report every fixed LS8AR image outcome without altering the diagnostics."""
import json
import math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_ls8ar_images'


def number(value, digits=5):
    return 'NA' if value is None else f'{value:.{digits}f}'


def main():
    summary=json.loads((OUT/'summary.json').read_text())
    audit=json.loads((OUT/'audit.json').read_text())
    rows=json.loads((OUT/'diagnostics.json').read_text())
    cfg=json.loads((ROOT/'config/ls8ar_images.json').read_text())
    assert len(rows)==14 and [r['id'] for r in rows]==[c['id'] for c in cfg['contexts']]
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
        next_action=('Close this GJ 581 follow-up under its fixed descriptive label without widening. '
                     'The next independent target is rank 16 of the unchanged reconciled LS8J ledger, EC14599-2047; '
                     'freeze its exact pair and header preflight before science values.')
    count=audit['comparisons']
    text=f'''# LS8AR — GJ 581 complete signed-event paired-image follow-up

Completed 22 September 2026. **COMPLETE_AUDITED**, independent audit **PASS**.

The separately frozen diagnostic retains the complete LS8AQ signed representative
set: nine positive and five negative events. No representative is added or substituted.
The image outcomes are: **{json.dumps(summary['outcomes'],sort_keys=True)}**.
These are descriptive image labels, not a determination of artificial or
astrophysical origin, and not detector qualification or a SETI-candidate claim.

| Representative | Sign | Fixed classification | DELTA/COR C0 / C1 | COR brightness explained C0 / C1 | COR displacement explained C0 / C1 |
|---|---|---|---:|---:|---:|
'''+ '\n'.join(table)+f'''

Thirteen representatives are one 60-second exposure; N1 is a two-exposure
120-second sum. NEXP=1 for each exposure.

| Representative | L2 row, zero-based | Duration | Original L2 score | L2 excess / local baseline |
|---|---:|---|---:|---:|
| TG023701_P0 | 1070 | 60 s | +10.117099458039316 | +0.248385% |
| TG023701_P1 | 2033 | 60 s | +11.029749181602263 | +0.352781% |
| TG023701_P2 | 2209 | 60 s | +15.415871544973099 | +0.653250% |
| TG023701_P3 | 2528 | 60 s | +61.514729501873468 | +1.502999% |
| TG023701_P4 | 2581 | 60 s | +15.370472148046623 | +0.534193% |
| TG023701_P5 | 2761 | 60 s | +29.757440687203143 | +1.089442% |
| TG023701_P6 | 2833 | 60 s | +9.187940675968894 | +0.224409% |
| TG023701_P7 | 3044 | 60 s | +11.554082508851558 | +0.282332% |
| TG023701_P8 | 3133 | 60 s | +59.493137161459714 | +1.504279% |
| TG023701_N0 | 975 | 60 s | -17.154258654577312 | -0.433973% |
| TG023701_N1 | 1511 | 120 s | -10.622953693161483 | -0.187652% |
| TG023701_N2 | 1587 | 60 s | -9.189141427759484 | -0.224489% |
| TG023701_N3 | 2679 | 60 s | -21.763188969336206 | -0.532478% |
| TG023701_N4 | 3264 | 60 s | -8.693767275408362 | -0.212390% |

Scores are not Gaussian significance. Both visits' complete signed sets were
checked; all 14 representatives are in CH_PR100011_TG023701_V0300. The second
visit has no eligible crossing and receives no image acquisition. Its large
displayed point at row 66 is too close to the end for complete context; the
null result applies only to its 84 eligible windows. The two displayed >3%
points at first-visit rows 3307/3308 fail the original status/context rule.
They are not newly selected, scored or substituted by this image follow-up.

## Scope and method

The metadata-only preflight established **814 unique CAL/COR exposure joins**
for the 407 fixed L2 context rows, with <=1 ms MJD/BJD differences and exact UTC
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

All nine inherited image tests plus two native 60-second-cadence two-row
known-answer tests run before payload access (11 tests). They protect signed
event sums, guards, masks, brightness preservation and both conventions.
Scientific functions and gates are unchanged. The independent
struct/long-double/scalar-normal-equation audit checks source ranges and
hashes, metadata joins, masks, event maps, fits and classifications:

- numerical comparisons: **{count['numeric']:,}**;
- exact checks: **{count['exact']:,}**;
- disagreements: **{len(audit['disagreements'])}**.

LS8AQ's L2 audit remains PASS. Historical LS8B's original FAIL and later
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
