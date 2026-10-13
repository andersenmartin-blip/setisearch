"""Create the admitted two-page Danish full-ON PDF after all actual QA passes.

--check-only creates nothing. --run requires the pinned final-report root GO,
the completed scientific-review artifact, and runs the required artifact marker
exactly once immediately before ReportLab authoring. Rendered pages require
human visual inspection before delivery.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

BASE = 'seti_burst_full'
FINAL_STATUS = 'COMPLETE_AUTHENTICATED_FULL_ON_SCIENTIFIC_REVIEW_NO_QUALIFIED_SETI_DETECTION'
GO_STATUS = 'GO_CREATE_DANISH_FULL_ON_PDF_AFTER_FRESH_ARCHIVE_REPLAY'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_bytes(), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def confined(root, relative):
    name = Path(relative)
    path = root/name
    require(not name.is_absolute() and '..' not in name.parts and not path.is_symlink()
            and path.resolve().is_relative_to(root), 'Confined ordinary report path required')
    return path


def pin(root, path):
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def number(value):
    return f'{int(value):,}'.replace(',', '.')


def create_pdf(path, summary):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
    pdfmetrics.registerFont(TTFont('DV', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DV-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
    pdfmetrics.registerFontFamily('DV', normal='DV', bold='DV-Bold', italic='DV', boldItalic='DV-Bold')
    navy, ink, muted, pale, line = [colors.HexColor(v) for v in ('#17324C', '#152636', '#5D6D7A', '#EFF5F8', '#D7E2EA')]
    styles = {
        'title': ParagraphStyle('title', fontName='DV-Bold', fontSize=19, leading=24, textColor=navy, spaceAfter=5),
        'subtitle': ParagraphStyle('subtitle', fontName='DV', fontSize=9, leading=13, textColor=muted, spaceAfter=13),
        'heading': ParagraphStyle('heading', fontName='DV-Bold', fontSize=11, leading=15, textColor=navy, spaceBefore=12, spaceAfter=6),
        'body': ParagraphStyle('body', fontName='DV', fontSize=8.6, leading=12.3, textColor=ink, spaceAfter=7),
        'small': ParagraphStyle('small', fontName='DV', fontSize=7.6, leading=10.7, textColor=muted, spaceAfter=6),
        'cell': ParagraphStyle('cell', fontName='DV', fontSize=7.6, leading=10.1, textColor=ink),
        'header': ParagraphStyle('header', fontName='DV-Bold', fontSize=7.3, leading=9.8, textColor=colors.white),
        'banner': ParagraphStyle('banner', fontName='DV-Bold', fontSize=12, leading=17, textColor=colors.white),
        'metric': ParagraphStyle('metric', fontName='DV-Bold', fontSize=11.5, leading=16, textColor=navy),
    }
    def para(text, style='body'):
        return Paragraph(text, styles[style])
    def table(rows, widths, header=True):
        converted = [[para(str(value), 'header' if header and row == 0 else 'cell') for value in values] for row, values in enumerate(rows)]
        result = Table(converted, colWidths=[width*mm for width in widths], repeatRows=1 if header else 0, hAlign='LEFT')
        commands = [('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5), ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6), ('LINEBELOW', (0, -1), (-1, -1), .4, line)]
        if header:
            commands.extend([('BACKGROUND', (0, 0), (-1, 0), navy), ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, pale])])
        result.setStyle(TableStyle(commands))
        return result
    story = [para('SETI: fuld ON-søgning', 'title'),
             para('HIP98505 / HD189733 | Observation: 28. april 2017 | Rapport: '+summary['date'], 'subtitle')]
    banner = Table([[para('Ingen kvalificeret SETI-detektion', 'banner')]], colWidths=[182*mm])
    banner.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), navy), ('TOPPADDING', (0, 0), (-1, -1), 10),
                               ('BOTTOMPADDING', (0, 0), (-1, -1), 10), ('LEFTPADDING', (0, 0), (-1, -1), 10)]))
    story += [banner, Spacer(1, 10)]
    metrics = Table([[para(number(2298)+'<br/><font size="8">kort</font>', 'metric'),
                      para(number(9412608)+'<br/><font size="8">kanalreferencer</font>', 'metric'),
                      para(number(20952465408)+'<br/><font size="8">korrelerede hypoteser</font>', 'metric')]], colWidths=[60*mm, 60*mm, 62*mm])
    metrics.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), pale), ('TOPPADDING', (0, 0), (-1, -1), 9),
                                ('BOTTOMPADDING', (0, 0), (-1, -1), 9), ('LEFTPADDING', (0, 0), (-1, -1), 9)]))
    story += [metrics, para('Søgningen og kontrollen', 'heading'),
              para('2.010 nye kort supplerer 288 uændrede pilotkort. Hvert af tre ON-scan dækker 766 core-domæner og 3.137.536 kanalreferencer. Alle 159 driftsværdier, syv overlappende vinduer på fire rækker og bredderne 1 og 3 indgår.'),
              para('Der gemmes både den ubetingede maksimumhypotese og den bedste hypotese, hvis valgte fire rækkebokse undgår de tre faste DC-centerbins. Power og normalisering er uændret. Ni præcise DC-centerkanaler har ingen tilladt hypotese og er markeret EMPTY.'),
              para('De ni globalt valgte DC-frie skabeloner', 'heading')]
    rows = [['ON / nr.', 'Frekvens<br/>MHz', 'Drift<br/>Hz/s', 'Valgte<br/>rækker', 'Bredde', 'Rangerings-<br/>score', 'DC-rækker<br/>4 / 16']]
    for record in summary['tracks']:
        point = record['selected_track']
        epoch = int(point['scan_id'][5])
        start = point['window_start_row']
        rows.append([str(epoch)+' / '+str(point['rank']), f"{point['frequency_hz_at_window_reference']/1e6:.8f}",
                     f"{point['drift_hz_s']:.4f}", str(start)+'-'+str(start+3), str(point['width_channels']),
                     f"{point['score']:.6f}", str(record['own_selected4_DC_contact_rows'])+' / '+str(record['own_full16_DC_contact_rows'])])
    story += [table(rows, [18, 42, 25, 25, 15, 32, 25]),
              Spacer(1, 6), para('Tre valg pr. ON-scan; scanene er rangeret hver for sig. Referencekanaler holdes mere end tre kanaler fra hinanden. Det er beskrivende frekvensafstand, ikke påviste uafhængige fysiske kilder. Rækkenumre er 0-15.', 'small'),
              para('Scoren er et udvælgelses- og rangeringstal. Den giver ikke en kalibreret signal-til-støj-værdi eller sandsynlighed for et ægte signal. Fire rækker er målingens support, ikke en påvist emissionsvarighed.', 'small'),
              PageBreak(), para('Faste kontekster og fortolkning', 'title'),
              para('54 profiler følger de samme ni skabeloner gennem seks ON/OFF-scan uden at optimere nye spor.', 'subtitle')]
    context_rows = [['Profilgruppe', 'Antal', 'DC-kontakt<br/>valgte 4', 'DC-kontakt<br/>alle 16', 'DC-rækker<br/>valgte 4 / alle 16']]
    for key, label in [('origin_ON', 'Oprindeligt ON'), ('other_ON', 'Øvrige ON'), ('OFF', 'OFF')]:
        group = summary['context_role_groups'][key]
        context_rows.append([label, number(group['profiles']), number(group['profiles_with_selected4_DC_contact']),
                             number(group['profiles_with_full16_DC_contact']), number(group['selected4_DC_contact_rows'])+' / '+number(group['full16_DC_contact_rows'])])
    story += [table(context_rows, [48, 18, 36, 36, 44]), Spacer(1, 7),
              para('DC-kontakt tælles som rækker, hvis inklusive breddeboks rammer et fast DC-centerbin. De ni oprindelige valgte fire-rækkers support er DC-frie. Andre ON/OFF-profiler og support over alle 16 rækker kan ramme DC. Markeringen ændrer ingen score og udgør ikke et kvalificeret OFF-veto.'),
              para('Pilot og fuld søgning', 'heading'),
              para(str(summary['previous_pilot_exact_tuple_matches'])+' af de ni fuldbandsvalg matcher præcis en tidligere pilot-TOP3-skabelon, inklusive frekvens, drift, vindue, bredde, score og referencetid. Sammenligningen bruger kun autentificerede og kontrollerede resultater.'),
              para(number(summary['dual_carrier_census']['clean_changed_winner_tuples'])+' kanalvindere ændrer skabelon eller bliver EMPTY efter den per-hypotese DC-betingelse. Den øvrige søgning og det oprindelige rå maksimum bevares.'),
              para('Hvad resultaterne kan sige', 'heading')]
    limits = [
        'Alle tre ON-scan er fra ét allerede eksponeret besøg i 2017. Tidsrum mellem scan og overlappende vinduer giver hverken kontinuerlig overvågning eller uafhængige observationsepoker.',
        'De 20,95 milliarder hypoteseforekomster er korrelerede. Udvælgelse efter maksimumsøgning giver selektionsbias; der er ingen kalibreret falsk-alarm-sandsynlighed.',
        '159 lineære driftsværdier, to bredder og fire-rækkers vinduer er en afgrænset familie. Andre signalformer kan overses. To yderste core-domæner er udeladt for fuld randstøtte.',
        'DC-fri support udelukker kun tre præcise centerbins. Normalisering bruger alle 16 rækker og hele 4.096-kanalers core. Nabokanallækage og anden interferens kan stadig spille ind.',
        'Fast drift ekstrapoleres gennem den faktiske kronologi uden ny tilpasning. Svagt eller manglende kontekstsvar udelukker ikke et andet eller intermitterende spor.'
    ]
    for text in limits:
        story.append(para(text, 'small'))
    story += [para('Kontrolhistorik og leverance', 'heading'),
              para('En syntetisk grænsetest havde en forkert testfixture før den egentlige data-QA. V2 isolerede spiken i række 0 og bestod alle ti testcases. Produktets scoringskode blev ikke ændret; observationsarrays blev ikke brugt til at rette testen.', 'small'),
              para('Alle tre faktiske kontroltrin har bestået: kilde- og dualmaksimum-QA, uafhængig fuldsortering af alle kanalvindere og seks-scan-kontekst-QA med fulde normaliseringskerner samt DC-diagnostik. Beskyttede 2016-data og lukket 2019-transport er uændret; oprindelig A/B-status er FAIL_CLOSED. Ingen nye teleskopforespørgsler eller udgifter.', 'small'),
              para('Arkivet er kontrolleret med SHA256 og CRC. En frisk udpakning bestod 10.050 gemte scalarkontroller og dualmaksimum-replay af 18 DC-frames, inklusive ni EMPTY. Samme uafhængige QA-implementering blev kørt igen; dette er reproduktion, ikke en tredje uafhængig implementering. Hele HDF5-kildefiler er ikke med i arkivet.', 'small'),
              para('Arkiv: '+summary['final_delivery_proof']['archive_filename']+'<br/>SHA256: '+summary['final_delivery_proof']['archive_sha256'], 'small')]
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(line)
        canvas.line(14*mm, 16*mm, 196*mm, 16*mm)
        canvas.setFont('DV', 7)
        canvas.setFillColor(muted)
        canvas.drawString(14*mm, 11*mm, 'SETI | '+summary['date']+' | Kontrolleret, eksponerede data; ingen kvalificeret detektion')
        canvas.drawRightString(196*mm, 11*mm, str(doc.page)+' / 2')
        canvas.restoreState()
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=14*mm, leftMargin=14*mm,
                            topMargin=14*mm, bottomMargin=22*mm, title='SETI: fuld ON-søgning', author='Martin Andersen / SETI Search')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check-only', action='store_true')
    mode.add_argument('--run', action='store_true')
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--go', default=BASE+'/FINAL_REPORT_GO.json')
    parser.add_argument('--go-sha256')
    parser.add_argument('--review-dir', default=BASE+'/report_results')
    parser.add_argument('--out-dir', default=BASE+'/output/pdf')
    args = parser.parse_args()
    code_sha = digest(Path(__file__))
    if args.check_only:
        print(json.dumps({'status': 'TWO_PAGE_DANISH_PDF_CODE_ONLY', 'code_sha256': code_sha,
                          'numerical_payloads_read': 0, 'PDF_created': False, 'artifact_marker_run': False}))
        return
    root = args.root.resolve()
    go_path = confined(root, args.go)
    require(args.go_sha256 and digest(go_path) == args.go_sha256, 'Exact root report phase GO required')
    go = read(go_path)
    require(go['status'] == GO_STATUS and go['pdf_generator_code_sha256'] == code_sha
            and re.fullmatch('[0-9a-f]{40}', go['public_freeze_commit']), 'PDF authoring phase not admitted')
    def bound(key):
        declaration = go[key]
        path = confined(root, declaration['path'])
        require(pin(root, path) == declaration, 'Final PDF dependency changed: '+key)
        return path
    science_go_path = bound('science_GO_pin')
    science_go = read(science_go_path)
    require(science_go['status'] == 'GO_COMPLETE_FULL_ON_FINAL_SCIENCE_REVIEW', 'Earlier scientific GO required')
    review_path, receipt_path = bound('science_review_pin'), bound('science_review_receipt_pin')
    receipt = read(receipt_path)
    require(receipt['status'] == 'PASS_COMPLETED_FINAL_SCIENCE_REVIEW_ARTIFACT' and receipt['phase_GO_sha256'] == go['science_GO_pin']['sha256']
            and receipt['science_review_code_sha256'] == science_go['science_review_code_sha256']
            and receipt['output'] == pin(root, review_path), 'Completed scientific-review artifact binding differs')
    summary = read(review_path)
    require(summary['status'] == FINAL_STATUS and summary['all_three_actual_QA_pass'] is True
            and summary['phase_GO_sha256'] == go['science_GO_pin']['sha256'] and summary['science_review_code_sha256'] == science_go['science_review_code_sha256'],
            'Actual completed scientific review required before PDF creation')
    archive_receipt_path, replay_receipt_path, extraction_path = bound('archive_receipt_pin'), bound('fresh_replay_receipt_pin'), bound('fresh_extraction_receipt_pin')
    archive_receipt, replay_receipt, extraction = read(archive_receipt_path), read(replay_receipt_path), read(extraction_path)
    require(archive_receipt['status'] == 'PASS_NEW2010_ARCHIVE_STREAMED_ALL_PAYLOAD_SHA_AND_CRC'
            and archive_receipt['source_HDF5_files_included'] is False and archive_receipt['extended_delivery'] is True,
            'Complete authenticated full archive required before final PDF')
    archive_path = confined(root, archive_receipt['archive']['path'])
    require(pin(root, archive_path) == archive_receipt['archive'], 'Actual final archive bytes differ')
    require(extraction['status'] == 'PASS_ALL_ARCHIVE_PAYLOAD_SHA_CRC_STRICT_REPLAY_SUBSET_EXTRACTED'
            and extraction['archive_sha256'] == archive_receipt['archive']['sha256'] and extraction['mode'] == 'full_dc'
            and extraction['source_HDF5_files_extracted'] is False, 'Fresh extraction of final archive required')
    require(replay_receipt['status'] == 'PASS10050_SAVED_SCALAR_SCORES_18_DC_FRAME_DUAL_REMAX9_EMPTY'
            and replay_receipt['mode'] == 'full_dc' and replay_receipt['scalar_queries'] == 10050
            and replay_receipt['independent_saved_DC_frames'] == 18 and replay_receipt['DC_clean_EMPTY_carriers'] == 9
            and replay_receipt['source_HDF5_files_read'] is False and replay_receipt['scope_sha256'] == extraction['scope_sha256'] == archive_receipt['scope_sha256'],
            'Actual fresh archived-data full-DC replay must pass')
    summary['final_delivery_proof'] = {'archive_filename': archive_path.name, 'archive_sha256': archive_receipt['archive']['sha256'],
                                     'archive_receipt_pin': go['archive_receipt_pin'], 'fresh_replay_receipt_pin': go['fresh_replay_receipt_pin']}
    for declaration in summary['input_pins_verified']:
        require(pin(root, confined(root, declaration['path'])) == declaration, 'Scientific input changed before PDF authoring')
    output_dir = confined(root, args.out_dir)
    require(not output_dir.exists(), 'Do not overwrite a PDF authoring namespace')
    node = os.environ.get('CODEX_PRIMARY_RUNTIME_NODE')
    marker = Path('/root/.codex/skills/builtins/pdf/container_tools/mark_artifact_operation_started.mjs')
    require(node and marker.is_file(), 'Required PDF artifact marker runtime unavailable')
    # Exactly once, immediately before the first create authoring command.
    subprocess.run([node, str(marker), '--operation-kind', 'create', '--expected-output-count', '1', '--output-format', 'pdf'], check=True)
    output_dir.mkdir(parents=True)
    pdf_path = output_dir/('SETI_FULL_ON_'+summary['date']+'.pdf')
    create_pdf(pdf_path, summary)
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    require(len(reader.pages) == 2, 'Final report must fit exactly two pages')
    text = '\n'.join(page.extract_text() or '' for page in reader.pages)
    require('20.952.465.408' in text and 'Ingen kvalificeret SETI-detektion' in text, 'Report text verification failed')
    preview_dir = confined(root, BASE+'/tmp/pdfs/full_on_report')
    preview_dir.mkdir(parents=True, exist_ok=False)
    renderer = shutil.which('pdftoppm')
    require(renderer is not None, 'PDF rendering tool unavailable')
    subprocess.run([renderer, '-png', '-scale-to', '1600', str(pdf_path), str(preview_dir/'page')], check=True)
    require(digest(Path(__file__)) == code_sha and digest(go_path) == args.go_sha256
            and receipt['output'] == pin(root, review_path), 'Report code/GO/scientific artifact changed during authoring')
    for key in ('science_GO_pin', 'science_review_pin', 'science_review_receipt_pin', 'archive_receipt_pin', 'fresh_replay_receipt_pin', 'fresh_extraction_receipt_pin'):
        bound(key)
    result = {'status': 'TWO_PAGE_DANISH_PDF_CREATED_TEXT_CHECKED_RENDERED_VISUAL_REVIEW_REQUIRED',
              'output': pin(root, pdf_path), 'page_count': 2, 'pdf_generator_code_sha256': code_sha,
              'phase_GO_sha256': args.go_sha256, 'scientific_review_pin': receipt['output'],
              'science_GO_pin': go['science_GO_pin'], 'archive_receipt_pin': go['archive_receipt_pin'],
              'fresh_replay_receipt_pin': go['fresh_replay_receipt_pin'], 'archive_sha256': archive_receipt['archive']['sha256'],
              'artifact_marker_run_exactly_once': True, 'preview_paths': [p.relative_to(root).as_posix() for p in sorted(preview_dir.glob('*.png'))],
              'numerical_search_rerun': False, 'source_HDF5_arrays_opened': False, 'visual_review_completed': False}
    with (output_dir/'PDF_RECEIPT.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
