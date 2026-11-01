"""Summarize completed acquisition/production; never edits frozen inputs."""
import csv
from decimal import Decimal
import json
import sys

sys.dont_write_bytecode = True
from common import BASE, HERE, csvout, csvrows, dump, now, require, sha, verified_scope


def main():
    rows, previous, protocol, freeze = verified_scope()
    acquisition = json.loads((HERE / 'acquisition/ACQUISITION_RESULT.json').read_text())
    manifest = json.loads((HERE / 'acquisition/DOWNLOAD_MANIFEST.json').read_text())
    run = json.loads((HERE / 'production/SUMMARY.json').read_text())
    publication = json.loads((HERE / 'acquisition/PUBLICATION.json').read_text())
    audit = json.loads((HERE / 'audit/SUMMARY.json').read_text())
    require(run['status'] == 'COMPLETED' and run['analyzed_exposures'] == 100 and run['not_analyzed_exposures'] == 0,
            'Expected complete production')
    require(acquisition['result_counts'] == {'PASS_METADATA_ONLY': 100}, 'Unexpected acquisition exclusions')
    require(audit['status'] == 'PASS_INDEPENDENT_NUMERICAL_AUDIT', 'Independent audit not complete')
    failures = []
    for receipt in manifest:
        for number, attempt in enumerate(receipt['attempts'], 1):
            if attempt['outcome'] != 'FAILED':
                continue
            successful = [i for i, a in enumerate(receipt['attempts'], 1) if a['outcome'] == 'SUCCESS']
            failures.append(dict(dp_id=receipt['dp_id'], selection_index=receipt['selection_index'],
                                 failed_attempt_index=number, error_type=attempt['error_type'], error=attempt['error'],
                                 started_utc=attempt['started_utc'], elapsed_seconds=attempt['elapsed_seconds'],
                                 returned_payload_bytes=attempt['returned_payload_bytes'],
                                 success_attempt_index=successful[0] if successful else None,
                                 final_download_status=receipt['download_status'], final_header_status=receipt['header_status']))
    csvout(HERE / 'FAILED_ATTEMPTS.csv', failures)
    original = csvrows(BASE / 'selection/MAIN100.csv')
    extension1 = csvrows(BASE / 'v2/selection/MAIN100.csv')
    prior1 = json.loads((BASE / 'production/RUN_SUMMARY.json').read_text())
    prior2 = json.loads((BASE / 'v2/production/SUMMARY.json').read_text())
    allrows = original + extension1 + rows
    seconds = sum(Decimal(r['t_exptime']) for r in allrows)
    require(len(allrows) == len({r['dp_id'] for r in allrows}) == 300, 'Main exposure count mismatch')
    total_v1 = prior1['threshold_run_status_counts']['PRELIMINARY_EMISSION_HIT'] + prior2['v1_hits'] + run['v1_hits']
    total_v2 = prior2['v2_hits'] + run['v2_hits']
    require(total_v1 == 22 and total_v2 == 669 and seconds == Decimal('255148.743'), 'Aggregate totals mismatch')
    source_names = ['FREEZE.json', 'MAIN100.csv', 'acquisition/PUBLICATION.json', 'acquisition/ROOT_PUBLICATION_VERIFICATION.json',
                    'acquisition/DOWNLOAD_MANIFEST.json', 'acquisition/ACQUISITION_RESULT.json',
                    'production/RUN_INPUTS.json', 'production/SUMMARY.json', 'production/V1_HITS.csv', 'production/V2_HITS.csv',
                    'production/V2_DISPOSITIONS.csv', 'audit/SUMMARY.json', 'FAILED_ATTEMPTS.csv', 'acquisition.log', 'analysis.log']
    summary = dict(created_utc=now(), status='COMPLETED_AND_INDEPENDENTLY_AUDITED', published_freeze_commit=publication['freeze_commit'],
                   freeze_sha256=sha(HERE / 'FREEZE.json'), frozen_source_hashes_verified=len(freeze['source_hashes']),
                   selected_new_exposures=100, unique_new_raw_exposures=100, new_targets=16,
                   new_exposure_seconds=run['exposure_seconds'], new_exposure_hours=run['exposure_seconds']/3600,
                   previous_inputs_excluded=209, main_exposures_total=300, distinct_main_targets_total=20,
                   main_exposure_seconds_total=str(seconds), main_exposure_hours_total=float(seconds/Decimal(3600)),
                   v1_new_hits=6, v1_total_hits=total_v1, v1_total_exposures=300,
                   v2_new_hits=336, v2_prior_hits=333, v2_total_hits=total_v2, v2_total_exposures=200,
                   v2_new_origin_status='UNREVIEWED_IN_UNCHANGED_PRODUCTION_CATALOG',
                   older_v2_origin_status='Retains its separate, later follow-up dispositions; no combined origin-status classification is asserted.',
                   headers_passed=100, production_exposures_completed=100, omitted_exposures=0,
                   acquisition_attempts=sum(len(r['attempts']) for r in manifest), failed_attempts=len(failures),
                   failed_attempt_errors=[r['error'] for r in failures], successful_retry_exposures=len(failures),
                   acquisition_payload_bytes=acquisition['returned_payload_bytes'], conservative_payload_charge=acquisition['conservative_charged_payload_bytes'],
                   acquisition_seconds=acquisition['elapsed_seconds'], production_compute_seconds=run['wall_seconds'],
                   independent_audit_status=audit['status'], independent_exact_algorithm_reruns=len(audit['exact_reruns']),
                   independent_replayed_exposures=3, source_hashes={name:sha(HERE/name) for name in source_names},
                   limitations=['No exposure replacement or algorithm/configuration retuning occurred.',
                                'Profile/run triggers are not laser identifications or calibrated detection significances.',
                                'There is no extension02-specific sensitivity measurement; the earlier192 injection trials remain conditional.',
                                'Absence from pinned published ADP/raw inventories does not demonstrate absence of previous searches.',
                                'V2 totals refer only to200 exposures; the first100 were not rerun with V2.'])
    dump(HERE / 'RESULTS.json', summary)
    failure_rows = '\n'.join(f"| `{r['dp_id']}` | {r['error']} | {r['success_attempt_index']} | Bestået |" for r in failures)
    text = f'''# HARPS extension02: gennemført og kontrolleret

Alle **100 nye eksponeringer** er hentet, metadatakontrolleret og analyseret med de uændrede, frosne V1- og V2-algoritmer. Udvidelsen giver **6 V1-træf og 336 V2-profiltræf**. De er foreløbige søgetræf; dette er ikke identifikationer af lasere.

## Omfang og samlede tal

De nye data dækker 16 mål og 86.849,578 sekunders observation (**24,124883 timer**). Der er ingen genbrugte ADP-ID'er, rå eksponeringer eller mål/starttidskombinationer fra de 209 tidligere hoved-, udviklings- og valideringsinputs. Alle 100 frosne eksponeringer blev analyseret; ingen blev erstattet eller udeladt.

| Delmængde | Hovedeksponeringer | V1-træf | V2-profiltræf |
|---|---:|---:|---:|
| Oprindelig hovedserie | 100 | 10 | Ikke kørt |
| Første udvidelse | 100 | 6 | 333 |
| Extension02 | 100 | 6 | 336 |
| Total for den respektive metode | V1: 300; V2: 200 | 22 | 669 |

Projektets hovedserier omfatter nu **300 unikke eksponeringer af 20 forskellige mål**, med samlet eksponeringstid **255.148,743 sekunder = 70,874651 timer**. Udviklings-/valideringsdata er ikke medregnet. De 669 V2-træf stammer fra **200** eksponeringer; V2 er ikke kørt på den oprindelige hovedserie på 100.

De nye 336 events har stabile ID'er `V2E2-0001`–`V2E2-0336` og bevarer `UNREVIEWED` i deres uændrede produktionskatalog. De oprindelige 333 har deres egne opfølgningsresultater. Vi sammenlægger ikke deres forskellige vurderingsstadier til én fælles oprindelsesklassifikation. Nye beskrivende og rådata-baserede opfølgninger ligger separat fra produktionen.

## Prospektiv frysning og hentning

Udvalg, protokol og kode blev publiceret og verificeret **før hentning** ved commit [{publication['freeze_commit']}](https://github.com/andersenmartin-blip/setisearch/commit/{publication['freeze_commit']}). `FREEZE.json` har SHA256 `{sha(HERE/'FREEZE.json')}`. Den oprindelige frosne README, udvælgelse og kode er uændret; denne resultatfil er oprettet efter kørslen.

Hentningen tog **244,42 sekunder** og overførte **526.334.400 response-body-bytes**, under den frosne grænse på 700.000.000 bytes. HTTP/TLS-overhead er ikke med i byteopgørelsen. Hver fil var under 10.000.000 bytes. Der var **103 forsøg: 100 vellykkede og tre HTTP 503-fejl**, hver efterfulgt af ét vellykket forsøg. Fejlforsøgene registrerede nul læste response-body-bytes. Ingen observationer blev udskiftet, og der blev ikke startet en ny uregistreret hentning.

| Eksponering | Første forsøgs fejl | Vellykket forsøg | Endelig headerstatus |
|---|---|---:|---|
{failure_rows}

Den maskinlæsbare fejlliste er `FAILED_ATTEMPTS.csv`; samtlige forsøg, tider, svarmetadata og filhashes findes i `acquisition/receipts/` og `acquisition/DOWNLOAD_MANIFEST.json`. Root-verificeringen af publiceringen er bevaret som `acquisition/ROOT_PUBLICATION_VERIFICATION.json`.

## Kontroller og analyse

Alle **100/100** filer bestod kontroller for hash, format, instrument, mål, tid, eksponeringstid, position, tilsigtede koordinater, observation/proposal, ADP-ID, præcist rå progenitor-ID fra metadataforespørgslen, bølgelængdeenheder, luftbølgelængde, barycentrisk reference og endelig BERV. Alle **55 frosne kildehashes** stemmer fortsat, inklusive de oprindelige algoritmer, konfigurationer og kataloger.

Den uændrede produktion afsluttede 100/100 inputs uden fejl. V1 søgte i **30.650.654 samples**. V2 søgte i **30.618.855 samples** og bevarede alle **23.242** screenede events: 22.885 afviste, 21 dubletfits og 336 accepterede profiltræf. Selve analyseberegningen tog **14,27 sekunder**. Hentning, filkontroller og efterfølgende vurderinger indgår ikke i denne beregningstid.

Den uafhængige numeriske audit bestod. Den kontrollerede alle 100 inputhashes og headers, identiteter, eksklusioner, bytes, tabelserialiseringer og totalsummer. Den første, midterste og sidste eksponering i den frosne rækkefølge blev genkørt med begge algoritmer: **seks eksakte matches** til gemte fulde resultater og inputmetadata. Auditens genkørsel bruger de samme frosne algoritmer; den er ikke en ny, uafhængigt implementeret detektor. Se `audit/SUMMARY.json`.

## Fortolkning og begrænsninger

Ingen tærskler eller detektorkonfigurationer blev ændret efter adgang til de nye spektraldata. Der er **ingen særskilt følsomhedsmåling for extension02**. De tidligere 192 injektionsforsøg er betingede valideringsresultater og må ikke omfortolkes som denne udvidelses målte følsomhed, fuldstændighed eller falskalarmrate.

Udvælgelsen bygger fortsat på det oprindelige alfabetisk afgrænsede metadataudtræk og er ikke repræsentativ for hele HARPS-arkivet. Fravær af match i det fastlåste litteraturprojekts ADP-/rå-ID-inventar er ikke bevis for, at observationerne aldrig tidligere er blevet undersøgt. Oprindelsen af de nye søgetræf kræver den separate opfølgning.

`RESULTS.json` indeholder de samme totalsummer og kildehashes. `production/SUMMARY.json`, de komplette hændelsestabeller og per-spektrum-resultater bevarer den faktiske produktion. `acquisition.log` og `analysis.log` bevarer kørselsloggene.
'''
    (HERE / 'RESULTS.md').write_text(text)
    print(json.dumps(dict(status=summary['status'], total_main=300, total_hours=summary['main_exposure_hours_total'],
                          v1_total=22, v2_total=669, v2_exposures=200, results_md_sha256=sha(HERE/'RESULTS.md'), results_json_sha256=sha(HERE/'RESULTS.json'))))


if __name__ == '__main__':
    main()
