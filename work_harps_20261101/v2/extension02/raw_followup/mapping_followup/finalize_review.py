"""Combine fixed posthoc reviews; preserve every baseline and mapping output."""
from pathlib import Path
import collections
import csv
import datetime
import hashlib
import json
import zipfile

OUT = Path(__file__).resolve().parent
OLD = OUT.parent
BASE = OLD.parent.parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def require(ok, detail):
    if not ok:
        raise RuntimeError(detail)


def dump(name, value):
    path = OUT / name
    require(not path.exists(), 'Refusing replacement: ' + name)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    plan = read(OUT / 'PLAN.json')
    for relative, expected in plan['input_hashes'].items():
        require(sha(BASE / relative) == expected, 'Baseline changed: ' + relative)
    first = read(OUT / 'FIRST_VISUAL_NOTES.json')['notes']
    second_record = read(OUT / 'SECOND_VISUAL_NOTES.json')
    second = second_record['notes']
    geometry = read(OUT / 'SUMMARY.json')
    verification = read(OUT / 'VERIFICATION.json')
    require(verification['status'] == 'PASS_EXACT_FRESH_PROCESS_RECONSTRUCTION_ALL_FOUR_EXPOSURES', 'Numerical verification incomplete')
    require(sha(OUT / 'SUMMARY.json') == second_record['mapping_summary_sha256'], 'Geometry summary changed after second review')
    require(set(first) == set(second) == set(plan['review_ids']), 'Review membership mismatch')
    require(all(first[k][0] == second[k][0] for k in first), 'Reviewer disagreement requires resolution')
    mapping = read(OUT / 'MAPPING_AUDIT.json')
    mapping_events = {r['review_id']: r for r in mapping['events']}
    baseline = list(csv.DictReader((OLD / 'BASELINE_SELECTED_EVENT_DISPOSITIONS.csv').open()))
    base_by_id = {r['review_id']: r for r in baseline}
    index = {r['review_id']: r for r in read(OUT / 'FIGURE_INDEX.json')}
    selected = list(csv.DictReader((OUT / 'SELECTED_EVENTS.csv').open()))
    status = {'A': 'PROVISIONAL_DETECTOR_ARTIFACT', 'U': 'UNRESOLVED_SPECTRAL_FEATURE', 'M': 'INSUFFICIENT_RAW_MAPPING', 'O': 'PROVISIONAL_ATMOSPHERIC_OI'}
    records = []
    for event in selected:
        key = event['review_id']
        code, reason = first[key]
        info = mapping_events[key]
        require((code == 'M') == (not info['mapping_supported']), 'Geometry limitation not preserved')
        prior = base_by_id[key]
        require(prior['baseline_disposition'] == 'INSUFFICIENT_LOCAL_RAW_MAPPING', 'Prior status not mapping-limited')
        refs = [r for r in mapping['reference_audit'] if r['dp_id'] == event['dp_id'] and r['order'] in info['covering_orders']]
        metrics = [{k: r[k] for k in ['order', 'valid_reference_windows', 'median_correlation', 'median_abs_peak_offset', 'windows_within_one_pixel', 'mapping_supported']} for r in refs]
        same = {'V1E2-0003': 'V2E2-0132', 'V2E2-0132': 'V1E2-0003'}.get(key, '')
        fig = index[key]
        records.append(dict(review_id=key, detector=event['detector'], dp_id=event['dp_id'], target=event['target'], baseline_code=prior['baseline_code'], baseline_status=prior['baseline_disposition'], proposed_code=code, proposed_status=status[code], evidence_first=reason, evidence_second=second[key][1], visual_review_agreement=True, all_covering_orders_reference_supported=info['mapping_supported'], covering_orders=json.dumps(info['covering_orders']), reference_metrics=json.dumps(metrics), coordinates_changed=False, original_native_and_raw_pixels_preserved=True, final_physical_origin_confirmed=False, same_physical_feature_record=same, figure=f'figures/REVIEW_{fig["page"]:02d}.png', figure_row=fig['row'], baseline_figure=prior['figure']))
    path = OUT / 'FOLLOWUP_DISPOSITIONS.csv'
    require(not path.exists(), 'Final followup table already exists')
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    counts = dict(collections.Counter(r['proposed_code'] for r in records))
    require(counts == {'A': 4, 'U': 4, 'M': 1}, 'Unexpected reviewed counts')
    overlay_counts = {}
    for detector in ('V1', 'V2'):
        counter = collections.Counter()
        for prior in baseline:
            if prior['detector'] != detector:
                continue
            code = first[prior['review_id']][0] if prior['review_id'] in first else prior['baseline_code']
            counter['M' if code == 'I' else code] += 1
        overlay_counts[detector] = dict(counter)
    products = read(OLD / 'products/MANIFEST.json')['products']
    dp_ids = {r['dp_id'] for r in records}
    source_products = [{k: r[k] for k in ['dp_id', 'kind', 'raw_id', 'archive_id', 'relative_path', 'bytes', 'sha256']} for r in products if r['dp_id'] in dp_ids]
    require(len(source_products) == 8, 'Incorrect source products')
    dump('SOURCE_PRODUCTS.json', dict(products=source_products, retrieval='Already verified admitted products from the unchanged baseline; no new downloads. Restore from original raw-followup checkpoint if needed.', raw_files_embedded_in_this_zip=False))
    remaining = next(r for r in mapping['reference_audit'] if r['dp_id'] == base_by_id['V2E2-0225']['dp_id'] and r['order'] == 32)
    report = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), status='COMPLETE_SEPARATE_POSTHOC_REVIEW_READY_FOR_ROOT_OVERLAY', records=9, exposures=4, detector_records={'V1': 1, 'V2': 8}, proposed_codes=counts, proposed_status_counts=dict(collections.Counter(r['proposed_status'] for r in records)), detector_proposed_codes={d: dict(collections.Counter(r['proposed_code'] for r in records if r['detector'] == d)) for d in ['V1', 'V2']}, geometry_supported_records=8, mapping_limited_records=['V2E2-0225'], reference_orders=13, reference_windows=65, source_products=8, cutouts=16, independent_numerical_reconstruction=verification['status'], visual_review_agreement_records=9, coordinates_changed=False, original_raw_pixels_and_native_samples_preserved=True, baseline_files_unchanged=True, original_catalogs_unchanged=True, root_overlay_created_by_this_script=False, overlay_counts_if_root_adopts=overlay_counts, other_V2_records_still_unreviewed=277, remaining_limitation=dict(review_id='V2E2-0225', order=32, median_correlation=remaining['median_correlation'], median_abs_peak_offset=remaining['median_abs_peak_offset'], valid_windows=remaining['valid_reference_windows'], explanation='Previously sample-limited order33 passes. Independently checking every covering order reveals order32 fails the fixed correlation threshold. A small spatial offset never overrides that gate.'), comparisons=dict(method='Exact prior mapping43 five-window method without changes', criterion_applied_to='All covering orders, including those previously locally supported; all65 baseline candidates excluded within±80pixels', previous_local_failure_group='All9 were insufficient-local-sample cases, none measured-shift failures', visual_blinding='Separate AI reviewers withheld new codes until fixed, but knew baseline/detector/project context; not blinded scientific or human validation', physical_origin='All interpretations provisional; V1E2-0003 and V2E2-0132 are the same raw feature recorded by two detectors'), acquisition_anomaly='Previously disclosed three stale raw-product prefixes remain unexplained and preserved separately. This followup used only hash-verified admitted final products and makes no new network-accounting claim.', new_network_calls=0, hashes={name: sha(OUT / name) for name in ['PLAN.json', 'SUMMARY.json', 'MAPPING_AUDIT.json', 'VERIFICATION.json', 'FIRST_VISUAL_NOTES.json', 'SECOND_VISUAL_NOTES.json', 'FOLLOWUP_DISPOSITIONS.csv', 'finalize_review.py']})
    dump('FINAL_REVIEW_SUMMARY.json', report)
    readme = '''# Separat opfølgning på ni usikre billedkoblinger

De bredere faste referenceområder giver støtte til **otte af ni hændelsesregistreringer uden at flytte nogen koordinater**. To separate agentgennemgange er enige om fire foreløbige detektorartefakter, fire uafklarede spektralstrukturer og ét fortsat kortlægningsbegrænset tilfælde. Det er ni registreringer; V1E2-0003 og V2E2-0132 beskriver samme råbilledfeature.

[Baseline og foreslået status, række for række](FOLLOWUP_DISPOSITIONS.csv) · [samlet reviewsammenfatning](FINAL_REVIEW_SUMMARY.json) · [oprindelig kortlægningssammenfatning](SUMMARY.json).

## Metode og den tilbageværende begrænsning

Den særskilte efterfølgende plan genbruger nøjagtigt den tidligere mapping43-metode: fem faste intervaller per dækkende orden, alle 65 baselinekandidater udeladt inden for ±80 native pixels, mindst 200 referencepixels per interval og mindst tre brugbare intervaller. Median rå/native-korrelation skal være over0,8; median absolut sporoffset højst0,75pixel; mindst tre offsets skal ligge inden for1pixel. Profilinterpolation, filtrering, orientering og headerkoordinater er uændrede. Planen blev fastlagt før de nye referenceområder blev undersøgt. Alle ni gamle fejl skyldtes utilstrækkelige lokale samples, ikke en målt stor forskydning.

**Alle dækkende ordener undersøges, også dem der tidligere havde lokal støtte.** Derfor forbliver V2E2-0225 begrænset: den gamle utilstrækkelige orden33 består nu, men orden32 har median korrelation0,600868. Dens medianoffset på kun0,0162pixel ophæver ikke korrelationskravet. Synlig kompakt ladningsstruktur beskrives, men bruges ikke til at tilsidesætte den bevarede begrænsning.

De fire artefaktregistreringer er V1E2-0003, V2E2-0132, V2E2-0208 og V2E2-0228. De uafklarede registreringer er V2E2-0001,0128,0130 og0131. Den svage blå struktur i0001 er ikke en bekræftet ghost eller laser. Ingen af vurderingerne bekræfter et fysisk ophav.

## Kontrol og afgrænsning

En separat proces genopbyggede alle16 fem-array-NPZ'er fra de otte oprindelige rå-/TAR-produkter, alle13 ordensreferencer og alle65 referencevinduer præcist. De oprindelige21×25 råpixels,41 native samples, koordinater og orienteringer er identiske. Alle kildehashes og baselinefiler er bevaret. [Numerisk efterkontrol](VERIFICATION.json).

Baseline for65 registreringer og336 V2-events er ikke ændret. Root kan oprette et særskilt aktuelt overlay efter review; det ville give V2:44A,8O,6U,1M i den valgte delmængde samt277 uden råbilledreview; V1:3A,3O. Det er en efterfølgende undersøgelse af en udvalgt problemgruppe, ikke ensartet genbehandling af hele kataloget. Reviewerne kendte detektor- og baselinekonteksten; dette er hverken blind videnskabelig eller menneskelig validering.

De tidligere dokumenterede tre uforklarede .part-præfikser er bevaret separat som ikke-videnskabelig dokumentation. Kun hashverificerede slutprodukter blev anvendt her; årsagen til præfikserne og deres netværksproveniens er fortsat ukendt.

## Reproduktion og indhold

Brug en separat arbejdskopi med de otte produkter i `SOURCE_PRODUCTS.json` og projektets fastlåste Python-miljø. `run_mapping.py` skaber kortlægningsresultatet; `plot_mapping.py` skaber figurerne; `verify_mapping.py` genopbygger værdierne i en frisk proces. De to visuelle notefiler er eksplicitte agentvurderinger. `finalize_review.py` sammenholder dem og skriver forslagstabellen uden at ændre baseline eller den oprindelige kortlægningssammenfatning.

`MAPPING_FOLLOWUP_EVIDENCE.zip` indeholder hele denne opfølgnings kode, planer, noter, referenceværdier,16 NPZ'er og fem PNG-figurer. De store oprindelige rå-/TAR-filer findes i det separate baseline-checkpoint og dubleres ikke i ZIP-filen. `EVIDENCE_ARCHIVE.json` dokumenterer medlemmernes hashes.

'''
    for number in range(1, 4):
        readme += f'![Hændelser side {number}](figures/REVIEW_{number:02d}.png)\n\n'
    for number in range(1, 3):
        readme += f'![Faste referencer side {number}](figures/REFERENCES_{number:02d}.png)\n\n'
    require(not (OUT / 'README.md').exists(), 'README already exists')
    (OUT / 'README.md').write_text(readme)
    for relative, expected in plan['input_hashes'].items():
        require(sha(BASE / relative) == expected, 'Baseline changed while finalizing')
    archive = OUT / 'MAPPING_FOLLOWUP_EVIDENCE.zip'
    files = [p for p in sorted(OUT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.zip', '.pyc') and p.name != 'EVIDENCE_ARCHIVE.json']
    members = [dict(path=str(p.relative_to(BASE)), bytes=p.stat().st_size, sha256=sha(p)) for p in files]
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for path in files:
            output.write(path, path.relative_to(BASE))
    with zipfile.ZipFile(archive) as output:
        require(output.testzip() is None, 'Archive CRC error')
        for member in members:
            require(hashlib.sha256(output.read(member['path'])).hexdigest() == member['sha256'], 'Archive member mismatch')
    dump('EVIDENCE_ARCHIVE.json', dict(filename=archive.name, bytes=archive.stat().st_size, sha256=sha(archive), members=len(members), files=members, source_raw_TAR_files_in_separate_baseline_checkpoint=True))
    print(json.dumps(dict(status=report['status'], review_counts=counts, overlay_counts_if_adopted=overlay_counts, archive_bytes=archive.stat().st_size, archive_sha256=sha(archive), final_summary_sha256=sha(OUT / 'FINAL_REVIEW_SUMMARY.json')), indent=2))


if __name__ == '__main__':
    main()
