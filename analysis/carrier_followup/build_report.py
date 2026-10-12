#!/usr/bin/env python3
"""Render concise Danish results directly from authenticated saved outputs."""
from pathlib import Path
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Image,Table,TableStyle,PageBreak

ROOT=Path(__file__).resolve().parent.parent;B=ROOT/'carrier_followup';O=B/'delivery';O.mkdir(exist_ok=True)
targets=['HIP97319','HIP97461','HIP97663']
read=lambda p:json.loads(p.read_text())
results={t:read(B/'ranking'/t/'RESULT.json') for t in targets}
selected=read(B/'ranking/SELECTED_TOP9.json')
context=read(B/'context/results/CONTEXT_PROFILES.json')
sq=read(B/'qa/selection/QA_RECEIPT.json');cq=read(B/'qa/context/QA_RECEIPT.json')
assert sq['status'].startswith('PASS') and cq['status'].startswith('PASS')
assert context['new_distinct_fixed_profile_queries']==0
recovered=[]
for t in targets:
    cores=[c for c in results[t]['core_summaries'] if c['original_coremax_DC_contact']]
    best=max(cores,key=lambda c:c['eligible_maximum']['score'])['eligible_maximum']
    recovered.append({'primary_target':t,'old_DC_core_count':len(cores),
        'eligible_recovered_winners':sum(c['eligible_DC_untouched_carriers'] for c in cores),
        'strongest_recovered_score':best['score'],'strongest_recovered_frequency_MHz':best['frequency_hz_at_own_first_midpoint']/1e6,
        'third_selected_score':results[t]['TOP3'][-1]['score'],
        'separated100_last_raw_rank':results[t]['prefix_completeness']['actual_raw_rank_of_last_separated_choice']})
assert sum(r['eligible_recovered_winners'] for r in recovered)==55539
rows=[];scans=['epoch1_on','epoch1_off','epoch2_on','epoch2_off','epoch3_on','epoch3_off']
for track in selected['records']:
    tid=track['primary_target']+'_rank'+str(track['exploratory_selection_rank'])
    profiles={p['context_scan_id']:p for p in context['selected_profiles'] if p['template_id']==tid}
    assert len(profiles)==6 and all(p['query_disposition']=='HASH_PINNED_BASELINE_REUSE' for p in profiles.values())
    row={'primary_target':track['primary_target'],'rank':track['exploratory_selection_rank'],'raw_rank':track['raw_rank'],
        'frequency_MHz':track['frequency_hz_at_own_first_midpoint']/1e6,'drift_Hz_s':track['drift_hz_s'],
        'width_channels':track['width_channels'],'original_score':track['score'],'contexts_reused':True}
    row.update({s:profiles[s]['source_fixed_profile']['fixed_robust_box_track_score'] for s in scans});rows.append(row)
for name,data in [('SELECTED9_REUSED_CONTEXT54.csv',rows),('RECOVERED_FROM_DC_CORES.csv',recovered)]:
    with (O/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)

palette=['#2176a6','#b45823','#64852f'];fig,(ax,bx)=plt.subplots(1,2,figsize=(11,4.3),gridspec_kw={'width_ratios':[1.5,1]})
for t,c in zip(targets,palette):
    ax.plot(range(1,101),[r['score'] for r in results[t]['raw_TOP100']],color=c,alpha=.45,lw=1.2,ls=':')
    ax.plot(range(1,101),[r['score'] for r in results[t]['frequency_separated_TOP100']],color=c,lw=1.8,label=t)
ax.set_title('Gemte scorer i TOP100',fontsize=13);ax.set_xlabel('Rang i den respektive liste');ax.set_ylabel('Empirisk robust box-score');ax.grid(alpha=.18);ax.legend(fontsize=9)
ax.text(.03,.96,'Fuldt optrukket: kanalafstand >3\nPrikket: rå rangering',transform=ax.transAxes,va='top',fontsize=8.5)
x=np.arange(3);bx.bar(x-.16,[r['strongest_recovered_score'] for r in recovered],.3,color='#a1b9c7',label='Bedste genfundne vinder')
bx.bar(x+.16,[r['third_selected_score'] for r in recovered],.3,color='#244e66',label='Valgt rang 3')
bx.set_xticks(x,['97319','97461','97663']);bx.set_xlabel('OFF-stjerne (HIP)');bx.set_title('Genfundne valg under top 3',fontsize=13);bx.set_ylim(0,7.5);bx.grid(axis='y',alpha=.18);bx.set_axisbelow(True);bx.legend(fontsize=8,loc='upper left')
fig.text(.5,.01,'Listerne er beskrivende; rang og score er ikke SNR, sigma, falskalarmrate eller antal uafhængige kilder.',ha='center',fontsize=8.5)
fig.tight_layout(rect=(0,.06,1,1));plot=O/'SETI_KANALMAKSIMA_RANGLISTER_2026-10-12.png';fig.savefig(plot,dpi=180);plt.close(fig)

summary={'cached_carrier_winners':9375744,'DC_contacting_winners':5901,'eligible_winners':9369843,
    'original_map_files_verified':2289,'original_coremax_tuples_verified':2289,
    'previous_selected_tuples_preserved':9,'new_selected_tuples':0,'DC_core_eligible_winners_recovered':55539,
    'selected_logical_templates':9,'distinct_normalized_templates':8,'hash_reused_logical_contexts':54,
    'hash_reused_physical_contexts':48,'new_fixed_profile_queries':0,'new_normalizations':0,
    'selection_QA_checks':sq['counts']['checks'],'selection_QA_mismatches':0,
    'recovered_by_target':recovered,'new_telescope_requests':0,'cost_DKK':0,
    'original_AB':'FAIL_CLOSED','qualified_SETI_detection':False,
    'scope_limits':'All declared cached winning paths only; discarded carriers may retain unexamined nonwinning hypotheses.'}
(O/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
fonts=Path('/usr/share/fonts/truetype/dejavu')
pdfmetrics.registerFont(TTFont('DVS',str(fonts/'DejaVuSans.ttf')));pdfmetrics.registerFont(TTFont('DVS-Bold',str(fonts/'DejaVuSans-Bold.ttf')))
pdfmetrics.registerFontFamily('DVS',normal='DVS',bold='DVS-Bold',italic='DVS',boldItalic='DVS-Bold')
sty=getSampleStyleSheet()
for n in ['Title','BodyText','Heading2']:sty[n].fontName='DVS';sty[n].textColor=colors.HexColor('#18394c')
sty['Title'].fontSize=21;sty['Title'].leading=27;sty['Title'].spaceAfter=12
sty['BodyText'].fontSize=9.3;sty['BodyText'].leading=13;sty['BodyText'].spaceAfter=8
sty['Heading2'].fontSize=12;sty['Heading2'].leading=16;sty['Heading2'].spaceBefore=9;sty['Heading2'].spaceAfter=7
P=lambda s:Paragraph(s,sty['BodyText'])
story=[Paragraph('SETI: alle 9,38 millioner kanalmaksima',sty['Title']),P('12. oktober 2026 | Global udvælgelse blandt gemte vinderbaner fra 28. april 2017'),
    P('<b>Den globale udvælgelse giver præcis de samme ni spor som før.</b> Alle 9.375.744 gemte kanalmaksima blev kontrolleret mod den fastlåste DC-geometri. 5.901 vinderbaner rammer DC; 9.369.843 passerer kontrollen. Ingen ny detektorsøgning blev udført. Resultatet afklarer, at udvælgelsen af ét maksimum pr. kerne ikke skjulte et bedre top-3-valg uden DC-kontakt inden for denne faste regel.'),
    P('<b>55.539 vinderbaner uden DC-kontakt blev genfundet i de 15 kerner med et DC-ramt kernemaksimum.</b> Deres stærkeste scorer er 5,424, 5,557 og 5,904 pr. OFF-stjerne. Alle ligger under stjernens tredje valgte score. Det siger noget om denne rangering; det afgør ikke signalernes oprindelse.'),
    Image(str(plot),width=499,height=195),Paragraph('Hvad er udvidet?',sty['Heading2']),
    P('Før blev 2.289 kernemaksima kontrolleret. Nu er alle 4.096 carriers i hvert af de samme 2.289 kort gennemgået. Hver carrier bidrager kun med sin allerede gemte vinder over 785 drifter og bredderne 1 og 3 bins. Original frekvens, drift, bredde og score er bevaret. Der er ingen ny observation eller frekvensdækning.'),
    P('Der bevares en rå TOP700 og rå TOP100 pr. OFF-stjerne samt en global TOP100 med mere end tre referencebins mellem valgene. De sidstnævnte lister når deres 100. valg ved rå rang 110, 104 og 105. Et dokumenteret maksimum på rå rang 694 viser, at den gemte TOP700 er tilstrækkelig. Kanalafstand er en geometriregel og dokumenterer ikke forskellige fysiske sendere.'),
    Paragraph('Uafhængig kontrol',sty['Heading2']),P('En separat beregning kontrollerede alle 2.289 kort, alle 9.375.744 vinderbaner, de tidligere kernemaksima, de globale lister og CSV-filer. 197.106 sammenligninger bestod uden afvigelser. Den bruger en separat rækkevis geometrikontrol og sorteret sammenfletning frem for producentens heap.'),PageBreak(),
    Paragraph('De ni valg er uændrede',sty['Heading2'])]
tab=[['OFF-stjerne/rang','Frekvens MHz','Drift Hz/s','Bredde','Gemt score']]
for r in rows:
    d=0. if abs(r['drift_Hz_s'])<1e-9 else r['drift_Hz_s']
    tab.append([r['primary_target']+' #'+str(r['rank']),f'{r["frequency_MHz"]:.9f}',f'{d:+.6f}',str(r['width_channels']),f'{r["original_score"]:.5f}'])
t=Table(tab,colWidths=[121,155,93,47,83],repeatRows=1);t.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'DVS'),('FONTSIZE',(0,0),(-1,-1),8),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5eef3')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f3f7f9')]),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('ALIGN',(1,1),(-1,-1),'RIGHT')]))
story += [t,P('Frekvensen refererer til udvælgelsesscanningens første integrationsmidtpunkt. Tabellen viser drift nær nul afrundet til nul; den oprindelige flydende værdi er bevaret i geometri, beregning og CSV.'),
    Paragraph('54 eksisterende råprofiler genbruges',sty['Heading2']),
    P('Alle ni valg matcher de tidligere målte baner præcist, inklusive normaliseringskerne og de 16 afrundede kanalcentre i hver af de seks scanninger. De 54 logiske kontekstprofiler genbruges med originale bytehashes; de svarer til otte måleskabeloner og 48 fysiske profiler. Der er nul nye råmålinger og nul nye normaliseringer i dette trin. De ni egne scorer blev kontrolleret direkte mod de oprindelige per-carrier-kort.'),
    P('Den tidligere stationære komponent ved 2300 MHz giver positive faste scorer i alle seks scanninger på fire stjerneretninger; stjerneeksklusivitet er derfor ikke etableret. Syv øvrige spor forbliver ubekræftede. Forskellen mellem eget udvalg og andre scanninger er påvirket af, at egen scanning allerede valgte frekvens, drift og bredde.'),
    P('En første kontekstkontrol krævede en snæver rettelse af kontrollens format for geometri-ID. De originale data, scorer og kanalcentre stemte allerede. Den første kvittering er bevaret. Metadata-, hash- og identitetskontrollen samt ni sammenligninger med gemte scorer blev gentaget med dokumenterede kodehashes. Ingen producentberegning eller råscore blev genberegnet.'),
    Paragraph('Afgrænsning og reproduktion',sty['Heading2']),
    P('ZIP-pakken indeholder alle 2.289 oprindelige kort, ranglister, kode, scopes, kontrolkvitteringer og de 48 tidligere fulde normaliseringscrops. Rangeringen kan genkontrolleres med Python og NumPy i en ny outputmappe. En særskilt kode og tidligere PASS-kvittering bevarer muligheden for at genberegne de gamle råprofiler fra crops. De fulde originale HDF5-filer er ikke med i pakken.'),
    P('En vinderhypotese med DC-kontakt kan stadig skjule en ren, ikke-vindende drift- eller breddehypotese ved samme carrier. De oprindeligt manglende kerner forbliver uden for domænet. Uden DC-kontakt betyder ikke fri for anden interferens. Scorerne er ikke kalibreret SNR, sigma eller falskalarmrate, og ingen kvalificeret SETI-detektion er etableret.'),
    P('<b>0 DKK; nul nye teleskoprequests.</b> Original A/B er fortsat FAIL_CLOSED, og de beskyttede 2016-kontroller forbliver lukkede. Planens formelle checkpoint er 20. oktober 2026.')]
def footer(c,d):c.setFont('DVS',7);c.setFillColor(colors.HexColor('#617b8b'));c.drawString(43,27,'SETI | Martin Andersen | 12. oktober 2026');c.drawRightString(553,27,str(d.page))
pdf=O/'SETI_KANALMAKSIMA_2026-10-12.pdf'
SimpleDocTemplate(str(pdf),title='SETI: global udvælgelse af gemte kanalmaksima',author='Martin Andersen / SETI-projektet',pagesize=(595.28,841.89),leftMargin=43,rightMargin=43,topMargin=36,bottomMargin=40).build(story,onFirstPage=footer,onLaterPages=footer)
print(json.dumps({'pdf':str(pdf),'plot':str(plot),'summary':summary}))
