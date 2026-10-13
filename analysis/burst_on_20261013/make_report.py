"""Render reviewed numerical outputs into a compact Danish result report."""
from pathlib import Path
import json, csv, hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT/'seti_burst_on'
OUT = BASE/'delivery'

def read(p): return json.loads(p.read_text())
def pin(p): return {'path':str(p.relative_to(ROOT)), 'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def main():
    context = read(BASE/'context_results/CONTEXT_PROFILES.json')
    qa = read(BASE/'qa_results/QA_RECEIPT.json')
    cqa = read(BASE/'context_qa_results/QA_RECEIPT.json')
    dcqa = read(BASE/'report_dependencies/DC_SOURCE_QA_RECEIPT.json')
    for item in (qa,cqa,dcqa):
        assert item['status'].startswith('PASS'), item['status']
    OUT.mkdir(exist_ok=True)
    tracks,profiles=context['selected_tracks'],context['profiles']
    scans=('epoch1_on','epoch1_off','epoch2_on','epoch2_off','epoch3_on','epoch3_off')
    matrix=np.array([[next(p['fixed_four_row_score'] for p in profiles if p['selected_track']['scan_id']==t['scan_id'] and p['selected_track']['rank']==t['rank'] and p['context_scan_id']==s) for s in scans] for t in tracks])
    own=[p['fixed_four_row_score'] for p in profiles if p['selected_track']['scan_id']==p['context_scan_id']]
    on=[p['fixed_four_row_score'] for p in profiles if p['original_acquisition_role']=='ON' and p['selected_track']['scan_id']!=p['context_scan_id']]
    off=[p['fixed_four_row_score'] for p in profiles if p['original_acquisition_role']=='OFF']
    ranges={k:{'count':len(v),'min':min(v),'max':max(v)} for k,v in [('own',own),('other_ON',on),('OFF',off)]}
    summary={'date':'2026-10-13','target':'HIP98505 / HD189733','visit':'2017-04-28','maps':288,'carrier_winners':1179648,'correlated_hypothesis_occurrences':2625896448,'window_duration_s':73.014444032,'reference_bandwidth_MHz_per_scan':1.0986328125,'reference_core_fraction':0.125,'selected_tracks':tracks,'context_counts':context['counts'],'ranges':ranges,'DC_alternative_counts':{'excluded_original_carriers':7083,'recovered_nonempty':7074,'EMPTY':9,'hypothesis_occurrences':11120310,'revised_TOP9_unchanged':True},'qualified_SETI_detection':False,'calibrated_SNR_FAP':False,'new_observation':False,'cost_DKK':0,'formal_checkpoint':'2026-10-20','QA_receipt_pins':[pin(p) for p in (BASE/'qa_results/QA_RECEIPT.json',BASE/'context_qa_results/QA_RECEIPT.json',BASE/'report_dependencies/DC_SOURCE_QA_RECEIPT.json')]}
    (OUT/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    columns=['scan_id','rank','frequency_hz_at_window_reference','drift_hz_s','width_channels','window_start_row','score']
    with (OUT/'TOP9.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows({k:t[k] for k in columns} for t in tracks)
    with (OUT/'CONTEXT54.csv').open('w') as f:
        cols=['origin_scan','rank','context_scan','context_target','role','fixed_four_row_score','fixed_full16_score']
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
        for p in profiles:w.writerow(dict(zip(cols,[p['selected_track']['scan_id'],p['selected_track']['rank'],p['context_scan_id'],p['context_target'],p['original_acquisition_role'],p['fixed_four_row_score'],p['fixed_full16_score']])))
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    fig,ax=plt.subplots(figsize=(9.2,4.65),layout='constrained')
    im=ax.imshow(matrix,cmap='RdBu_r',vmin=-max(3,float(matrix.max())),vmax=max(3,float(matrix.max())),aspect='auto')
    ax.set_xticks(range(6),['ON1','OFF1','ON2','OFF2','ON3','OFF3'])
    ax.set_yticks(range(9),[f"ON{t['scan_id'][5]} #{t['rank']}" for t in tracks])
    for y,t in enumerate(tracks):
        for x,s in enumerate(scans):
            color='white' if abs(matrix[y,x])>matrix.max()*.5 else '#142536'
            ax.text(x,y,f'{matrix[y,x]:.2f}',ha='center',va='center',color=color,fontsize=10,fontweight='bold' if s==t['scan_id'] else 'normal')
    ax.set_title('Ni udvalgte ON-spor: faste 4-række-scorer i alle seks scanninger',pad=12,fontweight='bold')
    fig.colorbar(im,ax=ax,label='Empirisk score - ikke sigma',shrink=.92)
    fig.savefig(OUT/'SETI_ON_BURST_KONTEKST_2026-10-13.png',dpi=180);plt.close(fig)
    owntext=f"De ni egne udvalgte scorer ligger fra {min(own):.3f} til {max(own):.3f}. Samme frosne baner i andre ON-scanninger ligger fra {min(on):.3f} til {max(on):.3f}, og i OFF fra {min(off):.3f} til {max(off):.3f}. Ingen fast-banegenfinding er etableret i de andre ON-scanninger."
    md=f"# SETI: 73-sekunders søgning i målstjernens ON-scanninger\n\n13. oktober 2026. HIP98505 / HD189733; samme historiske besøg 28. april 2017.\n\n288 nye kombinerede kort, 1.179.648 carrier-vindere og 54 faste kontekstprofiler er færdige. Syv fire-række-vinduer per kerne, 159 drifter og bredder 1/3 giver 2.625.896.448 korrelerede skabelonforekomster, ikke uafhængige statistiske forsøg.\n\n{owntext}\n\nHver ON-scanning blev rangeret separat. De tre ON-scanninger peger mod samme stjerne i ét besøg. Egne scorer var allerede optimeret over frekvens, drift, bredde og vindue. Ingen kalibreret SNR, falskalarmrate eller kvalificeret SETI-detektion er etableret.\n\nReferencekernerne q=4+8k i tre native-bånd dækker 1,0986328125 MHz per scanning, 12,5 procent af tripletens referencekanaler. De er på forhånd geometrisk langt fra de tre DC-bins; DC-kontrollen ændrer derfor ingen rangliste. Nyheden er den korte tidsfamilie i ON-scanningerne, ikke DC-fravalget, ny frekvensdækning eller observation.\n\n## Alternative hypoteser ved DC\n\nDen allerede klargjorte fase er også afsluttet: alle 7.083 tidligere DC-ramte carrier-vindere blev undersøgt over deres oprindelige 785 drifter, bredder 1/3 og 16 rækker. 7.074 fik en tilladt alternativ hypotese; ni havde ingen. Alle 11.120.310 lokale hypoteser er beregnet og uafhængigt kontrolleret. Den samlede TOP9 er uændret. Ingen nye kontekstprofiler er nødvendige for disse uændrede geometrier.\n\n## Kontrol og fortolkning\n\nPrimær-QA undersøger alle 288 kort og 1.170 raw503-scoreforespørgsler, og genberegner fulde median501-normaliseringer i de valgte kerner. Kontekst-QA genberegner normaliseringer og alle 54 profiler fra gemte raw12096-crops; den fulde kilde-QA åbner også de originale HDF5-kompakter. Den efterprøver profilerne; den gentager ikke hele søgegitterets maksimum. DC-QA genmaksimerer alle lokale alternative hypoteser uafhængigt. De eksakte kvitteringer er knyttet i SUMMARY.json.\n\nFaste svage andre-scanning-scorer beviser ikke fravær eller stjerneeksklusivitet: det grove driftgrid kan forskyde en faktisk mellem-grid-bane mange kanaler efter lange pauser. Samme fire-række-position benyttes i hver kontekst; et udbrud kan forekomme på et andet tidspunkt. Full16-profiler og bidrag er bevaret. Scorer er efter udvælgelse og observationerne er allerede eksponeret.\n\n0 DKK; nul nye teleskoprequests. Original A/B: FAIL_CLOSED. Beskyttede 2016-kontroller er lukkede; den lukkede 2019-rute er uændret. Formelt checkpoint: 20. oktober 2026.\n"
    (OUT/'RESULTS.md').write_text(md)
    fontdir=Path('/usr/share/fonts/truetype/dejavu')
    pdfmetrics.registerFont(TTFont('DejaVu',str(fontdir/'DejaVuSans.ttf')))
    pdfmetrics.registerFont(TTFont('DejaVuB',str(fontdir/'DejaVuSans-Bold.ttf')))
    W,H=A4;c=canvas.Canvas(str(OUT/'SETI_ON_BURST_2026-10-13.pdf'),pagesize=A4)
    c.setTitle('SETI: 73-sekunders søgning - 13. oktober 2026');c.setAuthor('Martin Andersen / SETI analysis')
    style=ParagraphStyle('body',fontName='DejaVu',fontSize=9.4,leading=14,textColor=HexColor('#253649'))
    def para(text,y,size=None):
        st=style if size is None else ParagraphStyle('small',parent=style,fontSize=size,leading=size*1.5)
        p=Paragraph(text,st);_,height=p.wrap(W-90,H);p.drawOn(c,45,y-height);return y-height-12
    def title(text,subtitle):
        c.setFillColor(HexColor('#102B46'));c.setFont('DejaVuB',23);c.drawString(45,H-58,text)
        c.setFont('DejaVu',10);c.setFillColor(HexColor('#617386'));c.drawString(45,H-79,subtitle)
    def footer(n):
        c.setFont('DejaVu',8);c.setFillColor(HexColor('#617386'));c.drawString(45,28,'SETI | Martin Andersen | 13. oktober 2026');c.drawRightString(W-45,28,str(n))
    title('SETI: korte spor i ON-data','HIP98505 / HD189733 | 73-sekunders vinduer | Historiske data fra 28. april 2017')
    y=H-107
    y=para('<b>288 nye søgekort og 54 faste profiler er færdige.</b> Udbrudssøgningen er nu anvendt på målstjernens tre ON-scanninger. Den tidligere korte søgning dækkede kontrolstjernerne.',y)
    y=para(owntext+' Det er beskrivende målinger efter udvælgelse; scorerne er hverken sigma eller en kalibreret falskalarmrate.',y)
    height=245;c.drawImage(ImageReader(str(OUT/'SETI_ON_BURST_KONTEKST_2026-10-13.png')),45,y-height,width=W-90,height=height,preserveAspectRatio=True,anchor='c');y-=height+16
    y=para('<b>Ét besøg, én målstjerne.</b> ON1, ON2 og ON3 peger mod den samme stjerne; OFF peger mod tre andre. Fed skrift markerer den scanning, der allerede valgte hvert spor. Farverne viser faste scorer og giver ikke selvstændig signalevidens.',y)
    y=para('96 fastlagte referencekerner pr. scanning dækker 1,0986 MHz, cirka 12,5 procent af de tre bevarede bånd. Syv vinduer med fire integrationer, 159 drifter og bredderne 1 og 3 giver 2,626 milliarder <i>korrelerede</i> skabelonforekomster. Der er ingen ny observation eller frekvensdækning.',y)
    y=para('<b>Ingen kvalificeret SETI-detektion.</b> De fastlåste profiler er bevaret til efterprøvning og videre diagnostik.',y)
    footer(1);c.showPage()
    title('Ni fastlåste udbrudsspor','Frekvensen henviser til hvert udvalgt vindues første integrationsmidtpunkt')
    y=H-115
    heads=['ON/rang','MHz','Hz/s','Bredde','Start-række','Score'];xs=[45,105,235,315,365,465]
    c.setFont('DejaVuB',9);c.setFillColor(HexColor('#102B46'))
    for x,h in zip(xs,heads):c.drawString(x,y,h)
    y-=24
    for idx,t in enumerate(tracks):
        if idx%2==0:c.setFillColor(HexColor('#F0F4F8'));c.rect(40,y-6,W-80,23,fill=1,stroke=0)
        c.setFillColor(HexColor('#253649'));c.setFont('DejaVu',8.8)
        vals=[f"{t['scan_id'][5]} / {t['rank']}",f"{t['frequency_hz_at_window_reference']/1e6:.9f}",f"{t['drift_hz_s']:+.6f}",str(t['width_channels']),str(t['window_start_row']),f"{t['score']:.5f}"]
        for x,v in zip(xs,vals):c.drawString(x,y,v)
        y-=25
    y-=14
    y=para('<b>DC-alternativer: topvalgene er uændrede.</b> 7.074 tilladte alternativer blev genfundet blandt 7.083 tidligere fravalgte carriers. Ni havde ingen. Alle 11.120.310 lokale oprindelige hypoteser blev genberegnet og uafhængigt kontrolleret. Ingen overtog en TOP3-plads.',y)
    y=para('<b>Kontrol.</b> Alle 288 kort og 1.170 råscore-audits er kontrolleret. Fuld median501-normalisering er genberegnet i de valgte primærkerner. Alle 54 kontekstprofiler og deres normaliseringscrops er genberegnet separat. Kvitteringer, kode, råcrops, kort og tabeller følger resultatpakken.',y)
    y=para('<b>Afgrænsning.</b> Svage faste kontrolscorer beviser ikke fravær: det grovere burst-driftgrid og lange pauser kan flytte et faktisk spor fra den målte bane. De samme fire rækkepositioner bruges i hver kontekst, selv om et udbrud kan ligge på andre tidspunkter. Data og egen udvælgelse er allerede eksponeret.',y)
    y=para('0 DKK; nul nye teleskoprequests. Original A/B er fortsat FAIL_CLOSED. Beskyttede 2016-kontroller og den lukkede 2019-rute er uændrede. Formelt checkpoint: <b>20. oktober 2026.</b>',y)
    assert y>45, y
    footer(2);c.save()
    print(json.dumps({'status':'REPORT_RENDERED_FROM_REVIEWED_OUTPUTS','ranges':ranges,'files':[str(p) for p in OUT.iterdir()]}))

if __name__=='__main__':main()
