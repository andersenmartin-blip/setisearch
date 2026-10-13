#!/usr/bin/env python3
"""Create the Danish ON-candidate report from final authenticated outputs."""
from pathlib import Path
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import Rectangle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Image,Table,TableStyle,PageBreak

ROOT=Path(__file__).resolve().parent.parent;B=ROOT/'on_cached';O=B/'delivery';O.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text())
selection=read(B/'ranking/SELECTED_TOP9.json');scope=read(B/'context/SCOPE.json')
matrix=read(B/'context/results/CONTEXT_PROFILES.json')
sq=read(B/'qa/selection/QA_RECEIPT.json');cq=read(B/'qa/context/QA_RECEIPT.json')
rp=read(B/'reproduction/REPRODUCTION_RECEIPT.json')
assert all(x['status'].startswith('PASS') for x in (sq,cq,rp))
scans=['epoch1_on','epoch1_off','epoch2_on','epoch2_off','epoch3_on','epoch3_off']
ids=[t['scan_id']+'_rank'+str(t['exploratory_selection_rank']) for t in selection['records']]
profiles={(p['template_id'],p['context_scan_id']):p for p in matrix['selected_profiles']}
assert len(profiles)==54 and len(ids)==9
M=np.asarray([[profiles[k,s]['source_fixed_profile']['fixed_robust_box_track_score'] for s in scans] for k in ids])
own={k:profiles[k,t['scan_id']]['source_fixed_profile'] for k,t in zip(ids,selection['records'])}
reuse={l['template_id']:l['reuse_baseline'] for l in scope['selected_logical_templates']}
newids=[k for k in ids if not reuse[k]]
assert len(newids)==8
other_on=[];off=[];contacts=[];rows=[]
for k,t in zip(ids,selection['records']):
    row={'template_id':k,'origin_scan':t['scan_id'],'selection_rank':t['exploratory_selection_rank'],
         'frequency_MHz_at_own_first_midpoint':t['frequency_hz_at_own_first_midpoint']/1e6,
         'drift_Hz_s':t['drift_hz_s'],'width_channels':t['width_channels'],'original_selected_score':t['score'],
         'own_fixed_score':own[k]['fixed_robust_box_track_score'],'baseline_reused':reuse[k],
         'positive_own_rows':own[k]['positive_row_count'],'largest_positive_own_row_fraction':own[k]['positive_row_contribution_max_fraction']}
    for j,s in enumerate(scans):
        row[s]=float(M[ids.index(k),j]);p=profiles[k,s]['source_fixed_profile']
        hit=p.get('DC_contact_rows_any_frozen_center',[])
        if hit:contacts.append({'template_id':k,'scan_id':s,'rows':hit})
        if k in newids:
            if s.endswith('_off'):off.append(row[s])
            elif s!=t['scan_id']:other_on.append(row[s])
    rows.append(row)
assert len(other_on)==16 and len(off)==24
with (O/'SELECTED9_CONTEXT54.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
newown=[own[k]['fixed_robust_box_track_score'] for k in newids]
summary={'ON_cached_maps':2298,'ON_cached_carrier_winners':9412608,'DC_contacting_winners':7083,'eligible_winners':9405525,
    'selected_logical_templates':9,'distinct_selected_normalized_templates':9,'new_selected_templates':8,'baseline_reused_templates':1,
    'selected_logical_contexts':54,'new_fixed_profiles':matrix['new_distinct_fixed_profile_queries'],'baseline_reused_profiles':6,
    'new_full16_normalizations':matrix['new_full16_normalizations'],'new_raw_crops':len(matrix['new_normalization_crops']),
    'new8_own_score_range':[min(newown),max(newown)],'new8_other16_ON_score_range':[min(other_on),max(other_on)],
    'new8_OFF24_score_range':[min(off),max(off)],'transported_DC_contact_profiles':len(contacts),
    'new8_own_positive_row_range':[min(own[k]['positive_row_count'] for k in newids),max(own[k]['positive_row_count'] for k in newids)],
    'new8_own_largest_positive_row_fraction_range':[min(own[k]['positive_row_contribution_max_fraction'] for k in newids),max(own[k]['positive_row_contribution_max_fraction'] for k in newids)],
    'selection_QA_checks':sq['counts']['checks'],'new_telescope_requests':0,'cost_DKK':0,'original_AB':'FAIL_CLOSED','qualified_SETI_detection':False}
(O/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
fig,ax=plt.subplots(figsize=(11,5.7));im=ax.imshow(M,aspect='auto',cmap='RdBu_r',norm=TwoSlopeNorm(vmin=-3,vcenter=0,vmax=10))
ax.set_yticks(range(9),[k.replace('epoch','ON').replace('_on_rank',' #')+(' *' if reuse[k] else '') for k in ids],fontsize=10)
ax.set_xticks(range(6),['ON1','OFF1','ON2','OFF2','ON3','OFF3'],fontsize=10)
for i,(k,t) in enumerate(zip(ids,selection['records'])):
    j=scans.index(t['scan_id']);ax.add_patch(Rectangle((j-.48,i-.48),.96,.96,fill=False,edgecolor='#f2cf53',linewidth=2))
    for j,v in enumerate(M[i]):
        tag='†' if any(c['template_id']==k and c['scan_id']==scans[j] for c in contacts) else ''
        ax.text(j,i,(f'{v:.2f}' if abs(v)<100 else f'{v:.1f}')+tag,ha='center',va='center',color='white' if v>5.7 else '#18394c',fontsize=10)
ax.set_title('Målstjernens ni faste valg i seks scanninger',fontsize=16,pad=14)
fig.colorbar(im,ax=ax,fraction=.035,pad=.03,label='Empirisk robust box-score; farver afgrænset til [-3,10]')
caption='Gul ramme: egen udvælgelsesscanning. * Genbrugt 2300 MHz-bane.'
if contacts:caption+=' † Kontakt med DC i transporteret boks.'
fig.text(.5,.014,caption,ha='center',fontsize=8.5)
fig.tight_layout(rect=(0,.065,1,1));plot=O/'SETI_MAALSTJERNE_KONTEKST_2026-10-13.png';fig.savefig(plot,dpi=180);plt.close(fig)

fonts=Path('/usr/share/fonts/truetype/dejavu');pdfmetrics.registerFont(TTFont('DVS',str(fonts/'DejaVuSans.ttf')));pdfmetrics.registerFont(TTFont('DVS-Bold',str(fonts/'DejaVuSans-Bold.ttf')))
pdfmetrics.registerFontFamily('DVS',normal='DVS',bold='DVS-Bold',italic='DVS',boldItalic='DVS-Bold')
sty=getSampleStyleSheet()
for n in ['Title','BodyText','Heading2']:sty[n].fontName='DVS';sty[n].textColor=colors.HexColor('#18394c')
sty['Title'].fontSize=21;sty['Title'].leading=27;sty['Title'].spaceAfter=12
sty['BodyText'].fontSize=9.3;sty['BodyText'].leading=13;sty['BodyText'].spaceAfter=8
sty['Heading2'].fontSize=12;sty['Heading2'].leading=16;sty['Heading2'].spaceBefore=9;sty['Heading2'].spaceAfter=7
P=lambda s:Paragraph(s,sty['BodyText'])
f=lambda x:f'{x:.3f}'.replace('.',',')
story=[Paragraph('SETI: nye spor fra målstjernen',sty['Title']),P('13. oktober 2026 | HIP98505 / HD189733 | Eksisterende besøg fra 28. april 2017'),
 P('<b>Målstjernens tre ON-scanninger har nu fået deres første globale DC-bevidste udvælgelse i de tre bevarede native-bånd.</b> Alle 9.412.608 gemte carrier-vindere i 2.298 kort er kontrolleret. 7.083 vinderbaner rammer DC; 9.405.525 passerer geometrireglen. Tre valg pr. ON-scanning blev fastlåst. Ét er den kendte fælles 2300 MHz-komponent; otte er nye i forhold til den tidligere OFF-opfølgning.'),
 P(f'<b>De otte nye valg er målt ved uændret frekvensbane i alle seks scanninger.</b> Deres egne faste scorer ligger fra {f(min(newown))} til {f(max(newown))}. De 16 målinger i de andre ON-scanninger ligger fra {f(min(other_on))} til {f(max(other_on))}; de 24 OFF-målinger fra {f(min(off))} til {f(max(off))}. Dette er beskrivende målinger efter udvælgelse. De etablerer ingen uafhængig genfinding eller kildeoprindelse.'),
 Image(str(plot),width=499,height=258),
 P('De tre ON-scanninger peger mod samme målstjerne. OFF-scanningerne peger mod tre andre stjerner. Alle seks stammer fra ét historisk besøg; dette er ikke tre nye observationsbesøg eller blind validering. Farver og scorer er ikke kalibreret SNR, sigma eller falskalarmrate.'),
 Paragraph('Hvad er faktisk nyt?',sty['Heading2']),
 P(f'48 nye faste råprofiler og {summary["new_full16_normalizations"]} fulde normaliseringer er bevaret. Seks profiler for 2300 MHz-banen genbruges med eksakte kanalcentre, normaliseringskerne og bytehashes. Målstjernens rådata og tidligere detektorkort er eksisterende; der er ingen ny observation, frekvensdækning eller gentagelse af drift-/breddegridet.'),
 P('Den stationære 2300 MHz-komponent giver positive faste scorer i alle seks scanninger og er tidligere påvist i flere stjerneretninger. Stjerneeksklusivitet er ikke etableret. De øvrige otte valg forbliver ubekræftede; egen scanning valgte allerede deres frekvens, drift og bredde.'),PageBreak(),Paragraph('De ni fastlåste valg',sty['Heading2'])]
tab=[['ON/rang','Frekvens MHz','Drift Hz/s','Bredde','Egen score']]
for r in rows:
    d=0. if abs(r['drift_Hz_s'])<1e-9 else r['drift_Hz_s'];label=r['origin_scan'].replace('epoch','ON').replace('_on','')+' #'+str(r['selection_rank'])+(' *' if r['baseline_reused'] else '')
    tab.append([label,f'{r["frequency_MHz_at_own_first_midpoint"]:.9f}',f'{d:+.6f}',str(r['width_channels']),f'{r["own_fixed_score"]:.5f}'])
t=Table(tab,colWidths=[121,155,93,47,83],repeatRows=1);t.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'DVS'),('FONTSIZE',(0,0),(-1,-1),8),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5eef3')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f3f7f9')]),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('ALIGN',(1,1),(-1,-1),'RIGHT')]))
story += [t,P('* Eksakt genbrug af tidligere målt 2300 MHz-geometri. Referencen er hver ON-scannings første integrationsmidtpunkt. Visning af drift nær nul ændrer ikke den oprindelige flydende driftværdi i beregning eller CSV.'),
 Paragraph('Udvælgelse og tidsreference',sty['Heading2']),
 P('Det tidligere ON-arbejde havde allerede søgt alle 766 referencekerner pr. scanning. Den nye fase rangerer deres gemte vinderbaner globalt med original score og fast tieorden, efter inklusiv kontrol mod tre kendte DC-bins. Der bevares rå TOP700 og TOP100 samt TOP100 med mere end tre referencebins mellem valgene. De sidstnævnte lister er komplette ved rå rang 107, 109 og 105, under det dokumenterede maksimum 694.'),
 P('De fire oprindelige producentfamilier er kontrolleret: 16 rækker, 785 drifter, bredde 1/3, 4.096 normaliseringskanaler og median501. Hver bruger egen første-midtpunktsreference. Transporten bruger faktiske starttider og pauser; ingen ny drift, bredde eller frekvens optimeres i kontekstscanningerne. Original fysisk normaliseringskerne bevares.'),
 Paragraph('Kontrol og reproduktion',sty['Heading2']),
 P('Uafhængig udvælgelseskontrol bestod 231.099 eksakte sammenligninger af alle kort, geometrier og ranglister. Ny rå-QA kontrollerer de 18 kompakte kildefiler, 288 originale decoded rækkehashes og alle nye normaliseringer med en separat fuld median501-beregning. Nye profiler, egne gemte scorer og de seks genbrugte profiler stemmer med deres dokumenterede inputs. En indledende QA-formatfejl i en metadata-gate blev rettet før arrays eller scorer blev læst; fejlkvitteringen er bevaret.'),
 P('Den bærbare NumPy-kontrol genberegner de nye normaliseringer og profiler fra bevarede råcrops uden HDF5 eller detektorimport. De gamle 54 profiler bevares som eksakte, hashbundne referencer og genberegnes ikke i dette replay. Kode, scopes, relevante kort, råcrops, profiler, CSV og kvitteringer følger resultatpakken.'),
 P(f'Der er {len(contacts)} transporterede kontekstprofiler med kontakt til de faste DC-bins. Disse kontakter er annoteret; de ændrer ikke udvalget eller scorerne. Et fravalgt carrier-maksimum kan stadig skjule en ren ikke-vindende drift-/breddehypotese. De to yderste referencekerner er fortsat uden for kortdomænet. Kanalafstand og forskellige skabeloner beviser ikke forskellige fysiske sendere.'),
 P('<b>Ingen kvalificeret SETI-detektion. 0 DKK; nul nye teleskoprequests.</b> Original A/B er fortsat FAIL_CLOSED. Beskyttede 2016-kontroller og den lukkede 2019-adgangsrute er uændrede. Formelt checkpoint: 20. oktober 2026.')]
def footer(c,d):c.setFont('DVS',7);c.setFillColor(colors.HexColor('#617b8b'));c.drawString(43,27,'SETI | Martin Andersen | 13. oktober 2026');c.drawRightString(553,27,str(d.page))
pdf=O/'SETI_MAALSTJERNE_2026-10-13.pdf';SimpleDocTemplate(str(pdf),title='SETI: nye faste spor fra maalstjernen',author='Martin Andersen / SETI-projektet',pagesize=(595.28,841.89),leftMargin=43,rightMargin=43,topMargin=36,bottomMargin=40).build(story,onFirstPage=footer,onLaterPages=footer)
print(json.dumps({'pdf':str(pdf),'plot':str(plot),'summary':summary}))
