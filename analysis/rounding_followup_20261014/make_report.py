"""Compose one four-page Danish PDF after completed numerical QA and PNG review.

The first two pages report exact native-channel family results; the final two
show the six frozen strongest-track waterfalls. This script never opens raw
spectra or imports a producer/QA module. Root runs the PDF marker before use.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import statistics


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fmt(value, decimals=2):
    require(isinstance(value, (int, float)) and math.isfinite(value), 'Nonfinite report value')
    return f'{value:.{decimals}f}'.replace('.', ',')


def label(p):
    return f"E{p['origin_scan_id'][5]}-R{p['origin_rank']}"


def target(p):
    rows = [v for v in p['offset_results'] if v['offset_channels'] == 0]
    require(len(rows) == 1, 'Missing or duplicate target offset')
    return rows[0]


def scores(p):
    t = target(p)
    return (t['legacy_fine_fixed_original4']['score'], t['exact_fixed_original4']['score'],
            t['legacy_fine_max7']['score'], t['exact_max7']['score'])


def ranks(p):
    return (p['control_ranks']['fixed_original4_rank_among_target_plus8'],
            p['control_ranks']['max7_rank_among_target_plus8'])


def order(p):
    return p['origin_scan_id'], p['origin_rank']


def prepare(args):
    scope, results, injections, qa, receipt = [read(p) for p in
        (args.scope, args.profiles, args.injections, args.qa, args.receipt)]
    geometry, diagnosis = read(args.geometry), read(args.diagnosis)
    require(results.get('schema')=='SETI_EXACT_CONTINUOUS_ROUNDING_OBSERVED_PROFILES_V1'
            and injections.get('schema')=='SETI_EXACT_ROUNDING_RESIDUAL_DOMAIN_INJECTION_V1',
            'Unexpected observed or injection report contract')
    require(results.get('scope_sha256') == sha(args.scope), 'Result scope pin differs')
    require(results.get('geometry_sha256')==sha(args.geometry)==scope['geometry_pin']['sha256'],
            'Exact geometry source pin differs')
    require(str(qa.get('status', '')).startswith('PASS'), 'Completed independent numerical QA required')
    require(qa.get('scope_sha256') == results['scope_sha256'], 'QA scope differs')
    require(qa.get('producer_receipt_sha256') == sha(args.receipt), 'QA producer receipt pin differs')
    require(qa['profiles']==54 and qa['normalization_cores']==54 and qa['exact_window_sets']==378
            and qa['exact_unique_paths_zero_offset']==22235 and qa['exact_path_scores_all_offsets']==200115
            and qa['exact_row_terms_all_offsets']==800460 and qa['conditional_injections']==3024,
            'Completed independent numerical QA census differs')
    require(results.get('qualified_SETI_detection') is False, 'Unexpected detection interpretation')
    require(results.get('physical_sensitivity_established') is False
            and results.get('calibrated_SNR_FAP') is False
            and injections.get('raw_sensitivity_or_FAP_established') is False,
            'Unexpected physical sensitivity or FAP interpretation')
    profiles, trials = results['profiles'], injections['trials']
    require(len(profiles) == 54 and len(trials) == 3024, 'Incomplete result census')
    require(set(p['profile_id'] for p in profiles)==set(scope['profile_ids'])
            and receipt['profiles']==54 and receipt['injection_trials']==3024
            and receipt['exact_paths_all_offsets']==200115
            and receipt['row_residual_terms_saved']==800460,
            'Scope/result/receipt numerical census differs')
    require(len({p['profile_id'] for p in profiles}) == 54, 'Duplicate profile identities')
    require(Counter(t['amplitude_per_active_standardized_single_bin'] for t in trials) == {2:1512, 8:1512},
            'Wrong injection amplitude census')
    for p in profiles:
        require(all(math.isfinite(v) for v in scores(p)) and all(1 <= r <= 9 for r in ranks(p)),
                'Invalid displayed score or descriptive rank')
    own = sorted([p for p in profiles if p['context_scan_id'] == p['origin_scan_id']], key=order)
    require(len(own) == 9, 'Expected nine selected original ON profiles')
    scans = ['epoch1_on','epoch1_off','epoch2_on','epoch2_off','epoch3_on','epoch3_off']
    require(Counter(p['context_scan_id'] for p in profiles) == {s:9 for s in scans}, 'Incomplete six-scan matrix')
    require(geometry['counts']['profiles'] == 54 and geometry['counts']['windows'] == 378
            and geometry['counts']['total_unique_paths_zero_offset'] == 22235
            and geometry['counts']['total_offset_path_scores'] == 200115
            and geometry['counts']['legacy_only_float_unique_paths_across_windows']==0,
            'Unexpected frozen exact family census')
    require(diagnosis['reported_missing_geometries'] == 19
            and diagnosis['all19_continuous_truth_points_strictly_feasible'] is True,
            'Unexpected preceding geometric diagnosis')
    return scope, results, injections, qa, receipt, geometry, diagnosis, profiles, trials, own, scans


def heatmap(path, profiles, own, scans):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    lookup = {(p['origin_scan_id'],p['origin_rank'],p['context_scan_id']):p for p in profiles}
    cells = [[lookup[(o['origin_scan_id'],o['origin_rank'],s)] for s in scans] for o in own]
    values = np.array([[scores(p)[3] for p in row] for row in cells])
    fig, ax = plt.subplots(figsize=(7.18,3.80),dpi=220)
    im = ax.imshow(values,cmap='Blues',aspect='auto',vmin=0,vmax=max(8,float(values.max())))
    for ri,row in enumerate(cells):
        for ci,p in enumerate(row):
            old4,new4,old7,new7 = scores(p)
            color = 'white' if values[ri,ci] > im.norm.vmax*.6 else '#153047'
            for dy,text in [(-.24,fmt(old4)+' → '+fmt(new4)),(.02,fmt(old7)+' → '+fmt(new7)),
                            (.29,'r '+str(ranks(p)[0])+' / '+str(ranks(p)[1]))]:
                ax.text(ci,ri+dy,text,ha='center',va='center',fontsize=6.9,color=color)
            if p['origin_scan_id'] == p['context_scan_id']:
                from matplotlib.patches import Rectangle
                ax.add_patch(Rectangle((ci-.49,ri-.49),.98,.98,fill=False,lw=1.5,edgecolor='#d57d18'))
    ax.set_xticks(range(6),['E1 ON','E1 OFF','E2 ON','E2 OFF','E3 ON','E3 OFF'],fontsize=8.2)
    ax.xaxis.tick_top()
    ax.set_yticks(range(9),[label(p) for p in own],fontsize=8)
    ax.set_xticks(np.arange(-.5,6,1),minor=True); ax.set_yticks(np.arange(-.5,9,1),minor=True)
    ax.grid(which='minor',color='white',lw=1); ax.tick_params(which='both',length=0)
    for spine in ax.spines.values(): spine.set_visible(False)
    cb=fig.colorbar(im,ax=ax,pad=.02,fraction=.022);cb.set_label('Eksakt all7-score',fontsize=7)
    cb.ax.tick_params(labelsize=7)
    fig.subplots_adjust(left=.085,right=.95,top=.94,bottom=.04)
    fig.savefig(path,dpi=220,facecolor='white');plt.close(fig)


def figure_paths(args, scans):
    manifest=read(args.waterfalls/'PLOT_MANIFEST.json')
    require(manifest['schema']=='SETI_FROZEN_RESIDUAL_WATERFALLS_V1'
            and manifest['counts']['PNG_files']==14 and manifest['counts']['new_scores_computed']==0
            and manifest['scope']['sha256']==sha(args.scope)
            and manifest['profiles']['sha256']==sha(args.profiles)
            and manifest['numerical_qa']['sha256']==sha(args.qa),
            'Waterfall manifest must match fourteen fixed profiles and completed result QA')
    lookup={p['profile_id']:p for p in manifest['plots']}
    workspace=args.scope.resolve().parent.parent
    paths=[]
    for scan in scans:
        profile_id='epoch3_on_rank1_'+scan
        p=lookup[profile_id]['image']
        path=workspace/p['path']
        require(path.is_file() and path.resolve().is_relative_to(args.waterfalls.resolve())
                and sha(path)==p['sha256'], 'Strongest-track waterfall PNG pin differs')
        paths.append(path)
    return paths


def render(args, prepared):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    from reportlab.platypus import Paragraph, Table, TableStyle
    from PIL import Image

    scope,results,injections,qa,receipt,geometry,diagnosis,profiles,trials,own,scans=prepared
    figures=figure_paths(args,scans)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    scratch=args.output.parent/'tmp_report';scratch.mkdir(exist_ok=True)
    chart=scratch/'exact_scan_scores.png';heatmap(chart,profiles,own,scans)
    fonts=Path('/usr/share/fonts/truetype/dejavu')
    for name,file in [('Body','DejaVuSans.ttf'),('Bold','DejaVuSans-Bold.ttf')]:
        pdfmetrics.registerFont(TTFont(name,str(fonts/file)))
    pdfmetrics.registerFontFamily('Body',normal='Body',bold='Bold')
    blue,dark,muted=map(colors.HexColor,('#16334c','#172738','#506575'))
    pale,line=map(colors.HexColor,('#edf3f7','#d5e0e8'))
    W,H=A4;left=35;width=W-70
    c=canvas.Canvas(str(args.output),pagesize=A4)
    c.setTitle('SETI - eksakte native kanalspor - 14. oktober 2026')
    c.setAuthor('Martin Andersen / SETI Search')
    styles={
        'body':ParagraphStyle('body',fontName='Body',fontSize=9.1,leading=12.7,textColor=dark),
        'small':ParagraphStyle('small',fontName='Body',fontSize=8.0,leading=10.8,textColor=muted),
        'head':ParagraphStyle('head',fontName='Bold',fontSize=11.2,leading=14,textColor=blue),
        'cell':ParagraphStyle('cell',fontName='Body',fontSize=7.65,leading=9.7,textColor=dark),
        'th':ParagraphStyle('th',fontName='Bold',fontSize=7.5,leading=9.5,textColor=colors.white)}

    def para(text,y,kind='body'):
        p=Paragraph(text,styles[kind]);_,h=p.wrap(width,H);p.drawOn(c,left,y-h);return y-h
    def head(text,y):return para(text,y-9,'head')-6
    def table(rows,widths,y,padding=4):
        data=[[Paragraph(str(v),styles['th' if ri==0 else 'cell']) for v in row] for ri,row in enumerate(rows)]
        t=Table(data,colWidths=widths)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),blue),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,pale]),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
            ('TOPPADDING',(0,0),(-1,-1),padding),('BOTTOMPADDING',(0,0),(-1,-1),padding),
            ('LINEBELOW',(0,1),(-1,-1),.25,line)]))
        _,h=t.wrap(width,H);t.drawOn(c,left,y-h);return y-h
    def header(page,title):
        c.setFillColor(blue);c.rect(0,H-17,W,17,fill=1,stroke=0)
        c.setFont('Bold',18);c.drawString(left,H-54,'SETI | Eksakte native kanalspor')
        c.setFillColor(muted);c.setFont('Body',9);c.drawString(left,H-72,'14. oktober 2026 · '+title)
        c.setStrokeColor(line);c.line(left,43,W-left,43)
        c.setFont('Body',7);c.drawString(left,29,'2017-data · 0 DKK · checkpoint 20. oktober 2026')
        c.drawRightString(W-left,29,f'{page} / 4')
        c.setFont('Body',6.4);c.drawString(left,18,'Frosset scope SHA256: '+results['scope_sha256'][:24]+'…')
        c.setFillColor(dark);return H-91

    y=header(1,'Sammenligning med den tidligere familie på 405 drift/fasepunkter')
    y=para('<b>Ingen kvalificeret SETI-detektion er etableret.</b> Den nye metode gennemgår alle '
           'opnåelige mønstre af fire afrundede native kanaler inden for samme lokale drift- og '
           'faseområde. Den fjerner en konstateret geometrisk mangel i den tidligere punktfamilie; '
           'resultaterne er fortsat betingede metodekontroller på ét tidligere eksponeret besøg.',y)-6
    recovery=qa['injection_recovery_by_amplitude']
    y=para('<b>Geometrien er komplet for alle 1.512 indsatte spor.</b> Ved amplitude 8 stiger fuld '
           f"indfangning hos scorevinderen fra {recovery['8']['old_noisy_winner_full_capture']} til "
           f"{recovery['8']['noisy_winner_full_capture']}; ved amplitude 2 falder den fra "
           f"{recovery['2']['old_noisy_winner_full_capture']} til {recovery['2']['noisy_winner_full_capture']}. "
           'Problemet med svage indsatser består, selv om deres fulde native spor nu findes i familien.',y,'small')-6
    y=para('Fast område: δdrift ±0,0253164557 Hz/s og fase ±0,5 kanal. De oprindelige fire rækker '
           'fastholdes i fixed4; all7 vælger mellem syv fire-rækkers vinduer. Anker, virkelige '
           'scan-tider og den oprindelige normaliseringskerne er uændrede.',y,'small')
    y=head('De ni oprindelige ON-udvalg',y)
    rows=[['Udvalg','405<br/>fixed4','Eksakt<br/>fixed4','405<br/>all7','Eksakt<br/>all7','Eksakt all7<br/>start/rang']]
    for p in own:
        a,b,d,e=scores(p)
        rows.append([label(p),fmt(a),fmt(b),fmt(d),fmt(e),f"{target(p)['exact_max7']['window_start_row']} / {ranks(p)[1]}"])
    y=table(rows,[67,81,91,81,91,width-411],y)
    y=para('De gemte drift- og faserepræsentanter er deterministisk valgte aliaser, ikke fysiske '
           'driftsestimater. Identiske native kanalspor kan have mange repræsentanter. En repræsentant '
           'på en rand afgør ikke dimensionen af hele sporets mulige område. '
           'Rækkeindeks starter ved 0; rang er blandt sporet og otte lokale kontroller.',y-6,'small')
    y=head('De øvrige scans, sammenfattet uden detektionsfortolkning',y)
    rows=[['Gruppe','n','Median fixed4<br/>405 / eksakt','Median all7<br/>405 / eksakt','Eksakt all7<br/>min / max','Rang 1<br/>4 / 7']]
    groups=[('Oprindeligt ON',lambda p:p['origin_scan_id']==p['context_scan_id']),
            ('Andre ON',lambda p:p['context_scan_id'].endswith('_on') and p['origin_scan_id']!=p['context_scan_id']),
            ('OFF',lambda p:p['context_scan_id'].endswith('_off'))]
    for title,pred in groups:
        group=[p for p in profiles if pred(p)];ss=[scores(p) for p in group]
        rows.append([title,len(group),fmt(statistics.median(v[0] for v in ss))+' / '+fmt(statistics.median(v[1] for v in ss)),
            fmt(statistics.median(v[2] for v in ss))+' / '+fmt(statistics.median(v[3] for v in ss)),
            fmt(min(v[3] for v in ss))+' / '+fmt(max(v[3] for v in ss)),
            f'{sum(ranks(p)[0]==1 for p in group)} / {sum(ranks(p)[1]==1 for p in group)}'])
    y=table(rows,[101,28,113,110,106,width-458],y)
    y=para('Kontrollerne ligger ±256, ±512, ±768 og ±1.024 kanaler fra sporet. De lokale spor, '
           'vinduer og forskydninger er korrelerede. Rang 1 betyder ingen strengt højere kontrolscore; '
           'ligheder står i resultat-JSON. <b>Rang er ikke falsk-alarm-sandsynlighed.</b> OFF-genmaksimering '
           'giver ingen kvalificeret OFF-veto eller uafhængig replikation.',y-7,'small')
    y=head('Uafhængig kontrol',y)
    y=para('<b>Numerisk QA: PASS.</b> Komplethed af native spor og deres residualscorer er kontrolleret '
           'særskilt. PASS beskriver den erklærede aritmetik og familie; det er ikke dokumentation for '
           'fysisk følsomhed. Original A/B er FAIL_CLOSED; 2016 er beskyttet og 2019 lukket.',y,'small')
    y=para('Alle ni oprindelige ON-udvalgs fixed4- og all7-vindere har et muligt område med positivt '
           'areal. E3-R1 i E2 OFF har derimod en all7-vinder, der kun er mulig i ét randpunkt under '
           'den erklærede nearest-even-afrunding; den er vist på figurarkene. Dette er ingen fysisk '
           'driftmåling. På tværs af 972 mål- og kontrolvindere: 922 arealer, 31 linjer og 19 punkter.',y-6,'small')
    require(y>51,f'Page 1 overflow: {y}');c.showPage()

    y=header(2,'Alle 54 profiler og 3.024 betingede indsprøjtninger')
    y=para('<b>Hver celle:</b> øverst fixed4, i midten all7, begge som 405 → eksakt. Nederst eksakt rang '
           'fixed4 / all7. Farven viser eksakt all7; orange kant viser oprindeligt ON-scan. '
           'Scorer er standardiserede residualsummer, ikke kalibreret SNR.',y,'small')-5
    chart_h=width*3.80/7.18;c.drawImage(str(chart),left,y-chart_h,width=width,height=chart_h,mask='auto');y-=chart_h+1
    y=head('Hvorfor den tidligere punktfamilie missede 19 geometrier',y)
    y=para('Alle 19 indsprøjtede sandhedsspor ligger i mulige afrundingsceller, men ingen af de '
           '405 gamle punkter ramte deres celle. Mindste afstand til en afrundingsgrænse var '
           f"{fmt(diagnosis['minimum_truth_rounding_boundary_margin_channels'],8)} kanal; største "
           f"fejl til nærmeste gridpunkt var {fmt(diagnosis['maximum_nearest_cartesian_continuum_error_channels'],5)} kanal. "
           'En lille kontinuerlig fejl kan derfor ændre en diskret native bin.',y,'small')
    y=head('Indsat signal: samme baggrunde og enkelt-bin-model',y)
    rows=[['Amplitude','n','405-vinder<br/>4/4','Eksakt vinder<br/>4/4','Eksakt rigtigt<br/>vindue','Median løft<br/>405 / eksakt']]
    for amp in (2,8):
        group=[t for t in trials if t['amplitude_per_active_standardized_single_bin']==amp]
        old_full=sum(t['legacy_fine_winner_matching_active4_count']==4 for t in group)
        new_full=sum(t['exact_winner_matching_active4_count']==4 for t in group)
        rows.append([amp,len(group),f'{old_full}/{len(group)}',f'{new_full}/{len(group)}',
            f"{sum(t['exact_winner_matches_true_activity_window'] for t in group)}/{len(group)}",
            fmt(statistics.median(t['legacy_fine_max7_uplift'] for t in group))+' / '+
            fmt(statistics.median(t['exact_max7_uplift'] for t in group))])
    y=table(rows,[63,40,100,108,113,width-424],y)
    once=[t for t in trials if t['amplitude_per_active_standardized_single_bin']==2]
    exact_geom=sum(t['signal_only_exact_best_matched_row_fraction']==1 for t in once)
    legacy_geom=sum(t['legacy_signal_only_fine_best_matched_row_fraction']==1 for t in once)
    old_missing=[t for t in once if t['legacy_signal_only_fine_best_matched_row_fraction']<1]
    repaired=sum(t['signal_only_exact_best_matched_row_fraction']==1 for t in old_missing)
    y=para(f'Signal alene: 405-familien rammer 4/4 i <b>{legacy_geom}/{len(once)}</b>; eksakt i '
           f'<b>{exact_geom}/{len(once)}</b>. Af de 19 tidligere partielle geometrier har '
           f'<b>{repaired}/{len(old_missing)}</b> nu fuld geometrisk indfangning. Amplituderne gentager '
           'samme 1.512 geometrier; scorevinderen kan stadig påvirkes af baggrunden.',y-6,'small')
    lost=[t for t in once if t['legacy_fine_winner_matching_active4_count']==4
          and t['exact_winner_matching_active4_count']<4]
    gained=[t for t in once if t['legacy_fine_winner_matching_active4_count']<4
            and t['exact_winner_matching_active4_count']==4]
    loss_gains=[t['exact_score']-t['legacy_fine_score'] for t in lost]
    y=para(f'<b>Amplitude 2: {len(lost)} gamle fulde vindere bliver partielle, {len(gained)} '
           f'partielle bliver fulde; netto {len(gained)-len(lost)}.</b> De nye vindere i tabene har '
           f"højere score, mindst +{fmt(min(loss_gains),5)}, median +{fmt(statistics.median(loss_gains),5)}. "
           'Flere delvist matchende støjmønstre kan dermed slå det bevarede fulde spor. Tabet skyldes '
           'maksimeringen, ikke manglende data, tie-policy eller afrundingsfejl.',y-6,'small')
    y=para('54 profiler × 7 vinduer × 4 off-grid drift/fasepar × 2 amplituder; indsat amplitude '
           '2 eller 8 i én afrundet native bin pr. aktiv række ved offset +512. Rådata og '
           'normalisering er urørte. <b>Ingen fysisk følsomhed, detektionsrate eller justeret '
           'tærskel udledes af disse betingede indsprøjtninger.</b>',y-6,'small')
    y=para('Familie: 378 profilvinduer, 22.235 særskilte native spor talt inden for hvert vindue, '
           '200.115 scorer inklusive ni forskydninger. Alle gamle native spor var mulige i den '
           'eksakte model; geometrisk scorelighed gør dem ikke til uafhængige forsøg.',y-6,'small')
    require(y>51,f'Page 2 overflow: {y}');c.showPage()

    for page,chunk in [(3,figures[:3]),(4,figures[3:])]:
        y=header(page,'Frosset stærkeste oprindelige udvalg E3-R1, tre scans pr. side')
        y=para('Waterfalls viser 16 integrationsrækker og 49 native kanaler omkring den gamle '
               'afrundede bane. <b>Nulkanalen varierer fra række til række.</b> Farver bruger samme '
               'faste residualskala [-5, 5]. Overlagte fire rækker er det gamle faste udvalg og '
               'den nye eksakte all7-vinder; denne visning følger en tidligere ON-udvælgelse.',y,'small')-8
        for image in chunk:
            iw,ih=Image.open(image).size
            height=min(width*ih/iw,197)
            image_width=height*iw/ih
            c.drawImage(str(image),left+(width-image_width)/2,y-height,
                        width=image_width,height=height,mask='auto');y-=height+6
        require(y>51,f'Figure page overflow: {y}');c.showPage()
    c.save()
    print(json.dumps({'status':'REPORT_CREATED_REQUIRES_VISUAL_QA','pdf':str(args.output),'pages':4,
                      'profiles':54,'injections':3024,'raw_arrays_opened':False}))


def main():
    here=Path(__file__).resolve().parent
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scope',type=Path,default=here/'SCOPE.json')
    p.add_argument('--profiles',type=Path,default=here/'results/PROFILES.json')
    p.add_argument('--injections',type=Path,default=here/'results/INJECTIONS.json')
    p.add_argument('--qa',type=Path,default=here/'qa_results/QA_RECEIPT.json')
    p.add_argument('--receipt',type=Path,default=here/'results/EXECUTION_RECEIPT.json')
    p.add_argument('--geometry',type=Path,default=here/'exact_geometry_results/GEOMETRY.json')
    p.add_argument('--diagnosis',type=Path,default=here/'geometry_results/DIAGNOSIS19.json')
    p.add_argument('--waterfalls',type=Path,default=here/'waterfalls')
    p.add_argument('--output',type=Path,default=here/'output/pdf/SETI_native_spor_2026-10-14.pdf')
    p.add_argument('--check-inputs',action='store_true')
    args=p.parse_args();prepared=prepare(args)
    if args.check_inputs:
        print(json.dumps({'status':'PASS_REPORT_INPUT_CENSUS','profiles':54,'injections':3024,'file_authored':False}));return
    render(args,prepared)


if __name__=='__main__':main()
