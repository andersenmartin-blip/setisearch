#!/usr/bin/env python3
"""Render frozen DC-untouched follow-up outputs; no new raw queries."""
from pathlib import Path
import json,csv,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import Rectangle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

B=Path(__file__).resolve().parent;O=B/'delivery';O.mkdir(exist_ok=True)
read=lambda x:json.loads((B/x).read_text())
selection=read('ranking/SELECTED_TOP9.json');context=read('crossscan/results/CONTEXT_PROFILES.json')
qa=read('qa/context/QA_RECEIPT.json');sq=read('qa/selection/QA_RECEIPT.json')
scans=['epoch1_on','epoch1_off','epoch2_on','epoch2_off','epoch3_on','epoch3_off']
ids=list(dict.fromkeys(x['template_id'] for x in context['profiles']))
group={k:[p for p in context['profiles'] if p['template_id']==k] for k in ids}
own={k:next(p for p in group[k] if p['is_own_primary_scan']) for k in ids}
M=np.array([[next(p for p in group[k] if p['context_scan_id']==s)['fixed_robust_box_track_score'] for s in scans] for k in ids])
stationary=[k for k in ids if abs(own[k]['selected_original_record']['frequency_hz_at_own_first_midpoint']-2300000000.373)<.01]
remaining=[k for k in ids if k not in stationary]
other=np.array([p['fixed_robust_box_track_score'] for k in remaining for p in group[k] if not p['is_own_primary_scan']])
assert len(stationary)==2 and len(remaining)==7 and len(other)==35
fig,ax=plt.subplots(figsize=(11,5.8))
im=ax.imshow(M,cmap='RdBu_r',norm=TwoSlopeNorm(vmin=-3,vcenter=0,vmax=10),aspect='auto')
ax.set_yticks(range(9),[k.replace('_rank',' #') for k in ids],fontsize=10)
labels=['HIP98505 A1','HIP97319 B1','HIP98505 A2','HIP97461 B2','HIP98505 A3','HIP97663 B3']
ax.set_xticks(range(6),labels,rotation=18,ha='right',fontsize=9)
for i,k in enumerate(ids):
    j=scans.index(own[k]['context_scan_id']);ax.add_patch(Rectangle((j-.48,i-.48),.96,.96,fill=False,edgecolor='#f2cf53',linewidth=2))
    for j,v in enumerate(M[i]):ax.text(j,i,f'{v:.2f}',ha='center',va='center',color='white' if v>5.7 else '#102f47',fontsize=10)
ax.set_title('Ni faste spor i alle seks oprindelige scanninger',fontsize=16,pad=13)
cb=fig.colorbar(im,ax=ax,fraction=.036,pad=.03);cb.set_label('Empirisk robust box-score',fontsize=10)
fig.text(.5,.015,'Gul ramme: sporets egen udvælgelsesscanning. 2300 MHz-sporet er samme fysiske bane i to logiske rækker.',ha='center',fontsize=9)
fig.tight_layout(rect=(0,.07,1,1));matrix=O/'SETI_DCFRIE_KONTEKST_2026-10-12.png';fig.savefig(matrix,dpi=180);plt.close(fig)

R=np.array([own[k]['row_score_contribution'] for k in ids]);fig,ax=plt.subplots(figsize=(11,4.8))
vmax=float(max(abs(R.min()),abs(R.max())));im=ax.imshow(R,aspect='auto',cmap='RdBu_r',vmin=-vmax,vmax=vmax)
ax.set_yticks(range(9),[k.replace('_rank',' #') for k in ids],fontsize=10);ax.set_xticks([0,3,6,9,12,15],['1','4','7','10','13','16']);ax.set_xlabel('Oprindelig integrationsrække (18,254 sekunder pr. række)')
ax.set_title('Tidsbidrag i sporernes egne udvælgelsesscanninger',fontsize=15)
fig.colorbar(im,ax=ax,fraction=.035,pad=.03,label='Bidrag til den faste score')
fig.text(.5,.015,'Alle rækker blev brugt til at vælge sporene; dette er beskrivende diagnose og ikke uafhængig signalevidens.',ha='center',fontsize=9)
fig.tight_layout(rect=(0,.07,1,1));rowsfig=O/'SETI_DCFRIE_TIDSBIDRAG_2026-10-12.png';fig.savefig(rowsfig,dpi=180);plt.close(fig)

tables=[]
for k in ids:
    p=own[k];t=p['selected_original_record'];row={'template_id':k,'primary_target':t['primary_target'],'selection_rank':t['exploratory_selection_rank'],'native':t['native_chunk_index'],'core_q':t['core_q'],'frequency_MHz_at_own_reference':t['frequency_hz_at_own_first_midpoint']/1e6,'drift_Hz_s':t['drift_hz_s'],'width_channels':t['width_channels'],'original_selected_score':t['score'],'own_fixed_score':p['fixed_robust_box_track_score'],'positive_rows':p['positive_row_count'],'largest_positive_row_fraction':p['positive_row_contribution_max_fraction']}
    row.update({s:float(M[ids.index(k),j]) for j,s in enumerate(scans)});tables.append(row)
with (O/'SELECTED9_AND_CONTEXT54.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(tables[0]));w.writeheader();w.writerows(tables)
summary={'selected_logical_tracks':9,'distinct_physical_templates':8,'context_profiles':54,'distinct_physical_context_geometries':48,'logical_duplicate_contexts':6,'cached_coremax_records':2289,'excluded_DC_contact_coremax_records':15,'eligible_existing_coremax_records':2274,'stationary_frequency_MHz':2300.000000372529,'stationary_six_scan_fixed_scores':M[ids.index(stationary[0])].tolist(),'remaining_logical_tracks':7,'remaining_own_score_range':[min(own[k]['fixed_robust_box_track_score'] for k in remaining),max(own[k]['fixed_robust_box_track_score'] for k in remaining)],'remaining_other_35_fixed_score_range':[float(other.min()),float(other.max())],'own_positive_row_count_range':[min(own[k]['positive_row_count'] for k in ids),max(own[k]['positive_row_count'] for k in ids)],'own_max_positive_row_fraction_range':[min(own[k]['positive_row_contribution_max_fraction'] for k in ids),max(own[k]['positive_row_contribution_max_fraction'] for k in ids)],'normalization_full_recomputed_by_independent_QA':48,'new_telescope_requests':0,'cost_DKK':0,'qualified_SETI_detection':False,'original_AB':'FAIL_CLOSED','new_observation_or_frequency_coverage':False}
(O/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')

fonts=Path('/usr/share/fonts/truetype/dejavu')
pdfmetrics.registerFont(TTFont('DVS',str(fonts/'DejaVuSans.ttf')));pdfmetrics.registerFont(TTFont('DVS-Bold',str(fonts/'DejaVuSans-Bold.ttf')))
pdfmetrics.registerFontFamily('DVS',normal='DVS',bold='DVS-Bold',italic='DVS',boldItalic='DVS-Bold')
sty=getSampleStyleSheet()
for n in ['Title','BodyText','Heading2']:sty[n].fontName='DVS';sty[n].textColor=colors.HexColor('#18394c')
sty['Title'].fontSize=21;sty['Title'].leading=27;sty['Title'].spaceAfter=13
sty['BodyText'].fontSize=9.3;sty['BodyText'].leading=13;sty['BodyText'].spaceAfter=8
sty['Heading2'].fontSize=12;sty['Heading2'].leading=16;sty['Heading2'].spaceBefore=9;sty['Heading2'].spaceAfter=7
P=lambda x:Paragraph(x,sty['BodyText'])
story=[Paragraph('SETI: ni spor efter DC-udvælgelsen',sty['Title']),P('12. oktober 2026 | Faste råmålinger i seks scanninger fra 28. april 2017'),P('<b>Ni tidligere gemte kernemaksima uden DC-kontakt er nu fulgt i alle seks oprindelige scanninger.</b> Den stationære komponent ved 2300,000000373 MHz blev valgt i to OFF-scanninger, men svarer til én fysisk frekvensbane. Den giver positive faste scorer i alle seks scanninger på fire stjerneretninger. Stjerneeksklusivitet er derfor ikke etableret. De ni logiske valg svarer til otte måleskabeloner; de 54 profiler omfatter 48 forskellige boksgeometrier.'),P(f'<b>Syv andre spor forbliver uafklarede.</b> Deres egne scorer er {summary["remaining_own_score_range"][0]:.3f}-{summary["remaining_own_score_range"][1]:.3f}, mens de 35 målinger i andre scanninger ligger {other.min():.3f}-{other.max():.3f}. Egenscanningerne valgte allerede sporene over frekvens, drift og bredde; denne forskel er ikke uafhængig signifikans.'),Image(str(matrix),width=499,height=263),P('Scorerne er empiriske robuste box-scorer. Farver og værdier er ikke kalibreret SNR, sigma, falskalarmrate eller en himmelkildeklassifikation. Flere stjerneretninger i samme historiske besøg er ikke uafhængige genobservationer af et mål.'),Paragraph('Udvælgelse med kendt afgrænsning',sty['Heading2']),P('2.289 oprindelige kernemaksima blev kontrolleret mod deres gemte kanalgeometri. 15 ramte en af de tre faste DC-bins; 2.274 var uden kontakt. De tre højest rangerede blev valgt pr. OFF-stjerne med en på forhånd fastlagt tieorden og mindst fire bins mellem referencekanalerne. Ingen detektorsøgning blev gentaget.'),P('Udvalget omfatter kun det tidligere maksimum pr. kerne. Det genfinder ikke rene alternative hypoteser, som et DC-forurenet maksimum kan have skjult. “Uden DC-kontakt” betyder ikke fri for anden radiointerferens. Ingen kvalificeret SETI-detektion er etableret.'),PageBreak(),Paragraph('De ni fastlåste spor',sty['Heading2'])]
tab=[['OFF-stjerne/rang','Frekvens MHz','Drift Hz/s','Bredde','Egen score']]
for r in tables:
    d=0. if abs(r['drift_Hz_s'])<1e-9 else r['drift_Hz_s'];tab.append([r['primary_target']+' #'+str(r['selection_rank']),f'{r["frequency_MHz_at_own_reference"]:.9f}',f'{d:+.6f}',str(r['width_channels']),f'{r["own_fixed_score"]:.5f}'])
t=Table(tab,colWidths=[121,155,93,47,83],repeatRows=1);t.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'DVS'),('FONTSIZE',(0,0),(-1,-1),8),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5eef3')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f3f7f9')]),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('ALIGN',(1,1),(-1,-1),'RIGHT')]))
story += [t,P('Frekvensen refererer til hver udvælgelsesscannings første integrationsmidtpunkt. Spor med drift måles i de andre scanninger ved at transportere hele den samme bane med faktiske starttider og pauser; der foretages ingen ny drift- eller breddeoptimering.'),Image(str(rowsfig),width=499,height=218),P(f'Alle ni egne profiler har 14-16 positive rækkebidrag. Den største række udgør {100*summary["own_max_positive_row_fraction_range"][0]:.1f}-{100*summary["own_max_positive_row_fraction_range"][1]:.1f} % af det samlede positive rækkebidrag. Det beskriver fordelingen i tidligere valgte spor og giver ikke ekstra bekræftelse.'),Paragraph('Kontrol, reproduktion og næste trin',sty['Heading2']),P('Uafhængig QA verificerede alle 18 kildefiler og 288 decoded rækkehashes. Alle 48 fulde normaliseringer blev genberegnet fra rådata med en separat median501-beregning, inklusive kernemedian, MAD og winsoriseret lokation. 54 profiler og de ni oprindelige scorer stemmer; største oprindelige scoreafvigelse er 1,24 x 10<super>-14</super>.'),P('48 komplette normaliseringscrops på i alt 37,25 MB er bevaret sammen med rå503-profiler, kode, scope og kontrolkvitteringer. De tillader en afgrænset numerisk reproduktion uden at kopiere de fulde originale HDF5-kilder. Det næste relevante søgetrin er at behandle alle gemte kanalmaksima, så rene alternative carriers i forurenede kerner også kan undersøges.'),P('<b>0 DKK; nul nye teleskoprequests.</b> Der er ingen ny observation eller frekvensdækning. Original A/B er fortsat FAIL_CLOSED; beskyttede 2016-kontroller forbliver lukkede. Planens formelle checkpoint er 20. oktober 2026.')]
def footer(c,d):c.setFont('DVS',7);c.setFillColor(colors.HexColor('#617b8b'));c.drawString(43,27,'SETI | Martin Andersen | 12. oktober 2026');c.drawRightString(553,27,str(d.page))
pdf=O/'SETI_DCFRIE_SPOR_2026-10-12.pdf';SimpleDocTemplate(str(pdf),title='SETI: ni DC-uberørte spor',author='Martin Andersen / SETI-projektet',pagesize=(595.28,841.89),leftMargin=43,rightMargin=43,topMargin=36,bottomMargin=40).build(story,onFirstPage=footer,onLaterPages=footer)
print(json.dumps({'pdf':str(pdf),'matrix':str(matrix),'time_contribution_plot':str(rowsfig),'summary':summary}))
