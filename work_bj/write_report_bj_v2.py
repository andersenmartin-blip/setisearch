"""Render the BJ V2 report with the failed first batch10 preserved explicitly.

Reads only final JSON metadata. Does not search, decode telescope data, query
Library or publish to GitHub. The Library identity is supplied by the caller
after the verified result package has been saved.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work_bj'


def require(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def dk(value, decimals=0):
    return format(value, f',.{decimals}f').replace(',', '\x00').replace('.', ',').replace('\x00', '.')


def render(summary, package, library_file_id):
    batches = summary['batch_results']
    cumulative = summary['cumulative_BG_BH_BI_BJ']
    require(summary['status'] == 'TWELVE_EFFECTIVE_REAL_BATCHES_AUDITED_WITH_PRESERVED_FAILED_FIRST_ATTEMPT'
            and summary['completed_batches'] == len(batches) == 12,
            'Completed twelve-batch summary required')
    require(summary['q_list'] == list(range(25, 121))
            and cumulative['q_list'] == list(range(1, 121)), 'Expected campaign/cumulative scope differs')
    require([q for b in batches for q in b['q_list']] == summary['q_list']
            and all(b['batch'] == i for i, b in enumerate(batches, 1)), 'Ordered batch scope differs')
    require(all(b['actual_search_exit_code'] == b['actual_audit_exit_code'] == 0 for b in batches),
            'Closed successful search/audit receipts required')
    require(summary['independent_scalar_sum_comparisons']
            == sum(b['independent_scalar_sum_comparisons'] for b in batches) == 20736
            and summary['shared_kernel_calibration_vector_replays']
            == sum(b['shared_kernel_calibration_vector_replays'] for b in batches) == 6912,
            'Expected measured finite audit counts differ')
    require(summary['total_correlated_track_trials_including_OFF']
            == sum(b['total_correlated_track_trials_including_OFF'] for b in batches) == 5196054528
            and cumulative['total_correlated_track_trials_including_OFF'] == 6495068160,
            'Derived trial totals differ')
    require(summary['new_archive_requests'] == summary['new_independent_observations']
            == summary['new_unique_archive_ID_credit'] == 0, 'Exposure/access credit differs')
    require(package['binary_members'] == 2132 and package['archive_members'] == 2133
            and package['effective_binary_members'] == 1968
            and package['preserved_failed_binary_members'] == 164
            and package['file_name'] == 'SETI_BJ_SEARCH_RESULTS_V2_2026-10-30.zip',
            'Verified package inventory differs')
    failure = summary['preserved_failed_first_batch10']
    require(failure['search_actual_exit_code'] == 0 and failure['audit_actual_exit_code'] == 1
            and failure['qualified_track_credit'] == 0
            and summary['actual_search_attempt_count'] == summary['actual_audit_attempt_count'] == 13
            and summary['failed_audit_attempt_count'] == 1,
            'Original provenance failure must remain explicit')
    comparison = failure['original_vs_replayed_binary_sha256']
    require(comparison['compared_members'] == 164
            and comparison['equal_members'] + comparison['different_members'] == 164,
            'Measured binary replay comparison differs')

    on = summary['ON_catalog_hits_ge10']
    off = summary['OFF_catalog_hits_ge10']
    forced = summary['real_forced_ON_OFF_measurements']
    passing = summary['passing_flags']
    if on == 0:
        require(forced == summary['forced_measurement_slots'] == 0,
                'Zero ON seeds must have zero triggered measurements')
        result_sentence = ('Ingen ON-spor nåede den faste lokale ESS-tærskel 10. '
                           'Ingen nye SETI-kandidater er kvalificeret.')
        forced_sentence = ('Der var ingen ON-frø over tærsklen og derfor **ingen faktiske, udløste '
                           'spormålinger på tværs af ON/OFF**. Konsistens i tomme kataloger er ikke '
                           'et selvstændigt fysisk ON/OFF-resultat.')
    else:
        result_sentence = (f'ON-katalogerne indeholder {dk(on)} lokale spor med ESS ≥10. '
                           f'Der blev målt {dk(forced)} understøttede ON/OFF-sporværdier; '
                           f'{dk(passing)} rækker opfyldte de beskrivende ON/OFF-regler.')
        forced_sentence = (f'ON-frøene udløste {dk(summary["forced_measurement_slots"])} målepladser, '
                           f'hvoraf {dk(forced)} var understøttede og '
                           f'{dk(summary["unsupported_forced_slots"])} lå uden for det gemte supportområde. '
                           'Beskrivende flag er ikke kvalificerede SETI-detektioner.')
    authority = summary['original_completed_authority_unchanged']
    ids = authority.get('IDs', authority.get('archive_IDs'))
    require(ids == 486 and authority['technical_MHz_visits'] == 268.50128173828125,
            'Original completed BA authority differs')
    prereg = summary['source_prereg_commit']
    recovery_prereg = summary['recovery_prereg_commit']
    library_url = f'https://chatgpt.com/library?file_id={library_file_id}&account_id=personal'
    elapsed = summary['campaign_wall_seconds']
    search_cpu = summary['search_user_cpu_seconds_sum'] + summary['search_system_cpu_seconds_sum']
    audit_cpu = summary['audit_user_cpu_seconds_sum'] + summary['audit_system_cpu_seconds_sum']
    lines = [
        '# SETI BJ V2 — længere kørsel: bånd 25–120 er gennemsøgt',
        '',
        '30. oktober 2026. **De 12 effektive batches er afsluttet med faktisk exitkode 0 for både søgning '
        'og resultatkontrol. Den første provenancefejl i batch 10 er bevaret.** De 96 ekstra bånd gav '
        f'**{dk(summary["total_correlated_track_trials_including_OFF"])} korrelerede sporkombinationer**. '
        + result_sentence,
        '',
        '| Størrelse | Denne kørsel: BJ | Samlet: BG–BJ |',
        '|---|---:|---:|',
        f'| Faste bånd | 96 (q25–q120) | **120 (q1–q120)** |',
        f'| Carrierkanaler | {dk(summary["carrier_channels"])} | {dk(cumulative["carrier_channels"])} |',
        f'| Teknisk kanalbredde | {dk(summary["technical_channel_bin_bandwidth_Hz"] / 1000000, 6)} MHz | '
        f'**{dk(cumulative["technical_channel_bin_bandwidth_Hz"] / 1000000, 6)} MHz** |',
        f'| Scan/bånd-søgninger | {dk(summary["scan_band_searches"])} | {dk(cumulative["scan_band_searches"])} |',
        f'| Korrelerede sporkombinationer, inklusive OFF | {dk(summary["total_correlated_track_trials_including_OFF"])} | '
        f'**{dk(cumulative["total_correlated_track_trials_including_OFF"])}** |',
        f'| ON-spor med lokal ESS ≥10 | {dk(on)} | {dk(cumulative["ON_catalog_hits_ge10"])} |',
        f'| OFF-spor med lokal ESS ≥10 | {dk(off)} | {dk(cumulative["OFF_catalog_hits_ge10"])} |',
        f'| Faktiske, udløste ON/OFF-spormålinger | {dk(forced)} | '
        f'{dk(cumulative["real_forced_ON_OFF_measurements"])} |',
        f'| Beståede beskrivende ON/OFF-flag | {dk(passing)} | {dk(cumulative["passing_flags"])} |',
        '',
        f'Forløbet tog {dk(elapsed, 2)} sekunder ({dk(elapsed / 60, 2)} minutter) fra den oprindelige start til '
        'V2-afslutningsmarkøren, inklusive stoppet og genoptagelsen. De 12 effektive søgekørsler brugte tilsammen '
        f'{dk(summary["search_wall_seconds_sum"], 2)} sekunders vægtid og {dk(search_cpu, 2)} CPU-sekunder '
        '(bruger- og systemtid). Resultatkontrollerne brugte '
        f'{dk(summary["audit_wall_seconds_sum"], 2)} sekunders vægtid og {dk(audit_cpu, 2)} CPU-sekunder. '
        'Dette er målinger for BJ-kørslen, ikke et samlet forbrug for hele projektet.',
        '',
        'Den første søgning i batch 10 sluttede med exit 0, men efterkontrollen sluttede med **exit 1**: '
        f'logfilen havde {dk(failure["current_saved_log_bytes"])} gemte bytes mod '
        f'{dk(failure["capture_recorded_log_bytes"])} registreret ved procesafslutningen. '
        'Denne log er ikke rekonstrueret, og den fejlede kontrol er ikke omklassificeret som et '
        'godkendt nulresultat. De første ni beståede batches blev fastholdt; batch 10 blev kørt igen '
        'i nye filer med samme båndvalg, tærskler og numeriske kode, hvorefter batch 11–12 blev afsluttet.',
        '',
        f'Den oprindelige batch 10 kostede yderligere {dk(failure["failed_attempt_search_wall_seconds"], 2)} '
        f'sekunders søgetid og {dk(failure["failed_attempt_audit_wall_seconds"], 2)} sekunders fejlet kontrol. '
        f'Alle 13 målte søgeforsøg brugte i alt {dk(summary["total_attempt_search_wall_seconds_sum"], 2)} '
        f'sekunders vægtid og {dk(summary["total_attempt_search_cpu_seconds_sum"], 2)} CPU-sekunder. '
        f'De 13 kontrolforsøg brugte {dk(summary["total_attempt_audit_wall_seconds_sum"], 2)} sekunders '
        f'vægtid og {dk(summary["total_attempt_audit_cpu_seconds_sum"], 2)} CPU-sekunder. '
        'Bånd og sporkombinationer tælles stadig kun én gang i de effektive resultater.',
        '',
        '| Batch | Bånd | ON ≥10 | OFF ≥10 | Søgning, s | Kontrol, s |',
        '|---:|---|---:|---:|---:|---:|'
    ]
    for batch in batches:
        lines.append(f'| {batch["batch"]} | q{batch["q_list"][0]}–q{batch["q_list"][-1]} | '
                     f'{dk(batch["ON_catalog_hits_ge10"])} | {dk(batch["OFF_catalog_hits_ge10"])} | '
                     f'{dk(batch["search_wall_seconds"], 2)} | {dk(batch["audit_wall_seconds"], 2)} |')
    lines.extend([
        '',
        f'BJ dækker frekvenscentrene {dk(summary["core_frequency_low_MHz"], 6)}–'
        f'{dk(summary["core_frequency_high_MHz"], 6)} MHz i de samme seks scans af '
        f'{summary["target"]} fra 28. april 2017: tre ON og tre OFF med 16 tidsrækker hver. '
        'Søgebredderne er fortsat 1, 3, 9 og 33 kanaler med 839 drifttrin over ±4 Hz/s. '
        'De afsluttede q1–q24 er bevaret.',
        '',
        '| Bredde i kanaler | Højeste lokale ESS i ON | Højeste lokale ESS i OFF |',
        '|---:|---:|---:|'
    ])
    for width in (1, 3, 9, 33):
        values = summary['maximum_local_ESS_by_width'][str(width)]
        lines.append(f'| {width} | {dk(values["ON"], 3)} | {dk(values["OFF"], 3)} |')
    lines.extend([
        '',
        f'Alle båndvalg, søgekode, kontrolkode og planer blev [fastholdt på GitHub før beregningen]'
        f'(https://github.com/andersenmartin-blip/setisearch/commit/{prereg}). '
        f'Den særskilte [genoptagelsesplan blev fastholdt før nye kørsler]'
        f'(https://github.com/andersenmartin-blip/setisearch/commit/{recovery_prereg}). '
        'Den numeriske metode er uændret fra BI; AC-normaliseringen beregnes over hele hver '
        'native-række før beskæring. Hver batch fulgtes af en afgrænset resultatkontrol, og '
        'kampagnen var indrettet til at stoppe ved fejl eller et bestået beskrivende signalflag.',
        '',
        f'De 12 beståede efterkontroller omfattede **{dk(summary["independent_scalar_sum_comparisons"])} udvalgte '
        'sporsummer med uafhængig `math.fsum`** og '
        f'**{dk(summary["shared_kernel_calibration_vector_replays"])} kalibreringsgenberegninger '
        'med den delte kernel**. De største observerede afvigelser var '
        f'{dk(summary["maximum_scalar_sum_error"], 6)} for skalarsummer og '
        f'{dk(summary["maximum_replayed_calibration_error"], 6)} for kalibrering. '
        'Proceskvitteringerne registrerer faktisk exitkode, stdout-EOF, afsluttet procesventning '
        'og overensstemmelse mellem observerede og gemte loghashes. Dette er en afgrænset kontrol, '
        'ikke en uafhængig genberegning af alle spor, rådatakodek eller hele normaliseringsmodellen.',
        '',
        forced_sentence,
        '',
        'Resultatet er en beskrivende genanalyse af tidligere eksponerede data fra ét historisk besøg. '
        'ESS kalibreres lokalt pr. bånd, drifttrin, bredde og scan og adskiller sig fra den historiske '
        'full-native ESS. ESS er ikke en kalibreret sigma-værdi, SNR eller falsk-alarm-sandsynlighed. '
        'Sporkombinationerne er korrelerede og må ikke tælles som uafhængige statistiske prøver. '
        'Ingen astronomisk følsomhed, fysisk oprindelse eller opdagelse er kvalificeret.',
        '',
        f'Der blev foretaget {dk(summary["new_archive_requests"])} nye arkivanmodninger og tilføjet '
        f'{dk(summary["new_independent_observations"])} nye observationer. BA-opgørelsen forbliver '
        f'{dk(ids)} unikke arkiv-ID’er og {dk(authority["technical_MHz_visits"], 14)} tekniske MHz-besøg.',
        '',
        f'Binære resultater og genoptagelsesoplysninger er gemt i [{package["file_name"]}]({library_url}). '
        f'Pakken har {dk(package["archive_members"])} medlemmer: 1.968 effektive binære resultatfiler, '
        '164 særskilt mærkede binære filer fra det første fejlede batch 10-forsøg og én genoptagelsesfil. '
        'CRC og SHA-256 er kontrolleret for alle medlemmer. '
        f'Sammenligningen af de 164 tilsvarende binære filer fra oprindelig og genkørt batch 10 viste '
        f'{dk(comparison["equal_members"])} med samme SHA-256 og {dk(comparison["different_members"])} med '
        'forskellige hashes. Denne bytekontrol ændrer ikke den oprindelige fejlede provenancekontrol. '
        'Rådata og programkode er bevaret via eksisterende datakilder og GitHub.',
        '',
        'Næste scope er **q121–q127** med en ny fast plan. Derefter skal **DC-bånd q128 udelades '
        'eksplicit**, før senere sikre bånd vælges. Ingen signalsøgning kører videre i baggrunden '
        'efter denne kampagne.',
        '',
        '- [Samlet resultat og kumulativ status](work_bj/results/REAL_SEARCH_SUMMARY_BJ_V2.json)',
        '- [Kampagnens V2-afslutning](work_bj/results/CAMPAIGN_COMPLETE_BJ_V2.json) og '
        '[det oprindelige stop](work_bj/results/CAMPAIGN_STOP_BJ.json)',
        '- [Faste planer](work_bj/plans) og [søgekode](work_bj/bounded_search_bj.py)',
        '- [Sekventiel processtyring](work_bj/run_campaign_bj.py) og '
        '[afgrænset resultatkontrol](work_bj/review/audit_real_results_bj.py)',
        '- [Datapakke og fortsættelsespunkt](work_bj/DELIVERY_BJ_V2.json)',
        ''
    ])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library-file-id', required=True)
    args = parser.parse_args()
    require(re.fullmatch(r'libfile_[A-Za-z0-9]+', args.library_file_id) is not None,
            'Exact saved Library file ID required')
    summary_path = WORK / 'results/REAL_SEARCH_SUMMARY_BJ_V2.json'
    package_path = WORK / 'results/BINARY_PACKAGE_BJ_V2.json'
    summary, package = read(summary_path), read(package_path)
    require(package['summary_sha256'] == sha(summary_path), 'Package/summary identity differs')
    require(package['source_prereg_commit'] == summary['source_prereg_commit'], 'Preregistration binding differs')
    require(package['recovery_prereg_commit'] == summary['recovery_prereg_commit'], 'Recovery preregistration binding differs')
    output = WORK / 'RADIO_PROGRESS_BJ_V2_2026-10-30.md'
    report = render(summary, package, args.library_file_id)
    with output.open('x') as stream:
        stream.write(report)
    print(json.dumps({'report_path': str(output), 'bytes': output.stat().st_size, 'sha256': sha(output)}))


if __name__ == '__main__':
    main()
