#!/usr/bin/env python3
"""Once-only byte-preserving final package; never rerun a numerical analysis.

Run only after the owner has finished all cohort reports and final audits.
Original work trees and source files are read-only inputs. All SHA/CRC checks
operate on opaque bytes; NumPy, SciPy, MessagePack and detector code are never
imported by this builder or its generated standalone package verifier.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import zipfile


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[2]
WORKSPACE = SOURCE.parent
PACKAGE_NAME = 'SETI_ALLE_NI_BAAND_2026-10-16'
COHORT_ID = 'SETI_REAL_FULLSCAN_COHORT_DESCRIPTIVE_20261016_V1'
CASE_PREFIX = 'SETI_REAL_FULLSCAN_DESCRIPTIVE_20261016_B'
CASE_PASS = 'COMPLETE_DESCRIPTIVE_REAL_FULLSCAN_QA_VERIFIED'
QA_PASS = 'PASS_DESCRIPTIVE_REAL_FULLSCAN_QA_ONLY'
COHORT_PASS = 'COMPLETE_EIGHT_BAND_DESCRIPTIVE_COHORT_QA_VERIFIED'
COHORT_INCOMPLETE = 'INCOMPLETE_COHORT_RETAINED_NO_RETRY'
CASE_FAILED = 'STOPPED_RETAINED_NO_RETRY'
RESTORE_ID = 'SETI_B06_SAVED_PAYLOAD_RESTORATION_QA_20261016_V1'
RESTORE_PASS = 'COMPLETE_EXACT_RESTORATION_AND_SEPARATE_SAVED_QA'
SOURCE_ZIP_SHA = '52b948958c89069a7afb563cf377ee33e4f1324e014428d597b4b3e3a20f6eb3'
SOURCE_ZIP_LIBRARY_ID = 'libfile_aed79b40b6e48191b3a2ec2e288ab4a5'
ENGINEERING_LIBRARY_ID = 'libfile_3f6c0fed67008191aa48e0bc56368666'
MANIFEST_NAME = 'PACKAGE_MANIFEST.json'
MAX_ARCHIVE_BYTES = 256 * 1024**2


VERIFY_SOURCE = r'''#!/usr/bin/env python3
"""Verify package byte inventory, all SHA-256 hashes and outer ZIP CRCs.

Only the Python standard library is used. This verifies delivered bytes, not a
fresh numerical search, scientific detection, source law or false-alarm rate.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile

MANIFEST = 'PACKAGE_MANIFEST.json'

def require(ok, message):
    if not ok:
        raise ValueError(message)

def pairs(items):
    result = {}
    for key, value in items:
        require(type(key) is str and key not in result, 'Duplicate/nonstring JSON key')
        result[key] = value
    return result

def decode(data):
    return json.loads(data, object_pairs_hook=pairs)

def digest(stream):
    value = hashlib.sha256()
    size = 0
    while True:
        block = stream.read(1 << 20)
        if not block:
            return size, value.hexdigest()
        size += len(block)
        value.update(block)

def safe(name):
    path = PurePosixPath(name)
    require(type(name) is str and bool(name) and '\\' not in name and not path.is_absolute()
            and '..' not in path.parts and '.' not in path.parts,
            'Unsafe package member name')
    return name

def validate_manifest(value):
    require(value['schema'] == 'SETI_NINE_BANDS_BYTE_PACKAGE_V1', 'Unknown package schema')
    members = value['members']
    require(type(members) is dict and MANIFEST not in members, 'Manifest must exclude its own digest')
    for name, pin in members.items():
        safe(name)
        require(set(pin) == {'bytes', 'sha256'} and type(pin['bytes']) is int and pin['bytes'] >= 0
                and type(pin['sha256']) is str and len(pin['sha256']) == 64,
                'Invalid byte inventory declaration')
    return members

def verify_zip(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), 'Duplicate ZIP member')
        candidates = [n for n in names if n.endswith('/' + MANIFEST) or n == MANIFEST]
        require(len(candidates) == 1, 'Exactly one package manifest required')
        manifest_name = candidates[0]
        prefix = manifest_name[:-len(MANIFEST)]
        require(archive.getinfo(manifest_name).file_size <= 16 * 1024**2, 'Manifest too large')
        value = decode(archive.read(manifest_name))
        members = validate_manifest(value)
        require(set(names) == {prefix + n for n in members} | {manifest_name}, 'ZIP inventory differs')
        for info in archive.infolist():
            safe(info.filename)
            require(not info.is_dir() and not (info.flag_bits & 1) and
                    not stat.S_ISLNK(info.external_attr >> 16), 'Nonregular/encrypted package member')
        require(archive.testzip() is None, 'ZIP CRC validation failed')
        for name, pin in members.items():
            info = archive.getinfo(prefix + name)
            require(info.file_size == pin['bytes'], 'ZIP member byte length differs: ' + name)
            with archive.open(info) as stream:
                size, actual = digest(stream)
            require(size == pin['bytes'] and actual == pin['sha256'], 'SHA-256 differs: ' + name)
    return value, len(members)

def verify_folder(folder):
    folder = Path(folder)
    value = decode((folder / MANIFEST).read_bytes())
    members = validate_manifest(value)
    actual = set()
    for path in folder.rglob('*'):
        require(not path.is_symlink(), 'Symlink in extracted package')
        if path.is_file():
            actual.add(path.relative_to(folder).as_posix())
        else:
            require(path.is_dir(), 'Special file in extracted package')
    require(actual == set(members) | {MANIFEST}, 'Extracted package inventory differs')
    for name, pin in members.items():
        with (folder / name).open('rb') as stream:
            size, actual = digest(stream)
        require(size == pin['bytes'] and actual == pin['sha256'], 'SHA-256 differs: ' + name)
    return value, len(members)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', type=Path, help='Verify the complete downloaded ZIP without extracting')
    parser.add_argument('--folder', type=Path, default=Path(__file__).resolve().parent,
                        help='Verify an extracted package (default: this script\'s directory)')
    args = parser.parse_args()
    value, count = verify_zip(args.zip) if args.zip else verify_folder(args.folder)
    print(json.dumps({'status': 'PASS_ALL_PACKAGE_BYTES', 'sha256_members_verified': count,
        'outer_ZIP_CRC_checked': bool(args.zip), 'numerical_searches_or_array_decodes': 0,
        'dependency_note': 'Original telescope ZIP is separate; see external_dependencies in manifest'}))

if __name__ == '__main__':
    main()
'''


def require(ok, message):
    if not ok:
        raise ValueError(message)


def pairs(items):
    result = {}
    for key, value in items:
        require(type(key) is str and key not in result, 'Duplicate or nonstring JSON key')
        result[key] = value
    return result


def read(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 16 * 1024**2,
            'Bounded regular metadata required: ' + str(path))
    return json.loads(path.read_text(), object_pairs_hook=pairs)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(1 << 20):
            value.update(block)
    return value.hexdigest()


def pin(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Regular original file required: ' + str(path))
    return {'bytes': path.stat().st_size, 'sha256': sha(path)}


def check_pin(declaration):
    path = Path(declaration['path'])
    actual = pin(path)
    require(actual == {k: declaration[k] for k in ('bytes', 'sha256')},
            'Original frozen dependency changed: ' + str(path))
    return path


def _regular_tree(root):
    root = Path(root)
    require(root.is_dir() and not root.is_symlink(), 'Original directory required: ' + str(root))
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(), 'Symlink in original tree: ' + str(path))
        if path.is_file():
            if '__pycache__' not in path.parts and path.suffix != '.pyc':
                yield path
        else:
            require(path.is_dir(), 'Special file in original tree: ' + str(path))


def _check_case(root, identity):
    root = Path(root)
    scope = read(root / 'FROZEN_SCOPE.json')
    result = read(root / 'RESULT.json')
    producer_path, qa_path = root / 'observation/PRODUCER.json', root / 'QA_REPORT.json'
    producer = read(producer_path) if producer_path.exists() else None
    qa = read(qa_path) if qa_path.exists() else None
    require(scope['identity'] == result['identity'] == identity,
            'Original execution identity differs: ' + identity)
    require(result['status'] in (CASE_PASS, CASE_FAILED), 'Original case is not terminal: ' + identity)
    require(result['scope_sha256'] == sha(root / 'FROZEN_SCOPE.json'),
            'Original case/scope binding differs: ' + identity)
    if result['status'] == CASE_PASS:
        require(producer is not None and qa is not None and producer['identity'] == qa['identity'] == identity
                and producer['status'] == 'PRODUCED_DESCRIPTIVE_REAL_FULLSCAN_ONLY'
                and qa['status'] == QA_PASS and qa['actual_complete_search_QA_performed'] is True,
                'A passed original case needs complete original primary/QA evidence: ' + identity)
        require(len(result['phases']) == 2 and all(p['status'] == 'ACCEPTED_DESCRIPTIVE_PHASE_ONLY' for p in result['phases']),
                'Both complete phase acceptance receipts required: ' + identity)
        require(qa['scope_sha256'] == result['scope_sha256']
                and qa['producer_receipt_sha256'] == sha(producer_path)
                and qa['payload_manifest_sha256'] == sha(root / 'observation/payload/MANIFEST.json'),
                'Exact original QA/source receipt binding differs: ' + identity)
    else:
        require(any(p['status'] == 'FAILED_RETAINED_NO_RETRY' for p in result['phases']),
                'A failed original identity must preserve a failed phase: ' + identity)
        if qa is not None:
            require(qa['identity'] == identity and qa['status'] == 'FAILED_DESCRIPTIVE_REAL_FULLSCAN_QA_ONLY',
                    'A failed original QA must stay failed: ' + identity)
    for document in (result, producer, qa):
        if document is not None:
            require(document['scientific_bank_admission'] is False and document['qualified_SETI_detection'] is False,
                    'Package must preserve descriptive interpretation: ' + identity)
    return scope, {'identity': identity, 'status': result['status'],
        'original_independent_QA_verified': result['status'] == CASE_PASS,
        'original_QA_status': qa['status'] if qa else 'NO_QA_REPORT',
        'failed_bytes_and_receipts_preserved': result['status'] == CASE_FAILED}


def _check_original_audits(report, baseline_source, cohort_result):
    baseline = read(baseline_source / 'report/FINAL_AUDIT.json')
    require(baseline['status'] == 'PASS' and baseline.get('errors', []) == [],
            'Completed B00 independent audit must remain passed')
    final = read(report / 'FINAL_AUDIT.json')
    resource = read(report / 'RESOURCE_AUDIT.json')
    interpretation = read(report / 'INTERPRETATION_REVIEW.json')
    require(final['cohort_execution_status'] == cohort_result['status']
            and resource['original_cohort_status'] == cohort_result['status'],
            'Original audit outcome must match the unchanged terminal cohort')
    if cohort_result['status'] == COHORT_PASS:
        require(final['status'] == 'PASS' and final.get('errors', []) == [],
                'Passed original cohort audit must have no errors')
    else:
        expected = {'B06 physical payload science_arrays.npz',
                    'B06 qa accepted whole-child process closure',
                    'B06 complete independent verified band'}
        expected_resource = {
            'exact-physical-phase-output-within-reserved-slot:' + CASE_PREFIX + '06:primary',
            'exact-physical-log-receipt-bytes-within-slot:' + CASE_PREFIX + '06:primary'}
        require(final['status'] == 'FAIL' and set(final['errors']) == expected
                and final.get('unexpected_audit_errors', []) == []
                and final['known_retained_failure_band'] == 'B06'
                and final['B06_original_failure_remains_unchanged'] is True,
                'Package preserves the exact known original B06 audit failure')
        require(resource['status'] == 'FAIL_RESOURCE_ACCOUNTING_AUDIT'
                and set(resource['errors']) == expected_resource
                and resource['original_failure_retained'] is True,
                'Package preserves known physical-output accounting deltas as failed audit evidence')
    require(interpretation['status'].startswith('PASS_SCIENTIFIC_INTERPRETATION')
            and interpretation['original_cohort_status'] == cohort_result['status'],
            'Original report needs a matching scientific wording review')
    return {'final_audit_status': final['status'], 'final_audit_errors': final['errors'],
        'resource_audit_status': resource['status'], 'resource_audit_errors': resource['errors'],
        'interpretation_review_status': interpretation['status'],
        'failed_evidence_is_packaged_without_promoting_it_to_pass': True}


def _check_restoration(source, workspace):
    """Read separate saved-result evidence, never promote the failed cohort."""
    prepared = source / 'tools/saved_payload_restore_20261016'
    root = workspace / 'work' / RESTORE_ID
    summary = {'identity': RESTORE_ID, 'status': 'NOT_EXECUTED_PREPARATION_ONLY',
        'separate_saved_search_QA_verified': False, 'additional_verified_bands': 0,
        'additional_verified_scan_maps': 0, 'original_cohort_status_changed': False}
    if not root.exists():
        return prepared, None, None, summary
    scope = read(root / 'FROZEN_SCOPE.json')
    result = read(root / 'RESULT.json')
    require(scope['identity'] == result['identity'] == RESTORE_ID
            and result['status'] in (RESTORE_PASS, CASE_FAILED),
            'Wait for ALLREADY: separate restoration study must be terminal')
    require(result['scope_sha256'] == sha(root / 'FROZEN_SCOPE.json') == sha(prepared / 'SCOPE.json'),
            'Separate restoration scope binding differs')
    require(result['original_cohort_status'] == COHORT_INCOMPLETE
            and result['original_failure_retained'] is True
            and result['no_primary_detector_invocation'] is True
            and result['scientific_bank_admission'] is False
            and result['qualified_SETI_detection'] is False,
            'Separate verification cannot rewrite the original cohort outcome')
    for declaration in scope['origin_evidence_pins'] + [scope['truncated_array_archive']]:
        check_pin(declaration)
    final = read(prepared / 'report/FINAL_AUDIT.json')
    summary.update(status=result['status'], final_audit_status=final['status'],
        result_sha256=sha(root / 'RESULT.json'), original_failed_NPZ=scope['truncated_array_archive'],
        expected_exact_restored_NPZ=scope['expected_restored_array_archive'])
    if result['status'] == RESTORE_PASS:
        require(final['status'].startswith('PASS') and final.get('errors', []) == [],
                'Complete separate saved-result verification needs its passed final audit')
        require(len(result['phases']) == 2 and all(p['status'] == 'ACCEPTED_SEPARATE_RESTORATION_STUDY_PHASE'
                for p in result['phases']), 'Both separate restoration/QA phases must be accepted')
        restored = read(root / 'RESTORATION_REPORT.json')
        wrapper = read(root / 'SAVED_QA_REPORT.json')
        numerical = read(root / 'NUMERICAL_QA_REPORT.json')
        require(restored['status'] == 'RESTORED_EXACT_ORIGINAL_PAYLOAD_BYTES_ONLY'
                and wrapper['status'] == 'PASS_RESTORED_SAVED_DESCRIPTIVE_SEARCH_QA_ONLY'
                and numerical['status'] == QA_PASS and numerical['actual_complete_search_QA_performed'] is True,
                'Exact restored bytes and independent saved-result QA must both pass')
        require(wrapper['numerical_report_sha256'] == sha(root / 'NUMERICAL_QA_REPORT.json')
                and wrapper['restoration_report_sha256'] == sha(root / 'RESTORATION_REPORT.json')
                and wrapper['scope_sha256'] == result['scope_sha256']
                and wrapper['original_failure_and_cohort_unchanged'] is True
                and wrapper['primary_detector_or_generator_invoked'] is False
                and wrapper['new_saved_result_verification_is_original_case_retry'] is False,
                'Separate saved-result report binding/interpretation differs')
        require(len(numerical['full_search_checks']) == 6
                and all(c['complete_search_recomputed'] and c['complete_retained_maps_checked']
                        for c in numerical['full_search_checks']), 'All six saved search maps need independent QA')
        require(pin(root / 'observation/payload/science_arrays.npz') == scope['expected_restored_array_archive'],
                'Restored copy must match the exact original complete NPZ hash, not merely equivalent arrays')
        producer = read(root / 'observation/PRODUCER.json')
        census = producer['output_census']
        summary.update(separate_saved_search_QA_verified=True, additional_verified_bands=1,
            additional_verified_scan_maps=6,
            retained_top5_ON_ge10_count=census['retained_top5_ON_ge10_count'],
            OFF_ge8_inventory_rows=sum(census['OFF_inventory_rows'].values()),
            maximum_ON_score=numerical['independent_global_pre_OFF_ON_maximum'],
            maximum_OFF_score=max(s['maximum_retained_score'] for s in census['scans'] if s['role'] == 'OFF'))
    return prepared, root, scope, summary


def _readme(aggregate, dependencies, restoration):
    total = aggregate['verified_totals']
    verified = aggregate['combined_bands_verified']
    if restoration['separate_saved_search_QA_verified']:
        saved = f'''Den særskilte undersøgelse {RESTORE_ID}
har genskabt en ny B06-kopi med præcis den oprindelige, før-fejlen fastlagte SHA-256
og bestået separat fuld uafhængig QA af det gemte søgeresultat. Dermed er de gemte
søgeresultater fra {verified + 1}/9 bånd og {aggregate['verified_scan_maps'] + 6} scanningskort verificeret.
Det ændrer ikke den oprindelige kohortes fejlstatus eller 7/8-afslutning. Ingen ny
primær B06-søgning er kørt. Den beskadigede original og den nye kopi er begge med.
Samlet for de verificerede gemte søgeresultater: {total['retained_top5_ON_ge10_count'] + restoration['retained_top5_ON_ge10_count']} bevarede ON-hypoteser
med score ≥10 og {total['OFF_ge8_inventory_rows'] + restoration['OFF_ge8_inventory_rows']} OFF-nativeidentiteter med score ≥8.
'''
    elif restoration['status'] == 'NOT_EXECUTED_PREPARATION_ONLY':
        saved = '''En særskilt restaurerings-/verifikationsrute er kun forberedt og har ikke
et afsluttet resultat i denne pakke. B06 tælles fortsat ikke som verificeret.
'''
    else:
        saved = f'''Den særskilte restaurerings-/verifikationsundersøgelse sluttede med status
{restoration['status']}. Dens fejl og delvise filer er medtaget uændret.
Den giver ingen ekstra verificerede bånd eller nulobservationer; B06 er fortsat
udelukket fra de verificerede videnskabelige summer.
'''
    return f'''SETI – ALLE NI GEMTE 2017-BÅND, 16. OKTOBER 2026

OPRINDELIG KOHORTE OG SÆRSKILT GEMT-RESULTAT-KONTROL
Den oprindelige kohorte har status {aggregate['cohort_status']}:
{aggregate['new_bands_verified']}/8 nye bånd har fuld accepteret afslutning og QA.
Sammen med uændret B00 er {verified}/9 oprindelige bånd og {aggregate['verified_scan_maps']} scanningskort verificeret.
B06's oprindelige QA fejlede. Dets bevarede beskadigede NPZ og de oprindelige
fejlede audits indgår som fejlbevis, aldrig som en godkendt nulobservation.
Den oprindelige FINAL_AUDIT er FAIL og RESOURCE_AUDIT bevarer de dokumenterede
fysiske output-/logdifferencer; pakning omdøber ikke disse forhold til PASS.

{saved}

For de {verified} oprindeligt verificerede bånd alene: {total['retained_top5_ON_ge10_count']} bevarede ON-hypoteser
med score ≥10 og {total['OFF_ge8_inventory_rows']} komplette OFF-nativeidentiteter med score ≥8.
ON-tallet omfatter bevaret topfem pr. referencekanal; et positivt antal ville ikke
være en udtømmende optælling af alle ON-hypoteser over snittet. OFF-inventaret er
komplet inden for den erklærede native-fire-række-familie og dens faste halo.
Den oprindelige rapport står under source/analysis/real_fullscan_cohort_20261016/report/.
Særskilt restaurerings-/QA-evidens står under source/tools/saved_payload_restore_20261016/
og work/{RESTORE_ID}/, når ruten er kørt.
Scorerne og snittene er ikke kalibrerede sigma-, SNR- eller sandsynlighedsniveauer.
Dette er efterudvalgte, tidligere eksponerede data fra ét besøg i 2017 med fire
oprindelige retninger. Nye dokumenterede kørsler er ikke nye teleskopdata,
uafhængig genobservation eller et krav om første gennemgang af hypoteserne.
Der er ingen rangkalibrering, FAP, fysisk klassifikation eller SETI-kvalifikation.
Resultaterne gælder kun de verificerede faste bånd, scorecuts og søgefamilier.

INDHOLD OG BEVARELSE
work/ indeholder alle oprindelige B00- og B01–B08-arbejdstræer, inklusive fejlede
B06-bytes, komplette bevarede payloads, søgekort, aliaser, OFF-inventarer,
proceslogs, scopes, SHA-manifester og QA-bilag. Den særskilte rutes fulde træ,
inklusive eventuel genskabt kopi, er bevaret separat. source/ indeholder kildekode,
scopes, offentlige readback-bilag og afsluttende rapporter/audits. De globale
engangsclaims er medtaget. Originale eksekveringsfiler og kodebytes er uændrede.
Pakning udfører ingen ny søgning, numerisk QA, array-dekodning eller rekonstruktion.

KONTROL AF DENNE PAKKE
Kun Python-standardbiblioteket kræves til kontrol af filbytes og SHA-256:
  python VERIFY_PACKAGE.py
Ved kontrol direkte i ZIP-filen, uden udpakning:
  python VERIFY_PACKAGE.py --zip SETI_ALLE_NI_BAAND_2026-10-16.zip
ZIP-varianten kontrollerer også samtlige ydre ZIP-CRC'er. Kontrollen dokumenterer
byteintegritet, også af bevidst bevarede defekte originalfiler; den erklærer ikke
deres interne payload gyldigt og foretager ingen ny videnskabelig validering. PACKAGE_MANIFEST
indeholder SHA-256 for hver anden fil og udelader bevidst sin egen hash for at
undgå en selvreference. Pakke-ZIP'ens SHA-256 leveres separat i en sidecarfil.

NUMERISK REPRODUKTION OG EKSTERNE FORUDSÆTNINGER
En fuld uafhængig numerisk reproduktion kræver Python, NumPy 2.3.5, SciPy 1.17.0,
msgpack 1.2.1 og det originale kildearkiv. Alle faktisk brugte rå arrays findes
også i de verificerede komplette payloads; det defekte oprindelige B06-payload
er uændret og skal ikke forveksles med en eventuel separat genskabt kopi.
Det oprindelige teleskop-ZIP gentages ikke i denne pakke:
  SETI_NATIVE_SPOR_2026-10-14.zip
  {dependencies['original_telescope_archive']['bytes']} bytes
  SHA-256: {dependencies['original_telescope_archive']['sha256']}
  Eksisterende kildefil: {dependencies['original_telescope_archive']['library_file_id']}
Den komplette tidligere engineeringpakke er separat tilgængelig som
{dependencies['complete_engineering_chain']['library_file_id']}. Her medtages
engineering-RESULT, dets præcise SHA og fastlåste kilder, men ikke de store
engineering-arrays. Dette er et forudsætningsbilag, ikke en ny science-admission.

De oprindelige scopes og procesbilag bevarer deres absolutte eksekveringsstier.
De er proveniens og kan ikke køres portabelt blot ved at gentage de gamle CLI'er.
En ny numerisk kørsel kræver særskilt scope, identitet og ressourceafgrænsning;
de medtagne engangsidentiteter må ikke genåbnes eller genforsøges.
Original A/B er fortsat FAIL_CLOSED. 2016- og 2019-ruterne er fortsat lukkede.
'''


def build(workspace, output):
    """Package only terminal, audited originals. No destination is overwritten."""
    workspace, output = Path(workspace).resolve(), Path(output).resolve()
    source = workspace / 'source'
    cohort_source = source / 'analysis/real_fullscan_cohort_20261016'
    baseline_source = source / 'analysis/real_fullscan_20261016'
    cohort_scope = read(cohort_source / 'COHORT_SCOPE.json')
    cohort_root = Path(cohort_scope['output_root'])
    cohort_result = read(cohort_root / 'RESULT.json')
    require(cohort_scope['identity'] == COHORT_ID and cohort_result['identity'] == COHORT_ID and
            cohort_result['status'] == COHORT_PASS and cohort_result['completed_verified_bands'] == 8,
            'Wait for ALLREADY: every new band must have completed independent QA')
    report = cohort_source / 'report'
    for path in (report / 'FINAL_AUDIT.json', baseline_source / 'report/FINAL_AUDIT.json'):
        document = read(path)
        require(document['status'] == 'PASS' and document.get('errors', []) == [],
                'Wait for ALLREADY: final independent audit must pass: ' + str(path))
    read(report / 'REPORT_MANIFEST.json')
    aggregate = read(report / 'AGGREGATE.json')
    require(aggregate['combined_bands_verified'] == 9 and aggregate['new_bands_verified'] == 8 and
            aggregate['verified_scan_maps'] == 54, 'Complete nine-band report required')
    require(aggregate['verified_totals']['payload_arrays'] == 9 * 460, 'All54 raw and4086 result arrays required')
    for path in (report / 'PUBLIC_FREEZE_READBACK.json', baseline_source / 'report/PUBLIC_FREEZE_READBACK.json'):
        read(path)
    baseline_result = check_pin(cohort_scope['B00_complete_prerequisite'])
    baseline_root = baseline_result.parent
    roots = [baseline_root]
    scopes = [_check_case(baseline_root, CASE_PREFIX + '00')]
    require([c['canonical_index'] for c in cohort_scope['cases']] == list(range(1, 9)), 'Exactly eight frozen new cases required')
    for entry in cohort_scope['cases']:
        require(sha(entry['scope_path']) == entry['scope_sha256'], 'Frozen per-case scope differs')
        root = Path(entry['output_root'])
        roots.append(root)
        scopes.append(_check_case(root, entry['identity']))
    engineering_result = check_pin(cohort_scope['integration_acceptance'])
    require(read(engineering_result)['status'] == 'PASS_COMPLETE_SEARCH_ENGINEERING_ONLY', 'Complete engineering prerequisite required')
    engineering_scope = read(engineering_result.parent / 'FROZEN_SCOPE.json')
    scopes += [cohort_scope, engineering_scope]
    frozen_pins = {}
    for scope in scopes:
        for declaration in scope['source_pins']:
            name = declaration['path']
            relative = PurePosixPath(name)
            require(not relative.is_absolute() and '..' not in relative.parts, 'Unsafe original source path')
            value = {k: declaration[k] for k in ('bytes', 'sha256')}
            require(name not in frozen_pins or frozen_pins[name] == value, 'Conflicting immutable source pins: ' + name)
            frozen_pins[name] = value
            require(pin(source / name) == value, 'Original frozen source changed: ' + name)

    entries = {}

    def add(path):
        path = Path(path).resolve()
        require(workspace in path.parents, 'Packaged original must remain inside workspace: ' + str(path))
        relative = path.relative_to(workspace).as_posix()
        actual = pin(path)
        require(relative not in entries or entries[relative]['pin'] == actual, 'Conflicting package member')
        entries[relative] = {'path': path, 'pin': actual}

    def tree(path, excluded=()):
        base = Path(path)
        for member in _regular_tree(base):
            relative = member.relative_to(base)
            if not any(part in excluded for part in relative.parts):
                add(member)

    tree(cohort_root)
    tree(baseline_root)
    #Original binary execution payloads live under work/. Source/results are
    #publication metadata mirrors and are omitted to avoid duplicate artifacts.
    tree(cohort_source, excluded=('results',))
    tree(baseline_source, excluded=('results',))
    for name in frozen_pins:
        add(source / name)
    add(engineering_result)
    add(engineering_result.parent / 'FROZEN_SCOPE.json')
    for optional in (source / 'tools/fullsearch_integration_20261016/report/FINAL_AUDIT.json',
                     workspace / 'work/SOURCE_RECOVERY_AUDIT_20261016.json'):
        if optional.is_file():
            add(optional)
    claims = workspace / 'work/REAL_DESCRIPTIVE_CLAIMS_20261016'
    for identity in [COHORT_ID] + [CASE_PREFIX + f'{index:02d}' for index in range(9)]:
        add(claims / (identity + '.json'))

    original_zip = cohort_scope['source_archive']
    require(original_zip['bytes'] == 48468705 and original_zip['sha256'] == SOURCE_ZIP_SHA,
            'Exact original telescope source dependency required')
    dependencies = {
        'original_telescope_archive': {'filename': 'SETI_NATIVE_SPOR_2026-10-14.zip',
            'bytes': 48468705, 'sha256': SOURCE_ZIP_SHA, 'included_in_this_package': False,
            'library_file_id': SOURCE_ZIP_LIBRARY_ID, 'all54_actual_raw_arrays_are_also_in_payloads': True},
        'complete_engineering_chain': {'filename': 'SETI_FULD_KAEDE_2026-10-16.zip',
            'library_file_id': ENGINEERING_LIBRARY_ID, 'included_in_this_package': False,
            'engineering_result_included': engineering_result.relative_to(workspace).as_posix(),
            'engineering_result_sha256': sha(engineering_result)},
        'full_numeric_reproduction_runtime': {'numpy': '2.3.5', 'scipy': '1.17.0', 'msgpack': '1.2.1',
            'python_required': True, 'recorded_absolute_execution_paths_are_not_portable_reexecution_commands': True}}
    prior_zip = workspace / 'deliverables/SETI_FULD_KAEDE_2026-10-16.zip'
    if prior_zip.is_file():
        dependencies['complete_engineering_chain'].update(pin(prior_zip))
    generated = {'README_DA.txt': _readme(aggregate, dependencies).encode('utf-8'),
                 'VERIFY_PACKAGE.py': VERIFY_SOURCE.encode('utf-8')}
    inventory = {name: info['pin'] for name, info in sorted(entries.items())}
    for name, value in generated.items():
        inventory[name] = {'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}
    manifest = {'schema': 'SETI_NINE_BANDS_BYTE_PACKAGE_V1', 'package_name': PACKAGE_NAME,
        'created_UTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'complete_bands': 9, 'complete_scan_maps': 54, 'all_actual_source_raw_arrays': 54,
        'members': inventory, 'manifest_excludes_its_own_hash': True,
        'immutable_union_source_pins': frozen_pins, 'external_dependencies': dependencies,
        'preserved_original_execution_bytes': True, 'numeric_recomputations_or_array_decodes': 0,
        'verification_scope': 'All delivered member lengths and SHA-256; outer ZIP CRC. Scientific QA is evidenced by original reports, not rerun.',
        'rank_status': 'NOT_APPLIED_NO_CALIBRATION', 'scientific_bank_admission': False,
        'qualified_SETI_detection': False, 'original_A_B': 'FAIL_CLOSED'}
    generated[MANIFEST_NAME] = (json.dumps(manifest, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    require(not output.exists(), 'Refuse to replace an existing final package')
    partial = output.with_suffix(output.suffix + '.partial')
    require(not partial.exists(), 'Retained partial package already exists; inspect before a new attempt')
    with zipfile.ZipFile(partial, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as archive:
        for name, info in sorted(entries.items()):
            archive.write(info['path'], PACKAGE_NAME + '/' + name)
            require(pin(info['path']) == info['pin'], 'Original changed while packaging: ' + name)
        for name, value in generated.items():
            archive.writestr(PACKAGE_NAME + '/' + name, value)
    require(partial.stat().st_size <= MAX_ARCHIVE_BYTES, 'Final archive exceeds256MiB packaging ceiling')
    #Execute only the generated standard-library byte verifier on opaque files.
    namespace = {'__name__': 'seti_package_byte_verifier', '__file__': str(HERE / 'VERIFY_PACKAGE.py')}
    exec(compile(VERIFY_SOURCE, 'VERIFY_PACKAGE.py', 'exec'), namespace)
    _, count = namespace['verify_zip'](partial)
    os.replace(partial, output)
    final_pin = pin(output)
    sidecar = output.with_suffix(output.suffix + '.sha256')
    with sidecar.open('x', encoding='ascii') as stream:
        stream.write(final_pin['sha256'] + '  ' + output.name + '\n')
    receipt = {'status': 'PASS_ALL_PACKAGE_BYTES', 'zip': str(output), **final_pin,
        'members_verified': count, 'outer_ZIP_CRC': 'PASS', 'complete_bands': 9,
        'all_actual_source_raw_arrays': 54, 'source_files_modified': False,
        'numeric_recomputations_or_array_decodes': 0,
        'manifest_sha256': hashlib.sha256(generated[MANIFEST_NAME]).hexdigest(),
        'sidecar': str(sidecar)}
    receipt_path = output.with_suffix(output.suffix + '.json')
    with receipt_path.open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write('\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=WORKSPACE)
    parser.add_argument('--output', type=Path, default=WORKSPACE / 'deliverables' / (PACKAGE_NAME + '.zip'))
    parser.add_argument('--build-after-all-ready', action='store_true',
                        help='Explicitly build after every final report/audit is complete')
    args = parser.parse_args()
    require(args.build_after_all_ready, 'Owner must confirm ALLREADY before packaging; no files have been written')
    print(json.dumps(build(args.workspace, args.output), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
