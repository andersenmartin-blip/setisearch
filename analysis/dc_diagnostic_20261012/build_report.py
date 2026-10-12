#!/usr/bin/env python3
"""Render the saved DC study; no original power or detector calls."""
from pathlib import Path
import json, hashlib, math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BASE=Path(__file__).resolve().parent
OUT=BASE/'delivery'; OUT.mkdir(exist_ok=True)
read=lambda p: json.loads((BASE/p).read_text())
templates=read('primary/results/FROZEN_TEMPLATE_ATTRIBUTION.json')['templates']
metrics=read('primary/results/DC_PATCH_METRICS.json')
rank=read('ranking/ANNOTATED_TOP120.json')
summary=metrics['deduplicated_summary']
with np.load(BASE/'primary/results/DC_RAW_PATCHES.npz',allow_pickle=False) as z:
    raw=z['raw_power'].astype(float); offsets=z['offsets_from_dc']; natives=z['native_dc_indices']
flanks=np.abs(offsets)>=16
normalized=raw/np.median(raw[:,:,flanks],axis=2)[:,:,None]
fig,axs=plt.subplots(1,3,figsize=(11.1,3.3),sharey=True)
freqs={170:2303.3203125,171:2300.390625,172:2297.4609375}
for ax,native in zip(axs,[170,171,172]):
    v=normalized[natives==native].reshape(-1,129)
    select=np.abs(offsets)<=8
    lo,hi=np.percentile(v,[10,90],axis=0)
    ax.fill_between(offsets[select],lo[select],hi[select],color='#c6dce7',label='10.-90. percentil')
    ax.plot(offsets[select],np.median(v,axis=0)[select],color='#175b78',marker='o',markersize=3,label='Median over 96 spektre')
    ax.axvline(0,color='#bc6332',linestyle='--',linewidth=1)
    ax.set_yscale('log');ax.set_ylim(.55,1000);ax.set_xticks([-8,-4,0,4,8])
    ax.set_title(f'{freqs[native]:.7f} MHz',fontsize=11)
    ax.set_xlabel('Fine kanaler fra DC-centret',fontsize=10)
    ax.grid(axis='y',alpha=.2);ax.spines[['top','right']].set_visible(False)
axs[0].set_ylabel('Råeffekt / lokal flankemedian',fontsize=10)
fig.suptitle('Tre faste linjer på instrumentets DC-kanaler',fontsize=15,fontweight='bold')
fig.text(.5,.01,'Hvert panel: 6 scanninger x 16 integrationer. Båndet er beskrivende variation, ikke et konfidensinterval.',ha='center',fontsize=9)
fig.tight_layout(rect=(0,.045,1,.93))
png=OUT/'SETI_DC_SPECTRA_2026-10-12.png';fig.savefig(png,dpi=190);plt.close(fig)

fontroot=Path('/usr/share/fonts/truetype/dejavu')
pdfmetrics.registerFont(TTFont('DejaVu',str(fontroot/'DejaVuSans.ttf')))
pdfmetrics.registerFont(TTFont('DejaVu-Bold',str(fontroot/'DejaVuSans-Bold.ttf')))
pdfmetrics.registerFontFamily('DejaVu',normal='DejaVu',bold='DejaVu-Bold',italic='DejaVu',boldItalic='DejaVu-Bold')
styles=getSampleStyleSheet()
for name in ['Normal','BodyText','Title','Heading1','Heading2']:
    styles[name].fontName='DejaVu';styles[name].textColor=colors.HexColor('#1e3544')
styles['Title'].fontSize=22;styles['Title'].leading=28;styles['Title'].spaceAfter=13
styles['BodyText'].fontSize=9.3;styles['BodyText'].leading=13;styles['BodyText'].spaceAfter=7
styles['Heading2'].fontSize=12;styles['Heading2'].leading=17;styles['Heading2'].spaceBefore=9
small=ParagraphStyle('Small',parent=styles['BodyText'],fontSize=8,leading=11)
p=lambda s:Paragraph(s,styles['BodyText'])
rows=[x['own_primary_profile'] for x in templates]
minfraction=min(x['positive_dc_cell_mass_fraction'] for x in rows)
remainders=[x['signed_remainder_score'] for x in rows]
story=[Paragraph('SETI: forklaring på de stærke stationære spor',styles['Title']),
       p('12. oktober 2026 | Eksplorativ analyse af seks historiske scanninger fra 28. april 2017'),
       p(f'<b>De tre dominerende linjer er stærkt forenelige med instrumentets dokumenterede DC-spidser.</b> De ligger præcist i midten af tre grove frekvenskanaler. Den enkelte DC-bin leverer mindst <b>{100*minfraction:.4f} %</b> af den positive standardiserede cellemasse i hver af de 18 oprindelige TOP3-skabeloner, målt i deres egne primærscanninger.'),
       p('<b>Ingen kvalificeret SETI-detektion.</b> Fortolkningen er en fysisk slutning ud fra geometri, rå spektralform og den officielle instrumentbeskrivelse. Den specifikke hardwareårsag er ikke direkte bevist.'),
       Paragraph('Resultaterne, der ændrer vurderingen',styles['Heading2']),
       p(f'Alle <b>{rank["counts"]["stored_records_annotated"]} gemte TOP20-poster</b> rammer en DC-bin i mindst én tidsrække. I <b>{summary["strict_center_peak_count_over288"]}/288 forskellige rækkespektre</b> er DC-centret større end hver af de øvrige 128 kanaler i det faste udsnit.'),
       p(f'Råeffekten i centret er <b>{summary["center_over_symmetric98_flank_median_over288"]["median"]:.2f} gange</b> den lokale flankemedian; spændet er {summary["center_over_symmetric98_flank_median_over288"]["min"]:.2f}-{summary["center_over_symmetric98_flank_median_over288"]["max"]:.2f}. Flankerne er de 98 faste kanaler med afstand 16-64 bins på hver side.'),
       Image(str(png),width=487,height=145)]
geo=[['Native','Frekvens (MHz)','Kildekanal','Afstand fra DC-bin']]
for n in [170,171,172]:geo.append([str(n),f'{freqs[n]:.7f}',str(n*1048576+524288),'0'])
t=Table(geo,colWidths=[49,132,146,160],hAlign='LEFT')
t.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'DejaVu'),('FONTSIZE',(0,0),(-1,-1),8),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8f0f4')),('BOTTOMPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#85a4b5'))]))
story.extend([Spacer(1,9),t,p('Afstanden mellem linjerne er præcist 2,9296875 MHz = 1.048.576 fine kanaler. Filens frekvensstart stemmer også med det offentliggjorte S-båndsgitter ved standardtuningen efter et helt antal grove kanaler.'),PageBreak(),Paragraph('Præcis attribution af de 18 udvalgte skabeloner',styles['Heading2']),p('Tabellen bevarer den oprindelige rang og score. “Rest” er summen af alle andre standardiserede celler i den samme oprindelige boks, med samme normalisering og nævner. Den er en algebraisk diagnose, ikke en ny søgning med DC fjernet.')])
tab=[['Bånd','OFF-stjerne','Rang','Opr. score','DC positiv masse','Rest']]
for x in rows:
    tr=x['selected_track'];tab.append([str(x['native_dc_index']),tr['primary_target'],str(tr['rank']),f'{x["saved_fixed_score"]:.2f}',f'{100*x["positive_dc_cell_mass_fraction"]:.4f} %',f'{x["signed_remainder_score"]:+.5f}'])
t=Table(tab,colWidths=[39,97,35,90,132,94],repeatRows=1,hAlign='LEFT')
t.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'DejaVu'),('FONTSIZE',(0,0),(-1,-1),7.7),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8f0f4')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f5f8fa')]),('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),('ALIGN',(2,1),(-1,-1),'RIGHT')]))
story.extend([t,Spacer(1,8),p(f'Restscorerne ligger mellem {min(remainders):+.5f} og {max(remainders):+.5f}, mens de oprindelige scorer er omkring 2.980-21.687. Små drifter kan få store scorer ved blot at krydse den samme stationære DC-bin i nogle af rækkerne.'),Paragraph('Kontrol og grænser',styles['Heading2']),p('108 faste kontekstprofiler er rekonstrueret fra de gemte rå503-kapsler og har bestået uafhængig numerisk QA. Rækkebokse matcher de tidligere værdier præcist; største scoreafvigelse er 3,64 x 10<super>-12</super>. 715.625 gentagne råcelleforekomster er bit-identiske. De 288 rækkespektre er deduplikeret efter fysisk kanal, scanning og række; de er ikke 288 uafhængige bekræftelser.'),p('Normaliseringen er betinget af de tidligere gemte fulde 16-række-konstanter. Ingen fuldkerne-normalisering eller detektorsøgning er gentaget. De 120 poster er tidligere eksponerede udvalg, ikke 120 uafhængige kilder. Tomme DC-uberørte TOP20-lister siger intet om skjulte svagere spor. Kortvarige burst4-vindere er ikke klassificeret her. Ingen kalibreret SNR eller FAP er fastlagt. Original A/B: FAIL_CLOSED; beskyttede 2016-kontroller forbliver lukkede.'),Paragraph('Kilder og fortsættelse',styles['Heading2']),Paragraph('Lebofsky m.fl.: <link href="https://seti.berkeley.edu/listen2019/BLdata2019.pdf" color="#175b78">Public data, formats, reduction and archiving</link>, tabel 4-5 og figur 10. Officiel <link href="https://blimpy.readthedocs.io/en/latest/blimpy.html#blimpy.waterfall.Waterfall.blank_dc" color="#175b78">blimpy DC-dokumentation</link> samt hashbundne kildekodesnapshots. Hele rå- og kodepakken bevarer reproduktion og uafhængige QA-kvitteringer.',small),p('Denne fase tilføjer ingen observation eller frekvensdækning. Ingen nye teleskoprequests; 0 DKK. Næste søgefase skal fastlægge en behandling af DC-bins og demonstrere signalgenfinding uden at forveksle aliaser med nye kilder. Det er ikke udført i denne fase. Planens formelle checkpoint er fortsat 20. oktober 2026.')])
pdf=OUT/'SETI_DC_RESULTAT_2026-10-12.pdf'
def footer(canvas,doc):
    canvas.setFont('DejaVu',7);canvas.setFillColor(colors.HexColor('#657c89'));canvas.drawString(44,28,'SETI | Martin Andersen | 12. oktober 2026');canvas.drawRightString(550,28,str(doc.page))
SimpleDocTemplate(str(pdf),title='SETI: DC-kanaler og stationære spor',author='Martin Andersen / SETI-projektet',pagesize=(595.28,841.89),leftMargin=44,rightMargin=44,topMargin=39,bottomMargin=43).build(story,onFirstPage=footer,onLaterPages=footer)
print(json.dumps({'pdf':str(pdf),'figure':str(png),'minimum_own_primary_dc_positive_fraction':minfraction}))
